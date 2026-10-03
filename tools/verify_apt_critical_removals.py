"""Verify APT critical-removal classification against captured read-only evidence.

This checks the preflight instrument. A passing instrument check does not establish
that an OEM package graph is protected or that an APT guard is installed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from tools.preflight import check_apt


APT_COMMANDS = {
    "upgrade": ["apt-get", "-s", "-o", "Debug::NoLocking=1", "upgrade"],
    "remove": ["apt-get", "-s", "-o", "Debug::NoLocking=1", "remove", "nvidia-system-station"],
}
CRITICAL_PACKAGES = ["nvidia-system-station"]


def _unknown(reason: str, could_not_run: int = 1) -> dict[str, Any]:
    return {"status": "unknown", "findings": [reason], "fail": 0,
            "could_not_run": could_not_run}


def _load(directory: Path) -> tuple[dict[str, Any], str] | str:
    try:
        path = directory / "apt-captures.json"
        raw = path.read_bytes()
        captures = json.loads(raw)
        expected_hash = (directory / "apt-captures.sha256").read_text(encoding="ascii").strip()
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return f"evidence unreadable: {exc}"
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        return "captured APT evidence hash mismatch"
    if not isinstance(captures, dict) or not isinstance(captures.get("commands"), list):
        return "captured APT commands missing or malformed"
    return captures, expected_hash


def _classify_capture(row: dict[str, Any], label: str) -> tuple[str, dict[str, Any] | str]:
    if type(row.get("exit_code")) is not int or not isinstance(row.get("stdout"), str) or not isinstance(row.get("stderr"), str):
        return "unknown", f"{label} exit/output malformed"
    if row["exit_code"] != 0:
        return "unknown", f"{label} simulation exit={row['exit_code']}"
    if row["stderr"]:
        return "unknown", f"{label} simulation wrote to stderr"
    outcome = check_apt({"plan": row["stdout"], "critical_packages": CRITICAL_PACKAGES,
                         "exit_code": row["exit_code"], "stderr": row["stderr"]})
    return outcome["status"], outcome


def verify(directory: Path) -> dict[str, Any]:
    """Classify captured real benign and dangerous simulations plus parser controls."""
    evidence = _load(directory)
    if isinstance(evidence, str):
        return _unknown(evidence)
    captures, digest = evidence
    if len(captures["commands"]) != len(APT_COMMANDS) or any(
            not isinstance(row, dict) for row in captures["commands"]):
        return _unknown("APT capture must contain exactly two well-formed command records")
    by_name: dict[str, list[Any]] = {name: [] for name in APT_COMMANDS}
    for row in captures["commands"]:
        if isinstance(row, dict) and isinstance(row.get("argv"), list):
            for name, argv in APT_COMMANDS.items():
                if row["argv"] == argv:
                    by_name[name].append(row)
    if any(len(rows) != 1 for rows in by_name.values()):
        return _unknown("expected exactly one raw upgrade and one raw critical remove capture")
    benign, benign_result = _classify_capture(by_name["upgrade"][0], "upgrade")
    dangerous, dangerous_result = _classify_capture(by_name["remove"][0], "remove")
    if benign == "unknown" or dangerous == "unknown":
        return _unknown(str(benign_result if benign == "unknown" else dangerous_result))
    if benign != "pass" or dangerous != "block":
        return {"status": "fail", "findings": [f"real capture classifications: upgrade={benign}, remove={dangerous}"],
                "fail": 1, "could_not_run": 0}
    return {
        "status": "pass",
        "findings": [],
        "fail": 0,
        "could_not_run": 0,
        "evidence_sha256": digest,
        "checks": {"captured_upgrade": "pass", "captured_critical_removal": "block"},
        "closure": "open",
        "open_blockers": ["OEM coverage and installed APT guard remain unverified"],
        "meaning": "instrument discriminates these host simulations; OEM protection and installed APT guard are unverified",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True, help="captured evidence directory")
    args = parser.parse_args(argv)
    result = verify(args.evidence)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 1 if result["status"] == "fail" else 2


if __name__ == "__main__":
    sys.exit(main())
