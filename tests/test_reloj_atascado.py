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


def _prepara_prueba(monkeypatch: pytest.MonkeyPatch, salida: str, ocupantes: list[object] | None = None) -> list[int]:
    """`ocupantes`: lo que devuelve cada consulta de procesos de computo, en orden (antes, al final); por defecto GPU libre."""
    n_sync: list[int] = []
    respuestas = list(ocupantes) if ocupantes is not None else [[], []]
    monkeypatch.setattr(r, "ocupantes", lambda *a, **k: respuestas.pop(0))
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


# --- FEATURE-RELOJ-ATASCADO-SEGUNDO-EJE-TFLOPS-Y-GUARDA-DE-OCUPACION-01: segundo eje TFLOP/s ---


def test_tflops_bajo_con_reloj_en_banda_y_sin_throttle_es_atascado() -> None:
    d = r.decide([_f(96, 1200)] * 20, tflops=40.0)
    assert d["estado"] == "ATASCADO" and d["tflops"] == 40.0
    assert d["umbral_tflops"] == r.UMBRAL_TFLOPS and "PROVISIONAL" in d["umbral_tflops_estado"]  # se imprime provisional


def test_tflops_control_negativo_mismo_reloj_con_tflops_sano_no_es_atascado() -> None:
    d = r.decide([_f(96, 1200)] * 20, tflops=90.0)
    assert d["estado"] == "INDETERMINADO"


def test_tflops_frontera_del_umbral_es_estricta() -> None:
    assert r.decide([_f(96, 1200)] * 20, tflops=r.UMBRAL_TFLOPS)["estado"] == "INDETERMINADO"
    assert r.decide([_f(96, 1200)] * 20, tflops=r.UMBRAL_TFLOPS - 0.1)["estado"] == "ATASCADO"


def test_tflops_bajo_con_throttle_o_sin_carga_no_es_atascado() -> None:
    assert r.decide([_f(96, 1200, thr="0x0000000000000004")] * 20, tflops=40.0)["estado"] == "INDETERMINADO"
    d = r.decide([_f(5, 1200)] * 20, tflops=10.0)  # sin carga: el segundo eje no rescata la falta de muestras
    assert d["estado"] == "INDETERMINADO" and d["motivo"].startswith("NOT_COLLECTED")


def test_tflops_ausente_deja_los_tres_estados_de_hoy() -> None:
    assert r.decide([_f(96, 660)] * 20)["estado"] == "ATASCADO"
    assert r.decide([_f(96, 2400, 55)] * 20)["estado"] == "SANO"
    d = r.decide([_f(96, 1200)] * 20)
    assert d["estado"] == "INDETERMINADO" and "umbral_tflops" not in d


def test_tflops_la_prueba_entrega_sus_tflops_a_decide(monkeypatch: pytest.MonkeyPatch) -> None:
    _prepara_prueba(monkeypatch, "1200, 20.0, 96, 0x0000000000000000")
    v = r.prueba(segundos=15)
    assert 0 < v["tflops"] < r.UMBRAL_TFLOPS and v["estado"] == "ATASCADO" and v["reloj_mediano_mhz"] == 1200.0
    # control negativo: las mismas filas con un umbral por debajo de lo medido ya no son ATASCADO
    monkeypatch.setattr(r, "UMBRAL_TFLOPS", 0.01)
    _prepara_prueba(monkeypatch, "1200, 20.0, 96, 0x0000000000000000")
    assert r.prueba(segundos=15)["estado"] == "INDETERMINADO"


def test_main_atascado_remedio_alineado_con_el_hilo_387029(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _, salida = _main_con(monkeypatch, {"estado": "ATASCADO"}, capsys, ["--prueba"])
    remedio = salida["remedio"]
    assert "adaptador" in remedio and "5 min" in remedio and "USB" in remedio and "387029" in remedio
    assert "pared -> adaptador -> equipo" in remedio


# --- FEATURE-RELOJ-PRUEBA-GUARDA-GPU-OCUPADA-01: guarda de GPU ocupada ---


def _runner(rc: int, salida: str, llamadas: list[list[str]] | None = None) -> r.vpg.Runner:
    def corre(argv: list[str]) -> tuple[int, str]:
        if llamadas is not None:
            llamadas.append(argv)
        return rc, salida

    return corre


def test_ocupada_consulta_reutiliza_apps_cmd_y_excluye_el_pid_propio(tmp_path: Path) -> None:
    (tmp_path / "4242").mkdir()
    (tmp_path / "4242" / "comm").write_text("VLLM::EngineCor\n", encoding="utf-8")
    llamadas: list[list[str]] = []
    o = r.ocupantes(runner=_runner(0, "4242, 34669\n777, 170\n", llamadas), propio=777, proc=tmp_path)
    assert llamadas == [r.vpg._APPS_CMD]
    assert o == [{"pid": 4242, "nombre": "VLLM::EngineCor", "mib": 34669}]
    # control negativo: solo el propio proceso en la lista es GPU libre
    assert r.ocupantes(runner=_runner(0, "777, 170\n"), propio=777, proc=tmp_path) == []
    assert r.ocupantes(runner=_runner(0, ""), propio=777, proc=tmp_path) == []


def test_ocupada_consulta_que_falla_o_ilegible_es_none_nunca_libre(tmp_path: Path) -> None:
    assert r.ocupantes(runner=_runner(127, "cannot run nvidia-smi"), propio=1, proc=tmp_path) is None
    assert r.ocupantes(runner=_runner(0, "4242, [N/A]\n"), propio=1, proc=tmp_path) is None
    # pid sin /proc legible: se lista igual, con el nombre como None (no se descarta)
    assert r.ocupantes(runner=_runner(0, "4242, 5\n"), propio=1, proc=tmp_path) == [{"pid": 4242, "nombre": None, "mib": 5}]


def test_ocupada_antes_de_la_prueba_da_indeterminado_sin_cargar_la_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    ajeno = [{"pid": 4242, "nombre": "VLLM::EngineCor", "mib": 34669}]
    n_sync = _prepara_prueba(monkeypatch, "660, 12.5, 96, 0x0000000000000000", ocupantes=[ajeno])
    v = r.prueba(segundos=15)
    assert v["estado"] == "INDETERMINADO" and v["motivo"].startswith("GPU_OCUPADA") and "4242" in v["motivo"]
    assert v["ocupantes"] == ajeno and n_sync == []  # ni un matmul sobre una GPU compartida


def test_ocupada_durante_la_prueba_anula_el_veredicto(monkeypatch: pytest.MonkeyPatch) -> None:
    ajeno = [{"pid": 4242, "nombre": "python3", "mib": 900}]
    _prepara_prueba(monkeypatch, "660, 12.5, 96, 0x0000000000000000", ocupantes=[[], ajeno])
    v = r.prueba(segundos=15)
    assert v["estado"] == "INDETERMINADO" and v["motivo"].startswith("GPU_OCUPADA") and v["ocupantes"] == ajeno
    assert v["reloj_mediano_mhz"] == 660.0 and v["tflops"] > 0  # las cifras se conservan, el veredicto no


def test_ocupada_control_negativo_gpu_libre_da_el_veredicto_de_siempre(monkeypatch: pytest.MonkeyPatch) -> None:
    _prepara_prueba(monkeypatch, "660, 12.5, 96, 0x0000000000000000")
    v = r.prueba(segundos=15)
    assert v["estado"] == "ATASCADO" and "ocupantes" not in v
    monkeypatch.setattr(r, "UMBRAL_TFLOPS", 0.01)  # el SANO de hoy, con TFLOP/s sobre el umbral
    _prepara_prueba(monkeypatch, "2080, 67.0, 96, 0x0000000000000000")
    assert r.prueba(segundos=15)["estado"] == "SANO"


def test_ocupada_consulta_que_falla_es_not_collected_sin_cargar(monkeypatch: pytest.MonkeyPatch) -> None:
    n_sync = _prepara_prueba(monkeypatch, "660, 12.5, 96, 0x0000000000000000", ocupantes=[None])
    v = r.prueba(segundos=15)
    assert v["estado"] == "INDETERMINADO" and v["motivo"].startswith("NOT_COLLECTED") and n_sync == []
    # y si falla al final, tampoco se afirma nada
    _prepara_prueba(monkeypatch, "660, 12.5, 96, 0x0000000000000000", ocupantes=[[], None])
    v = r.prueba(segundos=15)
    assert v["estado"] == "INDETERMINADO" and v["motivo"].startswith("NOT_COLLECTED")


def test_ocupada_en_el_arranque_registra_sin_avisar(tmp_path: Path) -> None:
    avisos: list[object] = []
    res = {"estado": "INDETERMINADO", "motivo": "GPU_OCUPADA: pid 4242", "ocupantes": [{"pid": 4242, "nombre": "x", "mib": 1}]}
    ev = r.arranque("observar", res, "b3", tmp_path, avisa=avisos.append)
    assert ev is not None and ev["motivo"].startswith("GPU_OCUPADA") and ev["ocupantes"][0]["pid"] == 4242 and avisos == []
    fila = json.loads((tmp_path / "reloj_arranque.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert fila["motivo"].startswith("GPU_OCUPADA")


# --- FEATURE-RELOJ-VEREDICTO-BAJO-NO-ATASCADO-01: motivos separados dentro de INDETERMINADO ---


def test_bajo_no_atascado_throttle_activo_lista_las_razones() -> None:
    d = r.decide([_f(96, 1200, thr="0x0000000000000004")] * 20, tflops=40.0)
    assert d["estado"] == "INDETERMINADO" and d["motivo"].startswith("THROTTLE_ACTIVO") and "0x0000000000000004" in d["motivo"]
    d = r.decide([_f(96, 660, thr="0x0000000000000040")] * 20)
    assert d["estado"] == "INDETERMINADO" and d["motivo"].startswith("THROTTLE_ACTIVO") and "0x0000000000000040" in d["motivo"]


def test_bajo_no_atascado_reloj_alto_con_tflops_bajo_no_es_atascado() -> None:
    d = r.decide([_f(96, 2000)] * 20, tflops=40.0)
    assert d["estado"] == "INDETERMINADO" and d["motivo"].startswith("RELOJ_ALTO_RENDIMIENTO_BAJO")
    d = r.decide([_f(96, 2000, thr="0x0000000000000004")] * 20, tflops=40.0)
    assert d["estado"] == "INDETERMINADO" and d["motivo"].startswith("THROTTLE_ACTIVO")


def test_bajo_no_atascado_reloj_en_banda_sin_throttle_da_la_mediana() -> None:
    for tflops in (None, 90.0):
        d = r.decide([_f(96, 1200)] * 20, tflops=tflops)
        assert d["estado"] == "INDETERMINADO" and d["motivo"].startswith("RELOJ_EN_BANDA") and "1200" in d["motivo"]


def test_bajo_no_atascado_control_negativo_las_filas_de_hoy_no_cambian() -> None:
    for tflops in (None, 23.5):
        d = r.decide([_f(96, 660)] * 20, tflops=tflops)
        assert d["estado"] == "ATASCADO" and "motivo" not in d
    for tflops in (None, 77.4):
        d = r.decide([_f(96, 2080, 67)] * 20, tflops=tflops)
        assert d["estado"] == "SANO" and "motivo" not in d
    assert r.decide([_f(96, 2400, 55, thr="0x0000000000000004")] * 20)["estado"] == "SANO"  # sin TFLOP/s, como hoy
