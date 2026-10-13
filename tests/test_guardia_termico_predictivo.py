"""guardia_termico_predictivo: decision pura, interruptor off/observar/actuar y repasada del historial."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
