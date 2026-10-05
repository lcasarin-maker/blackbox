"""Strict, read-only evidence gates for the hardware closure family."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tools.capture_io import read_regular_bytes, strict_json_loads

ROOT = Path(__file__).resolve().parents[1]
MAX_CAPTURE_BYTES = 8 * 1024 * 1024


def _generated_id_sets() -> tuple[set[str], set[str]]:
    # Batch membership comes from source-generated evaluator constants. Runtime
    # edits to a JSON inventory must never change which predicate owns an ID.
    from tools.hardware_batch02_controls import IDS as BATCH02_IDS
    from tools.hardware_batch03_controls import CARD_IDS as BATCH03_IDS

    return set(BATCH02_IDS), set(BATCH03_IDS)


def _result(status: str, reason: str, files: list[str] | None = None) -> dict[str, Any]:
    return {"status": status, "reason": reason, "files": files or [],
            "fail": int(status == "fail"), "could_not_run": int(status == "unknown")}


def _adapt_domain_result(result: dict[str, Any], path: Path, filename: str) -> dict[str, Any]:
    status = result.get("status", "unknown")
    findings = result.get("findings", [])
    reason = "; ".join(str(item) for item in findings) or "raw domain observations satisfy the verifier"
    return {**result, "reason": reason,
            "files": [str(path / filename)],
            "fail": int(status == "fail"), "could_not_run": int(status == "unknown")}


def _load_manifest(manifest: Path, finding_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    try:
        raw = read_regular_bytes(manifest, MAX_CAPTURE_BYTES)
        if len(raw) > MAX_CAPTURE_BYTES:
            return None, _result("fail", "capture manifest exceeds the 8 MiB input bound", [str(manifest)])
        data = strict_json_loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        return None, _result("fail", f"capture manifest unreadable or malformed: {exc}", [str(manifest)])
    if not isinstance(data, dict) or data.get("finding_id") != finding_id:
        return None, _result("fail", "manifest finding_id does not match requested subject", [str(manifest)])
    if not isinstance(data.get("captures"), list) or not data["captures"]:
        return None, _result("unknown", "raw captures are absent", [str(manifest)])
    return data, None


def _capture_files(evidence: Path, manifest: Path, rows: list[Any]) -> tuple[set[str], list[str], dict[str, Any] | None]:
    seen: set[str] = set()
    files = [str(manifest)]
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            return seen, files, _result("fail", "capture row lacks a relative path", files)
        rel = Path(row["path"])
        if rel.is_absolute() or ".." in rel.parts:
            return seen, files, _result("fail", "capture path escapes evidence directory", files)
        target = evidence / rel
        try:
            raw = read_regular_bytes(target, MAX_CAPTURE_BYTES)
        except FileNotFoundError:
            return seen, files, _result("unknown", f"raw capture unavailable: {rel}", files)
        except OSError as exc:
            return seen, files, _result("fail", f"unsafe or unreadable raw capture {rel}: {exc}", files)
        if len(raw) > MAX_CAPTURE_BYTES:
            return seen, files, _result("fail", f"raw capture exceeds the 8 MiB input bound: {rel}", files)
        if row.get("sha256") != hashlib.sha256(raw).hexdigest():
            return seen, files, _result("fail", f"raw capture hash mismatch: {rel}", files + [str(target)])
        files.append(str(target))
    return seen, files, None


def inspect_bundle(finding_id: str, evidence: Path, required: set[str]) -> dict[str, Any]:
    """Validate capture identity and hashes; never infer functional success from a report."""
    if not evidence.exists() or not evidence.is_dir():
        return _result("unknown", f"missing evidence directory: {evidence}")
    manifest = evidence / "capture.json"
    if not manifest.is_file():
        return _result("unknown", "capture.json with raw capture inventory is unavailable",
                       [str(p) for p in evidence.iterdir() if p.is_file()])
    data, error = _load_manifest(manifest, finding_id)
    if error:
        return error
    assert data is not None
    seen, files, error = _capture_files(evidence, manifest, data["captures"])
    if error:
        return error
    missing = sorted(required - seen)
    if missing:
        return _result("unknown", "unproven required observations: " + ", ".join(missing), files)
    # Manifest strings are inventory only. Required observations are derived by
    # the finding-specific parsers rather than self-declared claim fields.
    return _result("unknown", "raw traces are intact; domain predicates and controls require adjudication", files)


def _verify_generated(finding_id: str, path: Path) -> dict[str, Any] | None:
    batch02_ids, batch03_ids = _generated_id_sets()
    if finding_id in batch02_ids:
        from tools.hardware_batch02_controls import verify as verify_batch02

        return verify_batch02(finding_id, path)
    if finding_id in batch03_ids:
        from tools.hardware_batch03_controls import verify as verify_batch03

        return _adapt_domain_result(verify_batch03(finding_id, path), path, "capture.json")
    return None


# Criteria stay attached to finding identity so evidence for a neighboring issue cannot
# satisfy a control accidentally. Each label denotes an observation, never a boolean
# supplied outside a hash-verified raw capture.
REQUIREMENTS: dict[str, set[str]] = {
    "FEATURE-FORUM-GPU-CLOCK-CAP-AB-01": {"gpu_identity", "clock_cap_before", "clock_cap_after", "throughput_before", "throughput_after", "temperature_before", "temperature_after", "rollback"},
    "FEATURE-FORUM-WIFI-ISOLATION-01": {"wifi_interface_identity", "association", "route_table", "dns", "positive_connectivity", "isolated_negative", "rollback"},
    "FEATURE-USB-HID-POSTUPDATE-CHECK": {"usb_hid_identity", "boot_before", "boot_after_update", "hid_input_event", "management_access", "rollback"},
    "FORUM-02-GX10-READ-INTEGRITY": {"external_reference_provenance", "buffered_hashes", "direct_hashes", "nvme_health", "ras_edac", "firmware_identity"},
    "FEATURE-APT-CRITICAL-METAPACKAGE-GUARD": {"apt_sources", "apt_indexes_fresh", "critical_removal_blocked", "upgrade_control", "rollback"},
    "DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01": {"arm64_identity", "sources_uri", "index_freshness", "apt_update", "negative_bad_source", "rollback"},
    "DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01": {"oem_identity", "thermal_zones", "fan_rpm", "workload_identity", "coverage_assessment"},
    "DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01": {"oem_identity", "kernel", "driver_loaded", "module_provider", "firmware", "rollback"},
}


def verify(finding_id: str, evidence: str | Path | None = None, *,
           decision_sha256: str | None = None) -> dict[str, Any]:
    """Return pass/fail/unknown while preserving missing evidence as unknown."""
    path = Path(evidence) if evidence is not None else ROOT / "tasks/evidence" / finding_id
    # Generated closure batches resolve before generic inventory.
    generated = _verify_generated(finding_id, path)
    if generated is not None:
        return generated
    if finding_id == "FEATURE-FORUM-GPU-CLOCK-CAP-AB-01":
        from tools.verify_gpu_clock_cap_ab import verify as verify_gpu

        return verify_gpu(path)
    if finding_id == "FEATURE-FORUM-WIFI-ISOLATION-01":
        from tools.verify_wifi_isolation import verify as verify_wifi

        return verify_wifi(path)
    if finding_id == "FEATURE-USB-HID-POSTUPDATE-CHECK":
        from tools.verify_usb_hid_postupdate import verify as verify_usb

        return verify_usb(path)
    if finding_id in {"FEATURE-MEMORYSAVER-02-TRAZADOR", "FEATURE-MEMORYSAVER-04-PACKING-4K"}:
        from tools.verify_memory_saver import verify as verify_memory

        phase = "02-trazador" if finding_id.endswith("02-TRAZADOR") else "04-packing-4k"
        return _adapt_domain_result(verify_memory(phase, path), path, "capture.json")
    if finding_id == "DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01":
        from tools.verify_clock_cap_tradeoff import verify as verify_tradeoff

        return verify_tradeoff()
    if finding_id == "DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01":
        from tools.verify_apt_sources_closure import verify as verify_apt_sources

        captured_path = path / "commands.json"
        result = verify_apt_sources(captured_path, decision_sha256)
        gates = result.get("gates", [])
        reason = "; ".join(
            f"{gate.get('gate', 'gate')}={gate.get('status', 'unknown')}: {gate.get('reason', '')}"
            for gate in gates if isinstance(gate, dict) and gate.get("status") != "pass"
        ) or "APT source evidence satisfies all closure gates"
        status = result.get("status", "unknown")
        return {
            **result,
            "reason": reason,
            "files": [str(captured_path)],
            "fail": int(result.get("fail", int(status == "fail"))),
            "could_not_run": int(result.get("could_not_run", int(status == "unknown"))),
        }
    if finding_id in {
        "FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01",
        "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01",
        "FORUM-00-KERNEL-INITRD-UPDATE-GATE",
        "FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT",
        "FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01",
    }:
        from tools.forum_finding import evaluate

        return evaluate(finding_id, path)
    from tools.forum_finding import SUPPORTED, evaluate

    if finding_id in SUPPORTED:
        return evaluate(finding_id, path)
    return inspect_bundle(finding_id, path, REQUIREMENTS.get(finding_id, {
        "oem_identity", "software_stack", "subject_identity", "positive_case",
        "negative_control", "raw_results", "recovery_or_rollback",
    }))


def is_generated_control_id(finding_id: str) -> bool:
    """Whether a generated batch evaluator owns this exact finding ID."""
    batch02_ids, batch03_ids = _generated_id_sets()
    return finding_id in batch02_ids or finding_id in batch03_ids
