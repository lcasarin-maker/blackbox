"""Evaluate forum preflights against recorded raw command output."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from tools import preflight
from tools.capture_io import read_regular_bytes, strict_json_loads

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED = {
    "DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01",
    "FORUM-00-CX7-HOTPLUG-FAN-PROTECTION",
    "FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01",
    "FORUM-02-GX10-READ-INTEGRITY",
    "FEATURE-FORUM-SBSA-WATCHDOG-STATE-01",
    "FORUM-REALTEK-DRIVER-BINDING-01",
    "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01",
    "FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01",
    "FORUM-00-KERNEL-INITRD-UPDATE-GATE",
    "FORUM-00-REALTEK-EEE-DIRECT-LINK",
    "FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT",
    "FEATURE-FORUM-RESCUE-RUNBOOK-01",
    "FORUM-02-PSTORE-KERNEL-REGRESSION",
    "FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION",
    "FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01",
    "FORUM-02-USB-UVC-EP0",
}
MISSING_CONTROLS = {
    "FORUM-00-CX7-HOTPLUG-FAN-PROTECTION": "fan RPM observability, exact CX7/OEM firmware tuple, thermal A/B, and rollback",
    "FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01": "real per-request trace after worker restart, OEM support, and recovery/rollback",
    "FORUM-02-GX10-READ-INTEGRITY": "trusted external digest, repeated buffered/O_DIRECT reads, NVMe/RAS/firmware correlation",
    "FEATURE-FORUM-SBSA-WATCHDOG-STATE-01": "vendor-defined watchdog owner, boot-state transition, and restart/recovery control",
    "FORUM-REALTEK-DRIVER-BINDING-01": "warm/cold reboot A/B, package/signature proof, alternate-NIC negative, and rollback",
    "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01": "complete kernel/PTX manifest, tested model kernel, OEM support, and rollback",
    "FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01": "update-caused display regression, local/remote recovery, and rollback on identified OEM",
    "FORUM-00-KERNEL-INITRD-UPDATE-GATE": "apt/module checks, target-kernel signed-module proof, and bootable recovery trial",
    "FORUM-00-REALTEK-EEE-DIRECT-LINK": "direct-link peer tuple, repeated stall A/B, unaffected-link control, and rollback",
    "FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT": "effective KMS read, OTA compatibility declaration, accessible recovery, and rollback",
    "FEATURE-FORUM-RESCUE-RUNBOOK-01": "OEM-specific rescue transition, recovery access, and service/boot rollback",
    "FORUM-02-PSTORE-KERNEL-REGRESSION": "readable pstore panic evidence, exact kernel/OEM matrix, and non-regression control",
    "FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION": "matched workload baseline, sensor/OEM mapping, thermal safety, and model-recovery A/B",
    "FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01": "signature-rejection negative, OEM compatibility matrix, and recovery trial",
    "FORUM-02-USB-UVC-EP0": "UVC EP0 reproduction, corrected kernel/firmware version, unaffected-flow control, and rollback",
}
PREFLIGHTS = {
    "FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01": "fallback",
    "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01": "runtime",
    "FORUM-00-KERNEL-INITRD-UPDATE-GATE": "kernel",
    "FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT": "drm",
    "FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01": "gsp",
}
MAX_CAPTURE_BYTES = 4 * 1024 * 1024


def _result(status: str, reason: str, files: list[str]) -> dict[str, Any]:
    return {"status": status, "reason": reason, "files": files,
            "fail": int(status == "fail"), "could_not_run": int(status == "unknown")}


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        raw = read_regular_bytes(path, MAX_CAPTURE_BYTES)
        if len(raw) > MAX_CAPTURE_BYTES:
            return None
        value = strict_json_loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError):
        return None
    return value if isinstance(value, dict) else None


def _raw_commands(path: Path, finding_id: str) -> tuple[list[dict[str, Any]] | None, str | None]:
    data = _read_json(path)
    if data is None or data.get("id") != finding_id or not isinstance(data.get("commands"), list):
        return None, "raw command capture is missing, malformed, or belongs to another finding"
    rows: list[dict[str, Any]] = []
    for row in data["commands"]:
        if not isinstance(row, dict):
            return None, "raw command row is malformed"
        # Accept the two concrete capture formats already used by the repository.
        argv = row.get("argv", row.get("cmd"))
        rc = row.get("exit_code", row.get("exit"))
        if not isinstance(argv, (list, str)) or type(rc) is not int:
            return None, "raw command row lacks literal argv or exit code"
        if not isinstance(row.get("stdout"), str) or not isinstance(row.get("stderr", ""), str):
            return None, "raw command output is malformed"
        rows.append({"argv": argv, "rc": rc, "stdout": row["stdout"], "stderr": row.get("stderr", "")})
    return rows, None


def _evaluate_pstore(finding_id: str, directory: Path) -> dict[str, Any]:
    from tools.verify_forum_pstore import verify as verify_pstore

    result = verify_pstore(finding_id, directory)
    status = result["status"]
    reason = "; ".join(result.get("findings", [])) or "raw pstore and vendor controls verified"
    return _result(status, reason, [str(directory / "finding.json")])


def _recompute_provider_fixtures(commands: list[Any], files: list[str]) -> tuple[dict[str, dict[str, Any]], dict[str, Any] | None]:
    from tools.provider_trace import analyze_file
    results: dict[str, dict[str, Any]] = {}
    for command in commands:
        if not isinstance(command, dict) or not isinstance(command.get("cmd"), str):
            return results, _result("fail", "provider trace command row malformed", files)
        match = re.search(r"tests/fixtures/provider_trace/([a-z0-9-]+)\.jsonl$", command["cmd"])
        if not match:
            continue
        name = match.group(1)
        fixture = ROOT / "tests/fixtures/provider_trace" / f"{name}.jsonl"
        derived = analyze_file(fixture)
        try:
            recorded = strict_json_loads(command.get("stdout", ""))
        except (TypeError, json.JSONDecodeError, RecursionError):
            return results, _result("fail", f"provider fixture {name} output is not valid JSON", files)
        if recorded != derived:
            return results, _result("fail", f"provider fixture {name} output differs from re-evaluation", files)
        results[name] = derived
    return results, None


def _evaluate_real_provider_trace(raw_trace: Path) -> dict[str, Any]:
    from tools.provider_trace import analyze_file

    files = [str(raw_trace)]
    derived = analyze_file(raw_trace)
    if derived.get("could_not_run_count", 0):
        return _result("unknown", "real per-request trace is incomplete: "
                       + "; ".join(derived.get("unknowns", [])), files)
    if derived.get("status") not in {"pass", "block"}:
        return _result("unknown", "real provider trace did not produce an interpretable request sequence", files)
    if derived.get("status") == "block" and not derived.get("findings"):
        return _result("unknown", "real provider trace reports a block without request-level findings", files)
    return _result("unknown", "real request trace recomputed; OEM support and recovery/rollback evidence remain required",
                   files)


def _evaluate_provider_fallback(directory: Path) -> dict[str, Any]:
    path = directory / "provider-trace-run.json"
    document = _read_json(path)
    files = [str(path)]
    raw_trace = directory / "provider-trace.jsonl"
    if raw_trace.exists():
        return _evaluate_real_provider_trace(raw_trace)
    if document is None or document.get("id") != "FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01":
        return _result("unknown", "provider trace run record unavailable or mismatched", files)
    if document.get("input_kind") != "synthetic JSONL fixtures; no workload was generated":
        return _result("fail", "provider record misstates its fixture input provenance", files)
    commands = document.get("commands")
    if not isinstance(commands, list):
        return _result("fail", "provider trace commands are malformed", files)
    results, error = _recompute_provider_fixtures(commands, files)
    if error:
        return error
    healthy = results.get("gpu-healthy")
    cpu = results.get("cpu-only")
    restart = results.get("gpu-to-cpu-respawn")
    if not healthy or healthy.get("status") != "pass" or not cpu or cpu.get("status") != "pass":
        return _result("fail", "healthy-GPU and CPU-request fixture controls do not pass", files)
    if not restart or restart.get("status") != "block" or not restart.get("findings"):
        return _result("fail", "post-respawn GPU-to-CPU negative control is not detected", files)
    return _result("unknown", "fixture controls recompute correctly; no real workload trace, OEM validation, or recovery/rollback was captured", files)


def evaluate(finding_id: str, evidence: str | Path | None = None) -> dict[str, Any]:
    if finding_id not in SUPPORTED:
        return _result("fail", "unsupported forum finding ID", [])
    directory = Path(evidence) if evidence is not None else ROOT / "tasks/evidence" / finding_id
    if finding_id == "FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01":
        return _evaluate_provider_fallback(directory)
    from tools.forum_hardware_subjects import IDS as RAW_SUBJECT_IDS, evaluate as evaluate_subject

    if finding_id in RAW_SUBJECT_IDS:
        return evaluate_subject(finding_id, directory)
    return _evaluate_supported(finding_id, directory)


def _evaluate_supported(finding_id: str, directory: Path) -> dict[str, Any]:
    kind = PREFLIGHTS.get(finding_id)
    if finding_id == "FORUM-02-PSTORE-KERNEL-REGRESSION":
        return _evaluate_pstore(finding_id, directory)
    if kind is None:
        existing = sorted(str(path) for path in directory.rglob("*") if path.is_file()) if directory.is_dir() else []
        return _result("unknown", "finding-specific closure evidence still missing: " + MISSING_CONTROLS[finding_id], existing)
    preflight_path = directory / "preflight.json"
    command_path = directory / "commands.json"
    files = [str(preflight_path), str(command_path)]
    snapshot_doc = _read_json(preflight_path)
    if snapshot_doc is None or snapshot_doc.get("id") != finding_id:
        return _result("unknown", "preflight snapshot absent, malformed, or mismatched", files)
    snapshot = snapshot_doc.get("snapshot")
    if not isinstance(snapshot, dict):
        return _result("fail", "snapshot is not an object", files)
    raw_commands, error = _raw_commands(command_path, finding_id)
    if error:
        return _result("unknown", error, files)
    assert raw_commands is not None
    derived = preflight.CHECKS[kind](snapshot)
    recorded = snapshot_doc.get("preflight_result")
    if recorded != derived:
        return _result("fail", "recorded preflight result differs from re-evaluation", files)
    if derived["status"] == "block":
        return _result("fail", "; ".join(derived["findings"]), files)
    if derived["status"] != "pass":
        return _result("unknown", "; ".join(derived["findings"]), files)

    # The host snapshot proves a healthy instant. It does not prove that the
    # incident-triggering state was recognized, or that recovery and rollback work.
    captures_text = "\n".join(" ".join(row["argv"]) + "\n" + row["stdout"] + row["stderr"]
                              for row in raw_commands)
    if "Permission denied" in captures_text or "could_not_run" in captures_text:
        return _result("unknown", "one or more required raw probes were inaccessible", files)
    return _result("unknown", "healthy preflight matches raw commands; incident negative and recovery/rollback controls are missing", files)
