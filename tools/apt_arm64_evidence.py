"""Evaluate recorded, read-only Ubuntu arm64 APT source validation captures."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _outcome(status: str, reason: str, checks: dict[str, str]) -> dict[str, Any]:
    return {"status": status, "reason": reason, "checks": checks,
            "fail": int(status == "fail"), "could_not_run": int(status == "unknown")}


def _find_command(rows: list[Any], prefix: tuple[str, ...]) -> dict[str, Any] | None:
    for row in rows:
        if isinstance(row, dict) and tuple(row.get("argv", [])[:len(prefix)]) == prefix:
            return row
    return None


def _read_capture(path: Path, checks: dict[str, str]) -> tuple[list[Any] | None, dict[str, Any] | None]:
    try:
        captured = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, _outcome("unknown", f"raw command capture unavailable or malformed: {exc}", checks)
    if not isinstance(captured, dict) or captured.get("id") != "DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01":
        return None, _outcome("fail", "capture finding identity mismatch", checks)
    rows = captured.get("commands")
    if not isinstance(rows, list):
        return None, _outcome("unknown", "raw command rows missing", checks)
    if not _valid_rows(rows):
        return None, _outcome("fail", "a command row has invalid raw argv/exit/stdout/stderr", checks)
    return rows, None


def _validate_identity_and_source(rows: list[Any], checks: dict[str, str]) -> dict[str, Any] | None:
    arch = _find_command(rows, ("dpkg", "--print-architecture"))
    if arch is None or arch["exit_code"] != 0:
        return _outcome("unknown", "dpkg architecture query missing or unavailable", checks)
    if arch["stdout"].strip() != "arm64":
        checks["architecture"] = "fail"
        return _outcome("fail", "captured architecture differs from arm64", checks)
    checks["architecture"] = "pass"
    sources = _find_command(rows, ("cat", "/etc/apt/sources.list.d/ubuntu.sources"))
    if sources is None or sources["exit_code"] != 0:
        return _outcome("unknown", "active Ubuntu Deb822 source capture missing", checks)
    body = sources["stdout"]
    if "archive.ubuntu.com/ubuntu" in body:
        checks["ubuntu_source"] = "fail"
        return _outcome("fail", "captured Ubuntu archive endpoint is incompatible with arm64", checks)
    checks["ubuntu_source"] = "pass" if "ports.ubuntu.com/ubuntu-ports" in body else "unknown"
    return None if checks["ubuntu_source"] == "pass" else _outcome("unknown", "compatible Ubuntu ports source not proven", checks)


def _validate_index_signature(rows: list[Any], checks: dict[str, str]) -> dict[str, Any] | None:
    indexes = _find_command(rows, ("apt-get", "indextargets"))
    if indexes is None or indexes["exit_code"] != 0:
        return _outcome("unknown", "effective APT index inventory missing or unavailable", checks)
    tuples = [line for line in indexes["stdout"].splitlines() if line]
    if not any("ports.ubuntu.com/ubuntu-ports" in line and "|arm64|Packages" in line for line in tuples):
        checks["effective_index"] = "fail"
        return _outcome("fail", "no effective Ubuntu ports arm64 Packages tuple", checks)
    checks["effective_index"] = "pass"
    signed = next((row for row in rows if row["argv"][0] == "gpgv"
                   and "noble-updates_InRelease" in " ".join(row["argv"])), None)
    if signed is None or signed["exit_code"] != 0 or "Good signature" not in signed["stderr"]:
        return _outcome("unknown", "successful signature verification of captured InRelease missing", checks)
    checks["signed_index"] = "pass"
    return None


def _validate_simulation(rows: list[Any], checks: dict[str, str]) -> dict[str, Any] | None:
    simulation = next((row for row in rows if row["argv"][:3] == ["apt-get", "-s", "-o"]
                       and "upgrade" in row["argv"]), None)
    if simulation is None or simulation["exit_code"] != 0:
        return _outcome("unknown", "read-only upgrade simulation unavailable", checks)
    removed = re.search(r"(\d+) upgraded,\s+\d+ newly installed,\s+(\d+) to remove", simulation["stdout"])
    if not removed:
        return _outcome("unknown", "upgrade simulation removal summary unparseable", checks)
    if int(removed.group(2)):
        checks["upgrade_simulation"] = "fail"
        return _outcome("fail", f"simulation proposes removing {removed.group(2)} packages", checks)
    checks["upgrade_simulation"] = "pass"
    negative = next((row for row in rows if row["argv"][0] == "gpgv"
                     and any(arg.startswith("/tmp/") for arg in row["argv"])
                     and "InRelease" in " ".join(row["argv"])), None)
    if negative is None:
        return _outcome("unknown", "signature-negative capture absent", checks)
    if negative["exit_code"] != 1 or "BAD signature" not in negative["stderr"]:
        checks["bad_signature_negative"] = "fail"
        return _outcome("fail", "signature-negative control was not rejected", checks)
    checks["bad_signature_negative"] = "pass"
    return _outcome("unknown", "APT captures pass available checks; wrong-source negative remains unrun", checks)


def verify_capture(path: Path) -> dict[str, Any]:
    """Check raw command results and report the distinct source-negative gap."""
    checks = {name: "unknown" for name in (
        "architecture", "ubuntu_source", "effective_index", "signed_index",
        "upgrade_simulation", "bad_signature_negative", "bad_source_negative",
    )}
    rows, error = _read_capture(path, checks)
    if error:
        return error
    assert rows is not None
    for validator in (_validate_identity_and_source, _validate_index_signature, _validate_simulation):
        result = validator(rows, checks)
        if result:
            return result
    return _outcome("pass", "all source identity, signature, simulation, and negative checks pass", checks)


def _valid_rows(rows: list[Any]) -> bool:
    return all(isinstance(row, dict)
               and isinstance(row.get("argv"), list)
               and all(isinstance(arg, str) for arg in row["argv"])
               and isinstance(row.get("exit_code"), int)
               and isinstance(row.get("stdout"), str)
               and isinstance(row.get("stderr"), str)
               for row in rows)
