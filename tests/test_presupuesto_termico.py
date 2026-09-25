"""El gate termico: DGX-342, llegado de Atlas el 2026-09-25 (DGX-585).

Vino entero salvo su ultimo tercio, que probaba `_no_se_puede_tomar_otro` de
`liberation_watchdog` -- el DRENADOR de Atlas, que se queda alli y ahora
consulta este gate por proceso en vez de importarlo. Ese cableado se prueba
en `tests/test_liberation_watchdog.py` del repo de Atlas, y aqui se prueba lo
que decide: el presupuesto termico.

Original:

DGX-342: la cola tenía COMPUERTA de memoria y no tenía ninguna térmica.

El quinto crash del día tuvo 6 cruces de la alarma térmica en los 27 minutos
previos a morir, coincidiendo con este mismo watchdog encadenando jobs de
re-minado/reindexado sin pausa. `_presupuesto_termico` es la pregunta que
faltaba justo antes de tomar el job siguiente: ¿ya está caliente la máquina?

Mismo umbral que la telemetría de DGX-334 (94.8°C, 10°C bajo el trip de
104.8°C) -- dos números para "temperatura alta" en el mismo repo podrían
desacordar.

DGX-383 (2026-09-01): decidir con UNA muestra instantánea resultó medido como
57% de falsos frenos -- 36 de los 63 episodios de alarma del log real ocurren
con el GPU ocioso. El gate ahora exige `DEBOUNCE_MUESTRAS` calientes seguidas
y `CARGA_MINIMA_W` de consumo, y por eso **todo caso que espere un BLOQUEO
tiene que fijar su historial**: sin fijarlo, el veredicto lo decidiría la
temperatura ambiente de la máquina donde corra la suite. Medido: los mismos
casos daban verde en un worktree sin `logs/atom_gpu_telemetry.jsonl` y
devolvían "" contra el log vivo del checkout principal, con la máquina fría.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import atom_gpu_telemetry as tel

UMBRALES = {
    "thermal_zone0": {"type": "acpitz", "trip_c": 104.8, "umbral_c": 94.8},
    "thermal_zone4": {"type": "acpitz", "trip_c": 104.8, "umbral_c": 94.8},
}

# Valores del log real del 2026-09-01, no inventados: el episodio ocioso del
# dictamen tiene el GPU a 14.4 W, y las 768 muestras de carga real están sobre
# 60 W. `CALIENTE_C`/`FRIO_C` caen a los dos lados de 94.8.
OCIOSO_W = 14.4
CARGADO_W = 85.0
CALIENTE_C = 95.5
FRIO_C = 83.7


def _zona(nombre: str, temp_c) -> dict:
    return {"zona": nombre, "type": "acpitz", "temp_c": temp_c}


def _muestra(temp_c, watts, hace_s: float) -> dict:
    """Una línea `muestra` del jsonl del sampler, con la forma real que escribe
    `atom_gpu_telemetry` (verificada contra el log de producción)."""
    sello = datetime.now(timezone.utc) - timedelta(seconds=hace_s)
    return {
        "ts": sello.isoformat(), "evento": "muestra",
        "gpu_temp_c": 59.0, "gpu_util_pct": 6.0, "gpu_power_w": watts,
        "zonas": [_zona("thermal_zone0", temp_c), _zona("thermal_zone4", temp_c)],
    }


def _historial(pares, edad_ultima_s: float = 5.0) -> list[dict]:
    """`pares` es [(temp_c, watts), ...] de la MÁS VIEJA a la más nueva; los
    sellos quedan separados 5 s, el intervalo real del sampler."""
    n = len(pares)
    return [_muestra(t, watt, edad_ultima_s + 5.0 * (n - 1 - i))
            for i, (t, watt) in enumerate(pares)]


def _hist_sostenido_con_carga() -> list[dict]:
    """El caso que TIENE que seguir bloqueando: calor sostenido bajo carga
    real. Es el control negativo de todo lo que este archivo relaja."""
    return _historial([(CALIENTE_C, CARGADO_W)] * (tel.DEBOUNCE_MUESTRAS - 1))


def test_control_negativo_zonas_sanas_no_bloquean():
    """Carga normal (85-86°C medidos en DGX-334) tiene que pasar limpio -- sin
    este control, la prueba de abajo no probaría que el bloqueo depende de la
    temperatura real."""
    zonas = [_zona("thermal_zone0", 86.2), _zona("thermal_zone4", 84.0)]
    assert tel.presupuesto_termico(zonas, UMBRALES) == ""


def test_una_zona_sobre_el_umbral_bloquea_y_nombra_la_peor():
    """Reescrito en DGX-383: el historial se FIJA. El caso que describe sigue
    siendo el mismo (una zona sobre el umbral bloquea y se nombra), pero ahora
    sólo bloquea si el calor está corroborado, así que sin fijar el pasado la
    prueba mediría la máquina de quien corre la suite."""
    zonas = [_zona("thermal_zone0", 96.5), _zona("thermal_zone4", 84.0)]
    motivo = tel.presupuesto_termico(zonas, UMBRALES,
                                    historial=_hist_sostenido_con_carga())

    assert "thermal_zone0" in motivo
    assert "96.5" in motivo
    assert "94.8" in motivo
    assert "DGX-342" in motivo


def test_con_dos_zonas_calientes_reporta_la_mas_caliente():
    """Un motivo con la zona equivocada auditaría mal -- tiene que ser
    accionable, no sólo 'algo está caliente'. Historial fijado por DGX-383."""
    zonas = [_zona("thermal_zone0", 95.0), _zona("thermal_zone4", 97.6)]
    motivo = tel.presupuesto_termico(zonas, UMBRALES,
                                    historial=_hist_sostenido_con_carga())

    assert "thermal_zone4" in motivo
    assert "97.6" in motivo


def test_el_corte_esta_donde_dice_estar():
    """Justo en el umbral bloquea (>=, no >): la alarma de telemetría usa el
    mismo operador y las dos tienen que desacordar en cero casos. Historial
    fijado por DGX-383; el lado que NO bloquea no lo necesita, porque una
    lectura fría corta antes de consultar nada."""
    hist = _hist_sostenido_con_carga()
    assert tel.presupuesto_termico([_zona("thermal_zone0", 94.8)], UMBRALES,
                                  historial=hist) != ""
    assert tel.presupuesto_termico([_zona("thermal_zone0", 94.7)], UMBRALES,
                                  historial=hist) == ""


def test_zona_sin_temperatura_no_revienta_ni_bloquea():
    """`temp_c: None` es 'no se pudo leer', no 'cero grados' -- omitirla del
    cálculo es la misma doctrina que el resto del sampler."""
    assert tel.presupuesto_termico([_zona("thermal_zone0", None)], UMBRALES) == ""


def test_zona_sin_umbral_declarado_no_revienta_ni_bloquea():
    """Una zona que la telemetría reporta pero que no está en `umbrales` (p.
    ej. una plataforma distinta) se ignora en vez de fallar con KeyError."""
    zonas = [_zona("thermal_zone9", 99.0)]
    assert tel.presupuesto_termico(zonas, UMBRALES) == ""


# --------------------------------------------------------------------------
# DGX-383: compuerta de carga y debounce. Cada par de abajo es un test y su
# control negativo -- misma zona caliente, veredicto opuesto, y la única
# diferencia es el ingrediente que se está probando.
# --------------------------------------------------------------------------

def test_zona_caliente_con_gpu_ocioso_no_bloquea():
    """El 57% medido: 36 de los 63 episodios del log real disparaban con el
    GPU bajo 20 W. La zona está caliente y sostenida -- lo único que cambia
    respecto al test de abajo son los watts."""
    zonas = [_zona("thermal_zone0", 95.0)]
    hist = _historial([(CALIENTE_C, OCIOSO_W)] * (tel.DEBOUNCE_MUESTRAS - 1))

    assert tel.presupuesto_termico(zonas, UMBRALES, historial=hist) == ""


def test_zona_caliente_con_gpu_cargado_si_bloquea():
    """Control negativo del anterior, y el caso que el dictamen midió como
    REAL: con el GPU >=60 W, `thermal_zone0` tiene mediana 94.0°C y máximo
    98.3°C. Bajo carga la temperatura alta no es ruido y tiene que frenar."""
    zonas = [_zona("thermal_zone0", 95.0)]
    motivo = tel.presupuesto_termico(zonas, UMBRALES,
                                    historial=_hist_sostenido_con_carga())

    assert motivo != ""
    assert "thermal_zone0" in motivo
    assert f"{CARGADO_W:.1f} W" in motivo


def test_pico_aislado_rodeado_de_muestras_sanas_no_bloquea():
    """La ventana literal del dictamen, con el GPU a 14 W: z0 sube de 81.6 a
    95.0°C en 5 s y vuelve a 83.7 en 15 s. Aquí las previas están FRÍAS y los
    watts son de CARGA, para que el único motivo posible de no bloquear sea el
    debounce -- si el pico bastara, este caso frenaría la cola."""
    zonas = [_zona("thermal_zone0", 95.0)]
    hist = _historial([(FRIO_C, CARGADO_W)] * (tel.DEBOUNCE_MUESTRAS - 1))

    assert tel.presupuesto_termico(zonas, UMBRALES, historial=hist) == ""


def test_una_sola_previa_fria_ya_rompe_el_debounce():
    """El debounce exige TODAS las previas calientes, no la mayoría: una
    corrida que empieza no es una corrida sostenida."""
    zonas = [_zona("thermal_zone0", 95.0)]
    hist = _historial([(FRIO_C, CARGADO_W), (CALIENTE_C, CARGADO_W)])

    assert tel.presupuesto_termico(zonas, UMBRALES, historial=hist) == ""


def test_n_muestras_consecutivas_calientes_si_bloquean():
    """Control negativo del debounce: con exactamente `DEBOUNCE_MUESTRAS`
    lecturas calientes seguidas (la fresca más las previas) y carga real, el
    gate frena y lo dice."""
    zonas = [_zona("thermal_zone0", 96.0)]
    hist = _historial([(CALIENTE_C, CARGADO_W)] * (tel.DEBOUNCE_MUESTRAS - 1))
    motivo = tel.presupuesto_termico(zonas, UMBRALES, historial=hist)

    assert motivo != ""
    assert f"sostenido {tel.DEBOUNCE_MUESTRAS} muestras" in motivo


def test_historial_mas_largo_que_el_debounce_solo_mira_la_ventana():
    """Un episodio viejo y frío del mismo archivo no puede absolver al calor
    de ahora: sólo cuentan las `DEBOUNCE_MUESTRAS - 1` últimas."""
    zonas = [_zona("thermal_zone0", 96.0)]
    hist = _historial([(FRIO_C, OCIOSO_W)] * 8
                      + [(CALIENTE_C, CARGADO_W)] * (tel.DEBOUNCE_MUESTRAS - 1))

    assert tel.presupuesto_termico(zonas, UMBRALES, historial=hist) != ""


def test_la_compuerta_mira_el_pico_de_la_ventana_no_la_ultima_muestra():
    """Carga que acaba de caer sigue contando: el calor que dejó todavía es
    real. Mirar sólo la muestra más reciente absolvería el enfriamiento
    posterior a un job pesado, que es cuando la máquina está peor."""
    zonas = [_zona("thermal_zone0", 96.0)]
    hist = _historial([(CALIENTE_C, CARGADO_W), (CALIENTE_C, OCIOSO_W)])

    assert tel.presupuesto_termico(zonas, UMBRALES, historial=hist) != ""


# --------------------------------------------------------------------------
# DGX-383: sin datos frescos NO se pasa en silencio. Un gate que se vuelve
# permisivo cuando su instrumento se cae es el fallo que la política de
# reporte de la casa prohíbe: cero capturas es defecto del instrumento, nunca
# evidencia de que el sujeto esté limpio.
# --------------------------------------------------------------------------

def _bloqueo_declarado(motivo: str) -> bool:
    """El motivo bloquea Y confiesa que lo hace a ciegas. Las dos mitades
    importan: bloquear sin decirlo dejaría el freno sin auditar, y decirlo sin
    bloquear sería la permisividad que esto viene a impedir."""
    return motivo != "" and "DGX-383" in motivo


def test_sin_historial_bloquea_y_lo_declara():
    """El log ausente o vacío llega aquí como lista vacía."""
    zonas = [_zona("thermal_zone0", 96.0)]
    motivo = tel.presupuesto_termico(zonas, UMBRALES, historial=[])

    assert _bloqueo_declarado(motivo)
    assert "debounce" in motivo


def test_historial_insuficiente_bloquea_y_lo_declara():
    """Una muestra menos de las que exige el debounce no es 'casi': no alcanza
    para pronunciarse, así que se cae al criterio conservador."""
    zonas = [_zona("thermal_zone0", 96.0)]
    hist = _historial([(CALIENTE_C, CARGADO_W)] * (tel.DEBOUNCE_MUESTRAS - 2))

    assert _bloqueo_declarado(tel.presupuesto_termico(zonas, UMBRALES,
                                                     historial=hist))


def test_historial_viejo_bloquea_y_lo_declara():
    """El sampler murió hace rato: sus muestras siguen ahí y siguen frías, y
    creerles absolvería con datos que no describen el presente. Control
    negativo directo del caso ocioso de arriba -- mismo contenido, sólo cambia
    la antigüedad, y el veredicto se invierte."""
    zonas = [_zona("thermal_zone0", 96.0)]
    viejo = tel.MUESTRA_MAX_ANTIGUEDAD_S + 60.0
    hist = _historial([(FRIO_C, OCIOSO_W)] * (tel.DEBOUNCE_MUESTRAS - 1),
                      edad_ultima_s=viejo)
    motivo = tel.presupuesto_termico(zonas, UMBRALES, historial=hist)

    assert _bloqueo_declarado(motivo)
    assert "tope" in motivo


def test_historial_fresco_del_mismo_contenido_si_absuelve():
    """Control negativo del anterior: si esto también bloqueara, el test de
    arriba no estaría probando la antigüedad sino otra cosa."""
    zonas = [_zona("thermal_zone0", 96.0)]
    hist = _historial([(FRIO_C, OCIOSO_W)] * (tel.DEBOUNCE_MUESTRAS - 1))

    assert tel.presupuesto_termico(zonas, UMBRALES, historial=hist) == ""


def test_muestra_sin_sello_legible_bloquea_y_lo_declara():
    """`ts` corrupto no es `ts` reciente."""
    zonas = [_zona("thermal_zone0", 96.0)]
    hist = _historial([(FRIO_C, OCIOSO_W)] * (tel.DEBOUNCE_MUESTRAS - 1))
    hist[-1]["ts"] = "no-es-una-fecha"

    assert _bloqueo_declarado(tel.presupuesto_termico(zonas, UMBRALES,
                                                     historial=hist))


def test_sin_lectura_de_watts_bloquea_y_lo_declara():
    """`nvidia-smi` ausente deja `gpu_power_w: None` (el sampler lo escribe así
    a propósito). Sin watts no se puede AFIRMAR que el GPU esté ocioso, y una
    compuerta de carga que interpretara el hueco como 0 W absolvería justo
    cuando peor informada está."""
    zonas = [_zona("thermal_zone0", 96.0)]
    hist = _historial([(CALIENTE_C, None)] * (tel.DEBOUNCE_MUESTRAS - 1))

    assert _bloqueo_declarado(tel.presupuesto_termico(zonas, UMBRALES,
                                                     historial=hist))


# --------------------------------------------------------------------------
# DGX-383: el lector de la cola del jsonl. Se prueba contra archivos de
# verdad, no contra listas inyectadas -- es el único tramo que toca disco, y
# es donde vive el caso "el sampler no corre".
# --------------------------------------------------------------------------

def _escribir_jsonl(ruta: Path, eventos: list[dict]) -> Path:
    ruta.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n"
                            for e in eventos), encoding="utf-8")
    return ruta


def test_muestras_recientes_sin_archivo_devuelve_vacio_sin_reventar():
    """El sampler no corre, o corre desde otro checkout. Quien pregunta está
    decidiendo si frena trabajo: no puede recibir una excepción."""
    assert tel._muestras_recientes(2, Path("/no/existe/telemetria.jsonl")) == []


def test_muestras_recientes_archivo_vacio_devuelve_vacio(tmp_path):
    vacio = tmp_path / "vacio.jsonl"
    vacio.write_text("", encoding="utf-8")

    assert tel._muestras_recientes(2, vacio) == []


def test_muestras_recientes_devuelve_las_ultimas_en_orden(tmp_path):
    """Control negativo de los dos de arriba: con archivo bueno SÍ devuelve
    datos, y devuelve las MÁS NUEVAS, de la más vieja a la más nueva."""
    ruta = _escribir_jsonl(tmp_path / "t.jsonl",
                           _historial([(70.0, 10.0), (80.0, 20.0),
                                       (90.0, 30.0), (95.0, 40.0)]))
    ultimas = tel._muestras_recientes(2, ruta)

    assert [m["gpu_power_w"] for m in ultimas] == [30.0, 40.0]


def test_muestras_recientes_ignora_lineas_rotas_y_eventos_que_no_son_muestra(
        tmp_path):
    """El jsonl mezcla `muestra` con `temp_critica`, alertas de journal y
    arranques; y una línea a medio escribir puede cerrar el archivo, porque el
    sampler escribe en vivo. Nada de eso puede contar como muestra ni tumbar
    la lectura."""
    ruta = tmp_path / "sucio.jsonl"
    buenas = _historial([(95.0, 70.0), (96.0, 80.0)])
    ruta.write_text(
        json.dumps({"ts": buenas[0]["ts"], "evento": "temp_critica"}) + "\n"
        + json.dumps(buenas[0], ensure_ascii=False) + "\n"
        + json.dumps(buenas[1], ensure_ascii=False) + "\n"
        + '{"ts": "2026-09-01T00:00:00+00:00", "evento": "mues',
        encoding="utf-8")
    ultimas = tel._muestras_recientes(2, ruta)

    assert len(ultimas) == 2
    assert [m["gpu_power_w"] for m in ultimas] == [70.0, 80.0]


def test_muestras_recientes_solo_lee_la_cola_de_un_archivo_grande(tmp_path):
    """`MAX_LINEAS` deja el jsonl crecer a ~75 MB y `ingest_batch` lo consulta
    cada 30 s: leerlo entero sería el costo que esta función existe para no
    pagar. El relleno de arriba supera `COLA_BYTES`, así que si se leyera el
    archivo entero la lectura costaría todo ese tamaño."""
    relleno = _historial([(70.0, 5.0)] * 400, edad_ultima_s=3000.0)
    ruta = _escribir_jsonl(tmp_path / "grande.jsonl",
                           relleno + _historial([(95.0, 70.0), (96.0, 80.0)]))

    assert ruta.stat().st_size > tel.COLA_BYTES
    assert [m["gpu_power_w"]
            for m in tel._muestras_recientes(2, ruta)] == [70.0, 80.0]
