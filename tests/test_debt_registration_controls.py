"""Regression controls for defects registered during the debt audit."""

import json
import os
import subprocess
import sys

from test_bb_usable import _cargar
from pathlib import Path

import pytest

from tools import provider_trace


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
