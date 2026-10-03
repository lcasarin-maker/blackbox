"""Regression controls for defects registered during the debt audit."""

import json
import os
import subprocess
import sys
import time
import hashlib
import types

from test_bb_usable import _cargar
from test_bb_bash import _arbol_cgroup, _fila_escritorio, _syscall, correr
import test_bb_bash as bash_tests
from pathlib import Path

import pytest

from tools import provider_trace
from tools import cgroup_repro, cuda_integrity


def test_debt_schema_evidence_index_scope_01(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parent.parent
    manifest = root / "tasks/evidence/DEBT-SCHEMA-EVIDENCE-INDEX-SCOPE-01/migration.json"
    rows = json.loads(manifest.read_text(encoding="utf-8"))["files"]
    assert len(rows) == 4
    for row in rows:
        assert not (root / row["old"]).exists()
        assert hashlib.sha256((root / row["new"]).read_bytes()).hexdigest() == row["sha256"]
    runner = root / ".simplecode/run.py"
    positive = subprocess.run(
        [sys.executable, str(runner), "simplecode.verification.ledger_schema", "--root", str(root), "--check"],
        capture_output=True, text=True, timeout=60)
    assert positive.returncode == 0, positive.stdout + positive.stderr
    assert "could_not_run=0" in positive.stdout, positive.stdout
    # A genuine task placed outside governed folders must remain visible to the gate.
    misplaced = tmp_path / "tasks" / "misplaced"
    misplaced.mkdir(parents=True)
    card = root / "tasks/done/DEBT-RUFF-BB-USABLE-01.md"
    (misplaced / card.name).write_bytes(card.read_bytes())
    negative = subprocess.run(
        [sys.executable, str(runner), "simplecode.verification.ledger_schema", "--root", str(tmp_path), "--check"],
        capture_output=True, text=True, timeout=60)
    assert negative.returncode != 0, negative.stdout + negative.stderr
    assert card.name in negative.stdout + negative.stderr
    assert "could_not_run=1" in negative.stdout, negative.stdout


def test_bug_coverage_cli_subprocess_01(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parent.parent
    target = root / "tools/inventario.py"
    entrypoint = len(target.read_text(encoding="utf-8").splitlines())
    for patch_children in (True, False):
        config = root / ".coveragerc" if patch_children else tmp_path / "without-patch.ini"
        if not patch_children:
            config.write_text("[run]\n", encoding="utf-8")
        data = tmp_path / ("with-patch" if patch_children else "without-patch")
        report = data.with_suffix(".json")
        # This is an independent measurement, including its deliberately broken control.
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("COVERAGE_", "COV_CORE_"))}
        env.update(COVERAGE_FILE=str(data), COVERAGE_RCFILE=str(config))
        run = subprocess.run(
            [sys.executable, "-m", "coverage", "run", "--source=tools", "-m", "pytest", "-q",
             "tests/test_debt_registration_controls.py::test_debt_no_cover_inventario_146"],
            cwd=root, env=env, capture_output=True, text=True, timeout=60)
        assert run.returncode == 0, run.stdout + run.stderr
        exported = subprocess.run(
            [sys.executable, "-m", "coverage", "json", "-o", str(report)],
            cwd=root, env=env, capture_output=True, text=True, timeout=20)
        assert exported.returncode == 0, exported.stdout + exported.stderr
        measured = json.loads(report.read_text(encoding="utf-8"))["files"]["tools/inventario.py"]
        assert (entrypoint in measured["executed_lines"]) is patch_children, measured


def test_debt_broad_except_cuda_integrity_57() -> None:
    import ctypes

    slots = {7: (ctypes.c_void_p(7), 1, 1)}
    attempts = []

    def failed_free(pointer):
        attempts.append(pointer.value)
        return 8

    with pytest.raises(RuntimeError, match="cudaFree hole returned CUDA error 8") as raised:
        cuda_integrity.release_slots(slots, [7], failed_free, "hole")
    assert slots == {}
    assert attempts == [7]
    assert any("uncertain device state" in note for note in raised.value.__notes__)


def test_debt_broad_except_cuda_integrity_67() -> None:
    import ctypes

    slots = {7: (ctypes.c_void_p(7), 1, 1), 8: (ctypes.c_void_p(8), 1, 1)}
    attempts = []

    def free(pointer):
        attempts.append(pointer.value)
        return 8 if pointer.value == 7 else 0

    assert cuda_integrity.cleanup_slots(slots, free, lambda: 0) == [
        "pointer 7: cudaFree cleanup returned CUDA error 8"]
    assert slots == {}
    assert attempts == [7, 8]


def test_debt_broad_except_cuda_integrity_74() -> None:
    assert cuda_integrity.cleanup_slots({}, lambda _pointer: 0,
                                        lambda: 19) == ["cudaDeviceSynchronize cleanup returned CUDA error 19"]


def test_debt_broad_except_cuda_integrity_127() -> None:
    from test_memory_capture_and_cuda_integrity import FakeCuda

    fake = FakeCuda(fail_memset_after=3, fail_free_on_call=1)
    with pytest.raises(RuntimeError, match="cudaMemset initial allocation returned CUDA error 9") as raised:
        cuda_integrity.run_worker(fake, index=0, rounds=1, worker_bytes=4 * 1024 * 1024)
    assert len(fake.free_attempts) == 3
    assert len(set(fake.free_attempts)) == 3
    assert len(fake.buffers) == 1
    assert any("cleanup failures" in note for note in raised.value.__notes__)

    fake = FakeCuda(fail_free_on_call=1)
    memset_calls = 0
    def cancel_during_fill(pointer, value, size):
        nonlocal memset_calls
        memset_calls += 1
        if memset_calls == 3:
            raise KeyboardInterrupt("cancel CUDA worker")
        return fake.fill(pointer, value, size)
    fake.cudaMemset.function = cancel_during_fill
    with pytest.raises(KeyboardInterrupt, match="cancel CUDA worker") as cancelled:
        cuda_integrity.run_worker(fake, index=0, rounds=1, worker_bytes=4 * 1024 * 1024)
    assert len(fake.free_attempts) == 3
    assert len(set(fake.free_attempts)) == 3
    assert any("cleanup failures" in note for note in cancelled.value.__notes__)


def test_debt_broad_except_cuda_integrity_209(monkeypatch: pytest.MonkeyPatch,
                                              capsys: pytest.CaptureFixture[str]) -> None:
    error = RuntimeError("primary CUDA failure")
    error.add_note("cleanup failed for allocation 123")
    monkeypatch.setattr("sys.argv", ["cuda_integrity.py", "--_bounded-worker"])
    monkeypatch.setattr(cuda_integrity, "run", lambda *_args: (_ for _ in ()).throw(error))
    assert cuda_integrity.main() == 1
    result = json.loads(capsys.readouterr().out)
    assert result == {"status": "fail", "error": "RuntimeError: primary CUDA failure",
                      "notes": ["cleanup failed for allocation 123"]}
    monkeypatch.setattr(cuda_integrity, "run", lambda *_args: (_ for _ in ()).throw(KeyboardInterrupt("cancel")))
    with pytest.raises(KeyboardInterrupt, match="cancel"):
        cuda_integrity.main()
    capsys.readouterr()


def test_debt_broad_except_cgroup_repro_113(monkeypatch: pytest.MonkeyPatch,
                                           capsys: pytest.CaptureFixture[str]) -> None:
    from test_cgroup_repro import cuda_runtime

    runtime, events = cuda_runtime(monkeypatch, memset_result=17, fail_sync=3)
    runtime.cudaFree.callback = lambda ptr: events.append("free") or (0 if ptr is None else 23)
    assert cgroup_repro.cuda_worker("cuda_malloc", 1) == 33
    result = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert result["phase"] == "error"
    assert result["error"] == "RuntimeError: cudaMemset returned CUDA error 17"
    assert any("cudaFree returned CUDA error 23" in note for note in result["notes"])
    assert any("release cudaDeviceSynchronize returned CUDA error 44" in note for note in result["notes"])
    assert events.count("free") == 2  # warmup plus the one allocation cleanup attempt
    assert events.count("sync") == 3  # cleanup sync runs even after cudaFree reports failure

    runtime, events = cuda_runtime(monkeypatch, fail_sync=3)
    runtime.cudaMemset.callback = lambda *_args: (_ for _ in ()).throw(KeyboardInterrupt("cancel allocation"))
    runtime.cudaFree.callback = lambda pointer: events.append("free") or (
        0 if pointer is None else (_ for _ in ()).throw(RuntimeError("free teardown failed")))
    with pytest.raises(KeyboardInterrupt, match="cancel allocation") as cancelled:
        cgroup_repro.cuda_worker("cuda_malloc", 1)
    assert events.count("sync") == 3
    assert any("free teardown failed" in note for note in cancelled.value.__notes__)
    assert any("CUDA error 44" in note for note in cancelled.value.__notes__)


def test_debt_broad_except_cgroup_repro_150(monkeypatch: pytest.MonkeyPatch,
                                           capsys: pytest.CaptureFixture[str]) -> None:
    _assert_torch_primary_survives_cleanup(monkeypatch, capsys)
    _assert_torch_cancellation_survives_cleanup(monkeypatch)


def _assert_torch_primary_survives_cleanup(monkeypatch, capsys):
    import sys
    from test_cgroup_repro import fake_torch

    events = []
    torch = fake_torch(events, fail_fill=True)
    sync_calls = 0

    def failing_sync():
        nonlocal sync_calls
        sync_calls += 1
        events.append("sync")
        if sync_calls > 2:
            raise RuntimeError(f"sync teardown {sync_calls} failed")

    empty_cache_calls = 0

    def failing_empty_cache():
        nonlocal empty_cache_calls
        empty_cache_calls += 1
        events.append("empty_cache")
        if empty_cache_calls > 1:
            raise RuntimeError("empty_cache teardown failed")

    torch.cuda.synchronize = failing_sync
    torch.cuda.empty_cache = failing_empty_cache
    monkeypatch.setitem(sys.modules, "torch", torch)
    monkeypatch.setattr(cgroup_repro, "snapshot", lambda _pid: {"pid": 12})
    monkeypatch.setattr(cgroup_repro.time, "sleep", lambda _seconds: None)
    assert cgroup_repro.torch_worker(1) == 30
    result = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert result["error"] == "RuntimeError: fill failed"
    assert any("sync teardown 3 failed" in note for note in result["notes"])
    assert any("empty_cache teardown failed" in note for note in result["notes"])
    assert any("sync teardown 4 failed" in note for note in result["notes"])
    assert events.count("empty_cache") == 2  # warmup plus one teardown attempt

def _assert_torch_cancellation_survives_cleanup(monkeypatch):
    import sys
    from test_cgroup_repro import fake_torch

    class CancelTensor:
        def __init__(self, events, cancel):
            self.events = events
            self.cancel = cancel
        def fill_(self, _value):
            self.events.append("fill")
            if self.cancel:
                raise KeyboardInterrupt("cancel fill")

    events = []
    torch = fake_torch(events)
    tensor_count = 0
    original_empty = torch.empty

    def cancel_second_fill(*args, **kwargs):
        nonlocal tensor_count
        tensor_count += 1
        original_empty(*args, **kwargs)
        return CancelTensor(events, tensor_count > 1)

    torch.empty = cancel_second_fill
    sync_calls = 0
    def failing_cancel_sync():
        nonlocal sync_calls
        sync_calls += 1
        events.append("sync")
        if sync_calls > 2:
            raise RuntimeError(f"cancel teardown sync {sync_calls}")

    torch.cuda.synchronize = failing_cancel_sync
    monkeypatch.setitem(sys.modules, "torch", torch)
    with pytest.raises(KeyboardInterrupt, match="cancel fill") as cancelled:
        cgroup_repro.torch_worker(1)
    assert events.count("empty_cache") == 2
    assert any("cancel teardown sync 3" in note for note in cancelled.value.__notes__)
    assert any("cancel teardown sync 4" in note for note in cancelled.value.__notes__)



def _run_without_skips(selection: str) -> int:
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rs", selection],
        capture_output=True, text=True, cwd=root, timeout=60,
    )
    output = result.stdout + result.stderr
    assert " skipped" not in output, output
    assert "COULD_NOT_RUN" not in output, output
    return result.returncode


def test_debt_skip_test_calibra_techo_slice_164():
    assert _run_without_skips(
        "tests/test_calibra_techo_slice.py::test_una_muestra_ILEGIBLE_no_se_traga_en_silencio"
    ) == 0


def test_debt_skip_test_calibra_techo_slice_263():
    assert _run_without_skips(
        "tests/test_calibra_techo_slice.py::test_un_directorio_SIN_PERMISO_se_registra_y_no_pasa_por_vacio"
    ) == 0


def test_debt_skip_test_calibra_techo_slice_315():
    assert _run_without_skips(
        "tests/test_calibra_techo_slice.py::test_el_informe_NOMBRA_los_ficheros_ilegibles"
    ) == 0


def test_debt_skip_test_control_racha_118():
    assert _run_without_skips(
        "tests/test_control_racha.py::test_el_gate_sale_0_sobre_el_corpus_real"
    ) == 0


def test_debt_skip_test_control_racha_130():
    assert _run_without_skips(
        "tests/test_control_racha.py::test_control_negativo_el_gate_SI_sale_1_con_el_corte_bajado"
    ) == 0


def test_debt_skip_test_demonio_al_dia_52():
    assert _run_without_skips("tests/test_demonio_al_dia.py") == 0


def test_debt_skip_test_pii_scan_systemd_167():
    assert _run_without_skips("tests/test_pii_scan_systemd.py") == 0


def test_debt_skip_test_pii_scan_systemd_86():
    assert _run_without_skips("tests/test_pii_scan_systemd.py") == 0


def _simplecode_runner(tmp_path: Path) -> Path:
    """Copy the pinned ignored kit into a disposable subject repo for organ tests."""
    source = Path(__file__).resolve().parent.parent / ".simplecode"
    target = tmp_path / ".simplecode"
    target.mkdir()
    for name in ("run.py", "runtime.zip", "kit.lock"):
        (target / name).write_bytes((source / name).read_bytes())
    return target / "run.py"


def test_debt_exception_backlog_md_freeze_01(tmp_path: Path) -> None:
    """The current repo opts out; a declared frozen backlog blocks staged additions."""
    runner = _simplecode_runner(tmp_path)
    current = subprocess.run(
        [sys.executable, str(runner), "simplecode.verification.backlog_md_freeze", "--root", str(Path(__file__).resolve().parent.parent)],
        capture_output=True, text=True, check=False,
    )
    assert current.returncode == 0, current.stdout + current.stderr
    assert "not declared -- nothing frozen" in current.stdout

    root = tmp_path / "subject"
    (root / ".simplecode").mkdir(parents=True)
    (root / ".simplecode" / "backlog_md_frozen.json").write_text(
        '{"path":"BACKLOG.md","owner":"test","date":"2026-10-02","reason":"synthetic subject"}\n', encoding="utf-8")
    backlog = root / "BACKLOG.md"
    backlog.write_text("existing\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "BACKLOG.md"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base"], check=True)
    backlog.write_text("existing\nnew debt\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "BACKLOG.md"], check=True)
    negative = subprocess.run(
        [sys.executable, str(runner), "simplecode.verification.backlog_md_freeze", "--root", str(root)],
        capture_output=True, text=True, check=False,
    )
    assert negative.returncode == 1, negative.stdout + negative.stderr
    assert "adds 1 new line(s)" in negative.stdout


def test_debt_exception_lockfile_parity_01(tmp_path: Path) -> None:
    runner = _simplecode_runner(tmp_path)
    repo = Path(__file__).resolve().parent.parent
    current = subprocess.run(
        [sys.executable, str(runner), "simplecode.verification.lockfile_parity", "--root", str(repo)],
        capture_output=True, text=True, check=False,
    )
    assert current.returncode == 0, current.stdout + current.stderr
    assert "NO APLICA: no hay requirements-lock.txt" in current.stdout

    root = tmp_path / "subject"
    root.mkdir()
    (root / "pyproject.toml").write_text('[project]\ndependencies = ["synthetic-pkg==1.0"]\n', encoding="utf-8")
    (root / "requirements-lock.txt").write_text("synthetic-pkg==2.0\n", encoding="utf-8")
    negative = subprocess.run(
        [sys.executable, str(runner), "simplecode.verification.lockfile_parity", "--root", str(root)],
        capture_output=True, text=True, check=False,
    )
    assert negative.returncode == 1, negative.stdout + negative.stderr
    assert "DIVERGE synthetic-pkg" in negative.stdout


def test_debt_exception_red_team_corpus_01(tmp_path: Path) -> None:
    runner = _simplecode_runner(tmp_path)
    repo = Path(__file__).resolve().parent.parent
    current = subprocess.run(
        [sys.executable, str(runner), "simplecode.verification.red_team_corpus", "--root", str(repo), "--gate"],
        capture_output=True, text=True, check=False,
    )
    assert current.returncode == 0, current.stdout + current.stderr
    assert "generados hoy: 91" in current.stdout
    assert "casos registrados: 0" in current.stdout

    root = tmp_path / "subject"
    (root / "tasks").mkdir(parents=True)
    (root / "tasks" / "red_team_corpus.json").write_text(
        '{"casos":{"synthetic/removed":{"first_seen":"2026-10-02"}}}\n', encoding="utf-8")
    negative = subprocess.run(
        [sys.executable, str(runner), "simplecode.verification.red_team_corpus", "--root", str(root), "--gate"],
        capture_output=True, text=True, check=False,
    )
    assert negative.returncode == 1, negative.stdout + negative.stderr
    assert "FAIL: 1 caso(s) adversarial(es)" in negative.stderr


def _fake_observation_clock(monkeypatch: pytest.MonkeyPatch, *, advances: bool) -> list[float]:
    elapsed = [0.0]
    monkeypatch.setattr(cgroup_repro, "snapshot", lambda _pid: {"monotonic_ns": int(elapsed[0] * 1_000_000_000)})
    monkeypatch.setattr(cgroup_repro.time, "sleep", lambda seconds: elapsed.__setitem__(0, elapsed[0] + (seconds if advances else 0.0)))
    return elapsed


def _phase_times(output: str) -> dict[str, int]:
    return {event["phase"]: event["monotonic_ns"] for event in map(json.loads, output.splitlines())}


def test_debt_sunset_cgroup_repro_107(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """CUDA path retains allocation for the observation window, using mocked CUDA calls."""
    class Call:
        argtypes = None
        restype = None
        def __call__(self, *args):
            if args and hasattr(args[0], "_obj"):
                args[0]._obj.value = 1234
            return 0
    class Runtime:
        cudaMalloc = Call()
        cudaMallocManaged = Call()
        cudaMemset = Call()
        cudaFree = Call()
        cudaDeviceSynchronize = Call()
    monkeypatch.setattr(cgroup_repro.ctypes.util, "find_library", lambda _name: "libcudart-test")
    monkeypatch.setattr(cgroup_repro.ctypes, "CDLL", lambda _name: Runtime())
    elapsed = _fake_observation_clock(monkeypatch, advances=True)
    assert cgroup_repro.cuda_worker("cuda_malloc", 1) == 0
    held = _phase_times(capsys.readouterr().out)
    assert held["after_release"] - held["held"] >= 2_000_000_000
    assert elapsed[0] == 2

    _fake_observation_clock(monkeypatch, advances=False)
    assert cgroup_repro.cuda_worker("cuda_malloc", 1) == 0
    neutralized = _phase_times(capsys.readouterr().out)
    assert neutralized["after_release"] - neutralized["held"] < 2_000_000_000


def test_debt_sunset_cgroup_repro_149(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """PyTorch allocation path retains its live tensor for the bounded window; CUDA is mocked."""
    class Tensor:
        def fill_(self, _value):
            return self
    class Cuda:
        def is_available(self): return True
        def init(self): pass
        def synchronize(self): pass
        def empty_cache(self): pass
    fake_torch = types.SimpleNamespace(cuda=Cuda(), empty=lambda *_a, **_k: Tensor(), float16=object(), __version__="test")
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    elapsed = _fake_observation_clock(monkeypatch, advances=True)
    assert cgroup_repro.torch_worker(1) == 0
    held = _phase_times(capsys.readouterr().out)
    assert held["after_release"] - held["held"] >= 2_000_000_000
    assert elapsed[0] == 2

    _fake_observation_clock(monkeypatch, advances=False)
    assert cgroup_repro.torch_worker(1) == 0
    neutralized = _phase_times(capsys.readouterr().out)
    assert neutralized["after_release"] - neutralized["held"] < 2_000_000_000


def test_debt_sunset_cgroup_repro_167(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """CPU allocation worker exposes held and released phases across the same window."""
    elapsed = _fake_observation_clock(monkeypatch, advances=True)
    assert cgroup_repro.memory_worker("cpu_touch", 1) == 0
    held = _phase_times(capsys.readouterr().out)
    assert held["after_release"] - held["held"] >= 2_000_000_000
    assert elapsed[0] == 2

    _fake_observation_clock(monkeypatch, advances=False)
    assert cgroup_repro.memory_worker("cpu_touch", 1) == 0
    neutralized = _phase_times(capsys.readouterr().out)
    assert neutralized["after_release"] - neutralized["held"] < 2_000_000_000


def test_debt_sunset_atom_gpu_telemetry_1671(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    from tools import atom_gpu_telemetry as telemetry

    calls: list[float] = []
    samples = [0]
    def one_sample_then_stop(*_args, **_kwargs):
        if samples[0]:
            raise KeyboardInterrupt
        samples[0] += 1
        return []
    monkeypatch.setattr(telemetry, "leer_umbrales", lambda: {})
    monkeypatch.setattr(telemetry, "muestrear", one_sample_then_stop)
    monkeypatch.setattr(telemetry.time, "sleep", lambda seconds: calls.append(seconds))
    monkeypatch.setattr(sys, "argv", ["atom_gpu_telemetry", "--dry-run", "--interval-seconds", "0.25"])
    assert telemetry.main() == 0
    capsys.readouterr()
    assert calls == [0.25]
    assert samples[0] == 1


def test_debt_sunset_test_bb_bash_1550(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[float] = []
    now = [0.0]
    monkeypatch.setattr(bash_tests.subprocess, "run", lambda *_a, **_k: types.SimpleNamespace(stdout=""))
    monkeypatch.setattr(bash_tests.time, "time", lambda: now[0])
    def yielding_sleep(seconds: float) -> None:
        calls.append(seconds)
        now[0] += seconds
    monkeypatch.setattr(bash_tests.time, "sleep", yielding_sleep)
    with pytest.raises(AssertionError, match="ningun proceso"):
        bash_tests._esperar_proceso("synthetic-absent", timeout=0.1)
    assert calls == [0.05, 0.05]


def test_debt_sunset_test_bb_bash_1602(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[float] = []
    counter = [0]
    class Result:
        def __init__(self, stdout): self.stdout = stdout
    def pgrep_until_absent(*_args, **_kwargs):
        counter[0] += 1
        return Result("4242\n") if counter[0] < 3 else Result("")
    monkeypatch.setattr(bash_tests.subprocess, "run", pgrep_until_absent)
    monkeypatch.setattr(bash_tests.time, "sleep", lambda seconds: calls.append(seconds))
    monkeypatch.setattr(bash_tests.os, "killpg", lambda *_a: None)
    class Parent:
        pid = 4242
        def wait(self, **_kwargs): pass
    bash_tests._matar_electron_falso(Parent(), ["synthetic-renderer"], timeout=1)
    assert calls == [0.05, 0.05]


def _fresh_bb_data(tmp_path: Path, name: str) -> Path:
    data = tmp_path / name
    (data / "samples").mkdir(parents=True)
    return data


def test_debt_sunset_test_bb_bash_322(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bash_tests.test_swap_mide_el_RITMO_no_solo_el_nivel(_fresh_bb_data(tmp_path, "positive"), tmp_path)
    with monkeypatch.context() as no_wait:
        no_wait.setattr(bash_tests.time, "sleep", lambda _seconds: None)
        with pytest.raises(AssertionError):
            bash_tests.test_swap_mide_el_RITMO_no_solo_el_nivel(_fresh_bb_data(tmp_path, "neutralized"), tmp_path)


def test_debt_sunset_test_bb_bash_339(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bash_tests.test_control_negativo_sin_trafico_de_swap_el_ritmo_es_cero(_fresh_bb_data(tmp_path, "negative"), tmp_path)
    # The paired positive loses sensitivity when its interval is neutralized.
    with monkeypatch.context() as no_wait:
        no_wait.setattr(bash_tests.time, "sleep", lambda _seconds: None)
        with pytest.raises(AssertionError):
            bash_tests.test_swap_mide_el_RITMO_no_solo_el_nivel(_fresh_bb_data(tmp_path, "paired-positive"), tmp_path)


def test_debt_sunset_test_bb_bash_352(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bash_tests.test_un_contador_que_RETROCEDE_no_produce_un_ritmo_negativo(
        _fresh_bb_data(tmp_path, "negative-counter"), tmp_path)
    assert "time.sleep" not in bash_tests.test_un_contador_que_RETROCEDE_no_produce_un_ritmo_negativo.__code__.co_names


def test_debt_sunset_test_bb_bash_766(tmp_path: Path) -> None:
    bash_tests.test_cpu_top_NOMBRA_a_quien_quema_cpu(_fresh_bb_data(tmp_path, "cpu-positive"))
    assert "sleep" not in bash_tests.test_cpu_top_NOMBRA_a_quien_quema_cpu.__code__.co_names


def test_debt_sunset_test_bb_bash_802(tmp_path: Path) -> None:
    bash_tests.test_control_negativo_un_proceso_dormido_no_sale_como_que_quema(
        _fresh_bb_data(tmp_path, "cpu-negative"))
    assert "sleep" not in bash_tests.test_control_negativo_un_proceso_dormido_no_sale_como_que_quema.__code__.co_names



def test_bug_provider_trace_latency_overflow_01(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fixture = Path(__file__).parent / "fixtures" / "provider_trace" / "gpu-healthy.jsonl"
    records = [json.loads(line) for line in fixture.read_text(encoding="utf-8").splitlines()]
    for latency in (10**400, -10**400, True, -1, float("inf"), float("nan")):
        trace = [dict(record, milliseconds=latency) if record["event"] == "latency" else record for record in records]
        path = tmp_path / "trace.jsonl"
        path.write_text("\n".join(json.dumps(record) for record in trace), encoding="utf-8")
        assert provider_trace.main([str(path)]) == 2
        result = json.loads(capsys.readouterr().out)
        assert result["status"] == "unknown"
        assert result["could_not_run_count"] == 0
        assert any("invalid latency" in item for item in result["unknowns"])
    for latency in (0, 1, 1.5):
        trace = [json.dumps(dict(record, milliseconds=latency) if record["event"] == "latency" else record) for record in records]
        assert provider_trace.analyze_lines(trace)["status"] == "pass"
    fallback = fixture.with_name("gpu-to-cpu-respawn.jsonl")
    assert provider_trace.analyze_file(fallback)["status"] == "block"


def test_debt_noqa_bb_usable_249(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    executable = Path(__file__).resolve().parent.parent / "bin" / "bb-usable"
    lint = subprocess.run(["python3", "-m", "ruff", "check", "--select", "E731", "--ignore-noqa", str(executable)],
                          capture_output=True, text=True, check=False)
    assert lint.returncode == 0, lint.stdout + lint.stderr
    module = _cargar()
    monkeypatch.setattr(module, "notify", lambda message: None)
    monkeypatch.setattr(module, "probe", lambda: 0.001)

    def stop(_seconds: float) -> None:
        raise RuntimeError("stop before sampling")

    monkeypatch.setattr(module.time, "sleep", stop)
    with pytest.raises(RuntimeError, match="stop before sampling"):
        module.main()
    assert "[bb-usable] sonda sana de referencia:" in capsys.readouterr().err


def test_debt_shellcheck_bb_2(tmp_path: Path) -> None:
    datos = tmp_path / "blackbox"
    executable = Path(__file__).resolve().parent.parent / "bin" / "bb"
    source = executable.read_text(encoding="utf-8").replace("# shellcheck disable=SC2319\n", "")
    candidate = tmp_path / "status.sh"
    candidate.write_text(source, encoding="utf-8")
    lint = subprocess.run(["shellcheck", "--include=SC2319", str(candidate)], capture_output=True, text=True, check=False)
    assert lint.returncode == 0, lint.stdout + lint.stderr
    for low, expected in ((2 * 1024**3, "ARMADO"), (0, "FALTA")):
        result = correr(["status"], datos, _arbol_cgroup(tmp_path, low=low))
        assert expected in _fila_escritorio(result)


def test_debt_shellcheck_bb_2286(tmp_path: Path) -> None:
    datos = tmp_path / "blackbox"
    for low, expected in ((2 * 1024**3, "ARMADO"), (0, "FALTA")):
        result = correr(["status"], datos, _arbol_cgroup(tmp_path / "cgroups with spaces", low=low))
        assert expected in _fila_escritorio(result), result.stdout + result.stderr


def _run_script(path: Path, argv: list[str], expected: int) -> tuple[str, str]:
    root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, str(path), *argv], cwd=root, env=env,
        text=True, capture_output=True, timeout=10, check=False)
    assert result.returncode == expected, result.stdout + result.stderr
    return result.stdout, result.stderr


def _assert_no_cover_entrypoint(script: str, tmp_path: Path) -> None:
    import re

    source = Path(__file__).resolve().parent.parent / "tools" / script
    if script == "check_harvest_accepted.py":
        accepted = tmp_path / "accepted.md"
        accepted.write_text(
            '---\nid: HARVEST-TEST\naccepted: {by: maintainer, date: "2026-10-02", trigger: reopen-on-regression}\n---\n',
            encoding="utf-8")
        out, _ = _run_script(source, [str(accepted)], 0)
        assert "accepted completo" in out
        out, err = _run_script(source, [], 2)
        assert "uso:" in err
    elif script == "control_racha.py":
        samples = tmp_path / "samples"
        samples.mkdir()
        (samples / "valid.jsonl").write_text(
            '{"ts":"2026-09-15T03:00:00-0600","psi":{"mem_full":0}}\n',
            encoding="utf-8")
        out, _ = _run_script(source, ["--muestras", str(samples)], 0)
        assert "corpus 1 muestras" in out
        _, err = _run_script(source, ["--codex-invalid-argument"], 2)
        assert "unrecognized arguments" in err
    else:
        out, _ = _run_script(source, ["--help"], 0)
        assert "usage:" in out.lower()
        _, err = _run_script(source, ["--codex-invalid-argument"], 2)
        assert "unrecognized arguments" in err

    # A flipped launcher exit is the mutation this regression must catch.
    original = source.read_text(encoding="utf-8")
    if script == "check_harvest_accepted.py":
        mutated = original.replace("    main()\n", "    sys.exit(0)\n")
    else:
        mutated, count = re.subn(
            r"(?m)^if __name__ == [\"']__main__[\"']:\s*(?:#.*)?\n\s*(?:sys\.exit|raise SystemExit)\(main\(\)\)",
            'if __name__ == "__main__":\n    sys.exit(0)', original, count=1)
        assert count == 1
    mutant = tmp_path / script
    mutant.write_text(mutated, encoding="utf-8")
    if script == "check_harvest_accepted.py":
        mutant_argv = []
    else:
        mutant_argv = ["--codex-invalid-argument"]
    with pytest.raises(AssertionError):
        _run_script(mutant, mutant_argv, 2)


def test_debt_no_cover_atom_gpu_telemetry_1676(tmp_path):
    _assert_no_cover_entrypoint("atom_gpu_telemetry.py", tmp_path)


def test_debt_no_cover_calibra_latencia_x_333(tmp_path):
    _assert_no_cover_entrypoint("calibra_latencia_x.py", tmp_path)


def test_debt_no_cover_calibra_psi_322(tmp_path):
    _assert_no_cover_entrypoint("calibra_psi.py", tmp_path)


def test_debt_no_cover_calibra_techo_slice_226(tmp_path):
    _assert_no_cover_entrypoint("calibra_techo_slice.py", tmp_path)


def test_debt_no_cover_check_harvest_accepted_157(tmp_path):
    _assert_no_cover_entrypoint("check_harvest_accepted.py", tmp_path)


def test_debt_no_cover_control_racha_160(tmp_path):
    _assert_no_cover_entrypoint("control_racha.py", tmp_path)


def test_debt_no_cover_inventario_146(tmp_path):
    _assert_no_cover_entrypoint("inventario.py", tmp_path)


def test_debt_no_cover_mutacion_alcanza_66(tmp_path):
    _assert_no_cover_entrypoint("mutacion_alcanza.py", tmp_path)


def test_debt_no_cover_nombra_victimas_271(tmp_path):
    _assert_no_cover_entrypoint("nombra_victimas.py", tmp_path)


def test_debt_no_cover_presupuesto_memoria_497(tmp_path):
    _assert_no_cover_entrypoint("presupuesto_memoria.py", tmp_path)


def test_debt_shellcheck_bb_subject_01(tmp_path: Path) -> None:
    data = tmp_path / "data"
    audit = tmp_path / "audit with spaces"
    audit.mkdir()
    now = int(time.time())
    (audit / "audit.log.1").write_text(_syscall(now - 300, 9101, pid=1111, comm='"old"'), encoding="utf-8")
    (audit / "audit.log").write_text(_syscall(now - 10, 9102, pid=2222, comm='"new"'), encoding="utf-8")
    result = correr(["sigterm", "10 minutes ago"], data, {"BLACKBOX_AUDIT_DIR": str(audit)})
    assert "old[1111]" in result.stdout, result.stdout + result.stderr
    assert "new[2222]" in result.stdout, result.stdout + result.stderr
    assert "el registro cubre:" in result.stdout
    for path in audit.iterdir():
        path.write_text(_syscall(now - 10, 9103, pid=3333, key="unrelated"), encoding="utf-8")
    negative = correr(["sigterm", "10 minutes ago"], data, {"BLACKBOX_AUDIT_DIR": str(audit)})
    assert "0 senales registradas" in negative.stdout
    assert "3333" not in negative.stdout
