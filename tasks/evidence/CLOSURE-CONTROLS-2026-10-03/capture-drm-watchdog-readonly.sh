#!/usr/bin/env bash
# Fixed read-only observations; JSON goes to caller-controlled stdout.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo 'Requires sudo for root-owned DRM/watchdog observations.' >&2; exit 2; }
exec /usr/bin/python3 - <<'PY_CAPTURE'
import datetime
import hashlib
import json
import shutil
import subprocess
commands = [
    ("drm_modeset", ["cat", "/sys/module/nvidia_drm/parameters/modeset"]),
    ("watchdog_owners", ["lsof", "-nP", "-Fpc", "/dev/watchdog0"]),
    ("watchdog_runtime", ["systemctl", "show", "--property=RuntimeWatchdogUSec"]),
]
rows = []
for name, argv in commands:
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if shutil.which(argv[0]) is None:
        rows.append({"name": name, "argv": argv, "could_not_run": 1, "reason": "command unavailable"})
        continue
    try:
        result = subprocess.run(argv, capture_output=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        rows.append({"name": name, "argv": argv, "could_not_run": 1, "reason": type(exc).__name__})
        continue
    row = {"name": name, "argv": argv, "started_at": started,
           "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "returncode": result.returncode, "could_not_run": 0}
    for stream in ("stdout", "stderr"):
        raw = getattr(result, stream)
        row[stream + "_sha256"] = hashlib.sha256(raw).hexdigest()
        row[stream + "_bytes"] = len(raw)
        if len(raw) > 65536:
            row["could_not_run"] = 1
            row[stream + "_unavailable"] = "output exceeds bounded evidence size"
        else:
            try:
                row[stream] = raw.decode("utf-8")
            except UnicodeDecodeError:
                row["could_not_run"] = 1
                row[stream + "_unavailable"] = "output is not UTF8"
    if result.returncode != 0:
        row["could_not_run"] = 1
        row["reason"] = "query failed or owner attribution is incomplete; empty output does not prove absence"
    rows.append(row)
report = {"schema": 1, "execution_scope": "privileged read-only", "changes_performed": False,
          "physical_closures": 0, "rows": rows,
          "could_not_run": sum(row["could_not_run"] for row in rows)}
print(json.dumps(report, indent=2))
raise SystemExit(2 if report["could_not_run"] else 0)
PY_CAPTURE
