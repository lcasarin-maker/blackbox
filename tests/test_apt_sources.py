from __future__ import annotations

import json
from pathlib import Path
import secrets
from typing import Any
from urllib.parse import urlencode, urlunsplit

import pytest

from tools import apt_sources


def test_index_coverage_distinguishes_empty_nonempty_and_unresolved() -> None:
    import hashlib
    digest = hashlib.sha256(b"").hexdigest()
    payload = f"SHA256:\n {digest} 0 Empty\n {'a' * 64} 8 Nonempty\n"
    baseline = apt_sources.check_index_coverage(payload, ["Empty", "Nonempty"], ["Nonempty"])
    assert baseline["status"] == "pass"
    assert baseline["manifest_declared_empty"] == ["Empty"]
    assert baseline["could_not_run_count"] == baseline["fail"] == 0
    negative = apt_sources.check_index_coverage(payload, ["Empty", "Nonempty"], [])
    assert negative["status"] == "block" and negative["missing_nonempty"] == ["Nonempty"]
    incomplete = apt_sources.check_index_coverage(payload, ["Absent"], [])
    assert incomplete["status"] == "could_not_run" and incomplete["could_not_run_count"] == 1
    both = apt_sources.check_index_coverage(payload, ["Absent", "Nonempty"], [])
    assert both["fail"] == both["could_not_run_count"] == 1
    for keys in ([], [""]):
        assert apt_sources.check_index_coverage(payload, keys, [])["status"] == "could_not_run"
    assert apt_sources.check_index_coverage("invalid", ["Empty"], [])["status"] == "could_not_run"
    wrong_empty = f"SHA256:\n {'a' * 64} 0 Empty\n"
    assert apt_sources.check_index_coverage(wrong_empty, ["Empty"], [])["status"] == "block"


def test_deb822_comments_continuations_and_blank_stanzas() -> None:
    stanzas, errors = apt_sources.parse_deb822(
        "# before\nTypes: deb\n# within\nURIs: https://ports.ubuntu.com/ubuntu-ports\n"
        "Suites: noble\nComponents: main\nSigned-By: /key.gpg\n Architectures: arm64\n\n"
        "Types: deb-src\nURIs: https://example.test/ubuntu\nSuites: noble\nComponents: main\n")
    assert errors == []
    assert stanzas[0]["signed-by"] == "/key.gpg Architectures: arm64"
    assert stanzas[1]["types"] == "deb-src"


def test_deb822_reports_malformed_duplicate_and_missing_fields() -> None:
    stanzas, errors = apt_sources.parse_deb822(
        " orphan\nTypes: deb\nTypes: deb-src\nURIs: https://example.test/ubuntu\n"
        "Suites: noble\nComponents: main\nBad Field: nope\nno-colon\n")
    assert len(stanzas) == 1
    assert any("continuation without a field" in error for error in errors)
    assert any("duplicate field Types" in error for error in errors)
    assert any("malformed field name" in error for error in errors)
    assert any("expected Field: value" in error for error in errors)
    _, missing = apt_sources.parse_deb822("Types: deb\n")
    assert "missing required fields" in missing[0]
    assert apt_sources.parse_deb822("") == ([], [])
    assert apt_sources.parse_deb822("\n") == ([], [])


def test_index_target_parser_preserves_literal_tuple_fields() -> None:
    rows, errors = apt_sources.parse_index_targets(
        "https://ports.ubuntu.com/ubuntu-ports|noble-updates|arm64|Packages\n"
        "https://ports.ubuntu.com/ubuntu-ports|noble|$(ARCHITECTURE)|Translations\n"
        "missing|fields\nbad|tuple\n")
    assert rows[0]["architecture"] == "arm64"
    assert rows[1]["architecture"] == "$(ARCHITECTURE)"
    assert len(errors) == 2
    assert apt_sources.parse_index_targets("\n") == ([], [])


def test_diagnose_flags_only_exact_active_binary_ubuntu_archive_uri() -> None:
    bad, errors = apt_sources.parse_deb822(
        "Types: deb\nURIs: http://archive.ubuntu.com/ubuntu/\nSuites: noble\nComponents: main\n")
    assert errors == []
    target = {"uri": "http://ports.ubuntu.com/ubuntu-ports", "suite": "noble",
              "architecture": "arm64", "identifier": "Packages"}
    report = apt_sources.diagnose(bad, [target, target], "arm64")
    assert report["status"] == "block"
    assert len(report["findings"]) == 1
    assert report["effective_tuple_count"] == 1

    safe, errors = apt_sources.parse_deb822(
        "Types: deb\nURIs: http://ports.ubuntu.com/ubuntu-ports\nSuites: noble\nComponents: main\n")
    spoof, _ = apt_sources.parse_deb822(
        "Types: deb\nURIs: http://archive.ubuntu.com.evil.test/ubuntu\nSuites: noble\nComponents: main\n")
    disabled, _ = apt_sources.parse_deb822(
        "Types: deb\nEnabled: no\nURIs: http://archive.ubuntu.com/ubuntu\nSuites: noble\nComponents: main\n")
    source_only, _ = apt_sources.parse_deb822(
        "Types: deb-src\nURIs: http://archive.ubuntu.com/ubuntu\nSuites: noble\nComponents: main\n")
    assert errors == []
    assert apt_sources.diagnose(safe, [], "arm64")["status"] == "observed"
    assert len(apt_sources.diagnose(safe, [], "arm64")["configured_ubuntu_source_tuples"]) == 1
    assert apt_sources.diagnose(spoof, [], "arm64")["unassessed_source_tuples"]
    skipped_report = apt_sources.diagnose(disabled + source_only, [], "arm64")
    assert skipped_report["findings"] == []
    assert skipped_report["unassessed_source_tuples"] == []
    non_arm64, _ = apt_sources.parse_deb822(
        "Types: deb\nURIs: http://archive.ubuntu.com/ubuntu\nSuites: noble\n"
        "Components: main\nArchitectures: amd64\n")
    assert apt_sources.diagnose(non_arm64, [], "arm64")["findings"] == []


def test_effective_ota_tuple_extracts_versions_without_claiming_support() -> None:
    snapshot = {"effective_stack": {
        "dgx_release": {"status": "ok", "value":
            'DGX_SERIAL_NUMBER="private"\nDGX_SWBUILD_VERSION="7.2.3"\n'
            'DGX_OTA_VERSION="7.4.0"\nDGX_OTA_VERSION="7.6.0"\nDGX_OTA_DATE="2026-09-14"\n'},
        "driver_comparison": {"loaded_version": "580.178.04", "disk_version": "580.178.04",
                              "match": False}},
        "kernel": {"release": "6.17.0-1032-nvidia"}}
    result = apt_sources.effective_ota_tuple(snapshot)
    assert result["status"] == "observed"
    assert result["tuple"]["dgx_ota_version"] == "7.6.0"
    assert result["tuple"]["kernel_release"] == "6.17.0-1032-nvidia"
    assert result["tuple"]["loaded_disk_driver_match"] is True
    assert "private" not in json.dumps(result)
    assert result["support_verdict"] == "not evaluated"
    unknown = apt_sources.effective_ota_tuple({})
    assert unknown == {"status": "could_not_run",
                       "reason": "OTA, kernel, or driver observation unavailable"}

    snapshot["effective_stack"]["driver_comparison"]["disk_version"] = "590.1"
    assert apt_sources.effective_ota_tuple(snapshot)["tuple"]["loaded_disk_driver_match"] is False
    snapshot["effective_stack"]["driver_comparison"]["match"] = "yes"
    invalid_match = apt_sources.effective_ota_tuple(snapshot)
    assert invalid_match["status"] == "observed"
    assert invalid_match["tuple"]["loaded_disk_driver_match"] is False

    blank_kernel = json.loads(json.dumps(snapshot))
    blank_kernel["kernel"]["release"] = "  \t"
    kernel_unknown = apt_sources.effective_ota_tuple(blank_kernel)
    assert kernel_unknown["status"] == "could_not_run"
    assert "kernel_release" in kernel_unknown["missing"]

    blank_driver = json.loads(json.dumps(snapshot))
    blank_driver["effective_stack"]["driver_comparison"]["loaded_version"] = "  \t"
    driver_unknown = apt_sources.effective_ota_tuple(blank_driver)
    assert driver_unknown["status"] == "could_not_run"
    assert "loaded_driver" in driver_unknown["missing"]


def _authenticated_uri(host: str, path: str) -> tuple[str, tuple[str, ...]]:
    username = secrets.token_urlsafe(12)
    password = secrets.token_urlsafe(16)
    query_value = secrets.token_urlsafe(16)
    uri = urlunsplit(("https", f"{username}:{password}@{host}", path,
                      urlencode({"auth": query_value}), ""))
    return uri, (username, password, query_value)


def _ota_snapshot() -> dict[str, Any]:
    return {"effective_stack": {
        "dgx_release": {"status": "ok", "value":
            'DGX_SWBUILD_VERSION="7.2.3"\nDGX_OTA_VERSION="7.6.0"\nDGX_OTA_DATE="2026-09-14"\n'},
        "driver_comparison": {"loaded_version": "580.178.04", "disk_version": "580.178.04",
                              "match": True}},
        "kernel": {"release": "6.17.0-1032-nvidia"}}


def _patch_native(monkeypatch: pytest.MonkeyPatch, source: str,
                  runner: Any) -> None:
    original = Path.read_text

    def read_text(path: Path, *args: Any, **kwargs: Any) -> str:
        if str(path) == "/etc/apt/sources.list.d/ubuntu.sources":
            return source
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text)
    monkeypatch.setattr(apt_sources, "run_readonly", runner)
    monkeypatch.setattr(apt_sources, "capture_memory_profile", _ota_snapshot)


def test_capture_reports_native_readonly_effective_tuple(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    uri, credential_values = _authenticated_uri("ports.ubuntu.com", "/ubuntu-ports")

    def runner(argv: list[str]) -> dict[str, Any]:
        calls.append(argv)
        output = "arm64\n" if argv[0] == "dpkg" else (
            "https://ports.ubuntu.com/ubuntu-ports|noble|arm64|Packages\n")
        return {"status": "ok", "stdout": output}

    _patch_native(monkeypatch,
        f"Types: deb\nURIs: {uri}\nSuites: noble\nComponents: main\n", runner)
    result = apt_sources.capture()
    assert result["status"] == "observed"
    assert result["effective_tuple_count"] == 1
    assert result["captured_index_targets"] == [{
        "uri": "https://ports.ubuntu.com/ubuntu-ports", "suite": "noble",
        "architecture": "arm64", "identifier": "Packages"}]
    assert result["could_not_run_count"] == 0
    serialized = json.dumps(result)
    assert all(value not in serialized for value in credential_values)
    assert calls == [["dpkg", "--print-architecture"], ["apt-get", "indextargets",
        "--format=$(SITE)|$(RELEASE)|$(ARCHITECTURE)|$(IDENTIFIER)"]]


@pytest.mark.parametrize("failure", [FileNotFoundError("gone"), PermissionError("denied"),
                                       OSError("broken"), UnicodeError("bad text")])
def test_capture_preserves_source_read_failures(monkeypatch: pytest.MonkeyPatch,
                                                failure: Exception) -> None:
    def read_text(_path: Path, **_kwargs: Any) -> str:
        raise failure

    monkeypatch.setattr(Path, "read_text", read_text)
    result = apt_sources.capture()
    assert result == {"status": "could_not_run", "error": f"{type(failure).__name__}: {failure}",
                      "could_not_run_count": 1}


def test_capture_rejects_malformed_sources_before_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_native(monkeypatch, "Types: deb\n", lambda _argv: pytest.fail("must not run commands"))
    result = apt_sources.capture()
    assert result["status"] == "could_not_run"
    assert result["source_errors"]

    uri, credentials = _authenticated_uri("mirror.example", "/repo")
    _patch_native(monkeypatch, f"Types: deb\nURIs: {uri}\nSuites: stable\n",
                  lambda _argv: pytest.fail("must not run commands"))
    result = apt_sources.capture()
    assert result["status"] == "could_not_run"
    assert all(value not in json.dumps(result) for value in credentials)


def test_capture_preserves_command_failures_and_unavailable_arch(monkeypatch: pytest.MonkeyPatch) -> None:
    source = "Types: deb\nURIs: https://ports.ubuntu.com/ubuntu-ports\nSuites: noble\nComponents: main\n"
    _patch_native(monkeypatch, source,
                  lambda _argv: {"status": "could_not_run", "error": "dpkg missing"})
    assert apt_sources.capture()["status"] == "could_not_run"

    monkeypatch.setattr(apt_sources, "_read_architecture", lambda: (None, None))
    assert apt_sources.capture()["error"] == "system architecture unavailable"
    monkeypatch.setattr(apt_sources, "_read_architecture", lambda: ("arm64", None))
    _patch_native(monkeypatch, source, lambda argv: {"status": "ok", "stdout": "arm64\n"}
                  if argv[0] == "dpkg" else (_ for _ in ()).throw(ValueError("runner error")))
    assert apt_sources.capture()["status"] == "could_not_run"

    def runner(argv: list[str]) -> dict[str, Any]:
        if argv[0] == "dpkg":
            return {"status": "ok", "stdout": "arm64\n"}
        return {"status": "could_not_run", "returncode": 1, "stderr": "denied"}

    _patch_native(monkeypatch, source, runner)
    assert apt_sources.capture()["status"] == "could_not_run"

    def malformed(argv: list[str]) -> dict[str, Any]:
        return {"status": "ok", "stdout": "arm64\n" if argv[0] == "dpkg" else "bad|tuple\n"}

    monkeypatch.setattr(apt_sources, "_read_architecture", lambda: ("arm64", None))
    _patch_native(monkeypatch, source, malformed)
    assert apt_sources.capture()["target_errors"]

    def truncated(argv: list[str]) -> dict[str, Any]:
        return {"status": "ok", "stdout": "arm64\n"} if argv[0] == "dpkg" else {
            "status": "ok", "stdout": "x" * 100, "stdout_truncated": True}

    _patch_native(monkeypatch, source, truncated)
    result = apt_sources.capture()
    assert result["status"] == "could_not_run"
    assert result["could_not_run_count"] > 0

    uri, credentials = _authenticated_uri("ports.ubuntu.com", "/ubuntu-ports")
    source_with_auth = f"Types: deb\nURIs: {uri}\nSuites: noble\nComponents: main\n"
    def failed_with_auth(argv: list[str]) -> dict[str, Any]:
        if argv[0] == "dpkg":
            return {"status": "ok", "stdout": "arm64\n"}
        return {"status": "could_not_run", "stdout": uri, "stderr": uri}

    _patch_native(monkeypatch, source_with_auth, failed_with_auth)
    result = apt_sources.capture()
    assert result["status"] == "could_not_run"
    assert all(value not in json.dumps(result) for value in credentials)


def test_uri_credentials_are_redacted_and_malformed_uris_are_unknown() -> None:
    port_uri, port_credentials = _authenticated_uri("ports.ubuntu.com", "/ubuntu-ports")
    credentials, _ = apt_sources.parse_deb822(
        f"Types: deb\nURIs: {port_uri}\nSuites: noble\nComponents: main\n")
    safe = apt_sources._redact_stanzas(credentials)
    assert safe[0]["uris"] == "https://ports.ubuntu.com/ubuntu-ports"
    assert all(value not in json.dumps(safe) for value in port_credentials)
    malformed, _ = apt_sources.parse_deb822(
        "Types: deb\nURIs: https://[bad\nSuites: noble\nComponents: main\n")
    report = apt_sources.diagnose(malformed, [], "arm64")
    assert report["status"] == "could_not_run"
    assert report["malformed_source_uri_count"] == 1

    archive_uri, archive_credentials = _authenticated_uri("archive.ubuntu.com", "/ubuntu")
    blocked, _ = apt_sources.parse_deb822(
        f"Types: deb\nURIs: {archive_uri}\nSuites: noble\nComponents: main\n")
    mirror_uri, mirror_credentials = _authenticated_uri("mirror.example", "/repo")
    targets, errors = apt_sources.parse_index_targets(
        f"{mirror_uri}|stable|arm64|Packages\n")
    assert errors == []
    assert targets[0]["uri"] == "https://mirror.example/repo"
    all_redacted_outputs = json.dumps([apt_sources.diagnose(blocked, [], "arm64"),
                                       apt_sources._redact_stanzas(blocked), targets])
    assert all(value not in all_redacted_outputs for value in
               (*archive_credentials, *mirror_credentials))


def test_index_targets_reject_uris_without_endpoint_identity_and_redact_secrets() -> None:
    username = secrets.token_urlsafe(12)
    password = secrets.token_urlsafe(16)
    query_secret = secrets.token_urlsafe(16)
    ipv6_uri = urlunsplit(("https", f"{username}:{password}@[2001:db8::7]:8443",
                           "/ubuntu", urlencode({"token": query_secret}), ""))
    rows, errors = apt_sources.parse_index_targets(
        "https:///ubuntu|noble|arm64|Packages\n"
        "ports.ubuntu.com/ubuntu-ports|noble|arm64|Packages\n"
        f"{ipv6_uri}|noble|arm64|Packages\n")
    assert rows == [{"uri": "https://[2001:db8::7]:8443/ubuntu", "suite": "noble",
                     "architecture": "arm64", "identifier": "Packages"}]
    assert errors == ["line 1: malformed index target URI",
                      "line 2: malformed index target URI"]
    serialized = json.dumps({"rows": rows, "errors": errors})
    assert all(secret not in serialized for secret in (username, password, query_secret))


def test_main_prints_json_and_returns_status_code(monkeypatch: pytest.MonkeyPatch,
                                                 capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(apt_sources, "capture", lambda: {"status": "block", "findings": ["bad"]})
    assert apt_sources.main() == 1
    assert json.loads(capsys.readouterr().out)["status"] == "block"
    monkeypatch.setattr(apt_sources, "capture", lambda: {"status": "could_not_run",
                                                          "could_not_run_count": 1})
    assert apt_sources.main() == 2


def test_module_entrypoint_is_executable(capsys: pytest.CaptureFixture[str]) -> None:
    import runpy
    with pytest.raises(SystemExit) as result:
        runpy.run_path(str(Path(apt_sources.__file__)), run_name="__main__")
    assert result.value.code in (0, 1, 2)
    assert json.loads(capsys.readouterr().out)["status"] in ("observed", "block")


def test_release_index_checks_native_signed_baseline_and_same_size_mutation() -> None:
    import subprocess

    evidence = (Path(__file__).resolve().parents[1] / "tasks/evidence"
                / "DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/signed-integrity-canary")
    signed = evidence / "baseline.InRelease"
    signature = subprocess.run(
        ["gpgv", "--keyring", str(evidence / "canary-public-keyring.gpg"), str(signed)],
        capture_output=True, text=True, timeout=10,
    )
    assert signature.returncode == 0, signature.stderr
    payload = signed.read_text(encoding="utf-8")
    content = (evidence / "baseline.Packages").read_bytes()
    baseline = apt_sources.check_release_index(payload, "Packages", content)
    assert baseline["status"] == "pass" and baseline["could_not_run_count"] == 0
    changed = bytes([content[0] ^ 1]) + content[1:]
    negative = apt_sources.check_release_index(payload, "Packages", changed)
    assert negative["status"] == "block" and negative["fail"] == 1
    assert negative["actual_bytes"] == negative["expected_bytes"]
    assert negative["actual_sha256"] != negative["expected_sha256"]
    assert apt_sources.check_release_index(payload, "Packages", content + b"x")["status"] == "block"
    missing = apt_sources.check_release_index(payload, "unlisted/Packages", content)
    assert missing["status"] == "could_not_run" and missing["fail"] == 0


@pytest.mark.parametrize("payload", [
    "Origin: example\n",
    "SHA256:\nOther: empty\n",
    "SHA256:\n malformed\n",
    "SHA256:\n " + "g" * 64 + " 3 Packages\n",
    "SHA256:\n " + "a" * 64 + " -1 Packages\n",
    "SHA256:\n " + "a" * 64 + " ٣ Packages\n",
    "SHA256:\n " + "a" * 64 + " " + "1" * 21 + " Packages\n",
    "SHA256:\n " + "a" * 64 + " 3 /Packages\n",
    "SHA256:\n " + "a" * 64 + " 3 ../Packages\n",
    "SHA256:\n " + "a" * 64 + " 3 main//Packages\n",
    "SHA256:\n " + "a" * 64 + " 3 main/./Packages\n",
    "SHA256:\n " + "a" * 64 + " 3 Packages\n " + "b" * 64 + " 3 Packages\n",
    "SHA256:\n " + "a" * 64 + " 3 Packages\nSHA256:\n " + "b" * 64 + " 3 Other\n",
])
def test_release_manifest_rejects_ambiguous_or_unsafe_entries(payload: str) -> None:
    result = apt_sources.check_release_index(payload, "Packages", b"abc")
    assert result["status"] == "could_not_run" and result["could_not_run_count"] == 1
    assert result["fail"] == 0 and result["errors"]


def test_effective_index_identity_comparison_preserves_full_tuple():
    from tools.apt_sources import compare_index_identities

    approved = "https://ports.ubuntu.com/ubuntu-ports|noble|arm64|Packages\n"
    assert compare_index_identities(approved + approved, approved)["status"] == "pass"
    for old, new in (("ports.ubuntu.com", "archive.ubuntu.com"),
                     ("noble", "noble-updates"), ("arm64", "amd64"),
                     ("Packages", "Translations")):
        result = compare_index_identities(approved.replace(old, new), approved)
        assert result["status"] == "block"
        assert result["fail"] == 1 and result["could_not_run_count"] == 0
        assert len(result["unexpected"]) == len(result["missing"]) == 1
    flat = "https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/sbsa||arm64|Packages"
    assert compare_index_identities(flat, flat)["status"] == "pass"
    assert compare_index_identities(approved + flat, approved)["status"] == "block"
    assert compare_index_identities(approved, approved + flat)["status"] == "block"


@pytest.mark.parametrize("observed,approved", [
    ("", ""), ("malformed", "malformed"),
    ("https://example.test|noble||Packages", "https://example.test|noble||Packages"),
    ("https://example.test|noble|arm64|", "https://example.test|noble|arm64|"),
    ("https://example.test|noble|$(ARCHITECTURE)|Packages", "https://example.test|noble|arm64|Packages"),
])
def test_effective_index_identity_incomplete_input_is_could_not_run(observed, approved):
    from tools.apt_sources import compare_index_identities

    result = compare_index_identities(observed, approved)
    assert result["status"] == "could_not_run"
    assert result["could_not_run_count"] == 1 and result["fail"] == 0


@pytest.mark.parametrize("payload,age,expected", [
    ("Date: Sun, 04 Oct 2026 00:00:00 UTC\nValid-Until: Mon, 05 Oct 2026 00:00:00 UTC", None, "pass"),
    ("-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA512\nDate: Sun, 04 Oct 2026 00:00:00 UTC", 3600, "pass"),
    ("Date: Sun, 04 Oct 2026 00:00:00 UTC", 1800, "block"),
    ("Date: Mon, 05 Oct 2026 00:00:00 UTC", 3600, "block"),
    ("Date: Sun, 04 Oct 2026 00:00:00 UTC\nValid-Until: Sun, 04 Oct 2026 00:30:00 UTC", None, "block"),
    ("Date: Sun, 04 Oct 2026 00:00:00 UTC\nValid-Until: Sat, 03 Oct 2026 00:00:00 UTC", 3600, "block"),
    ("Date: Sun, 04 Oct 2026 00:00:00 UTC", None, "could_not_run"),
    ("", 3600, "could_not_run"),
    ("Date: invalid", 3600, "could_not_run"),
    ("Date: Sun, 04 Oct 2026 00:00:00", 3600, "could_not_run"),
    ("Date: Sun, 04 Oct 2026 00:00:00 UTC\nValid-Until: Mon, 05 Oct 2026 00:00:00", 3600, "could_not_run"),
    ("Date: Sun, 04 Oct 2026 00:00:00 UTC\nDate: Sun, 04 Oct 2026 00:00:00 UTC", 3600, "could_not_run"),
    ("Date: Sun, 04 Oct 2026 00:00:00 UTC", True, "could_not_run"),
    ("Date: Sun, 04 Oct 2026 00:00:00 UTC", 0, "could_not_run"),
    ("Date: Sun, 04 Oct 2026 00:00:00 UTC", 10**50, "could_not_run"),
])
def test_release_freshness_requires_valid_dates_and_explicit_policy(payload, age, expected):
    from datetime import datetime, timezone
    from tools.apt_sources import check_release_freshness

    result = check_release_freshness(payload, datetime(2026, 10, 4, 0, 30, tzinfo=timezone.utc), age)
    assert result["status"] == expected
    assert result["could_not_run_count"] == int(expected == "could_not_run")
    assert result["fail"] == int(expected == "block")


def test_release_freshness_rejects_naive_observation_time():
    from datetime import datetime
    from tools.apt_sources import check_release_freshness

    assert check_release_freshness("", datetime(2026, 10, 4), 3600)["status"] == "could_not_run"


def test_sha512_only_signed_manifest_index_and_negative_controls():
    import hashlib
    from pathlib import Path
    from tools.apt_sources import check_release_index, parse_release_digests

    manifest = (Path(__file__).resolve().parents[1] / "tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/all-cached-release-signatures/nvidia.github.io_libnvidia-container_stable_deb_arm64_InRelease").read_text(encoding="utf-8")
    entries, errors = parse_release_digests(manifest, "sha512")
    assert not errors and len(entries["Packages"][0]) == 128
    content = b"controlled index bytes"
    payload = "SHA512:\n " + hashlib.sha512(content).hexdigest() + " " + str(len(content)) + " Packages\n"
    positive = check_release_index(payload, "Packages", content, "sha512")
    assert positive["status"] == "pass" and positive["algorithm"] == "sha512"
    assert check_release_index(payload, "Packages", content[:-1] + b"X", "sha512")["status"] == "block"
    assert check_release_index(payload, "Packages", content)["status"] == "could_not_run"
    assert check_release_index(payload, "Packages", content, "md5")["status"] == "could_not_run"
    assert parse_release_digests("SHA512:\n " + "a" * 64 + " 1 Packages", "sha512")[1]


def test_sha256_compatibility_parser_retains_its_algorithm():
    from tools.apt_sources import parse_release_sha256

    assert parse_release_sha256("SHA256:\n " + "a" * 64 + " 1 Packages")[0] == {"Packages": ("a" * 64, 1)}
    assert parse_release_sha256("SHA512:\n " + "a" * 128 + " 1 Packages")[1]


@pytest.mark.parametrize("suite,components,valid", [
    ("/", "", True), ("stable/", "", True),
    ("/", "main", False), ("stable", "", False),
    ("stable", "main", True), ("stable /", "main", False),
])
def test_deb822_exact_path_requires_omitted_components(suite, components, valid):
    from tools.apt_sources import parse_deb822

    payload = f"Types: deb\nURIs: https://example.test/repository\nSuites: {suite}\n"
    if components:
        payload += f"Components: {components}\n"
    stanzas, errors = parse_deb822(payload)
    assert len(stanzas) == 1 and bool(errors) == (not valid)


def test_signature_verifier_authenticates_exact_bytes_and_rejects_mutation(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1] / 'tasks/evidence'
    # The first canary's key was generated with a 1-day expiry; since 2026-10-05 gpgv reports
    # EXPKEYSIG for it. It stays as the expired-key negative control; the never-expiring canary
    # (collector archived beside it) is the positive subject.
    expired = root / 'DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/signed-integrity-canary'
    stale = apt_sources.verify_release_signature(expired / 'baseline.InRelease', [expired / 'canary-public-keyring.gpg'])
    assert stale['status'] == 'block' and stale['fail'] == 1 and stale['could_not_run_count'] == 0, stale
    evidence = root / 'DEBT-PRUEBAS-SIN-FICHA-CRUDA-01/signature-canary'
    subject = evidence / 'baseline.InRelease'
    keys = [evidence / 'canary-public-keyring.gpg']
    baseline = apt_sources.verify_release_signature(subject, keys)
    assert baseline['status'] == 'pass', baseline
    altered = tmp_path / 'altered.InRelease'
    altered.write_bytes(subject.read_bytes().replace(b'Suite:', b'Suitx:', 1))
    negative = apt_sources.verify_release_signature(altered, keys)
    assert negative['status'] == 'block', negative
    assert negative['fail'] == 1 and negative['could_not_run_count'] == 0
    assert baseline['manifest_sha256'] != negative['manifest_sha256']
    assert 'cudatools@' not in json.dumps(baseline)


@pytest.mark.parametrize('case', ['missing', 'empty', 'large', 'directory', 'symlink', 'fifo', 'no_keys'])
def test_signature_input_unavailable_is_unknown(tmp_path: Path, case: str) -> None:
    import os
    path = tmp_path / 'input'
    key = tmp_path / 'key'
    key.write_bytes(b'key')
    if case == 'empty':
        path.write_bytes(b'')
    elif case == 'large':
        with path.open('wb') as stream:
            stream.truncate(8 * 1024 * 1024 + 1)
    elif case == 'directory':
        path.mkdir()
    elif case == 'symlink':
        path.symlink_to(key)
    elif case == 'fifo':
        os.mkfifo(path)
    elif case == 'no_keys':
        path.write_bytes(b'payload')
    result = apt_sources.verify_release_signature(path, [] if case == 'no_keys' else [key])
    assert result['status'] == 'could_not_run'
    assert result['could_not_run_count'] == 1 and result['fail'] == 0


@pytest.mark.parametrize(('capture', 'expected'), [
    ({'status': 'could_not_run'}, 'could_not_run'),
    ({'status': 'ok', 'returncode': 0, 'stdout_truncated': True}, 'could_not_run'),
    ({'status': 'ok', 'returncode': 0, 'stderr_truncated': True}, 'could_not_run'),
    ({'status': 'observed', 'returncode': 2, 'stdout': '[GNUPG:] NO_PUBKEY ABC'}, 'could_not_run'),
    ({'status': 'ok', 'returncode': 0, 'stdout': '[GNUPG:] GOODSIG ABC Contact'}, 'could_not_run'),
    ({'status': 'observed', 'returncode': 1, 'stdout': '[GNUPG:] BADSIG ABC Contact'}, 'block'),
    ({'status': 'ok', 'returncode': 0, 'stdout': '[GNUPG:] REVKEYSIG ABC Contact'}, 'block'),
])
def test_signature_native_outcomes_preserve_unknowns(capture: dict, expected: str) -> None:
    result = apt_sources._signature_verdict(capture)
    assert result['status'] == expected
    assert result['could_not_run_count'] == int(expected == 'could_not_run')
    assert result['fail'] == int(expected == 'block')


def test_signature_verifier_cannot_authenticate_with_an_unrelated_keyring() -> None:
    root = Path(__file__).resolve().parents[1]
    evidence = root / 'tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01'
    result = apt_sources.verify_release_signature(
        evidence / 'signed-integrity-canary/baseline.InRelease',
        [evidence / 'all-cached-release-signatures/keyrings/09-nvidia-container-toolkit-keyring.gpg'])
    assert result['status'] == 'could_not_run', result
    assert result['could_not_run_count'] == 1 and result['fail'] == 0
    assert result['validsig_records'] == []
    assert '--homedir' in result['command']
    temporary = Path(result['command'][result['command'].index('--homedir') + 1])
    assert not temporary.exists()


def _update_control_inputs(outcome: str) -> tuple[dict, dict, dict, Path]:
    base = Path(__file__).resolve().parents[1] / 'tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01'
    source = {'healthy': 'healthy-source-canary', 'wrong_arm64_source': 'wrong-source-canary'}.get(outcome, 'signed-integrity-canary')
    rows = json.loads((base / source / 'run.json').read_text(encoding="utf-8"))['commands']
    offset = {'healthy': 0, 'wrong_arm64_source': 0, 'bad_package_hash': 6, 'bad_release_signature': 9}[outcome]
    config, update, targets = rows[offset:offset + 3]
    import re
    isolated = re.search(r'^Dir::Etc "(/tmp/[^/]+)/', config['stdout'], re.MULTILINE)
    assert isolated is not None
    return config, update, targets, Path(isolated.group(1))


@pytest.mark.parametrize('outcome', ['healthy', 'wrong_arm64_source', 'bad_package_hash', 'bad_release_signature'])
def test_native_isolated_canary_controls_recompute_outcome_and_detect_false_success(outcome: str) -> None:
    config, update, targets, root = _update_control_inputs(outcome)
    baseline = apt_sources.check_isolated_update_control(config, update, targets, root, outcome)
    assert baseline['status'] == 'pass', baseline
    changed = {**update, 'exit_code': 100 if outcome == 'healthy' else 0}
    negative = apt_sources.check_isolated_update_control(config, changed, targets, root, outcome)
    assert negative['status'] == 'block' and negative['fail'] == 1
    assert negative['could_not_run_count'] == 0
    if outcome != 'healthy':
        reused = {**targets, 'stdout': '/tmp/old-cache/Packages|Packages\n'}
        assert apt_sources.check_isolated_update_control(config, update, reused, root, outcome)['status'] == 'block'


@pytest.mark.parametrize('mutation', ['host_directory', 'duplicate_directory', 'hook', 'error_mode', 'bad_receipt', 'wrong_command', 'failed_config', 'failed_targets'])
def test_isolated_canary_unsafe_or_unavailable_receipts_cannot_pass(mutation: str) -> None:
    config, update, targets, root = _update_control_inputs('healthy')
    config, update, targets = dict(config), dict(update), dict(targets)
    if mutation == 'host_directory':
        config['stdout'] = config['stdout'].replace(str(root / 'etc'), '/etc/apt')
    elif mutation == 'duplicate_directory':
        config['stdout'] += f'Dir::Etc "{root}/etc";\n'
    elif mutation == 'hook':
        config['stdout'] += 'APT::Update::Post-Invoke:: "touch /tmp/unexpected";\n'
    elif mutation == 'error_mode':
        config['stdout'] = config['stdout'].replace('APT::Update::Error-Mode "any";', '')
    elif mutation == 'bad_receipt':
        update['exit_code'] = True
    elif mutation == 'wrong_command':
        update['argv'] = ['apt-get', 'install', 'package']
    elif mutation == 'failed_config':
        config['exit_code'] = 1
    else:
        targets['exit_code'] = 1
    result = apt_sources.check_isolated_update_control(config, update, targets, root, 'healthy')
    assert result['status'] == 'could_not_run', result
    assert result['could_not_run_count'] == 1 and result['fail'] == 0


def test_isolated_canary_rejects_unknown_outcome() -> None:
    config, update, targets, root = _update_control_inputs('healthy')
    with pytest.raises(ValueError, match='unsupported'):
        apt_sources.check_isolated_update_control(config, update, targets, root, 'invented')


@pytest.mark.parametrize("root", [Path("relative"), Path("/tmp/bb-canary/nested"), Path("/tmp/..")])
def test_isolated_canary_requires_its_own_direct_temporary_root(root: Path) -> None:
    config, update, targets, _ = _update_control_inputs("healthy")
    result = apt_sources.check_isolated_update_control(config, update, targets, root, "healthy")
    assert result["status"] == "could_not_run", result
    assert result["could_not_run_count"] == 1 and result["fail"] == 0


@pytest.mark.parametrize('setting', ['insecure', 'missing_security_setting', 'wrong_architecture'])
def test_isolated_canary_must_preserve_security_and_arm64_scope(setting: str) -> None:
    config, update, targets, root = _update_control_inputs('healthy')
    text = config['stdout']
    if setting == 'insecure':
        text = text.replace('Acquire::AllowInsecureRepositories "0";', 'Acquire::AllowInsecureRepositories "1";')
    elif setting == 'missing_security_setting':
        text = text.replace('Acquire::AllowInsecureRepositories "0";', '')
    else:
        text = text.replace('APT::Architecture "arm64";', 'APT::Architecture "amd64";')
    result = apt_sources.check_isolated_update_control({**config, 'stdout': text}, update, targets, root, 'healthy')
    assert result['status'] == 'could_not_run', result
    assert result['could_not_run_count'] == 1 and result['fail'] == 0


@pytest.mark.parametrize('position', [0, 1, 2])
@pytest.mark.parametrize('field', ['stdout_truncated', 'stderr_truncated'])
def test_isolated_canary_truncated_capture_is_unknown(position: int, field: str) -> None:
    config, update, targets, root = _update_control_inputs('wrong_arm64_source')
    baseline = apt_sources.check_isolated_update_control(config, update, targets, root, 'wrong_arm64_source')
    assert baseline['status'] == 'pass', baseline
    rows = [dict(config), dict(update), dict(targets)]
    rows[position][field] = True
    result = apt_sources.check_isolated_update_control(rows[0], rows[1], rows[2], root, 'wrong_arm64_source')
    assert result['status'] == 'could_not_run', result
    assert result['could_not_run_count'] == 1 and result['fail'] == 0
