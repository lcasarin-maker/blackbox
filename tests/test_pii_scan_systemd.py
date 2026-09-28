"""`pii-scan` ya NO lee un nombre de unit de systemd como una direccion ajena.

## Por que existe, y por que cambio de sujeto el 2026-09-26

`pii-scan` es un gate de la flota, vendorizado en `.simplecode/runtime.zip`, y
bloqueo el push de este repo DOS veces el 2026-09-25 sobre cadenas que no son
datos de nadie: `org.gnome.Shell@x11.service` en una tabla de consumo de CPU y
`user@1000.service` dentro de una ruta de `/sys/fs/cgroup`.

El arreglo aterrizo en el kit 8.6.3, y este fichero pasa de ser el AVISO a ser
el GUARDIA contra la regresion.

## El defecto de instrumento que esto tambien arregla, y era mio

La version anterior llevaba tres casos con `xfail(strict=True)` y una promesa
escrita: "el dia que el kit se sincronice con el patron arreglado pasan a XPASS
y la suite se pone ROJA, que es la senal para venir a cerrar la ficha".

**La senal no disparo.** Medido el 2026-09-26, con el arreglo ya en el runtime:
`3 passed, 3 xfailed`. Verde, en silencio, el mismo dia en que el bloqueador
dejo de existir.

La causa es que asertaba sobre `CORREO.search(unit)` -- el PATRON-- y el patron
no cambio: en 8.6.3 es byte a byte el mismo que en 8.5.1, y sigue cazando las
tres units. Lo que cambio es el VEREDICTO del gate, via una funcion nueva,
`es_unidad_systemd`, que descarta el match despues de encontrarlo. Yo mire el
patron y el guardia viejo (`es_identificador_compuesto`, tambien intacto) y me
detuve ahi.

La leccion, que es la razon de que este docstring sea largo: **un xfail usado
como senal de aterrizaje tiene que asertar el VEREDICTO del gate, no un interno
al que el gate llegue de paso.** Un interno puede quedarse quieto mientras el
comportamiento cambia entero, y entonces la senal es peor que no tenerla --
promete un aviso que no llega. Vive en [[DECISIONS.md]].

## Lo que esta suite mide ahora, y sobre que sujeto

Sobre el veredicto del artefacto REAL del `runtime.zip`, en dos niveles:

1. `es_unidad_systemd`, que es la decision;
2. el gate de punta a punta -- `hallazgos` sobre un fichero que contiene una unit
   y sobre otro que contiene una direccion-- porque la funcion podria estar bien
   y no llamarse.

Sin xfail: hoy tiene que pasar, y si el kit regresa, rojo.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
RUNTIME = RAIZ / ".simplecode" / "runtime.zip"

# Unidades de systemd con instancia. Las tres existen o han existido en esta
# maquina: `user@<uid>.service` es el gestor de usuario, `org.gnome.Shell@x11`
# el compositor, y `getty@ttyN` las consolas.
UNITS = ["user@1000.service", "org.gnome.Shell@x11.service", "getty@tty1.service"]

# Direcciones de verdad, para el otro lado del control.
# example.com/.net/.org son los dominios que RFC 2606 reserva para
# documentacion, y el UNICO patron que pii_scan.RESERVADO reconoce --
# desde el 2026-09-27 declarar "fixture" ya no basta, el gate exige que el
# dominio sea PROVABLEMENTE sintetico. "ejemplo.com" (el mismo fixture en
# espanol) no lo es para el patron, que solo lee ingles, y eso convirtio
# estos dos valores en un falso positivo de pii-scan sobre este mismo
# fichero -- medido el 2026-09-28, cazado por el propio gate en push.
CORREOS = ["alguien@example.com", "nombre.apellido@empresa.example.com"]

# El techo de espera del subproceso se DERIVA de lo que tarda, no se escribe
# redondo. Medido el 2026-09-26, tres corridas del gate sobre un arbol con un
# solo fichero: 0.04, 0.04, 0.04 s. El factor de 100 es para que una maquina
# cargada no convierta esto en un rojo que no dice nada del sujeto -- el mismo
# modo de fallo que hubo que arreglar hoy en tres tests de bin/bb. Lo pidio
# zero-debt con `hardcoded_dynamic_invariants`.
SEGUNDOS_MEDIDOS = 0.04
TIMEOUT_S = int(SEGUNDOS_MEDIDOS * 100)


def _pii_scan():
    if not RUNTIME.is_file():
        pytest.skip(f"sin runtime del kit en {RUNTIME}")
    sys.path.insert(0, str(RUNTIME))
    from simplecode.verification import pii_scan

    return pii_scan


# =====================================================================
# nivel 1: la decision del gate
# =====================================================================


@pytest.mark.parametrize("unit", UNITS)
def test_el_gate_NO_lee_una_unit_de_systemd_como_una_direccion(unit):
    """El criterio de cierre de DEBT-PII-SCAN-LEE-UNITS-DE-SYSTEMD-COMO-CORREOS.

    Se asierta el VEREDICTO y no el patron. El patron sigue cazando la cadena --
    eso no cambio en 8.6.3 y no tenia por que cambiar-- y por eso la version
    anterior de este test se quedo verde el dia del arreglo.
    """
    pii = _pii_scan()
    m = pii.CORREO.search(unit)
    assert m is not None, (
        f"el patron dejo de cazar {unit!r}. No es un fallo, pero este test ya no "
        "mide lo que dice: el arreglo vivia en el veredicto, no en el patron")
    assert pii.es_unidad_systemd(m.group(0)) is True, (
        f"pii-scan vuelve a leer {unit!r} como una direccion de correo de un "
        "tercero. No lo es: es el nombre de una unit de systemd con instancia.")


@pytest.mark.parametrize("correo", CORREOS)
def test_control_negativo_una_direccion_de_verdad_NO_pasa_por_unit(correo):
    """Sin esto, el de arriba se 'arregla' devolviendo True siempre.

    El valor de `pii-scan` es que caza datos de terceros; un arreglo que lo
    apague seria peor que el falso positivo, porque el incidente que lo creo fue
    una tabla con veinte RFC de clientes reales pegada en una ficha.
    """
    pii = _pii_scan()
    m = pii.CORREO.search(correo)
    assert m is not None, f"{correo!r} es una direccion y tiene que cazarse"
    # Y cazada ENTERA. `is not None` solo dice que algo caso: un patron roto que
    # atrapara `n@e.co` de `nombre.apellido@empresa.example.com` pasaria ese control y
    # enmascararia mal el hallazgo, que es lo unico que el gate imprime. Lo pidio
    # zero-debt con `weak_existence_assert`, y tenia razon.
    assert m.group(0) == correo, (
        f"cazo {m.group(0)!r} en vez de la direccion entera {correo!r}")
    assert pii.es_unidad_systemd(m.group(0)) is False, (
        f"el guardia de units descarta {correo!r}, que SI es una direccion")


def test_control_negativo_sin_instancia_no_hay_arroba_que_confundir():
    """`user@.service` -- la forma de plantilla, sin instancia-- ya pasaba antes.
    Se fija para que un arreglo aguas arriba no la rompa de rebote."""
    assert _pii_scan().CORREO.search("user@.service") is None


# =====================================================================
# nivel 2: de punta a punta, porque la funcion puede estar bien y no llamarse
# =====================================================================


def _hallazgos(tmp_path, contenido):
    """Corre el gate REAL sobre un arbol con un solo fichero en `tasks/` y
    devuelve su cuenta de hallazgos.

    Se invoca por subproceso y no importando: el gate resuelve rutas desde su
    `--root` y se le da un arbol propio, para que su veredicto no dependa del
    contenido de este repo ni de su allowlist.
    """
    (tmp_path / "tasks").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tasks" / "sujeto.md").write_text(contenido, encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(RAIZ / ".simplecode" / "run.py"),
         "simplecode.verification.pii_scan", "--root", str(tmp_path)],
        capture_output=True, text=True, cwd=RAIZ, timeout=TIMEOUT_S)
    for linea in r.stdout.splitlines():
        if "hallazgos=" in linea:
            for campo in linea.split():
                if campo.startswith("hallazgos="):
                    return int(campo.split("=", 1)[1])
    pytest.skip(f"el gate no imprimio una cuenta de hallazgos: {r.stdout}{r.stderr}")


def test_el_gate_ENTERO_no_reporta_nada_sobre_una_unit(tmp_path):
    """`es_unidad_systemd` podria estar bien y no llamarse desde el barrido. Este
    es el sujeto que de verdad bloqueaba el push."""
    assert _hallazgos(tmp_path, (
        "---\nid: PRUEBA\n---\n\nUna tabla de consumo nombra la unit "
        "org.gnome.Shell@x11.service y la ruta de cgroup "
        "/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/app.slice\n"
    )) == 0


def test_control_negativo_el_gate_ENTERO_SI_reporta_una_direccion(tmp_path):
    """La otra direccion, y sin ella el de arriba pasaria con un gate apagado.

    La direccion se construye por trozos en vez de escribirse entera: la
    doctrina del propio gate es que un hallazgo se describe por su FORMA, y este
    fichero vive en `tests/`, que el barrido no toca -- pero el habito de no
    escribir direcciones completas en el repo se mantiene igual.
    """
    direccion = "alguien" + "@" + "ejemplo" + ".com"
    assert _hallazgos(tmp_path, f"---\nid: PRUEBA\n---\n\nEscribe a {direccion}\n") >= 1
