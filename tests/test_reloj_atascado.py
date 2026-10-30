"""reloj_atascado: tres estados, nunca sano sin carga, y el inicio medido en el historial."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import pytest
from test_bb_root_manifest import _forense  # reuso: arranque-forense sellado con las rutas de root sustituidas

from tools import bb_root_run as rr
from tools import incident_report
from tools import reloj_atascado as r

_CAPTURA_REAL = getattr(r, "captura_incidente", None)  # getattr: contra un modulo sin captura falla cada prueba, no la recoleccion


@pytest.fixture(autouse=True)
def _sin_captura_real(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hermetico: ningun ATASCADO de estas pruebas pide root ni lanza unidades de verdad. Las pruebas `captura_incidente`
    quitan la variable y entregan rutas y un `ejecuta` falso."""
    monkeypatch.setenv("BB_RELOJ_CAPTURA", "off")


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
    if "BB_ARRANQUE_JSONL" not in os.environ:  # hermetico: nunca la fila real de /var/lib/blackbox
        monkeypatch.setenv("BB_ARRANQUE_JSONL", "/nonexistent-bb-test/arranque.jsonl")
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


def test_ocupada_antes_de_la_prueba_carga_igual_y_juzga_por_reloj(monkeypatch: pytest.MonkeyPatch) -> None:
    # Sustituye al test de FEATURE-RELOJ-PRUEBA-GUARDA-GPU-OCUPADA-01 que exigia NO cargar con ajenos (n_sync == []): ese
    # diseno dejo ciego el arranque del 2026-10-26 y DEBT-RELOJ-ARRANQUE-GPU-OCUPADA-POR-EL-MOTOR-01 lo invierte.
    ajeno = [{"pid": 4242, "nombre": "VLLM::EngineCor", "mib": 34669}]
    n_sync = _prepara_prueba(monkeypatch, "660, 12.5, 96, 0x0000000000000000", ocupantes=[ajeno, ajeno])
    v = r.prueba(segundos=15)
    assert v["estado"] == "ATASCADO" and v["ocupantes"] == ajeno and v["tflops_valido"] is False and len(n_sync) > 10
    assert "GPU_OCUPADA" not in str(v.get("motivo")) and "4242" in v["tflops_motivo"]


def test_ocupada_durante_la_prueba_invalida_los_tflops_no_el_reloj(monkeypatch: pytest.MonkeyPatch) -> None:
    ajeno = [{"pid": 4242, "nombre": "python3", "mib": 900}]
    _prepara_prueba(monkeypatch, "660, 12.5, 96, 0x0000000000000000", ocupantes=[[], ajeno])
    v = r.prueba(segundos=15)
    assert v["estado"] == "ATASCADO" and v["ocupantes"] == ajeno and v["tflops_valido"] is False
    assert v["reloj_mediano_mhz"] == 660.0 and v["tflops"] > 0  # las cifras se conservan; los TFLOP/s no cuentan


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


# --- FEATURE-RELOJ-CAPTURA-PD-FIRMWARE-Y-TRANSICION-01: firmware por arranque y episodio cerrado ---
DESCUBRIMIENTO = Path(__file__).resolve().parent.parent / "tasks/evidence/FEATURE-RELOJ-CAPTURA-PD-FIRMWARE-Y-TRANSICION-01/descubrimiento.txt"
# La salida literal de `dmidecode -t 45` de esta unidad (2026-10-26) tal como quedo en la evidencia; no se inventa otra.
T45_REAL = DESCUBRIMIENTO.read_text(encoding="utf-8").split("--- dmidecode 45\n", 1)[1].split("--- esrt", 1)[0]
BIOS_REAL = ("# dmidecode 3.5\nHandle 0x0000, DMI type 0, 26 bytes\nBIOS Information\n"
             "\tVendor: American Megatrends International, LLC.\n\tVersion: 5.36_0ACUM08\n\tBIOS Revision: 5.36\n")
# Fila real de /var/lib/blackbox/pstore/arranque.jsonl (2026-10-25), anterior a esta ficha: solo el nombre de la fuente.
FILA_VIEJA = '{"ts":"2026-10-25T05:55:32Z","boot_id":"463297c1-9c29-415d-b9a8-3315c8ffe956","pstore_archivos":0,"bert":"ausente","firmware":"bios+t45"}'
PD0, PD1, EC, BIOS = "PD0 FW1: 5.22, FW2: 5.0", "PD1 FW1: 5.22, FW2: 5.0", "3.5.11", "5.36_0ACUM08"


def _dmidecode_falso(d: Path, t45: str | None, bios: str | None) -> Path:
    """Un `dmidecode` en el PATH: imprime el texto dado por tipo, o sale 1 si es None (un dmidecode que falla)."""
    d.mkdir()
    lineas = ["#!/bin/sh"]
    for tipo, texto in (("45", t45), ("bios", bios)):
        if texto is None:
            lineas.append(f'if [ "$2" = {tipo} ]; then exit 1; fi')
        else:
            (d / f"{tipo}.txt").write_text(texto, encoding="utf-8")
            lineas.append(f'if [ "$2" = {tipo} ]; then cat "{d / (tipo + ".txt")}"; fi')
    (d / "dmidecode").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    (d / "dmidecode").chmod(0o755)
    return d


def _forense_con(tmp_path: Path, t45: str | None, bios: str | None = BIOS_REAL, copias_viejas: bool = False) -> tuple[Path, dict]:
    """Corre arranque-forense (rutas sustituidas, sin root) con un dmidecode falso; devuelve base y la ultima fila."""
    s, base, _ = _forense(tmp_path)
    if copias_viejas:  # lo que dejo un arranque anterior con valores
        base.mkdir()
        base.chmod(0o755)
        (base / "dmidecode-t45.txt").write_text(T45_REAL, encoding="utf-8")
        (base / "dmidecode-bios.txt").write_text(BIOS_REAL, encoding="utf-8")
    stub = _dmidecode_falso(tmp_path / "bin", t45, bios)
    p = subprocess.run(["/bin/bash", str(s)], env={"PATH": f"{stub}:{rr.PATH_FIJO}", "LC_ALL": "C"}, capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    return base, json.loads((base / "pstore" / "arranque.jsonl").read_text(encoding="utf-8").splitlines()[-1])


def test_pd_firmware_arranque_forense_anade_los_valores_a_la_fila(tmp_path: Path) -> None:
    base, fila = _forense_con(tmp_path, T45_REAL)
    assert (fila["pd0"], fila["pd1"], fila["ec"], fila["bios"]) == (PD0, PD1, EC, BIOS)
    assert fila["firmware"] == "bios+t45" and fila["pstore_archivos"] == 0  # los campos de antes, iguales
    # los consumidores de siempre siguen leyendo: bin/bb busca la fila por boot_id con esta regex y bb incident lee la copia
    assert re.search(rf'"boot_id": ?"{fila["boot_id"]}"', (base / "pstore" / "arranque.jsonl").read_text(encoding="utf-8"))
    assert "PD Firmware=PD0 FW1: 5.22, FW2: 5.0" in incident_report.firmware_recogido(str(base))


def test_pd_firmware_control_negativo_dmidecode_que_falla_no_hereda_la_copia_de_otro_arranque(tmp_path: Path) -> None:
    base, fila = _forense_con(tmp_path, None, None, copias_viejas=True)
    assert (base / "dmidecode-t45.txt").read_text(encoding="utf-8") == T45_REAL  # la copia vieja sigue ahi...
    assert fila["pd0"] == fila["pd1"] == fila["ec"] == "NOT_COLLECTED: dmidecode -t 45 fallo"  # ...y no se atribuye a este
    assert fila["bios"] == "NOT_COLLECTED: dmidecode -t bios fallo" and fila["firmware"] == "NOT_COLLECTED"


def test_pd_firmware_control_negativo_componente_ausente_es_not_collected_nunca_vacio(tmp_path: Path) -> None:
    sin_pd = re.sub(r"Firmware Component Name: PD Firmware", "Firmware Component Name: OTRO", T45_REAL)
    assert sin_pd != T45_REAL  # la sustitucion casa: prueba no vacia
    _, fila = _forense_con(tmp_path, sin_pd, "# dmidecode 3.5\n# No SMBIOS nor DMI entry point found, sorry.\n")
    assert fila["pd0"] == "NOT_COLLECTED: sin PD0 en dmidecode -t 45" and fila["pd1"] == "NOT_COLLECTED: sin PD1 en dmidecode -t 45"
    assert fila["ec"] == EC  # lo que si esta, entra
    assert fila["bios"] == "NOT_COLLECTED: sin Version en dmidecode -t bios"


@pytest.mark.parametrize("malo", ['PD0 x", "pd1": "falso', "PD0 x\\u0000", "PD0 x\x01", "PD0 " + "9" * 90])
def test_pd_firmware_control_negativo_texto_fuera_de_la_lista_blanca_no_entra_al_json(tmp_path: Path, malo: str) -> None:
    t45 = T45_REAL.replace(f"Firmware Version: {PD0}", f"Firmware Version: {malo}")
    assert t45 != T45_REAL
    _, fila = _forense_con(tmp_path, t45)  # json.loads de la fila no falla: la inyeccion no rompio la fila
    assert fila["pd0"] == "NOT_COLLECTED: valor fuera de la lista blanca" and fila["pd1"] == PD1


def test_pd_firmware_atascado_lee_los_valores_de_la_ultima_fila(tmp_path: Path) -> None:
    ruta = tmp_path / "arranque.jsonl"
    nueva = json.loads(FILA_VIEJA) | {"ts": "2026-10-27T06:00:00Z", "boot_id": "b-nuevo", "pd0": PD0, "pd1": PD1, "ec": EC, "bios": BIOS}
    ruta.write_text(FILA_VIEJA + "\n" + json.dumps(nueva) + "\n\n", encoding="utf-8")
    fw = r.firmware(ruta)
    assert isinstance(fw, dict) and (fw["pd0"], fw["pd1"], fw["ec"], fw["bios"]) == (PD0, PD1, EC, BIOS)
    assert fw["boot_id"] == "b-nuevo" and fw["ts"] == "2026-10-27T06:00:00Z"
    # control negativo: la ULTIMA fila manda; si la ultima es vieja, no se toma la anterior con valores
    ruta.write_text(json.dumps(nueva) + "\n" + FILA_VIEJA + "\n", encoding="utf-8")
    fw = r.firmware(ruta)
    assert isinstance(fw, str) and fw.startswith("NOT_COLLECTED: ") and "no trae valores" in fw and "bios+t45" in fw


def test_pd_firmware_control_negativo_fila_vieja_sin_archivo_o_ilegible_es_not_collected(tmp_path: Path) -> None:
    ruta = tmp_path / "arranque.jsonl"
    ruta.write_text(FILA_VIEJA + "\n", encoding="utf-8")
    casos = {"vieja": r.firmware(ruta), "no existe": r.firmware(tmp_path / "no.jsonl"), "directorio": r.firmware(tmp_path)}
    ruta.write_text("", encoding="utf-8")
    casos["vacio"] = r.firmware(ruta)
    ruta.write_text("{roto\n", encoding="utf-8")
    casos["roto"] = r.firmware(ruta)
    for caso, fw in casos.items():
        assert isinstance(fw, str) and fw.startswith("NOT_COLLECTED: ") and len(fw) > len("NOT_COLLECTED: ") + 5, caso
    # fila con solo parte de los valores: el que falta se declara, no queda vacio
    ruta.write_text(json.dumps({"ts": "t", "pd0": PD0, "ec": ""}) + "\n", encoding="utf-8")
    fw = r.firmware(ruta)
    assert isinstance(fw, dict) and fw["pd0"] == PD0 and fw["ec"].startswith("NOT_COLLECTED") and fw["pd1"].startswith("NOT_COLLECTED")


def test_pd_firmware_la_ruta_se_sustituye_por_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ruta = tmp_path / "a.jsonl"
    ruta.write_text(json.dumps({"pd0": PD0, "pd1": PD1, "ec": EC, "bios": BIOS}) + "\n", encoding="utf-8")
    monkeypatch.setenv("BB_ARRANQUE_JSONL", str(ruta))
    fw = r.firmware()
    assert isinstance(fw, dict) and fw["pd0"] == PD0
    monkeypatch.setenv("BB_ARRANQUE_JSONL", str(tmp_path / "otra.jsonl"))
    assert str(r.firmware()).startswith("NOT_COLLECTED")


def test_pd_firmware_de_punta_a_punta_la_fila_del_script_llega_al_veredicto(tmp_path: Path) -> None:
    base, _ = _forense_con(tmp_path, T45_REAL)
    fw = r.firmware(base / "pstore" / "arranque.jsonl")
    assert isinstance(fw, dict) and (fw["pd0"], fw["pd1"], fw["ec"], fw["bios"]) == (PD0, PD1, EC, BIOS)


def test_pd_firmware_atascado_lo_adjunta_y_sano_o_indeterminado_no(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    ruta = tmp_path / "arranque.jsonl"
    ruta.write_text(json.dumps({"ts": "t", "pd0": PD0, "pd1": PD1, "ec": EC, "bios": BIOS}) + "\n", encoding="utf-8")
    monkeypatch.setenv("BB_ARRANQUE_JSONL", str(ruta))
    _, salida = _main_con(monkeypatch, {"estado": "ATASCADO"}, capsys, ["--prueba"])
    assert salida["firmware"]["pd0"] == PD0 and salida["firmware"]["pd1"] == PD1
    for estado in ("SANO", "INDETERMINADO"):
        _, salida = _main_con(monkeypatch, {"estado": estado}, capsys, ["--prueba"])
        assert "firmware" not in salida, estado
    ruta.write_text(FILA_VIEJA + "\n", encoding="utf-8")
    _, salida = _main_con(monkeypatch, {"estado": "ATASCADO"}, capsys, ["--prueba"])
    assert salida["firmware"].startswith("NOT_COLLECTED: ")


def test_pd_firmware_evento_de_arranque_solo_lo_lleva_si_el_veredicto_lo_trae() -> None:
    assert r.evento_arranque({"estado": "ATASCADO", "firmware": {"pd0": PD0}}, "b")["firmware"] == {"pd0": PD0}
    assert "firmware" not in r.evento_arranque({"estado": "SANO"}, "b")


def _serie(tmp_path: Path, filas: list[dict]) -> Path:
    ruta = tmp_path / "t.jsonl"
    ruta.write_text("".join(json.dumps(x) + "\n" for x in filas), encoding="utf-8")
    return ruta


SANA_1 = _f(96, 2400, 55, ts="2026-10-12T22:00:00+00:00")
ATASCADA_1 = _f(96, 663, 16, ts="2026-10-12T23:17:16+00:00")
RECUPERADA_1 = _f(96, 2080, 67, ts="2026-10-13T08:00:00+00:00")


def test_inicio_episodio_con_recuperacion_devuelve_el_episodio_cerrado(tmp_path: Path) -> None:
    ruta = _serie(tmp_path, [SANA_1, ATASCADA_1, _f(96, 660, ts="2026-10-12T23:30:00+00:00"), RECUPERADA_1, _f(96, 2100, ts="2026-10-13T08:05:00+00:00")])
    d = r.inicio(ruta)  # firma de antes de la ficha: el mismo llamado sobre el codigo viejo devuelve None
    assert d is not None, "inicio() devolvio None sobre una serie con recuperacion: el episodio cerrado se perdio"
    ep = d["ultimo_episodio_cerrado"]
    assert ep == {k: r._local(v) for k, v in (("ultima_sana", SANA_1["ts"]), ("primera_atascada", ATASCADA_1["ts"]), ("primera_recuperada", RECUPERADA_1["ts"]))}
    assert "primera_atascada" not in d  # nada abierto al final de la serie


def test_inicio_episodio_control_negativo_sin_paso_no_devuelve_ni_escribe(tmp_path: Path) -> None:
    ep = tmp_path / "ep.jsonl"
    assert r.inicio(_serie(tmp_path, [SANA_1, RECUPERADA_1, _f(10, 600, ts="2026-10-13T09:00:00+00:00")]), ep) is None
    assert not ep.exists()


def test_inicio_episodio_se_persiste_sin_duplicar_y_el_abierto_tambien(tmp_path: Path) -> None:
    ep = tmp_path / "ep.jsonl"
    abierto = _serie(tmp_path, [SANA_1, ATASCADA_1])
    d = r.inicio(abierto, ep)
    assert d is not None and "ultimo_episodio_cerrado" not in d and d["primera_atascada"] == r._local(ATASCADA_1["ts"])
    filas = [json.loads(x) for x in ep.read_text(encoding="utf-8").splitlines()]
    assert filas == [{"ultima_sana": SANA_1["ts"], "primera_atascada": ATASCADA_1["ts"], "primera_recuperada": None}]
    r.inicio(abierto, ep)
    assert len(ep.read_text(encoding="utf-8").splitlines()) == 1  # idempotente: la misma corrida no duplica
    # se recupera y luego se atasca otra vez: entra la fila cerrada del primero y la abierta del segundo, una vez cada una
    atascada_2 = _f(96, 650, ts="2026-10-14T10:00:00+00:00")
    serie = _serie(tmp_path, [SANA_1, ATASCADA_1, RECUPERADA_1, atascada_2])
    for _ in range(2):
        d = r.inicio(serie, ep)
    filas = [json.loads(x) for x in ep.read_text(encoding="utf-8").splitlines()]
    assert len(filas) == 3 and filas[1]["primera_recuperada"] == RECUPERADA_1["ts"]
    assert filas[2] == {"ultima_sana": RECUPERADA_1["ts"], "primera_atascada": atascada_2["ts"], "primera_recuperada": None}
    assert d is not None and d["primera_atascada"] == r._local(atascada_2["ts"]) and d["ultimo_episodio_cerrado"]["primera_recuperada"] == r._local(RECUPERADA_1["ts"])
    # control negativo: el registro sobrevive a que la telemetria rote (aqui: desaparezca)
    serie.unlink()
    assert r.inicio(serie, ep) is None and len(ep.read_text(encoding="utf-8").splitlines()) == 3


def test_inicio_episodio_por_defecto_junto_a_la_telemetria(tmp_path: Path) -> None:
    r.inicio(_serie(tmp_path, [SANA_1, ATASCADA_1, RECUPERADA_1]))
    assert (tmp_path / "episodios_reloj.jsonl").exists()


def test_inicio_episodio_archivo_de_episodios_ilegible_no_duplica_ni_anula(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ep = tmp_path / "ep.jsonl"
    ep.write_text("{roto\n", encoding="utf-8")
    d = r.inicio(_serie(tmp_path, [SANA_1, ATASCADA_1, RECUPERADA_1]), ep)
    assert d is not None and "ultimo_episodio_cerrado" in d  # el veredicto no se anula
    assert ep.read_text(encoding="utf-8") == "{roto\n" and "ilegible" in capsys.readouterr().err


def test_inicio_episodio_main_arranque_recorre_la_telemetria_aunque_salga_sano(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    llamadas: list[int] = []
    monkeypatch.setattr(r.interruptores, "modo", lambda nombre: "off")
    _main_con(monkeypatch, {"estado": "SANO"}, capsys, ["--arranque"])
    monkeypatch.setattr(r, "inicio", lambda: llamadas.append(1))
    r.main(["--arranque"])
    assert llamadas == [1] and "desde" not in json.loads(capsys.readouterr().out)
    r.main(["--prueba"])  # control negativo: --prueba SANO no recorre los 235 MB
    assert llamadas == [1]


# --- DEBT-RELOJ-ARRANQUE-GPU-OCUPADA-POR-EL-MOTOR-01: con ocupantes la carga corre y se juzga por reloj ---
MOTOR = [{"pid": 100762, "nombre": "VLLM::EngineCor", "mib": 30953}]
ATLAS = [{"pid": 3382, "nombre": "python3", "mib": 4522}]


def test_motor_a_gpu_ocupada_y_reloj_sano_es_sano_con_tflops_no_valido(monkeypatch: pytest.MonkeyPatch) -> None:
    n_sync = _prepara_prueba(monkeypatch, "2080, 67.0, 96, 0x0000000000000000", ocupantes=[ATLAS, ATLAS + MOTOR])
    v = r.prueba(segundos=15)
    assert 0 < v["tflops"] < r.UMBRAL_TFLOPS  # los TFLOP/s del falso estan bajo el umbral: el segundo eje los veria bajos...
    assert v["estado"] == "SANO" and v["reloj_mediano_mhz"] == 2080.0 and v["tflops_valido"] is False  # ...y no se aplica
    assert v["tflops_motivo"].startswith("COMPETENCIA") and "3382" in v["tflops_motivo"] and "100762" in v["tflops_motivo"]
    assert [o["pid"] for o in v["ocupantes"]] == [3382, 100762] and "umbral_tflops" not in v and len(n_sync) > 10


def test_motor_b_gpu_ocupada_y_reloj_atascado_es_atascado(monkeypatch: pytest.MonkeyPatch) -> None:
    # la firma medida el 2026-10-12 (663 MHz, 16 W, util alta, cero throttle) con el motor y Atlas en la GPU: hoy imposible
    _prepara_prueba(monkeypatch, "663, 16.0, 97, 0x0000000000000000", ocupantes=[ATLAS + MOTOR, ATLAS + MOTOR])
    v = r.prueba(segundos=15)
    assert v["estado"] == "ATASCADO" and v["reloj_mediano_mhz"] == 663.0 and v["potencia_mediana_w"] == 16.0
    assert v["sin_throttle"] is True and v["tflops_valido"] is False


def test_motor_b_control_negativo_ocupada_con_throttle_no_es_atascado(monkeypatch: pytest.MonkeyPatch) -> None:
    _prepara_prueba(monkeypatch, "663, 16.0, 97, 0x0000000000000004", ocupantes=[MOTOR, MOTOR])
    v = r.prueba(segundos=15)
    assert v["estado"] == "INDETERMINADO" and v["motivo"].startswith("THROTTLE_ACTIVO")


def test_motor_c_gpu_libre_conserva_el_segundo_eje(monkeypatch: pytest.MonkeyPatch) -> None:
    # las mismas filas que (a) con la GPU libre: el segundo eje se aplica y los TFLOP/s bajos impiden el SANO
    _prepara_prueba(monkeypatch, "2080, 67.0, 96, 0x0000000000000000")
    v = r.prueba(segundos=15)
    assert v["estado"] == "INDETERMINADO" and v["motivo"].startswith("RELOJ_ALTO_RENDIMIENTO_BAJO") and v["tflops_valido"] is True
    assert "ocupantes" not in v and "tflops_motivo" not in v and v["umbral_tflops"] == r.UMBRAL_TFLOPS
    _prepara_prueba(monkeypatch, "1200, 20.0, 96, 0x0000000000000000")  # en banda: libre => ATASCADO por TFLOP/s
    assert r.prueba(segundos=15)["estado"] == "ATASCADO"
    _prepara_prueba(monkeypatch, "1200, 20.0, 96, 0x0000000000000000", ocupantes=[MOTOR, MOTOR])  # ocupada => solo reloj
    v = r.prueba(segundos=15)
    assert v["estado"] == "INDETERMINADO" and v["motivo"].startswith("RELOJ_EN_BANDA")


def _torch_que_falla(error: Exception) -> types.ModuleType:
    mod = _torch_falso([])

    def randn(*a: object, **k: object) -> _Tensor:
        raise error

    setattr(mod, "randn", randn)
    return mod


def test_motor_d_la_carga_no_puede_correr_es_indeterminado(monkeypatch: pytest.MonkeyPatch) -> None:
    _prepara_prueba(monkeypatch, "2080, 67.0, 96, 0x0000000000000000", ocupantes=[MOTOR])
    oom = RuntimeError("CUDA out of memory. Tried to allocate 128.00 MiB\nsegunda linea")
    monkeypatch.setitem(sys.modules, "torch", _torch_que_falla(oom))
    v = r.prueba(segundos=15)
    assert v["estado"] == "INDETERMINADO" and v["motivo"].startswith("CARGA_NO_PUDO_CORRER: RuntimeError: CUDA out of memory")
    assert "100762" in v["motivo"] and "segunda linea" not in v["motivo"] and v["ocupantes"] == MOTOR
    # sin torch y con la GPU libre: tambien sin traceback, y dice que la GPU estaba libre
    _prepara_prueba(monkeypatch, "2080, 67.0, 96, 0x0000000000000000", ocupantes=[[]])
    monkeypatch.setitem(sys.modules, "torch", None)
    v = r.prueba(segundos=15)
    assert v["estado"] == "INDETERMINADO" and v["motivo"].startswith("CARGA_NO_PUDO_CORRER: ModuleNotFoundError") and "GPU libre" in v["motivo"]


def test_motor_e_consulta_que_falla_sigue_siendo_not_collected(monkeypatch: pytest.MonkeyPatch) -> None:
    n_sync = _prepara_prueba(monkeypatch, "660, 12.5, 96, 0x0000000000000000", ocupantes=[None])
    v = r.prueba(segundos=15)
    assert v["estado"] == "INDETERMINADO" and v["motivo"] == r.SIN_CONSULTA and n_sync == []
    _prepara_prueba(monkeypatch, "660, 12.5, 96, 0x0000000000000000", ocupantes=[MOTOR, None])  # ocupada y falla al final
    v = r.prueba(segundos=15)
    assert v["estado"] == "INDETERMINADO" and v["motivo"] == r.SIN_CONSULTA


def test_motor_codigo_de_salida_en_arranque() -> None:
    carga = {"estado": "INDETERMINADO", "motivo": "CARGA_NO_PUDO_CORRER: RuntimeError: CUDA out of memory", "ocupantes": MOTOR}
    assert r.codigo(carga, es_arranque=True) == 0  # el entorno: la unidad no queda Failed en cada boot
    assert r.codigo(carga) == 2  # control negativo: `--prueba` a mano sigue diciendo indeterminado
    assert r.codigo({**carga, "ocupantes": []}, es_arranque=True) == 2  # GPU libre y la carga falla: el instrumento, se ve
    assert r.codigo({"estado": "INDETERMINADO", "motivo": r.SIN_CONSULTA}, es_arranque=True) == 2
    assert r.codigo({"estado": "INDETERMINADO", "motivo": "RELOJ_EN_BANDA: x", "ocupantes": MOTOR}, es_arranque=True) == 2
    assert r.codigo({"estado": "ATASCADO", "ocupantes": MOTOR}, es_arranque=True) == 1  # un ATASCADO real sigue en 1
    assert r.codigo({"estado": "SANO", "ocupantes": MOTOR}, es_arranque=True) == 0


def test_motor_main_arranque_usa_el_codigo_de_arranque(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(r.interruptores, "modo", lambda nombre: "observar")
    monkeypatch.setattr(r, "arranque", lambda modo, res, boot: None)
    carga = {"estado": "INDETERMINADO", "motivo": "CARGA_NO_PUDO_CORRER: RuntimeError: x", "ocupantes": MOTOR}
    assert _main_con(monkeypatch, carga, capsys, ["--arranque"])[0] == 0
    assert _main_con(monkeypatch, carga, capsys, ["--prueba"])[0] == 2
    assert _main_con(monkeypatch, {"estado": "ATASCADO", "ocupantes": MOTOR}, capsys, ["--arranque"])[0] == 1


def _pasa_el_close_check(ruta: Path) -> bool:
    """La condicion del close_check de la ficha, sobre `ruta` en vez del archivo real."""
    filas = [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines() if x.strip()]
    filas = [x for x in filas if x["ts"] > "2026-10-27T01:30"]
    return bool(filas) and "GPU_OCUPADA" not in str(filas[-1].get("motivo"))


def test_motor_la_fila_de_arranque_registra_ocupantes_y_tflops_valido(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # la fila real del 2026-10-27T02:04:46Z (boot 56a1942a) no pasa el close_check: control negativo de la condicion
    real = tmp_path / "real" / "reloj_arranque.jsonl"
    real.parent.mkdir()
    real.write_text(json.dumps({"ts": "2026-10-27T02:04:46.825766+00:00", "estado": "INDETERMINADO", "motivo": "GPU_OCUPADA: pid 3382 (python3, 4522 MiB); los TFLOP/s saldrian bajos por competencia, no por el estado de energia", "ocupantes": ATLAS}) + "\n", encoding="utf-8")
    assert not _pasa_el_close_check(real)
    _prepara_prueba(monkeypatch, "2080, 67.0, 96, 0x0000000000000000", ocupantes=[ATLAS, ATLAS + MOTOR])
    ev = r.arranque("observar", r.prueba(segundos=15), "b-motor", tmp_path, avisa=lambda a: pytest.fail("SANO no avisa"))
    assert ev is not None and ev["estado"] == "SANO" and ev["tflops_valido"] is False and ev["tflops_motivo"].startswith("COMPETENCIA")
    fila = json.loads((tmp_path / "reloj_arranque.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert fila["tflops_valido"] is False and [o["pid"] for o in fila["ocupantes"]] == [3382, 100762] and fila["motivo"] is None
    # la misma fila, fechada tras el merge, si pasa la condicion: el close_check puede salir en ambos sentidos
    with real.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({**fila, "ts": "2026-10-28T02:05:00+00:00"}) + "\n")
    assert _pasa_el_close_check(real)


# --- FEATURE-RELOJ-CAPTURA-DE-INCIDENTE-ANTES-DE-QUITAR-AC-01: la captura que NVIDIA pide antes de quitar la corriente ---

AHORA = 1793361600.0  # 2026-10-30T12:00:00Z
DATMAN = "Handle 0x0045, DMI type 45\nFirmware Component Name: PD Firmware\nFirmware Version: PD0 1.2.3\n"
ROOT_RUN = ["sudo", "-n", "bb-root-run"]


def _iso(segundos_antes: float) -> str:
    return datetime.fromtimestamp(AHORA - segundos_antes, timezone.utc).isoformat()


class _Maquina:
    """`ejecuta` falso con el estado que tocaria la maquina real: forense/ (lo escribe root) y el manifiesto instalado."""

    def __init__(self, tmp: Path, sellados: tuple[str, ...] = ("arranque-forense", "nvidia-bug-report"), t45_fresca: bool = True) -> None:
        tmp.mkdir(parents=True, exist_ok=True)
        self.tmp, self.forense, self.manifiesto = tmp, tmp / "forense", tmp / "manifest.json"
        self.forense.mkdir()
        self.manifiesto.write_text(json.dumps({k: {"file": f"{k}.sh"} for k in sellados}), encoding="utf-8")
        self.llamadas: list[list[str]] = []
        self.rc = {"nvidia-smi": 0, "arranque-forense": 0, "systemd-run": 0, "nvidia-bug-report": 0}
        self.escribe_gz = True
        if t45_fresca:
            self.t45(AHORA - 60)
        self.telemetria = tmp / "datos" / "atom_gpu_telemetry.jsonl"
        self.telemetria.parent.mkdir()
        filas = [_f(96, 2400, ts=_iso(5 * 3600 + 30)), _f(96, 660, ts=_iso(5 * 3600 - 30)), _f(96, 660, ts=_iso(3 * 3600)),
                 _f(96, 660, ts=_iso(3600)), _f(96, 660, ts=_iso(5)), _f(96, 660, ts="2026-10-30T11:30:00")]  # la ultima, sin zona
        self.telemetria.write_text("".join(json.dumps(x) + "\n" for x in filas), encoding="utf-8")
        self.desde = {"ultima_sana": _iso(5 * 3600 + 30), "primera_atascada": _iso(5 * 3600 - 30)}

    def t45(self, mtime: float) -> None:
        f = self.forense / "dmidecode-t45.txt"
        f.write_text(DATMAN, encoding="utf-8")
        os.utime(f, (mtime, mtime))

    def __call__(self, argv: list[str], timeout: int) -> tuple[int, str, str]:
        self.llamadas.append(argv)
        clave = argv[3] if argv[:3] == ROOT_RUN else argv[0]
        rc = self.rc[clave]
        if clave == "nvidia-smi":
            return rc, ("==============NVSMI LOG==============\nClocks\n    SM : 663 MHz\n" if rc == 0 else ""), ("" if rc == 0 else "nvidia-smi: not found")
        if clave == "arranque-forense" and rc == 0:
            self.t45(AHORA)
        if clave == "nvidia-bug-report" and rc == 0 and self.escribe_gz:
            (self.forense / r.BUG_REPORT_GZ).write_bytes(b"gz")
        return rc, "", ("" if rc == 0 else f"{clave} fallo")

    def captura(self, desde: dict | None = None, ahora: float = AHORA) -> dict:
        assert _CAPTURA_REAL is not None, "el modulo no tiene captura_incidente"
        return _CAPTURA_REAL(self.desde if desde is None else desde, base=self.tmp / "incidentes", telemetria=self.telemetria,
                             forense=self.forense, manifiesto=self.manifiesto, ejecuta=self, ahora=lambda: ahora,
                             boot_id="b00t", arranque_s=AHORA - 3600 * 6)

    def nombres(self) -> list[str]:
        return [x[3] if x[:3] == ROOT_RUN else x[0] for x in self.llamadas]


def _main_captura(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], m: _Maquina, estado: str) -> tuple[int, dict, str]:
    monkeypatch.delenv("BB_RELOJ_CAPTURA")
    monkeypatch.setattr(r, "captura_incidente", lambda desde: m.captura(desde))
    monkeypatch.setattr(r, "prueba", lambda: {"estado": estado, "reloj_mediano_mhz": 660.0})
    monkeypatch.setattr(r, "inicio", lambda: m.desde)
    monkeypatch.setenv("BB_ARRANQUE_JSONL", "/nonexistent-bb-test/arranque.jsonl")
    codigo = r.main(["--prueba"])
    out = capsys.readouterr()
    return codigo, json.loads(out.out), out.err


def test_captura_incidente_atascado_arma_la_carpeta_y_el_bug_report_en_curso_no_es_completa(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    m = _Maquina(tmp_path)
    codigo, salida, err = _main_captura(monkeypatch, capsys, m, "ATASCADO")
    c = salida["captura_incidente"]
    carpeta = tmp_path / "incidentes" / "reloj-b00t"
    assert codigo == 1 and c["carpeta"] == str(carpeta)
    assert (carpeta / "nvidia-smi-q.txt").read_text(encoding="utf-8").startswith("==============NVSMI LOG")
    assert (carpeta / "dmidecode-t45.txt").read_text(encoding="utf-8") == DATMAN
    assert {k: c["piezas"][k]["estado"] for k in r.PIEZAS} == {"nvidia_smi_q": "ok", "telemetria_2h": "ok", "telemetria_transicion": "ok",
                                                              "dmidecode_t45": "ok", "nvidia_bug_report": "could_not_run"}
    # el bug-report sigue corriendo: la captura NO se presenta como completa y la linea final lo dice
    assert c["completa"] is False and c["could_not_run"] == 1 and c["faltan"] == ["nvidia_bug_report"]
    assert c["piezas"]["nvidia_bug_report"]["motivo"].startswith("EN_CURSO")
    assert f"captura de incidente en {carpeta}: INCOMPLETA, could_not_run=1 de 5 -- nvidia_bug_report: EN_CURSO" in err
    assert json.loads((carpeta / "captura.json").read_text(encoding="utf-8"))["completa"] is False
    lanzado = [x for x in m.llamadas if x[0] == "systemd-run"]
    assert len(lanzado) == 1 and lanzado[0][-2:] == ["--completar-bug-report", str(carpeta)] and "--user" in lanzado[0]
    assert all(x[:3] == ROOT_RUN for x in m.llamadas if x[0] == "sudo")  # root solo via bb-root-run
    # el completador cierra la pieza: solo entonces la captura es completa
    assert r.completar_bug_report(carpeta, forense=m.forense, ejecuta=m, ahora=lambda: AHORA + 1) == 0
    final = json.loads((carpeta / "captura.json").read_text(encoding="utf-8"))
    assert final["completa"] is True and final["could_not_run"] == 0 and final["faltan"] == []
    assert (carpeta / r.BUG_REPORT_GZ).read_bytes() == b"gz" and ROOT_RUN + ["nvidia-bug-report"] in m.llamadas


@pytest.mark.parametrize("estado", ["SANO", "INDETERMINADO"])
def test_captura_incidente_control_negativo_sano_o_indeterminado_no_crea_carpeta(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], estado: str) -> None:
    m = _Maquina(tmp_path)
    _, salida, err = _main_captura(monkeypatch, capsys, m, estado)
    assert "captura_incidente" not in salida and "captura de incidente" not in err
    assert not (tmp_path / "incidentes").exists() and m.llamadas == []


def test_captura_incidente_control_negativo_bug_report_no_instalado_es_could_not_run(tmp_path: Path) -> None:
    m = _Maquina(tmp_path, sellados=("arranque-forense",))
    c = m.captura()
    pieza = c["piezas"]["nvidia_bug_report"]
    assert (tmp_path / "incidentes" / "reloj-b00t" / "nvidia-smi-q.txt").exists()  # la carpeta existe con lo demas
    assert pieza["estado"] == "could_not_run" and pieza["motivo"].startswith("NO_INSTALADO") and "bb_root_manifest --propose" in pieza["motivo"]
    assert c["completa"] is False and c["could_not_run"] == 1 and c["faltan"] == ["nvidia_bug_report"]
    assert "systemd-run" not in m.nombres()


@pytest.mark.parametrize("pieza", ["nvidia_smi_q", "telemetria_2h", "dmidecode_t45", "nvidia_bug_report"])
def test_captura_incidente_control_negativo_una_pieza_que_falla_nunca_sale_completa(tmp_path: Path, pieza: str) -> None:
    m = _Maquina(tmp_path, t45_fresca=pieza != "dmidecode_t45")
    if pieza == "nvidia_smi_q":
        m.rc["nvidia-smi"] = 127
    elif pieza == "telemetria_2h":
        m.telemetria.unlink()
    elif pieza == "dmidecode_t45":
        m.rc["arranque-forense"] = 1
    else:
        m.rc["systemd-run"] = 1
    c = m.captura()
    assert c["completa"] is False and pieza in c["faltan"] and c["piezas"][pieza]["estado"] == "could_not_run"
    assert c["could_not_run"] == len(c["faltan"])
    if pieza == "nvidia_bug_report":
        assert c["piezas"][pieza]["motivo"].startswith("systemd-run rc=1")


def test_captura_incidente_t45_solo_de_este_arranque(tmp_path: Path) -> None:
    m = _Maquina(tmp_path / "a")
    assert m.captura()["piezas"]["dmidecode_t45"]["estado"] == "ok" and "arranque-forense" not in m.nombres()  # fresca: sin root
    otra = _Maquina(tmp_path / "b", t45_fresca=False)
    otra.t45(AHORA - 3600 * 7)  # copia de un arranque anterior
    otra.rc["arranque-forense"] = 1
    p = otra.captura()["piezas"]["dmidecode_t45"]
    assert p["estado"] == "could_not_run" and "anterior a este arranque" in p["motivo"] and "rc=1" in p["motivo"]
    assert not (tmp_path / "b" / "incidentes" / "reloj-b00t" / "dmidecode-t45.txt").exists()
    otra.rc["arranque-forense"] = 0  # control: el script sellado la refresca y entonces si se adjunta
    assert otra.captura()["piezas"]["dmidecode_t45"]["estado"] == "ok"


def test_captura_incidente_telemetria_2h_y_la_transicion_con_sus_filas(tmp_path: Path) -> None:
    m = _Maquina(tmp_path / "a")
    c = m.captura()
    filas = [json.loads(x) for x in (tmp_path / "a" / "incidentes" / "reloj-b00t" / "telemetria.jsonl").read_text(encoding="utf-8").splitlines()]
    assert c["piezas"]["telemetria_2h"]["filas"] == 2 and c["piezas"]["telemetria_transicion"]["filas"] == 2
    assert [x["ts"] for x in filas] == [_iso(5 * 3600 + 30), _iso(5 * 3600 - 30), _iso(3600), _iso(5)]  # ni la de -3 h ni la sin zona
    # control negativo: sin el paso sano->atascado la pieza de transicion no se da por cubierta
    p = _Maquina(tmp_path / "b").captura(desde={})["piezas"]
    assert p["telemetria_2h"]["estado"] == "ok" and p["telemetria_transicion"]["estado"] == "could_not_run"
    assert p["telemetria_transicion"]["motivo"].startswith("NOT_COLLECTED")


def test_captura_incidente_segunda_corrida_no_repite_lo_ok_ni_el_bug_report_en_curso(tmp_path: Path) -> None:
    m = _Maquina(tmp_path)
    m.rc["nvidia-smi"] = 127
    m.captura()
    m.rc["nvidia-smi"] = 0
    m.llamadas.clear()
    c = m.captura(ahora=AHORA + 60)
    assert m.nombres() == ["nvidia-smi"] and c["piezas"]["nvidia_smi_q"]["estado"] == "ok"  # solo lo que faltaba
    m.llamadas.clear()
    c = m.captura(ahora=AHORA + r.EN_CURSO_MAX_S + 1)  # el completador murio sin cerrar: se vuelve a pedir
    assert m.nombres() == ["systemd-run"] and c["completa"] is False


def test_captura_incidente_completador_que_falla_o_gz_viejo_no_cierra_la_pieza(tmp_path: Path) -> None:
    m = _Maquina(tmp_path)
    carpeta = Path(m.captura()["carpeta"])
    m.rc["nvidia-bug-report"] = 3  # p. ej. bb-root-run rechaza un hash cambiado
    assert r.completar_bug_report(carpeta, forense=m.forense, ejecuta=m, ahora=lambda: AHORA + 1) == 2
    d = json.loads((carpeta / "captura.json").read_text(encoding="utf-8"))
    assert d["completa"] is False and "rc=3" in d["piezas"]["nvidia_bug_report"]["motivo"]
    assert (carpeta / "nvidia-bug-report.salida.txt").read_text(encoding="utf-8") == "nvidia-bug-report fallo"
    gz = m.forense / r.BUG_REPORT_GZ  # rc 0 pero el .gz es de otra corrida: no se adjunta
    gz.write_bytes(b"viejo")
    os.utime(gz, (AHORA - 600, AHORA - 600))
    m.rc["nvidia-bug-report"], m.escribe_gz = 0, False
    assert r.completar_bug_report(carpeta, forense=m.forense, ejecuta=m, ahora=lambda: AHORA + 1) == 2
    assert not (carpeta / r.BUG_REPORT_GZ).exists()
    m.escribe_gz = True  # control: la corrida que si deja su .gz cierra la pieza
    assert r.completar_bug_report(carpeta, forense=m.forense, ejecuta=m, ahora=lambda: AHORA + 1) == 0


def test_captura_incidente_evento_de_arranque_lleva_ruta_y_faltantes() -> None:
    c = {"carpeta": "/x/reloj-b", "completa": False, "could_not_run": 1, "faltan": ["nvidia_bug_report"], "piezas": {}}
    ev = r.evento_arranque({"estado": "ATASCADO", "captura_incidente": c}, "b")
    assert ev["captura_incidente"] == {"carpeta": "/x/reloj-b", "completa": False, "could_not_run": 1, "faltan": ["nvidia_bug_report"]}
    assert "captura_incidente" not in r.evento_arranque({"estado": "SANO"}, "b")


def test_captura_incidente_desactivada_por_variable_se_declara(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    _, salida = _main_con(monkeypatch, {"estado": "ATASCADO"}, capsys, ["--prueba"])
    assert salida["captura_incidente"] == {"estado": "could_not_run", "motivo": "desactivada por BB_RELOJ_CAPTURA=off"}


# --- FEATURE-RELOJ-PRUEBA-CALENTAMIENTO-ANTES-DE-MEDIR-01: calentar fuera del cronometro y el A/B que decide si hace falta ---


def _prueba_anotada(monkeypatch: pytest.MonkeyPatch, calentamiento: int | None) -> tuple[dict, list[str]]:
    """`prueba` con torch y reloj falsos que anotan el orden: 'mm' (matmul), 'sync' y 't' (lectura del reloj)."""
    eventos: list[str] = []

    class _T:
        def __matmul__(self, otro: object) -> "_T":
            eventos.append("mm")
            return self

    mod = types.ModuleType("torch")
    setattr(mod, "float16", "fp16")
    setattr(mod, "randn", lambda *a, **k: _T())
    setattr(mod, "cuda", types.SimpleNamespace(synchronize=lambda: eventos.append("sync")))
    monkeypatch.setitem(sys.modules, "torch", mod)
    respuestas: list[object] = [[], []]
    monkeypatch.setattr(r, "ocupantes", lambda *a, **k: respuestas.pop(0))
    reloj = [1000.0]

    def ahora() -> float:
        eventos.append("t")
        reloj[0] += 0.1
        return reloj[0]

    monkeypatch.setattr(r, "time", types.SimpleNamespace(time=ahora))
    monkeypatch.setattr(r, "subprocess", types.SimpleNamespace(run=lambda *a, **k: types.SimpleNamespace(stdout="2400, 60.0, 96, 0x0000000000000000\n")))
    v = r.prueba(segundos=15) if calentamiento is None else r.prueba(segundos=15, calentamiento=calentamiento)
    return v, eventos


def test_calentamiento_va_antes_del_cronometro_y_fuera_del_conteo(monkeypatch: pytest.MonkeyPatch) -> None:
    v10, ev10 = _prueba_anotada(monkeypatch, 10)
    v0, ev0 = _prueba_anotada(monkeypatch, 0)
    assert ev10[:12] == ["mm"] * 10 + ["sync", "t"]  # los 10 matmuls y su sincronizacion, antes de la primera lectura del reloj
    assert ev10.count("mm") - ev0.count("mm") == 10
    assert v10["tflops"] == v0["tflops"] > 0  # los 10 de calentamiento (0.7 TFLOP en 15 s) no entran en la cifra
    assert v10["calentamiento"] == 10 and v0["calentamiento"] == 0
    # control negativo: sin calentamiento el primer matmul ya corre bajo el cronometro y cuenta
    assert ev0.index("t") < ev0.index("mm")


def test_calentamiento_por_defecto_es_cero_mientras_el_ab_no_mida_el_sesgo(monkeypatch: pytest.MonkeyPatch) -> None:
    v, ev = _prueba_anotada(monkeypatch, None)
    assert v["calentamiento"] == 0 and ev.index("t") < ev.index("mm") and v["tflops_valido"] is True


def _mide_falso(sin: list[float], con: list[float], llamadas: list[int], invalida: int | None = None):
    colas = {0: list(sin), r.CALENTAMIENTO_MATMULS: list(con)}

    def mide(calentamiento: int) -> dict:
        llamadas.append(calentamiento)
        if invalida is not None and len(llamadas) == invalida:
            colas[calentamiento].pop(0)
            return {"estado": "SANO", "tflops": 20.0, "tflops_valido": False, "tflops_motivo": "COMPETENCIA: pid 1 (vllm, 4000 MiB)"}
        return {"estado": "SANO", "tflops": colas[calentamiento].pop(0), "tflops_valido": True}
    return mide


def test_calentamiento_ab_mide_el_sesgo_y_el_control_negativo_queda_dentro_de_la_dispersion() -> None:
    llamadas: list[int] = []
    res = r.ab(3, mide=_mide_falso([70.0, 71.0, 72.0], [76.0, 77.0, 78.0], llamadas))
    assert res["veredicto"] == "SESGO_MEDIDO" and res["diferencia_medianas"] == 6.0 and res["rango_mayor"] == 2.0
    assert res["sin"] == {"tflops": [70.0, 71.0, 72.0], "mediana": 71.0, "rango": 2.0} and res["could_not_run"] == 0
    assert llamadas == [0, 10, 10, 0, 0, 10]  # el orden se alterna en cada par
    # control negativo: los mismos brazos sin diferencia real no inventan un sesgo
    res = r.ab(3, mide=_mide_falso([70.0, 71.0, 72.0], [72.0, 70.0, 71.5], []))
    assert res["veredicto"] == "DENTRO_DE_LA_DISPERSION" and abs(res["diferencia_medianas"]) <= res["rango_mayor"]


def test_calentamiento_ab_control_negativo_gpu_ocupada_o_pocas_corridas_es_could_not_run() -> None:
    res = r.ab(3, mide=_mide_falso([70.0, 71.0, 72.0], [76.0, 77.0, 78.0], [], invalida=4))
    assert res["veredicto"].startswith("COULD_NOT_RUN") and res["could_not_run"] == 1 and "diferencia_medianas" not in res
    assert res["no_corrio"] == [{"corrida": 2, "brazo": "sin", "estado": "SANO", "motivo": "COMPETENCIA: pid 1 (vllm, 4000 MiB)"}]
    res = r.ab(2, mide=_mide_falso([70.0, 71.0], [76.0, 77.0], []))
    assert res["veredicto"].startswith("COULD_NOT_RUN: n=2") and "diferencia_medianas" not in res


def test_calentamiento_main_ab_sale_2_sin_veredicto_y_0_con_el(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(r, "prueba", lambda calentamiento=0: {"estado": "INDETERMINADO", "motivo": "CARGA_NO_PUDO_CORRER: RuntimeError: x"})
    assert r.main(["--ab", "3"]) == 2
    assert json.loads(capsys.readouterr().out)["could_not_run"] == 6
    monkeypatch.setattr(r, "prueba", lambda calentamiento=0: {"estado": "SANO", "tflops": 77.0 + calentamiento / 100, "tflops_valido": True})
    assert r.main(["--ab", "3"]) == 0
    assert json.loads(capsys.readouterr().out)["veredicto"] == "SESGO_MEDIDO"
