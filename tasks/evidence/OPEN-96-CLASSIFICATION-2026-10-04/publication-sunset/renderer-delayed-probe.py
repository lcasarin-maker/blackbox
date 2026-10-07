"""Focal delayed-renderer cleanup probe; run from repository root.

Every wait in this probe is on a real signal, never on elapsed time:
- readiness: Popen returns only after execve succeeded (its CLOEXEC error pipe
  reaches EOF), so the marker argv is in /proc/<pid>/cmdline when it returns;
  one pgrep then confirms it, with no polling loop.
- deferred termination: after the cleanup request (the killpg stand-in), the
  renderer stays alive until the helper's own pgrep has SEEN it alive
  DEFERRED_ALIVE_OBSERVATIONS times; only then is it SIGKILLed and reaped with
  waitpid (renderer.wait), the real termination signal.
- immediate termination (negative control): SIGKILL plus waitpid inside the
  killpg stand-in itself, so the helper's first pgrep must already find nothing.
The probe exits 1 when it cannot tell the deferred trials from the immediate one.
"""
from __future__ import annotations

import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from unittest import mock


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "bb_bash_renderer_sunset_probe", ROOT / "tests/test_bb_bash.py"
)
if spec is None or spec.loader is None:
    raise SystemExit("could not load tests/test_bb_bash.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
real_killpg = os.killpg
DEFERRED_ALIVE_OBSERVATIONS = 2


class AlreadyReapedParent:
    """Stand-in for the killed main process; the renderer remains a real child."""

    pid = 987654321

    def wait(self, **_kwargs: object) -> int:
        return 0


def run_trial(deferred: bool, neutralized: bool) -> dict[str, object]:
    marker = "renderer-delay-" + uuid.uuid4().hex
    # executable= keeps argv[0] == marker with no intermediate shell; Popen
    # blocks until exec succeeded, which is the readiness signal.
    renderer = subprocess.Popen(
        [marker, "300"], executable="sleep", start_new_session=True
    )
    ready = subprocess.run(
        ["pgrep", "-f", marker], capture_output=True, text=True, check=False
    )
    if not ready.stdout.strip():
        renderer.kill()
        renderer.wait()
        raise RuntimeError("renderer marker absent after exec returned")

    original_run = subprocess.run
    termination_requested = [False]
    alive_observations = [0]
    alive_before_kill: list[int] = []
    pgrep_calls = [0]

    def terminate_now() -> None:
        try:
            real_killpg(renderer.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        renderer.wait(timeout=2)  # waitpid: the process has terminated
        alive_before_kill.append(alive_observations[0])

    def request_renderer_termination(_pgid: int, _sig: int) -> None:
        termination_requested[0] = True
        if not deferred:
            terminate_now()

    def observe_cleanup_pgrep(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if (
            termination_requested[0]
            and not alive_before_kill
            and alive_observations[0] >= DEFERRED_ALIVE_OBSERVATIONS
        ):
            terminate_now()
        pgrep_calls[0] += 1
        result = original_run(*args, **kwargs)
        if result.stdout.strip():
            alive_observations[0] += 1
        return result

    patches = [
        mock.patch.object(module.os, "killpg", request_renderer_termination),
        mock.patch.object(module.subprocess, "run", observe_cleanup_pgrep),
    ]
    if neutralized:
        # Neutralizes the HELPER's 50 ms poll interval (the subject), not a wait of this probe.
        patches.append(mock.patch.object(module.time, "sleep", lambda _seconds: None))
    started = time.monotonic()
    try:
        for patch in patches:
            patch.start()
        try:
            remaining = module._matar_electron_falso(
                AlreadyReapedParent(), [marker], timeout=2
            )
        finally:
            for patch in reversed(patches):
                patch.stop()
        elapsed = time.monotonic() - started
    finally:
        if renderer.poll() is None:
            try:
                real_killpg(renderer.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            renderer.wait(timeout=2)

    return {
        "termination": "deferred" if deferred else "immediate",
        "mode": "neutralized" if neutralized else "50ms-poll",
        "verdict": "remaining-empty" if remaining == [""] else repr(remaining),
        "pgrep_calls": pgrep_calls[0],
        "alive_observations_before_kill": alive_before_kill[0] if alive_before_kill else None,
        "elapsed_seconds": round(elapsed, 3),
    }


def distinguishes(trial: dict[str, object]) -> bool:
    alive = trial["alive_observations_before_kill"]
    if trial["verdict"] != "remaining-empty" or not isinstance(alive, int):
        return False
    if trial["termination"] == "deferred":
        # >= 1 is absolute: a deferral constant collapsed to 0 must not match itself.
        return (
            alive >= 1
            and alive == DEFERRED_ALIVE_OBSERVATIONS
            and trial["pgrep_calls"] == DEFERRED_ALIVE_OBSERVATIONS + 1
        )
    return alive == 0 and trial["pgrep_calls"] == 1


print(
    "scenario: actual temporary marker process; deferred SIGKILL after the helper's "
    f"pgrep has seen it alive {DEFERRED_ALIVE_OBSERVATIONS} times, immediate SIGKILL "
    "inside the cleanup request as negative control; helper deadline 2 s"
)
trials = [run_trial(True, False), run_trial(True, True), run_trial(False, False)]
for trial in trials:
    print(json.dumps(trial, sort_keys=True))
if not all(distinguishes(trial) for trial in trials):
    print("probe-verdict: CANNOT-DISTINGUISH deferred from immediate termination")
    raise SystemExit(1)
print("probe-verdict: deferred and immediate termination distinguished")
