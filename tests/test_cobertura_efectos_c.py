"""Pruebas reales de rutas de efecto que la barrera de cobertura exigia: `mayores_por_rss` y el `main` de
`verify_forum_finding`. Sin dobles de la funcion bajo prueba: archivos en `tmp_path` y el `/proc` falso de una
carpeta. (`bb saber` y sus pruebas se retiraron el 2026-11-01: el consumidor de conocimiento tiene su propia CLI.)"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import origen_proceso as op
from tools import verify_forum_finding as vff


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
