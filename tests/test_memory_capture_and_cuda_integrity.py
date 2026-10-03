import json
import ctypes as C
import os
import runpy
from pathlib import Path

import pytest

from tools import cuda_integrity, memory_profile


# This helper returns a classified record; it is not Path.read_text.
read_profile_value = memory_profile.read_text


def profile_value(value: object, *keys: str) -> object:
    for key in keys:
        assert isinstance(value, dict), f"profile section {key!r} must be an object"
        value = value[key]
    return value



def test_profile_value_rejects_non_object_section() -> None:
    with pytest.raises(AssertionError, match="must be an object"):
        profile_value({"uvm": []}, "uvm", "loaded")

def test_profile_marks_missing_parameter_unsupported(tmp_path: Path) -> None:
    module = tmp_path / "sys/module/nvidia_uvm"
    (module / "parameters").mkdir(parents=True)
    (module / "srcversion").write_text("loaded-id\n", encoding="utf-8")
    result = memory_profile.capture(tmp_path)
    assert profile_value(result, "uvm", "loaded") is True
    assert profile_value(result, "uvm", "loaded_version", "status") == "absent"
    assert profile_value(result, "uvm", "loaded_srcversion", "value") == "loaded-id"
    assert profile_value(result, "uvm", "packing_parameter", "status") == "unsupported"


def test_profile_distinguishes_unloaded_module_from_unsupported_parameter(tmp_path: Path,
                                                                           monkeypatch) -> None:
    monkeypatch.setattr(memory_profile, "command", lambda argv: {
        "status": "ok", "command": argv, "value": "disk-only"})
    result = memory_profile.capture(tmp_path)
    assert profile_value(result, "uvm", "loaded") is False
    assert profile_value(result, "uvm", "loaded_version", "status") == "module_not_loaded"
    assert profile_value(result, "uvm", "packing_parameter", "status") == "module_not_loaded"


def test_profile_keeps_64k_page_size_from_fixture(tmp_path: Path) -> None:
    result = memory_profile.capture(tmp_path, page_size_bytes=65536)
    assert profile_value(result, "kernel", "page_size_bytes") == 65536


def test_live_profile_records_running_host_page_size() -> None:
    result = memory_profile.capture()
    assert profile_value(result, "kernel", "page_size_bytes") == os.sysconf("SC_PAGE_SIZE")
    assert profile_value(result, "uvm", "loaded") is True
    assert profile_value(result, "uvm", "loaded_version", "status") == "ok"


def test_profile_distinguishes_loaded_and_disk_identity(tmp_path: Path, monkeypatch) -> None:
    module = tmp_path / "sys/module/nvidia_uvm"
    (module / "parameters").mkdir(parents=True)
    (module / "version").write_text("580.178.04", encoding="utf-8")
    (module / "srcversion").write_text("loaded-src", encoding="utf-8")
    (module / "parameters/uvm_pack_sysmem_leaf_tables").write_text("Y\n", encoding="utf-8")
    monkeypatch.setattr(memory_profile, "command", lambda argv: {
        "status": "ok", "command": argv, "value": "615.71.09"})
    result = memory_profile.capture(tmp_path)
    assert profile_value(result, "uvm", "loaded_version", "value") == "580.178.04"
    assert profile_value(result, "uvm", "disk_version", "value") == "615.71.09"
    assert profile_value(result, "uvm", "loaded_srcversion", "value") == "loaded-src"
    assert profile_value(result, "uvm", "disk_srcversion", "value") == "615.71.09"
    assert profile_value(result, "uvm", "packing_parameter", "value") == "Y"


def test_profile_preserves_read_failure_status(tmp_path: Path, monkeypatch) -> None:
    module = tmp_path / "sys/module/nvidia_uvm"
    (module / "parameters").mkdir(parents=True)
    original = memory_profile.read_text

    def denied(path: Path):
        if path.name == "meminfo":
            return {"status": "read_denied", "value": None, "error": "fixture denied"}
        return original(path)

    monkeypatch.setattr(memory_profile, "read_text", denied)
    result = memory_profile.capture(tmp_path)
    assert profile_value(result, "host_reserve_context", "meminfo", "status") == "read_denied"


def test_read_text_separates_absent_and_invalid_utf8(tmp_path: Path) -> None:
    assert read_profile_value(tmp_path / "absent")["status"] == "absent"
    invalid = tmp_path / "invalid"
    invalid.write_bytes(b"\xff")
    assert read_profile_value(invalid)["status"] == "collection_failed"


def test_read_text_reports_permission_denied(tmp_path: Path, monkeypatch) -> None:
    def denied(*args, **kwargs):
        raise PermissionError("fixture denied")

    monkeypatch.setattr(Path, "read_text", denied)
    assert read_profile_value(tmp_path / "restricted")["status"] == "read_denied"


def test_command_reports_unsupported_executable(monkeypatch) -> None:
    def missing(*args, **kwargs):
        raise FileNotFoundError("modinfo fixture missing")

    monkeypatch.setattr(memory_profile.subprocess, "run", missing)
    assert memory_profile.command(["modinfo"])["status"] == "unsupported"


def test_command_reports_nonzero_exit(monkeypatch) -> None:
    class Result:
        returncode = 3
        stdout = ""
        stderr = "modinfo denied"

    monkeypatch.setattr(memory_profile.subprocess, "run", lambda *args, **kwargs: Result())
    result = memory_profile.command(["modinfo"])
    assert result["status"] == "collection_failed"
    assert result["returncode"] == 3


def test_command_reports_timeout(monkeypatch) -> None:
    def timeout(*args, **kwargs):
        raise memory_profile.subprocess.TimeoutExpired(["modinfo"], 5)

    monkeypatch.setattr(memory_profile.subprocess, "run", timeout)
    assert memory_profile.command(["modinfo"])["status"] == "collection_failed"


def test_command_reports_permission_denied(monkeypatch) -> None:
    def denied(*args, **kwargs):
        raise PermissionError("fixture denied")

    monkeypatch.setattr(memory_profile.subprocess, "run", denied)
    assert memory_profile.command(["modinfo"])["status"] == "read_denied"


def test_profile_main_writes_requested_output(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "capture.json"
    monkeypatch.setattr("sys.argv", ["memory_profile", "--output", str(output)])
    monkeypatch.setattr(memory_profile, "capture", lambda _root: {"schema": 1})
    assert memory_profile.main() == 0
    assert json.loads(output.read_text(encoding="utf-8")) == {"schema": 1}


def test_profile_main_writes_stdout_when_no_output_is_set(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.argv", ["memory_profile"])
    monkeypatch.setattr(memory_profile, "capture", lambda _root: {"schema": 1})
    assert memory_profile.main() == 0
    assert json.loads(capsys.readouterr().out) == {"schema": 1}


def test_profile_script_entrypoint(monkeypatch, capsys) -> None:
    script = Path(memory_profile.__file__)
    monkeypatch.setattr("sys.argv", [str(script)])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(script), run_name="__main__")
    assert exc.value.code == 0
    assert json.loads(capsys.readouterr().out)["schema"] == 1


def test_profile_cli_writes_valid_json(tmp_path: Path) -> None:
    out = tmp_path / "profile.json"
    record = memory_profile.capture(tmp_path)
    out.write_text(json.dumps(record), encoding="utf-8")
    assert json.loads(out.read_text(encoding="utf-8"))["schema"] == 1


def test_cuda_readback_accepts_known_bytes() -> None:
    assert cuda_integrity.verify_bytes(b"\x07" * 32, b"\x07" * 32) is None


def test_cuda_readback_detects_mutated_byte() -> None:
    with pytest.raises(ValueError, match="readback mismatch at byte 2"):
        cuda_integrity.verify_bytes(b"abcd", b"abXd")


def test_cuda_readback_detects_truncation() -> None:
    with pytest.raises(ValueError, match="readback mismatch at byte 3"):
        cuda_integrity.verify_bytes(b"abc", b"abcd")


@pytest.mark.parametrize("workers", [0, 5, -1])
def test_cuda_worker_count_has_hard_bound(workers: int) -> None:
    with pytest.raises(ValueError, match="workers must be"):
        cuda_integrity.run(workers=workers)


@pytest.mark.parametrize("rounds", [0, 5, -2])
def test_cuda_round_count_has_hard_bound(rounds: int) -> None:
    with pytest.raises(ValueError, match="rounds must be"):
        cuda_integrity.run(rounds=rounds)


def test_cuda_aggregate_cap_is_at_most_16_mib() -> None:
    assert cuda_integrity.MAX_WORKERS * cuda_integrity.MAX_WORKER_BYTES == 16 * 1024 * 1024


class Callable:
    def __init__(self, function):
        self.function = function

    def __call__(self, *args: object) -> int:
        return self.function(*args)


class FakeCuda:
    def __init__(self, fail_memset_after: int | None = None,
                 fail_free_on_call: int | None = None):
        self.buffers = {}
        self.fail_memset_after = fail_memset_after
        self.memset_calls = 0
        self.fail_free_on_call = fail_free_on_call
        self.free_attempts = []
        self.cudaMalloc = Callable(self.allocate)
        self.cudaFree = Callable(self.release)
        self.cudaMemset = Callable(self.fill)
        self.cudaMemcpy = Callable(self.copy)
        self.cudaDeviceSynchronize = Callable(lambda: 0)

    def allocate(self, output, size):
        buffer = C.create_string_buffer(size)
        address = C.addressof(buffer)
        self.buffers[address] = buffer
        C.cast(output, C.POINTER(C.c_void_p))[0] = address
        return 0

    def release(self, pointer):
        address = pointer.value
        self.free_attempts.append(address)
        if len(self.free_attempts) == self.fail_free_on_call:
            return 8
        del self.buffers[address]
        return 0

    def fill(self, pointer, value, size):
        self.memset_calls += 1
        if self.memset_calls == self.fail_memset_after:
            return 9
        C.memset(pointer, value, size)
        return 0

    def copy(self, destination, pointer, size, direction):
        assert direction == 2
        C.memmove(destination, pointer, size)
        return 0


def test_cuda_worker_reuses_holes_and_reads_surviving_slots() -> None:
    fake = FakeCuda()
    allocated = cuda_integrity.run_worker(fake, index=0, rounds=1, worker_bytes=4 * 1024 * 1024)
    assert allocated == 6
    assert len(fake.free_attempts) == 6
    assert fake.buffers == {}


def test_cuda_worker_preserves_primary_error_and_attempts_cleanup() -> None:
    fake = FakeCuda(fail_memset_after=3, fail_free_on_call=1)
    with pytest.raises(RuntimeError, match="cudaMemset initial allocation returned CUDA error 9") as raised:
        cuda_integrity.run_worker(fake, index=0, rounds=1, worker_bytes=4 * 1024 * 1024)
    assert len(fake.free_attempts) == 3
    assert len(set(fake.free_attempts)) == 3
    assert any("cleanup failures" in note for note in raised.value.__notes__)


def test_failed_hole_free_is_not_retried_and_other_slots_are_cleaned() -> None:
    fake = FakeCuda(fail_free_on_call=1)
    with pytest.raises(RuntimeError, match="cudaFree hole returned CUDA error 8") as raised:
        cuda_integrity.run_worker(fake, index=0, rounds=1, worker_bytes=4 * 1024 * 1024)
    assert len(fake.free_attempts) == 4
    assert len(set(fake.free_attempts)) == 4
    assert len(fake.buffers) == 1
    assert any("uncertain device state" in note for note in raised.value.__notes__)


def test_cli_includes_cleanup_notes_in_failure_json(monkeypatch, capsys) -> None:
    error = RuntimeError("primary CUDA failure")
    error.add_note("cleanup failed for allocation 123")

    def fail_run(*args, **kwargs):
        raise error

    monkeypatch.setattr("sys.argv", ["cuda_integrity.py", "--_bounded-worker"])
    monkeypatch.setattr(cuda_integrity, "run", fail_run)
    assert cuda_integrity.main() == 1
    result = json.loads(capsys.readouterr().out)
    assert result["error"] == "RuntimeError: primary CUDA failure"
    assert result["notes"] == ["cleanup failed for allocation 123"]
