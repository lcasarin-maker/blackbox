"""El patron de correo de `pii-scan` caza nombres de unit de systemd.

## Por que existe este fichero

`pii-scan` es un gate de la flota, vendorizado en `.simplecode/runtime.zip`, y
bloqueo el push de este repo DOS veces el 2026-09-25 sobre cadenas que no son
datos de nadie:

    org.gnome.Shell@x11.service   -- en una tabla de consumo de CPU
    user@1000.service             -- dentro de una ruta de /sys/fs/cgroup

Su patron es `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}`, y una unit de
systemd con instancia lo casa igual que una direccion: local, arroba,
"dominio", punto, "tld". Mirando solo la cadena no hay forma de distinguirlas.

El coste inmediato esta pagado con `tasks/pii_allow.txt`, que es el mecanismo
sancionado y versionado. Lo que queda abierto es que el patron caza la CLASE
entera: cada unit con instancia que cualquier satelite documente habra que
declararla a mano, una a una, y el que no lo sepa leera "dato personal de
terceros" sobre el nombre de un servicio.

## Lo que esta suite mide, y sobre que sujeto

Sobre el artefacto REAL que corre en el gate -- el modulo dentro de
`runtime.zip`-- no sobre una copia del patron escrita aqui. Una copia probaria
que yo se escribir el mismo regex, no que el gate se comporte de una forma.

Por eso el positivo de abajo FALLA hoy: es el criterio de cierre de
`DEBT-PII-SCAN-LEE-UNITS-DE-SYSTEMD-COMO-CORREOS` y pasa cuando el arreglo
aterrice aguas arriba, en simplecode.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RUNTIME = Path(__file__).resolve().parent.parent / ".simplecode" / "runtime.zip"

# Unidades de systemd con instancia. Las tres existen o han existido en esta
# maquina: `user@<uid>.service` es el gestor de usuario, `org.gnome.Shell@x11`
# el compositor, y `getty@ttyN` las consolas.
UNITS = ["user@1000.service", "org.gnome.Shell@x11.service", "getty@tty1.service"]

# Direcciones de verdad, para el otro lado del control.
CORREOS = ["alguien@ejemplo.com", "nombre.apellido@empresa.com.mx"]


def _correo():
    if not RUNTIME.is_file():
        pytest.skip(f"sin runtime del kit en {RUNTIME}")
    sys.path.insert(0, str(RUNTIME))
    from simplecode.verification import pii_scan

    return pii_scan.CORREO


@pytest.mark.xfail(strict=True, reason=(
    "DEBT-PII-SCAN-LEE-UNITS-DE-SYSTEMD-COMO-CORREOS: el arreglo va aguas "
    "arriba, en simplecode. `strict=True` a proposito -- el dia que el kit se "
    "sincronice con el patron arreglado, esto pasa a XPASS y la suite se pone "
    "ROJA. Eso es la senal, no un fastidio: un xfail no estricto se quedaria "
    "verde para siempre y la ficha envejeceria sin que nadie lo notara."))
@pytest.mark.parametrize("unit", UNITS)
def test_una_unit_de_systemd_NO_es_una_direccion_de_correo(unit):
    """Mide el patron del artefacto REAL que corre en el gate, no una copia
    escrita aqui: una copia probaria que se escribir el mismo regex.

    Cuando el arreglo aterrice, este fichero pasa de ser el aviso a ser el
    guardia contra la regresion en la siguiente sincronizacion del kit -- el
    mismo papel que `tools/mutacion_alcanza.py` juega para el runner de
    mutacion.
    """
    assert _correo().search(unit) is None, (
        f"pii-scan lee {unit!r} como una direccion de correo de un tercero. "
        "No lo es: es el nombre de una unit de systemd con instancia.")


@pytest.mark.parametrize("correo", CORREOS)
def test_control_negativo_una_direccion_de_verdad_SI_se_caza(correo):
    """Sin esto, el de arriba se 'arregla' vaciando el patron.

    El valor de `pii-scan` es que caza datos de terceros; un arreglo que lo
    apague seria peor que el falso positivo, porque el incidente que lo creo
    fue una tabla con veinte RFC de clientes reales pegada en una ficha.
    """
    m = _correo().search(correo)
    assert m is not None, f"{correo!r} es una direccion y tiene que cazarse"
    # Y cazada ENTERA. `is not None` solo dice que algo caso: un patron roto
    # que atrapara `n@e.co` de `nombre.apellido@empresa.com.mx` pasaria ese
    # control y enmascararia mal el hallazgo, que es lo unico que el gate
    # imprime. Lo pidio zero-debt con `weak_existence_assert`, y tenia razon.
    assert m.group(0) == correo, (
        f"cazo {m.group(0)!r} en vez de la direccion entera {correo!r}")


def test_control_negativo_sin_instancia_no_hay_arroba_que_confundir():
    """`user@.service` -- la forma de plantilla, sin instancia-- ya pasa hoy.
    Se fija para que un arreglo aguas arriba no la rompa de rebote."""
    assert _correo().search("user@.service") is None
