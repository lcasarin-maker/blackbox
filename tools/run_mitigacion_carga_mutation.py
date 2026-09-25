#!/usr/bin/env python3
"""Control de mutación de la compuerta de carga de `mitigar()` (DGX-408).

El arreglo que se prueba aquí es **una condición**, y una condición rota no
produce errores: produce silencio. Esa es exactamente la falla que la ficha
vino a cerrar y la que este control tiene que poder ver -- si la compuerta
quedara leyendo un campo que nadie escribe, `mitigar()` no pausaría nunca y el
jsonl mostraría **cero `mitigacion_pausa`**, que es dígito por dígito lo mismo
que muestra cuando la compuerta funciona y filtra el 72% de ruido medido. Un
test que sólo compruebe "ya no pausa en ocioso" pasa con la mitigación
completamente muerta.

Las cuatro mutaciones son las cuatro formas de matarla que el encargo nombró:
la condición invertida, la pausa incondicional (o sea el estado anterior a
DGX-408), la ausencia del campo tratada como `con_carga`, y la ausencia
tratada como `ocioso` sin emitir el evento que la delata.

La maquinaria (corrida sana primero, muerte SÓLO por `failed` y nunca por
`error`, `compile()` antes de gastar máquina, flock global + del árbol,
restauración verificada por sha256 y árbol limpio exigido antes de tocar nada)
se reusa TAL CUAL de `tools/run_injection_mutation.py`, igual que hacen
`run_alarm_mark_mutation.py` y `run_grep_scope_mutation.py`.

    python tools/run_mitigacion_carga_mutation.py   # la suite objetivo tarda ~4 s
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_injection_mutation import correr

REPO = Path(__file__).resolve().parent.parent
ARTIFACT = REPO / "logs" / "mutacion_mitigacion_carga.txt"

TESTS = ["tests/test_mitigacion_solo_con_carga.py",
         "tests/test_atom_gpu_telemetry.py"]

AGT = "tools/atom_gpu_telemetry.py"

# Los anclajes literales del cuerpo de `mitigar()`. Van con su sangría de 4
# espacios, que es lo que los hace únicos en el archivo.
FILTRO = ('    con_carga = [e for e in criticas '
          'if e.get("carga_gpu") == "con_carga"]')
DISPARO = "    if con_carga and not mitigados:"
OPACAS = ('    opacas = [e for e in criticas\n'
          '              if e.get("carga_gpu") in (None, "sin_datos")]')

MUTACIONES: list[dict] = [
    {"id": "condicion_invertida", "archivo": AGT,
     "viejo": FILTRO,
     "nuevo": ('    con_carga = [e for e in criticas '
               'if e.get("carga_gpu") != "con_carga"]'),
     "rompe": "la compuerta al revés: el pico ocioso de 14.11 W de las 00:43:17 "
              "recibiría el SIGSTOP y los 10 precursores de 61 a 90 W del quinto "
              "crash pasarían de largo -- peor que no tener compuerta, porque "
              "para el ruido sí actúa"},

    {"id": "pausa_siempre", "archivo": AGT,
     "viejo": DISPARO,
     "nuevo": "    if criticas and not mitigados:",
     "rompe": "el estado anterior a DGX-408, literal: pausa sobre el evento crudo, "
              "que es ruido 3 de cada 4 veces. Es la mutación que un test escrito "
              "sólo del lado negativo dejaría viva"},

    {"id": "ausencia_tratada_como_con_carga", "archivo": AGT,
     "viejo": FILTRO,
     "nuevo": ('    con_carga = [e for e in criticas '
               'if e.get("carga_gpu", "con_carga") == "con_carga"]'),
     "rompe": "un evento anterior a DGX-396 dispararía la pausa como si trajera "
              "carga medida: la compuerta se vuelve permisiva justo donde no sabe, "
              "que es lo contrario de lo que hace el resto del módulo"},

    {"id": "ausencia_tratada_como_ocioso_sin_evento", "archivo": AGT,
     "viejo": OPACAS,
     "nuevo": "    opacas = []",
     "rompe": "LA MUTACIÓN QUE DEFINE LA FICHA: no pausa y no dice nada. Si el "
              "campo dejara de escribirse, la mitigación quedaría desactivada "
              "produciendo el MISMO cero que produce cuando funciona, y no habría "
              "forma de distinguir «filtró bien» de «no corre»"},
]


def main() -> int:
    return correr(MUTACIONES, TESTS, ARTIFACT)


if __name__ == "__main__":
    raise SystemExit(main())
