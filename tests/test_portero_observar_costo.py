"""El modo observar de la clase libreoffice registra una fila por conversion y su memoria de `ultimo` no se poda.

Cierre de DEBT-PORTERO-OBSERVAR-LIBREOFFICE-CRECE-SIN-COTA-01. Mientras la ficha siga abierta `tests/conftest.py`
marca estos tests xfail (tests/known_failures.json).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tools import portero as po

G = po.GIB_KB
CLAUDE = "/user.slice/user-1000.slice/user@1000.service/app.slice/app-com.anthropic.Claude-1.scope"


def _conv(raiz: int) -> po.Arbol:
    return po.Arbol(raiz=raiz, clase="libreoffice", rss_kb=200_000, procesos=2, edad_s=1.0, cgroup=CLAUDE,
                    pids=(raiz,), inicio=100)


def _ciclos(tmp_path: Path, n: int) -> tuple[dict[Any, str], Path]:
    """n ciclos del demonio; en cada uno vive UNA conversion distinta y la anterior ya murio (un lote real: ~1 s cada una)."""
    ultimo: dict[Any, str] = {}
    fx = po.Efectos(log=tmp_path / "p.jsonl", cola=tmp_path / "cola", ejecutar=lambda a: (1, "prueba"),
                    cg_raiz=tmp_path / "cg", proc=tmp_path / "proc", modo="actuar")
    estado = po.Estado(0.0, "", 42 * G, 30 * G)
    for i in range(n):
        arboles = [_conv(10_000 + i)]
        po.aplica(po.decide(arboles, estado), arboles, estado, fx, ultimo)
    return ultimo, fx.log


@pytest.mark.unit
def test_ultimo_no_guarda_arboles_que_ya_no_existen(tmp_path: Path):
    ultimo, _ = _ciclos(tmp_path, 300)
    assert len(ultimo) <= 5, f"`ultimo` creció a {len(ultimo)} claves tras 300 conversiones de 1 s"


@pytest.mark.unit
def test_control_negativo_ultimo_si_deduplica_un_arbol_vivo(tmp_path: Path):
    """El instrumento de arriba puede decir 'no crece': un mismo arbol vivo no vuelve a registrar el mismo motivo."""
    ultimo: dict[Any, str] = {}
    fx = po.Efectos(log=tmp_path / "p.jsonl", cola=tmp_path / "cola", ejecutar=lambda a: (1, "prueba"),
                    cg_raiz=tmp_path / "cg", proc=tmp_path / "proc", modo="actuar")
    estado = po.Estado(0.0, "", 42 * G, 30 * G)
    arboles = [_conv(10_000)]
    for _ in range(50):
        po.aplica(po.decide(arboles, estado), arboles, estado, fx, ultimo)
    assert len(ultimo) <= 2
    assert sum(1 for _ in fx.log.read_text(encoding="utf-8").splitlines()) <= 2


@pytest.mark.unit
def test_el_log_del_portero_tiene_cota_de_tamano(tmp_path: Path):
    """Cierre de DEBT-PORTERO-LOG-SIN-ROTACION-CON-OBSERVAR-DE-LIBREOFFICE-01: portero.jsonl no rota y la clase
    libreoffice en observar escribe ~4.9 filas/s (3.4 kB/s) mientras corre un lote."""
    log = tmp_path / "portero.jsonl"
    ev = {"accion": "habria_admitir", "motivo": "turno libre y puerta abierta", "relleno": "x" * 200}
    for _ in range(80_000):  # ~18 MB: unas 5 h de un lote en observar
        po._registra(ev, log)
    assert log.stat().st_size <= 16 * 1024 * 1024
