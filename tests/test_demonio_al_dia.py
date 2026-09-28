"""Suite de `tools/demonio_al_dia.sh`.

El script sostiene el `close_check` de
DEBT-UNA-BAJADA-MOMENTANEA-ABSUELVE-UN-COLAPSO, y por eso tiene suite: un
criterio de cierre que se apoya en un script sin probar es un eslabon que no
avisa cuando se rompe.

Lo que de verdad se mide aqui es la TERCERA salida. Un chequeo con dos salidas
habria leido una unit parada como "corre codigo viejo", y eso es un
COULD_NOT_RUN disfrazado de veredicto negativo -- el primer modo de fallo de la
lista de la casa. El primer intento de este chequeo, escrito como one-liner,
tenia exactamente ese defecto: `ExecMainStartTimestampUSec` no existe en el
systemd de esta maquina, devolvia cadena vacia, y `test "" -gt N` fallaba, con
lo que el veredicto salia "viejo" por ceguera.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "tools" / "demonio_al_dia.sh"

# Medido el 2026-09-27, tres corridas: 0.02, 0.02, 0.03 s. El factor de 100 es
# para que una maquina cargada no convierta esto en un rojo que no dice nada
# del sujeto. Lo pide zero-debt con `hardcoded_dynamic_invariants`.
SEGUNDOS_MEDIDOS = 0.03
TIMEOUT_S = int(SEGUNDOS_MEDIDOS * 100)

UNIT = "bb-usable.service"


def _correr(*args):
    return subprocess.run([str(SCRIPT), *args], capture_output=True, text=True,
                          cwd=RAIZ, timeout=TIMEOUT_S)


def _hay_unit():
    if not shutil.which("systemctl"):
        return False
    r = subprocess.run(["systemctl", "show", UNIT, "-p",
                        "ExecMainStartTimestamp", "--value"],
                       capture_output=True, text=True, timeout=TIMEOUT_S)
    return bool(r.stdout.strip())


necesita_unit = pytest.mark.skipif(
    not _hay_unit(), reason=f"{UNIT} no esta corriendo en esta maquina")


# ------------------------------------ las tres salidas


@necesita_unit
def test_codigo_mas_nuevo_que_el_proceso_sale_1(tmp_path):
    """El caso que importa: el arreglo esta en disco y el demonio no lo carga.

    Se fabrica tocando un fichero AHORA, que es por definicion posterior a
    cualquier arranque ya ocurrido.
    """
    nuevo = tmp_path / "recien-tocado.sh"
    nuevo.write_text("#!/bin/sh\n", encoding="utf-8")
    r = _correr(UNIT, str(nuevo))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "codigo VIEJO" in r.stdout
    assert "systemctl restart" in r.stdout, (
        "un veredicto negativo sin el comando que lo arregla obliga a quien lo "
        "lea a ir a buscarlo")


@necesita_unit
def test_control_positivo_codigo_mas_viejo_que_el_proceso_sale_0(tmp_path):
    """La otra direccion, y sin ella el de arriba pasaria con un script que
    devolviera 1 siempre."""
    viejo = tmp_path / "antiguo.sh"
    viejo.write_text("#!/bin/sh\n", encoding="utf-8")
    # 1970: mas viejo que cualquier arranque posible de esta maquina.
    os.utime(viejo, (0, 0))
    r = _correr(UNIT, str(viejo))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "despues de la ultima modificacion" in r.stdout


def test_unit_inexistente_es_COULD_NOT_RUN_y_no_un_veredicto():
    """2, no 1. "No se pudo medir" y "corre codigo viejo" son cosas distintas, y
    confundirlas es lo que hace que un instrumento caido parezca un sujeto
    roto."""
    r = _correr("no-existe-jamas-esta-unit.service", "bin/bb")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "COULD_NOT_RUN" in r.stderr


def test_fichero_inexistente_es_COULD_NOT_RUN():
    r = _correr(UNIT, "bin/no-existe-este-fichero")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "COULD_NOT_RUN" in r.stderr


def test_sin_argumentos_falla_en_vez_de_adivinar():
    """`set -u` con `${1:?}`: sin sujeto no hay veredicto que dar."""
    r = _correr()
    assert r.returncode != 0
    assert "uso:" in (r.stdout + r.stderr)


# ------------------------------------ el sujeto real de la ficha


@necesita_unit
def test_el_sujeto_de_la_ficha_se_puede_medir():
    """No se asierta el veredicto -- es 1 antes del restart y 0 despues, y las
    dos cosas son estados legitimos de la maquina. Lo que se asierta es que el
    chequeo LLEGA a un veredicto en vez de a COULD_NOT_RUN, porque un
    close_check que solo sabe decir "no pude" nunca cerraria la ficha."""
    r = _correr(UNIT, "bin/bb-usable")
    assert r.returncode in (0, 1), (
        f"COULD_NOT_RUN sobre el sujeto real:\n{r.stdout}{r.stderr}")


# ------------------------------------ --user: unit del gestor de usuario


@necesita_unit
def test_flag_user_es_transparente_para_el_caso_positivo(tmp_path):
    """Sin --user esta unit es de SISTEMA, asi que --user apuntandole a ella
    debe fallar por ausencia (COULD_NOT_RUN), no dar un falso positivo --
    prueba que el flag de verdad cambia el namespace consultado y no es un
    adorno que systemctl ignora."""
    r = _correr("--user", UNIT, "bin/bb")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "COULD_NOT_RUN" in r.stderr


def test_sin_flag_uso_menciona_el_flag_opcional():
    r = _correr()
    assert r.returncode != 0
    assert "--user" in (r.stdout + r.stderr)
