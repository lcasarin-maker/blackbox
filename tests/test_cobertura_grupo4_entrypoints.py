"""Guardas `if __name__ == "__main__"` de canario_motor, gpumem, huella_host, reloj_atascado y verifica_proveedor_gpu.

Cada prueba corre el modulo como script en un interprete hijo (`python -m tools.X`), el mismo camino que usan los
timers y `bb`; el codigo de salida y la salida estandar son lo observable. DEBT-COBERTURA-PISO-REBAJADO-01.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "verifica_proveedor_gpu"


def _script(modulo: str, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", f"tools.{modulo}", *args],
        cwd=REPO,
        env={**os.environ, **(env or {})},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_canario_motor_como_script_con_interruptor_off_sale_0_y_declara_off(tmp_path: Path) -> None:
    done = _script("canario_motor", "--paso", env={"BLACKBOX_DATA": str(tmp_path)})
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == {"modo": "off", "estado_general": None}
    assert not (tmp_path / "interruptores").exists()  # off no escribe


def test_gpumem_como_script_sin_region_sale_3_y_lo_dice(tmp_path: Path) -> None:
    done = _script("gpumem", "--raiz", str(tmp_path))
    assert done.returncode == 3, done.stderr
    assert done.stdout.startswith("SIN_REGION: dmem.capacity vacio")


def test_huella_host_como_script_con_paso_off_sale_0_sin_escribir_nada(tmp_path: Path) -> None:
    done = _script("huella_host", "--paso", env={"BLACKBOX_DATA": str(tmp_path)})
    assert done.returncode == 0, done.stderr
    assert list(tmp_path.iterdir()) == []


def _telemetria(tmp_path: Path, util: float, clk: float) -> subprocess.CompletedProcess[str]:
    fila = {"ts": "2026-10-12T22:00:00+00:00", "gpu_util_pct": util, "sm_clk_mhz": clk, "gpu_power_w": 15.0, "zonas": {"gpu": {"temp_c": 50.0}}, "throttle": "0x0000000000000000"}
    (tmp_path / "atom_gpu_telemetry.jsonl").write_text("".join(json.dumps(fila) + "\n" for _ in range(20)), encoding="utf-8")
    # BB_RELOJ_CAPTURA=off: el ATASCADO de esta prueba no pide root ni lanza una unidad de verdad (la captura se prueba con
    # falsos en tests/test_reloj_atascado.py); la salida lo declara como could_not_run.
    return _script("reloj_atascado", env={"BLACKBOX_DATA": str(tmp_path), "BB_RELOJ_CAPTURA": "off"})


def test_reloj_atascado_como_script_con_telemetria_sana_sale_0(tmp_path: Path) -> None:
    done = _telemetria(tmp_path, 96, 2400)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["estado"] == "SANO"


def test_reloj_atascado_como_script_con_telemetria_atascada_sale_1_con_el_remedio(tmp_path: Path) -> None:
    done = _telemetria(tmp_path, 96, 660)
    assert done.returncode == 1, done.stderr
    salida = json.loads(done.stdout)
    assert salida["estado"] == "ATASCADO" and "adaptador" in salida["remedio"]
    assert salida["captura_incidente"]["estado"] == "could_not_run"  # desactivada y declarada, nunca callada


def _docker_falso(bin_dir: Path, maps: str, apps: str) -> dict[str, str]:
    """Un `docker` de verdad en el PATH: responde al exec de maps (`sh -c`) y al de nvidia-smi."""
    maps_f, apps_f = bin_dir / "maps.txt", bin_dir / "apps.txt"
    maps_f.write_text(maps, encoding="utf-8")
    apps_f.write_text(apps, encoding="utf-8")
    docker = bin_dir / "docker"
    docker.write_text(f'#!/bin/sh\nif [ "$3" = "sh" ]; then cat "{maps_f}"; else cat "{apps_f}"; fi\n', encoding="utf-8")
    docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
    return {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}


def test_verifica_proveedor_gpu_como_script_gpu_sale_0(tmp_path: Path) -> None:
    maps = (FIXTURES / "gpu_maps.txt").read_text(encoding="utf-8")
    done = _script("verifica_proveedor_gpu", "c", env=_docker_falso(tmp_path, maps, "236, 34345\n"))
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["verdict"] == "GPU"


def test_verifica_proveedor_gpu_como_script_cpu_fallback_sale_1(tmp_path: Path) -> None:
    maps = (FIXTURES / "cpu_fallback_maps.txt").read_text(encoding="utf-8")
    done = _script("verifica_proveedor_gpu", "c", env=_docker_falso(tmp_path, maps, ""))
    assert done.returncode == 1, done.stderr
    assert json.loads(done.stdout)["verdict"] == "CPU_FALLBACK"
