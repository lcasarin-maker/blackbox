"""Read-only APT source diagnostics with observed effective index tuples."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Any
from urllib.parse import urlsplit

from tools.host_diagnostics import could_not_run_count, run_readonly
from tools.memory_profile import capture as capture_memory_profile


def _signature_input(path: Path) -> bytes:
    """Snapshot a regular input without following its final symlink or blocking on a FIFO."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("signature input must be a regular file")
        raw = stream.read(8 * 1024 * 1024 + 1)
    if not raw or len(raw) > 8 * 1024 * 1024:
        raise ValueError("signature input must contain 1 byte through 8 MiB")
    return raw


def verify_release_signature(manifest: Path, keyrings: list[Path]) -> dict[str, Any]:
    """Verify exact snapshot bytes against explicit keyrings, without granting source approval.

    Keyring authorization, freshness and source coverage are separate gates.
    Temporary input copies are removed on every exit; UID transcripts are omitted.
    """
    try:
        if not keyrings:
            raise ValueError("explicit keyrings are required")
        payload = _signature_input(manifest)
        keys = [_signature_input(path) for path in keyrings]
        with tempfile.TemporaryDirectory(prefix="bb-apt-signature-") as directory:
            root = Path(directory)
            subject = root / "InRelease"
            subject.write_bytes(payload)
            argv = ["gpgv", "--homedir", str(root), "--status-fd=1"]
            for index, raw in enumerate(keys):
                key = root / f"key-{index}.gpg"
                key.write_bytes(raw)
                argv.extend(["--keyring", str(key)])
            argv.append(str(subject))
            capture = run_readonly(argv, accepted_exit_codes=(1, 2))
        result = _signature_verdict(capture)
        result.update(manifest_sha256=hashlib.sha256(payload).hexdigest(),
                      keyring_sha256=[hashlib.sha256(raw).hexdigest() for raw in keys],
                      command=capture.get("command"), returncode=capture.get("returncode"))
        return result
    except (OSError, ValueError) as exc:
        return {"status": "could_not_run", "could_not_run_count": 1, "fail": 0,
                "errors": [f"signature inputs unavailable: {type(exc).__name__}: {exc}"]}


def _signature_verdict(capture: dict[str, Any]) -> dict[str, Any]:
    stdout = capture.get("stdout", "")
    lines = stdout.splitlines()
    valid = [line for line in lines if re.fullmatch(
        r"\[GNUPG:\] VALIDSIG [0-9A-F]{40,64} \S+(?: \S+){7,8}", line)]
    negative = any(line.startswith(("[GNUPG:] BADSIG ", "[GNUPG:] REVKEYSIG ",
                                   "[GNUPG:] EXPKEYSIG ", "[GNUPG:] EXPSIG ")) for line in lines)
    incomplete = (capture.get("status") == "could_not_run" or
                  capture.get("stdout_truncated") or capture.get("stderr_truncated"))
    if incomplete:
        status = "could_not_run"
    elif negative:
        status = "block"
    elif capture.get("returncode") == 0 and valid:
        status = "pass"
    else:
        status = "could_not_run"
    return {"status": status, "could_not_run_count": int(status == "could_not_run"),
            "fail": int(status == "block"), "validsig_records": valid,
            "scope": "Exact archived bytes against supplied keys; approval and freshness separate."}


def _isolated_config_errors(text: str, root: Path) -> list[str]:
    """Check observed native APT directory and hook settings for a canary."""
    errors: list[str] = []
    if not root.is_absolute() or root.parent != Path("/tmp") or ".." in root.parts:
        return ["canary root must be an explicit direct child of /tmp"]
    for field in ("Dir::Etc", "Dir::State::lists", "Dir::Cache", "Dir::Log"):
        values = re.findall(r"^" + re.escape(field) + r' "([^"]*)";$', text, re.MULTILINE)
        if len(values) != 1 or not Path(values[0]).is_relative_to(root) or ".." in Path(values[0]).parts:
            errors.append(f"{field} is absent, ambiguous or outside the isolated root")
    if re.search(r"(?:Pre|Post)-Invoke", text):
        errors.append("APT canary configuration contains invocation hooks")
    if 'APT::Update::Error-Mode "any";' not in text:
        errors.append("APT canary must fail on any update error")
    insecure = re.findall(r'^Acquire::AllowInsecureRepositories "([^"]*)";$', text, re.MULTILINE)
    if insecure not in (["0"], ["false"]):
        errors.append("APT canary must explicitly reject insecure repositories")
    architectures = re.findall(r'^APT::Architecture "([^"]*)";$', text, re.MULTILINE)
    if architectures != ["arm64"]:
        errors.append("APT canary native architecture must be exactly arm64")
    return errors


def check_isolated_update_control(config: dict[str, Any], update: dict[str, Any],
                                  targets: dict[str, Any], root: Path,
                                  outcome: str) -> dict[str, Any]:
    """Reparse a canary's native receipts, without trusting asserted outcome flags.

    Receipts remain caller supplied. Source bytes, signature verification,
    timestamps, cleanup and host/profile applicability require separate checks.
    This component classifies only update acceptance/rejection and empty lists.
    """
    expected = {"healthy": None, "wrong_arm64_source": "binary-arm64/Packages",
                "bad_package_hash": "Hash Sum mismatch", "bad_release_signature": "BADSIG"}
    if outcome not in expected:
        raise ValueError("unsupported canary outcome")
    rows = (config, update, targets)
    malformed = any(type(row.get("exit_code")) is not int or
                    not isinstance(row.get("stdout"), str) or not isinstance(row.get("stderr"), str) or
                    row.get("stdout_truncated") or row.get("stderr_truncated")
                    for row in rows)
    commands_match = (config.get("argv") == ["apt-config", "dump"] and
                      update.get("argv") == ["apt-get", "update"] and
                      isinstance(targets.get("argv"), list) and
                      targets["argv"][:2] == ["apt-get", "indextargets"])
    errors = ["literal command/result receipts missing"] if malformed or not commands_match else []
    if not errors:
        errors.extend(_isolated_config_errors(config["stdout"], root))
    if errors or config.get("exit_code") != 0 or targets.get("exit_code") != 0:
        return {"status": "could_not_run", "could_not_run_count": 1, "fail": 0, "errors": errors}
    output = update["stdout"] + "\n" + update["stderr"]
    if outcome == "healthy":
        matches = update["exit_code"] == 0 and bool(targets["stdout"].strip())
    else:
        marker = expected[outcome]
        assert marker is not None
        matches = update["exit_code"] == 100 and marker in output and not targets["stdout"].strip()
        if outcome == "wrong_arm64_source":
            matches = matches and "404" in output and "archive.ubuntu.com/ubuntu" in output
    return {"status": "pass" if matches else "block", "could_not_run_count": 0,
            "fail": int(not matches), "outcome": outcome,
            "scope": "Caller-supplied isolated APT process receipts only; source and trust gates separate."}


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



def _stanza_errors(stanza: dict[str, str], index: int) -> list[str]:
    """Validate required fields for distribution suites and exact-path suites."""
    errors: list[str] = []
    suites = stanza.get("suites", "").split()
    required = ("types", "uris", "suites")
    if not suites or any(not suite.endswith("/") for suite in suites):
        required += ("components",)
    missing = [name for name in required if not stanza.get(name)]
    if missing:
        errors.append(f"stanza {index}: missing required fields: {', '.join(missing)}")
    if stanza.get("components") and any(suite.endswith("/") for suite in suites):
        errors.append(f"stanza {index}: exact-path suites must omit Components")
    return errors

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
        errors.extend(_stanza_errors(stanza, index))
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



def compare_index_identities(observed: str, approved: str) -> dict[str, Any]:
    """Compare distinct effective tuples with an externally approved tuple list.

    This component proves identity agreement only. Approval authority, configured
    sources, signing keys, freshness and index integrity remain separate gates.
    URI credentials are deliberately excluded by the existing diagnostic parser.
    """
    actual, actual_errors = parse_index_targets(observed)
    expected, expected_errors = parse_index_targets(approved)
    errors = [*actual_errors, *expected_errors]
    if not actual or not expected:
        errors.append("observed and approved effective tuple lists must be nonempty")
    for row in [*actual, *expected]:
        if (not row["identifier"] or not row["architecture"]
                or (row["identifier"] == "Packages" and "$" in row["architecture"])):
            errors.append("effective index identity is missing or unresolved")
    if errors:
        return {"status": "could_not_run", "could_not_run_count": 1,
                "fail": 0, "errors": errors}
    keys = ("uri", "suite", "architecture", "identifier")
    actual_set = {tuple(row[key] for key in keys) for row in actual}
    expected_set = {tuple(row[key] for key in keys) for row in expected}
    unexpected = sorted(actual_set - expected_set)
    missing = sorted(expected_set - actual_set)
    matches = not unexpected and not missing
    return {"status": "pass" if matches else "block", "could_not_run_count": 0,
            "fail": int(not matches), "unexpected": unexpected, "missing": missing,
            "observed_distinct": len(actual_set), "approved_distinct": len(expected_set)}

def parse_release_digests(text: str, algorithm: str = "sha256") -> tuple[dict[str, tuple[str, int]], list[str]]:
    """Parse SHA256/SHA512 entries; signature authentication is a separate gate."""
    if algorithm not in ("sha256", "sha512"):
        return {}, ["only SHA256 and SHA512 digest sections are supported"]
    section = algorithm.upper()
    digest_length = 64 if algorithm == "sha256" else 128
    entries: dict[str, tuple[str, int]] = {}
    errors: list[str] = []
    active = False
    sections = 0
    for number, line in enumerate(text.splitlines(), 1):
        if line == section + ":":
            sections += 1
            active = True
            continue
        if not active:
            continue
        if not line.startswith(" "):
            active = False
            continue
        fields = line.split()
        if len(fields) != 3:
            errors.append(f"line {number}: malformed {section} entry")
            continue
        digest, size, name = fields
        if (re.fullmatch(r"[0-9a-f]{" + str(digest_length) + r"}", digest) is None or not size.isascii()
                or not size.isdecimal() or len(size) > 20 or name.startswith("/")
                or any(part in ("", ".", "..") for part in name.split("/"))):
            errors.append(f"line {number}: invalid {section} digest, size or relative path")
            continue
        if name in entries:
            errors.append(f"line {number}: duplicate {section} path {name}")
            continue
        entries[name] = (digest, int(size))
    if sections != 1 or not entries:
        errors.append(f"exactly one nonempty {section} section required")
    return entries, errors


def parse_release_sha256(text: str) -> tuple[dict[str, tuple[str, int]], list[str]]:
    """Retain the SHA256 parser API for callers that explicitly require SHA256."""
    return parse_release_digests(text)


def check_release_index(payload: str, meta_key: str, content: bytes,
                        algorithm: str = "sha256") -> dict[str, Any]:
    """Compare decompressed index bytes to a separately signature-verified Release.

    PASS establishes digest and size consistency only. Signature verification,
    repository approval, freshness and complete index coverage are separate gates.
    """
    entries, errors = parse_release_digests(payload, algorithm)
    if errors:
        return {"status": "could_not_run", "could_not_run_count": 1,
                "fail": 0, "errors": errors}
    expected = entries.get(meta_key)
    if expected is None:
        return {"status": "could_not_run", "could_not_run_count": 1,
                "fail": 0, "errors": ["index path is absent from the SHA256 manifest"]}
    digest = hashlib.new(algorithm, content).hexdigest()
    matches = (digest, len(content)) == expected
    return {"status": "pass" if matches else "block", "could_not_run_count": 0,
            "fail": int(not matches), "algorithm": algorithm, "expected_" + algorithm: expected[0],
            "expected_bytes": expected[1], "actual_" + algorithm: digest,
            "actual_bytes": len(content)}



def check_index_coverage(payload: str, expected_meta_keys: list[str],
                         observed_meta_keys: list[str], algorithm: str = "sha256") -> dict[str, Any]:
    """Resolve expected-but-absent indices against a separately verified Release.

    Empty digest AND size must agree. This component does not authenticate the
    manifest, derive the configured targets, or validate observed index bytes.
    """
    entries, errors = parse_release_digests(payload, algorithm)
    if not expected_meta_keys or any(not key for key in expected_meta_keys):
        errors.append("configured expected index paths must be nonempty")
    if errors:
        return {"status": "could_not_run", "could_not_run_count": 1,
                "fail": 0, "errors": errors}
    absent = sorted(set(expected_meta_keys) - set(observed_meta_keys))
    unresolved = [key for key in absent if key not in entries]
    empty_tuple = (hashlib.new(algorithm, b"").hexdigest(), 0)
    empty = [key for key in absent if entries.get(key) == empty_tuple]
    missing = [key for key in absent if key in entries and key not in empty]
    return {"status": "block" if missing else "could_not_run" if unresolved else "pass",
            "could_not_run_count": int(bool(unresolved)), "fail": int(bool(missing)),
            "missing_nonempty": missing, "manifest_declared_empty": empty,
            "unresolved_manifest_paths": unresolved}


def check_release_freshness(payload: str, observed_at: datetime,
                            max_age_seconds: int | None = None) -> dict[str, Any]:
    """Check signed-payload dates against the caller's explicit freshness policy.

    This component does not authenticate the payload or approve the policy. A
    repository without Valid-Until requires a configured maximum age.
    """
    fields: dict[str, str] = {}
    try:
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("observation time requires a timezone")
        if max_age_seconds is not None and (type(max_age_seconds) is not int or max_age_seconds <= 0):
            raise ValueError("maximum age must be a positive integer or absent")
        for line in payload.splitlines():
            name, separator, value = line.partition(":")
            if separator and name.lower() in ("date", "valid-until"):
                name = name.lower()
                if name in fields:
                    raise ValueError("duplicate Release date field")
                fields[name] = value.strip()
        issued = parsedate_to_datetime(fields["date"])
        expires = parsedate_to_datetime(fields["valid-until"]) if "valid-until" in fields else None
        if issued.utcoffset() is None or (expires is not None and expires.utcoffset() is None):
            raise ValueError("Release dates require timezones")
        if expires is None and max_age_seconds is None:
            raise ValueError("Release without Valid-Until requires an explicit maximum age")
        deadline = issued + timedelta(seconds=max_age_seconds) if max_age_seconds is not None else expires
    except (KeyError, ValueError, OverflowError) as error:
        return {"status": "could_not_run", "could_not_run_count": 1,
                "fail": 0, "errors": [str(error)]}
    assert deadline is not None
    valid = (issued <= observed_at < deadline
             and (expires is None or issued < expires and observed_at < expires))
    return {"status": "pass" if valid else "block", "could_not_run_count": 0,
            "fail": int(not valid), "issued_at": issued.isoformat(),
            "valid_until": expires.isoformat() if expires is not None else None,
            "policy_deadline": deadline.isoformat(), "observed_at": observed_at.isoformat()}

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
