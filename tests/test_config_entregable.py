"""Suite de `tools/config_entregable.sh`.

El script sostiene el `close_check` de
DEBT-CONFIG-ADOPTADA-QUE-NINGUN-SCRIPT-INSTALA, y por eso tiene suite: un
criterio de cierre apoyado en un script sin probar es un eslabon que no avisa
cuando se rompe.

Lo que se mide sobre todo es que el veredicto pueda salir en las DOS
direcciones. Un comprobador que sumara ficheros sin poder llegar nunca a cero
seria un cero perpetuo disfrazado de vigilancia -- exactamente el defecto que
esta ficha describe en `bb drift`, que reporta divergencias sin remedio.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "tools" / "config_entregable.sh"


def corre(raiz: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(raiz / "tools" / "config_entregable.sh")],
                          capture_output=True, text=True, timeout=60)


def _repo(tmp_path: Path, adoptados: dict[str, str], instalador: str,
          solo_registro: str | None = None) -> Path:
    (tmp_path / "tools").mkdir(parents=True, exist_ok=True)
    (tmp_path / "tools" / "config_entregable.sh").write_text(
        SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
    d = tmp_path / "adopted" / "system-config"
    d.mkdir(parents=True, exist_ok=True)
    for n, c in adoptados.items():
        (d / n).write_text(c, encoding="utf-8")
    (tmp_path / "enable-privileged.sh").write_text(instalador, encoding="utf-8")
    if solo_registro is not None:
        (tmp_path / "adopted" / "solo-registro.txt").write_text(
            solo_registro, encoding="utf-8")
    return tmp_path


def test_todos_instalados_sale_a_favor(tmp_path):
    r = corre(_repo(tmp_path, {"etc_uno.conf": "x", "etc_dos.conf": "y"},
                    "run cp adopted/system-config/etc_uno.conf /etc/uno\n"
                    "run cp adopted/system-config/etc_dos.conf /etc/dos\n"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OK:" in r.stdout


def test_uno_sin_camino_bloquea_y_lo_NOMBRA(tmp_path):
    """No basta con contar: un informe que dice '1 hueco' sin decir cual obliga
    a buscarlo a mano, que es lo que esta ficha existe para evitar."""
    r = corre(_repo(tmp_path, {"etc_uno.conf": "x", "etc_huerfano.conf": "y"},
                    "run cp adopted/system-config/etc_uno.conf /etc/uno\n"))
    assert r.returncode == 1
    assert "etc_huerfano.conf" in r.stdout
    assert "etc_uno.conf" not in r.stdout.split("adoptados:")[0], (
        "el que SI tiene instalador no se puede reportar como hueco")


def test_declararlo_solo_registro_lo_exime(tmp_path):
    """La segunda salida del cierre: no instalarlo es legitimo si se escribe por que."""
    ad = {"etc_uno.conf": "x", "etc_ajeno.conf": "y"}
    inst = "run cp adopted/system-config/etc_uno.conf /etc/uno\n"
    assert corre(_repo(tmp_path, ad, inst)).returncode == 1
    r = corre(_repo(tmp_path, ad, inst,
                    "etc_ajeno.conf  lo instala el paquete del fabricante\n"))
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("quita,porque", [
    ("adopted", "sin el directorio de adoptados no hay sujeto que auditar"),
    ("enable-privileged.sh", "sin instalador no se puede saber que instala"),
])
def test_falta_el_sujeto_es_COULD_NOT_RUN_y_no_un_veredicto(tmp_path, quita, porque):
    """La tercera salida. Un comprobador con dos salidas leeria 'falta el
    directorio' como 'todo cubierto' o como 'todo roto', y las dos mienten."""
    raiz = _repo(tmp_path, {"etc_uno.conf": "x"}, "run cp ...etc_uno.conf\n")
    p = raiz / quita
    if p.is_dir():
        import shutil
        shutil.rmtree(p)
    else:
        p.unlink()
    r = corre(raiz)
    assert r.returncode == 2, porque
    assert "COULD_NOT_RUN" in r.stdout


def test_un_directorio_dentro_de_adoptados_no_cuenta_como_fichero(tmp_path):
    raiz = _repo(tmp_path, {"etc_uno.conf": "x"},
                 "run cp adopted/system-config/etc_uno.conf /etc/uno\n")
    (raiz / "adopted" / "system-config" / "subdir").mkdir()
    r = corre(raiz)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "adoptados: 1" in r.stdout


# --------------------------- que el instalador COPIE, no que solo lo mencione
#
# `config_entregable.sh` busca el NOMBRE del fichero dentro del instalador, y
# ese es su limite declarado: un comentario que lo nombre sin llegar a copiarlo
# pasaria igual. Con once ficheros anadidos al instalador el 2026-09-28 para
# cerrar la ficha, ese limite dejo de ser teorico -- si manana alguien borra un
# `cp` y deja el comentario, el comprobador seguiria diciendo OK.
#
# Estos dos tests lo cierran leyendo lo que el instalador DICE QUE HARIA en vez
# de lo que menciona: `--dry-run` no necesita root y tarda 0.03, 0.03 y 0.04 s
# en tres corridas medidas hoy.

SEGUNDOS_DRY_RUN = 0.04
TIMEOUT_DRY_S = int(SEGUNDOS_DRY_RUN * 100)

INSTALADOR = RAIZ / "enable-privileged.sh"
ADOPTADOS = RAIZ / "adopted" / "system-config"
DECLARADOS = RAIZ / "adopted" / "solo-registro.txt"
MARCA = "[dry-run] cp adopted/system-config/"


def copiados(salida: str) -> set[str]:
    """Los ficheros que el dry-run dice que copiaria desde `adopted/`."""
    nombres = set()
    for linea in salida.splitlines():
        i = linea.find(MARCA)
        if i != -1:
            nombres.add(linea[i + len(MARCA):].split()[0])
    return nombres


def sin_camino(salida: str) -> set[str]:
    """Adoptados que ni se copian ni estan declarados solo-registro.

    La pertenencia a la declaracion se mira por subcadena, igual que hace
    `grep -qF` en el comprobador: si los dos criterios divergieran, el gate y su
    test dirian cosas distintas sobre el mismo repo.
    """
    declarados = (DECLARADOS.read_text(encoding="utf-8")
                  if DECLARADOS.exists() else "")
    hechos = copiados(salida)
    return {f.name for f in ADOPTADOS.iterdir()
            if f.is_file() and f.name not in hechos and f.name not in declarados}


@pytest.fixture(scope="module")
def dry_run() -> str:
    r = subprocess.run([str(INSTALADOR), "--dry-run"], capture_output=True,
                       text=True, cwd=RAIZ, timeout=TIMEOUT_DRY_S)
    assert r.returncode == 0, (
        "el dry-run del instalador no llego a correr. Eso es COULD_NOT_RUN, no "
        "un veredicto: un instrumento caido no prueba que el sujeto este "
        f"limpio.\n{r.stdout}{r.stderr}")
    return r.stdout


def test_el_instalador_COPIA_cada_adoptado_no_solo_lo_nombra(dry_run):
    faltan = sin_camino(dry_run)
    assert not faltan, (
        "adoptados que el instalador NO copia y que tampoco estan declarados en "
        f"adopted/solo-registro.txt: {sorted(faltan)}")


def test_control_negativo_quitar_un_cp_lo_delata(dry_run):
    """Sin esto, el de arriba pasaria con un lector que devolviera siempre todo.

    Se le quita a la salida la linea que copia UN fichero y se comprueba que
    sale ese y solo ese.
    """
    victima = "etc_sysctl.d_99-sysrq.conf"
    assert victima in copiados(dry_run), "la victima elegida ya no se copia"
    mutilada = "\n".join(l for l in dry_run.splitlines()
                         if f"{MARCA}{victima}" not in l)
    assert sin_camino(mutilada) == {victima}
