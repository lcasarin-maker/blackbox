from __future__ import annotations

import os
from pathlib import Path
import shutil

from tools import nvme_readonly


def _snapshot(*, mount_ro: bool = False, signals: dict | None = None,
              inventory: dict | None = None) -> dict:
    return {"checks": {"storage": {
        "root_mounts": {"status": "ok", "value": [{"target": "/", "read_only": mount_ro}]},
        "nvme_inventory": inventory or {"status": "ok", "stdout": "[{\"DevicePath\":\"/dev/nvme0n1\"}]"},
    }, "kernel_signals": signals or {"status": "ok", "stdout": "healthy boot"}}}


def test_nvme_report_distinguishes_media_error_readonly_unknown_and_healthy() -> None:
    healthy = nvme_readonly.classify(_snapshot())
    assert healthy["status"] == "pass" and healthy["could_not_run"] == 0
    assert healthy["writes_performed"] is False
    media = nvme_readonly.classify(_snapshot(signals={"status": "ok", "stdout": "nvme nvme0: I/O error"}))
    assert media["status"] == "fail" and media["fail"] == 1
    readonly = nvme_readonly.classify(_snapshot(mount_ro=True))
    assert readonly["status"] == "fail" and "read-only mount: /" in readonly["findings"]
    unavailable = nvme_readonly.classify(_snapshot(inventory={"status": "could_not_run"}))
    assert unavailable["status"] == "could_not_run" and unavailable["could_not_run"] == 1
    malformed = nvme_readonly.classify(_snapshot(inventory={"status": "ok", "stdout": "not-json"}))
    assert malformed["status"] == "could_not_run" and malformed["could_not_run"] == 1


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
        copied = nvme_readonly.export_copy(source, destination)
        assert copied["status"] == "pass" and copied["source_written"] is False
        target = Path(copied["destination"])
        assert target.read_bytes() == source.read_bytes()
        duplicate = nvme_readonly.export_copy(source, destination)
        assert duplicate["status"] == "could_not_run"
    finally:
        shutil.rmtree(destination)
