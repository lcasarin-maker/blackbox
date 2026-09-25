"""DGX-408: `mitigar()` pausa SÓLO cuando la alarma trae carga real en el GPU.

La compuerta es `carga_gpu == "con_carga"`, el campo que `_alarmas` escribe en
cada `temp_critica` desde DGX-396. El motivo está medido: la alarma cruda es
ruido 3 de cada 4 veces, y 90 s después del reinicio de las 18:41:52 el primer
cruce salió `descarta / ocioso / 14.11 W de pico` a 95.2 °C declarados -- un
pico de sensor con el GPU casi apagado que la mitigación vieja habría atendido
con un SIGSTOP.

**Qué prueba este archivo, y por qué son cuatro casos y no uno.** Un
`mitigar()` que nunca pause pasaría un test que sólo compruebe "ya no pausa en
ocioso". Los cuatro casos son el control negativo mutuo:

  `con_carga`      -> pausa
  `ocioso`         -> no pausa, y NO emite `mitigacion_sin_datos`
  campo ausente    -> no pausa, y SÍ emite `mitigacion_sin_datos`
  `sin_datos`      -> no pausa, y SÍ emite `mitigacion_sin_datos`

Los dos últimos son la parte delicada: sin su evento propio, una compuerta que
lee un campo que dejó de escribirse quedaría **desactivada pareciendo
arreglada** -- cero pausas, indistinguible del cero de "filtró bien".

**Convención de las ventanas replayadas.** Los eventos y las muestras salen
verbatim de `logs/atom_gpu_telemetry.jsonl`; lo único que se re-sella es el
`ts` de las muestras del historial, porque `_corroboracion` descarta por vieja
toda ventana de más de `MUESTRA_MAX_ANTIGUEDAD_S` y estas son de ayer. La
ventana de cada cruce es la misma que usó el replay de
`docs/agent_findings/2026-09-01_pierna_de_carga_en_el_flanco.md` (las dos
últimas muestras escritas, la del cruce incluida), para que los picos de aquí
sean los mismos que su tabla publicó.
"""
import json
from datetime import datetime, timedelta, timezone

from tools import atom_gpu_telemetry as agt

# La línea LITERAL del jsonl de producción: el primer cruce tras el reinicio
# de las 18:41:52, 90 s después. 95.2 °C declarados con el GPU a 14.11 W de
# pico -- el caso que justifica la ficha.
EVENTO_REAL_004317 = json.loads(
    '{"ts": "2026-09-02T00:43:17.794554+00:00", "zona": "thermal_zone4", '
    '"type": "acpitz", "temp_c": 95.2, "umbral_c": 94.8, "trip_c": 104.8, '
    '"evento": "temp_critica", "corroboracion": "descarta", '
    '"corroboracion_detalle": "2 de las 2 muestras previas están bajo el '
    'umbral: pico aislado del sensor, no evento térmico", '
    '"carga_gpu": "ocioso", "carga_gpu_pico_w": 14.11}')

# Las 7 zonas `acpitz` de la ATOM, con el `trip_c` real de 104.8 °C y el
# `umbral_c` de 94.8 que el log trae en cada evento.
UMBRALES_ATOM = {f"thermal_zone{i}": {"type": "acpitz", "trip_c": 104.8,
                                      "umbral_c": 94.8} for i in range(7)}

# Ventanas reales, `(vatios, [7 temperaturas])`, de los 27 minutos previos al
# quinto crash de DGX-342. La primera es el cruce de las 02:42:21 (pico 90.16
# W, `con_carga`); la segunda la de las 02:59:27 (pico 40.03 W, `ocioso`) --
# el límite declarado de la compuerta.
VENTANA_PRECURSOR_CON_CARGA = [
    (87.05, [94.2, 73.2, 82.3, 72.6, 74.4, 94.2, 77.7]),   # 02:42:16
    (90.16, [96.5, 73.6, 75.4, 74.6, 83.8, 96.5, 75.9]),   # 02:42:21, el cruce
]
VENTANA_PRECURSOR_40W = [
    (40.03, [85.6, 75.0, 85.6, 75.1, 84.3, 83.0, 79.9]),   # 02:59:22
    (29.15, [96.4, 73.7, 83.6, 74.9, 96.4, 79.9, 78.8]),   # 02:59:27, el cruce
]


class _SenalFalsa:
    """Mismo doble que `test_atom_gpu_telemetry`: registra sin señalar nada."""

    def __init__(self) -> None:
        self.llamadas: list[tuple[int, int]] = []

    def __call__(self, pid: int, sig: int) -> None:
        self.llamadas.append((pid, sig))


def _critica(carga: str | None = "con_carga", *, zona: str = "thermal_zone0",
             pico: float | None = 90.16) -> dict:
    """Un `temp_critica` con la forma que `_alarmas` emite. `carga=None`
    devuelve el evento SIN el campo (un evento anterior a DGX-396), que no es
    lo mismo que `carga="sin_datos"`."""
    evento = {"evento": "temp_critica", "zona": zona, "type": "acpitz",
              "temp_c": 96.5, "umbral_c": 94.8, "trip_c": 104.8,
              "corroboracion": "descarta"}
    if carga is not None:
        evento["carga_gpu"] = carga
        evento["carga_gpu_pico_w"] = pico
    return evento


def _historial(ventana):
    """Las muestras de `ventana` re-selladas a los últimos segundos, para que
    `_corroboracion` no las descarte por viejas. Los vatios y las temperaturas
    son los del log, sin tocar."""
    ahora = datetime.now(timezone.utc)
    muestras = []
    for i, (vatios, temps) in enumerate(ventana):
        sello = ahora - timedelta(seconds=5 * (len(ventana) - i))
        muestras.append({
            "ts": sello.isoformat(), "evento": "muestra",
            "gpu_power_w": vatios,
            "zonas": [{"zona": f"thermal_zone{j}", "type": "acpitz",
                       "temp_c": t} for j, t in enumerate(temps)],
        })
    return muestras


def _zonas(temps):
    return [{"zona": f"thermal_zone{j}", "type": "acpitz", "temp_c": t}
            for j, t in enumerate(temps)]


# --- los cuatro casos de la compuerta -------------------------------------

def test_con_carga_pausa():
    """Control POSITIVO. Sin él los tres negativos de abajo los pasaría un
    `mitigar()` que nunca pause, que es exactamente la falla que se teme."""
    senal = _SenalFalsa()
    estado = {"en_alarma": {"thermal_zone0"}, "mitigados": set()}

    resultado = agt.mitigar([_critica("con_carga")], estado,
                            listar_pids=lambda: [111], enviar_senal=senal)

    assert senal.llamadas == [(111, agt.signal.SIGSTOP)]
    assert estado["mitigados"] == {111}
    assert [e["evento"] for e in resultado] == ["mitigacion_pausa"]


def test_ocioso_no_pausa_y_no_emite_sin_datos():
    """`ocioso` es un VEREDICTO, no un hueco: la compuerta hizo su trabajo y
    no hay nada que reportar. Emitir `mitigacion_sin_datos` aquí ahogaría la
    señal que sí importa bajo el 72% de ruido del log."""
    senal = _SenalFalsa()
    estado = {"en_alarma": {"thermal_zone0"}, "mitigados": set()}

    resultado = agt.mitigar([_critica("ocioso", pico=14.11)], estado,
                            listar_pids=lambda: [111], enviar_senal=senal)

    assert senal.llamadas == []
    assert estado["mitigados"] == set()
    assert resultado == []


def test_campo_ausente_no_pausa_y_emite_sin_datos():
    """La rama delicada. Un evento anterior a DGX-396 no trae `carga_gpu`, la
    condición nunca se cumple, y sin este evento propio la mitigación quedaría
    apagada con el mismo cero que tiene cuando funciona."""
    senal = _SenalFalsa()
    estado = {"en_alarma": {"thermal_zone0"}, "mitigados": set()}

    resultado = agt.mitigar([_critica(None)], estado,
                            listar_pids=lambda: [111], enviar_senal=senal)

    assert senal.llamadas == []
    assert estado["mitigados"] == set()
    assert [e["evento"] for e in resultado] == ["mitigacion_sin_datos"]
    assert resultado[0]["zona"] == "thermal_zone0"
    assert resultado[0]["carga_gpu"] is None
    assert "no trae `carga_gpu`" in resultado[0]["motivo"]


def test_sin_datos_no_pausa_y_emite_sin_datos():
    """El otro hueco: el sampler corrió pero no dejó `gpu_power_w` fresco. Se
    reporta con un motivo DISTINTO al del campo ausente -- son dos averías
    distintas y colapsarlas perdería cuál de las dos está pasando."""
    senal = _SenalFalsa()
    estado = {"en_alarma": {"thermal_zone4"}, "mitigados": set()}

    resultado = agt.mitigar([_critica("sin_datos", zona="thermal_zone4",
                                      pico=None)], estado,
                            listar_pids=lambda: [111], enviar_senal=senal)

    assert senal.llamadas == []
    assert [e["evento"] for e in resultado] == ["mitigacion_sin_datos"]
    assert resultado[0]["zona"] == "thermal_zone4"
    assert resultado[0]["carga_gpu"] == "sin_datos"
    assert "sampler no dejó" in resultado[0]["motivo"]


def test_lote_mixto_pausa_por_una_zona_y_reporta_el_hueco_de_la_otra():
    """Una muestra puede traer varias zonas cruzando a la vez -- los cruces
    reales de DGX-342 vienen de dos en dos. Si una trae `con_carga` y otra
    viene sin clasificar, se pausa POR la primera y se reporta el hueco de la
    segunda: la pausa no es coartada para callar que a esa alarma no se le
    pudo aplicar la compuerta."""
    senal = _SenalFalsa()
    estado = {"en_alarma": {"thermal_zone0", "thermal_zone4"},
              "mitigados": set()}

    resultado = agt.mitigar(
        [_critica("con_carga"), _critica("sin_datos", zona="thermal_zone4")],
        estado, listar_pids=lambda: [111], enviar_senal=senal)

    assert senal.llamadas == [(111, agt.signal.SIGSTOP)]
    assert [e["evento"] for e in resultado] == ["mitigacion_pausa",
                                                "mitigacion_sin_datos"]
    assert resultado[1]["zona"] == "thermal_zone4"


# --- replay de los eventos reales -----------------------------------------

def test_replay_del_evento_real_de_las_004317_no_pausa():
    """El caso que justifica el encargo, con la línea literal del jsonl: 95.2
    °C declarados 90 s después del reinicio, `ocioso`, 14.11 W de pico. La
    mitigación vieja lo habría atendido; si un `remine_harvest_lens.py`
    hubiera estado corriendo, le habría llegado un SIGSTOP por ruido de
    sensor."""
    senal = _SenalFalsa()
    estado = {"en_alarma": {"thermal_zone4"}, "mitigados": set()}

    resultado = agt.mitigar([EVENTO_REAL_004317], estado,
                            listar_pids=lambda: [111], enviar_senal=senal)

    assert EVENTO_REAL_004317["carga_gpu"] == "ocioso"
    assert EVENTO_REAL_004317["carga_gpu_pico_w"] == 14.11
    assert senal.llamadas == []
    assert resultado == []


def test_replay_del_primer_precursor_de_dgx342_si_pausa():
    """Control positivo con material real, y de punta a punta: la ventana del
    cruce de las 02:42:21 entra por `_alarmas`, que es quien ESCRIBE
    `carga_gpu`, y su evento sale hacia `mitigar`, que es quien lo LEE. Así el
    test también falla si el campo se renombra en un lado y no en el otro.

    Pico 90.16 W, el 90.2 de la tabla del dictamen. Es un precursor de una
    muerte real de la máquina: exactamente lo que la mitigación debe frenar."""
    senal = _SenalFalsa()
    estado = {"en_alarma": set(), "inicio": {}, "mitigados": set()}

    alarmas = agt._alarmas(_zonas(VENTANA_PRECURSOR_CON_CARGA[-1][1]),
                           UMBRALES_ATOM, estado,
                           historial=_historial(VENTANA_PRECURSOR_CON_CARGA))
    criticas = [e for e in alarmas if e["evento"] == "temp_critica"]

    # zone0 y zone5, las dos a 96.5 °C -- las mismas dos filas del dictamen.
    assert [e["zona"] for e in criticas] == ["thermal_zone0", "thermal_zone5"]
    assert {e["carga_gpu"] for e in criticas} == {"con_carga"}
    assert {e["carga_gpu_pico_w"] for e in criticas} == {90.16}

    resultado = agt.mitigar(alarmas, estado, listar_pids=lambda: [111],
                            enviar_senal=senal)

    assert senal.llamadas == [(111, agt.signal.SIGSTOP)]
    assert [e["evento"] for e in resultado] == ["mitigacion_pausa"]


def test_limite_declarado_los_precursores_de_40w_no_pausan():
    """El límite de la compuerta, escrito como límite y no como bug. El cruce
    de las 02:59:27 precedió al MISMO crash que el de las 02:42:21, pero su
    ventana tiene el GPU a 40.03 W de pico, bajo `CARGA_MINIMA_W = 60.0`: sale
    `ocioso` y no pausa.

    No se emite `mitigacion_sin_datos` -- hay dato, y dice que no hay carga.
    Si alguna vez se re-mide `CARGA_MINIMA_W`, estos son los dos eventos que
    hay que mirar, y `carga_gpu_pico_w` viaja en el evento para poder mirarlos
    sin volver a replayar el log."""
    senal = _SenalFalsa()
    estado = {"en_alarma": set(), "inicio": {}, "mitigados": set()}

    alarmas = agt._alarmas(_zonas(VENTANA_PRECURSOR_40W[-1][1]),
                           UMBRALES_ATOM, estado,
                           historial=_historial(VENTANA_PRECURSOR_40W))
    criticas = [e for e in alarmas if e["evento"] == "temp_critica"]

    assert [e["zona"] for e in criticas] == ["thermal_zone0", "thermal_zone4"]
    assert {e["carga_gpu"] for e in criticas} == {"ocioso"}
    assert {e["carga_gpu_pico_w"] for e in criticas} == {40.03}
    assert agt.CARGA_MINIMA_W == 60.0  # el número que deja fuera a estos dos

    resultado = agt.mitigar(alarmas, estado, listar_pids=lambda: [111],
                            enviar_senal=senal)

    assert senal.llamadas == []
    assert resultado == []
