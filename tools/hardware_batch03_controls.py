"""Evaluate seven generated hardware/forum investigations from bounded captures.

The capture contract is intentionally evidence-first: each measurement artifact
is read as raw bytes, bounded, and checked against an independent ``sha256sum``
receipt. The command/provenance receipts are caller supplied, so matching hashes
prove byte consistency only; they do not authenticate who ran a command or the
physical host that produced its output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
from typing import Any

from tools.capture_io import read_regular_bytes, strict_json_loads as _strict_json
from tools.hitos_incidente import _journal_time

MAX_CAPTURE_BYTES = 8 * 1024 * 1024
CARD_IDS = {
    "DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01",
    "DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01",
    "DELTA-FORUM-USB-RAID-LINK-ADMISSION-01",
    "DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01",
    "DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01",
    "DELTA-ROOT-GX10-SOC-EC-CABLE-RECOVERY-CANDIDATE-01",
    "DELTA-ROOT-SUBAMBIENT-COOLING-AND-UMA-CANARY-01",
}


class MissingEvidence(Exception):
    """Evidence is absent, unreadable, or insufficient to classify."""


def _regular_bytes(path: Path) -> bytes:
    return read_regular_bytes(path, MAX_CAPTURE_BYTES)


def _result(status: str, findings: list[str], could_not_run: int = 0) -> dict[str, Any]:
    return {"status": status, "findings": findings, "could_not_run": could_not_run,
            "could_not_run_count": could_not_run, "fail": int(status == "fail"),
            "provenance": "caller-supplied; hashes establish consistency, not authenticity"}


def verify(card_id: str, evidence_path: Path) -> dict[str, Any]:
    """Recompute a generated card's predicates from captured native outputs."""
    try:
        path = evidence_path / "capture.json" if evidence_path.is_dir() else evidence_path
        if path.is_symlink():
            return _result("unknown", ["capture.json must be a regular non-symlink input"], 1)
        raw = _regular_bytes(path)
        if len(raw) > MAX_CAPTURE_BYTES:
            return _result("unknown", ["capture.json exceeds the 8 MiB input bound"], 1)
        document = _strict_json(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        return _result("unknown", [f"raw card capture unavailable: {type(exc).__name__}: {exc}"], 1)
    if not isinstance(document, dict):
        return _result("unknown", ["capture top level must be an object"], 1)
    identity_result = _validate_document_identity(card_id, document)
    if identity_result:
        return identity_result
    return _evaluate_document(card_id, document, path.parent)


def _validate_document_identity(card_id: str, document: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(card_id, str) or card_id not in CARD_IDS:
        return _result("fail", ["unsupported exact card id"], 0)
    if document.get("card_id") is not None and document.get("card_id") != card_id:
        return _result("fail", ["schema or exact card identity mismatch"], 0)
    if document.get("schema") is None or document.get("card_id") is None:
        return _result("unknown", ["capture lacks the required schema/card identity binding"], 1)
    if type(document.get("schema")) is not int or document["schema"] != 1:
        return _result("unknown", ["capture schema version is unsupported or malformed"], 1)
    return None


def _evaluate_document(card_id: str, document: dict[str, Any], directory: Path) -> dict[str, Any]:
    try:
        captures = _capture_index(document.get("captures"), directory)
        context = _target_context(captures)
        check = _EVALUATORS[card_id]
        return check(document, captures, context)
    except MissingEvidence as exc:
        return _result("unknown", [str(exc)], 1)
    except ValueError as exc:
        return _result("fail", [f"raw evidence contradicts a required identity/integrity predicate: {exc}"])
    except (KeyError, TypeError, AttributeError, OverflowError, ZeroDivisionError) as exc:
        return _result("unknown", [f"raw evidence malformed: {type(exc).__name__}: {exc}"], 1)


def _capture_index(raw: Any, directory: Path) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        raise MissingEvidence("bounded native command captures are required")
    indexed: dict[str, dict[str, Any]] = {}
    for row in raw:
        if not isinstance(row, dict):
            raise MissingEvidence("capture record must be an object")
        key = row.get("name")
        if not isinstance(key, str) or not key:
            raise MissingEvidence("capture record needs a nonempty string name")
        if key in indexed:
            raise ValueError("capture names must be unique nonempty strings")
        indexed[key] = _capture_record(row, key, directory)
    for required in ("host_diagnostics", "thermal_coverage", "study"):
        if required not in indexed:
            raise MissingEvidence(f"required {required} native capture is absent")
    if indexed["host_diagnostics"]["command"] != ["python3", "-m", "tools.host_diagnostics"]:
        raise ValueError("host identity must come from the existing read-only host_diagnostics collector")
    if indexed["thermal_coverage"]["command"] != ["python3", "-m", "tools.thermal_coverage"]:
        raise ValueError("sensor inventory must come from the existing thermal_coverage collector")
    return indexed


def _capture_record(row: dict[str, Any], key: str, directory: Path) -> dict[str, Any]:
    command, code, stderr = row.get("command"), row.get("returncode"), row.get("stderr")
    if not _valid_argv(command):
        raise MissingEvidence(f"{key}: literal argv capture absent or invokes a shell")
    if type(code) is not int or not isinstance(stderr, str):
        raise MissingEvidence(f"{key}: literal process result/stderr missing")
    relative = row.get("artifact")
    if not isinstance(relative, str) or not relative:
        raise MissingEvidence(f"{key}: raw artifact path missing")
    artifact = Path(relative)
    if artifact.is_absolute() or ".." in artifact.parts:
        raise ValueError(f"{key}: artifact path escapes evidence directory")
    raw_bytes = _bounded_artifact(directory / artifact, key)
    _check_sha_oracle(row.get("sha256_oracle"), relative, raw_bytes, key)
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeError as exc:
        raise MissingEvidence(f"{key}: raw artifact is not UTF-8 text") from exc
    if code != 0:
        raise MissingEvidence(f"{key}: native capture command returned {code}")
    return {**row, "raw_bytes": raw_bytes, "text": text, "sha256": hashlib.sha256(raw_bytes).hexdigest()}


def _valid_argv(command: Any) -> bool:
    return (isinstance(command, list) and bool(command) and
            all(isinstance(part, str) and part for part in command) and
            not any(part in ("-c", "-lc", "--command") for part in command))


def _bounded_artifact(source: Path, key: str) -> bytes:
    if source.is_symlink():
        raise ValueError(f"{key}: raw artifact must not be a symlink")
    try:
        raw_bytes = _regular_bytes(source)
    except OSError as exc:
        raise MissingEvidence(f"{key}: bounded raw artifact unreadable: {exc}") from exc
    if len(raw_bytes) > MAX_CAPTURE_BYTES:
        raise MissingEvidence(f"{key}: raw artifact exceeds 8 MiB input bound")
    return raw_bytes


def _check_sha_oracle(oracle: Any, relative: str, raw_bytes: bytes, key: str) -> None:
    if not isinstance(oracle, dict):
        raise MissingEvidence(f"{key}: independent sha256sum command receipt missing")
    if (oracle.get("command") != ["sha256sum", relative] or type(oracle.get("returncode")) is not int or
            oracle.get("returncode") != 0 or not isinstance(oracle.get("stdout"), str)):
        raise MissingEvidence(f"{key}: sha256sum oracle command/result missing")
    expected_line = f"{hashlib.sha256(raw_bytes).hexdigest()}  {relative}\n"
    if oracle["stdout"] != expected_line:
        raise ValueError(f"{key}: independent sha256sum output does not match raw artifact bytes")


def _json_capture(captures: dict[str, dict[str, Any]], key: str) -> Any:
    try:
        return _strict_json(captures[key]["text"])
    except (json.JSONDecodeError, KeyError, RecursionError) as exc:
        raise MissingEvidence(f"{key}: raw JSON capture malformed or missing") from exc


def _target_context(captures: dict[str, dict[str, Any]]) -> dict[str, Any]:
    host = _json_capture(captures, "host_diagnostics")
    thermal = _json_capture(captures, "thermal_coverage")
    if not isinstance(host, dict) or not isinstance(thermal, dict):
        raise MissingEvidence("host/sensor collector outputs must be JSON objects")
    if host.get("schema") != 1 or thermal.get("schema") != 1:
        raise ValueError("existing collector schema mismatch")
    identity = host.get("identity")
    target = thermal.get("host")
    dmi = target.get("dmi") if isinstance(target, dict) else None
    if not isinstance(identity, dict) or not isinstance(dmi, dict):
        raise MissingEvidence("raw kernel/architecture and DMI identity captures required")
    values: dict[str, str] = {}
    for key in ("kernel_release", "architecture"):
        value = identity.get(key)
        if not isinstance(value, str) or not value.strip():
            raise MissingEvidence(f"host_diagnostics lacks {key}")
        values[key] = value.strip()
    for key in ("sys_vendor", "product_name", "product_version", "board_name"):
        row = dmi.get(key)
        if not isinstance(row, dict) or row.get("status") != "ok" or not isinstance(row.get("value"), str) or not row["value"].strip():
            raise MissingEvidence(f"thermal_coverage lacks readable DMI {key}")
        values[key] = row["value"].strip()
    if (not isinstance(target, dict) or target.get("system") != "Linux" or
            thermal.get("status") not in ("observed", "partial")):
        raise MissingEvidence("thermal_coverage does not identify a Linux sensor inventory")
    if values["kernel_release"] != target.get("release") or values["architecture"] != target.get("machine"):
        raise ValueError("host_diagnostics and thermal_coverage identify different running stacks")
    values["thermal_capture_sha256"] = captures["thermal_coverage"]["sha256"]
    values["host_capture_sha256"] = captures["host_diagnostics"]["sha256"]
    values["study_capture_sha256"] = captures["study"]["sha256"]
    return {"host": host, "thermal": thermal, "identity": values}


def _study_rows(captures: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    capture = captures["study"]
    try:
        rows = [_strict_json(line) for line in capture["text"].splitlines() if line.strip()]
    except (json.JSONDecodeError, RecursionError) as exc:
        raise MissingEvidence("study artifact must contain raw JSON Lines") from exc
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise MissingEvidence("study JSON Lines are absent or not objects")
    return rows


def _subject(context: dict[str, Any], *, vendor: str | None = None,
             product: str | None = None, arch: str = "aarch64") -> dict[str, Any] | None:
    identity = context["identity"]
    if identity["architecture"] != arch:
        return {"status": "fail", "finding": "captured architecture does not match the investigated platform"}
    if vendor and vendor.casefold() not in identity["sys_vendor"].casefold():
        return {"status": "fail", "finding": "captured OEM does not match the card's exact subject"}
    if product and product.casefold() not in identity["product_name"].casefold():
        return {"status": "fail", "finding": "captured product/SKU does not match the card's exact subject"}
    return None


def _need_fields(row: dict[str, Any], fields: tuple[str, ...], label: str) -> None:
    absent = [key for key in fields if key not in row]
    if absent:
        raise MissingEvidence(f"{label}: raw fields absent: {', '.join(absent)}")


def _finite_number(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise MissingEvidence(f"{label}: finite numeric measurement required")
    return float(value)


def _ordered_samples(run: dict[str, Any], label: str) -> list[dict[str, Any]]:
    samples = run.get("samples")
    if not isinstance(samples, list) or len(samples) < 2 or any(not isinstance(x, dict) for x in samples):
        raise MissingEvidence(f"{label}: at least two raw time-series samples required")
    stamps = [x.get("timestamp_ns") for x in samples]
    if any(type(x) is not int or x < 0 for x in stamps):
        raise MissingEvidence(f"{label}: integer monotonic timestamps required")
    if any(a >= b for a, b in zip(stamps, stamps[1:])):
        raise ValueError(f"{label}: sample timestamps are not strictly increasing")
    if not isinstance(run.get("boot_id"), str) or not run["boot_id"].strip():
        raise MissingEvidence(f"{label}: boot identity absent")
    return samples


def _run_index(rows: list[dict[str, Any]], key: str = "case") -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        name = row.get(key)
        if not isinstance(name, str) or not name or name in indexed:
            raise ValueError("study rows need unique literal case labels")
        indexed[name] = row
    return indexed


def _native_result(row: dict[str, Any], name: str) -> tuple[int, str, str]:
    """Extract a literal argv/rc/stdout/stderr receipt from a case row."""
    commands = row.get("native_commands")
    result = commands.get(name) if isinstance(commands, dict) else None
    if not isinstance(result, dict):
        raise MissingEvidence(f"{name}: native command receipt missing")
    argv = result.get("argv")
    if (not isinstance(argv, list) or not argv or any(not isinstance(arg, str) or not arg for arg in argv)
            or any(arg in ("-c", "-lc", "--command") for arg in argv)):
        raise MissingEvidence(f"{name}: literal shell-free argv required")
    expected_programs = {
        "mdadm_detail": "mdadm", "findmnt": "findmnt", "driver_parameter": "journalctl",
        "sway": "systemctl", "ssh": "ssh", "scanout_log": "journalctl", "window_events": "cat",
        "pci_inventory": "lspci", "module_inventory": "lsmod", "carrier": "cat",
        "eeprom": "ethtool", "link": "ethtool", "tx_before": "cat", "tx_after": "cat",
        "rx_before": "cat", "rx_after": "cat",
    }
    expected_program = expected_programs.get(name)
    if expected_program is not None and argv[0] != expected_program:
        raise MissingEvidence(f"{name}: native output must come from {expected_program}")
    code, stdout, stderr = result.get("returncode"), result.get("stdout"), result.get("stderr")
    if type(code) is not int or not isinstance(stdout, str) or not isinstance(stderr, str):
        raise MissingEvidence(f"{name}: literal return code/stdout/stderr required")
    return code, stdout, stderr


def _findmnt_targets(stdout: str) -> list[dict[str, Any]]:
    try:
        data = _strict_json(stdout)
    except (json.JSONDecodeError, RecursionError) as exc:
        raise MissingEvidence("findmnt output must be raw JSON") from exc
    filesystems = data.get("filesystems") if isinstance(data, dict) else None
    if not isinstance(filesystems, list):
        raise MissingEvidence("findmnt JSON lacks filesystems array")
    if any(not isinstance(row, dict) for row in filesystems):
        raise MissingEvidence("findmnt JSON filesystem records must be objects")
    return filesystems


def _thermal_aux(document: dict[str, Any], captures: dict[str, dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    wrong = _subject(context, vendor="ASUS", product="GX10")
    if wrong:
        return _result(wrong["status"], [wrong["finding"]])
    runs = _run_index(_study_rows(captures))
    required = {"stock", "base_fan", "extractor_plus_clock_cap", "negative_control"}
    if set(runs) != required:
        raise MissingEvidence("matched stock, base-fan, extractor/clock-cap, and negative-control runs required")
    profiles: dict[str, tuple[float, float, float, float]] = {}
    workload_ids: set[str] = set()
    ambient: set[float] = set()
    ambient_sources: set[str] = set()
    versions: set[tuple[str, str, str]] = set()
    for name in ("stock", "base_fan", "extractor_plus_clock_cap"):
        run = runs[name]
        metadata = _thermal_run_metadata(name, run, context)
        workload_ids.add(metadata[0])
        ambient.add(metadata[1])
        ambient_sources.add(metadata[2])
        versions.add(metadata[3])
        profile, failure = _thermal_profile(name, run, context, captures)
        if failure:
            return failure
        assert profile is not None
        profiles[name] = profile
    if len(workload_ids) != 1 or len(ambient) != 1 or len(ambient_sources) != 1 or len(versions) != 1:
        raise MissingEvidence("A/B runs must share workload, ambient source/value and exact software/firmware stack")
    if not _rollback_complete(runs, ("stock", "base_fan", "extractor_plus_clock_cap")):
        raise MissingEvidence("stock airflow/clock configuration rollback lacks byte-identical before/after captures")
    baseline = profiles["stock"]
    treated = profiles["base_fan"]
    capped = profiles["extractor_plus_clock_cap"]
    if capped[3] > 2000:
        return _result("fail", ["extractor treatment did not measure the requested 2 GHz clock cap"])
    negative_failure = _thermal_negative(runs["negative_control"])
    if negative_failure:
        return negative_failure
    return _result("pass", [f"matched ASUS GX10 results measured: base-fan ΔGPU={treated[0] - baseline[0]:.2f} C, "
                             f"extractor/cap ΔGPU={capped[0] - baseline[0]:.2f} C, "
                             f"throughput deltas={treated[2] - baseline[2]:.3f}/{capped[2] - baseline[2]:.3f}; "
                             "recorded limit values held; their source provenance remains caller supplied"])


def _thermal_run_metadata(name: str, run: dict[str, Any], context: dict[str, Any]) -> tuple[str, float, str, tuple[str, str, str]]:
    fields = ("workload_id", "ambient_c", "ambient_source", "kernel_release", "driver_version",
              "firmware_version", "oem_limits", "samples", "configuration_sha256")
    _need_fields(run, fields, name)
    workload = run["workload_id"]
    if not isinstance(workload, str) or not re.fullmatch(r"[0-9a-f]{64}", workload):
        raise MissingEvidence(f"{name}: exact SHA-256 workload identity required")
    driver, firmware = run["driver_version"], run["firmware_version"]
    if (run["kernel_release"] != context["identity"]["kernel_release"] or
            not isinstance(driver, str) or not driver.strip() or
            not isinstance(firmware, str) or not firmware.strip()):
        raise MissingEvidence(f"{name}: exact matching kernel, driver and firmware stack required")
    source = run["ambient_source"]
    if not isinstance(source, str) or not source.strip():
        raise MissingEvidence(f"{name}: ambient measurement source identity required")
    version = (run["kernel_release"], driver, firmware)
    return workload, _finite_number(run["ambient_c"], f"{name}.ambient_c"), source, version


def _thermal_negative(negative: dict[str, Any]) -> dict[str, Any] | None:
    fields = ("baseline_ambient_c", "candidate_ambient_c", "baseline_workload_id", "candidate_workload_id")
    _need_fields(negative, fields, "negative_control")
    mismatch = (negative["baseline_ambient_c"] != negative["candidate_ambient_c"] or
                negative["baseline_workload_id"] != negative["candidate_workload_id"])
    if not mismatch:
        return _result("fail", ["negative control contains no actual ambient/workload mismatch to reject"])
    return None


def _thermal_profile(name: str, run: dict[str, Any], context: dict[str, Any], captures: dict[str, dict[str, Any]]) -> tuple[tuple[float, float, float, float] | None, dict[str, Any] | None]:
    samples = _ordered_samples(run, name)
    limits = run["oem_limits"]
    if not isinstance(limits, dict) or limits.get("stack_sha256") != context["identity"]["thermal_capture_sha256"]:
        raise MissingEvidence(f"{name}: OEM thermal/power limits must bind to captured stack identity")
    limit_capture = captures.get("oem_limits_doc")
    if limit_capture is None:
        raise MissingEvidence(f"{name}: raw OEM limit document capture is missing")
    if limits.get("document_sha256") != limit_capture["sha256"]:
        raise MissingEvidence(f"{name}: limit values are not bound to the captured OEM document bytes")
    source_limits = _parse_oem_limits(limit_capture["text"])
    keys = ("gpu_c", "cpu_c", "inlet_c", "psu_zone_c", "wall_power_w", "throughput", "gpu_clock_mhz")
    sums = {key: 0.0 for key in keys}
    for sample in samples:
        _need_fields(sample, keys, name)
        for key in keys:
            sums[key] += _finite_number(sample[key], f"{name}.{key}")
        failure = _check_thermal_sample(name, sample, limits, source_limits)
        if failure:
            return None, failure
    divisor = len(samples)
    profile = (sums["gpu_c"] / divisor, sums["psu_zone_c"] / divisor,
               sums["throughput"] / divisor, sums["gpu_clock_mhz"] / divisor)
    if not isinstance(run["configuration_sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", run["configuration_sha256"]):
        raise MissingEvidence(f"{name}: configuration snapshot digest required")
    return profile, None


def _check_thermal_sample(name: str, sample: dict[str, Any], limits: dict[str, Any],
                          source_limits: dict[str, float]) -> dict[str, Any] | None:
    if sample.get("throttled") is not False or sample.get("shutdown") is not False:
        return _result("fail", [f"{name}: observed throttling or shutdown during the controlled run"])
    bounded = (("gpu_c", "gpu_max_c"), ("cpu_c", "cpu_max_c"),
               ("psu_zone_c", "psu_zone_max_c"), ("wall_power_w", "wall_power_max_w"))
    for key, limit_key in bounded:
        limit = _finite_number(limits.get(limit_key), f"OEM {limit_key} limit")
        if source_limits.get(limit_key) != limit:
            raise MissingEvidence(f"{name}: {limit_key} disagrees with raw OEM document")
        if sample[key] > limit:
            return _result("fail", [f"{name}: measured sample violates a stack-bound OEM limit"])
    return None


def _parse_oem_limits(text: str) -> dict[str, float]:
    keys = ("gpu_max_c", "cpu_max_c", "psu_zone_max_c", "wall_power_max_w")
    values: dict[str, float] = {}
    if not isinstance(text, str) or not text.strip():
        raise MissingEvidence("raw OEM limit document is empty")
    for line in text.splitlines():
        match = re.fullmatch(r"([a-z_]+)=([0-9]+(?:\.[0-9]+)?)", line)
        if match is None or match.group(1) not in keys or match.group(1) in values:
            raise MissingEvidence("OEM limit document contains malformed, duplicate, or unrecognized rows")
        values[match.group(1)] = float(match.group(2))
    missing = [key for key in keys if key not in values]
    if missing:
        raise MissingEvidence(f"OEM document lacks explicit {', '.join(missing)} values in the documented capture format")
    return values


def _rollback_complete(runs: dict[str, dict[str, Any]], names: tuple[str, ...]) -> bool:
    for name in names:
        row = runs[name]
        before, after = row.get("configuration_before"), row.get("configuration_after")
        if not isinstance(before, dict) or not before or not isinstance(after, dict) or before != after:
            return False
        if not all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
                   for value in before.values()):
            return False
    return True


def _thermal_coverage(document: dict[str, Any], captures: dict[str, dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    wrong = _subject(context, vendor="ASUS", product="GX10")
    if wrong:
        return _result(wrong["status"], [wrong["finding"]])
    runs = _run_index(_study_rows(captures))
    required = {"inference_soak", "thermal_control", "oom_control", "power_cut_control", "negative_stale_sensor"}
    if set(runs) != required:
        raise MissingEvidence("GX10 synchronized soak, stable firmware, three distinct event controls, and stale-sensor negative required")
    soak = runs["inference_soak"]
    _need_fields(soak, ("workload_id", "boot_id", "firmware", "samples", "journal_records", "thermal_sources"), "inference_soak")
    collector = _thermal_collector_state(context)
    if collector["could_not_run"]:
        return _result("unknown", collector["diagnostics"], collector["could_not_run"])
    samples = _ordered_samples(soak, "inference_soak")
    firmware = soak["firmware"]
    if (not isinstance(firmware, dict) or firmware.get("channel") != "stable" or
            firmware.get("signature_verification_stdout") != "Valid\n" or
            firmware.get("signature_verification_returncode") != 0):
        raise MissingEvidence("stable firmware channel and literal successful signature-verification output are required")
    _validate_sensor_sources(soak["thermal_sources"])
    _bind_thermal_inventory(soak, context)
    journal_rows = _journal_capture_rows(captures)
    event_result = _validate_native_event_classes(runs, journal_rows, context, captures)
    if event_result:
        return event_result
    stale_result = _validate_stale_sensor(runs["negative_stale_sensor"], soak)
    if stale_result:
        return stale_result
    return _result("pass", [f"{len(samples)} synchronized samples; sensor gaps and event classes are explicit, with no root-cause attribution"])


def _thermal_collector_state(context: dict[str, Any]) -> dict[str, Any]:
    """Validate the preserved collector's own completeness and channel records."""
    thermal = context["thermal"]
    count, captured = _collector_header(thermal)
    diagnostics: list[str] = []
    computed = _collector_raw_count(thermal, diagnostics)
    if computed != count:
        raise ValueError(f"thermal_coverage collector could_not_run={count} disagrees with raw channel statuses ({computed})")
    if count > 0:
        diagnostics.insert(0, f"thermal_coverage collector reports could_not_run={count}")
    return {"could_not_run": count, "diagnostics": diagnostics, "captured_at_utc": captured}


def _collector_header(thermal: dict[str, Any]) -> tuple[int, str]:
    count = thermal.get("could_not_run")
    if type(count) is not int or count < 0:
        raise MissingEvidence("thermal_coverage collector could_not_run must be a nonnegative integer")
    if thermal.get("status") != ("observed" if count == 0 else "partial"):
        raise ValueError("thermal_coverage status disagrees with its could_not_run count")
    captured = thermal.get("captured_at_utc")
    if not isinstance(captured, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?[+-]\d\d:\d\d", captured):
        raise MissingEvidence("thermal_coverage collector timestamp must be RFC3339")
    try:
        parsed_time = datetime.fromisoformat(captured)
    except ValueError as exc:
        raise MissingEvidence("thermal_coverage collector timestamp is not a calendar time") from exc
    offset = parsed_time.utcoffset()
    if offset is None or offset.total_seconds() != 0:
        raise MissingEvidence("thermal_coverage collector timestamp must be UTC")
    return count, captured


def _collector_raw_count(thermal: dict[str, Any], diagnostics: list[str]) -> int:
    zone_scan = _collector_scan(thermal.get("thermal_zone_scan"), "thermal zones", diagnostics)
    hwmon_scan = _collector_scan(thermal.get("hwmon_scan"), "hwmon", diagnostics)
    zones, devices, channels = _collector_inventory_rows(thermal, diagnostics)
    _check_scan_rows(zone_scan, len(zones), "thermal zones")
    _check_scan_rows(hwmon_scan, len(devices), "hwmon")
    computed = int(zone_scan["status"] != "ok") + int(hwmon_scan["status"] == "could_not_run")
    computed += sum(int(zone["temperature"].get("status") != "ok") for zone in zones)
    computed += sum(int(channel.get("status") != "ok") for channel in channels)
    computed += sum(_trip_count(zone) for zone in zones)
    if type(thermal.get("no_sensor_detected")) is not bool:
        raise MissingEvidence("thermal_coverage no_sensor_detected flag malformed")
    expected_no_sensor = not zones and not channels
    if thermal["no_sensor_detected"] != expected_no_sensor:
        raise ValueError("thermal_coverage no_sensor_detected disagrees with captured channels")
    if expected_no_sensor:
        diagnostics.append("thermal_coverage collector detected no sensor channels")
        computed += 1
    return computed


def _collector_inventory_rows(thermal: dict[str, Any], diagnostics: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    zones, devices = thermal.get("thermal_zones"), thermal.get("hwmon")
    if not isinstance(zones, list) or not isinstance(devices, list):
        raise MissingEvidence("thermal_coverage channel collections must be arrays")
    for zone in zones:
        if not isinstance(zone, dict):
            raise MissingEvidence("thermal-zone row malformed")
        _collector_channel(zone.get("temperature"), diagnostics, "thermal-zone temperature")
    for device in devices:
        if not isinstance(device, dict):
            raise MissingEvidence("thermal_coverage hwmon device row malformed")
        for name in ("temperature_inputs", "fan_inputs"):
            channels = device.get(name)
            if not isinstance(channels, list):
                raise MissingEvidence(f"thermal_coverage hwmon {name} must be an array")
            for channel in channels:
                _collector_channel(channel, diagnostics, "hwmon channel")
    channels = [channel for device in devices for name in ("temperature_inputs", "fan_inputs")
                for channel in device[name]]
    return zones, devices, channels


def _collector_scan(raw: Any, label: str, diagnostics: list[str]) -> dict[str, Any]:
    if not isinstance(raw, dict) or type(raw.get("count")) is not int or raw["count"] < 0:
        raise MissingEvidence(f"thermal_coverage {label} scan record malformed")
    status = raw.get("status")
    if status == "could_not_run":
        diagnostics.append(f"thermal_coverage {label} scan could not run: {raw.get('error')}")
    elif status not in ("ok", _empty_scan_status(label)):
        raise MissingEvidence(f"thermal_coverage {label} scan status is unknown")
    return raw


def _check_scan_rows(scan: dict[str, Any], rows: int, label: str) -> None:
    if scan["status"] != "could_not_run" and scan["count"] != rows:
        raise ValueError(f"thermal_coverage {label} scan count disagrees with captured rows")
    expected = "ok" if rows else _empty_scan_status(label)
    if scan["status"] != "could_not_run" and scan["status"] != expected:
        raise ValueError(f"thermal_coverage {label} scan status disagrees with captured rows")


def _empty_scan_status(label: str) -> str:
    return "no_thermal_zones" if label == "thermal zones" else "no_hwmon_devices"


def _trip_count(zone: dict[str, Any]) -> int:
    scan, trips = zone.get("trip_point_scan"), zone.get("trip_points")
    if not isinstance(scan, dict) or not isinstance(trips, list):
        raise MissingEvidence("thermal-zone trip-point scan record malformed")
    if scan.get("status") != "could_not_run" and scan.get("count") != len(trips):
        raise ValueError("thermal-zone trip-point scan count disagrees with captured rows")
    count = int(scan.get("status") != "ok")
    for point in trips:
        if not isinstance(point, dict):
            raise MissingEvidence("thermal trip-point row malformed")
        count += int(not isinstance(point.get("type"), dict) or point["type"].get("status") != "ok")
        count += int(not isinstance(point.get("temperature"), dict) or point["temperature"].get("status") != "ok")
    return count


def _collector_channel(channel: Any, diagnostics: list[str], label: str) -> None:
    if not isinstance(channel, dict):
        raise MissingEvidence(f"{label} record malformed")
    status = channel.get("status")
    if status != "ok":
        diagnostics.append(f"{label} {channel.get('path', '<unknown path>')} status={status!r}")
        return
    read = channel.get("read")
    if (not isinstance(channel.get("path"), str) or not isinstance(read, dict) or
            read.get("status") != "ok" or not isinstance(read.get("value"), str) or
            type(channel.get("value_raw")) is not int or
            type(channel.get("value")) not in (int, float) or not math.isfinite(channel["value"]) or
            not isinstance(channel.get("unit"), str)):
        raise MissingEvidence(f"{label} raw read/value/unit fields incomplete")
    try:
        raw_numeric = int(read["value"])
    except ValueError as exc:
        raise MissingEvidence(f"{label} raw read value is not an integer") from exc
    divisor = 1 if channel["unit"] == "rpm" else 1000
    if channel["value_raw"] != raw_numeric or channel["value"] != raw_numeric / divisor:
        raise ValueError(f"{label} parsed numeric fields disagree with raw read bytes")


def _bind_thermal_inventory(soak: dict[str, Any], context: dict[str, Any]) -> None:
    thermal = context["thermal"]
    sources = soak["thermal_sources"]
    digest = context["identity"]["thermal_capture_sha256"]
    captured = thermal["captured_at_utc"]
    if soak.get("thermal_capture_sha256") != digest or soak.get("collector_captured_at_utc") != captured:
        raise MissingEvidence("soak must bind the exact thermal collector bytes and capture timestamp")
    channels = _collector_channel_index(thermal)
    for source in sources:
        _bind_thermal_source(source, channels, digest, captured)


def _collector_channel_index(thermal: dict[str, Any]) -> dict[str, dict[str, Any]]:
    channels: dict[str, dict[str, Any]] = {}
    for zone in thermal.get("thermal_zones", []):
        channel = zone.get("temperature") if isinstance(zone, dict) else None
        if isinstance(channel, dict) and isinstance(channel.get("path"), str):
            channels[channel["path"]] = channel
    for device in thermal.get("hwmon", []):
        if not isinstance(device, dict):
            continue
        for channel in (*device.get("temperature_inputs", []), *device.get("fan_inputs", [])):
            if isinstance(channel, dict) and isinstance(channel.get("path"), str):
                channels[channel["path"]] = channel
    return channels


def _bind_thermal_source(source: dict[str, Any], channels: dict[str, dict[str, Any]],
                         digest: str, captured: str) -> None:
    if source.get("collector_sha256") != digest or source.get("collector_captured_at_utc") != captured:
        raise MissingEvidence("each per-source status must bind collector bytes and timestamp")
    path = source.get("source")
    native = channels.get(path) if isinstance(path, str) else None
    if source.get("status") == "observed":
        if native is None or native.get("status") != "ok":
            raise MissingEvidence(f"observed source {path!r} has no readable matching native channel")
        if (source.get("unit") != native.get("unit") or source.get("value_raw") != native.get("value_raw") or
                source.get("value") != native.get("value")):
            raise ValueError(f"per-source reading disagrees with the raw collector channel: {path}")
    elif native is not None and native.get("status") == "ok":
        raise ValueError(f"per-source status contradicts readable collector channel: {path}")


def _validate_sensor_sources(sources: Any) -> None:
    if not isinstance(sources, list) or not sources:
        raise MissingEvidence("per-source thermal/sensor coverage matrix required")
    seen: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            raise MissingEvidence("thermal source rows must be objects")
        _need_fields(source, ("source", "status", "unit", "freshness_ns"), "thermal source")
        if not isinstance(source["source"], str) or source["source"] in seen:
            raise ValueError("thermal sensor sources must be unique and named")
        seen.add(source["source"])
        if source["status"] not in ("observed", "absent", "unreadable"):
            raise MissingEvidence("sensor capability must distinguish observed, absent and unreadable channels")
        if source["status"] == "observed" and (type(source["freshness_ns"]) is not int or source["freshness_ns"] < 0):
            raise MissingEvidence("observed thermal channel needs raw freshness age")


def _validate_event_classes(runs: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    controls = ("thermal_control", "oom_control", "power_cut_control")
    signatures = [runs[name].get("journal_text") for name in controls]
    if any(not isinstance(text, str) or not text.strip() for text in signatures):
        raise MissingEvidence("literal journal text from each independent event control is required")
    thermal_text, oom_text, power_text = signatures
    assert isinstance(thermal_text, str) and isinstance(oom_text, str) and isinstance(power_text, str)
    thermal = bool(re.search(r"thermal.*(?:throttl|slowdown)|(?:throttl|slowdown).*thermal", thermal_text, re.I))
    oom = bool(re.search(r"out of memory:.*killed process", oom_text, re.I | re.S))
    power = bool(re.search(r"power.*(?:cut|loss)|(?:cut|loss).*power", power_text, re.I))
    if not thermal or not oom or not power:
        return _result("fail", ["literal event records do not distinguish thermal throttle, OOM and abrupt power loss"])
    if not isinstance(runs["power_cut_control"].get("independent_capture_command"), list):
        raise MissingEvidence("power loss must have a separate independent instrument command receipt")
    return None


def _journal_capture_rows(captures: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    capture = captures.get("journal_events")
    if not isinstance(capture, dict):
        raise MissingEvidence("bounded raw journal_events capture is required")
    command = capture.get("command")
    if (not isinstance(command, list) or len(command) < 5 or Path(str(command[0])).name != "journalctl" or
            "--output=json" not in command or "--no-pager" not in command or
            "--since" not in command or "--until" not in command):
        raise MissingEvidence("journal capture must preserve a literal bounded journalctl JSON argv")
    try:
        rows = [_strict_json(line) for line in capture["text"].splitlines() if line.strip()]
    except (KeyError, json.JSONDecodeError, RecursionError) as exc:
        raise MissingEvidence("raw journal capture must be valid JSON Lines") from exc
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise MissingEvidence("raw journal JSON Lines are absent or contain non-object records")
    for row in rows:
        stamp = row.get("__REALTIME_TIMESTAMP")
        boot = row.get("_BOOT_ID")
        message = row.get("MESSAGE")
        if (not isinstance(stamp, str) or not stamp.isdecimal() or not isinstance(boot, str) or not boot.strip() or
                not isinstance(message, str)):
            raise MissingEvidence("journal record needs decimal __REALTIME_TIMESTAMP, _BOOT_ID, and string MESSAGE")
        if _journal_time(row) is None:
            raise MissingEvidence("journal __REALTIME_TIMESTAMP is outside the supported epoch range")
    return rows


def _validate_native_event_classes(runs: dict[str, dict[str, Any]], journal: list[dict[str, Any]],
                                   context: dict[str, Any],
                                   captures: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    host_digest = context["identity"]["host_capture_sha256"]
    journal_capture = captures["journal_events"]
    capture_start, capture_end = _journal_command_window(journal_capture["command"])
    windows: dict[str, list[dict[str, Any]]] = {}
    for name in ("inference_soak", "thermal_control", "oom_control", "power_cut_control"):
        run = runs[name]
        subject_digest = run.get("subject_host_capture_sha256")
        if not isinstance(subject_digest, str) or not subject_digest:
            raise MissingEvidence(f"{name}: run must bind the exact host identity capture")
        if subject_digest != host_digest:
            raise ValueError(f"{name}: run is bound to a different host identity capture")
        run_start, run_end = _parse_utc_interval(run.get("started_at_utc"), run.get("ended_at_utc"), name)
        if run_start < capture_start or run_end > capture_end:
            raise MissingEvidence(f"{name}: journal command capture does not span the declared run window")
        windows[name] = _journal_rows_in_run_window(journal, run, name)
        if not windows[name]:
            raise MissingEvidence(f"{name}: no journal records from the declared boot/window")
    _validate_soak_sample_window(runs["inference_soak"])
    thermal_text = "\n".join(row["MESSAGE"] for row in windows["thermal_control"])
    oom_text = "\n".join(row["MESSAGE"] for row in windows["oom_control"])
    thermal_match = re.search(r"thermal.*(?:throttl|slowdown)|(?:throttl|slowdown).*thermal", thermal_text, re.I)
    oom_match = re.search(r"out of memory:.*killed process", oom_text, re.I | re.S)
    if thermal_match is None or oom_match is None:
        return _result("fail", ["raw journal records do not show the thermal and OOM control events in their declared windows"])
    power = _power_loss_instrument(captures, runs["power_cut_control"], host_digest)
    return power


def _journal_command_window(command: Any) -> tuple[datetime, datetime]:
    if not isinstance(command, list):
        raise MissingEvidence("journal command argv is malformed")
    values: dict[str, str] = {}
    index = 0
    while index < len(command):
        token = command[index]
        if token in ("--since", "--until"):
            if token in values or index + 1 >= len(command) or not isinstance(command[index + 1], str):
                raise MissingEvidence("journal command needs unique --since and --until timestamps")
            values[token] = command[index + 1]
            index += 2
            continue
        if isinstance(token, str) and (token.startswith("--since=") or token.startswith("--until=")):
            name, value = token.split("=", 1)
            if name in values or not value:
                raise MissingEvidence("journal command has duplicate or empty time bounds")
            values[name] = value
        index += 1
    if set(values) != {"--since", "--until"}:
        raise MissingEvidence("journal command must preserve both --since and --until time bounds")
    return _parse_utc_interval(values["--since"], values["--until"], "journal command")


def _journal_rows_in_run_window(journal: list[dict[str, Any]], run: dict[str, Any], label: str) -> list[dict[str, Any]]:
    _need_fields(run, ("boot_id", "started_at_utc", "ended_at_utc"), label)
    if not isinstance(run["boot_id"], str) or not run["boot_id"].strip():
        raise MissingEvidence(f"{label}: boot identity required")
    start, end = _parse_utc_interval(run["started_at_utc"], run["ended_at_utc"], label)
    matches: list[dict[str, Any]] = []
    other_boot = False
    for row in journal:
        stamp = _journal_time(row)
        if stamp is None:
            raise MissingEvidence(f"{label}: journal timestamp could not be parsed")
        observed = datetime.fromisoformat(stamp)
        if start <= observed <= end:
            if row["_BOOT_ID"] == run["boot_id"]:
                matches.append(row)
            else:
                other_boot = True
    if not matches and other_boot:
        raise ValueError(f"{label}: journal rows in the declared window belong to a different boot")
    return matches


def _parse_utc_interval(start_raw: Any, end_raw: Any, label: str) -> tuple[datetime, datetime]:
    if not isinstance(start_raw, str) or not isinstance(end_raw, str):
        raise MissingEvidence(f"{label}: explicit UTC event window timestamps required")
    try:
        start = datetime.fromisoformat(start_raw.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MissingEvidence(f"{label}: event window timestamp is malformed") from exc
    if (start.tzinfo is None or end.tzinfo is None or start.utcoffset() != timezone.utc.utcoffset(start) or
            end.utcoffset() != timezone.utc.utcoffset(end) or end <= start):
        raise MissingEvidence(f"{label}: event window must be ordered UTC timestamps")
    return start, end


def _validate_soak_sample_window(soak: dict[str, Any]) -> None:
    start, end = _parse_utc_interval(soak.get("started_at_utc"), soak.get("ended_at_utc"), "inference_soak")
    samples = soak["samples"]
    utc_samples: list[datetime] = []
    for sample in samples:
        if sample.get("boot_id") != soak["boot_id"]:
            raise ValueError("inference_soak sample boot id differs from its declared run")
        try:
            observed = datetime.fromisoformat(sample["timestamp_utc"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise MissingEvidence("inference_soak samples need literal UTC wall-clock timestamps") from exc
        if observed.tzinfo is None or observed.utcoffset() != timezone.utc.utcoffset(observed):
            raise MissingEvidence("inference_soak sample wall-clock timestamp must be UTC")
        utc_samples.append(observed)
    if any(a >= b for a, b in zip(utc_samples, utc_samples[1:])):
        raise ValueError("inference_soak UTC sample times are not strictly increasing")
    if any(sample < start or sample > end for sample in utc_samples):
        raise ValueError("inference_soak sample falls outside the declared journal window")


def _parse_utc_point(raw: Any, label: str) -> datetime:
    if not isinstance(raw, str):
        raise MissingEvidence(f"{label}: UTC timestamp required")
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MissingEvidence(f"{label}: timestamp is malformed") from exc
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise MissingEvidence(f"{label}: timestamp must be UTC")
    return value


def _power_loss_instrument(captures: dict[str, dict[str, Any]] | None, run: dict[str, Any],
                           host_digest: str) -> dict[str, Any] | None:
    if captures is None or "power_loss_instrument" not in captures:
        raise MissingEvidence("power-loss event requires a separate captured external recorder; journal absence is not evidence")
    capture = captures["power_loss_instrument"]
    command = capture.get("command")
    if not isinstance(command, list) or not command or Path(command[0]).name == "journalctl":
        raise MissingEvidence("power-loss recorder must be a separate literal non-journal command capture")
    try:
        record = _strict_json(capture["text"])
    except (KeyError, json.JSONDecodeError, RecursionError) as exc:
        raise MissingEvidence("external power-loss recorder must preserve one JSON event record") from exc
    if not isinstance(record, dict):
        raise MissingEvidence("external power-loss recorder output must be a JSON object")
    _need_fields(record, ("event_kind", "observed_at_utc", "run_boot_id", "subject_host_capture_sha256", "instrument_id"),
                 "external power-loss recorder")
    if record["event_kind"] != "power_loss" or record["run_boot_id"] != run.get("boot_id"):
        return _result("fail", ["external power-loss recorder event kind or boot binding contradicts the run"])
    if record["subject_host_capture_sha256"] != host_digest:
        return _result("fail", ["external power-loss recorder is bound to a different host identity capture"])
    if not isinstance(record["instrument_id"], str) or not record["instrument_id"].strip():
        raise MissingEvidence("external power-loss recorder identity is absent")
    start, end = _parse_utc_interval(run.get("started_at_utc"), run.get("ended_at_utc"), "power_cut_control")
    observed = _parse_utc_point(record["observed_at_utc"], "external power-loss recorder")
    if not start <= observed <= end:
        return _result("fail", ["external power-loss observation falls outside the declared control window"])
    return None


def _validate_stale_sensor(stale: dict[str, Any], soak: dict[str, Any]) -> dict[str, Any] | None:
    fields = ("sample_time_ns", "observed_at_ns", "max_freshness_ns", "sensor_value_raw")
    _need_fields(stale, fields, "negative_stale_sensor")
    times = ("sample_time_ns", "observed_at_ns", "max_freshness_ns")
    if any(type(stale[key]) is not int or stale[key] < 0 for key in times):
        raise MissingEvidence("stale-sensor test needs raw integer sample/observation times and policy age")
    if not isinstance(stale["sensor_value_raw"], str) or not stale["sensor_value_raw"].strip():
        raise MissingEvidence("stale-sensor negative requires the old raw sensor value")
    if stale["observed_at_ns"] - stale["sample_time_ns"] <= stale["max_freshness_ns"]:
        return _result("fail", ["stale sensor negative actually falls within its recorded freshness limit"])
    if soak["samples"][-1]["timestamp_ns"] < stale["observed_at_ns"]:
        raise MissingEvidence("soak and stale-sensor capture windows are not time-correlated")
    return None


def _usb_raid(document: dict[str, Any], captures: dict[str, dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    rows = _run_index(_study_rows(captures))
    required = {"healthy_boot_a", "healthy_boot_b", "slow_link", "missing_speed", "negative_identity_swap", "rollback"}
    if set(rows) != required:
        raise MissingEvidence("two cold boots, healthy/slow/missing-speed/identity-swap controls and rollback capture required")
    floor = document.get("operator_declared_floor_mbps")
    if type(floor) is not int or floor < 5000 or document.get("floor_source") != "operator_or_OEM_recorded":
        raise MissingEvidence("USB link-speed floor must be explicitly recorded from operator/OEM policy (at least 5000 Mbps for this card)")
    for name in ("healthy_boot_a", "healthy_boot_b", "slow_link", "missing_speed", "negative_identity_swap"):
        failure = _usb_case_result(name, rows[name], floor, document)
        if failure:
            return failure
    boots = {rows[name]["boot_id"] for name in ("healthy_boot_a", "healthy_boot_b")}
    if len(boots) != 2:
        raise MissingEvidence("healthy negotiation must be observed across two distinct cold boots")
    if not _rollback_complete({"rollback": rows["rollback"]}, ("rollback",)):
        raise MissingEvidence("USB quirk/configuration rollback lacks identical raw before/after hashes")
    return _result("pass", ["per-member speed and stable identity recomputed; below-floor and missing-speed controls stayed unassembled/unmounted"])


def _usb_case_result(name: str, run: dict[str, Any], floor: int, document: dict[str, Any]) -> dict[str, Any] | None:
    _need_fields(run, ("boot_id", "cold_boot", "array_uuid", "members"), name)
    if run["cold_boot"] is not True or not isinstance(run["boot_id"], str) or not run["boot_id"]:
        raise MissingEvidence(f"{name}: independent cold-boot identity required")
    members = run["members"]
    if not isinstance(members, list) or not members:
        raise MissingEvidence(f"{name}: raw member identity/speed observations required")
    speeds, pairs, duplicate = _usb_member_observations(members, name)
    if duplicate:
        return _result("fail", [f"{name}: duplicate/misidentified RAID member UUID"])
    mdadm_rc, mdadm_out, _ = _native_result(run, "mdadm_detail")
    findmnt_rc, findmnt_out, _ = _native_result(run, "findmnt")
    mount_rows = _findmnt_targets(findmnt_out) if findmnt_rc == 0 else []
    assembled = mdadm_rc == 0 and re.search(rf"(?m)^\s*Array UUID\s*:\s*{re.escape(str(run['array_uuid']))}\s*$", mdadm_out) is not None
    mounted = any(target.get("target") == run.get("mountpoint") and target.get("uuid") == run.get("array_uuid") for target in mount_rows)
    facts = {"speeds": speeds, "pairs": pairs, "assembled": assembled, "mounted": mounted}
    return _usb_case_policy(name, facts, floor, document)


def _usb_member_observations(members: Any, name: str) -> tuple[list[int | None], set[tuple[str, str]], bool]:
    if any(not isinstance(member, dict) for member in members):
        raise MissingEvidence(f"{name}: member rows must be objects")
    identities: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    speeds: list[int | None] = []
    for member in members:
        _need_fields(member, ("uuid", "serial", "sysfs_speed_raw"), name)
        uuid, serial = member["uuid"], member["serial"]
        if not isinstance(uuid, str) or not uuid.strip() or not isinstance(serial, str) or not serial.strip():
            raise MissingEvidence(f"{name}: stable UUID and serial required per array member")
        if uuid in identities:
            return speeds, pairs, True
        identities.add(uuid)
        pairs.add((uuid, serial))
        raw_speed = member["sysfs_speed_raw"]
        if raw_speed is None:
            speeds.append(None)
        elif isinstance(raw_speed, str) and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", raw_speed):
            speed = float(raw_speed)
            if not speed.is_integer():
                raise MissingEvidence(f"{name}: USB link speed is not an integer Mbps value")
            speeds.append(int(speed))
        else:
            raise MissingEvidence(f"{name}: malformed raw sysfs USB speed")
    return speeds, pairs, False


def _usb_case_policy(name: str, facts: dict[str, Any], floor: int,
                     document: dict[str, Any]) -> dict[str, Any] | None:
    speeds = facts["speeds"]
    pairs = facts["pairs"]
    assembled = facts["assembled"]
    mounted = facts["mounted"]
    if name.startswith("healthy"):
        healthy = all(speed is not None and speed >= floor for speed in speeds)
        if not healthy or not assembled or not mounted:
            return _result("fail", [f"{name}: healthy negotiated array failed admission or verified mount"])
        return None
    if name == "slow_link":
        if all(speed is None or speed >= floor for speed in speeds):
            return _result("fail", ["slow-link control contains no measured below-floor member"])
        return _result("fail", ["array was admitted despite a measured link below its declared floor"]) if assembled or mounted else None
    if name == "missing_speed":
        return _result("fail", ["missing speed did not fail closed before assemble/mount"]) if not any(speed is None for speed in speeds) or assembled or mounted else None
    expected = document.get("expected_members")
    if not isinstance(expected, list) or not expected or any(not isinstance(item, dict) for item in expected):
        raise MissingEvidence("expected per-member stable UUID/serial policy is required")
    expected_pairs = {(item.get("uuid"), item.get("serial")) for item in expected}
    if pairs == expected_pairs:
        return _result("fail", ["identity-swap negative did not alter any member UUID/serial pair"])
    return _result("fail", ["array was assembled or mounted after the stable-identity mismatch"]) if assembled or mounted else None


def _backup_mount(document: dict[str, Any], captures: dict[str, dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    rows = _run_index(_study_rows(captures))
    required = {"mounted_after_boot", "missing_device", "wrong_uuid", "mountpoint_only"}
    if set(rows) != required:
        raise MissingEvidence("post-boot mounted identity and absent/wrong-UUID/existing-directory controls required")
    for name, row in rows.items():
        failure = _backup_case(name, row)
        if failure:
            return failure
    return _result("pass", ["post-boot UUID/source/mountpoint and read-back digest matched; absent/mismatch controls made zero writes"])


def _backup_case(name: str, row: dict[str, Any]) -> dict[str, Any] | None:
    _need_fields(row, ("mountpoint", "expected_source", "expected_uuid", "backup_sha256_before",
                       "backup_sha256_after", "write_attempts"), name)
    if not _backup_fields_valid(row):
        raise MissingEvidence(f"{name}: explicit mount identity, raw backup digest and write audit required")
    findmnt_rc, findmnt_out, _ = _native_result(row, "findmnt")
    if findmnt_rc != 0:
        raise MissingEvidence("findmnt native capture failed; destination absence cannot be inferred")
    observed_rows = _findmnt_targets(findmnt_out)
    mounted = next((item for item in observed_rows if item.get("target") == row["mountpoint"]), None)
    if name == "mounted_after_boot":
        if not _backup_postboot_matches(row, mounted):
            return _result("fail", ["post-boot backup destination or read-back identity/digest did not match expected device"])
        if row["write_attempts"] < 0:
            raise ValueError("write audit count cannot be negative")
        return None
    if not _backup_write_safe(row):
        return _result("fail", [f"{name}: write was attempted or backup data changed under a blocked mount"])
    if name == "wrong_uuid":
        return _backup_wrong_uuid(row, mounted)
    elif mounted is not None:
        return _result("fail", [f"{name}: absent or unmounted destination was treated as the expected backup filesystem"])
    return None


def _backup_fields_valid(row: dict[str, Any]) -> bool:
    return (all(isinstance(row[key], str) and row[key].strip() for key in
                ("mountpoint", "expected_source", "expected_uuid")) and
            re.fullmatch(r"[0-9a-f]{64}", row["backup_sha256_before"]) is not None and
            re.fullmatch(r"[0-9a-f]{64}", row["backup_sha256_after"]) is not None and
            type(row["write_attempts"]) is int)


def _backup_postboot_matches(row: dict[str, Any], mounted: dict[str, Any] | None) -> bool:
    return (mounted is not None and mounted.get("source") == row["expected_source"] and
            mounted.get("uuid") == row["expected_uuid"] and isinstance(row.get("boot_id"), str) and
            bool(row["boot_id"].strip()) and row.get("backup_read_sha256") == row["backup_sha256_before"])


def _backup_write_safe(row: dict[str, Any]) -> bool:
    return row["write_attempts"] == 0 and row["backup_sha256_after"] == row["backup_sha256_before"]


def _backup_wrong_uuid(row: dict[str, Any], mounted: dict[str, Any] | None) -> dict[str, Any] | None:
    if mounted is None:
        raise MissingEvidence("wrong-UUID control must show same target with an independently observed different UUID")
    if mounted.get("uuid") == row["expected_uuid"]:
        return _result("fail", ["wrong-UUID control unexpectedly matched expected identity"])
    return None


def _display_carveout(document: dict[str, Any], captures: dict[str, dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    wrong = _subject(context, vendor="GIGABYTE", product="AI TOP ATOM")
    if wrong:
        return _result(wrong["status"], [wrong["finding"]])
    rows = _run_index(_study_rows(captures))
    required = {"baseline_6k_failure", "candidate_6k", "candidate_4k", "cache_pressure", "rollback"}
    if set(rows) != required:
        raise MissingEvidence("reproduced 6K failure, candidate 6K/4K/cache runs, unsupported-OEM negative and rollback required")
    baseline = rows["baseline_6k_failure"]
    _need_fields(baseline, ("resolution", "free_memory_bytes", "scanout_log"), "baseline_6k_failure")
    if (baseline.get("resolution") != "6K" or type(baseline.get("free_memory_bytes")) is not int or
            baseline["free_memory_bytes"] <= 0 or re.search(r"NV_ERR_NO_MEMORY", baseline["scanout_log"]) is None):
        return _result("fail", ["baseline does not capture the reported scanoutcarveout failure with free UMA evidence"])
    for name in ("candidate_6k", "candidate_4k", "cache_pressure"):
        failure = _display_candidate(name, rows[name], context)
        if failure:
            return failure
    if baseline.get("driver_version") != rows["candidate_6k"].get("driver_version"):
        raise MissingEvidence("before/after candidate driver version comparison is incomplete")
    if not _rollback_complete({"rollback": rows["rollback"]}, ("rollback",)):
        raise MissingEvidence("display carveout rollback lacks byte-identical original/effective value captures")
    return _result("pass", ["candidate 6K/4K/cache evidence preserves Sway/SSH and is bounded to the captured OEM"])


def _display_candidate(name: str, run: dict[str, Any], context: dict[str, Any]) -> dict[str, Any] | None:
    fields = ("stack_sha256", "driver_version", "reserved_bytes_before", "reserved_bytes_after",
              "native_commands")
    _need_fields(run, fields, name)
    if run["stack_sha256"] != context["identity"]["thermal_capture_sha256"]:
        raise MissingEvidence(f"{name}: effective carveout capture not bound to exact OEM stack")
    if not isinstance(run["driver_version"], str) or not run["driver_version"].strip():
        raise MissingEvidence(f"{name}: exact display driver version required")
    for key in ("reserved_bytes_before", "reserved_bytes_after"):
        if type(run[key]) is not int or run[key] < 0:
            raise MissingEvidence(f"{name}: raw integer {key} required")
    parameter_rc, parameter_out, _ = _native_result(run, "driver_parameter")
    sway_rc, sway_out, _ = _native_result(run, "sway")
    ssh_rc, ssh_out, _ = _native_result(run, "ssh")
    log_rc, log_out, _ = _native_result(run, "scanout_log")
    events_rc, events_out, _ = _native_result(run, "window_events")
    parameter_match = re.search(r"(?m)^AdjustableDisplayReservedMemory=([0-9]+)\n?$", parameter_out)
    if parameter_rc != 0 or parameter_match is None:
        raise MissingEvidence("AdjustableDisplayReservedMemory support/effective value is not captured as a native output")
    if type(run["reserved_bytes_after"]) is not int or int(parameter_match.group(1)) != run["reserved_bytes_after"]:
        raise MissingEvidence("effective driver parameter does not match the measured after value")
    if run["reserved_bytes_before"] == run["reserved_bytes_after"]:
        raise MissingEvidence("candidate has no before/after carveout change to evaluate")
    if sway_rc != 0 or sway_out.strip() != "active" or ssh_rc != 0 or ssh_out.strip() != "connected":
        return _result("fail", [f"{name}: Sway or SSH was lost during the candidate canary"])
    opened = set(re.findall(r"(?m)^open ([^\s]+)$", events_out))
    closed = set(re.findall(r"(?m)^close ([^\s]+)$", events_out))
    if log_rc != 0 or re.search(r"NV_ERR_NO_MEMORY", log_out) is not None or events_rc != 0 or not opened.intersection(closed):
        return _result("fail", [f"{name}: candidate scanout/open-close check failed"])
    return None


def _gx10_cable(document: dict[str, Any], captures: dict[str, dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    wrong = _subject(context, vendor="ASUS", product="GX10")
    if wrong:
        return _result(wrong["status"], [wrong["finding"]])
    rows = _run_index(_study_rows(captures))
    required = {"original_tuple", "candidate_tuple", "cold_reboot", "warm_reboot", "rollback"}
    if set(rows) != required:
        raise MissingEvidence("original/candidate SoC+EC tuple, cold/warm reboots and rollback required")
    original, candidate = rows["original_tuple"], rows["candidate_tuple"]
    for name, row in (("original", original), ("candidate", candidate)):
        _validate_cable_tuple(name, row)
    _validate_cable_candidate(original, candidate)
    for name in ("cold_reboot", "warm_reboot"):
        failure = _validate_cable_boot(name, rows[name], candidate)
        if failure:
            return failure
    if rows["cold_reboot"]["boot_id"] == rows["warm_reboot"]["boot_id"]:
        raise MissingEvidence("cold and warm boot evidence must identify distinct boots")
    if not _rollback_complete({"rollback": rows["rollback"]}, ("rollback",)):
        raise MissingEvidence("OEM cable-recovery rollback lacks byte-identical original firmware inventory")
    return _result("pass", ["candidate tuple has observed functional traffic after separate cold/warm boots; no firmware action performed by verifier"])


def _validate_cable_candidate(original: dict[str, Any], candidate: dict[str, Any]) -> None:
    if original["soc_version"] == candidate["soc_version"] and original["ec_version"] == candidate["ec_version"]:
        raise MissingEvidence("candidate tuple does not differ from original SoC/EC firmware")
    reference = candidate.get("vendor_approval_ref")
    if not isinstance(reference, str) or not reference.strip():
        raise MissingEvidence("testing-channel candidate requires vendor procedure/approval reference")


def _validate_cable_tuple(name: str, row: dict[str, Any]) -> None:
    fields = ("soc_version", "ec_version", "channel", "bundle_sha256", "hotplug_state_raw")
    _need_fields(row, fields, name)
    if (not isinstance(row["soc_version"], str) or not isinstance(row["ec_version"], str) or
            not row["soc_version"].strip() or not row["ec_version"].strip() or
            row["channel"] != "LVFS testing" or not isinstance(row["hotplug_state_raw"], str) or
            re.search(r"(?m)^hotplug_enabled=1\s*$", row["hotplug_state_raw"]) is None or
            not re.fullmatch(r"[0-9a-f]{64}", row["bundle_sha256"])):
        raise MissingEvidence(f"{name} tuple lacks exact channel, version, bundle digest, or native hotplug state")


def _validate_cable_boot(name: str, run: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any] | None:
    fields = ("boot_id", "soc_version", "ec_version", "native_commands")
    _need_fields(run, fields, name)
    if run["soc_version"] != candidate["soc_version"] or run["ec_version"] != candidate["ec_version"]:
        return _result("fail", [f"{name}: active SoC/EC tuple differs from the reviewed candidate"])
    if not isinstance(run["boot_id"], str) or not run["boot_id"].strip():
        raise MissingEvidence(f"{name}: boot identity missing")
    pci_rc, pci_out, _ = _native_result(run, "pci_inventory")
    module_rc, module_out, _ = _native_result(run, "module_inventory")
    carrier_rc, carrier_out, _ = _native_result(run, "carrier")
    eeprom_rc, eeprom_out, eeprom_err = _native_result(run, "eeprom")
    link_rc, link_out, _ = _native_result(run, "link")
    if pci_rc != 0 or not pci_out.strip() or module_rc != 0 or not re.search(r"(?m)^mlx5_core\s", module_out):
        return _result("fail", [f"{name}: expected PCI function or kernel module is absent"])
    if carrier_rc != 0 or carrier_out.strip() != "1" or eeprom_rc != 0 or not eeprom_out.strip() or eeprom_err:
        return _result("fail", [f"{name}: carrier is down or EEPROM read failed"])
    if link_rc != 0 or re.search(r"(?mi)^\s*Speed:\s*[1-9][0-9]*\s*Mb/s\s*$", link_out) is None or re.search(r"(?mi)^\s*Link detected:\s*yes\s*$", link_out) is None:
        return _result("fail", [f"{name}: negotiated link is absent"])
    for direction in ("tx", "rx"):
        before_rc, before_out, _ = _native_result(run, f"{direction}_before")
        after_rc, after_out, _ = _native_result(run, f"{direction}_after")
        if before_rc != 0 or after_rc != 0 or not before_out.strip().isdigit() or not after_out.strip().isdigit():
            raise MissingEvidence(f"{name}: raw {direction} byte counters before/after are required")
        if int(after_out.strip()) <= int(before_out.strip()):
            return _result("fail", [f"{name}: {direction.upper()} traffic counters did not increase"])
    return None


def _dew_point(temperature_c: float, humidity_percent: float | None) -> float:
    if humidity_percent is None or type(humidity_percent) not in (int, float):
        raise ValueError("relative humidity must be a finite number")
    humidity = float(humidity_percent)
    if not math.isfinite(humidity) or not 0 < humidity <= 100:
        raise ValueError("relative humidity must be within (0, 100]")
    a, b = 17.62, 243.12
    gamma = math.log(humidity / 100.0) + a * temperature_c / (b + temperature_c)
    return b * gamma / (a - gamma)


def _subambient(document: dict[str, Any], captures: dict[str, dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    wrong = _subject(context, product="GB10")
    if wrong:
        return _result(wrong["status"], [wrong["finding"]])
    rows = _run_index(_study_rows(captures))
    if set(rows) != {"baseline", "subambient_canary", "negative_unknown_humidity", "rollback"}:
        raise MissingEvidence("matched baseline, subambient canary, unknown-humidity negative and rollback required")
    identities: set[str] = set()
    means: dict[str, dict[str, float]] = {}
    for name in ("baseline", "subambient_canary"):
        run_means, workload, failure = _subambient_run(name, rows[name], context)
        if failure:
            return failure
        assert run_means is not None and workload is not None
        means[name] = run_means
        identities.add(workload)
    if len(identities) != 1:
        raise MissingEvidence("baseline and subambient canary workload hashes differ")
    negative_failure = _subambient_negative(rows["negative_unknown_humidity"])
    if negative_failure:
        return negative_failure
    if not _rollback_complete({"rollback": rows["rollback"]}, ("rollback",)):
        raise MissingEvidence("subambient setup/parameter rollback lacks byte-identical before/after measurements")
    treated, baseline = means["subambient_canary"], means["baseline"]
    if treated["uma_used_bytes"] > baseline["uma_used_bytes"] or treated["throughput"] < baseline["throughput"]:
        return _result("fail", ["canary worsens UMA pressure or useful throughput against its matched baseline"])
    return _result("pass", ["matched canary has measured dew-point margin, clear airflow and preserved UMA/desktop/SSH; no cross-OEM inference"])


def _subambient_negative(negative: dict[str, Any]) -> dict[str, Any] | None:
    _need_fields(negative, ("ambient_c", "humidity_raw"), "negative_unknown_humidity")
    if negative["humidity_raw"] is not None:
        return _result("fail", ["unknown-humidity negative control contains an invented/fallback humidity value"])
    try:
        _dew_point(_finite_number(negative["ambient_c"], "negative control ambient"), None)
    except (ValueError, TypeError):
        return None
    return _result("fail", ["dew-point calculation accepted unknown humidity"])


def _subambient_run(name: str, run: dict[str, Any], context: dict[str, Any]) -> tuple[dict[str, float] | None, str | None, dict[str, Any] | None]:
    fields = ("workload_sha256", "stack_sha256", "boot_id", "humidity_samples", "ambient_samples_c",
              "surface_min_samples_c", "airflow_velocity_mps", "duct_clearance_raw", "samples")
    _need_fields(run, fields, name)
    if run["stack_sha256"] != context["identity"]["thermal_capture_sha256"]:
        raise MissingEvidence(f"{name}: stack identity mismatch for same-subject A/B")
    workload = run["workload_sha256"]
    if not isinstance(workload, str) or not re.fullmatch(r"[0-9a-f]{64}", workload):
        raise MissingEvidence(f"{name}: exact workload hash required")
    samples = _ordered_samples(run, name)
    humidity, ambient, surface = run["humidity_samples"], run["ambient_samples_c"], run["surface_min_samples_c"]
    flow, clearance = run["airflow_velocity_mps"], run["duct_clearance_raw"]
    arrays = (humidity, ambient, surface, flow)
    if not all(isinstance(values, list) and len(values) == len(samples) for values in arrays):
        raise MissingEvidence(f"{name}: time-aligned humidity, ambient, surface and airflow measurements required")
    if not isinstance(clearance, str) or not clearance.strip():
        raise MissingEvidence(f"{name}: duct clearance inspection record required")
    keys = ("gpu_c", "cpu_c", "soc_c", "uma_used_bytes", "throughput")
    temperatures = {key: [] for key in keys}
    for index, sample in enumerate(samples):
        for key in keys:
            temperatures[key].append(_finite_number(sample.get(key), f"{name}.{key}"))
        conditions = (ambient[index], humidity[index], surface[index], flow[index])
        failure = _subambient_sample_safety(name, sample, conditions)
        if failure:
            return None, None, failure
    means = {key: sum(values) / len(values) for key, values in temperatures.items()}
    return means, workload, None


def _subambient_sample_safety(name: str, sample: dict[str, Any], conditions: tuple[Any, Any, Any, Any]) -> dict[str, Any] | None:
    ambient, humidity, surface, airflow = conditions
    dew = _dew_point(_finite_number(ambient, f"{name}.ambient"), _finite_number(humidity, f"{name}.humidity"))
    surface_c = _finite_number(surface, f"{name}.surface")
    uncertainty = _finite_number(sample.get("sensor_uncertainty_c"), f"{name}.sensor uncertainty")
    velocity = _finite_number(airflow, f"{name}.airflow velocity")
    if uncertainty < 0:
        raise ValueError("sensor uncertainty cannot be negative")
    if velocity <= 0:
        return _result("fail", [f"{name}: measured airflow stopped during observation"])
    if surface_c <= dew + uncertainty:
        return _result("fail", [f"{name}: measured coldest surface reaches calculated dew point within sensor uncertainty"])
    journal = sample.get("journal_text")
    if not isinstance(journal, str):
        raise MissingEvidence(f"{name}: literal kernel journal window is required")
    if re.search(r"Out of memory:.*Killed process", journal, re.I | re.S):
        return _result("fail", [f"{name}: kernel journal contains an OOM kill during the canary"])
    sway_rc, sway_out, _ = _native_result(sample, "sway")
    ssh_rc, ssh_out, _ = _native_result(sample, "ssh")
    if sway_rc != 0 or sway_out.strip() != "active" or ssh_rc != 0 or ssh_out.strip() != "connected":
        return _result("fail", [f"{name}: native Sway/SSH continuity checks failed"])
    return None


_EVALUATORS = {
    "DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01": _thermal_aux,
    "DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01": _thermal_coverage,
    "DELTA-FORUM-USB-RAID-LINK-ADMISSION-01": _usb_raid,
    "DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01": _backup_mount,
    "DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01": _display_carveout,
    "DELTA-ROOT-GX10-SOC-EC-CABLE-RECOVERY-CANDIDATE-01": _gx10_cable,
    "DELTA-ROOT-SUBAMBIENT-COOLING-AND-UMA-CANARY-01": _subambient,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, choices=sorted(CARD_IDS))
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args(argv)
    result = verify(args.id, args.evidence)
    print(json.dumps(result, sort_keys=True))
    return {"pass": 0, "fail": 1, "unknown": 2}[result["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
