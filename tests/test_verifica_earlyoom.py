"""tools/verifica_earlyoom_sin_muertes_motor.sh: el close_check de DEBT-EARLYOOM-MOTOR-SIGUE-ELEGIBLE-01."""

import os
import subprocess
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "tools/verifica_earlyoom_sin_muertes_motor.sh"
MATA = 'oct 20 03:00:00 h earlyoom[1]: sending SIGTERM to process 42 uid 0 "VLLM::EngineCor": badness 900, VmRSS 8000 MiB\n'
SANO = 'oct 20 03:00:00 h earlyoom[1]: sending SIGTERM to process 43 uid 1000 "python3": badness 800, VmRSS 100 MiB\n'


def _corre(tmp_path: Path, dias: float, journal: str) -> subprocess.CompletedProcess[str]:
    forense = tmp_path / "forense"
    forense.mkdir()
    copia = forense / "etc_default_earlyoom.abc"
    copia.write_text("viejo", encoding="utf-8")
    t = time.time() - dias * 86400
    os.utime(copia, (t, t))
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    falso = bin_ / "journalctl"
    falso.write_text(f"#!/bin/sh\nprintf '%s' '{journal}'\n", encoding="utf-8")
    falso.chmod(0o755)
    env = {"PATH": f"{bin_}:{os.environ['PATH']}", "BB_FORENSE_DIR": str(forense)}
    return subprocess.run(["bash", str(SCRIPT)], env=env, capture_output=True, text=True)


def test_pasa_con_14_dias_y_cero_senales_al_motor(tmp_path: Path):
    r = _corre(tmp_path, 15, SANO)
    assert r.returncode == 0 and "motor desde" in r.stdout and ": 0" in r.stdout


def test_control_negativo_una_senal_al_motor_falla(tmp_path: Path):
    r = _corre(tmp_path, 15, MATA)
    assert r.returncode == 1 and ": 1" in r.stdout


def test_control_negativo_antes_de_14_dias_sale_2_y_no_dice_cero(tmp_path: Path):
    r = _corre(tmp_path, 3, SANO)
    assert r.returncode == 2 and "aun no" in r.stderr


def test_sin_copia_del_archivo_viejo_sale_2(tmp_path: Path):
    vacio = tmp_path / "vacio"
    vacio.mkdir()
    r = subprocess.run(["bash", str(SCRIPT)], env={"PATH": os.environ["PATH"], "BB_FORENSE_DIR": str(vacio)}, capture_output=True, text=True)
    assert r.returncode == 2 and "no se aplico" in r.stderr
