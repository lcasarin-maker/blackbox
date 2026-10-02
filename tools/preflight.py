"""Read-only, evidence-driven preflight checks for update and GPU incidents.

Input is an observation snapshot (JSON); this module never changes the host.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def _result(findings: list[str]) -> dict[str, Any]:
    return {"status": "pass" if not findings else "block", "findings": findings}


def _unknown(reason: str) -> dict[str, Any]:
    return {"status": "unknown", "findings": [reason]}


def _nonempty_strings(snapshot: dict[str, Any], fields: tuple[str, ...]) -> bool:
    return all(isinstance(snapshot[key], str) and snapshot[key].strip() for key in fields)


def _runtime_types_valid(snapshot: dict[str, Any]) -> bool:
    text_fields = ("host_arch", "image_arch", "image_digest", "driver_version", "image_driver_constraint", "gpu_arch", "driver_compatibility")
    return (_nonempty_strings(snapshot, text_fields)
            and isinstance(snapshot["backend_arches"], list)
            and all(isinstance(item, str) and item.strip() for item in snapshot["backend_arches"])
            and type(snapshot["backend_manifest_complete"]) is bool)


def _runtime_findings(snapshot: dict[str, Any]) -> tuple[list[str], list[str]]:
    findings: list[str] = []
    unknowns: list[str] = []
    if snapshot["host_arch"] != "aarch64" or snapshot["image_arch"] not in ("arm64", "aarch64"):
        findings.append("host/image architecture is not a supported ARM64 pair")
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", str(snapshot["image_digest"])):
        findings.append("image digest is absent or malformed")
    if snapshot["driver_compatibility"] == "block":
        findings.append("native NVIDIA constraint evaluation rejected this driver/image pair")
    elif snapshot["driver_compatibility"] == "unknown":
        unknowns.append("native NVIDIA constraint evaluation is unavailable")
    if not snapshot["backend_manifest_complete"]:
        unknowns.append("backend kernel/PTX architecture manifest is incomplete")
    elif snapshot["gpu_arch"] not in snapshot["backend_arches"]:
        findings.append("complete backend manifest excludes the detected GPU architecture")
    return findings, unknowns


def check_apt(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Block simulated plans that remove a named critical package."""
    plan = snapshot.get("plan")
    critical = snapshot.get("critical_packages")
    exit_code = snapshot.get("exit_code")
    stderr = snapshot.get("stderr")
    if not isinstance(plan, str) or not isinstance(critical, list) or not critical or not all(isinstance(item, str) and item.strip() for item in critical):
        return _unknown("plan or critical_packages missing or malformed")
    if type(exit_code) is not int or not isinstance(stderr, str):
        return _unknown("APT exit_code or stderr missing or malformed")
    if exit_code != 0 or stderr:
        return _unknown("APT simulation failed or wrote to stderr")
    summary = re.search(r"^(\d+) upgraded, \d+ newly installed, (\d+) to remove\b", plan, re.MULTILINE)
    if not summary:
        return _unknown("APT simulation output is incomplete or unrecognized")
    removed_lines = re.findall(r"^Remv\s+(\S+)", plan, re.MULTILINE)
    if len(removed_lines) != int(summary.group(2)):
        return _unknown("APT removal count does not match complete Remv records")
    removed = {name.split(":", 1)[0] for name in removed_lines}
    affected = sorted(removed.intersection(str(item).split(":", 1)[0] for item in critical))
    return _result([f"critical package scheduled for removal: {name}" for name in affected])


def check_runtime(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Check image identity and consume native driver/kernel-manifest verdicts."""
    required = ("host_arch", "image_arch", "image_digest", "driver_version", "image_driver_constraint", "gpu_arch", "backend_arches", "driver_compatibility", "backend_manifest_complete")
    missing = [key for key in required if key not in snapshot or snapshot[key] in (None, "")]
    if missing:
        return {"status": "unknown", "findings": [f"missing observation: {key}" for key in missing]}
    if not _runtime_types_valid(snapshot):
        return _unknown("runtime observation has invalid field types")
    if snapshot["driver_compatibility"] not in ("pass", "block", "unknown"):
        return _unknown("native driver compatibility verdict is invalid")
    findings, unknowns = _runtime_findings(snapshot)
    if findings:
        return _result(findings)
    if unknowns:
        return {"status": "unknown", "findings": unknowns}
    return _result([])


def check_gsp(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Distinguish PCI presence from usable CUDA/GSP state."""
    required = ("pci_present", "cuda_status", "gsp_timeout", "evidence_id")
    missing = [key for key in required if key not in snapshot or snapshot[key] is None]
    if missing:
        return {"status": "unknown", "findings": [f"missing observation: {key}" for key in missing]}
    if type(snapshot["pci_present"]) is not bool or type(snapshot["gsp_timeout"]) is not bool or type(snapshot["cuda_status"]) is not int or not isinstance(snapshot["evidence_id"], str) or not snapshot["evidence_id"].strip():
        return _unknown("GSP observation has invalid field types or empty evidence_id")
    findings: list[str] = []
    if not snapshot["pci_present"]:
        findings.append("GPU absent from PCI inventory")
    if snapshot["cuda_status"] != 0:
        findings.append("CUDA probe failed despite PCI inventory")
    if snapshot["gsp_timeout"]:
        findings.append("GSP timeout observed")
    return _result(findings)


def check_fallback(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Detect a GPU-requesting workload silently served by CPU."""
    required = ("requests", "requested_provider", "observed_provider", "worker_restarted", "evidence_id")
    missing = [key for key in required if key not in snapshot or snapshot[key] is None]
    if missing:
        return {"status": "unknown", "findings": [f"missing observation: {key}" for key in missing]}
    if type(snapshot["requests"]) is not int or type(snapshot["worker_restarted"]) is not bool or not isinstance(snapshot["requested_provider"], str) or not isinstance(snapshot["observed_provider"], str) or not isinstance(snapshot["evidence_id"], str) or not snapshot["evidence_id"].strip():
        return _unknown("fallback observation has invalid field types or empty evidence_id")
    if snapshot["requested_provider"] not in ("gpu", "cpu") or snapshot["observed_provider"] not in ("gpu", "cpu"):
        return _unknown("fallback provider must be gpu or cpu")
    if snapshot["requests"] < 0:
        return _result(["request count is invalid"])
    if snapshot["requests"] == 0:
        return {"status": "unknown", "findings": ["no request exercised provider selection"]}
    if snapshot["requested_provider"] == "gpu" and snapshot["observed_provider"] == "cpu":
        return _result(["GPU request was served by CPU"])
    return _result([])


def check_drm(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Require readable effective KMS state and a compatible OTA declaration."""
    required = ("effective_modeset", "target_requires_kms", "override_present", "recovery_accessible")
    missing = [key for key in required if key not in snapshot or snapshot[key] is None]
    if missing:
        return {"status": "unknown", "findings": [f"missing observation: {key}" for key in missing]}
    if not isinstance(snapshot["effective_modeset"], str) or snapshot["effective_modeset"] not in ("Y", "N") or any(type(snapshot[key]) is not bool for key in ("target_requires_kms", "override_present", "recovery_accessible")):
        return _unknown("DRM observation has invalid field types or modeset value")
    findings: list[str] = []
    if snapshot["target_requires_kms"] and snapshot["effective_modeset"] != "Y":
        findings.append("OTA requires KMS but effective modeset is not enabled")
    if snapshot["override_present"] and snapshot["effective_modeset"] != "Y":
        findings.append("DRM override conflicts with effective KMS state")
    if not snapshot["recovery_accessible"]:
        findings.append("recovery path is unavailable")
    return _result(findings)


def check_kernel(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Require coherent packages, boot files, module, and previous-kernel recovery."""
    required = ("dpkg_clean", "apt_check", "vmlinuz_present", "initrd_present", "module_ready", "previous_kernel_bootable")
    missing = [key for key in required if key not in snapshot or snapshot[key] is None]
    if missing:
        return {"status": "unknown", "findings": [f"missing observation: {key}" for key in missing]}
    if any(type(snapshot[key]) is not bool for key in required):
        return _unknown("kernel observation fields must be booleans")
    labels = {
        "dpkg_clean": "dpkg audit reports incomplete packages",
        "apt_check": "APT dependency check failed",
        "vmlinuz_present": "target vmlinuz missing",
        "initrd_present": "target initrd missing or empty",
        "module_ready": "target GPU module is unavailable or unsigned",
        "previous_kernel_bootable": "previous kernel recovery is unverified",
    }
    return _result([labels[key] for key in required if not snapshot[key]])


CHECKS = {
    "apt": check_apt,
    "runtime": check_runtime,
    "gsp": check_gsp,
    "fallback": check_fallback,
    "drm": check_drm,
    "kernel": check_kernel,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=sorted(CHECKS))
    parser.add_argument("snapshot", type=Path, help="JSON observation file")
    args = parser.parse_args(argv)
    try:
        document = json.loads(args.snapshot.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "unknown", "findings": [str(exc)]}, sort_keys=True))
        return 2
    if not isinstance(document, dict):
        result = {"status": "unknown", "findings": ["snapshot must be a JSON object"]}
    else:
        snapshot = document.get("snapshot", document)
        if not isinstance(snapshot, dict):
            result = {"status": "unknown", "findings": ["snapshot must be a JSON object"]}
        else:
            result = CHECKS[args.kind](snapshot)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    sys.exit(main())
