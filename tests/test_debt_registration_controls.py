"""Regression controls for defects registered during the debt audit."""

import json
import subprocess
import sys

from test_bb_usable import _cargar
from test_bb_bash import _arbol_cgroup, _fila_escritorio, correr
from pathlib import Path

import pytest

from tools import provider_trace


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
