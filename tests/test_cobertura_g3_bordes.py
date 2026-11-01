"""DEBT-COBERTURA-PISO-REBAJADO-01, grupo 3: bordes que faltaban en gpumem_historial y los puntos de
entrada `python -m` de calibra_calor, entrega_cosecha_foro, hid_inventario y monitor_distros.

Los puntos de entrada se corren en un interprete hijo (coverage los mide con `patch = subprocess`) contra
directorios en tmp_path: el codigo ejecutado es el real, lo observado es el rc y la salida.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tools import gpumem_historial

ROOT = Path(__file__).resolve().parents[1]


def _modulo(nombre: str, *args: str, datos: Path, extra: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "BLACKBOX_DATA": str(datos), **(extra or {})}
    return subprocess.run([sys.executable, "-m", nombre, *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, check=False, timeout=60)


# ---------------------------------------------------------------- gpumem_historial

def test_hojas_de_una_fila_ausente_o_vacia_es_dict_vacio() -> None:
    assert gpumem_historial._hojas(None) == {}
    assert gpumem_historial._hojas({}) == {}
    assert gpumem_historial._hojas({"hojas": [{"quien": "a", "gib": 1.5}]}) == {"a": 1.5}


def test_gpumem_historial_como_script_imprime_el_resumen_del_historial(tmp_path: Path) -> None:
    fila = {"ts": "2026-10-13T12:00:00+00:00", "boot_id": "b", "estado": "OK", "pico_por_quien": {"a": 3.0}}
    (tmp_path / "gpumem_historial.jsonl").write_text(json.dumps(fila) + "\n", encoding="utf-8")
    proc = _modulo("tools.gpumem_historial", datos=tmp_path)
    assert proc.returncode == 0
    assert json.loads(proc.stdout) == {"filas": 1, "picos_por_quien": {"a": 3.0}, "ultimo_estado": "OK"}


# ---------------------------------------------------------------- puntos de entrada `python -m`

def test_calibra_calor_como_script_sin_telemetria_es_could_not_run_rc2(tmp_path: Path) -> None:
    proc = _modulo("tools.calibra_calor", "--telemetria", str(tmp_path / "no.jsonl"), datos=tmp_path)
    assert proc.returncode == 2
    assert "COULD_NOT_RUN: no existe la telemetria" in proc.stderr


def test_entrega_cosecha_foro_como_script_sin_destino_imprime_el_uso_rc2(tmp_path: Path) -> None:
    proc = _modulo("tools.entrega_cosecha_foro", datos=tmp_path)
    assert proc.returncode == 2
    assert "uso: python -m tools.entrega_cosecha_foro" in proc.stderr and proc.stdout == ""


def test_hid_inventario_como_script_sin_hid_ni_linea_base_es_indeterminado_rc2(tmp_path: Path) -> None:
    usb = tmp_path / "usb"
    usb.mkdir()
    entrada = tmp_path / "input"
    entrada.write_text("", encoding="utf-8")
    proc = _modulo("tools.hid_inventario", "--sys-usb", str(usb), "--input", str(entrada),
                   "--estado", str(tmp_path / "estado.json"), "--kernel", "6.17.0-test", "--no-guardar", datos=tmp_path)
    assert proc.returncode == 2
    salida = json.loads(proc.stdout)
    assert salida["veredicto"] == "INDETERMINADO" and salida["kernel"] == "6.17.0-test"
    assert not (tmp_path / "estado.json").exists()  # --no-guardar


def test_monitor_distros_como_script_con_interruptor_apagado_no_hace_nada_rc0(tmp_path: Path) -> None:
    proc = _modulo("tools.monitor_distros", "--paso", datos=tmp_path)
    assert proc.returncode == 0
    assert json.loads(proc.stdout) is None
    assert not (tmp_path / "monitor_distros_estado.json").exists()
