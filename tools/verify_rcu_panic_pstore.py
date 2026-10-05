"""Verify captured RCU panic/pstore controls without inducing a panic.

Evidence fields and digests are caller-supplied and unauthenticated; digest
matching establishes consistency only, not host or pstore provenance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any


MAX_EVIDENCE_BYTES = 1024 * 1024


def verify(directory: Path) -> dict[str, Any]:
    try:
        path = directory / "recovery.json"
        with path.open("rb") as stream:
            raw = stream.read(MAX_EVIDENCE_BYTES + 1)
        if len(raw) > MAX_EVIDENCE_BYTES:
            return _r("unknown", ["recovery evidence exceeds 1 MiB bounded input"], 1)
        d = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        return _r("unknown", [f"raw recovery evidence unavailable: {exc}"], 1)
    if not isinstance(d, dict):
        return _r("unknown", ["top-level recovery evidence must be a JSON object"], 1)
    try:
        return _evaluate(d)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
        return _r("unknown", [f"raw recovery evidence malformed: {exc}"], 1)


def _evaluate(d: dict[str, Any]) -> dict[str, Any]:
    if type(d.get("schema")) is not int or d["schema"] != 1:
        return _r("fail", ["schema or target boot identity invalid"], 0)
    host = d.get("host")
    if not isinstance(host, dict) or not isinstance(host.get("boot_id"), str) or not host["boot_id"].strip():
        return _r("unknown", ["target boot identity capture missing"], 1)
    active = d.get("active")
    active_result = _active_policy(active)
    if active_result:
        return active_result
    return _forced_test(d, host["boot_id"])


def _active_policy(active: Any) -> dict[str, Any] | None:
    if not isinstance(active, dict):
        return _r("unknown", ["raw active sysctl/cmdline/pstore backend capture incomplete"], 1)
    if not all(isinstance(active.get(k), str) and active[k].strip() for k in ("sysctl_text", "cmdline")):
        return _r("unknown", ["raw active sysctl/cmdline capture incomplete"], 1)
    backend = active.get("pstore_backend_capture")
    if not _real_backend(backend):
        return _r("unknown", ["raw kernel log showing a registered persistent pstore backend is required"], 1)
    try:
        values = _sysctls(active["sysctl_text"])
    except ValueError as exc:
        return _r("fail", [str(exc)], 0)
    if not all(k in values for k in ("kernel.panic_on_rcu_stall", "kernel.panic")):
        return _r("unknown", ["raw active sysctl text lacks required RCU panic keys"], 1)
    if values.get("kernel.panic_on_rcu_stall") != "1" or not values.get("kernel.panic", "0").isdigit() or int(values.get("kernel.panic", "0")) <= 0:
        return _r("fail", ["active RCU panic or reboot timeout does not match requested recovery policy"], 0)
    return None


def _forced_test(d: dict[str, Any], current_boot_id: str) -> dict[str, Any]:
    failure = _validate_record(d.get("forced_test", {}), current_boot_id)
    if failure:
        return failure
    rollback = _validate_rollback(d)
    if rollback:
        return rollback
    # A forced test cannot demonstrate spontaneous RCU recovery.
    return _r("pass", [], 0, natural_rcu_recovery="unobserved")


def _validate_record(test: Any, current_boot_id: str) -> dict[str, Any] | None:
    if not isinstance(test, dict):
        return _r("unknown", ["forced_test must be a raw evidence object"], 1)
    raw = test.get("raw_pstore")
    marker = test.get("expected_marker")
    if not isinstance(raw, str) or not isinstance(marker, str) or not marker.strip() or test.get("raw_pstore_sha256") != hashlib.sha256(raw.encode()).hexdigest():
        return _r("unknown", ["arrival-side forced-panic marker and post-reboot pstore record required"], 1)
    if marker not in raw:
        return _r("fail", ["expected forced-panic marker absent from raw pstore bytes"], 0)
    if not re.search(r"Kernel panic - not syncing:", raw):
        return _r("fail", ["pstore contains marker text without a kernel panic signature"], 0)
    before_boot, after_boot = test.get("boot_before"), test.get("boot_after")
    if not isinstance(before_boot, str) or not before_boot or not isinstance(after_boot, str) or not after_boot:
        return _r("unknown", ["both pre-test and post-test boot IDs are required"], 1)
    if before_boot == after_boot:
        return _r("fail", ["forced panic evidence does not show a new boot"], 0)
    if after_boot != current_boot_id:
        return _r("fail", ["post-test boot ID does not match current target boot capture"], 0)
    return None


def _validate_rollback(d: dict[str, Any]) -> dict[str, Any] | None:
    rollback = d.get("rollback", {})
    kdump = d.get("kdump", {})
    if not isinstance(rollback, dict) or not isinstance(kdump, dict):
        return _r("unknown", ["rollback and kdump raw evidence objects required"], 1)
    before_settings = rollback.get("original_sysctl_text")
    restored_settings = rollback.get("restored_sysctl_text")
    if not isinstance(before_settings, str) or not before_settings or not isinstance(restored_settings, str) or restored_settings != before_settings:
        return _r("fail", ["rollback does not restore the exact original sysctl text"], 0)
    service_raw = kdump.get("systemctl_show")
    if not isinstance(service_raw, str) or not service_raw.strip():
        return _r("unknown", ["raw systemctl show output for kdump required"], 1)
    try:
        service = _sysctls(service_raw)
    except ValueError as exc:
        return _r("fail", [str(exc)], 0)
    if service.get("ActiveState") != "active" or service.get("LoadState") != "loaded":
        return _r("fail", ["rollback or existing kdump control failed"], 0)
    return None


def _real_backend(capture: Any) -> bool:
    if not isinstance(capture, dict) or capture.get("command") != ["dmesg"] or capture.get("returncode") != 0:
        return False
    output = capture.get("stdout")
    return isinstance(output, str) and re.search(r"Registered [A-Za-z0-9_-]+ as persistent store backend", output) is not None


def _sysctls(raw: str) -> dict[str, str]:
    values = {}
    for line in raw.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            key, value = key.strip(), value.strip()
            if key in values and values[key] != value:
                raise ValueError(f"conflicting duplicate value for {key}")
            values[key] = value
    return values


def _r(status: str, findings: list[str], could_not_run: int, **extra: Any) -> dict[str, Any]:
    return {"status": status, "findings": findings, "could_not_run": could_not_run,
            "could_not_run_count": could_not_run, "fail": int(status == "fail"), **extra}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence", type=Path, required=True)
    a = p.parse_args(argv)
    out = verify(a.evidence)
    print(json.dumps(out, sort_keys=True))
    return {"pass": 0, "fail": 1, "unknown": 2}[out["status"]]


if __name__ == "__main__":
    sys.exit(main())
