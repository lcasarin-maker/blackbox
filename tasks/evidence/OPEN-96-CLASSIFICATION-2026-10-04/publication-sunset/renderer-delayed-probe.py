"""Focal 120 ms delayed-renderer cleanup probe; run from repository root."""
from __future__ import annotations

import importlib.util
import json
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "bb_bash_renderer_sunset_probe", ROOT / "tests/test_bb_bash.py"
)
if spec is None or spec.loader is None:
    raise SystemExit("could not load tests/test_bb_bash.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
real_sleep = time.sleep
real_killpg = os.killpg


class AlreadyReapedParent:
    """Stand-in for the killed main process; the renderer remains a real child."""

    pid = 987654321

    def wait(self, **_kwargs: object) -> int:
        return 0


def run_trial(neutralized: bool) -> dict[str, object]:
    marker = "renderer-delay-" + uuid.uuid4().hex
    renderer = subprocess.Popen(
        ["bash", "-c", f"exec -a {marker} sleep 300"], start_new_session=True
    )
    ready_deadline = time.monotonic() + 3
    while time.monotonic() < ready_deadline:
        ready = subprocess.run(
            ["pgrep", "-f", marker], capture_output=True, text=True, check=False
        )
        if ready.stdout.strip():
            break
        real_sleep(0.01)  # blocking-sleep: intervalo de sondeo DENTRO del bucle con deadline explicito de 3 s (arriba) -- DEBT-RENDERER-PROBE-SLEEP-01  # sunset-reviewed: 2.5 -- sleep justificado por ficha DEBT-RENDERER-PROBE-SLEEP-01 (2026-10-05); revisar al cerrar la ficha
    else:
        renderer.kill()
        renderer.wait()
        raise RuntimeError("temporary renderer marker did not appear")

    delayed_termination: list[bool] = []
    original_killpg = module.os.killpg
    original_sleep = module.time.sleep
    original_run = module.subprocess.run
    pgrep_calls = [0]

    def request_delayed_renderer_termination(_pgid: int, _sig: int) -> None:
        def terminate_after_delay() -> None:
            real_sleep(0.12)  # blocking-sleep: el retraso de 120 ms ES el sujeto de la prueba (terminacion diferida del renderer), no una espera de sincronizacion -- DEBT-RENDERER-PROBE-SLEEP-01  # sunset-reviewed: 2.5 -- sleep justificado por ficha DEBT-RENDERER-PROBE-SLEEP-01 (2026-10-05); revisar al cerrar la ficha
            try:
                real_killpg(renderer.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            delayed_termination.append(True)

        threading.Thread(target=terminate_after_delay, daemon=True).start()

    def count_cleanup_pgrep(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        pgrep_calls[0] += 1
        return original_run(*args, **kwargs)

    module.os.killpg = request_delayed_renderer_termination
    module.subprocess.run = count_cleanup_pgrep
    module.time.sleep = (lambda _seconds: None) if neutralized else real_sleep
    started = time.monotonic()
    try:
        remaining = module._matar_electron_falso(
            AlreadyReapedParent(), [marker], timeout=2
        )
        elapsed = time.monotonic() - started
    finally:
        module.os.killpg = original_killpg
        module.subprocess.run = original_run
        module.time.sleep = original_sleep
        if renderer.poll() is None:
            try:
                real_killpg(renderer.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            renderer.wait(timeout=2)

    return {
        "mode": "neutralized" if neutralized else "50ms-poll",
        "verdict": "remaining-empty" if remaining == [""] else repr(remaining),
        "pgrep_calls": pgrep_calls[0],
        "elapsed_seconds": round(elapsed, 3),
        "delayed_termination": bool(delayed_termination),
    }


print(
    "scenario: actual temporary marker process, async SIGKILL delayed 120 ms "
    "after cleanup request; helper deadline 2 s"
)
print(json.dumps(run_trial(False), sort_keys=True))
print(json.dumps(run_trial(True), sort_keys=True))
