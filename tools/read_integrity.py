"""Bounded, read-only buffered and O_DIRECT SHA-256 checks for one file region.

The expected digest is an external trust input supplied by the caller. This
instrument cannot establish that the reference itself is trustworthy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import os
import stat
from typing import Any

MAX_REGION_BYTES = 1024 * 1024
DIRECT_ALIGNMENT = 4096


def _valid_digest(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)


def _digest_buffered(fd: int, offset: int, length: int) -> str:
    digest = hashlib.sha256()
    position = offset
    remaining = length
    while remaining:
        chunk = os.pread(fd, min(remaining, 64 * 1024), position)
        if not chunk:
            raise OSError("short buffered read")
        digest.update(chunk)
        position += len(chunk)
        remaining -= len(chunk)
    return digest.hexdigest()


def _digest_direct(fd: int, offset: int, length: int) -> str:
    digest = hashlib.sha256()
    with mmap.mmap(-1, length) as buffer:
        view = memoryview(buffer)
        try:
            position = offset
            remaining = length
            while remaining:
                count = os.preadv(fd, [view[:remaining]], position)
                if count <= 0:
                    raise OSError("short O_DIRECT read")
                digest.update(view[:count])
                position += count
                remaining -= count
        finally:
            view.release()
    return digest.hexdigest()


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _could_not_run(path: str, offset: int, length: int, exc: OSError) -> dict[str, Any]:
    return {"status": "could_not_run", "could_not_run_count": 1,
            "reason": f"{type(exc).__name__}: {exc}", "path": path,
            "offset": offset, "length": length}


def _validate_parameters(offset: int, length: int, expected_sha256: str, repeats: int) -> None:
    if offset < 0 or length <= 0 or length > MAX_REGION_BYTES:
        raise ValueError(f"length must be 1..{MAX_REGION_BYTES} and offset nonnegative")
    if repeats < 1 or repeats > 5:
        raise ValueError("repeats must be between 1 and 5")
    if not _valid_digest(expected_sha256):
        raise ValueError("expected_sha256 must be 64 hexadecimal characters")
    if offset % DIRECT_ALIGNMENT or length % DIRECT_ALIGNMENT:
        raise ValueError(f"offset and length must be multiples of {DIRECT_ALIGNMENT}")


def _read_repeated(fd_buffered: int, fd_direct: int, offset: int, length: int,
                   repeats: int) -> tuple[list[str], list[str]]:
    buffered: list[str] = []
    direct: list[str] = []
    for _ in range(repeats):
        buffered.append(_digest_buffered(fd_buffered, offset, length))
        direct.append(_digest_direct(fd_direct, offset, length))
    return buffered, direct


def inspect(path: str, offset: int, length: int, expected_sha256: str,
            repeats: int = 2) -> dict[str, Any]:
    """Hash a bounded aligned region buffered and O_DIRECT, without writing."""
    _validate_parameters(offset, length, expected_sha256, repeats)

    fd_buffered: int | None = None
    fd_direct: int | None = None
    try:
        path_before = os.stat(path, follow_symlinks=False)
        if not stat.S_ISREG(path_before.st_mode):
            raise OSError("target must be a regular file; symlinks and special files are refused")
        fd_buffered = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        fd_direct = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_DIRECT)
        buffered_before = os.fstat(fd_buffered)
        direct_before = os.fstat(fd_direct)
        if not stat.S_ISREG(buffered_before.st_mode) or not stat.S_ISREG(direct_before.st_mode):
            raise OSError("target must remain a regular file")
        same_file = (_identity(path_before) == _identity(buffered_before)
                     == _identity(direct_before))
        if not same_file:
            raise OSError("file identity changed between buffered and O_DIRECT opens")
        if offset + length > buffered_before.st_size:
            raise ValueError("requested region extends beyond end of file")
        buffered, direct = _read_repeated(fd_buffered, fd_direct, offset, length, repeats)
        path_after = os.stat(path, follow_symlinks=False)
        buffered_after = os.fstat(fd_buffered)
        direct_after = os.fstat(fd_direct)
        stable = (_identity(path_after) == _identity(buffered_before)
                  == _identity(direct_before) == _identity(buffered_after)
                  == _identity(direct_after))
        expected = expected_sha256.lower()
        all_digests = buffered + direct
        matches = all(digest == expected for digest in all_digests)
        consistent = len(set(all_digests)) == 1
        status = "pass" if stable and matches and consistent else "fail"
        return {"status": status, "could_not_run_count": 0,
                "path": path, "offset": offset, "length": length,
                "alignment": DIRECT_ALIGNMENT, "max_region_bytes": MAX_REGION_BYTES,
                "repeats": repeats, "reference_sha256": expected,
                "reference_source": "caller-supplied; provenance unverified",
                "buffered_sha256": buffered,
                "direct_sha256": direct, "reference_match": matches,
                "modes_consistent": consistent, "file_stable": stable,
                "writes_performed": False}
    except OSError as exc:
        return _could_not_run(path, offset, length, exc)
    finally:
        if fd_direct is not None:
            os.close(fd_direct)
        if fd_buffered is not None:
            os.close(fd_buffered)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    parser.add_argument("--offset", type=int, required=True)
    parser.add_argument("--length", type=int, required=True)
    parser.add_argument("--sha256", required=True, help="trusted digest supplied externally")
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    try:
        result = inspect(args.path, args.offset, args.length, args.sha256, args.repeats)
    except (OSError, ValueError) as exc:
        result = {"status": "could_not_run", "could_not_run_count": 1,
                  "reason": f"{type(exc).__name__}: {exc}"}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 2 if result["status"] == "could_not_run" else 1


if __name__ == "__main__":
    raise SystemExit(main())
