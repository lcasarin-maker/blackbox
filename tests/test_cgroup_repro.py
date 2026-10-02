import json
import builtins
import runpy
import sys
import weakref
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

from tools import cgroup_repro as repro


def make_snapshot_tree(tmp_path, *, cgroup="0::/demo", meminfo="MemAvailable: 42 kB\n", files=True):
    proc_root = tmp_path / "proc"
    proc = proc_root / "123"
    proc.mkdir(parents=True)
    (proc / "cgroup").write_text(cgroup + "\n", encoding="utf-8")
    (proc_root / "meminfo").write_text(meminfo, encoding="utf-8")
    pressure = proc_root / "pressure"
    pressure.mkdir()
    (pressure / "memory").write_text("some avg10=0.00\n", encoding="utf-8")
    root = tmp_path / "sys"
    root.mkdir()
    (root / "dmem.capacity").write_text("", encoding="utf-8")
    cg = root / "demo"
    cg.mkdir()
    if files:
        for name in ("memory.current", "memory.events", "memory.pressure", "dmem.current", "cpu.stat"):
            (cg / name).write_text("0\n", encoding="utf-8")
    monkeypatch = SimpleNamespace()
    return proc_root, root, cg


def patch_tree(monkeypatch, tree):
    proc_root, root, _cg = tree
    monkeypatch.setattr(repro, "PROC_ROOT", proc_root)
    monkeypatch.setattr(repro, "CGROUP_ROOT", root)


def test_snapshot_reads_effective_cgroup_and_root_only_capacity(tmp_path, monkeypatch):
    tree = make_snapshot_tree(tmp_path)
    patch_tree(monkeypatch, tree)
    result = repro.snapshot(123)
    assert result["proc_cgroup"] == "0::/demo"
    assert result["files"]["memory.current"] == {"value": "0", "error": None}
    assert result["files"]["dmem.capacity"] == {"value": "", "error": None}
    assert result["mem_available"] == "MemAvailable: 42 kB"
    assert result["host_memory_pressure"] == "some avg10=0.00"


def test_snapshot_reports_missing_proc_files_cgroup_path_and_unrecognized_entries(tmp_path, monkeypatch):
    tree = make_snapshot_tree(tmp_path, cgroup="1:name=systemd:/legacy", meminfo="unavailable field\n", files=False)
    patch_tree(monkeypatch, tree)
    result = repro.snapshot(123)
    assert result["cgroup_path"] is None
    assert result["files"]["memory.current"]["error"] == "cgroup v2 path unavailable"
    assert result["mem_available"] is None
    assert result["mem_available_error"] is None

    monkeypatch.setattr(repro, "PROC_ROOT", tmp_path / "absent")
    missing = repro.snapshot(456)
    assert missing["proc_cgroup"] is None
    assert "FileNotFoundError" in missing["proc_cgroup_error"]


def test_read_reports_decode_errors(tmp_path):
    path = tmp_path / "bad-utf8"
    path.write_bytes(b"\xff")
    value, error = repro.read(path)
    assert value is None
    assert error is not None
    assert "UnicodeDecodeError" in error


def test_worker_bounds_allocation_size(monkeypatch):
    monkeypatch.setattr("sys.argv", ["cgroup_repro.py", "--mib", "33"])
    with pytest.raises(SystemExit) as exc:
        repro.main()
    assert exc.value.code == 2


def test_memory_worker_and_dispatcher_emit_negative_and_positive_phases(monkeypatch, capsys):
    monkeypatch.setattr(repro, "snapshot", lambda _pid: {"pid": 12, "monotonic_ns": 1})
    monkeypatch.setattr(repro.time, "sleep", lambda _seconds: None)
    for api, expected in (("none", 0), ("cpu_touch", 2 * 1024 * 1024)):
        assert repro.worker(api, 2) == 0
        phases = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
        assert [entry["phase"] for entry in phases] == ["before", "held", "after_release"]
        assert phases[1]["requested_bytes"] == expected
    with pytest.raises(ValueError, match="unknown API"):
        repro.worker("invalid", 1)


@pytest.mark.parametrize("api", ["cuda_malloc", "cuda_malloc_managed", "pytorch_empty"])
def test_worker_dispatches_cuda_apis(api, monkeypatch, capsys):
    monkeypatch.setattr(repro, "snapshot", lambda _pid: {"pid": 1})
    monkeypatch.setattr(repro, "cuda_worker", lambda selected, mib: 40 if selected == api and mib == 2 else 0)
    monkeypatch.setattr(repro, "torch_worker", lambda mib: 41 if mib == 2 else 0)
    assert repro.worker(api, 2) in (40, 41)
    capsys.readouterr()


def cuda_runtime(monkeypatch, *, cuda_result=0, memset_result=0, fail_sync=0, free_result=0):
    events = []

    class Function:
        def __init__(self, callback):
            self.callback = callback
            self.argtypes = None
            self.restype = None
        def __call__(self, *args):
            return self.callback(*args)

    class Runtime:
        def __init__(self):
            self.sync_count = 0
            self.cudaMalloc = Function(lambda ptr, _size: setattr(ptr._obj, "value", 123) or events.append("malloc") or cuda_result)
            self.cudaMallocManaged = Function(lambda ptr, _size, _flags: setattr(ptr._obj, "value", 456) or events.append("managed") or cuda_result)
            self.cudaMemset = Function(lambda *_args: events.append("memset") or memset_result)
            self.cudaFree = Function(lambda ptr: events.append("free") or (free_result if ptr is not None else 0))
            self.cudaDeviceSynchronize = Function(self.synchronize)
        def synchronize(self):
            self.sync_count += 1
            events.append("sync")
            return 44 if self.sync_count == fail_sync else 0

    runtime = Runtime()
    monkeypatch.setattr(repro.ctypes.util, "find_library", lambda _name: "libcudart-test.so")
    monkeypatch.setattr(repro.ctypes, "CDLL", lambda _name: runtime)
    monkeypatch.setattr(repro, "snapshot", lambda _pid: {"pid": 12, "monotonic_ns": 1, "files": {}})
    monkeypatch.setattr(repro.time, "sleep", lambda _seconds: None)
    return runtime, events


@pytest.mark.parametrize("fail_free,fail_sync", [(True, False), (False, True)])
def test_cuda_context_warmup_errors_are_recorded(fail_free, fail_sync, monkeypatch, capsys):
    runtime, _events = cuda_runtime(monkeypatch, fail_sync=1 if fail_sync else 0)
    if fail_free:
        runtime.cudaFree.callback = lambda ptr: 17 if ptr is None else 0
    assert repro.cuda_worker("cuda_malloc", 1) == 33
    output = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert output["phase"] == "error"
    assert "warmup" in output["error"]


def test_cuda_missing_library_and_configured_signatures(capsys, monkeypatch):
    monkeypatch.setattr(repro.ctypes.util, "find_library", lambda _name: None)
    assert repro.cuda_worker("cuda_malloc", 1) == 32
    assert json.loads(capsys.readouterr().out)["error"] == "libcudart not found"

    runtime, events = cuda_runtime(monkeypatch)
    assert repro.cuda_worker("cuda_malloc_managed", 1) == 0
    assert runtime.cudaMalloc.argtypes == [repro.ctypes.POINTER(repro.ctypes.c_void_p), repro.ctypes.c_size_t]
    assert runtime.cudaFree.argtypes == [repro.ctypes.c_void_p]
    assert "managed" in events and events.index("memset") < len(events) - 1 - events[::-1].index("free")
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["phase"] == "after_release"


@pytest.mark.parametrize("failure,expected", [("allocation", "allocation returned"), ("memset", "cudaMemset returned"),
                                                ("sync", "CUDA error 44"), ("free", "cudaFree returned")])
def test_cuda_errors_are_reported_and_allocations_are_freed(failure, expected, monkeypatch, capsys):
    runtime, events = cuda_runtime(monkeypatch,
        cuda_result=17 if failure == "allocation" else 0,
        memset_result=17 if failure == "memset" else 0,
        fail_sync=3 if failure == "sync" else 0,
        free_result=17 if failure == "free" else 0)
    assert repro.cuda_worker("cuda_malloc", 1) == 33
    output = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert any(expected in entry.get("error", "") for entry in output)
    if failure != "allocation":
        assert events.count("free") == 2  # context warmup and allocation cleanup
    else:
        assert "malloc" in events
    assert runtime.cudaMalloc.restype is repro.ctypes.c_int


class FakeTensor:
    def __init__(self, events, fail_fill=False):
        self.events = events
        self.fail_fill = fail_fill
    def fill_(self, _value):
        self.events.append("fill")
        if self.fail_fill: raise RuntimeError("fill failed")


def fake_torch(events, *, available=True, fail_fill=False, references=None):
    torch = ModuleType("torch")
    setattr(torch, "__version__", "test-version")
    setattr(torch, "float16", object())
    tensor_count = 0
    def empty(*_args, **_kwargs):
        nonlocal tensor_count
        events.append("empty")
        tensor_count += 1
        tensor = FakeTensor(events, fail_fill and tensor_count > 1)
        if references is not None: references.append(weakref.ref(tensor))
        return tensor
    setattr(torch, "empty", empty)
    setattr(torch, "cuda", SimpleNamespace(is_available=lambda: available,
        init=lambda: events.append("init"), synchronize=lambda: events.append("sync"),
        empty_cache=lambda: events.append("empty_cache")))
    return torch


def test_torch_success_warms_allocates_fills_and_releases_cache(monkeypatch, capsys):
    events = []
    refs = []
    torch = fake_torch(events, references=refs)
    original_empty_cache = torch.cuda.empty_cache
    def check_release():
        original_empty_cache()
        if len(refs) == 2:
            assert refs[-1]() is None
    setattr(torch.cuda, "empty_cache", check_release)
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setattr(repro, "snapshot", lambda _pid: {"pid": 12, "monotonic_ns": 1, "files": {}})
    monkeypatch.setattr(repro.time, "sleep", lambda _seconds: None)
    assert repro.torch_worker(1) == 0
    phases = [json.loads(line)["phase"] for line in capsys.readouterr().out.splitlines()]
    assert phases == ["before_allocation", "held", "allocator_cache_released", "after_release"]
    assert events.count("empty_cache") == 2


@pytest.mark.parametrize("available,fail_fill,error", [(False, False, "torch.cuda.is_available() is false"),
                                                         (True, True, "fill failed")])
def test_torch_errors_are_reported_and_target_cache_is_released(available, fail_fill, error, monkeypatch, capsys):
    events = []
    monkeypatch.setitem(sys.modules, "torch", fake_torch(events, available=available, fail_fill=fail_fill))
    monkeypatch.setattr(repro, "snapshot", lambda _pid: {"pid": 12, "monotonic_ns": 1, "files": {}})
    monkeypatch.setattr(repro.time, "sleep", lambda _seconds: None)
    assert repro.torch_worker(1) == 30
    output = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert any(entry.get("error", "").endswith(error) for entry in output)
    if fail_fill:
        assert "empty_cache" in events
        assert output[-1]["phase"] == "allocator_cache_released"


def test_torch_import_failure_is_reported(monkeypatch, capsys):
    import builtins
    real_import = builtins.__import__
    def without_torch(name, *args, **kwargs):
        if name == "torch": raise ModuleNotFoundError("torch unavailable")
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", without_torch)
    assert repro.torch_worker(1) == 30
    assert "torch unavailable" in capsys.readouterr().out


def test_torch_release_is_a_noop_before_allocation(capsys):
    repro.release_torch_allocation(None, False)
    assert capsys.readouterr().out == ""


def test_parse_worker_output_checks_json_objects_and_required_phases():
    failures = repro.parse_worker_output("[]\n{broken\n", "none")
    assert "worker output must be a JSON object" in failures
    assert any(item.startswith("invalid JSON") for item in failures)
    assert "missing observation phase: held" in failures
    file_failure = repro.parse_worker_output(
        '{"phase":"before","files":{"memory.current":{"error":"denied"},"cpu.stat":{"error":null}}}\n', "none")
    assert "memory.current: denied" in file_failure
    assert repro.parse_worker_output('{"phase":"before"}\n{"phase":"held"}\n{"phase":"after_release"}', "none") == []


def test_run_case_parses_collection_failures_and_stops_timed_out_scope(monkeypatch):
    calls = []
    def fake_run(command, **_kwargs):
        calls.append(command)
        if command[0] == "systemd-run":
            raise subprocess_timeout(command)
        return SimpleNamespace(returncode=1, stdout="", stderr="permission denied")
    monkeypatch.setattr(repro.subprocess, "run", fake_run)
    timed_out = repro.run_case("none", "none", 1)
    assert any("TimeoutExpired" in item for item in timed_out["could_not_run"])
    assert any("unit stop failed" in item for item in timed_out["could_not_run"])
    assert calls[1] == ["systemctl", "--user", "stop", timed_out["unit"] + ".scope"]
    assert any("RuntimeMaxSec=60s" in item for item in timed_out["command"])

    monkeypatch.setattr(repro.subprocess, "run", lambda *_a, **_k: SimpleNamespace(returncode=0,
        stdout='{"phase":"error","error":"worker failed"}\n', stderr=""))
    malformed = repro.run_case("none", "none", 1)
    assert "worker failed" in malformed["could_not_run"]
    assert any("missing observation phase" in item for item in malformed["could_not_run"])


@pytest.mark.parametrize("raise_error", [False, True])
def test_run_case_marks_nonzero_and_collection_failures(raise_error, monkeypatch):
    def fake_run(command, **_kwargs):
        if raise_error:
            raise OSError("spawn denied")
        return SimpleNamespace(returncode=7, stdout="", stderr="unit failed")
    monkeypatch.setattr(repro.subprocess, "run", fake_run)
    result = repro.run_case("none", "none", 1)
    assert result["returncode"] in (7, None)
    assert result["could_not_run"]


def subprocess_timeout(command):
    return repro.subprocess.TimeoutExpired(command, 90)


def test_main_reports_missing_smi_and_runner_failure_as_partial(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["cgroup_repro.py", "--mib", "1", "--output", str(tmp_path / "missing.json")])
    monkeypatch.setattr(repro.shutil, "which", lambda _name: None)
    monkeypatch.setattr(repro, "run_case", lambda api, worker, _mib: {"api": api, "worker_api": worker, "could_not_run": []})
    assert repro.main() == 2
    result = json.loads((tmp_path / "missing.json").read_text(encoding="utf-8"))
    assert result["status"] == "partial"
    assert "nvidia-smi executable unavailable" in result["could_not_run"]
    assert json.loads(capsys.readouterr().out)["status"] == "partial"


@pytest.mark.parametrize("smi_result", ["nonzero", "timeout"])
def test_main_records_failed_nvidia_smi(smi_result, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["cgroup_repro.py", "--mib", "1", "--output", str(tmp_path / "smi.json")])
    monkeypatch.setattr(repro.shutil, "which", lambda _name: "/usr/bin/nvidia-smi")
    def fake_run(*_args, **_kwargs):
        if smi_result == "timeout": raise repro.subprocess.TimeoutExpired("nvidia-smi", 10)
        return SimpleNamespace(returncode=9, stdout="", stderr="device unavailable")
    monkeypatch.setattr(repro.subprocess, "run", fake_run)
    monkeypatch.setattr(repro, "run_case", lambda api, worker, _mib: {"api": api, "worker_api": worker, "could_not_run": []})
    assert repro.main() == 2
    data = json.loads((tmp_path / "smi.json").read_text(encoding="utf-8"))
    assert data["status"] == "partial"
    assert any("nvidia-smi" in item for item in data["could_not_run"])
    capsys.readouterr()


@pytest.mark.parametrize("scenario", [(True, False, 0), (True, True, 2), (False, False, 2)])
def test_main_status_and_host_measurement_collection(tmp_path, monkeypatch, capsys, scenario):
    smi_available, run_failure, expected = scenario
    output = tmp_path / "result.json"
    monkeypatch.setattr("sys.argv", ["cgroup_repro.py", "--mib", "1", "--output", str(output)])
    monkeypatch.setattr(repro.shutil, "which", lambda _name: "/usr/bin/nvidia-smi" if smi_available else None)
    monkeypatch.setattr(repro.subprocess, "run", lambda *_a, **_k: SimpleNamespace(returncode=0, stdout="GPU fake\n", stderr=""))
    def fake_run_case(api, worker, _mib):
        return {"api": api, "worker_api": worker, "could_not_run": ["fixture worker failure"] if run_failure else []}
    monkeypatch.setattr(repro, "run_case", fake_run_case)
    assert repro.main() == expected
    record = json.loads(output.read_text(encoding="utf-8"))
    assert (record["status"] == "observations_recorded") is (expected == 0)
    assert record["host"]["nvidia_smi"]
    assert json.loads(capsys.readouterr().out)["runs"] == 6


def test_main_worker_mode_and_registered_dmem_capacity(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["cgroup_repro.py", "--worker", "none", "--mib", "1"])
    monkeypatch.setattr(repro, "worker", lambda api, mib: 42 if (api, mib) == ("none", 1) else 0)
    assert repro.main() == 42
    capsys.readouterr()

    root = tmp_path / "sys"
    root.mkdir()
    (root / "dmem.capacity").write_text("registered\n", encoding="utf-8")
    monkeypatch.setattr(repro, "CGROUP_ROOT", root)
    output = tmp_path / "registered.json"
    monkeypatch.setattr("sys.argv", ["cgroup_repro.py", "--output", str(output)])
    monkeypatch.setattr(repro.shutil, "which", lambda _name: "/usr/bin/nvidia-smi")
    monkeypatch.setattr(repro.subprocess, "run", lambda *_a, **_k: SimpleNamespace(returncode=0, stdout="GPU fake", stderr=""))
    monkeypatch.setattr(repro, "run_case", lambda api, worker, _mib: {"api": api, "worker_api": worker, "could_not_run": []})
    assert repro.main() == 0
    assert "dmem_registration" not in json.loads(output.read_text(encoding="utf-8"))["host"]
    capsys.readouterr()


def test_running_file_executes_script_entrypoint(monkeypatch):
    import runpy
    monkeypatch.setattr("sys.argv", ["tools/cgroup_repro.py", "--worker", "none", "--mib", "1"])
    # The negative-control worker reads host counters but performs no allocation.
    monkeypatch.setattr(repro.time, "sleep", lambda _seconds: None)
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(Path(__file__).parents[1] / "tools" / "cgroup_repro.py"), run_name="__main__")
    assert exc.value.code == 0


@pytest.mark.parametrize("missing_name,raises", [("tools", False), ("tools.memory_profile", True)])
def test_script_profile_import_fallback_is_narrow(monkeypatch, missing_name, raises):
    script = Path(__file__).parents[1] / "tools" / "cgroup_repro.py"
    monkeypatch.syspath_prepend(str(script.parent))
    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "tools.memory_profile":
            raise ModuleNotFoundError("fixture import failure", name=missing_name)
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    if raises:
        with pytest.raises(ModuleNotFoundError, match="fixture import failure"):
            runpy.run_path(str(script), run_name="cgroup_repro_import_probe")
        return
    namespace = runpy.run_path(str(script), run_name="cgroup_repro_import_probe")
    assert callable(namespace["capture_memory_profile"])
