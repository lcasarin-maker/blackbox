"""Regression controls for defects registered during the debt audit."""

import json
import subprocess
import sys
import types

from test_bb_usable import _cargar
from test_bb_bash import _arbol_cgroup, _fila_escritorio, correr
import test_bb_bash as bash_tests
from pathlib import Path

import pytest

from tools import provider_trace
from tools import cgroup_repro


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
    elapsed = [0.0]
    observed: list[float] = []
    monkeypatch.setattr(telemetry.time, "monotonic", lambda: elapsed[0])
    def one_sample_then_stop(*_args, **_kwargs):
        if samples[0]:
            observed.append(elapsed[0])
            assert observed[-1] - observed[-2] == 0.25
            raise KeyboardInterrupt
        observed.append(elapsed[0])
        samples[0] += 1
        return []
    monkeypatch.setattr(telemetry, "leer_umbrales", lambda: {})
    monkeypatch.setattr(telemetry, "muestrear", one_sample_then_stop)
    def advance(seconds: float) -> None:
        calls.append(seconds)
        elapsed[0] += seconds
    monkeypatch.setattr(telemetry.time, "sleep", advance)
    monkeypatch.setattr(sys, "argv", ["atom_gpu_telemetry", "--dry-run", "--interval-seconds", "0.25"])
    assert telemetry.main() == 0
    capsys.readouterr()
    assert calls == [0.25]
    assert samples[0] == 1

    calls.clear()
    elapsed[0] = 0.0
    samples[0] = 0
    observed.clear()
    with monkeypatch.context() as neutralized:
        neutralized.setattr(telemetry.time, "sleep", lambda _seconds: None)
        with pytest.raises(AssertionError):
            telemetry.main()


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
    source = bash_tests.BB.read_text(encoding="utf-8")
    without_rate = source.replace('v=(a-b)/d', 'v=(a-b)')
    assert without_rate != source
    mutant = tmp_path / "bb-without-rate-normalization"
    mutant.write_text(without_rate, encoding="utf-8")
    mutant.chmod(0o755)
    mutant_tmp = tmp_path / "rate-mutant-inputs"
    mutant_tmp.mkdir()
    with monkeypatch.context() as sourcecopy:
        sourcecopy.setattr(bash_tests, "BB", mutant)
        with pytest.raises(AssertionError):
            bash_tests.test_swap_mide_el_RITMO_no_solo_el_nivel(
                _fresh_bb_data(tmp_path, "rate-mutant"), mutant_tmp)


def test_debt_sunset_test_bb_bash_339(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data = _fresh_bb_data(tmp_path, "negative")
    bash_tests.test_control_negativo_sin_trafico_de_swap_el_ritmo_es_cero(data, tmp_path)
    assert bash_tests.muestras(data)[-1]["swap"]["in_pag_s"] == 0.0


def test_debt_sunset_test_bb_bash_352(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bash_tests.test_un_contador_que_RETROCEDE_no_produce_un_ritmo_negativo(
        _fresh_bb_data(tmp_path, "negative-counter"), tmp_path)
    original = bash_tests.BB.read_text(encoding="utf-8")
    vulnerable = original.replace('printf "%.1f", (v>0?v:0)', 'printf "%.1f", v')
    assert vulnerable != original
    mutant = tmp_path / "bb-without-swap-clamp"
    mutant.write_text(vulnerable, encoding="utf-8")
    mutant.chmod(0o755)
    mutant_data = _fresh_bb_data(tmp_path, "mutant-counter")
    mutant_tmp = tmp_path / "mutant-inputs"
    mutant_tmp.mkdir()
    (tmp_path / "date-count").unlink(missing_ok=True)
    with monkeypatch.context() as sourcecopy:
        sourcecopy.setattr(bash_tests, "BB", mutant)
        with pytest.raises(AssertionError) as mutant_failure:
            bash_tests.test_un_contador_que_RETROCEDE_no_produce_un_ritmo_negativo(mutant_data, mutant_tmp)
    assert "-899988.0" in str(mutant_failure.value)


def test_debt_sunset_test_bb_bash_766(tmp_path: Path) -> None:
    data = _fresh_bb_data(tmp_path, "cpu-positive")
    bash_tests.test_cpu_top_NOMBRA_a_quien_quema_cpu(data)
    assert "cpu_top" in bash_tests.muestras(data)[-1]


def test_debt_sunset_test_bb_bash_802(tmp_path: Path) -> None:
    data = _fresh_bb_data(tmp_path, "cpu-negative")
    bash_tests.test_control_negativo_un_proceso_dormido_no_sale_como_que_quema(data)
    assert "cpu_top" in bash_tests.muestras(data)[-1]


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
