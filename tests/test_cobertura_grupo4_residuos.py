"""Lineas que las suites de hallazgo y guardia_termico_predictivo dejaban sin ejecutar.
DEBT-COBERTURA-PISO-REBAJADO-01. Sin dobles que solo cuenten llamadas: cada prueba afirma archivos, valores o codigos de salida."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import NoReturn

import pytest

from tools import guardia_termico_predictivo as g
from tools import hallazgo as h

REPO = Path(__file__).resolve().parent.parent


# --- hallazgo ---------------------------------------------------------------------------------------------------


def test_leer_machine_id_distingue_ausente_ilegible_y_legible(tmp_path: Path) -> None:
    ok = tmp_path / "machine-id"
    ok.write_text("abcdef0123456789\n", encoding="utf-8")
    assert h._leer_machine_id(str(ok)) == "abcdef0123456789"  # el salto de linea se recorta
    assert h._leer_machine_id(str(tmp_path / "no-existe")) == "UNSUPPORTED"
    assert h._leer_machine_id(str(tmp_path)) == "COLLECTION_FAILED"  # un directorio: OSError que no es FileNotFoundError


def test_nodo_anonimo_sobre_archivos_reales_hashea_y_declara_ausencias(tmp_path: Path) -> None:
    ok = tmp_path / "machine-id"
    ok.write_text("abcdef0123456789\n", encoding="utf-8")
    nodo = h.nodo_anonimo(lambda _ruta: h._leer_machine_id(str(ok)))
    assert nodo.startswith("node-") and len(nodo) == len("node-") + 8 and "abcdef" not in nodo
    assert h.nodo_anonimo(lambda _ruta: h._leer_machine_id(str(tmp_path / "no-existe"))) == "COLLECTION_FAILED"
    assert h.nodo_anonimo(lambda _ruta: h._leer_machine_id(str(tmp_path))) == "COLLECTION_FAILED"


def test_bandeja_sigue_blackbox_data_y_cae_en_el_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path / "datos"))
    assert h.bandeja() == tmp_path / "datos" / "hallazgos"
    monkeypatch.delenv("BLACKBOX_DATA")
    monkeypatch.setenv("HOME", str(tmp_path / "casa"))
    assert h.bandeja() == tmp_path / "casa" / ".local/share/blackbox" / "hallazgos"


def test_un_esquema_distinto_se_reporta_con_la_version_esperada() -> None:
    base = h.construye(
        h.Hallazgo(
            id="bb-2026-10-11-corte-abrupto-54b71618",
            tipo="corte_abrupto",
            confianza="medido",
            generado="2026-10-11T12:13:23-06:00",
            por="bb reboots",
            nodo="node-9d835fe3",
            datos="reboots.jsonl#54b7161869da4fc99f7becb9571f529d",
            atlas_refs=("knowledge/investigations/gb10_cortes_2026-10-11/00_INDICE.md",),
            fuentes="- Veredicto de `reboots.jsonl`: CORTE_ABRUPTO.",
            inferencia="- [inferencia] causa indeterminada.",
        )
    )
    assert h.valida(base) == []  # control: el original es valido
    ajeno = base.replace('esquema: "bb-hallazgo/1"', 'esquema: "bb-hallazgo/2"')
    assert ajeno != base
    assert h.valida(ajeno) == [f"esquema distinto de {h.ESQUEMA}"]


# --- guardia_termico_predictivo ---------------------------------------------------------------------------------


class _Alto(Exception):
    """Corta el bucle `while True` de main tras la primera vuelta."""


def test_main_sin_argumentos_decide_una_vuelta_registra_y_duerme_5s(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ahora = datetime.now(timezone.utc)
    sube = [
        {"ts": (ahora - timedelta(seconds=5 * (7 - i))).isoformat(), "boot_id": "b" * 8, "gpu_power_w": 10.0, "zonas": [{"zona": "z0", "temp_c": 90.0 + i}]}
        for i in range(8)
    ]
    (tmp_path / "interruptores.json").write_text(json.dumps({"modos": {g.NOMBRE: "observar"}}), encoding="utf-8")
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["guardia"])
    monkeypatch.setattr(g, "lee_cola", lambda: sube)
    pausas: list[float] = []

    def duerme(s: float) -> NoReturn:
        pausas.append(s)
        raise _Alto

    monkeypatch.setattr(g.time, "sleep", duerme)
    with pytest.raises(_Alto):
        g.main()
    assert pausas == [5]
    filas = [json.loads(linea) for linea in (tmp_path / "interruptores" / f"{g.NOMBRE}.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(filas) == 1 and filas[0]["modo"] == "observar" and filas[0]["habria_actuado"] is True


def test_guardia_como_script_con_repasa_imprime_el_informe_vacio(tmp_path: Path) -> None:
    (tmp_path / "atom_gpu_telemetry.jsonl").write_text("", encoding="utf-8")
    done = subprocess.run(
        [sys.executable, "-m", "tools.guardia_termico_predictivo", "--repasa"],
        cwd=REPO,
        env={**os.environ, "BLACKBOX_DATA": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == {}

