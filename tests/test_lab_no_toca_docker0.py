"""El laboratorio de Docker no puede tocar el puente de produccion (incidente 2026-10-12 07:55:30).

`dockerd --bridge=none` elimino `docker0` del host al arrancar el segundo dockerd del laboratorio; `atlas-pgvector`
(red bridge) quedo sin red hasta que se reinicio Docker de produccion a las 13:16. Estas pruebas leen el script,
porque levantar un dockerd real exige root; el limite esta declarado en la ficha.
"""

from __future__ import annotations

from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "tools" / "portero_docker_lab.sh"


def _codigo() -> list[str]:
    """Lineas de codigo, sin comentarios puros."""
    return [l for l in SCRIPT.read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("#")]


def test_el_dockerd_del_lab_no_desactiva_el_puente_por_defecto() -> None:
    assert not any("--bridge=none" in l for l in _codigo())


def test_el_lab_usa_su_propio_puente_con_su_propia_subred() -> None:
    codigo = "\n".join(_codigo())
    assert "--bridge=bblab0" in codigo and "--bip=172.31.250.1/24" in codigo
    assert "docker0" in codigo, "debe vigilar el puente de produccion"


def test_up_aborta_si_docker0_desaparece_y_down_borra_solo_su_puente() -> None:
    codigo = "\n".join(_codigo())
    assert 'DOCKER0_ANTES' in codigo and "ip link show docker0" in codigo
    assert "ip link del bblab0" in codigo
    assert "ip link del docker0" not in codigo
