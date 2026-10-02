from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import runpy
from typing import Any

import pytest

from tools import read_integrity

REGION = b"a" * read_integrity.DIRECT_ALIGNMENT


def make_file(tmp_path: Path, content: bytes = REGION) -> Path:
    path = tmp_path / "sample.bin"
    path.write_bytes(content)
    return path


def test_healthy_buffered_and_direct_match_external_reference(tmp_path: Path) -> None:
    path = make_file(tmp_path)

    result = read_integrity.inspect(str(path), 0, len(REGION), hashlib.sha256(REGION).hexdigest())

    assert result["status"] == "pass"
    assert result["could_not_run_count"] == 0
    assert result["reference_source"] == "caller-supplied; provenance unverified"
    assert result["writes_performed"] is False
    assert result["buffered_sha256"] == [hashlib.sha256(REGION).hexdigest()] * 2
    assert result["direct_sha256"] == [hashlib.sha256(REGION).hexdigest()] * 2


def test_corrupted_reference_is_detected(tmp_path: Path) -> None:
    path = make_file(tmp_path)

    result = read_integrity.inspect(str(path), 0, len(REGION), "0" * 64)

    assert result["status"] == "fail"
    assert result["reference_match"] is False


def test_mode_disagreement_is_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = make_file(tmp_path)
    monkeypatch.setattr(read_integrity, "_digest_direct", lambda *_args: "0" * 64)

    result = read_integrity.inspect(str(path), 0, len(REGION), hashlib.sha256(REGION).hexdigest())

    assert result["status"] == "fail"
    assert result["modes_consistent"] is False


@pytest.mark.parametrize(("offset", "length", "digest", "repeats"), [
    (-1, 4096, "0" * 64, 1),
    (0, 0, "0" * 64, 1),
    (0, read_integrity.MAX_REGION_BYTES + 4096, "0" * 64, 1),
    (1, 4096, "0" * 64, 1),
    (0, 4097, "0" * 64, 1),
    (0, 4096, "bad", 1),
    (0, 4096, "0" * 64, 6),
])
def test_invalid_bounds_and_reference_rejected(tmp_path: Path, offset: int, length: int,
                                               digest: str, repeats: int) -> None:
    path = make_file(tmp_path)
    with pytest.raises(ValueError):
        read_integrity.inspect(str(path), offset, length, digest, repeats)


def test_region_beyond_file_rejected(tmp_path: Path) -> None:
    path = make_file(tmp_path)
    with pytest.raises(ValueError, match="beyond end"):
        read_integrity.inspect(str(path), 4096, 4096, "0" * 64)


def test_symlink_target_refused(tmp_path: Path) -> None:
    target = make_file(tmp_path)
    alias = tmp_path / "alias.bin"
    alias.symlink_to(target)

    result = read_integrity.inspect(str(alias), 0, 4096, hashlib.sha256(REGION).hexdigest())
    assert result["status"] == "could_not_run"
    assert result["could_not_run_count"] == 1


def test_direct_io_permission_failure_is_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = make_file(tmp_path)
    original_open = os.open

    def denied(file: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if flags & getattr(os, "O_DIRECT", 0):
            raise PermissionError("direct I/O denied")
        return original_open(file, flags, *args, **kwargs)

    monkeypatch.setattr(read_integrity.os, "open", denied)
    result = read_integrity.inspect(str(path), 0, 4096, hashlib.sha256(REGION).hexdigest())
    assert result["status"] == "could_not_run"
    assert result["could_not_run_count"] == 1
    assert "direct I/O denied" in result["reason"]


def test_buffered_and_direct_use_distinct_open_flags(tmp_path: Path,
                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    path = make_file(tmp_path)
    original_open = os.open
    flags_seen: list[int] = []

    def tracked(file: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        flags_seen.append(flags)
        return original_open(file, flags, *args, **kwargs)

    monkeypatch.setattr(read_integrity.os, "open", tracked)
    result = read_integrity.inspect(str(path), 0, 4096, hashlib.sha256(REGION).hexdigest(), 1)

    assert result["status"] == "pass"
    assert len(flags_seen) == 2
    assert not flags_seen[0] & os.O_DIRECT
    assert flags_seen[1] & os.O_DIRECT


def test_direct_open_failure_closes_buffered_descriptor(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = make_file(tmp_path)
    original_open = os.open
    opened: list[int] = []

    def fail_direct(file: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if flags & os.O_DIRECT:
            raise PermissionError("direct I/O denied")
        descriptor = original_open(file, flags, *args, **kwargs)
        opened.append(descriptor)
        return descriptor

    monkeypatch.setattr(read_integrity.os, "open", fail_direct)
    result = read_integrity.inspect(str(path), 0, 4096, hashlib.sha256(REGION).hexdigest(), 1)

    assert result["status"] == "could_not_run"
    assert result["could_not_run_count"] == 1
    assert len(opened) == 1
    with pytest.raises(OSError):
        os.fstat(opened[0])


def test_path_replacement_between_opens_is_rejected(tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    path = make_file(tmp_path)
    original_open = os.open
    call_count = 0

    def replace_before_direct(file: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            replacement = tmp_path / "replacement.bin"
            replacement.write_bytes(REGION)
            replacement.replace(path)
        return original_open(file, flags, *args, **kwargs)

    monkeypatch.setattr(read_integrity.os, "open", replace_before_direct)
    result = read_integrity.inspect(str(path), 0, 4096, hashlib.sha256(REGION).hexdigest(), 1)

    assert result["status"] == "could_not_run"
    assert result["could_not_run_count"] == 1
    assert "identity changed" in result["reason"]


def test_direct_read_error_returns_could_not_run(tmp_path: Path,
                                                monkeypatch: pytest.MonkeyPatch) -> None:
    path = make_file(tmp_path)

    def denied(*_args: Any) -> str:
        raise OSError("direct I/O unsupported")

    monkeypatch.setattr(read_integrity, "_digest_direct", denied)
    result = read_integrity.inspect(str(path), 0, 4096, hashlib.sha256(REGION).hexdigest())
    assert result["status"] == "could_not_run"
    assert result["could_not_run_count"] == 1
    assert "direct I/O unsupported" in result["reason"]


@pytest.mark.parametrize(("reader", "message"), [
    ("buffered", "short buffered read"), ("direct", "short O_DIRECT read"),
])
def test_short_reads_become_could_not_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                         reader: str, message: str) -> None:
    path = make_file(tmp_path)
    if reader == "buffered":
        monkeypatch.setattr(read_integrity.os, "pread", lambda *_args: b"")
    else:
        monkeypatch.setattr(read_integrity.os, "preadv", lambda *_args: 0)
    result = read_integrity.inspect(str(path), 0, 4096, hashlib.sha256(REGION).hexdigest())
    assert result["status"] == "could_not_run"
    assert result["could_not_run_count"] == 1
    assert message in result["reason"]


def test_non_regular_target_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = make_file(tmp_path)
    monkeypatch.setattr(read_integrity.stat, "S_ISREG", lambda _mode: False)
    result = read_integrity.inspect(str(path), 0, 4096, hashlib.sha256(REGION).hexdigest())
    assert result["status"] == "could_not_run"
    assert result["could_not_run_count"] == 1


def test_descriptor_type_change_is_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = make_file(tmp_path)
    calls = 0

    def regular(_mode: int) -> bool:
        nonlocal calls
        calls += 1
        return calls == 1

    monkeypatch.setattr(read_integrity.stat, "S_ISREG", regular)
    result = read_integrity.inspect(str(path), 0, 4096, hashlib.sha256(REGION).hexdigest())
    assert result["status"] == "could_not_run"
    assert result["could_not_run_count"] == 1


def test_main_emits_parseable_negative_control(monkeypatch: pytest.MonkeyPatch,
                                              capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("sys.argv", ["read_integrity.py", "/missing", "--offset", "0",
                                     "--length", "4096", "--sha256", "0" * 64])
    assert read_integrity.main() == 2
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "could_not_run"
    assert result["could_not_run_count"] == 1


def test_module_entrypoint_invokes_main(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.argv", ["read_integrity.py", "/missing", "--offset", "0",
                                     "--length", "4096", "--sha256", "0" * 64])
    with pytest.warns(RuntimeWarning, match="found in sys.modules"):
        with pytest.raises(SystemExit) as raised:
            runpy.run_module("tools.read_integrity", run_name="__main__")
    assert raised.value.code == 2


@pytest.mark.parametrize(("status", "exit_code"), [("pass", 0), ("fail", 1)])
def test_main_maps_inspection_verdict(monkeypatch: pytest.MonkeyPatch,
                                      capsys: pytest.CaptureFixture[str],
                                      status: str, exit_code: int) -> None:
    monkeypatch.setattr("sys.argv", ["read_integrity.py", "sample", "--offset", "0",
                                     "--length", "4096", "--sha256", "0" * 64])
    monkeypatch.setattr(read_integrity, "inspect", lambda *_args: {"status": status})
    assert read_integrity.main() == exit_code
    assert json.loads(capsys.readouterr().out) == {"status": status}


def test_main_converts_invalid_input_to_could_not_run(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("sys.argv", ["read_integrity.py", "sample", "--offset", "1",
                                     "--length", "4096", "--sha256", "0" * 64])
    assert read_integrity.main() == 2
    assert json.loads(capsys.readouterr().out)["reason"].startswith("ValueError:")
