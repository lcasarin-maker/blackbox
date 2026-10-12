"""Pruebas reales de rutas de efecto que la barrera de cobertura exigia: `bb saber`, `mayores_por_rss` y el `main` de
`verify_forum_finding`. Sin dobles de la funcion bajo prueba: archivos en `tmp_path`, el entorno real de `ATLAS_KNOWLEDGE`
y el `/proc` falso de una carpeta."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import origen_proceso as op
from tools import saber, verify_forum_finding as vff


def _kb(tmp_path: Path, n: int) -> Path:
    kb = tmp_path / "knowledge"
    kb.mkdir()
    for i in range(n):
        (kb / f"nota{i}.md").write_text(f"linea uno\nclave-{i} aparece aqui\n", encoding="utf-8")
    (kb / "_privado.md").write_text("clave-oculta\n", encoding="utf-8")
    return kb


def test_saber_main_imprime_coincidencias_y_sale_0(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("ATLAS_KNOWLEDGE", str(_kb(tmp_path, 2)))
    assert saber.main(["clave-1"]) == 0
    salida = capsys.readouterr().out
    assert "nota1.md:2: clave-1 aparece aqui" in salida and "nota0.md" not in salida


def test_saber_main_cero_coincidencias_declara_el_alcance_y_sale_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("ATLAS_KNOWLEDGE", str(_kb(tmp_path, 2)))
    assert saber.main(["clave-oculta"]) == 1  # control negativo: el archivo `_privado.md` no se indexa
    err = capsys.readouterr().err
    assert "0 coincidencias en" in err and "2 archivos revisados" in err


def test_saber_main_trunca_con_aviso_y_ruta_ausente_es_could_not_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("ATLAS_KNOWLEDGE", str(_kb(tmp_path, 3)))
    assert saber.main(["aparece", "--max", "1"]) == 0
    assert "1 de 3 coincidencias (usa --max)" in capsys.readouterr().err
    monkeypatch.setenv("ATLAS_KNOWLEDGE", str(tmp_path / "no-existe"))
    assert saber.main(["x"]) == 2
    assert "COULD_NOT_RUN" in capsys.readouterr().err


def test_saber_regex_invalida_no_se_confunde_con_sin_resultados(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ATLAS_KNOWLEDGE", str(_kb(tmp_path, 1)))
    assert saber.main(["(", "--regex"]) == 2


def test_mayores_por_rss_cuenta_los_ilegibles_y_ordena(tmp_path: Path) -> None:
    def proceso(pid: str, rss: str) -> None:
        d = tmp_path / pid
        d.mkdir()
        campos = ["S", "1"] + ["0"] * 19 + [rss] + ["0"] * 5  # tras `) `: estado, ppid ... rss en el indice 21
        (d / "stat").write_text(f"{pid} (x) " + " ".join(campos) + "\n", encoding="ascii")
    proceso("10", "500")
    proceso("11", "900")
    (tmp_path / "12").mkdir()  # sin archivo stat: ilegible
    (tmp_path / "13").mkdir()
    (tmp_path / "13" / "stat").write_text("13 (x) basura\n", encoding="ascii")  # truncado: IndexError
    (tmp_path / "no-es-pid").mkdir()
    pids, vistos, ilegibles = op.mayores_por_rss(5, proc=tmp_path)
    assert pids == [11, 10] and vistos == 2 and ilegibles == 2


def test_verify_forum_finding_main_devuelve_fail_para_un_id_no_soportado(capsys: pytest.CaptureFixture[str]) -> None:
    assert vff.main(["--id", "NO-EXISTE-ESTE-ID"]) == 1
    salida = json.loads(capsys.readouterr().out)
    assert salida["status"] == "fail" and salida["reason"] == "unsupported forum finding ID"
