"""Regression controls for defects registered during the debt audit."""

import json
import os
import subprocess
import sys

from test_bb_usable import _cargar
from test_bb_bash import _arbol_cgroup, _fila_escritorio, correr
from pathlib import Path

import pytest

from tools import provider_trace
from tools import cgroup_repro, cuda_integrity


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
