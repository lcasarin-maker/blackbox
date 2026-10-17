"""La prueba del contenido pendiente puede salir roja: se corre contra (a) el contenido desplegado hoy (el ANTES),
(b) el pendiente sin 'node' -- las dos deben FALLAR -- y (c) el pendiente tal cual, que debe PASAR.

Uso, desde la raiz del repo: python3 tasks/evidence/DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01/rojo_y_verde.py
"""

from __future__ import annotations

import importlib
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]


def main() -> int:
    sys.path.insert(0, str(RAIZ))
    tp = importlib.import_module("tests.test_procesos_protegidos")
    prueba = tp.test_earlyoom_pendiente_cubre_toda_la_lista_y_no_evita_lo_no_protegido
    pendiente = tp.EARLYOOM_PENDIENTE
    texto = pendiente.read_text(encoding="utf-8")
    sin_node = Path(tempfile.mkdtemp()) / "etc_default_earlyoom"
    sin_node.write_text(texto.replace("^(node|", "^("), encoding="utf-8")
    assert sin_node.read_text(encoding="utf-8") != texto, "la mutacion no cambio nada: control vacio"
    veredictos = []
    for etiqueta, ruta in (("ANTES: contenido desplegado (adopted/system-config)", tp.EARLYOOM),
                           ("pendiente SIN 'node'", sin_node), ("pendiente tal cual", pendiente)):
        setattr(tp, "EARLYOOM_PENDIENTE", ruta)
        try:
            prueba()
            veredicto = "PASA"
        except AssertionError:
            veredicto = "FALLA"
        veredictos.append(veredicto)
        print(f"{etiqueta}: {veredicto}; faltan_en_earlyoom = {sorted(tp.faltan_en_earlyoom(ruta))}")
    setattr(tp, "EARLYOOM_PENDIENTE", pendiente)
    return 0 if veredictos == ["FALLA", "FALLA", "PASA"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
