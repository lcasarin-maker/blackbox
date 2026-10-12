#!/usr/bin/env python3
"""Hallazgo `bb-hallazgo/1`: la unica forma en que blackbox deja conocimiento para Atlas.

Relacion de INFORMACION, no de codigo (SPEC.md, "Contrato con Atlas", enmienda del 2026-10-11):
blackbox publica un archivo en su propia bandeja (`$BLACKBOX_DATA/hallazgos/`) y Atlas lo recoge con
su flujo. blackbox nunca escribe dentro del repo de Atlas: sus tests exigen que cada dictamen de
`docs/agent_findings/` este indexado, y un hallazgo por reinicio meteria corpus sin que Atlas lo decida.

El cuerpo reusa los dos encabezados LITERALES del contrato de hallazgos de Atlas
(`tools/kb_investigator.py`, REQUIRED_SOURCES_HEADING y REQUIRED_INFERENCE_HEADING) y exige una cita a
un archivo, para que Atlas lo valide con su propio `_contract_violations`. Aqui se copian como constantes
de instrumento; si Atlas los cambia, `test_hallazgo_cumple_el_contrato_de_atlas` lo avisa (se omite si
Atlas no esta).

Frontmatter: todo valor de texto va ENTRE COMILLAS. Sin comillas YAML lo convierte en fecha o entero y
rompe la serializacion JSON del indice de Atlas (medido el 2026-10-11: 1276 fechas sin citar en el primer
envio de un paquete).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ESQUEMA = "bb-hallazgo/1"
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
    "atlas_refs",
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
    por incidente y el hallazgo, para que Atlas pueda cruzarlos."""
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
    atlas_refs: tuple[str, ...]
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
        "atlas_refs: [" + ", ".join(_q(r) for r in h.atlas_refs) + "]",
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
        if k != "atlas_refs" and not (v.startswith('"') and v.endswith('"'))
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


def desde_veredicto(
    fila: dict[str, Any], *, nodo: str, generado: str, datos: str
) -> str:
    """Hallazgo de un reinicio a partir de una fila de `bb reboots`. Lo medido va en fuentes; lo no
    probado (la causa de un corte abrupto) va en inferencia, marcado como tal."""
    et = fila["etiqueta"]
    boot = fila["boot_id"][:8]
    tipo = (
        "corte_abrupto"
        if et in ("CORTE_ABRUPTO", "COLAPSO_MEMORIA", "PANIC_KERNEL", "INDETERMINADO")
        else "reinicio"
    )
    fuentes = [
        f"- Veredicto de `{datos}`: **{et}** para el boot `{boot}`; hueco hasta el siguiente arranque: {fila.get('hueco_s')} s.",
        *[f"- {r}" for r in fila.get("razones", [])],
        f"- Registro BERT en el arranque siguiente: guid `{fila.get('bert_guid')}`, palabra en 0x14 `{fila.get('bert_palabra_0x14')}`.",
        f"- Lo que no pudo correr (`could_not_run`): {', '.join(fila.get('could_not_run') or ['nada'])}.",
    ]
    inferencia = (
        "- [inferencia] La causa de un corte abrupto sin observador externo queda INDETERMINADA entre energia y hardware interno; "
        "la palabra BERT no esta decodificada y su relacion con el tipo de reset es una hipotesis (ver "
        "`DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01.md`)."
        if tipo == "corte_abrupto"
        else "- Sin inferencia nueva: el cierre quedo registrado y clasificado."
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
            atlas_refs=(
                "knowledge/investigations/gb10_cortes_2026-10-11/00_INDICE.md",
            ),
            fuentes="\n".join(fuentes),
            inferencia=inferencia,
        )
    )
