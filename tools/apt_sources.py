"""Read-only APT source diagnostics with observed effective index tuples."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlsplit

from tools.host_diagnostics import could_not_run_count, run_readonly
from tools.memory_profile import capture as capture_memory_profile


def _read_architecture() -> tuple[str | None, dict[str, Any] | None]:
    """Read architecture identity from the host dpkg database."""
    result = run_readonly(["dpkg", "--print-architecture"])
    if result["status"] != "ok":
        return None, {"status": "could_not_run", "architecture_query": {
            "command": result.get("command"), "status": result.get("status"),
            "returncode": result.get("returncode"), "stdout_truncated": result.get("stdout_truncated"),
            "stderr_present": bool(result.get("stderr"))}}
    architecture = result.get("stdout", "").strip()
    return (architecture or None, None)


def _field_value(line_number: int, line: str, current: dict[str, str],
                 errors: list[str]) -> str | None:
    """Validate and store one non-continuation Deb822 field."""
    if ":" not in line:
        errors.append(f"line {line_number}: expected Field: value")
        return None
    key, value = line.split(":", 1)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9-]*", key):
        errors.append(f"line {line_number}: malformed field name")
        return None
    normalized = key.lower()
    if normalized in current:
        errors.append(f"line {line_number}: duplicate field {key}")
        return None
    current[normalized] = value.strip()
    return normalized


def parse_deb822(text: str) -> tuple[list[dict[str, str]], list[str]]:
    """Parse the field/continuation subset used by deb822 .sources files."""
    stanzas: list[dict[str, str]] = []
    errors: list[str] = []
    current: dict[str, str] = {}
    last_key: str | None = None
    for line_number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        if not line.strip():
            if current:
                stanzas.append(current)
            current = {}
            last_key = None
            continue
        if line[0].isspace():
            if last_key:
                current[last_key] += " " + line.strip()
            else:
                errors.append(f"line {line_number}: continuation without a field")
            continue
        last_key = _field_value(line_number, line, current, errors)
    if current:
        stanzas.append(current)

    for index, stanza in enumerate(stanzas, 1):
        missing = [name for name in ("types", "uris", "suites", "components")
                   if not stanza.get(name)]
        if missing:
            errors.append(f"stanza {index}: missing required fields: {', '.join(missing)}")
    return stanzas, errors


def parse_index_targets(text: str) -> tuple[list[dict[str, str]], list[str]]:
    """Read pipe-delimited apt indextargets output without rewriting identities."""
    rows: list[dict[str, str]] = []
    errors: list[str] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line:
            continue
        fields = line.split("|")
        if len(fields) != 4:
            errors.append(f"line {line_number}: malformed index target tuple")
            continue
        uri, suite, architecture, identifier = fields
        safe_uri = _safe_uri(uri)
        if safe_uri is None:
            errors.append(f"line {line_number}: malformed index target URI")
            continue
        rows.append({"uri": safe_uri, "suite": suite, "architecture": architecture,
                     "identifier": identifier})
    return rows, errors


def _safe_uri(uri: str) -> str | None:
    """Drop URI credentials and query material before retaining source identity."""
    try:
        parsed = urlsplit(uri)
        host = parsed.hostname
        if parsed.scheme in ("http", "https") and not host:
            return None
        if not parsed.scheme:
            return None
        port = parsed.port
    except ValueError:
        return None
    netloc = host or ""
    if ":" in netloc and not netloc.startswith("["):
        netloc = f"[{netloc}]"
    if port is not None:
        netloc += f":{port}"
    return f"{parsed.scheme}://{netloc}{parsed.path}" if host else f"{parsed.scheme}:{parsed.path}"


def _redact_stanzas(stanzas: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep parsed source fields while stripping authentication and query data."""
    redacted: list[dict[str, str]] = []
    for stanza in stanzas:
        safe = dict(stanza)
        safe["uris"] = " ".join(_safe_uri(uri) or "<invalid-uri>"
                                 for uri in stanza.get("uris", "").split())
        redacted.append(safe)
    return redacted


def _reported(result: dict[str, Any]) -> dict[str, Any]:
    """Print unavailable-check counts for both complete and partial captures."""
    return {**result, "could_not_run_count": could_not_run_count(result)}


def diagnose(stanzas: list[dict[str, str]], targets: list[dict[str, str]],
             architecture: str) -> dict[str, Any]:
    """Report one evidence-based Ubuntu arm64 source incompatibility and tuple inventory."""
    findings: list[str] = []
    ubuntu_sources: list[dict[str, str]] = []
    unknown_sources: list[dict[str, str]] = []
    malformed_uris: list[str] = []
    for stanza in stanzas:
        if stanza.get("enabled", "yes").lower() == "no" or "deb" not in stanza.get("types", "").split():
            continue
        uris = stanza.get("uris", "").split()
        suites = stanza.get("suites", "").split()
        arches = stanza.get("architectures", "").split() or [architecture]
        for uri in uris:
            for suite in suites:
                for arch in arches:
                    safe_uri = _safe_uri(uri)
                    row = {"type": "deb", "uri": safe_uri or "<invalid-uri>", "suite": suite, "architecture": arch,
                           "signed_by": stanza.get("signed-by", "")}
                    if safe_uri is None:
                        malformed_uris.append("<invalid-uri>")
                        unknown_sources.append(row)
                        continue
                    parsed_uri = urlsplit(safe_uri)
                    ubuntu_archive = (parsed_uri.hostname == "archive.ubuntu.com"
                                      and parsed_uri.path.rstrip("/") == "/ubuntu")
                    ubuntu_ports = (parsed_uri.hostname == "ports.ubuntu.com"
                                    and parsed_uri.path.rstrip("/") == "/ubuntu-ports")
                    if ubuntu_archive or ubuntu_ports:
                        ubuntu_sources.append(row)
                        if ubuntu_archive and arch == "arm64":
                            findings.append(
                                f"Ubuntu source {safe_uri} suite {suite} targets arm64; "
                                "this endpoint lacks Ubuntu binary arm64 indexes (observed compatible endpoint: ports.ubuntu.com/ubuntu-ports)")
                    else:
                        unknown_sources.append(row)
    observed = sorted({(row["uri"], row["suite"], row["architecture"], row["identifier"])
                       for row in targets})
    unassessed_targets = [
        {"uri": uri, "suite": suite, "architecture": arch, "identifier": identifier}
        for uri, suite, arch, identifier in observed
        if not (urlsplit(uri).hostname == "ports.ubuntu.com"
                and urlsplit(uri).path.rstrip("/") == "/ubuntu-ports")]
    status = "could_not_run" if malformed_uris else "block" if findings else "observed"
    return {"status": status, "findings": findings,
            "architecture": architecture,
            "source_scope": "only /etc/apt/sources.list.d/ubuntu.sources was parsed",
            "malformed_source_uri_count": len(malformed_uris),
            "configured_ubuntu_source_tuples": ubuntu_sources,
            "unassessed_source_tuples": unknown_sources,
            "unassessed_effective_index_tuples": unassessed_targets,
            "effective_index_tuples": [
                {"uri": uri, "suite": suite, "architecture": arch, "identifier": identifier}
                for uri, suite, arch, identifier in observed],
            "effective_tuple_count": len(observed)}


def effective_ota_tuple(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Project memory_profile evidence onto the observed OTA/kernel/driver tuple."""
    stack = snapshot.get("effective_stack")
    kernel = snapshot.get("kernel")
    release = stack.get("dgx_release") if isinstance(stack, dict) else None
    driver = stack.get("driver_comparison") if isinstance(stack, dict) else None
    release_text = release.get("value") if isinstance(release, dict) and release.get("status") == "ok" else None
    kernel_release = kernel.get("release") if isinstance(kernel, dict) else None
    if not isinstance(release_text, str) or not isinstance(kernel_release, str) or not isinstance(driver, dict):
        return {"status": "could_not_run", "reason": "OTA, kernel, or driver observation unavailable"}
    kernel_release = kernel_release.strip()
    values: dict[str, str] = {}
    for line in release_text.splitlines():
        match = re.fullmatch(r'(DGX_(?:OTA_VERSION|OTA_DATE|SWBUILD_VERSION))="([^"]*)"', line)
        if match and match.group(2).strip():
            values[match.group(1)] = match.group(2).strip()
    loaded_value = driver.get("loaded_version")
    disk_value = driver.get("disk_version")
    loaded_driver = loaded_value.strip() if isinstance(loaded_value, str) else None
    disk_driver = disk_value.strip() if isinstance(disk_value, str) else None
    tuple_values = {
        "dgx_swbuild_version": values.get("DGX_SWBUILD_VERSION"),
        "dgx_ota_version": values.get("DGX_OTA_VERSION"),
        "dgx_ota_date": values.get("DGX_OTA_DATE"),
        "kernel_release": kernel_release,
        "loaded_driver": loaded_driver if isinstance(loaded_driver, str) and loaded_driver else None,
        "disk_driver": disk_driver if isinstance(disk_driver, str) and disk_driver else None,
        "loaded_disk_driver_match": (loaded_driver == disk_driver
                                     if loaded_driver and disk_driver else None),
    }
    missing = [key for key, value in tuple_values.items()
               if value is None or isinstance(value, str) and not value.strip()]
    return {"status": "observed" if not missing else "could_not_run",
            "tuple": tuple_values, "missing": missing,
            "provenance": "memory_profile snapshot; values are observations, provenance unverified",
            "support_verdict": "not evaluated"}


def capture() -> dict[str, Any]:
    """Read source configuration and APT's existing index-target inventory."""
    source_path = Path("/etc/apt/sources.list.d/ubuntu.sources")
    try:
        source_text = source_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return _reported({"status": "could_not_run", "error": f"{type(exc).__name__}: {exc}"})
    stanzas, source_errors = parse_deb822(source_text)
    if source_errors:
        return _reported({"status": "could_not_run", "source_errors": source_errors,
                          "parsed_stanzas": _redact_stanzas(stanzas)})
    architecture, architecture_error = _read_architecture()
    if architecture_error:
        return _reported(architecture_error)
    if not architecture or architecture == "unknown":
        return _reported({"status": "could_not_run", "error": "system architecture unavailable"})
    try:
        result = run_readonly(["apt-get", "indextargets",
                               "--format=$(SITE)|$(RELEASE)|$(ARCHITECTURE)|$(IDENTIFIER)"])
    except (OSError, ValueError) as exc:
        return _reported({"status": "could_not_run", "error": f"{type(exc).__name__}: {exc}"})
    targets, target_errors = parse_index_targets(result.get("stdout", ""))
    if result["status"] != "ok" or result.get("stdout_truncated") or target_errors:
        return _reported({"status": "could_not_run",
                          "index_target_command": result.get("command"),
                          "index_target_status": result.get("status"),
                          "index_target_returncode": result.get("returncode"),
                          "index_target_stdout_truncated": result.get("stdout_truncated", False),
                          "index_target_stderr_present": bool(result.get("stderr")),
                          "target_errors": target_errors})
    report = diagnose(stanzas, targets, architecture)
    report["source_file"] = str(source_path)
    report["source_stanzas"] = _redact_stanzas(stanzas)
    report["captured_index_targets"] = targets
    report["ota_effective_tuple"] = effective_ota_tuple(capture_memory_profile())
    return _reported(report)


def main() -> int:
    result = _reported(capture())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["could_not_run_count"] else (1 if result["status"] == "block" else 0)


if __name__ == "__main__":
    sys.exit(main())
