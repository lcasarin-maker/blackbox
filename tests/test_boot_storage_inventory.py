"""Read-only backup target and current boot inventory controls."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tools.host_diagnostics import backup_destination_check, boot_state_inventory


def _mount_output(target: str = "/mnt/backup", source: str = "/dev/sdb1",
                  uuid: str | None = "expected-uuid") -> str:
    record: dict[str, Any] = {"target": target, "source": source}
    if uuid is not None:
        record["uuid"] = uuid
    return json.dumps({"filesystems": [record]})


def _runner(stdout: str, returncode: int = 0, stderr: str = ""):
    def run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert argv == ["findmnt", "--json", "--mountpoint", "/mnt/backup",
                        "--output", "TARGET,SOURCE,UUID"]
        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)
    return run


def _mountpoint(root: Path) -> None:
    (root / "mnt/backup").mkdir(parents=True)


def test_backup_destination_requires_exact_mount_and_identity(tmp_path: Path) -> None:
    _mountpoint(tmp_path)
    result = backup_destination_check(tmp_path, "/mnt/backup", "/dev/sdb1", "expected-uuid",
                                      _runner(_mount_output()))
    assert result["status"] == "pass"
    assert result["mismatches"] == []


@pytest.mark.parametrize("source,uuid", [
    ("/dev/sdb1", "different-uuid"),
    ("/dev/sdc1", "expected-uuid"),
])
def test_backup_destination_blocks_identity_mismatch(
    tmp_path: Path, source: str, uuid: str,
) -> None:
    _mountpoint(tmp_path)
    result = backup_destination_check(
        tmp_path, "/mnt/backup", "/dev/sdb1", "expected-uuid",
        _runner(_mount_output(source=source, uuid=uuid)),
    )
    assert result["status"] == "block"
    assert result["mismatches"]


def test_existing_directory_without_mount_blocks_before_backup(tmp_path: Path) -> None:
    _mountpoint(tmp_path)
    result = backup_destination_check(
        tmp_path, "/mnt/backup", "/dev/sdb1", "expected-uuid",
        _runner("", returncode=1),
    )
    assert result["status"] == "block"
    assert result["reason"] == "exact mountpoint is not mounted"


def test_mount_on_parent_is_not_exact_target(tmp_path: Path) -> None:
    _mountpoint(tmp_path)
    result = backup_destination_check(
        tmp_path, "/mnt/backup", "/dev/sdb1", "expected-uuid",
        _runner(_mount_output(target="/mnt")),
    )
    assert result["status"] == "block"
    assert result["mismatches"] == ["target"]


def test_backup_destination_unknown_without_explicit_expected_identity(tmp_path: Path) -> None:
    assert backup_destination_check(tmp_path, None, "/dev/sdb1", "uuid")["status"] == "unknown"
    assert backup_destination_check(tmp_path, "/mnt/backup", "", "uuid")["status"] == "unknown"


def test_backup_destination_rejects_relative_mountpoint(tmp_path: Path) -> None:
    result = backup_destination_check(tmp_path, "mnt/backup", "/dev/sdb1", "uuid",
                                      _runner(_mount_output()))
    assert result["status"] == "unknown"


def test_backup_destination_never_queries_live_findmnt_for_fixture_root(tmp_path: Path) -> None:
    result = backup_destination_check(tmp_path, "/mnt/backup", "/dev/sdb1", "uuid")
    assert result["status"] == "unknown"
    assert "injected findmnt runner" in result["reason"]


def test_backup_destination_blocks_missing_mountpoint_directory(tmp_path: Path) -> None:
    result = backup_destination_check(tmp_path, "/mnt/backup", "/dev/sdb1", "uuid",
                                      _runner("", returncode=1))
    assert result == {"status": "block", "reason": "mountpoint directory absent"}


def test_backup_destination_rejects_path_escape_and_parent_segments(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-backup"
    outside.mkdir()
    (tmp_path / "mnt").mkdir()
    (tmp_path / "mnt/backup").symlink_to(outside, target_is_directory=True)
    escaped = backup_destination_check(tmp_path, "/mnt/backup", "/dev/sdb1", "uuid",
                                      _runner(_mount_output()))
    parent = backup_destination_check(tmp_path, "/mnt/../outside-backup", "/dev/sdb1", "uuid",
                                     _runner(_mount_output()))
    assert escaped["status"] == "unknown"
    assert parent["status"] == "unknown"


def test_backup_destination_unknown_on_inaccessible_query(tmp_path: Path) -> None:
    _mountpoint(tmp_path)

    def denied(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 2, "", "permission denied")

    result = backup_destination_check(tmp_path, "/mnt/backup", "/dev/sdb1", "uuid", denied)
    assert result["status"] == "unknown"
    assert result["query"]["status"] == "could_not_run"


@pytest.mark.parametrize("output", ["{", "{}",
                                    '{"filesystems": [{"target":"/mnt/backup","source":"/dev/sdb1"}]}'])
def test_backup_destination_unknown_on_unusable_identity_json(tmp_path: Path, output: str) -> None:
    _mountpoint(tmp_path)
    result = backup_destination_check(
        tmp_path, "/mnt/backup", "/dev/sdb1", "uuid", _runner(output))
    assert result["status"] == "unknown"


def test_backup_destination_blocks_successful_query_without_target_mount(tmp_path: Path) -> None:
    _mountpoint(tmp_path)
    result = backup_destination_check(
        tmp_path, "/mnt/backup", "/dev/sdb1", "uuid", _runner('{"filesystems": []}'))
    assert result["status"] == "block"


def test_backup_destination_unknown_when_findmnt_identity_is_ambiguous(tmp_path: Path) -> None:
    _mountpoint(tmp_path)
    result = backup_destination_check(
        tmp_path, "/mnt/backup", "/dev/sdb1", "uuid",
        _runner('{"filesystems": [{}, {}]}'),
    )
    assert result["status"] == "unknown"


def test_backup_destination_blocks_when_mountpoint_is_a_file(tmp_path: Path) -> None:
    (tmp_path / "mnt").mkdir()
    (tmp_path / "mnt/backup").write_text("empty target file", encoding="utf-8")
    result = backup_destination_check(tmp_path, "/mnt/backup", "/dev/sdb1", "uuid",
                                      _runner(_mount_output()))
    assert result["status"] == "block"


def test_boot_state_reports_parameter_command_line_and_artifact_presence(tmp_path: Path) -> None:
    (tmp_path / "sys/module/nvidia_drm/parameters").mkdir(parents=True)
    (tmp_path / "sys/module/nvidia_drm/parameters/modeset").write_text("Y\n", encoding="utf-8")
    (tmp_path / "proc").mkdir()
    (tmp_path / "proc/cmdline").write_text("root=UUID=abc ro\n", encoding="utf-8")
    (tmp_path / "boot").mkdir()
    (tmp_path / "boot/vmlinuz-test-kernel").write_text("kernel artifact", encoding="utf-8")
    result = boot_state_inventory(tmp_path, "test-kernel")
    assert result["running_kernel_release"] == {
        "status": "observed", "value": "test-kernel", "source": "explicit input"}
    assert result["drm_command_line_overrides"] == {
        "status": "ok", "observed_modeset_overrides": []}
    assert result["nvidia_drm_modeset_effective"] == {"status": "ok", "value": "Y"}
    assert result["current_kernel_artifact_presence_only"] == {
        "vmlinuz-test-kernel": {"status": "observed", "present": True},
        "initrd.img-test-kernel": {"status": "observed", "present": False},
    }
    assert result["bootability"] == "not_verified"


def test_boot_state_preserves_missing_parameter_and_command_line_as_unavailable(
    tmp_path: Path,
) -> None:
    result = boot_state_inventory(tmp_path, "test-kernel")
    assert result["nvidia_drm_modeset_effective"]["status"] == "unknown"
    assert result["drm_command_line_overrides"]["status"] == "could_not_run"
    assert all(item["present"] is False for item in
               result["current_kernel_artifact_presence_only"].values())


def test_boot_state_preserves_boot_artifact_symlink_loop_error(tmp_path: Path) -> None:
    (tmp_path / "boot").mkdir()
    artifact_path = tmp_path / "boot/vmlinuz-test-kernel"
    artifact_path.symlink_to(artifact_path)
    result = boot_state_inventory(tmp_path, "test-kernel")
    artifact = result["current_kernel_artifact_presence_only"]["vmlinuz-test-kernel"]
    assert artifact["status"] == "could_not_run"
    assert "RuntimeError" in artifact["error"]


def test_boot_state_captures_modeset_override_without_raw_cmdline(tmp_path: Path) -> None:
    (tmp_path / "proc").mkdir()
    (tmp_path / "proc/cmdline").write_text(
        "nvidia-drm.modeset=0 secret_token=do-not-capture\n", encoding="utf-8")
    result = boot_state_inventory(tmp_path, "test-kernel")
    assert result["drm_command_line_overrides"] == {
        "status": "ok", "observed_modeset_overrides": ["0"]}
    assert "secret_token" not in json.dumps(result)


def test_boot_state_redacts_unexpected_modeset_value(tmp_path: Path) -> None:
    (tmp_path / "proc").mkdir()
    (tmp_path / "proc/cmdline").write_text("nvidia-drm.modeset=secret123\n", encoding="utf-8")
    result = boot_state_inventory(tmp_path, "test-kernel")
    assert result["drm_command_line_overrides"]["observed_modeset_overrides"] == ["unknown"]
    assert "secret123" not in json.dumps(result)


@pytest.mark.parametrize("release", ["../escape", "bad/kernel", ".."])
def test_boot_state_rejects_release_path_traversal(tmp_path: Path, release: str) -> None:
    result = boot_state_inventory(tmp_path, release)
    assert result["status"] == "could_not_run"
    assert result["reason"] == "invalid kernel release token"


def test_boot_state_rejects_artifact_symlink_escape(tmp_path: Path) -> None:
    (tmp_path / "boot").mkdir()
    outside = tmp_path.parent / "external-initrd"
    outside.write_text("external", encoding="utf-8")
    (tmp_path / "boot/initrd.img-test-kernel").symlink_to(outside)
    result = boot_state_inventory(tmp_path, "test-kernel")
    artifact = result["current_kernel_artifact_presence_only"]["initrd.img-test-kernel"]
    assert artifact["status"] == "could_not_run"


def test_boot_state_reads_release_from_supplied_filesystem_root(tmp_path: Path) -> None:
    path = tmp_path / "proc/sys/kernel"
    path.mkdir(parents=True)
    (path / "osrelease").write_text("fixture-kernel\n", encoding="utf-8")
    result = boot_state_inventory(tmp_path)
    assert result["running_kernel_release"] == {
        "status": "observed", "value": "fixture-kernel", "source": "proc/sys/kernel/osrelease"}


def test_boot_state_rejects_osrelease_symlink_outside_root(tmp_path: Path) -> None:
    kernel_path = tmp_path / "proc/sys/kernel"
    kernel_path.mkdir(parents=True)
    outside = tmp_path.parent / "external-osrelease"
    outside.write_text("external-kernel\n", encoding="utf-8")
    (kernel_path / "osrelease").symlink_to(outside)
    result = boot_state_inventory(tmp_path)
    assert result["status"] == "could_not_run"
    assert result["running_kernel_release"]["status"] == "could_not_run"


def test_boot_state_returns_unknown_when_release_is_unavailable(tmp_path: Path) -> None:
    result = boot_state_inventory(tmp_path)
    assert result["status"] == "could_not_run"
    assert result["running_kernel_release"]["status"] == "could_not_run"


def test_boot_state_rejects_cmdline_symlink_outside_root(tmp_path: Path) -> None:
    (tmp_path / "proc").mkdir()
    outside = tmp_path.parent / "external-cmdline"
    outside.write_text("nvidia-drm.modeset=0\n", encoding="utf-8")
    (tmp_path / "proc/cmdline").symlink_to(outside)
    result = boot_state_inventory(tmp_path, "test-kernel")
    assert result["drm_command_line_overrides"]["status"] == "could_not_run"
    assert "observed_modeset_overrides" not in result["drm_command_line_overrides"]


@pytest.mark.parametrize("outcome,expected", [
    (_mount_output(target="/"), 0),
    (_mount_output(target="/", uuid="wrong"), 1),
    ("", 2),
])
def test_backup_destination_cli_exit_codes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    outcome: str, expected: int,
) -> None:
    from tools import host_diagnostics

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        assert argv == ["findmnt", "--json", "--mountpoint", "/", "--output",
                        "TARGET,SOURCE,UUID"]
        code = 2 if not outcome else 0
        return subprocess.CompletedProcess(argv, code, outcome, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    code = host_diagnostics.main([
        "--check-backup-destination", "--backup-mountpoint", "/",
        "--backup-source", "/dev/sdb1", "--backup-uuid", "expected-uuid",
    ])
    assert code == expected
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == {0: "pass", 1: "block", 2: "unknown"}[expected]


def test_backup_destination_cli_keeps_missing_identity_unknown(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from tools import host_diagnostics

    assert host_diagnostics.main(["--check-backup-destination"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "unknown"


@pytest.mark.parametrize("argv", [
    ["--root", "/tmp/fixture", "--check-backup-destination"],
    ["--backup-source", "/dev/sdb1"],
])
def test_cli_rejects_fixture_root_or_unrequested_identity(
    argv: list[str],
) -> None:
    from tools import host_diagnostics

    with pytest.raises(SystemExit) as exc:
        host_diagnostics.main(argv)
    assert exc.value.code == 2
