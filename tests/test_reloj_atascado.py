"""reloj_atascado: tres estados, nunca sano sin carga, y el inicio medido en el historial."""

from __future__ import annotations

import json
from pathlib import Path

from tools import reloj_atascado as r


def _f(util: float, clk: float, w: float = 15.0, thr: object = "0x0000000000000000", ts: str = "2026-10-12T22:00:00+00:00") -> dict:
    return {"ts": ts, "gpu_util_pct": util, "sm_clk_mhz": clk, "gpu_power_w": w, "throttle": thr}


def test_carga_con_reloj_bajo_y_sin_throttle_es_atascado() -> None:
    d = r.decide([_f(96, 660)] * 20)
    assert d["estado"] == "ATASCADO" and d["sin_throttle"] is True


def test_carga_con_reloj_alto_es_sano() -> None:
    assert r.decide([_f(96, 2400, 55)] * 20)["estado"] == "SANO"


def test_reloj_bajo_con_throttle_activo_no_es_atascado() -> None:
    d = r.decide([_f(96, 660, thr="0x0000000000000004")] * 20)
    assert d["estado"] == "INDETERMINADO"  # un throttle termico real no es el bug de reloj atascado


def test_sin_carga_no_se_afirma_sano_ni_atascado() -> None:
    assert r.decide([_f(5, 656, 6.0)] * 50)["estado"] == "INDETERMINADO"


def test_pocas_muestras_con_carga_es_indeterminado() -> None:
    assert r.decide([_f(96, 660)] * 5)["estado"] == "INDETERMINADO"


def test_el_minimo_de_muestras_es_parametro() -> None:
    assert r.decide([_f(96, 660)] * 8, minimas=8)["estado"] == "ATASCADO"


def test_inicio_encuentra_el_paso_de_sano_a_atascado(tmp_path: Path) -> None:
    filas = [_f(96, 2400, 55, ts="2026-10-12T22:00:00+00:00"), _f(96, 2300, 50, ts="2026-10-12T22:05:00+00:00"),
             _f(96, 670, 9, ts="2026-10-12T23:17:16+00:00"), _f(96, 660, 9, ts="2026-10-12T23:20:00+00:00")]
    ruta = tmp_path / "t.jsonl"
    ruta.write_text("\n".join(json.dumps(x) for x in filas) + "\nbasura\n", encoding="utf-8")
    d = r.inicio(ruta)
    assert d is not None and d["primera_atascada"].startswith("2026-10-12T") and d["ultima_sana"] < d["primera_atascada"]


def test_inicio_sin_paso_devuelve_none(tmp_path: Path) -> None:
    ruta = tmp_path / "t.jsonl"
    ruta.write_text(json.dumps(_f(96, 2400, 55)) + "\n", encoding="utf-8")
    assert r.inicio(ruta) is None


def test_arranque_off_no_registra_nada(tmp_path: Path) -> None:
    avisos: list[object] = []
    assert r.arranque("off", {"estado": "ATASCADO"}, "b", tmp_path, avisa=avisos.append) is None
    assert avisos == [] and not (tmp_path / "reloj_arranque.jsonl").exists()


def test_arranque_observar_sano_registra_y_no_avisa(tmp_path: Path) -> None:
    avisos: list[object] = []
    ev = r.arranque("observar", {"estado": "SANO", "reloj_mediano_mhz": 2080.0, "tflops": 77.4}, "b1", tmp_path, avisa=avisos.append)
    assert ev is not None and ev["estado"] == "SANO" and "habria_actuado" not in ev and avisos == []
    assert (tmp_path / "reloj_arranque.jsonl").exists()


def test_arranque_atascado_avisa_con_las_cifras(tmp_path: Path) -> None:
    avisos: list[object] = []
    ev = r.arranque("observar", {"estado": "ATASCADO", "reloj_mediano_mhz": 663.0, "tflops": 23.5}, "b2", tmp_path, avisa=avisos.append)
    assert ev is not None and ev["habria_actuado"] is True and len(avisos) == 1
    aviso = avisos[0]
    assert getattr(aviso, "urgencia") == "critical" and "663" in getattr(aviso, "cuerpo")
