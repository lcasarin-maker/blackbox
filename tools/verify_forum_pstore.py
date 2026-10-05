"""Verify a forum finding against local raw pstore and vendor evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse

SUPPORTED = {"FORUM-02-PSTORE-KERNEL-REGRESSION"}


def verify(finding_id: str, directory: Path) -> dict[str, Any]:
    if finding_id not in SUPPORTED:
        return _r("fail", [f"unsupported finding id: {finding_id}"], 0)
    try:
        d = json.loads((directory / "finding.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return _r("unknown", [f"raw finding evidence unavailable: {exc}"], 1)
    return _evaluate(finding_id, d)


def _evaluate(finding_id: str, d: dict[str, Any]) -> dict[str, Any]:
    if d.get("schema") != 1 or d.get("id") != finding_id:
        return _r("fail", ["finding identity/schema mismatch"], 0)
    identity = d.get("stack")
    required = ("oem", "bios", "ec", "kernel", "driver", "boot_id")
    if not isinstance(identity, dict) or any(not identity.get(k) for k in required):
        return _r("unknown", ["full target OEM/firmware/kernel/driver/boot identity missing"], 1)
    pstore_result = _pstore(d, identity)
    if pstore_result:
        return pstore_result
    return _vendor_and_controls(d, identity)


def _pstore(d: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any] | None:
    pstore = d.get("pstore")
    if not isinstance(pstore, dict) or not isinstance(pstore.get("raw_records"), list) or not pstore["raw_records"]:
        return _r("unknown", ["readable raw pstore capture with record hashes required"], 1)
    if pstore.get("boot_id") != identity["boot_id"]:
        return _r("fail", ["pstore and target boot identity differ"], 0)
    signatures = set()
    for record in pstore["raw_records"]:
        content = record.get("content")
        if not isinstance(content, str) or hashlib.sha256(content.encode()).hexdigest() != record.get("sha256"):
            return _r("fail", ["pstore record bytes missing or hash mismatch"], 0)
        for marker in ("FPAC", "PSCI", "NMI", "SBSA", "DOE"):
            if marker in content:
                signatures.add(marker)
    if not {"FPAC", "PSCI", "NMI"} <= signatures:
        return _r("fail", ["raw pstore bytes lack separate FPAC/PSCI/NMI signatures"], 0)
    return None


def _vendor_and_controls(d: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    vendor = d.get("vendor_resolution")
    if not isinstance(vendor, dict) or not isinstance(vendor.get("source_text"), str) or not isinstance(vendor.get("source_url"), str):
        return _r("unknown", ["vendor resolution for exact affected version required"], 1)
    if urlparse(vendor["source_url"]).hostname not in ("nvidia.com", "www.nvidia.com", "docs.nvidia.com"):
        return _r("fail", ["vendor resolution source is outside NVIDIA-owned documentation"], 0)
    if hashlib.sha256(vendor["source_text"].encode()).hexdigest() != vendor.get("source_sha256") or identity["kernel"] not in vendor["source_text"]:
        return _r("fail", ["vendor source digest/version does not support target-kernel applicability"], 0)
    if vendor.get("corrected_version") and not vendor.get("verified_fix"):
        return _r("fail", ["claimed corrected version lacks verified vendor fix evidence"], 0)
    recommendation = d.get("recommendation")
    control = d.get("negative_control")
    if not isinstance(recommendation, dict) or recommendation.get("action") not in ("monitor", "rollback", "update", "RMA") or not recommendation.get("reason"):
        return _r("unknown", ["evidence-backed action and reason required"], 1)
    if not isinstance(control, dict) or not isinstance(control.get("content"), str):
        return _r("unknown", ["raw negative-control record required"], 1)
    if hashlib.sha256(control["content"].encode()).hexdigest() != control.get("sha256"):
        return _r("fail", ["negative-control record hash mismatch"], 0)
    if any(marker in control["content"] for marker in ("FPAC", "PSCI", "NMI")):
        return _r("fail", ["negative control contains a target crash signature"], 0)
    return _r("pass", [], 0)


def _r(status: str, findings: list[str], could_not_run: int) -> dict[str, Any]:
    return {"status": status, "findings": findings, "could_not_run": could_not_run,
            "could_not_run_count": could_not_run, "fail": int(status == "fail")}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--id", required=True)
    p.add_argument("--evidence", type=Path, required=True)
    a = p.parse_args(argv)
    out = verify(a.id, a.evidence)
    print(json.dumps(out, sort_keys=True))
    return {"pass": 0, "fail": 1, "unknown": 2}[out["status"]]


if __name__ == "__main__":
    sys.exit(main())
