"""`bin/bb-parada-diagnostico`: lo que escribe al parar una unidad y el cableado de las cinco unidades que no deben morir en silencio."""

import os
import subprocess
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "bin/bb-parada-diagnostico"
UNIDADES = ("bb-guardia-proceso", "bb-portero", "bb-vigilante-memavail", "bb-vigilante-gpuoom", "bb-vigilante-termico")
LINEA = "ExecStopPost=-%h/projects/blackbox/bin/bb-parada-diagnostico %n $EXIT_STATUS $SERVICE_RESULT"


def _corre(datos: Path) -> subprocess.CompletedProcess[str]:
    env = {"PATH": os.environ["PATH"], "HOME": str(datos), "BLACKBOX_DATA": str(datos)}
    return subprocess.run([str(SCRIPT), "bb-prueba.service", "TERM", "success"], env=env, capture_output=True, text=True)


def test_registra_las_senales_recientes_y_no_las_viejas(tmp_path: Path):
    ahora = int(time.time())
    (tmp_path / "sigterm.jsonl").write_text(
        f'{{"ts":{ahora - 3600},"id":"a","senal":"SIGKILL","emisor":{{"comm":"emisor-viejo"}}}}\n'
        f'{{"ts":{ahora},"id":"b","senal":"SIGTERM","emisor":{{"comm":"emisor-reciente"}}}}\n', encoding="utf-8")
    r = _corre(tmp_path)
    log = (tmp_path / "paradas.log").read_text(encoding="utf-8")
    assert r.returncode == 0 and "unit=bb-prueba.service" in log
    assert "emisor-reciente" in log and "emisor-viejo" not in log  # control negativo: lo de hace una hora no entra


def test_sale_0_sin_sigterm_jsonl_y_declara_el_encabezado(tmp_path: Path):
    r = _corre(tmp_path)
    assert r.returncode == 0 and "exit_status=TERM service_result=success" in (tmp_path / "paradas.log").read_text(encoding="utf-8")


def test_las_cinco_unidades_lo_llaman_y_las_demas_no_cambian():
    for u in UNIDADES:
        texto = (RAIZ / f"systemd/{u}.service").read_text(encoding="utf-8")
        assert texto.count(LINEA) == 1, u
        assert texto.index("ExecStart=") < texto.index(LINEA) < texto.index("[Install]"), u
    assert LINEA not in (RAIZ / "systemd/bb-canario-motor.service").read_text(encoding="utf-8")  # control negativo
