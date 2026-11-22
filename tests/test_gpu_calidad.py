import importlib.util
from pathlib import Path
_spec = importlib.util.spec_from_file_location("muestreo_calidad", Path(__file__).resolve().parents[1] / "tools/muestreo_1s.py")
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)
CalidadGPU = _m.CalidadGPU


def test_entrega_identica_renueva_entrega_y_no_contenido():
    reloj = [10.0]
    c = CalidadGPU(lambda: reloj[0])
    assert c.observar({"gpu_util_pct": 0})["comparacion"] == "inicio"
    reloj[0] = 14.0
    misma = c.observar({"gpu_util_pct": 0})
    assert misma["edad_entrega_s"] == 0 and misma["edad_contenido_s"] == 4
    reloj[0] = 16.0
    error = c.observar(None, estado="error")
    assert error["estado"] == "error" and error["edad_entrega_s"] == 2


def test_reloj_regresivo_invalida_anclas():
    reloj = [3.0]
    c = CalidadGPU(lambda: reloj[0])
    c.observar("x")
    reloj[0] = 2.0
    assert c.observar("x")["estado"] == "reloj_invalido"
