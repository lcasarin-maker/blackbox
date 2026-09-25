#!/usr/bin/env python3
"""Control de mutación de la marca de corroboración del evento `temp_critica`
(DGX-396).

Un test que pasa igual con el código roto no prueba nada, y aquí eso importa
por la misma razón que en DGX-160: el defecto que se arregló **no producía
errores**. `_alarmas` escribía su evento con toda la calma del mundo mientras
`presupuesto_termico` -- leyendo el MISMO sensor, en el MISMO módulo -- decía
lo contrario, y las dos cosas convivieron un día entero sin que nada fallara.
Una marca decorativa aquí se vería idéntica a una que muerde hasta que
costara otro dictamen de 122 eventos leídos a mano.

Las mutaciones de abajo rompen, una por una, las piezas del arreglo: la marca
invertida, la marca clavada en cada uno de sus dos veredictos útiles, el
criterio propio que deja de seguir al gate, los campos borrados, el parámetro
`historial` ignorado, y -- la que contradice el voto de Luis directamente --
el evento suprimido cuando la marca no corrobora. Cada una exige que la suite
MUERA.

La maquinaria (corrida sana primero, muerte SÓLO por `failed` y nunca por
`error`, `compile()` antes de gastar máquina, flock global + del árbol,
restauración verificada por sha256 y árbol limpio exigido antes de tocar nada)
se reusa TAL CUAL de `tools/run_injection_mutation.py`, igual que hicieron
`run_grep_scope_mutation.py` y `run_pool_mutation.py`.

    python tools/run_alarm_mark_mutation.py     # la suite objetivo tarda ~7 s
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_injection_mutation import correr

REPO = Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "logs" / "mutacion_alarm_mark.txt"

TESTS = ["tests/test_presupuesto_termico.py", "tests/test_atom_gpu_telemetry.py"]

AGT = "tools/atom_gpu_telemetry.py"

# El bloque real, con su sangría de 12 espacios -- que es lo que lo hace único
# frente al bloque gemelo de `presupuesto_termico`, sangrado a 4.
MARCA = '                            "corroboracion": veredicto,\n'
LLAMADA = ("            veredicto, detalle, carga, pico = _corroboracion("
           "historial,\n                                                 "
           "            umbrales)")
APPEND = '            eventos.append({**base, "evento": "temp_critica",'

# --- seguimiento de DGX-396: la pierna de CARGA, expuesta aparte ------------
# La marca completa mide otra cosa en el flanco (3 `corrobora` contra 121
# `descarta` sobre el log real), y la pierna de carga sí es conocible ahí: 34
# `con_carga` contra 90 `ocioso`, y **10 de los 12 precursores del quinto
# crash** que la marca descartaba. Las mutaciones de abajo rompen esa pierna
# por sus tres vías: invertida, clavada, y —la que contradice la condición que
# Luis pegó al voto— leída de una fuente propia en vez de `_corroboracion`.
PIERNA = ('    return (("con_carga" if pico >= CARGA_MINIMA_W else "ocioso"), '
          'pico)')
CAMPOS_CARGA = ('                            "carga_gpu": carga,\n'
                '                            "carga_gpu_pico_w": pico})')

MUTACIONES: list[dict] = [
    # --- la marca dice lo contrario de lo que mide ------------------------
    {"id": "marca_invertida", "archivo": AGT,
     "viejo": MARCA,
     "nuevo": '                            "corroboracion": ("descarta"\n'
              '                                if veredicto == "corrobora"\n'
              '                                else "corrobora"),\n',
     "rompe": "el episodio real de DGX-342 (61-90 W) saldría marcado como ruido "
              "y el pico ocioso como evento térmico: peor que no marcar"},
    {"id": "marca_clavada_en_corrobora", "archivo": AGT,
     "viejo": MARCA,
     "nuevo": '                            "corroboracion": "corrobora",\n',
     "rompe": "marca decorativa: el 72% de ruido medido pasaría a llamarse "
              "evento térmico corroborado, que es la mentira más cara de las dos"},
    {"id": "marca_clavada_en_descarta", "archivo": AGT,
     "viejo": MARCA,
     "nuevo": '                            "corroboracion": "descarta",\n',
     "rompe": "la otra marca decorativa: los 6 cruces que precedieron al quinto "
              "crash quedarían indistinguibles de un pico del sensor"},

    # --- el criterio deja de ser el del gate ------------------------------
    {"id": "criterio_propio_en_vez_de_corroboracion", "archivo": AGT,
     "viejo": LLAMADA,
     "nuevo": '            veredicto, detalle, carga, pico = (\n'
              '                ("corrobora" if historial else "sin_datos"), "",\n'
              '                "con_carga", 99.0)',
     "rompe": "EXACTAMENTE el defecto que esta ficha cierra: un segundo criterio "
              "de «temperatura alta» que hoy coincide y mañana no -- ya no mira "
              "`CARGA_MINIMA_W` ni `DEBOUNCE_MUESTRAS`, así que el gate podría "
              "moverse sin que la marca se entere"},
    {"id": "historial_del_parametro_ignorado", "archivo": AGT,
     "viejo": "            if historial is None:",
     "nuevo": "            if True:",
     "rompe": "el pasado lo decidiría siempre el jsonl de la máquina donde corra "
              "la suite en vez del que fija el llamador: la marca deja de ser "
              "probable y hereda la temperatura ambiente"},

    # --- la marca desaparece ----------------------------------------------
    {"id": "campos_de_marca_borrados", "archivo": AGT,
     "viejo": '"evento": "temp_critica",\n'
              '                            "corroboracion": veredicto,\n'
              '                            "corroboracion_detalle": detalle,',
     "nuevo": '"evento": "temp_critica",',
     "rompe": "vuelve al estado previo a DGX-396: el evento que la gente lee no "
              "dice nada de si el gate lo respaldaba"},

    # --- el voto de Luis, contradicho directamente -------------------------
    {"id": "evento_suprimido_si_no_corrobora", "archivo": AGT,
     "viejo": APPEND,
     "nuevo": '            if veredicto != "descarta":\n'
              '                eventos.append({**base, "evento": "temp_critica",',
     "rompe": "lo que Luis votó EN CONTRA el 2026-09-01: suprimir el pico impide "
              "volver a estudiar el ruido, que es lo que hizo medible a DGX-383. "
              "El productor informa; quien consume decide"},

    # --- la pierna de carga dice lo contrario de lo que mide ---------------
    {"id": "pierna_de_carga_invertida", "archivo": AGT,
     "viejo": PIERNA,
     "nuevo": '    return (("ocioso" if pico >= CARGA_MINIMA_W else "con_carga"), '
              'pico)',
     "rompe": "los 10 precursores del quinto crash (61 a 90 W) saldrían `ocioso` y "
              "los picos del sensor `con_carga`: la mitigación de DGX-342 leería "
              "exactamente al revés de lo que pasó"},
    {"id": "pierna_de_carga_clavada_en_con_carga", "archivo": AGT,
     "viejo": PIERNA,
     "nuevo": '    return ("con_carga", pico)',
     "rompe": "pierna decorativa: los 90 eventos ociosos medidos pasarían a "
              "llamarse carga real, y el 28% de señal dejaría de ser señal porque "
              "todo valdría igual"},
    {"id": "pierna_de_carga_clavada_en_ocioso", "archivo": AGT,
     "viejo": PIERNA,
     "nuevo": '    return ("ocioso", pico)',
     "rompe": "la otra pierna decorativa, y la que borra el encargo: los 12 "
              "precursores volverían a ser indistinguibles del ruido, que es "
              "justo lo que esta ficha vino a arreglar"},
    {"id": "sin_datos_de_carga_colapsado_en_ocioso", "archivo": AGT,
     "viejo": '        return ("sin_datos", None)',
     "nuevo": '        return ("ocioso", None)',
     "rompe": "«el sampler dejó de escribir gpu_power_w» se leería como «el GPU "
              "está quieto» -- la misma confusión que DGX-383 deshizo, reabierta "
              "en el campo nuevo"},

    # --- la pierna deja de salir del criterio del gate ---------------------
    {"id": "pierna_de_carga_de_fuente_propia", "archivo": AGT,
     "viejo": LLAMADA,
     "nuevo": "            veredicto, detalle, _c, pico = _corroboracion(historial,\n"
              "                                                         umbrales)\n"
              "            _w = [m['gpu_power_w'] for m in historial\n"
              "                  if isinstance(m.get('gpu_power_w'), (int, float))]\n"
              "            carga = ('sin_datos' if not _w else\n"
              "                     ('con_carga' if max(_w) >= 60.0 else 'ocioso'))",
     "rompe": "LA CONDICIÓN QUE LUIS PEGÓ AL VOTO: una segunda lectura de la "
              "potencia con su propio 60.0 copiado. Hoy coincide dígito a dígito "
              "con la de `_corroboracion` y mañana no -- mover `CARGA_MINIMA_W` "
              "movería el gate y dejaría el campo donde estaba, que es la "
              "divergencia que DGX-396 vino a cerrar"},

    # --- la pierna desaparece del evento -----------------------------------
    {"id": "campos_de_carga_borrados", "archivo": AGT,
     "viejo": CAMPOS_CARGA,
     "nuevo": "                            })",
     "rompe": "vuelve al estado de DGX-396: quien lee el log para ver qué precedió "
              "a un crash sólo tiene el 97.5% de `descarta` y ninguna forma de "
              "separar los 34 episodios con carga de los 90 ociosos"},
    {"id": "pico_de_carga_no_viaja", "archivo": AGT,
     "viejo": '                            "carga_gpu_pico_w": pico})',
     "nuevo": '                            "carga_gpu_pico_w": None})',
     "rompe": "el veredicto se calcula contra la `CARGA_MINIMA_W` del día en que "
              "se escribió; sin el número crudo un evento viejo deja de poder "
              "releerse si la constante se re-mide, y esa relectura es la que "
              "produjo esta ficha"},
]


def main() -> int:
    return correr(MUTACIONES, TESTS, ARTIFACT)


if __name__ == "__main__":
    raise SystemExit(main())
