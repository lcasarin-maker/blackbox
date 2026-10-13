"""Read-only check: does a container's engine process hold a real CUDA context?

States: GPU (libcuda mapped AND listed by nvidia-smi compute-apps with memory),
CPU_FALLBACK (the engine process has no CUDA context: libcuda not mapped, or
mapped but absent from compute-apps), INDETERMINADO (instrument could not
read, no engine process matched, or the signals contradict each other).
Only ``docker exec`` of read commands is used; nothing is restarted or changed.
Measured signal, not intent: a process serving CPU on purpose also reads
CPU_FALLBACK; compare with the request's requested provider (provider_trace).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any, Callable

Runner = Callable[[list[str]], tuple[int, str]]

_MAPS_SCRIPT = (
    'for p in /proc/[0-9]*; do n=$(tr "\\0" " " < $p/cmdline 2>/dev/null | cut -c1-80); '
    'c=$(grep -c libcuda $p/maps 2>/dev/null) || c=ERR; echo "${p#/proc/}|$c|$n"; done'
)
_APPS_CMD = ["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"]


def _docker_runner(argv: list[str]) -> tuple[int, str]:
    try:
        done = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, f"cannot run {argv[0]}: {exc}"
    return done.returncode, done.stdout


def parse_maps(text: str) -> list[dict[str, Any]]:
    """Parse ``pid|libcuda_count|cmd`` lines; an unreadable maps gives libcuda=None."""
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        pid, sep, rest = line.partition("|")
        count, sep2, cmd = rest.partition("|")
        if not (sep and sep2 and pid.isdigit()):
            continue  # not a row of the script's format; ignored by design (shell noise)
        rows.append({"pid": int(pid), "libcuda": int(count) if count.isdigit() else None, "cmd": cmd.strip()})
    return rows


def parse_apps(text: str) -> dict[int, int] | None:
    """Parse nvidia-smi csv (pid, MiB); None when any line is malformed."""
    apps: dict[int, int] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
            return None
        apps[int(parts[0])] = int(parts[1])
    return apps


def classify(processes: list[dict[str, Any]], apps: dict[int, int] | None, match: str) -> dict[str, Any]:
    """Pure verdict from one snapshot. ``apps`` None means nvidia-smi unreadable."""
    reasons: list[str] = []
    if apps is None:
        reasons.append("nvidia-smi compute-apps unreadable")
    targets = [p for p in processes if match in p["cmd"]]
    if not targets:
        reasons.append(f"no process matches {match!r}")
    detail = []
    states: list[str] = []
    for proc in targets:
        mib = (apps or {}).get(proc["pid"], 0)
        lib = proc["libcuda"]
        if lib is None or apps is None:
            state = "INDETERMINADO"
            reasons.append(f"pid {proc['pid']}: maps or compute-apps unreadable")
        elif lib > 0 and mib > 0:
            state = "GPU"
        elif lib == 0 and mib > 0:
            state = "INDETERMINADO"
            reasons.append(f"pid {proc['pid']}: GPU memory without libcuda mapped (contradiction)")
        else:
            state = "CPU_FALLBACK"
        states.append(state)
        detail.append({"pid": proc["pid"], "libcuda_maps": lib, "gpu_mib": mib, "state": state})
    if "GPU" in states:
        verdict = "GPU"
    elif states and all(s == "CPU_FALLBACK" for s in states):
        verdict = "CPU_FALLBACK"
    else:
        verdict = "INDETERMINADO"
    return {"verdict": verdict, "processes": detail, "reasons": reasons}


def check_container(container: str, match: str = "EngineCore", runner: Runner = _docker_runner) -> dict[str, Any]:
    rc_m, maps_out = runner(["docker", "exec", container, "sh", "-c", _MAPS_SCRIPT])
    if rc_m != 0:
        return {"verdict": "INDETERMINADO", "processes": [], "reasons": [f"docker exec maps failed rc={rc_m}"]}
    rc_a, apps_out = runner(["docker", "exec", container, *_APPS_CMD])
    apps = parse_apps(apps_out) if rc_a == 0 else None
    return classify(parse_maps(maps_out), apps, match)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("container")
    parser.add_argument("--match", default="EngineCore", help="substring of the engine process cmdline")
    args = parser.parse_args(argv)
    result = check_container(args.container, args.match)
    print(json.dumps(result, sort_keys=True))
    return {"GPU": 0, "CPU_FALLBACK": 1}.get(result["verdict"], 2)


if __name__ == "__main__":
    sys.exit(main())
