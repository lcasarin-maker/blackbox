#!/usr/bin/env python3
"""Hallazgo `bb-hallazgo/2`: la unica forma en que blackbox deja conocimiento para quien lo consume.

Relacion de INFORMACION, no de codigo (SPEC.md, "Contrato con el consumidor de conocimiento"): blackbox
publica un archivo en su propia bandeja (`$BLACKBOX_DATA/hallazgos/`) y el consumidor lo recoge con su
flujo. blackbox nunca escribe dentro del repo de otro: un hallazgo por reinicio meteria corpus ajeno sin
que su dueno lo decida.

El cuerpo lleva dos encabezados LITERALES (`H_FUENTES`, `H_INFERENCIA`) y exige una cita a un archivo: es
el contrato de hallazgos que el consumidor valida con su propio validador. Aqui son constantes de
instrumento, y el fixture DORADO `tests/fixtures/contrato/bb_hallazgo_2.md` (mismo sha256 en los dos
repos) fija la forma entera, byte a byte.

`/2` es `/1` con la lista de referencias en `refs` en vez de la clave que nombraba al consumidor (boleta
#18 A, 2026-11-01). Se emite `/2` porque el consumidor ya acepta las dos versiones.

Frontmatter: todo valor de texto va ENTRE COMILLAS. Sin comillas YAML lo convierte en fecha o entero y
rompe la serializacion JSON del indice del consumidor (medido el 2026-10-11: 1276 fechas sin citar en el
primer envio de un paquete).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ESQUEMA = "bb-hallazgo/2"
H_FUENTES = "## Lo que dicen las fuentes"
H_INFERENCIA = "## Conexión nueva (inferencia de este agente)"
TIPOS = {"corte_abrupto", "reinicio", "medicion", "firma_nueva", "mitigacion_probada"}
CONFIANZA = {"medido", "inferido", "hipotesis"}
CLAVES = (
    "esquema",
    "id",
    "prov:generatedAtTime",
    "prov:wasAttributedTo",
    "prov:wasGeneratedBy",
    "tipo",
    "confianza",
    "nodo",
    "datos",
    "refs",
)
CITA_ARCHIVO = re.compile(r"[\w/._-]+\.(md|json|py|pdf|jsonl|txt)")
ID_VALIDO = re.compile(r"^bb-[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-z0-9-]{1,60}$")


def _leer_machine_id(ruta: str) -> str:
    try:
        return Path(ruta).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "UNSUPPORTED"
    except OSError:
        return "COLLECTION_FAILED"


def nodo_anonimo(leer: Callable[[str], str] | None = None) -> str:
    """Identificador estable del nodo sin hostname ni serie: hash del machine-id. Lo comparten el reporte
    por incidente y el hallazgo, para que el consumidor pueda cruzarlos."""
    mid = (leer or _leer_machine_id)("/etc/machine-id")
    if mid in ("UNSUPPORTED", "COLLECTION_FAILED"):
        return "COLLECTION_FAILED"
    return "node-" + hashlib.sha256(mid.encode()).hexdigest()[:8]


def bandeja() -> Path:
    return (
        Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))
        / "hallazgos"
    )


def _q(v: str) -> str:
    return json.dumps(v, ensure_ascii=False)


@dataclass(frozen=True)
class Hallazgo:
    id: str
    tipo: str
    confianza: str
    generado: str
    por: str
    nodo: str
    datos: str
    refs: tuple[str, ...]
    fuentes: str
    inferencia: str


def construye(h: Hallazgo) -> str:
    cab = [
        "---",
        f"esquema: {_q(ESQUEMA)}",
        f"id: {_q(h.id)}",
        f"prov:generatedAtTime: {_q(h.generado)}",
        f"prov:wasAttributedTo: {_q('blackbox')}",
        f"prov:wasGeneratedBy: {_q(h.por)}",
        f"tipo: {_q(h.tipo)}",
        f"confianza: {_q(h.confianza)}",
        f"nodo: {_q(h.nodo)}",
        f"datos: {_q(h.datos)}",
        "refs: [" + ", ".join(_q(r) for r in h.refs) + "]",
        "---",
        "",
    ]
    return (
        "\n".join(cab)
        + f"# {h.id}\n\n{H_FUENTES}\n\n{h.fuentes.strip()}\n\n{H_INFERENCIA}\n\n{h.inferencia.strip()}\n"
    )


def _frontmatter(texto: str) -> dict[str, str] | None:
    m = re.match(r"---\n(.*?)\n---\n", texto, re.S)
    if not m:
        return None
    out: dict[str, str] = {}
    for linea in m.group(1).splitlines():
        k, _, v = linea.partition(": ")
        out[k.strip()] = v.strip()
    return out


def _v(fm: dict[str, str], k: str) -> str | None:
    """Valor de texto decodificado, o None si falta o no esta entre comillas (esa falta ya se reporta)."""
    try:
        x = json.loads(fm[k])
    except (KeyError, json.JSONDecodeError):
        return None
    return x if isinstance(x, str) else None


def valida(texto: str) -> list[str]:
    """Faltas al esquema. Lista vacia = valido. Cada regla tiene su caso negativo en los tests."""
    fm = _frontmatter(texto)
    if fm is None:
        return ["sin frontmatter"]
    faltas = [f"falta la clave '{k}'" for k in CLAVES if k not in fm]
    # un valor de texto sin comillas YAML lo vuelve fecha o entero: rompe el payload JSON del indice
    faltas += [
        f"'{k}' sin comillas"
        for k, v in fm.items()
        if k != "refs" and not (v.startswith('"') and v.endswith('"'))
    ]
    if _v(fm, "esquema") not in (None, ESQUEMA):
        faltas.append(f"esquema distinto de {ESQUEMA}")
    for clave, validos in (("tipo", TIPOS), ("confianza", CONFIANZA)):
        if _v(fm, clave) is not None and _v(fm, clave) not in validos:
            faltas.append(f"{clave} fuera de {sorted(validos)}")
    if _v(fm, "id") is not None and not ID_VALIDO.match(_v(fm, "id") or ""):
        faltas.append("id no cumple bb-AAAA-MM-DD-slug")
    if H_FUENTES not in texto:
        faltas.append(f"falta la seccion literal '{H_FUENTES}'")
    if H_INFERENCIA not in texto:
        faltas.append(f"falta la seccion literal '{H_INFERENCIA}'")
    cuerpo = texto.split("\n---\n", 1)[-1]
    if not CITA_ARCHIVO.search(
        cuerpo.split(H_INFERENCIA)[0] if H_INFERENCIA in cuerpo else cuerpo
    ):
        faltas.append("la seccion de fuentes no cita ningun archivo")
    return faltas


def publica(texto: str, destino: Path | None = None) -> tuple[Path, str]:
    """Escribe el hallazgo en la bandeja. Idempotente por contenido: mismo id y mismo texto no duplica;
    mismo id con otro texto se rechaza (un hallazgo publicado no se reescribe en silencio)."""
    faltas = valida(texto)
    if faltas:
        raise ValueError("hallazgo invalido: " + "; ".join(faltas))
    d = destino or bandeja()
    d.mkdir(parents=True, exist_ok=True)
    fm = _frontmatter(texto) or {}
    ruta = d / f"{_v(fm, 'id')}.md"
    if ruta.exists():
        if (
            hashlib.sha256(ruta.read_bytes()).digest()
            == hashlib.sha256(texto.encode()).digest()
        ):
            return ruta, "ya_publicado"
        raise FileExistsError(f"{ruta.name} ya existe con otro contenido")
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(texto, encoding="utf-8")
    tmp.replace(ruta)
    return ruta, "publicado"


# Las etiquetas cuya causa ya nombra el journal (o la telemetria): la misma regla de `veredicto` en
# tools/reboot_verdict.py, para leer una fila de antes del campo `causa`.
_CAUSA_ES_ETIQUETA = ("PANIC_", "COLAPSO_", "CIERRE_ORDENADO_")


def _tipo(etiqueta: str, causa: str) -> str:
    """`reinicio` para el cierre ordenado y para el arranque que no completo (FALLO_DE_ARRANQUE_*, fantasma
    o no): ahi no hubo maquina en marcha que cortar, el arranque se quedo en una etapa y volvio a arrancar.
    Todo lo demas es una maquina que murio en marcha: `corte_abrupto`, tambien CORTE_DE_RED y
    APAGADO_INTERNO, que antes de leer la causa salian `reinicio`."""
    if etiqueta.startswith("CIERRE_ORDENADO_") or causa.startswith(("CIERRE_ORDENADO_", "FALLO_DE_ARRANQUE_")):
        return "reinicio"
    return "corte_abrupto"


def desde_veredicto(
    fila: dict[str, Any], *, nodo: str, generado: str, datos: str
) -> str:
    """Hallazgo de un reinicio a partir de una fila `bb-reboot/1` de `bb reboots`. Lo medido va en fuentes,
    incluida la causa que cruza todas las fuentes (`causa`) con su cita (`causa_fuente`); lo no probado va
    en inferencia, marcado como tal. Solo una causa INDETERMINADO se declara indeterminada."""
    et = fila["etiqueta"]
    boot = fila["boot_id"][:8]
    if "causa" in fila:
        causa, cita = fila["causa"] or "INDETERMINADO", fila.get("causa_fuente")
        linea_causa = f"- Causa cruzando las fuentes (`causa`): **{causa}**; su fuente (`causa_fuente`): " + (
            f"`{cita}`." if cita else "ninguna."
        )
    else:
        causa, cita = (et if et.startswith(_CAUSA_ES_ETIQUETA) else "INDETERMINADO"), None
        linea_causa = (
            "- La fila no trae `causa` ni `causa_fuente` (es anterior a esos campos): "
            f"de la etiqueta se lee **{causa}**, con la regla de `tools/reboot_verdict.py`."
        )
    tipo = _tipo(et, causa)
    no_corrio = fila.get("could_not_run") or []
    fuentes = [
        f"- Veredicto de `{datos}`: **{et}** para el boot `{boot}`; hueco hasta el siguiente arranque: {fila.get('hueco_s')} s.",
        linea_causa,
        *[f"- {r}" for r in fila.get("razones", [])],
        f"- Registro BERT en el arranque siguiente: guid `{fila.get('bert_guid')}`, palabra en 0x14 `{fila.get('bert_palabra_0x14')}`.",
        f"- Lo que no pudo correr (`could_not_run`): {', '.join(no_corrio or ['nada'])}.",
    ]
    bert = (
        "la palabra BERT no esta decodificada y su relacion con el tipo de reset es una hipotesis (ver "
        "`DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01.md`)."
    )
    if tipo == "corte_abrupto" and causa == "INDETERMINADO":
        inferencia = (
            "- [inferencia] La causa de un corte abrupto sin observador externo queda INDETERMINADA entre energia y hardware interno; "
            if "observador_externo" in no_corrio
            else "- [inferencia] La causa de este corte abrupto queda INDETERMINADA entre energia y hardware interno: "
            "el observador externo no alcanzo a decidirla; "
        ) + bert
    elif tipo == "reinicio" and not causa.startswith("FALLO_DE_ARRANQUE_"):
        inferencia = "- Sin inferencia nueva: el cierre quedo registrado y clasificado."
    else:
        inferencia = f"- La causa la nombra la fila: **{causa}**, con fuente `{cita or 'ninguna'}`." + (
            " [inferencia] En el corte, " + bert if tipo == "corte_abrupto" else ""
        )
    return construye(
        Hallazgo(
            id=f"bb-{generado[:10]}-{et.lower().replace('_', '-')}-{boot}",
            tipo=tipo,
            confianza="medido",
            generado=generado,
            por="bb reboots",
            nodo=nodo,
            datos=datos,
            refs=(
                "knowledge/investigations/gb10_cortes_2026-10-11/00_INDICE.md",
            ),
            fuentes="\n".join(fuentes),
            inferencia=inferencia,
        )
    )
