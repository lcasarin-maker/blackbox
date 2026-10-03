from __future__ import annotations

import json
from pathlib import Path
import secrets
from typing import Any
from urllib.parse import urlencode, urlunsplit

import pytest

from tools import apt_sources


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
