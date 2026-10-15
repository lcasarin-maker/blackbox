"""close_check de DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01: la clasificacion escrita de cada corte.

El close_check anterior era `grep -q . clasificacion.md`, que acepta cualquier archivo con un
byte (medido el 2026-10-14: un archivo con la palabra "basura" sale rc=0). Este exige, para cada
uno de los tres cortes del titulo, una seccion `### Corte <fecha> (boot <id>)` con el boot
correcto, la clasificacion INDETERMINADA, una linea de evidencia y una de lo que falta que
nombre las dos fichas de salida; y la marca `clasificacion_indeterminada_declarada`. Las pruebas
de abajo son sus controles negativos: un archivo vacio, una sola linea o una seccion incompleta
lo hacen fallar.

El archivo es `.txt` y no el `.md` que nombraba el close_check viejo: ledger-schema trata un
`.md` dentro de una carpeta de evidencia como una ficha sin gobernar (COULD_NOT_RUN).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
CLASIFICACION = RAIZ / "tasks/evidence/DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01/clasificacion.txt"
MARCA = "clasificacion_indeterminada_declarada"
# Los tres cortes del titulo de la ficha y su boot, de `bb reboots` y `journalctl --list-boots`.
CORTES = {"06-oct": "36ebc0d9", "07-oct": "0de3e072", "08-oct": "e651544a"}
SALIDAS = ("FEATURE-MEDIDOR-DE-ENERGIA-EXTERNO-01", "FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01")


def _secciones(texto: str) -> dict[str, str]:
    """Cuerpo de cada `### Corte <fecha> ...`, hasta el siguiente encabezado."""
    partes = re.split(r"^(### Corte .*)$", texto, flags=re.M)
    return {partes[i]: partes[i + 1] for i in range(1, len(partes) - 1, 2)}


def faltas(texto: str) -> list[str]:
    """Lo que le falta a una clasificacion para cerrar la ficha; vacia si cumple."""
    out = [] if MARCA in texto else [f"falta la marca {MARCA}"]
    secciones = _secciones(texto)
    for fecha, boot in CORTES.items():
        cuerpo = next((c for t, c in secciones.items() if t.startswith(f"### Corte {fecha} ")), None)
        if cuerpo is None:
            out.append(f"{fecha}: sin seccion '### Corte {fecha} (boot {boot})'")
            continue
        titulo = next(t for t in secciones if t.startswith(f"### Corte {fecha} "))
        if boot not in titulo:
            out.append(f"{fecha}: la seccion no nombra el boot {boot}")
        if "Clasificacion: INDETERMINADA (energia o hardware interno)" not in cuerpo:
            out.append(f"{fecha}: sin 'Clasificacion: INDETERMINADA (energia o hardware interno)'")
        if not re.search(r"^- Evidencia: \S.{40,}", cuerpo, re.M):
            out.append(f"{fecha}: sin linea '- Evidencia:' con contenido")
        falta = re.search(r"^- Falta: .*$", cuerpo, re.M)
        if falta is None or not all(s in falta.group(0) for s in SALIDAS):
            out.append(f"{fecha}: la linea '- Falta:' no nombra {', '.join(SALIDAS)}")
    return out


def test_la_clasificacion_real_cubre_los_tres_cortes() -> None:
    assert faltas(CLASIFICACION.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    "texto",
    ["", "basura\n", f"{MARCA}\n", f"INDETERMINADA {MARCA} 06-oct 07-oct 08-oct\n"],
    ids=["vacio", "basura", "solo-la-marca", "una-linea-con-todo"],
)
def test_rechaza_archivos_que_el_grep_viejo_aceptaba(texto: str) -> None:
    assert faltas(texto) != []


def test_rechaza_la_clasificacion_real_sin_un_corte() -> None:
    real = CLASIFICACION.read_text(encoding="utf-8")
    sin_07 = re.sub(r"### Corte 07-oct.*?(?=^### )", "", real, flags=re.S | re.M)
    assert sin_07 != real
    assert faltas(sin_07) == ["07-oct: sin seccion '### Corte 07-oct (boot 0de3e072)'"]


def test_rechaza_boot_equivocado_clasificacion_cambiada_o_salida_ausente() -> None:
    real = CLASIFICACION.read_text(encoding="utf-8")
    assert faltas(real.replace("### Corte 08-oct (boot e651544a)", "### Corte 08-oct (boot 05d62d81)")) == [
        "08-oct: la seccion no nombra el boot e651544a"
    ]
    otra = real.replace("Clasificacion: INDETERMINADA", "Clasificacion: ENERGIA", 1)
    assert faltas(otra) == ["06-oct: sin 'Clasificacion: INDETERMINADA (energia o hardware interno)'"]
    sin_salida = real.replace("FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01", "otra ficha")
    assert [f for f in faltas(sin_salida) if "Falta" in f] == [
        f"{c}: la linea '- Falta:' no nombra {', '.join(SALIDAS)}" for c in CORTES
    ]
    assert faltas(real.replace(MARCA, "marca")) == [f"falta la marca {MARCA}"]
