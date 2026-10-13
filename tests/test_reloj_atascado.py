"""reloj_atascado: tres estados, nunca sano sin carga, y el inicio medido en el historial."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

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


def test_inicio_ignora_filas_sin_carga_o_sin_numero_y_archivo_ausente(tmp_path: Path) -> None:
    filas = [_f(96, 2400, ts="2026-10-12T22:00:00+00:00"), _f(10, 600, ts="2026-10-12T22:01:00+00:00"),
             {"ts": "2026-10-12T22:02:00+00:00", "gpu_util_pct": 96, "sm_clk_mhz": "n/a"},
             _f(96, 650, ts="2026-10-12T23:00:00+00:00")]
    ruta = tmp_path / "t.jsonl"
    ruta.write_text("\n".join(json.dumps(x) for x in filas) + "\n", encoding="utf-8")
    d = r.inicio(ruta)
    assert d is not None and d["primera_atascada"].startswith("2026-10-12T") and d["ultima_sana"] < d["primera_atascada"]
    # control negativo: la fila de baja carga (600 MHz) sola no cuenta como atascada
    ruta.write_text("\n".join(json.dumps(x) for x in filas[:2]) + "\n", encoding="utf-8")
    assert r.inicio(ruta) is None
    assert r.inicio(tmp_path / "no_existe.jsonl") is None


class _Tensor:
    def __matmul__(self, otro: object) -> "_Tensor":
        return self


def _torch_falso(n_sync: list[int]) -> types.ModuleType:
    mod = types.ModuleType("torch")
    setattr(mod, "float16", "fp16")
    setattr(mod, "randn", lambda *a, **k: _Tensor())
    setattr(mod, "cuda", types.SimpleNamespace(synchronize=lambda: n_sync.append(1)))
    return mod


def _prepara_prueba(monkeypatch: pytest.MonkeyPatch, salida: str) -> list[int]:
    n_sync: list[int] = []
    monkeypatch.setitem(sys.modules, "torch", _torch_falso(n_sync))
    reloj = [1000.0]

    def ahora() -> float:
        reloj[0] += 0.1
        return reloj[0]

    monkeypatch.setattr(r, "time", types.SimpleNamespace(time=ahora))
    monkeypatch.setattr(r, "subprocess", types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(stdout=salida + "\n")))
    return n_sync


def test_prueba_con_falsos_mide_tflops_y_veredicto_atascado(monkeypatch: pytest.MonkeyPatch) -> None:
    n_sync = _prepara_prueba(monkeypatch, "660, 12.5, 96, 0x0000000000000000")
    v = r.prueba(segundos=15)
    assert v["estado"] == "ATASCADO" and v["segundos"] == 15 and v["reloj_mediano_mhz"] == 660.0
    assert v["tflops"] > 0 and len(n_sync) > 10


def test_prueba_con_salida_malformada_es_indeterminado(monkeypatch: pytest.MonkeyPatch) -> None:
    _prepara_prueba(monkeypatch, "N/A")  # control negativo: sin filas validas jamas se afirma ATASCADO ni SANO
    v = r.prueba(segundos=15)
    assert v["estado"] == "INDETERMINADO" and v["motivo"].startswith("NOT_COLLECTED")


def _main_con(monkeypatch: pytest.MonkeyPatch, resultado: dict, capsys: pytest.CaptureFixture[str], argv: list[str]) -> tuple[int, dict]:
    monkeypatch.setattr(r, "prueba", lambda: resultado)
    monkeypatch.setattr(r, "inicio", lambda: {"ultima_sana": "a", "primera_atascada": "b"})
    codigo = r.main(argv)
    return codigo, json.loads(capsys.readouterr().out)


def test_main_prueba_codigos_de_salida(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    assert _main_con(monkeypatch, {"estado": "SANO"}, capsys, ["--prueba"])[0] == 0
    assert _main_con(monkeypatch, {"estado": "INDETERMINADO"}, capsys, ["--prueba"])[0] == 2
    codigo, salida = _main_con(monkeypatch, {"estado": "ATASCADO"}, capsys, ["--prueba"])
    assert codigo == 1 and salida["desde"]["primera_atascada"] == "b" and "remedio" in salida


def test_main_sano_no_agrega_desde_ni_remedio(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _, salida = _main_con(monkeypatch, {"estado": "SANO"}, capsys, ["--prueba"])
    assert "desde" not in salida and "remedio" not in salida


def test_main_pasiva_decide_sobre_la_cola(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(r.g, "lee_cola", lambda filas=60: [_f(96, 2400, 55)] * 20)
    monkeypatch.setattr(r, "prueba", lambda: pytest.fail("la pasiva no corre la prueba activa"))
    assert r.main([]) == 0
    assert json.loads(capsys.readouterr().out)["estado"] == "SANO"


def test_main_arranque_registra_con_el_modo_del_interruptor(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    llamadas: list[tuple[str, dict, str]] = []
    monkeypatch.setattr(r.interruptores, "modo", lambda nombre: "observar")
    monkeypatch.setattr(r, "arranque", lambda modo, res, boot: llamadas.append((modo, res, boot)))
    codigo, _ = _main_con(monkeypatch, {"estado": "SANO"}, capsys, ["--arranque"])
    assert codigo == 0 and len(llamadas) == 1 and llamadas[0][0] == "observar" and llamadas[0][2]
    # control negativo: --prueba sola no registra
    _main_con(monkeypatch, {"estado": "SANO"}, capsys, ["--prueba"])
    assert len(llamadas) == 1
