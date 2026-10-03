from __future__ import annotations

import json
import os
from pathlib import Path
import pytest
import shutil
import subprocess
import sys
from types import SimpleNamespace
from tools import nvme_readonly


def _snapshot(*, mount_ro: bool = False, signals: dict | None = None,
              inventory: dict | None = None) -> dict:
    return {"checks": {"storage": {
        "root_mounts": {"status": "ok", "value": [{"target": "/", "options": "ro" if mount_ro else "rw",
                                                             "read_only": mount_ro}]},
        "nvme_inventory": inventory or {"status": "ok", "stdout": "[{\"DevicePath\":\"/dev/nvme0n1\",\"SerialNumber\":\"fixture-serial\"}]"},
    }, "kernel_signals": signals or {"status": "ok", "stdout": "healthy boot"}}}


def test_nvme_report_distinguishes_media_error_readonly_unknown_and_healthy() -> None:
    healthy = nvme_readonly.classify(_snapshot())
    assert healthy["status"] == "pass" and healthy["could_not_run"] == 0
    assert healthy["writes_performed"] is False
    assert "physical device health remains unproven" in healthy["claim"]
    media = nvme_readonly.classify(_snapshot(signals={"status": "ok", "stdout": "nvme nvme0: I/O error"}))
    assert media["status"] == "fail" and media["fail"] == 1
    readonly = nvme_readonly.classify(_snapshot(mount_ro=True))
    assert readonly["status"] == "fail" and "read-only root mount" in readonly["findings"]
    unavailable = nvme_readonly.classify(_snapshot(inventory={"status": "could_not_run"}))
    assert unavailable["status"] == "could_not_run" and unavailable["could_not_run"] == 1
    malformed = nvme_readonly.classify(_snapshot(inventory={"status": "ok", "stdout": "not-json"}))
    assert malformed["status"] == "could_not_run" and malformed["could_not_run"] == 1
    unidentifiable = nvme_readonly.classify(_snapshot(inventory={
        "status": "ok", "stdout": "[{\"DevicePath\":\"/dev/nvme0n1\"}]"}))
    assert unidentifiable["status"] == "could_not_run"
    empty_inventory = nvme_readonly.classify(_snapshot(inventory={"status": "ok", "stdout": "[]"}))
    assert empty_inventory["status"] == "could_not_run"
    unrelated_io = nvme_readonly.classify(_snapshot(signals={
        "status": "ok", "stdout": "usb 1-1: I/O error"}))
    assert unrelated_io["status"] == "pass"
    unrelated_io_other_line = nvme_readonly.classify(_snapshot(signals={
        "status": "ok", "stdout": "nvme nvme0: controller ready\nusb 1-1: I/O error"}))
    assert unrelated_io_other_line["status"] == "pass"
    empty_mounts = _snapshot()
    empty_mounts["checks"]["storage"]["root_mounts"]["value"] = []
    assert nvme_readonly.classify(empty_mounts)["status"] == "could_not_run"
    missing_root = _snapshot()
    missing_root["checks"]["storage"]["root_mounts"]["value"] = [
        {"target": "/models", "options": "rw", "read_only": False}]
    assert nvme_readonly.classify(missing_root)["status"] == "could_not_run"
    duplicate_root = _snapshot()
    duplicate_root["checks"]["storage"]["root_mounts"]["value"].append(
        {"target": "/", "options": "rw", "read_only": False})
    assert nvme_readonly.classify(duplicate_root)["status"] == "could_not_run"


def test_export_requires_separate_filesystem_and_never_overwrites(tmp_path: Path) -> None:
    source = tmp_path / "identified-copy.img"
    source.write_bytes(b"immutable test copy")
    same_filesystem = nvme_readonly.export_copy(source, tmp_path / "backup")
    assert same_filesystem["status"] == "could_not_run"
    assert source.read_bytes() == b"immutable test copy"

    shm = Path("/dev/shm")
    if not shm.is_dir() or os.stat(source).st_dev == os.stat(shm).st_dev:
        return
    destination = shm / f"nvme-readonly-test-{os.getpid()}"
    destination.mkdir(mode=0o700)
    try:
        root = Path(__file__).resolve().parents[1]
        command = [sys.executable, "-m", "tools.nvme_readonly", "--export-source", str(source),
                   "--destination-dir", str(destination)]
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        assert completed.returncode == 0
        copied = json.loads(completed.stdout)
        assert copied["status"] == "pass" and copied["source_written"] is False
        target = Path(copied["destination"])
        assert target.read_bytes() == source.read_bytes()
        duplicate = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        assert duplicate.returncode == 2 and json.loads(duplicate.stdout)["status"] == "could_not_run"
    finally:
        shutil.rmtree(destination)


def test_nvme_cli_reads_snapshot_and_exports_identified_copy(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    snapshot = tmp_path / "snapshot.json"
    snapshot.write_text(json.dumps(_snapshot()), encoding="utf-8")
    command = [sys.executable, "-m", "tools.nvme_readonly", "--snapshot", str(snapshot)]
    report = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    assert report.returncode == 0
    assert json.loads(report.stdout)["status"] == "pass"

    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    unavailable = subprocess.run([*command[:4], str(bad)], cwd=root,
                                 capture_output=True, text=True, check=False)
    assert unavailable.returncode == 2
    assert json.loads(unavailable.stdout)["could_not_run"] == 1


def test_nvme_main_reports_fail_and_refuses_incomplete_export(tmp_path: Path,
                                                               capsys: pytest.CaptureFixture[str]) -> None:
    snapshot = tmp_path / "bad-media.json"
    snapshot.write_text(json.dumps(_snapshot(signals={"status": "ok", "stdout": "nvme nvme0: I/O error"})),
                        encoding="utf-8")
    assert nvme_readonly.main(["--snapshot", str(snapshot)]) == 1
    assert json.loads(capsys.readouterr().out)["fail"] == 1
    with pytest.raises(SystemExit) as error:
        nvme_readonly.main(["--export-source", str(snapshot)])
    assert error.value.code == 2


def test_copy_removes_partial_destination_when_source_changes(tmp_path: Path,
                                                               monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source-copy"
    source.write_bytes(b"source contents")
    target = tmp_path / "recovery-copy"
    real_fstat = os.fstat
    calls = 0

    def changing_fstat(fd: int):
        nonlocal calls
        calls += 1
        current = real_fstat(fd)
        if calls == 1:
            return current
        return SimpleNamespace(st_dev=current.st_dev, st_ino=current.st_ino,
                               st_size=current.st_size, st_mtime_ns=current.st_mtime_ns + 1,
                               st_ctime_ns=current.st_ctime_ns)

    monkeypatch.setattr(nvme_readonly.os, "fstat", changing_fstat)
    with pytest.raises(OSError, match="source changed during copy"):
        nvme_readonly._copy_file(source, target, source.stat())
    assert source.read_bytes() == b"source contents"
    assert not target.exists()


def test_copy_refuses_destination_without_capacity(tmp_path: Path,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source-copy"
    source.write_bytes(b"data")
    destination = tmp_path / "separate"
    real_stat = Path.stat

    def destination_on_other_device(path: Path, *args, **kwargs):
        result = real_stat(path, *args, **kwargs)
        if path == destination:
            return SimpleNamespace(st_dev=result.st_dev + 1)
        return result

    monkeypatch.setattr(Path, "stat", destination_on_other_device)
    monkeypatch.setattr(nvme_readonly.shutil, "disk_usage",
                        lambda _path: SimpleNamespace(free=0))
    result = nvme_readonly.export_copy(source, destination)
    assert result["status"] == "could_not_run"
    assert "insufficient destination space" in result["error"]
    assert source.read_bytes() == b"data"


def test_copy_detects_path_replaced_with_same_bytes_and_timestamp(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source-copy"
    source.write_bytes(b"same bytes")
    expected = source.stat()
    original = tmp_path / "original-inode"
    real_fstat = os.fstat
    calls = 0

    def replace_path(fd: int):
        nonlocal calls
        calls += 1
        current = real_fstat(fd)
        if calls == 2:
            source.rename(original)
            source.write_bytes(b"same bytes")
            os.utime(source, ns=(expected.st_atime_ns, expected.st_mtime_ns))
        return current

    monkeypatch.setattr(nvme_readonly.os, "fstat", replace_path)
    target = tmp_path / "recovery-copy"
    with pytest.raises(OSError, match="source path changed during copy"):
        nvme_readonly._copy_file(source, target, expected)
    assert source.read_bytes() == original.read_bytes() == b"same bytes"
    assert not target.exists()


@pytest.mark.parametrize("record", [None, "not a record", []])
def test_capture_text_rejects_non_mapping_records(record: object) -> None:
    assert nvme_readonly._capture_text(record) == (None, "capture record malformed")


@pytest.mark.parametrize("record", [
    {"status": "error", "stdout": "ignored"},
    {"status": "ok", "stdout": None},
])
def test_capture_text_rejects_unavailable_status_or_output(record: dict) -> None:
    assert nvme_readonly._capture_text(record) == (None, "query status or output unavailable")


@pytest.mark.parametrize("document", ["", "42", "{\"Devices\":\"not-a-list\"}"])
def test_nvme_inventory_distinguishes_empty_from_malformed(document: str) -> None:
    observed = nvme_readonly._has_inventory_device(document)
    assert observed is (False if document == "" else None)


def test_kernel_signal_query_unavailable_stays_unknown() -> None:
    report = nvme_readonly.classify(_snapshot(signals={"status": "could_not_run"}))
    assert report["status"] == "could_not_run"
    assert report["could_not_run"] >= 1
    assert "kernel signal query query unavailable" in report["unknowns"]


def test_classify_reports_missing_checks_as_could_not_run() -> None:
    report = nvme_readonly.classify({"snapshot": "without checks"})
    assert report == {
        "status": "could_not_run", "fail": 0, "could_not_run": 1,
        "findings": ["snapshot checks missing"],
    }


def test_copy_rejects_source_changed_between_inventory_and_open(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source-copy"
    source.write_bytes(b"identified bytes")
    expected = source.stat()
    target = tmp_path / "recovery-copy"
    real_open = os.open

    def replace_before_open(path, flags, *args, **kwargs):
        if Path(path) == source:
            source.write_bytes(b"replacement bytes")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(nvme_readonly.os, "open", replace_before_open)
    with pytest.raises(OSError, match="source identity changed before copy"):
        nvme_readonly._copy_file(source, target, expected)
    assert source.read_bytes() == b"replacement bytes"
    assert not target.exists()


def test_copy_detects_destination_digest_mismatch_and_removes_copy(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source-copy"
    source.write_bytes(b"original bytes")
    target = tmp_path / "recovery-copy"
    monkeypatch.setattr(nvme_readonly, "_hash_file", lambda _path: "wrong-digest")
    with pytest.raises(OSError, match="destination copy digest mismatch"):
        nvme_readonly._copy_file(source, target, source.stat())
    assert source.read_bytes() == b"original bytes"
    assert not target.exists()


def test_export_refuses_symlink_source_without_touching_target(tmp_path: Path) -> None:
    original = tmp_path / "original"
    original.write_bytes(b"keep original")
    link = tmp_path / "suspect-link"
    link.symlink_to(original)
    result = nvme_readonly.export_copy(link, tmp_path / "elsewhere")
    assert result["status"] == "could_not_run"
    assert "regular file" in result["error"]
    assert original.read_bytes() == b"keep original"
