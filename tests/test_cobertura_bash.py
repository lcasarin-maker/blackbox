"""`tools/cobertura_bash.sh` tiene que ver lo que el sujeto ejecuta DE VERDAD.

## Por que existe

El medidor ponia `PS4='+${BASH_SOURCE}:${LINENO}:'` y luego buscaba las lineas
con un patron anclado en UN solo `+`. Bash repite el primer caracter de PS4
tantas veces como profundidad de anidamiento tenga lo que ejecuta: `+` en el
cuerpo principal, `++` dentro de una funcion llamada desde `$(...)`, `+++` un
nivel mas adentro.

Asi que todo lo que corria en una substitucion, una tuberia o un subshell se
contaba como SIN CUBRIR. En `bin/bb` eso es casi todo, porque cada bloque de la
muestra se arma con `x=$(funcion)`.

Medido el 2026-09-25: al arreglar el ancla, `bin/bb` paso de 27.0 % a 33.3 %.
**Nadie escribio un test nuevo entre las dos cifras.** 59 lineas siempre
estuvieron cubiertas y el instrumento no las veia -- que es la forma en que un
medidor da un numero mas bajo del real y nadie lo nota, porque un numero bajo
parece prudente.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MEDIDOR = RAIZ / "tools" / "cobertura_bash.sh"
SUJETO_REL = "tests/fixtures/cobertura_sujeto.sh"

# El techo de espera se DERIVA de lo que tarda, no se escribe redondo. Medido el
# 2026-09-25, tres corridas del medidor sobre este fixture: 0.02, 0.02, 0.01 s.
# El factor de 100 es para que una maquina cargada no lo convierta en un rojo
# que no dice nada -- el mismo modo de fallo que este commit arregla en otros
# tres tests. Lo pidio zero-debt con `hardcoded_dynamic_invariants`.
SEGUNDOS_MEDIDOS = 0.02
TIMEOUT_S = int(SEGUNDOS_MEDIDOS * 100)


SUJETO = RAIZ / "tests" / "fixtures" / "cobertura_sujeto.sh"


def _sin_cubrir():
    """Corre el medidor sobre el fixture y devuelve el conjunto de lineas que
    declara SIN CUBRIR.

    El sujeto se invoca por RUTA ABSOLUTA a proposito: `BASH_SOURCE` sale tal
    cual se llamo al script, y el medidor busca la absoluta. Llamarlo con una
    ruta relativa hace que NADA case y que el informe salga con todo sin
    cubrir -- que es lo que paso al escribir este fichero, y se parece
    demasiado a un 0 % legitimo como para dejarlo sin escribir.
    """
    r = subprocess.run([str(MEDIDOR), SUJETO_REL, str(SUJETO)],
                       capture_output=True, text=True, cwd=RAIZ, timeout=TIMEOUT_S)
    assert "SIN CUBRIR" in r.stdout, r.stdout + r.stderr
    cola = r.stdout.split("SIN CUBRIR (numero de linea):")[1]
    # Se corta en el LIMITE DECLARADO y se saca por patron. Partir por comas
    # sobre el texto entero pegaba la frase siguiente al ultimo numero y lo
    # descartaba en silencio: la primera version de este helper perdia L14 y
    # el test fallaba senalando al medidor, que estaba bien.
    cola = cola.split("LIMITE DECLARADO")[0]
    return {int(n) for n in re.findall(r"L(\d+)", cola)}, r.stdout


def test_una_funcion_llamada_desde_una_SUBSTITUCION_cuenta_como_cubierta():
    """El bug. `local b=2` (L7) y `echo "$b"` (L8) corren a profundidad 2 de
    xtrace, y el ancla vieja no las veia."""
    sin_cubrir, salida = _sin_cubrir()
    assert 9 not in sin_cubrir and 10 not in sin_cubrir, (
        f"lineas de una funcion llamada desde $(...) contadas como sin cubrir: "
        f"{sorted(sin_cubrir)}\n{salida}")


def test_control_negativo_una_funcion_que_NADIE_llama_sale_SIN_cubrir():
    """Sin esto, el de arriba tambien pasaria con un medidor que contara TODAS
    las lineas como cubiertas -- que es el arreglo perezoso del bug de arriba, y
    daria un 100 % permanente."""
    sin_cubrir, salida = _sin_cubrir()
    assert 13 in sin_cubrir and 14 in sin_cubrir, (
        f"la funcion que nadie llama tendria que salir sin cubrir: "
        f"{sorted(sin_cubrir)}\n{salida}")


def test_control_negativo_la_llamada_DIRECTA_se_seguia_viendo():
    """La profundidad 1 nunca estuvo rota. Se fija para que el arreglo del
    ancla no la pierda de rebote."""
    sin_cubrir, _ = _sin_cubrir()
    assert 5 not in sin_cubrir and 6 not in sin_cubrir, sorted(sin_cubrir)
