#!/usr/bin/env python3
"""close_check reutilizable para fichas HARVEST-*.md (sugerencias de cosecha
de Atlas, ver satd_family: HARVEST_SUGGESTION).

Estas fichas no tienen un fix de código que probar -- lo único verificable
por máquina es que la DECISIÓN quedó registrada. Sin esto, las 11 fichas
originales traían `close_check: {"cmd": "true", ...}` -- prohibido por
backlog_verifier.PROHIBITED_COMMANDS como no-op, y bloqueaba el push (medido
2026-09-09: contract_breaches=11).

Dos formas válidas, comprobadas en este orden -- las mismas que
`simplecode.verification.harvest_decision`, que es la compuerta de flota:

1. CERRADA (`status: done`): la decisión registrada ES el entregable. Válida
   sólo con un `closure_type` declarado y un `reason` no vacío. Va primero
   porque `ledger_schema` prohíbe que `accepted` conviva con `status: done`
   ("una ficha cerrada no tiene nada que aceptar"), así que un cierre real ya
   no lleva `accepted` y caer a la forma 2 lo rechazaría siempre.
2. ABIERTA + aceptada (`status: open` o ausente): `accepted.{by,date,trigger}`
   completos y sin marcador de pendiente.

## Por qué se endureció el 2026-09-23

Este módulo divergió de la compuerta de flota y aceptaba de más. Medido:

    accepted.by="TODO", trigger="TODO"    -> "accepted completo"  rc=0
    accepted.by="(pendiente)"             -> rechaza              rc=1
    status: done sin closure_type         -> "accepted completo"  rc=0

Rechazaba exactamente UNA cadena literal. Una ficha cuya decisión es
literalmente "TODO" satisfacía su propio close_check, y una ficha movida a
`status: done` sin `closure_type` pasaba aquí y fallaba en la flota
(`harvest_decision` da rc=1 sobre ese mismo fichero). Es el patrón que
`/debt` ya documenta de `aequitas_os`: doctrina y código divergiendo sin que
nada lo diga, que es peor que cualquiera de las dos reglas por separado.

## Residuo declarado

`_es_marcador()` compara contra una lista de marcadores conocidos. Un valor
corto que no esté en esa lista -- `by: "x"` -- sigue pasando. NO se pone un
mínimo de longitud: los 60 valores reales de este repo van de 53 a 191
caracteres, pero son una cohorte escrita por el mismo proceso el mismo día, y
derivar un umbral de ahí sería ajustarlo a la muestra, no medirlo. Un número
inventado además se paga con relleno, que es peor que el hueco.
"""

import re
import sys
from pathlib import Path

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STATUS_RE = re.compile(r'^status:\s*"?([\w-]+)"?\s*$', re.MULTILINE)
CLOSURE_TYPE_RE = re.compile(r'^closure_type:\s*"?([\w-]+)"?\s*$', re.MULTILINE)
REASON_RE = re.compile(r"^reason:\s*(.+?)\s*$", re.MULTILINE)

# El mismo enum que acepta `genuine_task_closure.py` de la flota. Se mantiene
# aquí como literal en vez de importarse: este repo no depende de simplecode
# como librería (`bin/bb` es bash y el kit llega por sync), así que un import
# lo ataría a una instalación que un clon puede no tener. Si el enum de la
# flota crece, esta lista se queda corta y el fallo es RECHAZAR de más, que se
# ve; lo contrario -- aceptar de más -- es lo que hubo que arreglar hoy.
CLOSURE_TYPES = frozenset({"void_wontfix", "duplicate", "relocated_prior_verification"})

# Marcadores de "aquí todavía no hay una decisión". `(pendiente)` es el que
# Atlas deja al crear la ficha; el resto son las formas en que un humano o un
# agente escriben lo mismo. Se compara contra el valor ENTERO ya recortado y
# sin distinguir mayúsculas: un trigger real de este repo tiene 97 caracteres
# como mínimo y no puede colisionar con ninguno de estos.
MARCADORES = frozenset({
    "(pendiente)", "pendiente", "por decidir", "sin decidir",
    "todo", "tbd", "tba", "fixme", "xxx", "hack",
    "n/a", "na", "none", "null", "nil", "pending", "unknown",
    "-", "--", "?", "??", "...", ".",
})


def _es_marcador(valor: str) -> bool:
    return valor.strip().strip("*_`").casefold() in MARCADORES


def _decision_cerrada(texto: str) -> tuple[bool, str] | None:
    """(ok, motivo) para una ficha `status: done`, o None si no lo es.

    None significa "esta forma no aplica, sigue con la otra", que es distinto
    de "esta forma la rechaza" -- devolver False aquí para una ficha abierta
    la mataría antes de llegar a su contrato real.
    """
    estado = STATUS_RE.search(texto)
    if estado is None or estado.group(1) != "done":
        return None
    tipo = CLOSURE_TYPE_RE.search(texto)
    if tipo is None or tipo.group(1) not in CLOSURE_TYPES:
        declarado = tipo.group(1) if tipo else "ninguno"
        return False, (
            f"status: done con closure_type={declarado}, que no esta en "
            f"{sorted(CLOSURE_TYPES)}"
        )
    motivo = REASON_RE.search(texto)
    texto_motivo = motivo.group(1).strip().strip('"').strip() if motivo else ""
    if not texto_motivo:
        return False, "closure_type declarado sin reason"
    if _es_marcador(texto_motivo):
        return False, f"reason es un marcador de pendiente: {texto_motivo!r}"
    return True, f"cerrada por closure_type={tipo.group(1)}: {texto_motivo}"


def check(task_path: Path) -> tuple[bool, str]:
    if not task_path.is_file():
        return False, f"no existe: {task_path}"
    text = task_path.read_text(encoding="utf-8")

    cerrada = _decision_cerrada(text)
    if cerrada is not None:
        return cerrada

    m = re.search(r"^accepted:\s*(\{.*\})\s*$", text, re.MULTILINE)
    if not m:
        return False, "sin campo accepted en el frontmatter"

    import yaml
    acc = yaml.safe_load(m.group(1))
    if not isinstance(acc, dict):
        return False, "accepted no es un objeto"

    for field in ("by", "date", "trigger"):
        val = str(acc.get(field) or "").strip()
        if not val:
            return False, f"accepted.{field} vacío"
        if _es_marcador(val):
            return False, f"accepted.{field} sigue en un marcador de pendiente: {val!r}"

    if not DATE_RE.match(acc["date"]):
        return False, f"accepted.date no es ISO-8601: {acc['date']!r}"

    return True, "accepted completo"


def main():
    if len(sys.argv) != 2:
        print("uso: check_harvest_accepted.py <ruta-a-la-ficha.md>", file=sys.stderr)
        sys.exit(2)
    ok, reason = check(Path(sys.argv[1]))
    print(reason)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":  # pragma: no cover -- entry point, ejercitado via main()
    main()
