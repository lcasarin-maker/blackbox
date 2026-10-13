"""guardia_termico_predictivo: decision pura, interruptor off/observar/actuar y repasada del historial."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tools import guardia_termico_predictivo as g


def _serie(temps: list[float], paso_s: float = 5.0) -> list[tuple[float, float]]:
    return [(i * paso_s, t) for i, t in enumerate(temps)]


def _fila(ts: datetime, zona: float, gpu_w: float = 10.0, boot: str = "b" * 8) -> dict:
    return {"ts": ts.isoformat(), "boot_id": boot, "gpu_power_w": gpu_w, "zonas": [{"zona": "z0", "temp_c": zona}]}


def test_plana_no_dispara() -> None:
    assert g.decide(_serie([80.0] * 8))["dispara"] is False


def test_subida_rapida_hacia_el_tope_dispara_por_prediccion() -> None:
    d = g.decide(_serie([90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 95.5, 96.0]))
    assert d["dispara"] is True and d["regla"] == "prediccion>=tope"


def test_pocas_muestras_se_declara_sin_dato() -> None:
    assert g.decide(_serie([90.0, 95.0]))["motivo"].startswith("NOT_COLLECTED")


def test_causa_distingue_gpu_ociosa() -> None:
    sube = _serie([90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 95.5, 96.0])
    assert g.decide(sube, gpu_w=8.0)["causa_probable"].startswith("cpu_o_soc")
    assert g.decide(sube, gpu_w=60.0)["causa_probable"] == "gpu"


def test_acumulacion_lenta_dispara_y_la_corta_no() -> None:
    lenta = _serie([60.0 + 0.1 * i for i in range(g.ACUM_VENTANA)])  # 1.2 C/min durante 10 min hasta ~72: aun fria
    assert g.decide_acumulacion(lenta)["dispara"] is False  # zona < 85
    caliente = _serie([75.0 + 0.1 * i for i in range(g.ACUM_VENTANA)])  # termina en ~87 C subiendo 1.2 C/min
    assert g.decide_acumulacion(caliente)["dispara"] is True
    assert g.decide(caliente[-g.VENTANA :])["dispara"] is False  # la regla corta no la ve


def test_paso_off_no_registra_y_observar_si(tmp_path: Path) -> None:
    ahora = datetime.now(timezone.utc)
    filas = [_fila(ahora - timedelta(seconds=5 * (7 - i)), 90.0 + i) for i in range(8)]
    assert g.paso("off", filas, directorio=tmp_path, ahora=ahora.timestamp()) is None
    ev = g.paso("observar", filas, carga=3.0, directorio=tmp_path, ahora=ahora.timestamp())
    assert ev is not None and ev["habria_actuado"] is True and "accion" not in ev
    assert (tmp_path / f"{g.NOMBRE}.jsonl").exists()
    ev2 = g.paso("actuar", filas, directorio=tmp_path, ahora=ahora.timestamp())
    assert ev2 is not None and ev2["accion"].startswith("UNSUPPORTED")


def test_muestra_vieja_no_decide(tmp_path: Path) -> None:
    ahora = datetime.now(timezone.utc)
    viejas = [_fila(ahora - timedelta(seconds=600 + 5 * (7 - i)), 90.0 + i) for i in range(8)]
    assert g.paso("observar", viejas, directorio=tmp_path, ahora=ahora.timestamp()) is None


def test_repasa_cuenta_episodios_por_arranque(tmp_path: Path) -> None:
    base = datetime(2026, 10, 12, tzinfo=timezone.utc)
    ruta = tmp_path / "t.jsonl"
    filas = [_fila(base + timedelta(seconds=5 * i), 70.0 if i < 400 else 70.0 + (i - 400) * 1.5) for i in range(430)]
    ruta.write_text("\n".join(json.dumps(f) for f in filas) + "\nbasura\n", encoding="utf-8")
    r = g.repasa(ruta, min_muestras=300)
    assert list(r) == ["bbbbbbbb"]
    assert r["bbbbbbbb"]["corta"]["episodios"] >= 1
    assert r["bbbbbbbb"]["corta"]["ultimo_disparo_antes_del_fin_s"] is not None


def test_pendiente_y_decide_sin_dato_suficiente() -> None:
    assert g.pendiente_c_min(_serie([80.0, 81.0, 82.0])) is None  # menos de 4 puntos
    mismo_t = [(10.0, 80.0 + i) for i in range(5)]
    assert g.pendiente_c_min(mismo_t) is None  # sin variacion de tiempo
    assert g.decide(mismo_t)["motivo"] == "NOT_COLLECTED: pendiente sin tiempo"
    assert g.pendiente_c_min(_serie([80.0, 81.0, 82.0, 83.0])) == 12.0  # control positivo: 1 C / 5 s


def test_zona_alta_y_subiendo_dispara_sin_llegar_al_tope() -> None:
    d = g.decide(_serie([93.22, 93.48, 93.74, 94.0]))  # 3.1 C/min, prediccion 95.6 < 96
    assert d["dispara"] is True and d["regla"] == "alta_y_subiendo"
    # control negativo: misma zona alta pero estable no dispara
    assert g.decide(_serie([94.5] * 4))["dispara"] is False


def test_acumulacion_sin_dato_suficiente() -> None:
    assert g.decide_acumulacion(_serie([90.0] * 10))["motivo"].startswith("NOT_COLLECTED")
    mismo_t = [(0.0, 90.0)] * g.ACUM_VENTANA
    assert g.decide_acumulacion(mismo_t)["motivo"] == "NOT_COLLECTED: pendiente sin tiempo"


def test_serie_descarta_ts_invalidos_y_filas_sin_zona() -> None:
    ahora = datetime(2026, 10, 12, tzinfo=timezone.utc)
    filas = [_fila(ahora, 80.0), {"ts": "no-es-fecha", "zonas": [{"temp_c": 90.0}]}, {"zonas": [{"temp_c": 90.0}]},
             {"ts": ahora.isoformat(), "zonas": []}]
    assert g._serie(filas) == [(ahora.timestamp(), 80.0)]


def test_lee_cola_toma_las_ultimas_filas_legibles(tmp_path: Path) -> None:
    ruta = tmp_path / "t.jsonl"
    lineas = [json.dumps({"i": i, "zonas": [{"temp_c": 50.0 + i}]}) for i in range(10)]
    lineas.insert(3, "basura{")
    lineas.append(json.dumps({"i": 99, "zonas": []}))  # sin temperatura: se descarta
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    assert [f["i"] for f in g.lee_cola(ruta, filas=3)] == [7, 8, 9]
    assert g.lee_cola(tmp_path / "no_existe.jsonl") == []  # control negativo: archivo ausente


def test_lee_carga_lee_el_primer_campo_y_falla_a_none(tmp_path: Path) -> None:
    ruta = tmp_path / "loadavg"
    ruta.write_text("0.52 0.40 0.30 1/200 999\n", encoding="utf-8")
    assert g.lee_carga(ruta) == 0.52
    ruta.write_text("x y\n", encoding="utf-8")
    assert g.lee_carga(ruta) is None
    ruta.write_text("", encoding="utf-8")
    assert g.lee_carga(ruta) is None
    assert g.lee_carga(tmp_path / "no_existe") is None


def test_paso_fresco_sin_disparo_no_registra(tmp_path: Path) -> None:
    ahora = datetime.now(timezone.utc)
    planas = [_fila(ahora - timedelta(seconds=5 * (7 - i)), 60.0) for i in range(8)]
    assert g.paso("observar", planas, directorio=tmp_path, ahora=ahora.timestamp()) is None
    assert not (tmp_path / f"{g.NOMBRE}.jsonl").exists()


def test_paso_sin_filas_no_decide(tmp_path: Path) -> None:
    assert g.paso("observar", [], directorio=tmp_path, ahora=0.0) is None


def test_repasa_omite_arranques_con_pocas_muestras(tmp_path: Path) -> None:
    base = datetime(2026, 10, 12, tzinfo=timezone.utc)
    ruta = tmp_path / "t.jsonl"
    ruta.write_text("\n".join(json.dumps(_fila(base + timedelta(seconds=5 * i), 70.0)) for i in range(50)) + "\n", encoding="utf-8")
    assert g.repasa(ruta, min_muestras=300) == {}
    plano = g.repasa(ruta, min_muestras=40)["bbbbbbbb"]  # control positivo: con el minimo bajo si aparece, sin disparos
    assert plano["corta"]["episodios"] == 0 and plano["corta"]["ultimo_disparo_antes_del_fin_s"] is None


def test_main_con_repasa_imprime_el_informe_y_regresa(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(g, "repasa", lambda: {"bbbbbbbb": {"muestras": 3}})
    monkeypatch.setattr(sys, "argv", ["guardia", "--repasa"])
    assert g.main() is None
    assert json.loads(capsys.readouterr().out) == {"bbbbbbbb": {"muestras": 3}}
