"""Las ramas que la suite heredada de Atlas no ejercía.

Este fichero nace de la migración de DGX-585: `tools/atom_gpu_telemetry.py`
pasó de Atlas a blackbox el 2026-09-24, y llegó con 458 sentencias al **87 %**.
Este repo exige 100 % sobre `tools/`, así que las 59 que faltaban se cubren
aquí en vez de bajarle el listón al gate.

Casi todas son ramas de ERROR y de borde: el fichero se lee de `/proc`, de
`journalctl` y de un endpoint HTTP, y esas son justo las que fallan durante un
cuelgue. Una suite que solo prueba el camino feliz de un instrumento de
cuelgues no prueba el instrumento.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tools import atom_gpu_telemetry as agt


# ------------------------------------------------------- lectura de /proc y sysfs

def test_argv_tokens_lee_el_argv_real_del_proceso_vivo():
    tokens = agt._argv_tokens(str(os.getpid()))
    assert tokens and any("pytest" in t or "python" in t for t in tokens), tokens


def test_control_negativo_argv_tokens_de_un_pid_muerto_da_lista_vacia():
    assert agt._argv_tokens("999999999") == []


def test_correr_devuelve_la_salida_del_proceso():
    assert agt._correr("echo", "hola").strip() == "hola"


def test_leer_texto_de_una_ruta_que_no_existe_da_None():
    assert agt._leer_texto(Path("/no/existe/de/verdad")) is None


def test_zonas_ordenadas_sin_directorio_de_zonas_da_lista_vacia(monkeypatch, tmp_path):
    monkeypatch.setattr(agt, "THERMAL_DIR", tmp_path / "ausente")
    assert agt._zonas_ordenadas() == []


def test_memoria_declara_los_campos_que_NO_encontro(monkeypatch, tmp_path):
    """Un hueco se declara; no se rellena con un cero que se leería como dato."""
    falso = tmp_path / "meminfo"
    falso.write_text("MemTotal:  1000 kB\n", encoding="utf-8")
    real = agt.Path

    class _P(type(Path())):
        pass

    def _path(arg, *a, **k):
        return falso if str(arg) == "/proc/meminfo" else real(arg, *a, **k)

    monkeypatch.setattr(agt, "Path", _path)
    campos = agt.leer_memoria_sistema()
    assert "mem_ausente" in campos, campos
    assert "no encontrados en /proc/meminfo" in campos["mem_ausente"]


# ------------------------------------------------------------------ vLLM

def test_linea_vllm_sin_valor_numerico_no_ensucia_el_resultado():
    res: dict = {}
    agt._procesar_linea_vllm("vllm:num_requests_running no_es_un_numero", res)
    assert res == {}


def test_linea_vllm_de_una_sola_palabra_se_ignora():
    res: dict = {}
    agt._procesar_linea_vllm("basura", res)
    assert res == {}


def test_vllm_con_status_distinto_de_200_lo_DECLARA(monkeypatch):
    class _Resp:
        status = 503
        def read(self): return b""            # pragma: no cover - no se llega
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(agt.urllib.request, "urlopen", lambda *a, **k: _Resp())
    campos = agt.leer_vllm_metrics(url="http://127.0.0.1:1/metrics")
    assert campos["vllm_ausente"] == "HTTP status 503", campos


# -------------------------------------------------------------- journal

def test_correr_journalctl_devuelve_el_stdout_del_journal_de_verdad():
    """No comparte punto de sustitucion con `_correr` a proposito: la salida
    -- o la falla -- de uno no se debe poder leer como dato del otro."""
    salida = agt._correr_journalctl("--no-pager", "-o", "json", "-n", "1")
    assert salida.strip(), "el journal de esta maquina no puede venir vacio"
    assert json.loads(salida.strip().splitlines()[-1]).get("__CURSOR"), salida[:200]


def test_control_negativo_journalctl_con_un_argumento_invalido_no_da_datos():
    """El error se va a stderr y el stdout queda vacio: una falla NO se puede
    leer como una linea de journal."""
    assert agt._correr_journalctl("--no-pager", "--opcion-que-no-existe") == ""


def test_journal_descarta_las_lineas_que_no_son_JSON(monkeypatch):
    salida = "nota de journalctl que no es json\n" + json.dumps(
        {"__CURSOR": "c1", "MESSAGE": "x"}) + "\n"
    monkeypatch.setattr(agt, "_correr_journalctl", lambda *a: salida)
    entradas, cursor = agt.leer_journal_nuevo("cursor-previo")
    assert len(entradas) == 1 and cursor == "c1", (entradas, cursor)


def test_linea_de_decodifica_un_MESSAGE_que_viene_como_bytes():
    linea = agt._linea_de({"MESSAGE": list(b"hola"), "SYSLOG_IDENTIFIER": "krn"})
    assert linea == "krn: hola", linea


def test_linea_de_con_MESSAGE_nulo_da_cadena_vacia():
    assert agt._linea_de({"MESSAGE": None}) == ""


# ------------------------------------------------- muestras recientes y edad

def test_muestras_recientes_sobre_un_fichero_que_no_existe_da_vacio(tmp_path):
    assert agt._muestras_recientes(3, ruta=tmp_path / "no-esta.jsonl") == []


def test_muestras_recientes_de_cero_da_vacio():
    assert agt._muestras_recientes(0) == []


def test_antiguedad_sin_sello_da_None_y_NO_cero():
    """None y 0.0 no son lo mismo: cero afirmaría que la muestra es de ahora."""
    assert agt._antiguedad_s({}) is None
    assert agt._antiguedad_s({"ts": "no-es-una-fecha"}) is None


def test_antiguedad_de_un_sello_sin_zona_se_lee_como_UTC():
    hace_un_minuto = (datetime.now(timezone.utc) - timedelta(minutes=1))
    edad = agt._antiguedad_s({"ts": hace_un_minuto.replace(tzinfo=None).isoformat()})
    assert edad is not None and 50 < edad < 70, edad


def test_pierna_de_carga_sin_vatios_dice_sin_datos():
    assert agt._pierna_de_carga([{"zonas": []}]) == ("sin_datos", None)


# ---------------------------------------------------------- corroboracion

def _historial(n, temp, vatios):
    ahora = datetime.now(timezone.utc).isoformat()
    return [{"ts": ahora, "gpu_power_w": vatios,
             "zonas": [{"zona": "thermal_zone0", "temp_c": temp}]} for _ in range(n)]


UMBRALES = {"thermal_zone0": {"umbral_c": 94.8, "trip_c": 104.8}}


def test_corroboracion_con_debounce_apagado_no_revienta(monkeypatch):
    """`ventana[-1]` sobre un historial vacío sería IndexError dentro del gate
    que decide si corre trabajo. Se declara sin_datos, no se explota."""
    monkeypatch.setattr(agt, "DEBOUNCE_MUESTRAS", 1)
    veredicto, detalle, carga, pico = agt._corroboracion([], UMBRALES)
    assert veredicto == "sin_datos" and "debounce está apagado" in detalle
    assert (carga, pico) == ("sin_datos", None)


def test_corroboracion_con_muestra_rancia_no_la_toma_por_buena():
    viejo = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    hist = [{"ts": viejo, "gpu_power_w": 90.0,
             "zonas": [{"zona": "thermal_zone0", "temp_c": 96.0}]}] * 8
    veredicto, detalle, _, _ = agt._corroboracion(hist, UMBRALES)
    assert veredicto == "sin_datos" and "tope" in detalle, detalle


def test_corroboracion_sin_sello_legible_en_la_ultima_muestra():
    hist = [{"ts": None, "gpu_power_w": 90.0,
             "zonas": [{"zona": "thermal_zone0", "temp_c": 96.0}]}] * 8
    veredicto, detalle, _, _ = agt._corroboracion(hist, UMBRALES)
    assert veredicto == "sin_datos" and "sello legible" in detalle, detalle


def test_corroboracion_sin_vatios_no_afirma_que_el_GPU_este_ocioso():
    ahora = datetime.now(timezone.utc).isoformat()
    hist = [{"ts": ahora, "zonas": [{"zona": "thermal_zone0", "temp_c": 96.0}]}] * 8
    veredicto, detalle, carga, _ = agt._corroboracion(hist, UMBRALES)
    assert veredicto == "sin_datos" and carga == "sin_datos"
    assert "no se puede afirmar que el GPU esté ocioso" in detalle, detalle


def test_corroboracion_CORROBORA_con_calor_sostenido_y_carga():
    veredicto, detalle, carga, pico = agt._corroboracion(_historial(8, 96.0, 90.0), UMBRALES)
    assert veredicto == "corrobora" and carga == "con_carga" and pico == 90.0
    assert "sostenido" in detalle, detalle


def test_control_negativo_corroboracion_DESCARTA_con_el_GPU_ocioso():
    veredicto, _, carga, _ = agt._corroboracion(_historial(8, 96.0, 5.0), UMBRALES)
    assert veredicto == "descarta" and carga == "ocioso"


# -------------------------------------------------------------- alarmas

def test_alarma_se_levanta_y_luego_se_normaliza_con_histeresis():
    estado: dict = {"en_alarma": set(), "inicio": {}}
    caliente = [{"zona": "thermal_zone0", "temp_c": 96.0, "type": "gpu"}]
    hist = _historial(8, 96.0, 90.0)
    subida = agt._alarmas(caliente, UMBRALES, estado, historial=hist)
    assert any(e["evento"] == "temp_critica" for e in subida), subida
    assert subida[0]["corroboracion"] == "corrobora"

    frio = [{"zona": "thermal_zone0", "temp_c": 80.0, "type": "gpu"}]
    bajada = agt._alarmas(frio, UMBRALES, estado, historial=hist)
    normalizada = [e for e in bajada if e["evento"] == "temp_normalizada"]
    assert normalizada, bajada
    assert normalizada[0]["segundos_en_alarma"] is not None


def test_control_negativo_una_zona_fria_no_levanta_alarma():
    estado: dict = {"en_alarma": set(), "inicio": {}}
    frio = [{"zona": "thermal_zone0", "temp_c": 50.0, "type": "gpu"}]
    assert agt._alarmas(frio, UMBRALES, estado, historial=_historial(8, 50.0, 90.0)) == []


# ------------------------------------------------------------ main / muestrear

def test_muestrear_emite_una_muestra_sin_escribir_nada(tmp_path, monkeypatch):
    monkeypatch.setattr(agt, "JSONL_PATH", tmp_path / "t.jsonl")
    eventos = agt.muestrear({}, {"en_alarma": set(), "inicio": {}, "anclas": {}},
                            escribir=False)
    assert eventos == [] or isinstance(eventos, list)
    assert not (tmp_path / "t.jsonl").exists(), "escribir=False no debe tocar disco"


def test_main_once_en_dry_run_imprime_y_sale_cero(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr(agt, "JSONL_PATH", tmp_path / "t.jsonl")
    monkeypatch.setattr(agt.sys, "argv", ["agt", "--once", "--dry-run"])
    assert agt.main() == 0
    salida = capsys.readouterr().out
    assert '"evento": "arranque"' in salida, salida[:300]
    assert not (tmp_path / "t.jsonl").exists()


def test_main_declara_si_no_hay_zonas_termicas(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr(agt, "THERMAL_DIR", tmp_path / "sin-zonas")
    monkeypatch.setattr(agt, "JSONL_PATH", tmp_path / "t.jsonl")
    monkeypatch.setattr(agt.sys, "argv", ["agt", "--once", "--dry-run"])
    agt.main()
    assert "zonas_ausentes" in capsys.readouterr().out


# ------------------------------------------------- presupuesto_termico (el gate)
# Este es EL gate: decide si se le suma más carga a una máquina caliente. Sus
# tres salidas tienen que distinguirse, y la tercera es la que importa -- sin
# telemetría fresca NO se relaja (DGX-383).

ZONA_CALIENTE = [{"zona": "thermal_zone0", "temp_c": 96.0, "type": "gpu"}]


def test_presupuesto_no_bloquea_si_ninguna_zona_pasa_del_umbral():
    frio = [{"zona": "thermal_zone0", "temp_c": 40.0, "type": "gpu"}]
    assert agt.presupuesto_termico(frio, UMBRALES, historial=_historial(8, 40.0, 90.0)) == ""


def test_presupuesto_BLOQUEA_con_calor_sostenido_y_carga():
    motivo = agt.presupuesto_termico(ZONA_CALIENTE, UMBRALES,
                                     historial=_historial(8, 96.0, 90.0))
    assert "se espera a que baje antes de sumar más carga" in motivo, motivo
    assert "thermal_zone0 a 96.0" in motivo


def test_control_negativo_presupuesto_DESCARTA_un_pico_con_el_GPU_ocioso():
    assert agt.presupuesto_termico(ZONA_CALIENTE, UMBRALES,
                                   historial=_historial(8, 96.0, 5.0)) == ""


def test_sin_telemetria_fresca_el_gate_NO_se_relaja(monkeypatch):
    """DGX-383: la ausencia de dato no es permiso. Con el historial rancio el
    gate bloquea con el criterio de una sola muestra, no deja pasar."""
    viejo = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    rancio = [{"ts": viejo, "gpu_power_w": 90.0,
               "zonas": [{"zona": "thermal_zone0", "temp_c": 96.0}]}] * 8
    motivo = agt.presupuesto_termico(ZONA_CALIENTE, UMBRALES, historial=rancio)
    assert "el gate NO se relaja" in motivo, motivo


def test_presupuesto_sin_historial_explicito_lo_lee_del_jsonl(monkeypatch, tmp_path):
    """El `historial=None` de los dos llamadores de DGX-342: leen del sampler."""
    ruta = tmp_path / "t.jsonl"
    ahora = datetime.now(timezone.utc).isoformat()
    ruta.write_text("\n".join(
        json.dumps({"ts": ahora, "evento": "muestra", "gpu_power_w": 90.0,
                    "zonas": [{"zona": "thermal_zone0", "temp_c": 96.0}]})
        for _ in range(10)) + "\n", encoding="utf-8")
    monkeypatch.setattr(agt, "JSONL_PATH", ruta)
    motivo = agt.presupuesto_termico(ZONA_CALIENTE, UMBRALES)
    assert "se espera a que baje" in motivo, motivo


# ------------------------------------------------------------ ramas de borde

def test_zonas_ordenadas_ordena_el_10_despues_del_9(tmp_path, monkeypatch):
    for n in (1, 2, 9, 10):
        (tmp_path / f"thermal_zone{n}").mkdir()
    monkeypatch.setattr(agt, "THERMAL_DIR", tmp_path)
    assert [p.name for p in agt._zonas_ordenadas()] == [
        "thermal_zone1", "thermal_zone2", "thermal_zone9", "thermal_zone10"]


def test_procesos_gpu_ignora_las_lineas_con_otro_numero_de_campos(monkeypatch):
    monkeypatch.setattr(agt, "_correr", lambda *a: "1, python, 100\n2, roto\n\n")
    res = agt.leer_procesos_gpu()
    assert res["gpu_mem_total_mib"] == 100, res
    assert len(res["gpu_procs"]) == 1, res


def test_journal_ignora_las_lineas_en_blanco(monkeypatch):
    monkeypatch.setattr(agt, "_correr_journalctl",
                        lambda *a: "\n\n" + json.dumps({"__CURSOR": "c", "MESSAGE": "m"}) + "\n")
    entradas, _ = agt.leer_journal_nuevo("previo")
    assert len(entradas) == 1


def test_muestras_recientes_descarta_una_linea_a_medio_escribir(tmp_path, monkeypatch):
    ruta = tmp_path / "t.jsonl"
    ahora = datetime.now(timezone.utc).isoformat()
    bueno = json.dumps({"ts": ahora, "evento": "muestra", "gpu_power_w": 1.0})
    ruta.write_text(bueno + "\n" + '{"ts": "cortad', encoding="utf-8")
    assert len(agt._muestras_recientes(5, ruta=ruta)) == 1


def test_escribir_deja_la_linea_en_disco_con_fsync(tmp_path, monkeypatch):
    """El sampler existe para sobrevivir a una muerte dura: lo que no se
    sincroniza no existe despues del cuelgue."""
    ruta = tmp_path / "t.jsonl"
    monkeypatch.setattr(agt, "JSONL_PATH", ruta)
    agt._escribir({"evento": "prueba"})
    assert json.loads(ruta.read_text(encoding="utf-8").strip())["evento"] == "prueba"


def test_es_el_script_invocado_rechaza_lo_que_es_argumento_de_otro_script():
    """Hacia atras hay un token que no es bandera ni interprete: es otro script,
    asi que `tokens[i]` es argumento suyo y no el script invocado."""
    assert agt._es_el_script_invocado(["wrapper.sh", "otro.py", "dato.py"], 2) is False
    assert agt._es_el_script_invocado(["x.py"], 0) is True
    assert agt._es_el_script_invocado(["python3", "-u", "x.py"], 2) is True


def test_zonas_ordenadas_con_el_directorio_ilegible_da_vacio(monkeypatch, tmp_path):
    """Un OSError leyendo sysfs no puede tumbar al sampler."""
    class _Roto:
        def glob(self, _patron):
            raise OSError("sysfs ilegible")

    monkeypatch.setattr(agt, "THERMAL_DIR", _Roto())
    assert agt._zonas_ordenadas() == []


def test_el_dedupe_olvida_las_anclas_que_salieron_de_la_ventana(monkeypatch):
    """Sin la poda, una ancla vieja seguiria suprimiendo eventos nuevos para
    siempre -- un supresor que no caduca es un instrumento que deja de avisar."""
    viejo = 1000.0
    estado = {"cursor": "c0", "anclas": {"clave-vieja": viejo}}
    entrada = {"__CURSOR": "c1", "MESSAGE": "GPU has fallen off the bus",
               "_TRANSPORT": "kernel",
               "__REALTIME_TIMESTAMP": str(int((viejo + agt.VENTANA_DEDUPE_S + 60) * 1e6))}
    monkeypatch.setattr(agt, "_correr_journalctl",
                        lambda *a: json.dumps(entrada) + "\n")
    eventos, _cursor = agt.vigilar_journal(estado)
    # se observa lo que la llamada DEVUELVE, no solo el estado que muto
    assert len(eventos) == 1, eventos
    assert eventos[0]["tipo"] == "gpu_fuera_del_bus", eventos[0]
    assert "clave-vieja" not in estado["anclas"], estado["anclas"]
    assert ("gpu_fuera_del_bus", None, None) in estado["anclas"], estado["anclas"]


def test_reanudar_un_proceso_que_ya_murio_no_revienta():
    """Se pauso, murio mientras estaba pausado, y al reanudar ya no esta."""
    def _muerto(_pid, _sig):
        raise ProcessLookupError

    estado = {"mitigados": [999999999], "en_alarma": set(), "inicio": {}}
    resultado = agt.mitigar([], estado, enviar_senal=_muerto)
    assert estado["mitigados"] == [], estado
    assert any(e["evento"] == "mitigacion_reanuda" for e in resultado), resultado


def test_solo_banderas_hacia_atras_no_basta_para_ser_el_script():
    """Se agotan los tokens sin hallar interprete: no se puede afirmar que lo sea."""
    assert agt._es_el_script_invocado(["-u", "x.py"], 1) is False


def test_el_bucle_sale_limpio_con_Ctrl_C(monkeypatch, tmp_path, capsys):
    """Sin `--once` el sampler es de vida larga; la unica salida ordenada es
    la senal, y tiene que devolver 0, no un traceback."""
    monkeypatch.setattr(agt, "JSONL_PATH", tmp_path / "t.jsonl")
    monkeypatch.setattr(agt.sys, "argv", ["agt", "--dry-run"])

    def _corta(_s):
        raise KeyboardInterrupt

    monkeypatch.setattr(agt.time, "sleep", _corta)
    assert agt.main() == 0
    assert '"evento": "arranque"' in capsys.readouterr().out


# ------------------------------------------------------- el gate como comando
# Atlas consulta la decision termica por PROCESO, no por import (contrato de
# los dos repos, DGX-585). Si este contrato se rompe, el encolador de Atlas
# decide con otro numero que el sampler, y dos "temperatura alta" en la misma
# maquina se desacuerdan en silencio.


def _gate(monkeypatch, capsys, zonas, umbrales, historial_en_disco, tmp_path):
    ruta = tmp_path / "t.jsonl"
    ruta.write_text("\n".join(json.dumps(m | {"evento": "muestra"})
                              for m in historial_en_disco) + "\n", encoding="utf-8")
    monkeypatch.setattr(agt, "JSONL_PATH", ruta)
    monkeypatch.setattr(agt, "leer_zonas", lambda: zonas)
    monkeypatch.setattr(agt, "leer_umbrales", lambda: umbrales)
    monkeypatch.setattr(agt.sys, "argv", ["agt", "--gate-termico"])
    rc = agt.main()
    return rc, json.loads(capsys.readouterr().out)


def test_gate_termico_como_comando_BLOQUEA_y_sale_1(monkeypatch, capsys, tmp_path):
    rc, salida = _gate(monkeypatch, capsys, ZONA_CALIENTE, UMBRALES,
                       _historial(10, 96.0, 90.0), tmp_path)
    assert rc == 1, salida
    assert salida["bloquea"] is True
    assert "se espera a que baje" in salida["motivo"], salida


def test_control_negativo_gate_termico_DEJA_PASAR_una_maquina_fria(monkeypatch, capsys, tmp_path):
    fria = [{"zona": "thermal_zone0", "temp_c": 45.0, "type": "gpu"}]
    rc, salida = _gate(monkeypatch, capsys, fria, UMBRALES,
                       _historial(10, 45.0, 90.0), tmp_path)
    assert rc == 0, salida
    assert salida["bloquea"] is False and salida["motivo"] == ""


def test_el_gate_por_comando_NO_se_relaja_sin_telemetria_fresca(monkeypatch, capsys, tmp_path):
    """Quien no sabe, no pasa: es la unica politica segura para un encolador
    que decide si le suma 68 GB a una maquina caliente."""
    viejo = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    rancio = [{"ts": viejo, "gpu_power_w": 90.0,
               "zonas": [{"zona": "thermal_zone0", "temp_c": 96.0}]} for _ in range(10)]
    rc, salida = _gate(monkeypatch, capsys, ZONA_CALIENTE, UMBRALES, rancio, tmp_path)
    assert rc == 1 and "el gate NO se relaja" in salida["motivo"], salida


# ------------------------------------------- procesos de GPU como comando
# Atlas preguntaba "quien esta en la GPU" invocando nvidia-smi por su cuenta.
# Con la frontera de DGX-585 el driver lo interroga quien gobierna el hardware
# y Atlas decide con la respuesta: el HECHO aqui, la POLITICA alli.


def test_procesos_gpu_como_comando_devuelve_el_hecho(monkeypatch, capsys):
    monkeypatch.setattr(agt, "_correr", lambda *a: "1234, python3, 500\n")
    monkeypatch.setattr(agt.sys, "argv", ["agt", "--procesos-gpu"])
    rc = agt.main()
    salida = json.loads(capsys.readouterr().out)
    assert rc == 0, salida
    assert salida["gpu_mem_total_mib"] == 500
    assert salida["gpu_procs"][0]["pid"] == "1234"


def test_control_negativo_procesos_gpu_sale_1_si_no_pudo_averiguarlo(monkeypatch, capsys):
    """Quien no sabe, no pasa: si nvidia-smi no se puede ejecutar, el rc dice
    que no hubo respuesta en vez de devolver una lista vacia, que el llamador
    leeria como 'la GPU esta libre'."""
    def _no_ejecutable(*_a):
        raise OSError("no existe")

    monkeypatch.setattr(agt, "_correr", _no_ejecutable)
    monkeypatch.setattr(agt.sys, "argv", ["agt", "--procesos-gpu"])
    rc = agt.main()
    salida = json.loads(capsys.readouterr().out)
    assert rc == 1, salida
    assert salida["gpu_procs"] is None
    assert "no ejecutable" in salida["gpu_procs_ausente"]


def test_una_gpu_de_verdad_ociosa_NO_es_lo_mismo_que_no_saber(monkeypatch, capsys):
    """Cero procesos es un dato valido; la diferencia con el caso de arriba es
    justo lo que el rc distingue."""
    monkeypatch.setattr(agt, "_correr", lambda *a: "")
    monkeypatch.setattr(agt.sys, "argv", ["agt", "--procesos-gpu"])
    rc = agt.main()
    salida = json.loads(capsys.readouterr().out)
    assert rc == 0 and salida["gpu_procs"] == [] and salida["gpu_mem_total_mib"] == 0
