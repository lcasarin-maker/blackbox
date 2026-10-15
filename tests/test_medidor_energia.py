"""tools/medidor_energia.py: lectura del enchufe y clasificacion tri-estado de la ventana de un corte (FEATURE-MEDIDOR-DE-ENERGIA-EXTERNO-01)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tools import interruptores
from tools import medidor_energia as m

SHELLY = {"tipo": "shelly", "url": "http://enchufe.local/"}
TASMOTA = {"tipo": "tasmota", "url": "http://enchufe.local"}


def _resp(obj: Any) -> Any:
    return lambda url: json.dumps(obj).encode()


def _roto(url: str) -> bytes:
    raise OSError("sin red")


def test_lee_shelly_y_tasmota_con_los_campos_documentados() -> None:
    r = m.lee(SHELLY, _resp({"apower": 38.5, "voltage": 121.0, "current": 0.32}))
    assert r == {"ok": True, "voltaje_v": 121.0, "potencia_w": 38.5, "corriente_a": 0.32}
    t = m.lee(TASMOTA, _resp({"StatusSNS": {"ENERGY": {"Power": 40, "Voltage": 119, "Current": 0.34}}}))
    assert t["ok"] is True and t["voltaje_v"] == 119.0 and t["potencia_w"] == 40.0


def test_lee_nunca_inventa_cifras() -> None:
    assert m.lee(SHELLY, _resp({"apower": 38.5}))["error"].startswith("NOT_COLLECTED")  # sin voltaje
    assert m.lee(SHELLY, _resp({"apower": True, "voltage": 120}))["ok"] is False  # un booleano no es potencia
    assert m.lee(SHELLY, _roto) == {"ok": False, "error": "OSError"}
    assert m.lee(SHELLY, lambda u: b"no es json")["ok"] is False
    assert m.lee({"tipo": "otro", "url": "x"}, _roto)["error"].startswith("NOT_COLLECTED")
    assert m.lee(SHELLY, _resp({"voltage": 120, "apower": 10}))["corriente_a"] is None  # la corriente es opcional


def test_paso_off_no_lee_y_on_anade_una_fila(tmp_path: Path) -> None:
    ruta = tmp_path / "externo" / "energia.jsonl"
    assert m.paso("off", SHELLY, ruta, _roto) is None and not ruta.exists()
    f = m.paso("observar", SHELLY, ruta, _resp({"apower": 30, "voltage": 120}), ahora=1000.0)
    assert f is not None and f["ok"] is True and f["epoch"] == 1000.0
    m.paso("observar", SHELLY, ruta, _roto, ahora=1001.0)  # un enchufe mudo se registra, no se descarta
    filas = [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines()]
    assert [x["ok"] for x in filas] == [True, False]


def _escribe(ruta: Path, filas: list[tuple[float, float, float]]) -> None:
    ruta.write_text("\n".join(json.dumps({"epoch": t, "ok": True, "voltaje_v": v, "potencia_w": w}) for t, v, w in filas) + "\n", encoding="utf-8")


def test_ventana_pared_cortada_voltaje_medido_bajo(tmp_path: Path) -> None:
    ruta = tmp_path / "e.jsonl"
    _escribe(ruta, [(990, 120, 40), (999, 121, 40), (1000.5, 12, 0), (1002, 0, 0)])
    r = m.ventana_de_corte(ruta, 1000, 255)
    assert r is not None and r["voltaje_perdido"] is True


def test_ventana_apagado_interno_pared_con_voltaje_y_consumo_cero(tmp_path: Path) -> None:
    ruta = tmp_path / "e.jsonl"
    _escribe(ruta, [(990, 120, 38), (999, 120, 39), (1001, 120, 0.3), (1002, 121, 0.3), (1003, 120, 0.2)])
    r = m.ventana_de_corte(ruta, 1000, 255)
    assert r is not None and r["voltaje_perdido"] is False


def test_ventana_no_concluyente_en_los_casos_dudosos(tmp_path: Path) -> None:
    ruta = tmp_path / "e.jsonl"
    assert m.ventana_de_corte(ruta, 1000, 255) is None  # sin archivo
    _escribe(ruta, [(100, 120, 40)])
    assert m.ventana_de_corte(ruta, 1000, 255) is None  # filas fuera de la ventana
    # el enchufe deja de responder: puede ser el Wi-Fi, NO es voltaje perdido
    ruta.write_text("\n".join(json.dumps(x) for x in [{"epoch": 999, "ok": True, "voltaje_v": 120, "potencia_w": 40}, {"epoch": 1001, "ok": False, "error": "OSError"}, {"epoch": 1002, "ok": False, "error": "OSError"}]) + "\n", encoding="utf-8")
    r = m.ventana_de_corte(ruta, 1000, 255)
    assert r is not None and r["voltaje_perdido"] is None
    # la ATOM ya estaba casi sin consumo antes del corte: no se afirma apagado interno
    _escribe(ruta, [(999, 120, 2), (1001, 120, 0.2), (1002, 120, 0.2)])
    r2 = m.ventana_de_corte(ruta, 1000, 255)
    assert r2 is not None and r2["voltaje_perdido"] is None


def test_ventana_ignora_lineas_corruptas(tmp_path: Path) -> None:
    ruta = tmp_path / "e.jsonl"
    ruta.write_text("{roto\n" + json.dumps({"epoch": 999, "ok": True, "voltaje_v": 120, "potencia_w": 40}) + "\n[1,2]\n", encoding="utf-8")
    r = m.ventana_de_corte(ruta, 1000, 255)
    assert r is not None and r["voltaje_perdido"] is None


def test_main_sin_config_sin_argumentos_y_con_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    assert m.main([]) == 2
    assert m.main(["--paso"]) == 1 and "medidor.json" in capsys.readouterr().err
    (tmp_path / "externo").mkdir()
    (tmp_path / "externo" / "medidor.json").write_text(json.dumps(SHELLY), encoding="utf-8")
    monkeypatch.setattr(m, "_abre", _resp({"apower": 30, "voltage": 120}))
    monkeypatch.setattr(m, "paso", lambda modo, cfg, ruta, abre=m._abre, ahora=None: {"modo": modo})  # no toca la red
    assert m.main(["--paso"]) == 0 and json.loads(capsys.readouterr().out.strip().splitlines()[-1]) == {"modo": interruptores.modo(m.NOMBRE)}


def test_abre_real_lee_una_url_local(tmp_path: Path) -> None:
    (tmp_path / "x.json").write_text("{}", encoding="utf-8")
    assert m._abre((tmp_path / "x.json").as_uri()) == b"{}"


def test_script_entrypoint_sale_con_el_codigo_de_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    import runpy

    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["medidor_energia.py", "--paso"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(Path(m.__file__)), run_name="__main__")
    assert exc.value.code == 1  # sin medidor.json: NOT_COLLECTED
    assert "NOT_COLLECTED" in capsys.readouterr().err
