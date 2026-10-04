"""Classify read-only NVMe snapshots and export identified regular-file copies."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import argparse
from typing import Any

from tools.capture_io import read_regular_bytes, strict_json_loads

MAX_SNAPSHOT_BYTES = 16 * 1024 * 1024

IO_RE = re.compile(r"(?:I/O error|medium error|critical medium error|uncorrectable|Buffer I/O error)", re.I)
NVME_DEVICE_RE = re.compile(r"\bnvme\d+(?:n\d+)?\b", re.I)


def _capture_text(record: Any) -> tuple[str | None, str | None]:
    if not isinstance(record, dict):
        return None, "capture record malformed"
    if record.get("status") == "could_not_run":
        return None, "query unavailable"
    if record.get("status") not in ("ok", "observed") or not isinstance(record.get("stdout"), str):
        return None, "query status or output unavailable"
    return record["stdout"], None


def _capture(checks: dict[str, Any], section: str, key: str) -> Any:
    group = checks.get(section)
    return group.get(key) if isinstance(group, dict) else None


def _has_inventory_device(text: str | None) -> bool | None:
    if not text:
        return False
    try:
        document = strict_json_loads(text)
    except json.JSONDecodeError:
        return None
    devices = document.get("Devices") if isinstance(document, dict) else document
    if not isinstance(devices, list):
        return None
    if not devices:
        return False
    if any(not isinstance(device, dict) or not isinstance(device.get("DevicePath"), str)
           or not isinstance(device.get("SerialNumber"), str)
           or not device["DevicePath"].startswith("/dev/nvme")
           or not device["SerialNumber"].strip() for device in devices):
        return None
    return True


def _nvme_io_error(text: str) -> bool:
    return any(IO_RE.search(line) and NVME_DEVICE_RE.search(line)
               for line in text.splitlines())


def _classify_records(mounts: Any, devices: Any, signals: Any) -> dict[str, Any]:
    unknown: list[str] = []
    findings: list[str] = []
    mount_value = mounts.get("value") if isinstance(mounts, dict) else None
    root_mounts = ([row for row in mount_value if isinstance(row, dict) and row.get("target") == "/"]
                   if isinstance(mount_value, list) else [])
    if (not isinstance(mounts, dict) or mounts.get("status") != "ok"
            or not isinstance(mount_value, list) or not mount_value
            or any(not isinstance(row, dict) or not isinstance(row.get("target"), str)
                   or not isinstance(row.get("options"), str)
                   or type(row.get("read_only")) is not bool for row in mount_value)
            or len(root_mounts) != 1):
        unknown.append("root mount state unavailable")
    else:
        findings.extend("read-only root mount"
                        for mount in root_mounts if mount.get("read_only") is True)
    device_text, device_error = _capture_text(devices)
    if device_error:
        unknown.append(f"NVMe inventory {device_error}")
    signal_text, signal_error = _capture_text(signals)
    if signal_error:
        unknown.append(f"kernel signal query {signal_error}")
    elif _nvme_io_error(signal_text or ""):
        findings.append("kernel log contains a device-specific NVMe I/O error")
    if findings:
        status = "fail"
    elif unknown or _has_inventory_device(device_text) is not True:
        status = "could_not_run"
        if not device_error:
            unknown.append("NVMe inventory is empty or malformed")
    else:
        status = "pass"
    return {"status": status, "fail": int(status == "fail"),
            "could_not_run": len(unknown), "findings": findings,
            "unknowns": unknown, "writes_performed": False,
            "claim": "no recorded failure signal; physical device health remains unproven"
            if status == "pass" else None}


def classify(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Classify only corroborated signals; unavailable inputs stay unknown."""
    checks = snapshot.get("checks") if isinstance(snapshot, dict) else None
    if not isinstance(checks, dict):
        return {"status": "could_not_run", "fail": 0, "could_not_run": 1,
                "findings": ["snapshot checks missing"]}
    return _classify_records(_capture(checks, "storage", "root_mounts"),
                             _capture(checks, "storage", "nvme_inventory"),
                             checks.get("kernel_signals"))


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _copy_file(source: Path, target: Path, expected: os.stat_result) -> tuple[int, str]:
    digest = hashlib.sha256()
    fd_in = os.open(source, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    created = False
    try:
        opened = os.fstat(fd_in)
        if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns) != (
                expected.st_dev, expected.st_ino, expected.st_size,
                expected.st_mtime_ns, expected.st_ctime_ns):
            raise OSError("source identity changed before copy")
        fd_out = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
        created = True
        try:
            with os.fdopen(fd_in, "rb", closefd=False) as reader, os.fdopen(fd_out, "wb", closefd=False) as writer:
                while block := reader.read(1024 * 1024):
                    digest.update(block)
                    writer.write(block)
                writer.flush()
                os.fsync(fd_out)
            after = os.fstat(fd_in)
            identity_before = (opened.st_dev, opened.st_ino, opened.st_size,
                               opened.st_mtime_ns, opened.st_ctime_ns)
            identity_after = (after.st_dev, after.st_ino, after.st_size,
                              after.st_mtime_ns, after.st_ctime_ns)
            if identity_before != identity_after:
                raise OSError("source changed during copy")
            if _hash_file(target) != digest.hexdigest():
                raise OSError("destination copy digest mismatch")
            path_after = source.stat(follow_symlinks=False)
            if (path_after.st_dev, path_after.st_ino, path_after.st_size,
                    path_after.st_mtime_ns, path_after.st_ctime_ns) != identity_before:
                raise OSError("source path changed during copy")
        finally:
            os.close(fd_out)
        return expected.st_dev, digest.hexdigest()
    except BaseException:
        if created:
            target.unlink(missing_ok=True)
        raise
    finally:
        os.close(fd_in)


def export_copy(source: Path, destination_dir: Path) -> dict[str, Any]:
    """Copy one identified regular file to a separate filesystem without overwrite."""
    try:
        source_stat = source.stat(follow_symlinks=False)
        if not stat.S_ISREG(source_stat.st_mode):
            raise OSError("source must be a regular file; symlinks and devices are refused")
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination_stat = destination_dir.stat()
        if source_stat.st_dev == destination_stat.st_dev:
            raise OSError("destination must be on a different filesystem")
        if shutil.disk_usage(destination_dir).free < source_stat.st_size:
            raise OSError("insufficient destination space")
        target = destination_dir / f"{source.name}.{source_stat.st_ino}.recovery-copy"
        _source_device, digest = _copy_file(source, target, source_stat)
        return {"status": "pass", "fail": 0, "could_not_run": 0,
                "source": str(source), "source_device": source_stat.st_dev,
                "destination": str(target), "destination_device": destination_stat.st_dev,
                "bytes": source_stat.st_size, "sha256": digest, "source_written": False}
    except (OSError, ValueError) as exc:
        return {"status": "could_not_run", "fail": 0, "could_not_run": 1,
                "error": f"{type(exc).__name__}: {exc}", "source_written": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snapshot", type=Path, help="read-only host_diagnostics JSON snapshot")
    mode.add_argument("--export-source", type=Path, help="identified regular file to copy")
    parser.add_argument("--destination-dir", type=Path,
                        help="existing or new directory on a separate filesystem")
    args = parser.parse_args(argv)
    if args.snapshot:
        try:
            raw = read_regular_bytes(args.snapshot, MAX_SNAPSHOT_BYTES)
            if len(raw) > MAX_SNAPSHOT_BYTES:
                raise ValueError("snapshot exceeds bounded input size")
            report = classify(strict_json_loads(raw.decode("utf-8")))
        except (OSError, ValueError, json.JSONDecodeError, RecursionError) as exc:
            report = {"status": "could_not_run", "fail": 0, "could_not_run": 1,
                      "error": f"{type(exc).__name__}: {exc}", "writes_performed": False}
    elif args.destination_dir and args.export_source:
        report = export_copy(args.export_source, args.destination_dir)
    else:
        parser.error("--destination-dir is required with --export-source")
    sys.stdout.write(json.dumps(report, sort_keys=True) + "\n")
    return 0 if report["status"] == "pass" else 1 if report["status"] == "fail" else 2


if __name__ == "__main__":
    raise SystemExit(main())
