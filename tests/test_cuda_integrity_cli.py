"""Bounded CUDA driver loading and CLI wrapper behavior using fake bindings."""
from __future__ import annotations

import ctypes as C
import json
from pathlib import Path
import runpy
import subprocess
from types import SimpleNamespace
from typing import Any, cast

import pytest

from tools import cuda_integrity


class Function:
    def __init__(self, callback: Any) -> None:
        self.callback = callback
        self.argtypes: Any = None
        self.restype: Any = None

    def __call__(self, *args: Any) -> Any:
        return self.callback(*args)


class FakeLibrary:
    def __init__(self, device_count: int = 1, count_error: int = 0) -> None:
        self.device_count = device_count
        self.count_error = count_error
        self.buffers: dict[int, Any] = {}
        self.cudaGetDeviceCount = Function(self.get_device_count)
        self.cudaMalloc = Function(self.allocate)
        self.cudaFree = Function(self.release)
        self.cudaMemset = Function(self.fill)
        self.cudaMemcpy = Function(self.copy)
        self.cudaDeviceSynchronize = Function(lambda: 0)

    def get_device_count(self, result: Any) -> int:
        C.cast(result, C.POINTER(C.c_int))[0] = self.device_count
        return self.count_error

    def allocate(self, result: Any, size: int) -> int:
        buffer = C.create_string_buffer(size)
        pointer = C.cast(buffer, C.c_void_p)
        assert pointer.value is not None
        self.buffers[pointer.value] = buffer
        C.cast(result, C.POINTER(C.c_void_p))[0] = pointer
        return 0

    def release(self, pointer: Any) -> int:
        self.buffers.pop(pointer.value, None)
        return 0

    def fill(self, pointer: Any, value: int, size: int) -> int:
        C.memset(pointer, value, size)
        return 0

    def copy(self, destination: Any, pointer: Any, size: int, direction: int) -> int:
        assert direction == 2
        C.memmove(destination, pointer, size)
        return 0


def test_configure_sets_complete_cuda_runtime_abi() -> None:
    library = FakeLibrary()

    cuda_integrity.configure(cast(C.CDLL, library))

    assert library.cudaMalloc.argtypes == [C.POINTER(C.c_void_p), C.c_size_t]
    assert library.cudaMalloc.restype is C.c_int
    assert library.cudaFree.argtypes == [C.c_void_p]
    assert library.cudaFree.restype is C.c_int
    assert library.cudaMemset.argtypes == [C.c_void_p, C.c_int, C.c_size_t]
    assert library.cudaMemset.restype is C.c_int
    assert library.cudaMemcpy.argtypes == [C.c_void_p, C.c_void_p, C.c_size_t, C.c_int]
    assert library.cudaMemcpy.restype is C.c_int
    assert library.cudaDeviceSynchronize.argtypes == []
    assert library.cudaDeviceSynchronize.restype is C.c_int


def test_allocate_slot_rejects_successful_null_pointer() -> None:
    library = SimpleNamespace(cudaMalloc=Function(lambda *_args: 0),
                              cudaMemset=Function(lambda *_args: 0))
    with pytest.raises(RuntimeError, match="cudaMalloc null probe returned a null pointer"):
        cuda_integrity.allocate_slot(library, {}, 1, 1, "null probe")


def test_run_missing_runtime_library_is_could_not_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cuda_integrity.ctypes.util, "find_library", lambda _name: None)
    assert cuda_integrity.run(workers=1, rounds=1) == {
        "status": "could_not_run", "reason": "libcudart unavailable"}


def test_run_cdll_load_failure_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cuda_integrity.ctypes.util, "find_library", lambda _name: "libcudart.so")

    def unavailable(_name: str) -> Any:
        raise OSError("loader denied")

    monkeypatch.setattr(cuda_integrity.C, "CDLL", unavailable)
    with pytest.raises(OSError, match="loader denied"):
        cuda_integrity.run(workers=1, rounds=1)


@pytest.mark.parametrize(("device_count", "count_error", "expected"), [
    (0, 0, {"status": "could_not_run", "reason": "no usable CUDA device",
            "cuda_error": 0, "device_count": 0}),
    (2, 35, {"status": "could_not_run", "reason": "no usable CUDA device",
             "cuda_error": 35, "device_count": 2}),
])
def test_run_device_count_controls_no_device_outcome(
        monkeypatch: pytest.MonkeyPatch, device_count: int, count_error: int,
        expected: dict[str, object]) -> None:
    library = FakeLibrary(device_count=device_count, count_error=count_error)
    monkeypatch.setattr(cuda_integrity.ctypes.util, "find_library", lambda _name: "fake-cudart")
    monkeypatch.setattr(cuda_integrity.C, "CDLL", lambda _name: library)

    assert cuda_integrity.run(workers=1, rounds=1) == expected


def test_run_configures_library_and_runs_bounded_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    library = FakeLibrary()
    monkeypatch.setattr(cuda_integrity.ctypes.util, "find_library", lambda _name: "fake-cudart")
    monkeypatch.setattr(cuda_integrity.C, "CDLL", lambda _name: library)

    result = cuda_integrity.run(workers=1, rounds=1)

    assert result["status"] == "pass"
    assert result["library"] == "fake-cudart"
    assert result["allocations"] == 6
    assert result["max_aggregate_allocation_bytes"] == cuda_integrity.MAX_WORKER_BYTES
    assert result["full_buffer_readback"] is True
    assert library.cudaMalloc.restype is C.c_int
    assert library.buffers == {}


def test_run_rejects_changed_worker_byte_bound() -> None:
    with pytest.raises(ValueError, match="worker_bytes must equal"):
        cuda_integrity.run(workers=1, rounds=1, worker_bytes=1024)


def test_run_worker_reports_cleanup_sync_failure_without_primary_error() -> None:
    library = FakeLibrary()
    sync_calls = 0

    def sync() -> int:
        nonlocal sync_calls
        sync_calls += 1
        return 9 if sync_calls == 12 else 0

    library.cudaDeviceSynchronize = Function(sync)
    with pytest.raises(RuntimeError, match="CUDA cleanup failures: cudaDeviceSynchronize cleanup returned CUDA error 9"):
        cuda_integrity.run_worker(cast(C.CDLL, library), index=0, rounds=1,
                                  worker_bytes=cuda_integrity.MAX_WORKER_BYTES)
    assert sync_calls == 12


def invoke_main(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                run_result: Any, argv: list[str] | None = None) -> tuple[int, dict[str, Any]]:
    monkeypatch.setattr("sys.argv", argv or ["cuda_integrity.py"])
    monkeypatch.setattr(cuda_integrity.shutil, "which", lambda _name: "/usr/bin/systemd-run")
    monkeypatch.setattr(cuda_integrity.subprocess, "run", run_result)
    code = cuda_integrity.main()
    return code, json.loads(capsys.readouterr().out)


def test_main_missing_scope_runner_returns_partial_json(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("sys.argv", ["cuda_integrity.py"])
    monkeypatch.setattr(cuda_integrity.shutil, "which", lambda _name: None)
    assert cuda_integrity.main() == 2
    assert json.loads(capsys.readouterr().out) == {
        "status": "could_not_run", "reason": "systemd-run unavailable"}


def test_main_scoped_payload_uses_last_nonempty_line(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    code, output = invoke_main(
        monkeypatch, capsys,
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout='noise\n{"status":"pass"}\n',
                                                  stderr=""),
    )
    assert code == 0
    assert output == {"status": "pass"}


def test_main_scoped_empty_stdout_reports_command_result(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    code, output = invoke_main(
        monkeypatch, capsys,
        lambda *_args, **_kwargs: SimpleNamespace(returncode=7, stdout="", stderr="worker failed"),
    )
    assert code == 7
    assert output["status"] == "could_not_run"
    assert output["returncode"] == 7
    assert output["stderr"] == "worker failed"
    assert output["command"][1:4] == ["--user", "--scope", "--quiet"]


@pytest.mark.parametrize("error", [
    OSError("spawn denied"),
    subprocess.TimeoutExpired(cmd="systemd-run", timeout=75),
])
def test_main_scope_spawn_failure_attempts_cleanup(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], error: Exception) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_kwargs: Any) -> Any:
        calls.append(argv)
        if argv[0] == "/usr/bin/systemd-run":
            raise error
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    code, output = invoke_main(monkeypatch, capsys, fake_run)
    assert code == 2
    assert output["status"] == "could_not_run"
    assert output["error"].startswith(type(error).__name__ + ":")
    assert calls[1][:3] == ["systemctl", "--user", "stop"]
    assert calls[1][3].startswith("bb-cuda-integrity-")


def test_main_scope_spawn_failure_suppresses_cleanup_failure(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    calls = 0

    def fake_run(_argv: list[str], **_kwargs: Any) -> Any:
        nonlocal calls
        calls += 1
        raise OSError("cannot spawn")

    code, output = invoke_main(monkeypatch, capsys, fake_run)
    assert code == 2
    assert output["error"] == "OSError: cannot spawn"
    assert calls == 2


def test_main_nonzero_scoped_payload_preserves_worker_status(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    code, output = invoke_main(
        monkeypatch, capsys,
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout='{"status":"fail"}\n',
                                                  stderr=""),
    )
    assert code == 1
    assert output == {"status": "fail"}


def test_main_bounded_worker_success_returns_zero(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("sys.argv", ["cuda_integrity.py", "--_bounded-worker"])
    monkeypatch.setattr(cuda_integrity, "run", lambda *_args: {"status": "pass"})
    assert cuda_integrity.main() == 0
    assert json.loads(capsys.readouterr().out) == {"status": "pass"}


def test_module_entrypoint_exits_with_scope_runner_status(
        monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("sys.argv", ["cuda_integrity.py"])
    monkeypatch.setattr(cuda_integrity.shutil, "which", lambda _name: None)
    with pytest.raises(SystemExit) as raised:
        runpy.run_path(str(Path(cuda_integrity.__file__)), run_name="__main__")
    assert raised.value.code == 2
    assert json.loads(capsys.readouterr().out) == {
        "status": "could_not_run", "reason": "systemd-run unavailable"}


def test_duplicate_live_pointer_is_detected_before_overwriting_owner():
    import ctypes
    from types import SimpleNamespace

    from tools.cuda_integrity import allocate_slot

    original = ctypes.c_void_p(123)
    slots = {123: (original, 16, 7)}
    writes = []

    def allocate(pointer, _size):
        ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p))[0] = 123
        return 0

    fake = SimpleNamespace(cudaMalloc=allocate,
                           cudaMemset=lambda *args: writes.append(args))
    with pytest.raises(RuntimeError, match='already live pointer'):
        allocate_slot(fake, slots, 16, 9, 'duplicate control')
    assert slots == {123: (original, 16, 7)}
    assert writes == []
