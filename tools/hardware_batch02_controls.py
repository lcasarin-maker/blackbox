"""Evidence-driven gates for the generated Batch 02 hardware findings.

Capture files contain caller-supplied command transcripts and are not authenticated
by this reader. Each predicate reparses native outputs; metadata never grants PASS.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import json
import math
import re
import shlex
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from tools.apt_sources import verify_release_signature
from tools.capture_io import read_regular_bytes, strict_json_loads

ROOT = Path(__file__).resolve().parents[1]
# Generated from hardware-batch-02.json; tests assert this tuple stays in exact
# source order so runtime edits to that file cannot alter predicate ownership.
IDS = (
    "DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01",
    "DELTA-FORUM-CX7-FW-UPDATE-GUARD-01",
    "DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01",
    "DELTA-FORUM-CX7-POSTHOTPLUG-01",
    "DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01",
    "DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01",
    "DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01",
    "DELTA-FORUM-MEMORY-RECOVERY-SOAK-01",
    "DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01",
    "DELTA-FORUM-RECOVERY-APT-UPDATE-01",
)
MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 50_000


class UnsafeCapture(ValueError):
    """The named evidence path violates a filesystem safety condition."""


def _result(status: str, reason: str, evidence: Path) -> dict[str, Any]:
    return {"status": status, "reason": reason, "files": [str(evidence)],
            "fail": int(status == "fail"), "could_not_run": int(status == "unknown")}


def _load(evidence: Path, finding_id: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    path = evidence / "commands.json"
    try:
        raw = _read_bounded_regular(path)
        data = strict_json_loads(raw.decode("utf-8"))
    except UnsafeCapture as exc:
        return None, _result("fail", str(exc), path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        return None, _result("unknown", f"raw command capture unavailable or malformed: {exc}", path)
    if not isinstance(data, dict) or type(data.get("schema")) is not int or data.get("schema") != 1:
        return None, _result("fail", "capture schema is not version 1", path)
    if data.get("id") != finding_id:
        return None, _result("fail", "capture finding ID mismatch", path)
    rows = data.get("commands")
    if not isinstance(rows, list) or not rows:
        return None, _result("unknown", "native command transcript is absent", path)
    if any(key in data for key in ("status", "pass", "passed", "healthy", "negative_detected", "_trusted_plan_sha256")):
        return None, _result("fail", "capture contains an asserted outcome flag", path)
    error = _validate_rows(rows, path)
    return (None, error) if error else (data, None)


def _read_bounded_regular(path: Path) -> bytes:
    try:
        raw = read_regular_bytes(path, MAX_BYTES)
    except OSError as exc:
        if isinstance(exc, FileNotFoundError):
            raise
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise UnsafeCapture("evidence path traverses a symlink or non-directory component") from exc
        if any(
            message in str(exc).lower() for message in ("regular file", "parent traversal")
        ):
            raise UnsafeCapture(str(exc)) from exc
        raise
    if len(raw) > MAX_BYTES:
        raise UnsafeCapture("capture exceeds the 8 MiB input bound")
    return raw


def _validate_rows(rows: list[Any], path: Path) -> dict[str, Any] | None:
    if len(rows) > MAX_ROWS:
        return _result("fail", "capture row count exceeds safety bound", path)
    stamps: list[datetime] = []
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get("argv"), list)
                or not row["argv"] or any(not isinstance(arg, str) for arg in row["argv"])
                or type(row.get("exit")) is not int or not isinstance(row.get("stdout"), str)
                or not isinstance(row.get("stderr", ""), str)
                or not isinstance(row.get("captured_at"), str)):
            return _result("fail", "raw command row is malformed", path)
        try:
            stamp = datetime.fromisoformat(row["captured_at"].replace("Z", "+00:00"))
        except ValueError:
            return _result("fail", "capture timestamp is not ISO-8601", path)
        if stamp.tzinfo is None:
            return _result("fail", "capture timestamp has no timezone", path)
        stamps.append(stamp)
        if any(key in row for key in ("status", "pass", "passed", "healthy", "negative_detected")):
            return _result("fail", "command row contains an asserted outcome flag", path)
    if any(left >= right for left, right in zip(stamps, stamps[1:])):
        return _result("fail", "command timestamps are not strictly increasing", path)
    return None


def _cmd(data: dict[str, Any], predicate: Callable[[list[str]], bool], *, phase: str | None = None) -> dict[str, Any] | None:
    rows = data["commands"]
    return next((row for row in rows if predicate(row["argv"])
                 and (phase is None or row.get("phase") == phase)), None)


def _need(data: dict[str, Any], path: Path, label: str,
          predicate: Callable[[list[str]], bool], *, phase: str | None = None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    row = _cmd(data, predicate, phase=phase)
    if row is None:
        return None, _result("unknown", f"required raw command missing: {label}", path)
    if row["exit"] != 0:
        return None, _result("fail", f"required command failed: {label} (exit {row['exit']})", path)
    return row, None


def _prefix(command: str, *args: str) -> Callable[[list[str]], bool]:
    expected = [command, *args]
    return lambda argv: argv[:len(expected)] == expected


def _identity(data: dict[str, Any], path: Path) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
    dmi, error = _need(data, path, "dmidecode -t system", _prefix("dmidecode", "-t", "system"))
    if error:
        return None, error
    kernel, error = _need(data, path, "uname -r", _prefix("uname", "-r"))
    if error:
        return None, error
    assert dmi is not None and kernel is not None
    fields: dict[str, str] = {}
    for line in dmi["stdout"].splitlines():
        key, separator, value = line.partition(":")
        if separator and key.strip() in {"Manufacturer", "Product Name", "BIOS Version"}:
            fields[key.strip()] = value.strip()
    if not all(fields.get(key) for key in ("Manufacturer", "Product Name", "BIOS Version")):
        return None, _result("unknown", "manufacturer/product/BIOS tuple incomplete", path)
    release = kernel["stdout"].strip()
    if not release:
        return None, _result("unknown", "running kernel release is empty", path)
    fields["Kernel"] = release
    return fields, None


def _json_stdout(row: dict[str, Any], label: str) -> tuple[Any | None, str | None]:
    try:
        value = json.loads(row["stdout"], parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)))
    except (json.JSONDecodeError, ValueError, RecursionError):
        return None, f"{label} output is not valid finite JSON"
    return value, None


def _finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except (OverflowError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _parsed_number(value: str) -> float | None:
    if not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", value):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _vendor_refs(data: dict[str, Any], identity: dict[str, str]) -> tuple[list[dict[str, str]] | None, str | None]:
    refs = data.get("vendor_sources")
    if not isinstance(refs, list) or not refs:
        return None, "primary vendor compatibility text with URL and digest is missing"
    accepted = {"nvidia.com", "docs.nvidia.com", "asus.com", "www.asus.com", "hp.com", "www.hp.com",
                "dell.com", "www.dell.com", "ubuntu.com", "canonical.com"}
    valid: list[dict[str, str]] = []
    for ref in refs:
        if not isinstance(ref, dict) or not isinstance(ref.get("url"), str) or not isinstance(ref.get("text"), str):
            return None, "vendor reference row malformed"
        parsed_url = urlsplit(ref["url"])
        if (parsed_url.scheme != "https" or parsed_url.username is not None or parsed_url.password is not None
                or parsed_url.hostname not in accepted):
            return None, "reference URL is not a primary vendor domain"
        if hashlib.sha256(ref["text"].encode()).hexdigest() != ref.get("sha256"):
            return None, "vendor excerpt digest mismatch"
        if len(ref["text"].strip()) < 80:
            return None, "vendor excerpt is too short to establish compatibility"
        valid.append({"url": ref["url"], "text": ref["text"]})
    all_text = "\n".join(row["text"] for row in valid)
    missing = [key for key, value in identity.items() if value not in all_text]
    if missing:
        return None, "vendor compatibility excerpt does not cite captured tuple: " + ", ".join(missing)
    return valid, None


def _capture_plan(data: dict[str, Any], path: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    plan = data.get("experiment_plan")
    if not isinstance(plan, dict):
        return None, _result("unknown", "predeclared experiment plan missing", path)
    row = _cmd(data, lambda argv: Path(argv[0]).name == "cat" and any("experiment-plan" in arg for arg in argv[1:]))
    if row is None or row["exit"] != 0:
        return None, _result("unknown", "literal captured experiment-plan file missing", path)
    if data["commands"].index(row) != 0:
        return None, _result("fail", "experiment plan was first captured after other commands; predeclaration chronology is unproven", path)
    captured, error = _json_stdout(row, "experiment plan")
    if error:
        return None, _result("fail", error, path)
    if captured != plan:
        return None, _result("fail", "plan differs from captured plan-file content", path)
    return plan, None


def _cutlass(data: dict[str, Any], path: Path) -> dict[str, Any]:
    plan, error = _capture_plan(data, path)
    if error:
        return error
    assert plan is not None
    error = _cutlass_plan(plan, path)
    if error:
        return error
    error = _cutlass_build(data, path, plan)
    if error:
        return error
    error = _cutlass_canary(data, path, plan)
    if error:
        return error
    error = _cutlass_negative(data, path)
    if error:
        return error
    return _result("pass", "pinned SM121 build, supported-path accuracy/requests/soak and unsupported-ISA negative were recomputed from caller-supplied native captures", path)


def _cutlass_plan(plan: dict[str, Any], path: Path) -> dict[str, Any] | None:
    required = ("cutlass_revision", "cute_revision", "backend", "operation", "model_sha256",
                "input_sha256", "batch_size", "concurrency", "soak_seconds")
    if any(not isinstance(plan.get(k), str) or not plan[k].strip() for k in required[:6]):
        return _result("unknown", "CUTLASS/CuTe/backend/operation/model/input contract incomplete", path)
    if any(type(plan.get(k)) is not int or plan[k] <= 0 for k in required[6:]):
        return _result("unknown", "positive batch/concurrency/soak contract is incomplete", path)
    return None


def _cutlass_build(data: dict[str, Any], path: Path, plan: dict[str, Any]) -> dict[str, Any] | None:
    identity, error = _identity(data, path)
    if error:
        return error
    assert identity is not None
    gpu, error = _need(data, path, "nvidia-smi name/compute capability/driver query",
                       lambda a: a[:2] == ["nvidia-smi", "--query-gpu=name,compute_cap,driver_version"])
    if error:
        return error
    assert gpu is not None
    fields = [x.strip() for x in gpu["stdout"].strip().split(",")]
    if len(fields) != 3 or "GB10" not in fields[0] or fields[1] not in {"12.1", "12.0"}:
        return _result("fail", "subject is not a GB10/SM12x GPU or driver tuple is malformed", path)
    build, error = _need(data, path, "pinned CUTLASS build", lambda a: "cmake" in a[0].lower() or "ninja" in a[0].lower(), phase="build")
    if error:
        return error
    assert build is not None
    pinned = (plan["cutlass_revision"], plan["cute_revision"], plan["backend"], plan["operation"])
    build_material = "\n".join([*build["argv"], build["stdout"], build["stderr"]])
    if any(value not in build_material for value in pinned):
        return _result("unknown", "captured build invocation/output does not bind all pinned CUTLASS/CuTe/backend/operation versions", path)
    if any("CUTE_DSL_ARCH=sm_100a" in arg or "sm_100a" in arg for arg in build["argv"]):
        return _result("fail", "build forces SM100 architecture for an SM121 subject", path)
    elf, error = _need(data, path, "cuobjdump ELF architecture inspection",
                       lambda a: Path(a[0]).name == "cuobjdump" and "--list-elf" in a)
    if error:
        return error
    assert elf is not None
    if "sm_121" not in elf["stdout"] or re.search(r"\bsm_100a?\b", elf["stdout"]):
        return _result("fail", "compiled artifact does not exclusively expose the planned SM121 path", path)
    return None


def _cutlass_canary(data: dict[str, Any], path: Path, plan: dict[str, Any]) -> dict[str, Any] | None:
    smoke, error = _need(data, path, "captured SM121 canary result", lambda a: Path(a[0]).name == "cat", phase="canary")
    if error:
        return error
    assert smoke is not None
    result, parse_error = _json_stdout(smoke, "SM121 canary")
    if parse_error or not isinstance(result, dict):
        return _result("fail", parse_error or "SM121 canary result must be an object", path)
    measured = ("requests", "completed", "batch_size", "concurrency", "duration_seconds")
    if any(_finite(result.get(key)) is None for key in measured):
        return _result("unknown", "canary lacks measured requests/soak values", path)
    logits, reference = result.get("logits"), result.get("reference_logits")
    if (not isinstance(logits, list) or not logits or not isinstance(reference, list)
            or len(reference) != len(logits) or any(_finite(x) is None for x in logits + reference)):
        return _result("unknown", "canary must carry aligned finite logits and reference values for recomputation", path)
    error_value = max(abs(float(left) - float(right)) for left, right in zip(logits, reference))
    if (result["requests"] <= 0 or result["completed"] != result["requests"]
            or result["batch_size"] != plan["batch_size"] or result["concurrency"] != plan["concurrency"]
            or result["duration_seconds"] < plan["soak_seconds"]):
        return _result("fail", "SM121 canary requests, logits, batching, or planned soak failed", path)
    tolerance = _finite(plan.get("reference_max_abs_error"))
    if tolerance is None or tolerance < 0:
        return _result("unknown", "reference comparison tolerance is not predeclared", path)
    if error_value > tolerance:
        return _result("fail", "SM121 canary exceeds predeclared reference tolerance", path)
    return None


def _cutlass_negative(data: dict[str, Any], path: Path) -> dict[str, Any] | None:
    negative = _cmd(data, lambda a: "tcgen05" in " ".join(a), phase="negative")
    if negative is None:
        return _result("unknown", "unsupported tcgen05 negative build missing", path)
    if negative["exit"] == 0:
        return _result("fail", "unsupported tcgen05 path was accepted for SM12x", path)
    if not re.search(r"unsupported|not support|requires.*sm_10[01]", negative["stdout"] + negative["stderr"], re.I):
        return _result("fail", "SM12x negative did not demonstrate the expected early ISA rejection", path)
    return None


def _fw_guard(data: dict[str, Any], path: Path) -> dict[str, Any]:
    plan, error = _capture_plan(data, path)
    if error:
        return error
    assert plan is not None
    approval = _plan_approval(data, path, plan)
    if approval:
        return approval
    identity, error = _identity(data, path)
    if error:
        return error
    assert identity is not None
    if "ASUS" not in identity["Manufacturer"].upper() or "GX10" not in identity["Product Name"].upper():
        return _result("fail", "firmware guard subject is not the scoped ASUS GX10", path)
    error = _fw_device(data, path, plan)
    if error:
        return error
    error = _fw_package_guard(data, path, plan)
    if error:
        return error
    error = _fw_recovery(data, path)
    if error:
        return error
    device = _cmd(data, lambda a: any(Path(x).name in {"mstflint", "flint"} for x in a) and "q" in a)
    assert device is not None
    fw = re.search(r"(?im)^(?:FW Version|Firmware version):\s*(\S+)", device["stdout"])
    psid = re.search(r"(?im)^PSID:\s*(\S+)", device["stdout"])
    if fw is None or psid is None:
        return _result("unknown", "exact firmware tuple unavailable for OEM reference matching", path)
    refs, ref_error = _vendor_refs(data, {"PSID": psid.group(1), "firmware": fw.group(1),
                                         "package": str(plan.get("package_name", "")),
                                         "package version": str(plan.get("package_version", "")),
                                         "repository key fingerprint": str(plan.get("repository_fingerprint", ""))})
    if ref_error or refs is None:
        return _result("unknown", ref_error or "OEM firmware compatibility evidence missing", path)
    return _result("pass", "PSID/firmware, PCI bus-master and active RDMA-driver state, maintainer-script scan, signed source and indirect-writer negative were parsed", path)


def _fw_device(data: dict[str, Any], path: Path, plan: dict[str, Any]) -> dict[str, Any] | None:
    target, error = _fw_device_target(plan, path)
    if error:
        return error
    assert target is not None
    bdf, hca = target
    query, error = _fw_query(data, path, bdf)
    if error:
        return error
    assert query is not None
    psid = re.search(r"(?im)^PSID:\s*(\S+)", query["stdout"])
    firmware = re.search(r"(?im)^(?:FW Version|Firmware version):\s*(\S+)", query["stdout"])
    if psid is None or firmware is None:
        return _result("unknown", "read-only query lacks exact CX7 PSID and firmware version", path)
    if psid.group(1) != "NVD0000000087":
        return _result("fail", "CX7 PSID differs from the finding's scoped device", path)
    pci_error = _fw_pci_binding(data, path, bdf)
    if pci_error:
        return pci_error
    return _fw_hca_binding(data, path, bdf, hca, firmware.group(1))


def _fw_device_target(plan: dict[str, Any], path: Path) -> tuple[tuple[str, str] | None, dict[str, Any] | None]:
    bdf = plan.get("bdf")
    hca = plan.get("rdma_hca")
    if not isinstance(bdf, str) or not re.fullmatch(r"[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]", bdf):
        return None, _result("unknown", "canonical full-domain CX7 BDF is missing from the plan", path)
    if not isinstance(hca, str) or not re.fullmatch(r"mlx\d+_\d+", hca):
        return None, _result("unknown", "exact RDMA HCA identity is missing from the plan", path)
    return (bdf.lower(), hca), None


def _fw_query(data: dict[str, Any], path: Path, bdf: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    query, error = _need(data, path, "read-only Mellanox PSID/firmware query",
                         lambda a: any(Path(x).name in {"mstflint", "flint"} for x in a) and "q" in a and "-d" in a)
    if error:
        return None, error
    assert query is not None
    if query["argv"].index("-d") + 1 >= len(query["argv"]):
        return None, _result("fail", "mstflint device argument is missing", path)
    query_index = query["argv"].index("-d")
    query_bdf = query["argv"][query_index + 1] if query_index + 1 < len(query["argv"]) else ""
    if query_bdf.removeprefix("0000:").lower() != bdf.split(":", 1)[1].lower():
        return None, _result("fail", "mstflint query targets a different PCI bus/device/function", path)
    return query, None


def _fw_pci_binding(data: dict[str, Any], path: Path, bdf: str) -> dict[str, Any] | None:
    lspci, error = _need(data, path, "targeted PCI identity/BME/driver query",
                         lambda a: Path(a[0]).name == "lspci" and "-vv" in a and "-s" in a and bdf in a)
    if error:
        return error
    assert lspci is not None
    pci_ids = re.findall(r"(?im)^\s*([0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7])\s+", lspci["stdout"])
    short_bdf = bdf.split(":", 1)[1]
    selected_matches = [seen for seen in pci_ids if seen.lower().endswith(short_bdf.lower())]
    if bdf.lower() not in {item.lower() for item in pci_ids} or selected_matches != [bdf.lower()]:
        return _result("fail", "targeted PCI capture does not uniquely bind canonical BDF to the selected bus/device/function", path)
    inventory, error = _need(data, path, "domain-qualified PCI inventory", lambda a: Path(a[0]).name == "lspci" and "-D" in a)
    if error:
        return error
    assert inventory is not None
    inventory_ids = re.findall(r"(?im)^\s*([0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7])\s+", inventory["stdout"])
    if [item.lower() for item in inventory_ids if item.lower().endswith(short_bdf.lower())] != [bdf.lower()]:
        return _result("unknown", "short mstflint BDF cannot be uniquely normalized against full-domain PCI inventory", path)
    if "15b3:" not in lspci["stdout"].lower():
        return _result("fail", "planned CX7 PCI function does not report Mellanox vendor identity", path)
    if "BusMaster+" not in lspci["stdout"]:
        return _result("fail", "CX7 PCI bus mastering prerequisite is disabled", path)
    if not re.search(r"(?im)^\s*Kernel driver in use:\s*mlx5_core\s*$", lspci["stdout"]):
        return _result("fail", "ConnectX device is not bound to its native mlx5_core driver", path)
    return None


def _fw_hca_binding(data: dict[str, Any], path: Path, bdf: str, hca: str, firmware: str) -> dict[str, Any] | None:
    sysfs, error = _need(data, path, "RDMA HCA sysfs-to-PCI mapping",
                         lambda a: Path(a[0]).name == "readlink" and "-f" in a and f"/sys/class/infiniband/{hca}/device" in a)
    if error:
        return error
    assert sysfs is not None
    if bdf.lower() not in sysfs["stdout"].lower():
        return _result("fail", "RDMA HCA sysfs device path resolves to a different PCI BDF", path)
    rdma, error = _need(data, path, "targeted active RDMA port/firmware readback",
                         lambda a: Path(a[0]).name == "ibv_devinfo" and "-v" in a and "-d" in a and hca in a)
    if error:
        return error
    assert rdma is not None
    if not re.search(r"(?im)^\s*state:\s*PORT_ACTIVE\s*$", rdma["stdout"]):
        return _result("fail", "native RDMA device reports no active port", path)
    rdma_fw = re.search(r"(?im)^\s*fw_ver:\s*(\S+)", rdma["stdout"])
    if rdma_fw is None or rdma_fw.group(1) != firmware:
        return _result("fail", "mstflint and the BDF-bound RDMA HCA firmware readbacks disagree", path)
    return None


def _fw_package_guard(data: dict[str, Any], path: Path, plan: dict[str, Any]) -> dict[str, Any] | None:
    package, error = _fw_package_contract(plan, path)
    if error:
        return error
    assert package is not None
    package_path, package_name, package_digest = package
    package_error = _fw_package_digest(data, path, package_path, package_digest)
    if package_error:
        return package_error
    extract_dir = str(plan["script_extract_dir"])
    scripts, error = _fw_package_scripts(data, path, package_path, extract_dir)
    if error:
        return error
    assert scripts is not None
    stages = {Path(row["argv"][-1]).name for row in scripts if row["exit"] == 0}
    if not {"preinst", "postinst", "prerm", "postrm"}.issubset(stages):
        return _result("unknown", "captured package preinst/postinst/prerm/postrm scripts missing; indirect flash path cannot be excluded", path)
    helper_error = _fw_script_helpers(data, path, scripts)
    if helper_error:
        return helper_error
    return _fw_signature_source(data, path, plan, package_name, package_path)


def _fw_script_helpers(data: dict[str, Any], path: Path, scripts: list[dict[str, Any]]) -> dict[str, Any] | None:
    helpers: set[str] = set()
    for row in scripts:
        direct, refs, ambiguous = _firmware_script_analysis(row["stdout"])
        if direct:
            return _result("fail", "package maintainer script invokes a CX7 firmware writer", path)
        if ambiguous:
            return _result("unknown", "maintainer script has an indirect/dynamic command whose target cannot be resolved", path)
        helpers.update(refs)
    if not helpers:
        return None
    for helper in sorted(helpers):
        error = _check_helper_source(data, path, helper)
        if error:
            return error
    return None


def _check_helper_source(data: dict[str, Any], path: Path, helper: str) -> dict[str, Any] | None:
    row = _cmd(data, lambda a: Path(a[0]).name == "cat" and len(a) == 2 and a[1] == helper, phase="helper-source")
    if row is None:
        return _result("unknown", f"bytes for invoked maintainer helper are missing: {helper}", path)
    if row["exit"] != 0:
        return _result("fail", f"maintainer helper source read failed: {helper}", path)
    direct, nested, ambiguous = _firmware_script_analysis(row["stdout"])
    if direct:
        return _result("fail", f"invoked helper contains a CX7 firmware writer: {helper}", path)
    if nested or ambiguous:
        return _result("unknown", f"nested or dynamic helper chain is unresolved: {helper}", path)
    if not re.match(r"^#!\s*(?:(?:/usr/bin/env\s+)?(?:ba|da)?sh|/(?:usr/)?bin/(?:ba|da)?sh)\b", row["stdout"]):
        return _result("unknown", f"invoked helper bytes are not a recognized shell script: {helper}", path)
    return None


def _firmware_script_analysis(text: str) -> tuple[bool, set[str], bool]:
    helpers: set[str] = set()
    ambiguous = False
    for line in text.splitlines():
        command = line.split("#", 1)[0].strip()
        if not command or command.startswith("#!"):
            continue
        try:
            shlex.split(command, comments=False, posix=True)
        except ValueError:
            ambiguous = True
            continue
        if _contains_firmware_writer(command):
            return True, helpers, False
        indirect = re.search(r"(?:^|[;&|]\s*|then\s+)(?:(?:exec|command)\s+)?(?:source\s+|\.\s+|(?:sh|bash|dash)\s+)(\S+)", command)
        if indirect:
            target = indirect.group(1).strip("'\"")
            if target.startswith("/") and "$" not in target and "`" not in target:
                helpers.add(target)
            else:
                ambiguous = True
        for external in re.finditer(r"(?:^|[;&|]\s*|then\s+|do\s+)(?:(?:exec|command)\s+)?(/[^\s;|&]+)(?=\s|[;&|]|$)", command):
            helpers.add(external.group(1).strip("'\"") )
        if re.search(r"(?:^|[;&|]\s*|then\s+|do\s+)(?:exec\s+|command\s+)?(?:python\S*|perl\S*|ruby\S*|node\S*|env\s+\S+|[A-Za-z0-9_.+-]+/[^\s;|&]+)(?:\s|$)", command):
            ambiguous = True
        if re.search(r"(?:\beval\b|\$\(|`)", command):
            ambiguous = True
    return False, helpers, ambiguous


def _fw_signature_source(data: dict[str, Any], path: Path, plan: dict[str, Any],
                         package_name: str, package_path: str) -> dict[str, Any] | None:
    repository_error = _fw_repository_plan(data, path, plan, package_name)
    if repository_error:
        return repository_error
    release, error = _verify_signed_release(data, path, plan)
    if error:
        return error
    assert release is not None
    package_error = _verify_signed_package_index(data, path, plan, package_name, package_path)
    if package_error:
        return package_error
    return None


def _fw_repository_plan(data: dict[str, Any], path: Path, plan: dict[str, Any],
                       package_name: str) -> dict[str, Any] | None:
    required = ("package_origin", "package_source_uri", "package_version", "inrelease_path", "keyring_path",
                "repository_fingerprint", "inrelease_artifact", "keyring_artifact",
                "inrelease_sha256", "keyring_sha256", "packages_index_path", "package_index_relative", "package_filename")
    if any(not isinstance(plan.get(key), str) or not plan[key] for key in required):
        return _result("unknown", "signed InRelease/Packages-to-deb verification plan is incomplete", path)
    if type(plan.get("package_size")) is not int or plan["package_size"] <= 0:
        return _result("unknown", "candidate package size is missing or malformed", path)
    fingerprint = plan["repository_fingerprint"]
    if not re.fullmatch(r"[0-9A-F]{40,64}", fingerprint):
        return _result("unknown", "pinned repository signing fingerprint is malformed", path)
    channel, error = _need(data, path, "signed repository origin",
                           lambda a: Path(a[0]).name == "apt-cache" and "policy" in a and package_name in a)
    if error:
        return error
    assert channel is not None
    source_uri = plan["package_source_uri"].rstrip("/")
    if not _valid_package_source_uri(source_uri, plan["package_origin"]):
        return _result("fail", "predeclared APT source URI is not a canonical HTTPS URL on the vendor domain", path)
    arch, component, suite = (plan.get("package_architecture"), plan.get("package_component"), plan.get("package_suite"))
    if not all(isinstance(value, str) and value for value in (arch, component, suite)):
        return _result("unknown", "exact signed repository suite/component/architecture tuple is incomplete", path)
    if plan["package_index_relative"] != f"{component}/binary-{arch}/Packages":
        return _result("fail", "APT source tuple and signed Packages index component/architecture disagree", path)
    policy = rf"(?im)^\s*500\s+{re.escape(source_uri)}\s+{re.escape(str(suite))}/{re.escape(str(component))}\s+{re.escape(str(arch))}\s+Packages\s*$"
    if not re.search(policy, channel["stdout"]):
        return _result("fail", "APT candidate origin does not match the predeclared signed repository", path)
    return None


def _signature_inputs(path: Path, plan: dict[str, Any]) -> tuple[Path | None, Path | None, bytes | None, str | None, dict[str, Any] | None]:
    manifest = _artifact_path(path, plan.get("inrelease_artifact"))
    keyring = _artifact_path(path, plan.get("keyring_artifact"))
    if manifest is None or keyring is None:
        return None, None, None, None, _result("unknown", "archived InRelease and explicit repository keyring artifacts are required", path)
    fingerprint = plan.get("repository_fingerprint")
    if (not isinstance(fingerprint, str) or not re.fullmatch(r"[0-9A-F]{40,64}", fingerprint)
            or not re.fullmatch(r"[0-9a-f]{64}", str(plan.get("inrelease_sha256", "")))
            or not re.fullmatch(r"[0-9a-f]{64}", str(plan.get("keyring_sha256", "")))):
        return None, None, None, None, _result("unknown", "approved exact InRelease/keyring digests and signing fingerprint are required", path)
    try:
        release_bytes = _read_bounded_regular(manifest)
        keyring_bytes = _read_bounded_regular(keyring)
    except (OSError, UnsafeCapture) as exc:
        return None, None, None, None, _result("unknown", f"archived signature input unavailable: {type(exc).__name__}: {exc}", path)
    if hashlib.sha256(release_bytes).hexdigest() != plan["inrelease_sha256"]:
        return None, None, None, None, _result("fail", "archived InRelease bytes differ from the approved digest", path)
    if hashlib.sha256(keyring_bytes).hexdigest() != plan["keyring_sha256"]:
        return None, None, None, None, _result("fail", "archived repository keyring differs from the approved digest", path)
    return manifest, keyring, release_bytes, fingerprint, None


def _verify_signed_release(data: dict[str, Any], path: Path, plan: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    manifest, keyring, release_bytes, fingerprint, error = _signature_inputs(path, plan)
    if error:
        return None, error
    assert manifest is not None and keyring is not None and release_bytes is not None and fingerprint is not None
    result = verify_release_signature(manifest, [keyring])
    if result.get("status") == "could_not_run":
        return None, _result("unknown", "exact archived InRelease signature verification could not run", path)
    if result.get("status") != "pass" or result.get("manifest_sha256") != plan["inrelease_sha256"]:
        return None, _result("fail", "archived InRelease signature is invalid or binds different bytes", path)
    if result.get("keyring_sha256") != [plan["keyring_sha256"]]:
        return None, _result("fail", "signature verifier used a different repository keyring", path)
    records = result.get("validsig_records")
    if not isinstance(records, list) or not any(
            isinstance(record, str) and re.fullmatch(
                rf"\[GNUPG:\] VALIDSIG {re.escape(fingerprint)} \S+(?: \S+){{7,8}}", record)
            for record in records):
        return None, _result("fail", "exact InRelease signature lacks a full native VALIDSIG for the approved fingerprint", path)
    try:
        return release_bytes.decode("utf-8"), None
    except UnicodeError:
        return None, _result("unknown", "archived InRelease is not UTF-8 text", path)


def _artifact_path(capture_path: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value or Path(value).is_absolute() or ".." in Path(value).parts:
        return None
    return capture_path.parent / value


def _release_index_entry(text: str, relative_path: str) -> tuple[str, int] | None:
    lines = text.splitlines()
    section = next((index for index, line in enumerate(lines) if line == "SHA256:"), None)
    if section is None:
        return None
    for line in lines[section + 1:]:
        if not line[:1].isspace():
            break
        match = re.fullmatch(r"\s*([0-9a-f]{64})\s+(\d+)\s+(\S+)\s*", line)
        if match and match.group(3) == relative_path:
            return match.group(1), int(match.group(2))
    return None


def _verify_signed_package_index(data: dict[str, Any], path: Path, plan: dict[str, Any],
                                 package_name: str, package_path: str) -> dict[str, Any] | None:
    index_path = plan["packages_index_path"]
    index, error = _need(data, path, "raw Packages index", lambda a: Path(a[0]).name == "cat" and len(a) == 2 and a[1] == index_path)
    if error:
        return error
    assert index is not None
    expected_release = _release_index_entry(_captured_inrelease(path, plan), plan["package_index_relative"])
    if expected_release is None:
        return _result("unknown", "signed Release index metadata unavailable", path)
    actual_hash = hashlib.sha256(index["stdout"].encode("utf-8")).hexdigest()
    actual_size = len(index["stdout"].encode("utf-8"))
    if (actual_hash, actual_size) != expected_release:
        return _result("fail", "Packages index bytes differ from signed InRelease SHA256/size", path)
    parsed_index = _verify_packages_stanza(data, index["stdout"], path, package_name, plan)
    if parsed_index:
        return parsed_index
    pkg_size, error = _native_file_size(data, path, package_path)
    if error:
        return error
    if pkg_size != plan["package_size"]:
        return _result("fail", "candidate .deb size differs from its signed Packages stanza", path)
    return None


def _captured_inrelease(path: Path, plan: dict[str, Any]) -> str:
    artifact = _artifact_path(path, plan.get("inrelease_artifact"))
    if artifact is None:
        return ""
    try:
        return _read_bounded_regular(artifact).decode("utf-8")
    except (OSError, UnicodeError, UnsafeCapture):
        return ""


def _verify_packages_stanza(data: dict[str, Any], text: str, path: Path, package_name: str,
                            plan: dict[str, Any]) -> dict[str, Any] | None:
    package_path = str(plan["package_path"])
    stanza = next((block for block in text.split("\n\n") if re.search(rf"(?m)^Package:\s*{re.escape(package_name)}\s*$", block)
                   and re.search(rf"(?m)^Version:\s*{re.escape(plan['package_version'])}\s*$", block)), None)
    if stanza is None:
        return _result("unknown", "exact package/version stanza absent from the signed Packages index", path)
    digest = re.search(r"(?m)^SHA256:\s*([0-9a-f]{64})\s*$", stanza)
    size = re.search(r"(?m)^Size:\s*(\d+)\s*$", stanza)
    filename = re.search(r"(?m)^Filename:\s*(\S+)\s*$", stanza)
    if digest is None or size is None or filename is None:
        return _result("unknown", "signed Packages stanza lacks filename, size or SHA256", path)
    actual_digest = _captured_sha256(data, package_path)
    if actual_digest is None:
        return _result("unknown", "candidate .deb hash readback missing", path)
    if digest.group(1) != actual_digest or int(size.group(1)) != plan["package_size"]:
        return _result("fail", "candidate .deb SHA256/size differs from signed Packages stanza", path)
    if filename.group(1) != plan["package_filename"]:
        return _result("fail", "candidate filename differs from signed Packages stanza", path)
    if filename.group(1).rsplit("/", 1)[-1] != Path(package_path).name:
        return _result("fail", "local candidate artifact name differs from signed Packages filename", path)
    return None


def _captured_sha256(data: dict[str, Any], package_path: str) -> str | None:
    row = _cmd(data, lambda a: Path(a[0]).name == "sha256sum" and package_path in a)
    match = re.search(r"(?m)^([0-9a-f]{64})\s+", row["stdout"]) if row is not None and row["exit"] == 0 else None
    return match.group(1) if match else None


def _native_file_size(data: dict[str, Any], path: Path, target: str) -> tuple[int | None, dict[str, Any] | None]:
    row, error = _need(data, path, "stat byte-size readback", lambda a: Path(a[0]).name == "stat" and a[-1] == target and "-c" in a)
    if error:
        return None, error
    assert row is not None
    match = re.fullmatch(r"\s*(\d+)\s*", row["stdout"])
    return (int(match.group(1)), None) if match else (None, _result("fail", "stat size output malformed", path))


def _fw_package_scripts(data: dict[str, Any], path: Path, package_path: str,
                        extract_dir: str) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None]:
    extract, error = _need(data, path, "read-only dpkg control archive extraction",
                           lambda a: Path(a[0]).name == "dpkg-deb" and a[1:3] == ["--control", package_path]
                           and len(a) == 4 and a[3] == extract_dir)
    if error:
        return None, error
    assert extract is not None
    scripts = [row for row in data["commands"] if row.get("phase") == "maintainer-script"
               and Path(row["argv"][0]).name == "cat" and row["argv"][-1].startswith(extract_dir + "/")]
    return scripts, None


def _fw_package_contract(plan: dict[str, Any], path: Path) -> tuple[tuple[str, str, str] | None, dict[str, Any] | None]:
    package_path = plan.get("package_path")
    package_digest = plan.get("package_sha256")
    package_name = plan.get("package_name")
    package_origin = plan.get("package_origin")
    extract_dir = plan.get("script_extract_dir")
    if (not isinstance(package_path, str) or not package_path or not isinstance(package_name, str)
            or not package_name or not isinstance(package_origin, str) or not package_origin
            or not isinstance(extract_dir, str) or not extract_dir.startswith("/tmp/")
            or not isinstance(package_digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", package_digest)):
        return None, _result("unknown", "exact candidate package path/name/hash must be predeclared", path)
    if not _valid_package_origin(package_origin):
        return None, _result("fail", "candidate firmware package origin is outside the NVIDIA/ASUS vendor domains", path)
    return (package_path, package_name, package_digest), None


def _valid_package_origin(origin: str) -> bool:
    return any(origin == domain or origin.endswith("." + domain) for domain in ("nvidia.com", "asus.com"))


def _valid_package_source_uri(value: str, origin: str) -> bool:
    parsed = urlsplit(value)
    return (parsed.scheme == "https" and parsed.hostname == origin and parsed.username is None
            and parsed.password is None and parsed.port is None and not parsed.query and not parsed.fragment)


def _fw_package_digest(data: dict[str, Any], path: Path, package_path: str, package_digest: str) -> dict[str, Any] | None:
    digest, error = _need(data, path, "candidate package SHA-256", lambda a: Path(a[0]).name == "sha256sum" and package_path in a)
    if error:
        return error
    assert digest is not None
    found = re.search(r"(?m)^([0-9a-f]{64})\s+", digest["stdout"])
    if found is None or found.group(1) != package_digest:
        return _result("fail", "candidate package digest does not match the predeclared artifact", path)
    return None


def _contains_firmware_writer(text: str) -> bool:
    tools = {"mlxfwupdater", "mstflint", "flint", "mlxfwmanager", "fwupdater"}
    for line in text.splitlines():
        command = line.split("#", 1)[0].strip()
        for segment in re.split(r"&&|\|\||[;|]", command):
            try:
                words = shlex.split(segment, comments=False, posix=True)
            except ValueError:
                continue
            while words and words[0] in {"if", "then", "else", "elif", "do", "!", "exec", "command", "sudo"}:
                words.pop(0)
            if words and Path(words[0]).name.casefold() in tools:
                return True
    return False


def _fw_recovery(data: dict[str, Any], path: Path) -> dict[str, Any] | None:
    recovery, error = _need(data, path, "OEM recovery procedure capture", lambda a: Path(a[0]).name == "cat", phase="recovery-procedure")
    if error:
        return error
    assert recovery is not None
    if not recovery["stdout"].strip():
        return _result("unknown", "OEM recovery path is empty", path)
    return None


def _topology(data: dict[str, Any], path: Path) -> dict[str, Any]:
    identity, error = _identity(data, path)
    if error:
        return error
    plan, error = _capture_plan(data, path)
    if error:
        return error
    assert plan is not None and identity is not None
    link = _topology_map(data, plan, path)
    if link:
        return link
    traffic = _topology_traffic(data, plan, path)
    if traffic:
        return traffic
    return _result("pass", "PCI/LLDP connector map, disconnect negative, sustained RDMA rate and NCCL collective recomputed", path)


def _topology_map(data: dict[str, Any], plan: dict[str, Any], path: Path) -> dict[str, Any] | None:
    links = plan.get("links")
    if not isinstance(links, list) or len(links) < 2 or any(not isinstance(x, dict) for x in links):
        return _result("unknown", "planned BDF/netdev/physical peer map is incomplete", path)
    link_error = _validate_link_plan(links, path)
    if link_error:
        return link_error
    pci_error = _validate_link_devices(data, links, path)
    if pci_error:
        return pci_error
    physical, error = _need(data, path, "physical port/peer map", lambda a: Path(a[0]).name in {"lldpctl", "lldpcli"})
    if error:
        return error
    assert physical is not None
    peer_json, parse_error = _json_stdout(physical, "LLDP topology")
    if parse_error or not isinstance(peer_json, dict):
        return _result("unknown", parse_error or "LLDP topology not a structured peer map", path)
    expected = {(str(x["local_port"]), str(x["peer_port"])) for x in links}
    discovered = _lldp_edges(peer_json)
    if not expected.issubset(discovered):
        return _result("fail", "observed LLDP physical peer map does not match intended ports", path)
    for local, peer in expected:
        if {dest for source, dest in discovered if source == local} != {peer}:
            return _result("fail", f"observed physical peer alias for {local}", path)
    return None


def _validate_link_plan(links: list[dict[str, Any]], path: Path) -> dict[str, Any] | None:
    if any(not isinstance(x.get(key), str) for x in links for key in ("bdf", "netdev", "local_port", "peer_port")):
        return _result("unknown", "planned BDF/netdev/physical peer map is incomplete", path)
    expected = {(str(x.get("local_port")), str(x.get("peer_port"))) for x in links}
    locals_ = [source for source, _ in expected]
    if len(expected) != len(links) or len(locals_) != len(set(locals_)):
        return _result("fail", "planned physical map aliases one local port to multiple peers", path)
    bdfs = [str(x["bdf"]).lower() for x in links]
    netdevs = [str(x["netdev"]) for x in links]
    if len(set(bdfs)) != len(bdfs) or len(set(netdevs)) != len(netdevs):
        return _result("fail", "planned BDF/netdev map aliases distinct physical paths", path)
    if any(str(x["local_port"]) != str(x["netdev"]) for x in links):
        return _result("unknown", "LLDP local port identifiers must resolve to the mapped netdev names", path)
    return None


def _validate_link_devices(data: dict[str, Any], links: list[dict[str, Any]], path: Path) -> dict[str, Any] | None:
    pci, error = _need(data, path, "PCI function inventory", lambda a: Path(a[0]).name == "lspci" and "-D" in a)
    if error:
        return error
    assert pci is not None
    if "15b3:" not in pci["stdout"].lower():
        return _result("fail", "planned ConnectX PCI functions are absent", path)
    for link in links:
        bdf = str(link["bdf"]).lower()
        netdev = str(link["netdev"])
        if not re.fullmatch(r"[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]", bdf):
            return _result("fail", "planned PCI BDF malformed", path)
        if bdf not in pci["stdout"].lower():
            return _result("fail", f"planned PCI function {bdf} absent from native inventory", path)
        info, info_error = _need(data, path, f"ethtool driver-to-BDF mapping for {netdev}",
                                 lambda a, netdev=netdev: Path(a[0]).name == "ethtool" and len(a) >= 3 and a[1] == "-i" and a[2] == netdev)
        if info_error:
            return info_error
        assert info is not None
        bus = re.search(r"(?im)^bus-info:\s*(\S+)", info["stdout"])
        if bus is None or bus.group(1).lower() != bdf:
            return _result("fail", f"native netdev-to-PCI mapping does not match {netdev} -> {bdf}", path)
    return None


def _topology_traffic(data: dict[str, Any], plan: dict[str, Any], path: Path) -> dict[str, Any] | None:
    disconnected = _cmd(data, lambda a: "ib_write_bw" in a, phase="negative")
    if disconnected is None:
        return _result("unknown", "physical-disconnect or loopback negative traffic control missing", path)
    negative_rate = _bandwidth(disconnected["stdout"])
    if (disconnected["exit"] == 0 and negative_rate != 0
            or negative_rate not in (None, 0)
            or (disconnected["exit"] != 0 and not re.search(r"(?i)failed|no route|unable|timeout", disconnected["stderr"] + disconnected["stdout"]))):
        return _result("fail", "disconnected physical path still carries measured RDMA traffic", path)
    bw, error = _need(data, path, "sustained peer RDMA traffic", lambda a: "ib_write_bw" in a, phase="positive")
    if error:
        return error
    assert bw is not None
    rate = _bandwidth(bw["stdout"])
    minimum = _finite(plan.get("minimum_gbps"))
    seconds = plan.get("traffic_seconds")
    if rate is None or minimum is None or type(seconds) is not int or seconds <= 0 or "-D" not in bw["argv"]:
        return _result("unknown", "peer throughput or predeclared minimum is unavailable", path)
    if seconds > 3600 or not any(arg.isdigit() and int(arg) >= seconds for arg in bw["argv"]):
        return _result("fail", "RDMA command duration does not match the predeclared sustained traffic interval", path)
    if rate < minimum:
        return _result("fail", "physical peer traffic is below its predeclared minimum", path)
    nccl, error = _need(data, path, "intended-topology NCCL collective", lambda a: "all_reduce_perf" in a or "nccl-tests" in a)
    if error:
        return error
    assert nccl is not None
    if not _nccl_completed(nccl["stdout"]):
        return _result("fail", "NCCL collective did not report completed correctness/performance rows", path)
    return None


def _lldp_edges(value: Any) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    def visit(node: Any) -> None:
        if isinstance(node, dict):
            local = node.get("local_port") or node.get("port_id")
            peer = node.get("peer_port") or node.get("remote_port_id")
            if isinstance(local, str) and isinstance(peer, str):
                edges.add((local, peer))
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)
    visit(value)
    return edges


def _bandwidth(output: str) -> float | None:
    rows = re.findall(r"(?m)^\s*(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s*$", output)
    if rows and re.search(r"BW average\[MB/sec\]", output):
        average_mbytes = _parsed_number(rows[-1][3])
        return average_mbytes * 8 / 1000 if average_mbytes is not None else None
    values = re.findall(r"(?im)^\s*(?:BW average|Bandwidth|BW)\s*[:=]\s*([\d.]+)\s*(?:Gb/sec|Gbit/s|Gbps)\b", output)
    return _parsed_number(values[-1]) if values else None


def _nccl_completed(output: str) -> bool:
    rows = [line.split() for line in output.splitlines()
            if re.fullmatch(r"\s*\d+\s+\d+\s+[\d.]+\s+[\d.]+\s+[\d.]+\s+\d+\s*", line)]
    if not rows or re.search(r"(?i)\b(?:mismatch|failed)\b", output):
        return False
    for row in rows:
        values = [_parsed_number(item) for item in row]
        if any(value is None for value in values) or int(row[5]) != 0 or any(float(x) <= 0 for x in row[0:5]):
            return False
    return True


def _posthotplug(data: dict[str, Any], path: Path) -> dict[str, Any]:
    plan, error = _capture_plan(data, path)
    if error:
        return error
    assert plan is not None
    approval = _plan_approval(data, path, plan)
    if approval:
        return approval
    identity_error = _rdma_stack_identity(data, path, plan)
    if identity_error:
        return identity_error
    error = _posthotplug_pci(data, path, plan)
    if error:
        return error
    error = _posthotplug_services(data, path, plan)
    if error:
        return error
    return _result("pass", "post-hotplug PCI/AER, fresh FieldDiag, bidirectional RDMA, NCCL and recovery evidence passed", path)


def _posthotplug_pci(data: dict[str, Any], path: Path, plan: dict[str, Any]) -> dict[str, Any] | None:
    before = _cmd(data, lambda a: Path(a[0]).name == "lspci" and "-vv" in a, phase="before")
    after = _cmd(data, lambda a: Path(a[0]).name == "lspci" and "-vv" in a, phase="after-hotplug")
    if before is None or after is None:
        return _result("unknown", "pre/post-hotplug PCI endpoint and AER captures missing", path)
    for row, stage in ((before, "pre-hotplug"), (after, "post-hotplug")):
        if row["exit"] != 0:
            return _result("fail", f"{stage} PCI inventory failed", path)
    bdf = str(plan.get("bdf", ""))
    if not re.fullmatch(r"[0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-7]", bdf):
        return _result("unknown", "planned exact CX7 PCI BDF missing", path)
    if bdf.lower() not in before["stdout"].lower() or bdf.lower() not in after["stdout"].lower():
        return _result("fail", "CX7 PCI endpoint disappeared after hotplug", path)
    if any(not re.search(rf"(?im)^\s*{label}:.*$", after["stdout"]) for label in ("UESta", "CESta", "LnkSta", "DevSta")):
        return _result("unknown", "post-hotplug AER/link/device status fields are not fully captured", path)
    if re.search(r"(?im)UESta:.*(?:CorrErr\+|UncorrErr\+)|AER:.*(?:Fatal|Uncorrected)", after["stdout"]):
        return _result("fail", "post-hotplug PCIe AER reports an error", path)
    return None


def _posthotplug_services(data: dict[str, Any], path: Path, plan: dict[str, Any]) -> dict[str, Any] | None:
    after = _cmd(data, lambda a: Path(a[0]).name == "lspci" and "-vv" in a, phase="after-hotplug")
    if after is None:
        return _result("unknown", "post-hotplug PCI timestamp missing", path)
    fielddiag = _cmd(data, _is_fielddiag_command, phase="after-hotplug")
    if fielddiag is None or fielddiag["exit"] != 0:
        return _result("unknown", "fresh post-hotplug FieldDiag capture missing", path)
    if not _fresh(fielddiag, after, int(plan.get("fielddiag_max_age_seconds", 600))):
        return _result("fail", "FieldDiag capture is stale relative to post-hotplug state", path)
    if re.search(r"(?i)FAIL|ERROR|unavailable", fielddiag["stdout"]):
        return _result("fail", "FieldDiag reports failed or unavailable CX7", path)
    serial = plan.get("device_serial")
    if not isinstance(serial, str) or not serial or serial not in fielddiag["stdout"]:
        return _result("unknown", "FieldDiag output is not bound to the planned CX7 serial", path)
    return _posthotplug_traffic(data, path, plan)


def _is_fielddiag_command(argv: list[str]) -> bool:
    return Path(argv[0]).name.lower() == "fielddiag" or (
        Path(argv[0]).name == "nvsm" and "show" in argv and "fielddiag" in [x.lower() for x in argv])


def _posthotplug_traffic(data: dict[str, Any], path: Path, plan: dict[str, Any]) -> dict[str, Any] | None:
    rates = [_cmd(data, lambda a: "ib_write_bw" in a, phase=phase)
             for phase in ("after-hotplug:local-to-peer", "after-hotplug:peer-to-local")]
    if any(row is None or row["exit"] != 0 for row in rates):
        return _result("unknown", "post-hotplug bidirectional RDMA traffic is incomplete", path)
    min_rate = _finite(plan.get("minimum_gbps"))
    observed = [_bandwidth(row["stdout"]) for row in rates if row is not None]
    if min_rate is None or any(rate is None for rate in observed):
        return _result("unknown", "predeclared post-hotplug rate bound or measured traffic missing", path)
    if any(rate < min_rate for rate in observed if rate is not None):
        return _result("fail", "post-hotplug link throughput fell below predeclared minimum", path)
    nccl, error = _need(data, path, "post-hotplug NCCL collective", lambda a: "all_reduce_perf" in a, phase="after-hotplug")
    if error:
        return error
    assert nccl is not None
    if not _nccl_completed(nccl["stdout"]):
        return _result("fail", "post-hotplug NCCL collectives failed correctness/performance output", path)
    rollback = _cmd(data, lambda a: Path(a[0]).name == "lspci" and "-D" in a, phase="rollback")
    bdf = str(plan.get("bdf", "")).lower()
    netdev = plan.get("netdev")
    rollback_link = _cmd(data, lambda a: Path(a[0]).name == "ethtool" and "-i" not in a
                         and isinstance(netdev, str) and netdev in a, phase="rollback")
    if (rollback is None or rollback["exit"] != 0 or not rollback["stdout"].strip()
            or not bdf or bdf not in rollback["stdout"].lower()
            or rollback_link is None or rollback_link["exit"] != 0
            or not re.search(r"(?im)^\s*Link detected:\s*yes\s*$", rollback_link["stdout"])):
        return _result("unknown", "OEM recovery/rollback readback missing", path)
    return None


def _fresh(left: dict[str, Any], right: dict[str, Any], max_age: int) -> bool:
    try:
        a = datetime.fromisoformat(left["captured_at"].replace("Z", "+00:00"))
        b = datetime.fromisoformat(right["captured_at"].replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return False
    age = abs((a - b).total_seconds())
    return 0 < max_age <= 3600 and age <= max_age


def _rdma_asymmetry(data: dict[str, Any], path: Path) -> dict[str, Any]:
    plan, error = _capture_plan(data, path)
    if error:
        return error
    assert plan is not None
    scenarios, tolerance, error = _asymmetry_plan(plan, path)
    if error:
        return error
    assert scenarios is not None and tolerance is not None
    observed: dict[str, dict[str, float]] = {}
    approval = _plan_approval(data, path, plan)
    if approval:
        return approval
    identity_error = _rdma_stack_identity(data, path, plan)
    if identity_error:
        return identity_error
    for scenario in scenarios:
        rates, error = _asymmetry_pair(data, scenario, path)
        if error:
            return error
        assert rates is not None
        observed[scenario] = rates
    cable = _cmd(data, lambda a: Path(a[0]).name == "mlxlink" and "-m" in a)
    if cable is None or cable["exit"] != 0 or not re.search(r"(?im)^PN:\s*\S+", cable["stdout"]):
        return _result("unknown", "exact DAC/cable part-number inventory is missing", path)
    for scenario, directions in observed.items():
        ratio = max(directions.values()) / min(directions.values())
        if ratio > tolerance:
            return _result("fail", f"directional RDMA bandwidth ratio {ratio:.3f} exceeds predeclared bound in {scenario}", path)
    return _result("pass", "bidirectional cold/reboot/hotplug throughput compared against a predeclared ratio with cable inventory", path)


def _rdma_stack_identity(data: dict[str, Any], path: Path, plan: dict[str, Any]) -> dict[str, Any] | None:
    hosts = plan.get("hosts")
    if not isinstance(hosts, list) or len(hosts) != 2 or any(not isinstance(h, str) or not h for h in hosts):
        return _result("unknown", "two named OEM hosts are required for tuple matching", path)
    tuples: dict[str, dict[str, str]] = {}
    for host in hosts:
        dmi = _cmd(data, lambda a: a[:3] == ["ssh", host, "dmidecode"])
        kernel = _cmd(data, lambda a: a[:3] == ["ssh", host, "uname"])
        fw = _cmd(data, lambda a: a[:3] == ["ssh", host, "ethtool"])
        if any(item is None for item in (dmi, kernel, fw)):
            return _result("unknown", f"OEM/kernel/ConnectX firmware tuple missing for {host}", path)
        assert dmi is not None and kernel is not None and fw is not None
        if any(item["exit"] != 0 for item in (dmi, kernel, fw)):
            return _result("fail", f"remote identity query failed for {host}", path)
        manufacturer = re.search(r"(?im)^Manufacturer:\s*(.+)$", dmi["stdout"])
        product = re.search(r"(?im)^Product Name:\s*(.+)$", dmi["stdout"])
        bios = re.search(r"(?im)^BIOS Version:\s*(.+)$", dmi["stdout"])
        release = kernel["stdout"].strip()
        version = re.search(r"(?im)^firmware-version:\s*(\S+)", fw["stdout"])
        if not all((manufacturer, product, bios, release, version)):
            return _result("unknown", f"complete OEM/BIOS/kernel/CX7 firmware tuple missing for {host}", path)
        assert manufacturer is not None and product is not None and bios is not None and version is not None
        tuples[host] = {"manufacturer": manufacturer.group(1).strip(), "product": product.group(1).strip(),
                        "bios": bios.group(1).strip(), "kernel": release,
                        "firmware": version.group(1)}
    declared = plan.get("host_tuples")
    if declared != tuples:
        return _result("fail", "observed peer OEM/BIOS/kernel/CX7 firmware tuples differ from pinned plan", path)
    refs, ref_error = _vendor_refs(data, {f"{host}:{key}": value for host, values in tuples.items() for key, value in values.items()})
    if ref_error or refs is None:
        return _result("unknown", ref_error or "OEM compatibility reference missing", path)
    return None


def _asymmetry_plan(plan: dict[str, Any], path: Path) -> tuple[list[str] | None, float | None, dict[str, Any] | None]:
    scenarios = plan.get("scenarios")
    tolerance = _finite(plan.get("max_directional_ratio"))
    required = {"cold", "reboot-individual", "reboot-sequential", "hotplug"}
    if (not isinstance(scenarios, list) or set(scenarios) != required or len(scenarios) != len(required)
            or tolerance is None or tolerance < 1):
        return None, None, _result("unknown", "exact cold, individual/sequential reboot, hotplug cases and predeclared ratio are required", path)
    return sorted(required), tolerance, None


def _plan_approval(data: dict[str, Any], path: Path, plan: dict[str, Any]) -> dict[str, Any] | None:
    anchor = data.get("_trusted_plan_sha256")
    if not isinstance(anchor, str) or not re.fullmatch(r"[0-9a-f]{64}", anchor):
        return _result("unknown", "trusted human approval anchor was not supplied separately from the evidence bundle", path)
    digest = hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if anchor != digest:
        return _result("fail", "trusted approval anchor does not bind this exact experiment plan", path)
    return None


def _asymmetry_pair(data: dict[str, Any], scenario: str, path: Path) -> tuple[dict[str, float] | None, dict[str, Any] | None]:
    observed: dict[str, float] = {}
    for direction in ("spark_to_gx10", "gx10_to_spark"):
        phase = f"{scenario}:{direction}"
        row = _cmd(data, lambda a: "ib_write_bw" in a, phase=phase)
        if row is None:
            return None, _result("unknown", f"missing raw {direction} benchmark for {scenario}", path)
        if row["exit"] != 0:
            return None, _result("fail", f"{direction} benchmark failed during {scenario}", path)
        rate = _bandwidth(row["stdout"])
        if rate is None or rate <= 0:
            return None, _result("fail", f"{direction} reported invalid bandwidth during {scenario}", path)
        observed[direction] = rate
    return observed, None


def _dual_spark(data: dict[str, Any], path: Path) -> dict[str, Any]:
    plan, error = _capture_plan(data, path)
    if error:
        return error
    assert plan is not None
    hosts = plan.get("hosts")
    cycles = plan.get("cycles")
    if not isinstance(hosts, list) or len(hosts) != 2 or len(set(hosts)) != 2 or type(cycles) is not int or cycles < 2:
        return _result("unknown", "two distinct GB10 hosts and at least two predeclared repeated observations are required", path)
    if not isinstance(plan.get("oem_power_procedure"), str) or not plan["oem_power_procedure"].strip():
        return _result("unknown", "OEM clean-shutdown procedure reference is missing", path)
    if not isinstance(plan.get("model_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", plan["model_sha256"]):
        return _result("unknown", "pinned model digest is required for matched repeated workload measurements", path)
    if not isinstance(plan.get("input_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", plan["input_sha256"]):
        return _result("unknown", "pinned workload input digest is required", path)
    approval = _plan_approval(data, path, plan)
    if approval:
        return approval
    identity_error = _rdma_stack_identity(data, path, plan)
    if identity_error:
        return identity_error
    records, error = _power_records(data, path, hosts, cycles, plan)
    if error:
        return error
    assert records is not None
    return _power_compare(records, path, hosts, cycles)


def _power_records(data: dict[str, Any], path: Path, hosts: list[Any], cycles: int, plan: dict[str, Any]
                   ) -> tuple[dict[tuple[str, int, str], dict[str, float]] | None, dict[str, Any] | None]:
    records: dict[tuple[str, int, str], dict[str, float]] = {}
    for row in data["commands"]:
        if row.get("phase") not in {"before-reset", "after-reset", "control"}:
            continue
        host = row.get("host")
        cycle = row.get("cycle")
        phase = row.get("phase")
        if host not in hosts or type(cycle) is not int or cycle < 1 or cycle > cycles:
            return None, _result("fail", "power-reset capture host/cycle metadata is outside plan", path)
        if row["exit"] != 0:
            return None, _result("fail", f"read-only measurement failed for {host} cycle {cycle} {phase}", path)
        value, parse_error = _json_stdout(row, "power/workload sample")
        if parse_error or not isinstance(value, dict):
            continue
        needed = ("power_w", "clock_mhz", "throughput_tokens_s", "link_gbps")
        if any(_finite(value.get(key)) is None for key in needed):
            continue
        if (value.get("model_sha256") != plan.get("model_sha256")
                or value.get("input_sha256") != plan.get("input_sha256")
                or value.get("concurrency") != plan.get("concurrency")):
            return None, _result("fail", "before/after/control workload identity differs from the pinned model/input/concurrency", path)
        records[(host, cycle, phase)] = {key: float(value[key]) for key in needed}
    return records, None


def _power_compare(records: dict[tuple[str, int, str], dict[str, float]], path: Path,
                   hosts: list[Any], cycles: int) -> dict[str, Any]:
    delta_fields = ("throughput_tokens_s", "power_w", "clock_mhz", "link_gbps")
    deltas: dict[str, list[tuple[float, float]]] = {key: [] for key in delta_fields}
    for host in hosts:
        for cycle in range(1, cycles + 1):
            before, after, control = (records.get((host, cycle, phase)) for phase in ("before-reset", "after-reset", "control"))
            if before is None or after is None or control is None:
                return _result("unknown", f"paired before/after/control measurements missing: {host} cycle {cycle}", path)
            if before["throughput_tokens_s"] <= 0 or after["throughput_tokens_s"] <= 0 or control["throughput_tokens_s"] <= 0:
                return _result("fail", f"non-positive workload measurement: {host} cycle {cycle}", path)
            # Report measured A/B/control deltas; the card defines no universal recovery threshold.
            for key in delta_fields:
                deltas[key].append((after[key] - before[key], control[key] - before[key]))
    rendered = []
    for key, pairs in deltas.items():
        reset_values = ",".join(f"{after:+.3f}" for after, _ in pairs)
        control_values = ",".join(f"{control:+.3f}" for _, control in pairs)
        rendered.append(f"{key} after-before=[{reset_values}] control-before=[{control_values}]")
    return _result("pass", "; ".join(rendered) + "; observational only, no causal claim", path)


def _kv_quant(data: dict[str, Any], path: Path) -> dict[str, Any]:
    plan, error = _capture_plan(data, path)
    if error:
        return error
    assert plan is not None
    error = _kv_contract(plan, path)
    if error:
        return error
    identity, error = _identity(data, path)
    if error:
        return error
    assert identity is not None
    supported, support_error = _kv_vendor_support(data, path, identity, plan)
    if support_error or supported is None:
        status = "fail" if support_error and support_error.startswith("source explicitly denies") else "unknown"
        return _result(status, support_error or "primary-source backend support evidence missing", path)
    snapshots, error = _kv_snapshots(data, path)
    if error:
        return error
    assert snapshots is not None
    if any(not snapshots.get(phase) for phase in ("baseline", "quantized")):
        return _result("unknown", "host/cgroup/RSS/framework metrics are not paired with both KV modes", path)
    results, error = _kv_runs(data, path, plan)
    if error:
        return error
    assert results is not None
    modes = {r.get("kv_mode") for r in results}
    if len(modes) != 2 or plan.get("reference_max_abs_error") is None:
        return _result("unknown", "baseline and quantized KV modes plus reference tolerance required", path)
    if any(r["max_abs_error"] > plan["reference_max_abs_error"] for r in results):
        return _result("fail", "KV quant output differs from reference beyond predeclared tolerance", path)
    return _result("pass", "separate host/cgroup/RSS/KV metrics and matched correctness/prefill/decode outcomes parsed", path)


def _kv_vendor_support(data: dict[str, Any], path: Path, identity: dict[str, str],
                       plan: dict[str, Any]) -> tuple[list[dict[str, str]] | None, str | None]:
    subject = {key: identity[key] for key in ("Manufacturer", "Product Name", "Kernel")}
    subject["backend"] = plan["backend"]
    refs, error = _vendor_refs(data, subject)
    if error or refs is None:
        return None, error or "primary-source GB10/backend compatibility reference missing"
    text = "\n".join(ref["text"] for ref in refs).casefold()
    backend = re.escape(plan["backend"].casefold())
    if "gb10" not in text or plan["backend"].casefold() not in text:
        return None, "primary-source reference does not bind the GB10 subject and exact backend"
    denial = re.search(rf"{backend}.{{0,60}}\b(unsupported|not supported|incompatible)\b", text)
    if denial:
        return None, f"source explicitly denies support for backend {plan['backend']} on the captured GB10 tuple"
    support_patterns = (rf"\b(?:backend\s+{backend}|{backend}\s+backend)\b.{{0,50}}\b(supported|validated|compatible)\b",
                        rf"\bgb10\b.{{0,80}}\b{backend}\b.{{0,50}}\b(supported|validated|compatible)\b")
    if not any(re.search(pattern, text) for pattern in support_patterns):
        return None, "primary-source excerpt does not directly connect GB10 and exact backend support/compatibility"
    return refs, None


def _kv_contract(plan: dict[str, Any], path: Path) -> dict[str, Any] | None:
    strings = ("model_sha256", "backend", "baseline_kv_mode", "quantized_kv_mode", "input_sha256")
    if any(not isinstance(plan.get(k), str) or not plan[k].strip() for k in strings) or any(
        type(plan.get(k)) is not int or plan[k] <= 0 for k in ("context_tokens", "concurrency")):
        return _result("unknown", "exact model/backend/KV-mode/context/input contract is incomplete", path)
    if plan["baseline_kv_mode"] == plan["quantized_kv_mode"]:
        return _result("fail", "baseline and quantized KV modes must differ", path)
    return None


def _kv_snapshots(data: dict[str, Any], path: Path) -> tuple[dict[str, list[dict[str, float]]] | None, dict[str, Any] | None]:
    metric_rows = [r for r in data["commands"] if r["exit"] == 0 and "curl" in r["argv"] and "/metrics" in " ".join(r["argv"])]
    if len(metric_rows) < 2:
        return None, _result("unknown", "raw Prometheus metrics captures before/after quantization are missing", path)
    snapshots: dict[str, list[dict[str, float]]] = {"baseline": [], "quantized": []}
    for row in metric_rows:
        phase = row.get("phase")
        if phase not in snapshots:
            return None, _result("unknown", "raw Prometheus sample lacks a baseline/quantized phase binding", path)
        values: dict[str, float] = {}
        for line in row["stdout"].splitlines():
            if line.startswith("#"):
                continue
            m = re.fullmatch(r"([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{[^\n]*\})?\s+([^\s]+)(?:\s+\d+)?", line)
            if not m:
                continue
            name = m.group(1)
            if name in {"process_resident_memory_bytes", "container_memory_working_set_bytes",
                        "node_memory_MemAvailable_bytes", "node_memory_SwapFree_bytes",
                        "vllm_kv_cache_usage_perc", "llamacpp_kv_cache_bytes"}:
                number = _parsed_number(m.group(2))
                if number is not None:
                    values[name] = number
        required = {"process_resident_memory_bytes", "container_memory_working_set_bytes",
                    "node_memory_MemAvailable_bytes", "node_memory_SwapFree_bytes"}
        if not required.issubset(values) or not any(k in values for k in ("vllm_kv_cache_usage_perc", "llamacpp_kv_cache_bytes")):
            return None, _result("unknown", "RSS, cgroup, host available/swap and framework KV counters must remain separate", path)
        snapshots[phase].append(values)
    return snapshots, None


def _kv_runs(data: dict[str, Any], path: Path, plan: dict[str, Any]
             ) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None]:
    contract = ("model_sha256", "backend", "kv_mode", "context_tokens", "concurrency", "input_sha256")
    workloads = [r for r in data["commands"] if Path(r["argv"][0]).name == "cat"
                 and r.get("phase") in {"baseline", "quantized"}]
    if {row.get("phase") for row in workloads} != {"baseline", "quantized"}:
        return None, _result("unknown", "matched baseline and quantized workload outputs are missing", path)
    results: list[dict[str, Any]] = []
    for row in workloads:
        if row["exit"] != 0:
            return None, _result("fail", "KV quant benchmark command returned nonzero", path)
        value, parse_error = _json_stdout(row, "KV quant benchmark")
        if parse_error or not isinstance(value, dict):
            return None, _result("unknown", parse_error or "benchmark result malformed", path)
        expected = {key: plan[key] for key in contract if key != "kv_mode"}
        expected["kv_mode"] = plan["baseline_kv_mode"] if row["phase"] == "baseline" else plan["quantized_kv_mode"]
        if any(value.get(k) != expected.get(k) for k in contract):
            return None, _result("fail", "baseline/quant benchmark contract differs from predeclared model/backend/context/input", path)
        for metric in ("prefill_tokens_s", "decode_tokens_s", "correct_tokens", "total_tokens", "max_abs_error"):
            if _finite(value.get(metric)) is None:
                return None, _result("unknown", f"benchmark lacks measured {metric}", path)
        if value["correct_tokens"] != value["total_tokens"] or value["total_tokens"] <= 0:
            return None, _result("fail", "quantized generation token correctness failed", path)
        results.append(value)
    return results, None


def _memory_soak(data: dict[str, Any], path: Path) -> dict[str, Any]:
    plan, error = _capture_plan(data, path)
    if error:
        return error
    assert plan is not None
    approval = _plan_approval(data, path, plan)
    if approval:
        return approval
    duration = plan.get("soak_seconds")
    if type(duration) is not int or duration < 7200:
        return _result("unknown", "predeclared multihour soak must be at least 7200 seconds", path)
    max_gap = plan.get("max_sample_gap_seconds")
    if type(max_gap) is not int or max_gap <= 0:
        return _result("unknown", "predeclared maximum sample gap missing", path)
    parsed, error = _memory_samples(data, path)
    if error:
        return error
    assert parsed is not None
    return _memory_recovery_gate(parsed, path, duration, max_gap)


def _memory_samples(data: dict[str, Any], path: Path) -> tuple[list[tuple[dict[str, Any], datetime, dict[str, Any]]] | None, dict[str, Any] | None]:
    rows = [r for r in data["commands"] if r.get("phase") in
            {"soak", "client-terminated", "server-terminated", "control"}]
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        sample = row.get("sample")
        if not isinstance(sample, str) or not sample:
            return None, _result("unknown", "native memory observations lack sample grouping metadata", path)
        groups.setdefault((row["phase"], sample), []).append(row)
    if len(groups) < 7:
        return None, _result("unknown", "memory time series and ordered recovery/control observations missing", path)
    samples: list[tuple[dict[str, Any], datetime, dict[str, Any]]] = []
    for (phase, _sample), captures in groups.items():
        parsed, error = _parse_memory_group(data, path, phase, captures)
        if error:
            return None, error
        assert parsed is not None
        samples.append(parsed)
    samples.sort(key=lambda entry: entry[1])
    return samples, None


def _parse_memory_group(data: dict[str, Any], path: Path, phase: str, captures: list[dict[str, Any]]) -> tuple[tuple[dict[str, Any], datetime, dict[str, Any]] | None, dict[str, Any] | None]:
        free = next((r for r in captures if Path(r["argv"][0]).name == "free" and "-b" in r["argv"]), None)
        psi = next((r for r in captures if Path(r["argv"][0]).name == "cat" and "/proc/pressure/memory" in r["argv"]), None)
        processes = [r for r in captures if Path(r["argv"][0]).name == "ps" and "-p" in r["argv"]]
        if free is None or psi is None or len(processes) < 2:
            return None, _result("unknown", "each memory sample needs native free, PSI, client and server process captures", path)
        if free["exit"] != 0 or psi["exit"] != 0:
            return None, _result("fail", f"native memory/process query failed in {phase}", path)
        mem = re.search(r"(?im)^Mem:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", free["stdout"])
        swap = re.search(r"(?im)^Swap:\s+(\d+)\s+(\d+)\s+(\d+)\s*$", free["stdout"])
        some = re.search(r"(?im)^some\s+avg10=([\d.]+)", psi["stdout"])
        if mem is None or swap is None or some is None:
            return None, _result("unknown", "native free/PSI output lacks available/swap/pressure counters", path)
        assert mem is not None and swap is not None and some is not None
        parsed_processes: list[tuple[int, str, int, str]] = []
        for process in processes:
            pid_arg = process["argv"][process["argv"].index("-p") + 1] if "-p" in process["argv"] else ""
            match = re.search(r"(?m)^\s*(\d+)\s+(\S+)\s+(\d+)\s+(.+?)\s*$", process["stdout"])
            if not pid_arg.isdigit():
                return None, _result("fail", "ps command did not request a numeric PID", path)
            expected_gone = ((phase == "client-terminated" and int(pid_arg) == int(data.get("experiment_plan", {}).get("client_pid", -1)))
                             or (phase == "server-terminated" and int(pid_arg) in {
                                 int(data.get("experiment_plan", {}).get("client_pid", -1)),
                                 int(data.get("experiment_plan", {}).get("rpc_server_pid", -1))}))
            if (match is None and expected_gone and process["exit"] == 1
                    and not process["stdout"].strip() and not process["stderr"].strip()):
                parsed_processes.append((int(pid_arg), "X", 0, ""))
                continue
            if (process["exit"] != 0 or match is None or int(match.group(1)) != int(pid_arg)
                    or not match.group(4).strip()):
                return None, _result("fail", "ps process identity output does not match requested PID", path)
            parsed_processes.append((int(match.group(1)), match.group(2), int(match.group(3)), match.group(4).strip()))
        if len({p[0] for p in parsed_processes}) != 2:
            return None, _result("fail", "client and RPC server PID captures are not distinct", path)
        pids = {pid: state for pid, state, _rss, _start in parsed_processes}
        starts = {pid: start for pid, _state, _rss, start in parsed_processes}
        server_pid = int(data.get("experiment_plan", {}).get("rpc_server_pid", -1))
        client_pid = int(data.get("experiment_plan", {}).get("client_pid", -1))
        if server_pid not in pids or client_pid not in pids or server_pid == client_pid:
            return None, _result("unknown", "predeclared client/server PIDs are absent from native process observations", path)
        rss = sum(p[2] for p in parsed_processes) * 1024
        state_map = {pid: state for pid, state in pids.items()}
        value = {"mem_available_bytes": int(mem.group(6)), "swap_free_bytes": int(swap.group(3)),
                 "psi_memory_some_avg10": float(some.group(1)), "rss_bytes": rss,
                 "rpc_server_pid": server_pid, "rpc_server_state": "stopped" if state_map[server_pid] in {"Z", "X"} else "running",
                 "rpc_server_start": starts[server_pid], "client_pid": client_pid,
                 "client_state": "stopped" if state_map[client_pid] in {"Z", "X"} else "running",
                 "client_start": starts[client_pid]}
        latest = max((r for r in captures), key=lambda r: r["captured_at"])
        return (latest, datetime.fromisoformat(latest["captured_at"].replace("Z", "+00:00")), value), None


def _memory_recovery_gate(samples: list[tuple[dict[str, Any], datetime, dict[str, Any]]],
                          path: Path, duration: int, max_gap: int) -> dict[str, Any]:
    soak_samples = [stamp for row, stamp, _ in samples if row.get("phase") == "soak"]
    if (len(soak_samples) < 3 or (soak_samples[-1] - soak_samples[0]).total_seconds() < duration
            or any((b-a).total_seconds() > max_gap for a,b in zip(soak_samples, soak_samples[1:]))):
        return _result("unknown", "multihour time-series coverage does not span the declared soak", path)
    pids = {value["rpc_server_pid"] for _, _, value in samples}
    if len(pids) != 1:
        return _result("fail", "RPC server identity changed during the soak", path)
    live_server_starts = {value["rpc_server_start"] for _, _, value in samples
                          if value["rpc_server_state"] == "running" and value["rpc_server_start"]}
    live_client_starts = {value["client_start"] for _, _, value in samples
                          if value["client_state"] == "running" and value["client_start"]}
    if len(live_server_starts) != 1 or len(live_client_starts) != 1:
        return _result("fail", "server/client start times changed or were never established; PID reuse cannot be excluded", path)
    client_closed = [(stamp,value) for row,stamp,value in samples if row.get("phase")=="client-terminated"]
    server_closed = [(stamp,value) for row,stamp,value in samples if row.get("phase")=="server-terminated"]
    if not client_closed or not server_closed:
        return _result("unknown", "ordered client-then-server termination observations missing", path)
    client_stamp, client_sample = client_closed[0]
    server_stamp, server_sample = server_closed[0]
    if not client_stamp < server_stamp:
        return _result("fail", "RPC server terminated before the client in recovery sequence", path)
    if client_sample["client_state"] != "stopped" or client_sample["rpc_server_state"] != "running":
        return _result("fail", "client exit was not measured while the identified RPC server remained alive", path)
    if server_sample["rpc_server_state"] != "stopped":
        return _result("fail", "RPC server termination was not observed", path)
    if server_sample["mem_available_bytes"] <= client_sample["mem_available_bytes"]:
        return _result("fail", "available UMA did not increase after RPC server termination", path)
    control = [(stamp, value) for row, stamp, value in samples if row.get("phase") == "control"]
    if (len(control) < 3 or any(value["rpc_server_state"] != "running" for _, value in control)
            or (control[-1][0] - control[0][0]).total_seconds() < duration):
        return _result("unknown", "healthy RPC-server control series missing", path)
    return _result("pass", "multi-hour UMA/swap/PSI and exact RPC PID recovery/control series recomputed", path)


def _ota_tuple(data: dict[str, Any], path: Path) -> dict[str, Any]:
    plan, error = _capture_plan(data, path)
    if error:
        return error
    assert plan is not None
    approval = _plan_approval(data, path, plan)
    if approval:
        return approval
    identity, error = _identity(data, path)
    if error:
        return error
    assert identity is not None
    phases, error = _ota_observations(data, path)
    if error:
        return error
    assert phases is not None
    comparison = _ota_compare(data, path, plan, phases, identity)
    if comparison["status"] != "pass":
        return comparison
    return _ota_soak(data, path, plan)


def _ota_soak(data: dict[str, Any], path: Path, plan: dict[str, Any]) -> dict[str, Any]:
    spec, error = _ota_soak_contract(plan, path)
    if error:
        return error
    assert spec is not None
    duration, max_gap = spec["duration_seconds"], spec["max_sample_gap_seconds"]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in data["commands"]:
        if row.get("phase") == "workload-soak":
            sample = row.get("sample")
            if not isinstance(sample, str) or not sample:
                return _result("unknown", "OTA workload-soak rows lack sample grouping", path)
            grouped.setdefault(sample, []).append(row)
    if len(grouped) < 2:
        return _result("unknown", "OTA needs repeated native memory/PSI/workload/PID samples", path)
    observations: list[tuple[datetime, int, str]] = []
    for sample, rows in grouped.items():
        observation, error = _ota_soak_sample(rows, sample, spec, path)
        if error:
            return error
        assert observation is not None
        observations.append(observation)
    observations.sort(key=lambda value: value[0])
    if len({observation[2] for observation in observations}) != 1:
        return _result("fail", "OTA workload PID start identity changed during soak", path)
    if ((observations[-1][0] - observations[0][0]).total_seconds() < duration
            or any((right[0] - left[0]).total_seconds() > max_gap for left, right in zip(observations, observations[1:]))):
        return _result("unknown", "OTA workload soak does not span its declared duration/cadence", path)
    return _result("pass", "native MemAvailable/PSI plus completed planned workload and live PID were sampled across declared OTA soak", path)


def _ota_soak_contract(plan: dict[str, Any], path: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    spec = plan.get("workload_soak")
    if not isinstance(spec, dict):
        return None, _result("unknown", "predeclared OTA workload-soak contract missing", path)
    argv, model, input_digest, pid = (spec.get(key) for key in ("argv", "model_sha256", "input_sha256", "pid"))
    duration, max_gap = spec.get("duration_seconds"), spec.get("max_sample_gap_seconds")
    valid_argv = isinstance(argv, list) and bool(argv) and all(isinstance(arg, str) and arg for arg in argv)
    valid_digests = all(isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest)
                        for digest in (model, input_digest))
    if (not valid_argv or not valid_digests or type(pid) is not int or pid <= 0
            or type(duration) is not int or duration <= 0 or type(max_gap) is not int or max_gap <= 0):
        return None, _result("unknown", "OTA workload soak needs exact argv/model/input/PID, duration, and cadence", path)
    return spec, None


def _ota_soak_sample(rows: list[dict[str, Any]], sample: str, spec: dict[str, Any],
                     path: Path) -> tuple[tuple[datetime, int, str] | None, dict[str, Any] | None]:
    argv, pid, max_gap = spec["argv"], spec["pid"], spec["max_sample_gap_seconds"]
    selected = (
        next((row for row in rows if Path(row["argv"][0]).name == "free" and "-b" in row["argv"]), None),
        next((row for row in rows if Path(row["argv"][0]).name == "cat" and "/proc/pressure/memory" in row["argv"]), None),
        next((row for row in rows if row["argv"] == argv), None),
        next((row for row in rows if Path(row["argv"][0]).name == "ps" and row["argv"][:3] == ["ps", "-p", str(pid)]), None),
    )
    if any(item is None for item in selected):
        return None, _result("unknown", f"OTA soak sample {sample} lacks native free/PSI/workload/ps observations", path)
    free, psi, workload, process = selected
    assert free is not None and psi is not None and workload is not None and process is not None
    if any(row["exit"] != 0 for row in (free, psi, workload, process)):
        return None, _result("fail", f"native OTA soak command failed in sample {sample}", path)
    try:
        stamps = [datetime.fromisoformat(row["captured_at"].replace("Z", "+00:00")) for row in rows]
    except (TypeError, ValueError):
        return None, _result("unknown", f"OTA soak sample {sample} has invalid command times", path)
    if (max(stamps) - min(stamps)).total_seconds() > max_gap:
        return None, _result("unknown", f"OTA soak sample {sample} observations exceed the planned capture interval", path)
    memory = re.search(r"(?im)^Mem:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", free["stdout"])
    pressure = re.search(r"(?im)^some\s+avg10=([\d.]+)", psi["stdout"])
    observed_process = re.search(r"(?m)^\s*(\d+)\s+(\S+)\s+(\d+)\s+(.+?)\s*$", process["stdout"])
    result, parse_error = _json_stdout(workload, "OTA workload soak")
    pressure_value = _parsed_number(pressure.group(1)) if pressure else None
    if (memory is None or pressure_value is None or observed_process is None
            or parse_error or not isinstance(result, dict)):
        return None, _result("unknown", f"OTA soak sample {sample} lacks parseable memory/PSI/PID/workload values", path)
    if int(observed_process.group(1)) != pid or observed_process.group(2) in {"Z", "X"}:
        return None, _result("fail", "predeclared OTA soak workload PID is absent or terminated", path)
    if (result.get("pid") != pid or result.get("model_sha256") != spec["model_sha256"]
            or result.get("input_sha256") != spec["input_sha256"]):
        return None, _result("fail", "OTA soak workload output does not bind the planned PID/model/input", path)
    requests, completed = _finite(result.get("requests")), _finite(result.get("completed"))
    if requests is None or completed is None or requests <= 0 or completed != requests:
        return None, _result("fail", "OTA soak workload requests did not complete", path)
    stamp = datetime.fromisoformat(workload["captured_at"].replace("Z", "+00:00"))
    return (stamp, int(memory.group(6)), observed_process.group(4).strip()), None


def _ota_observations(data: dict[str, Any], path: Path) -> tuple[dict[str, dict[str, Any]] | None, dict[str, Any] | None]:
    needed = ("ota_release", "dgx_os_build", "kernel_release", "loaded_driver", "disk_driver",
              "cuda_runtime", "ec_version", "carveout_bytes")
    phases = {p: {} for p in ("before-update", "after-update", "rollback")}
    for phase in phases:
        for row in data["commands"]:
            if row.get("phase") == phase and row["exit"] == 0:
                phases[phase].update(_ota_fields_from_row(row))
    for phase, values in phases.items():
        if any(k not in values for k in needed):
            return None, _result("unknown", f"effective firmware/software tuple incomplete in {phase}", path)
    return phases, None


def _ota_fields_from_row(row: dict[str, Any]) -> dict[str, Any]:
    text, command = row["stdout"], row["argv"]
    if command[:2] == ["uname", "-r"]:
        return {"kernel_release": text.strip()}
    if Path(command[0]).name == "cat" and "/proc/driver/nvidia/version" in command:
        match = re.search(r"(?im)^NVRM version:.*?Module\s+(\S+)", text)
        return {"loaded_driver": match.group(1)} if match else {}
    if Path(command[0]).name == "modinfo" and command[-2:] == ["version", "nvidia"]:
        values = text.strip().splitlines()
        return {"disk_driver": values[-1]} if values and re.fullmatch(r"[0-9][A-Za-z0-9.+:~-]*", values[-1]) else {}
    if Path(command[0]).name == "dpkg-query" and any("cuda-cudart" in arg for arg in command):
        match = re.search(r"(?im)^cuda-cudart(?:-[\w.+-]+)?\s+([0-9][A-Za-z0-9.+:~-]*)\s*$", text)
        return {"cuda_runtime": match.group(1)} if match else {}
    if Path(command[0]).name == "nvsm" and "show" in command:
        return _ota_nvsm_fields(text)
    return {}


def _ota_nvsm_fields(text: str) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for key, pattern in {
        "ota_release": r"(?im)^OTA Release:\s*(\S+)",
        "dgx_os_build": r"(?im)^DGX OS Build:\s*(\S+)",
        "ec_version": r"(?im)^EC Version:\s*(\S+)",
        "carveout_bytes": r"(?im)^Carveout Bytes:\s*(\d+)",
    }.items():
        match = re.search(pattern, text)
        if match:
            fields[key] = int(match.group(1)) if key == "carveout_bytes" else match.group(1)
    return fields


def _ota_compare(data: dict[str, Any], path: Path, plan: dict[str, Any],
                 phases: dict[str, dict[str, Any]], identity: dict[str, str]) -> dict[str, Any]:
    needed = ("ota_release", "dgx_os_build", "kernel_release", "loaded_driver", "disk_driver",
              "cuda_runtime", "ec_version", "carveout_bytes")
    compatible_tuple = {**identity, **{k: str(phases["after-update"][k]) for k in needed}}
    refs, ref_error = _vendor_refs(data, compatible_tuple)
    if ref_error or refs is None:
        return _result("unknown", ref_error or "release compatibility evidence unavailable", path)
    if phases["before-update"] == phases["after-update"]:
        return _result("fail", "post-update effective tuple did not change from pre-update tuple", path)
    if phases["rollback"] != phases["before-update"]:
        return _result("fail", "rollback tuple does not restore the exact prior stack", path)
    supported = plan.get("supported_tuple")
    if not isinstance(supported, dict) or set(supported) != set(needed):
        return _result("unknown", "complete predeclared OEM-supported effective tuple is missing", path)
    if any(phases["after-update"].get(k) != v for k, v in supported.items()):
        return _result("fail", "effective post-OTA tuple differs from predeclared OEM-supported tuple", path)
    return _result("pass", "pre/post/rollback kernel, driver, CUDA, OTA/build, EC and carveout tuple compared to source", path)


def _recovery_apt(data: dict[str, Any], path: Path) -> dict[str, Any]:
    plan, error = _capture_plan(data, path)
    if error:
        return error
    assert plan is not None
    required = ("last_kernel", "last_driver", "last_package", "console_route", "recovery_media_path",
                "recovery_media_sha256", "oem_recovery_url")
    if any(not isinstance(plan.get(k), str) or not plan[k].strip() for k in required):
        return _result("unknown", "recovery runbook lacks kernel/driver/package, external console and OEM media identity", path)
    if not re.fullmatch(r"[0-9a-f]{64}", plan["recovery_media_sha256"]):
        return _result("fail", "OEM recovery media digest malformed", path)
    error = _recovery_packages(data, path, plan)
    if error:
        return error
    error = _recovery_access(data, path)
    if error:
        return error
    error = _recovery_media(data, path, plan)
    if error:
        return error
    return _result("pass", "last package tuple, hashed OEM media path, external console and recovery/rollback/RMA runbook parsed", path)


def _recovery_packages(data: dict[str, Any], path: Path, plan: dict[str, Any]) -> dict[str, Any] | None:
    sources = data.get("vendor_sources")
    refs, ref_error = _vendor_refs(data, {"kernel": plan["last_kernel"], "driver": plan["last_driver"],
                                           "package": plan["last_package"]})
    if ref_error or refs is None:
        return _result("unknown", ref_error or "OEM media compatibility source missing", path)
    if not any(ref["url"] == plan["oem_recovery_url"] for ref in refs):
        return _result("unknown", "OEM recovery URL is not among the captured primary references", path)
    packages, error = _need(data, path, "dpkg transaction history", lambda a: Path(a[0]).name in {"zgrep", "grep"} and any("dpkg.log" in x for x in a))
    if error:
        return error
    assert packages is not None
    if not any(token in packages["stdout"] for token in (plan["last_kernel"], plan["last_driver"], plan["last_package"])):
        return _result("unknown", "captured transaction log does not identify last kernel/driver/package", path)
    return None


def _recovery_access(data: dict[str, Any], path: Path) -> dict[str, Any] | None:
    route = str(data.get("experiment_plan", {}).get("console_route", ""))
    console, error = _need(data, path, "external console probe",
                           lambda a: Path(a[0]).name == "ssh" and route in a)
    if error:
        return error
    assert console is not None
    if not console["stdout"].strip() or "failed" in console["stdout"].lower():
        return _result("fail", "external recovery console is unreachable", path)
    procedure, error = _need(data, path, "read-only recovery procedure",
                             lambda a: Path(a[0]).name == "cat", phase="recovery-runbook")
    if error:
        return error
    assert procedure is not None
    required_steps = ("preserve", "console", "media", "rollback", "rma")
    if any(step not in procedure["stdout"].lower() for step in required_steps):
        return _result("fail", "recovery procedure omits preservation, console, verified media, rollback, or RMA path", path)
    return None


def _recovery_media(data: dict[str, Any], path: Path, plan: dict[str, Any]) -> dict[str, Any] | None:
    expected_path = str(data.get("experiment_plan", {}).get("recovery_media_path", ""))
    media, error = _need(data, path, "OEM recovery media hash readback",
                         lambda a: Path(a[0]).name == "sha256sum" and expected_path in a)
    if error:
        return error
    assert media is not None
    digest = re.search(r"(?im)^([0-9a-f]{64})\s+", media["stdout"])
    if digest is None:
        return _result("unknown", "recovery media hash output unavailable", path)
    if digest.group(1) != plan["recovery_media_sha256"]:
        return _result("fail", "recovery media digest differs from predeclared OEM image", path)
    return None


PREDICATES: dict[str, Callable[[dict[str, Any], Path], dict[str, Any]]] = {
    IDS[0]: _cutlass,
    IDS[1]: _fw_guard,
    IDS[2]: _topology,
    IDS[3]: _posthotplug,
    IDS[4]: _rdma_asymmetry,
    IDS[5]: _dual_spark,
    IDS[6]: _kv_quant,
    IDS[7]: _memory_soak,
    IDS[8]: _ota_tuple,
    IDS[9]: _recovery_apt,
}


def verify(finding_id: str, evidence: str | Path | None = None, *, trusted_plan_sha256: str | None = None) -> dict[str, Any]:
    if finding_id not in PREDICATES:
        return {"status": "fail", "reason": "ID is not part of the generated Batch 02 source", "files": [],
                "fail": 1, "could_not_run": 0}
    directory = Path(evidence) if evidence is not None else ROOT / "tasks/evidence" / finding_id
    path = directory / "commands.json"
    data, error = _load(directory, finding_id)
    if error:
        return error
    assert data is not None
    if trusted_plan_sha256 is not None:
        data["_trusted_plan_sha256"] = trusted_plan_sha256
    try:
        return PREDICATES[finding_id](data, path)
    except (KeyError, TypeError, ValueError, OverflowError, AttributeError, IndexError) as exc:
        return _result("unknown", f"incomplete raw observation: {type(exc).__name__}: {exc}", path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, choices=IDS)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--trusted-plan-sha256")
    args = parser.parse_args(argv)
    result = verify(args.id, args.evidence, trusted_plan_sha256=args.trusted_plan_sha256)
    print(json.dumps(result, sort_keys=True))
    return {"pass": 0, "fail": 1, "unknown": 2}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
