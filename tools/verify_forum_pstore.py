"""Verify a forum finding against supplied pstore and vendor captures.

Identity, source, recommendation and provenance fields are caller-supplied and
unauthenticated; hashes establish consistency only, not origin or applicability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlparse

SUPPORTED = {"FORUM-02-PSTORE-KERNEL-REGRESSION"}
MAX_EVIDENCE_BYTES = 1024 * 1024


def verify(finding_id: str, directory: Path) -> dict[str, Any]:
    if finding_id not in SUPPORTED:
        return _r("fail", [f"unsupported finding id: {finding_id}"], 0)
    try:
        with (directory / "finding.json").open("rb") as stream:
            raw = stream.read(MAX_EVIDENCE_BYTES + 1)
        if len(raw) > MAX_EVIDENCE_BYTES:
            return _r("unknown", ["finding evidence exceeds 1 MiB bounded input"], 1)
        d = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        return _r("unknown", [f"raw finding evidence unavailable: {exc}"], 1)
    if not isinstance(d, dict):
        return _r("unknown", ["top-level finding evidence must be a JSON object"], 1)
    try:
        return _evaluate(finding_id, d)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
        return _r("unknown", [f"raw finding evidence malformed: {exc}"], 1)


def _evaluate(finding_id: str, d: dict[str, Any]) -> dict[str, Any]:
    if type(d.get("schema")) is not int or d.get("schema") != 1 or d.get("id") != finding_id:
        return _r("fail", ["finding identity/schema mismatch"], 0)
    identity = d.get("stack")
    required = ("oem", "bios", "ec", "kernel", "driver", "boot_id")
    if not isinstance(identity, dict) or any(not isinstance(identity.get(k), str) or not identity[k].strip() or
            identity[k].strip().lower() in {"unknown", "unbound", "n/a", "none"} for k in required):
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
        if not isinstance(record, dict):
            return _r("unknown", ["raw pstore record must be an object"], 1)
        content = record.get("content")
        if not isinstance(content, str) or hashlib.sha256(content.encode()).hexdigest() != record.get("sha256"):
            return _r("fail", ["pstore record bytes missing or hash mismatch"], 0)
        for marker in ("FPAC", "PSCI", "NMI", "SBSA", "DOE", "link x0", "link width 0"):
            if marker.lower() in content.lower():
                signatures.add(marker.lower())
    if not signatures.intersection({"fpac", "psci", "nmi"}):
        return _r("fail", ["raw pstore bytes lack a target RAS/firmware signature"], 0)
    return _classification(pstore.get("classification"), signatures)


def _classification(classification: Any, signatures: set[str]) -> dict[str, Any] | None:
    if not isinstance(classification, dict) or classification.get("ras_signature") not in signatures:
        return _r("unknown", ["explicit raw-signature classification is required"], 1)
    if classification.get("sbsa_assessment") not in ("observed", "not_in_record") or classification.get("doe_link_assessment") not in ("observed", "not_in_record"):
        return _r("unknown", ["separate SBSA and DOE/link x0 assessment is required"], 1)
    return None


def _vendor_and_controls(d: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    vendor = d.get("vendor_resolution")
    if not isinstance(vendor, dict) or not isinstance(vendor.get("source_text"), str) or not isinstance(vendor.get("source_url"), str):
        return _r("unknown", ["vendor resolution for exact affected version required"], 1)
    source_issue = _vendor_source_issue(vendor, identity)
    if source_issue:
        return source_issue
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


def _vendor_source_issue(vendor: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any] | None:
    hostname = urlparse(vendor["source_url"]).hostname
    if not hostname or not isinstance(vendor.get("publisher_domain"), str) or hostname != vendor["publisher_domain"]:
        return _r("unknown", ["source publisher and URL host are not bound"], 1)
    text = vendor["source_text"]
    if hashlib.sha256(text.encode()).hexdigest() != vendor.get("source_sha256"):
        return _r("fail", ["vendor source digest does not match supplied bytes"], 0)
    issue = _applicability(vendor.get("applicability"), identity, text)
    if issue:
        return issue
    if not isinstance(vendor.get("symptom_resolution"), str) or not vendor["symptom_resolution"].strip() or vendor["symptom_resolution"] not in text:
        return _r("unknown", ["source-backed symptom/resolution text is required"], 1)
    return None


def _applicability(raw: Any, identity: dict[str, Any], source_text: str) -> dict[str, Any] | None:
    keys = ("oem", "bios", "ec", "kernel", "driver")
    if not isinstance(raw, dict) or any(raw.get(key) != identity[key] for key in keys):
        return _r("unknown", ["vendor applicability must address the captured OEM/BIOS/EC/kernel/driver tuple"], 1)
    if any(identity[key] not in source_text for key in keys):
        return _r("unknown", ["vendor source does not contain the full applicable stack tuple"], 1)
    return None


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
