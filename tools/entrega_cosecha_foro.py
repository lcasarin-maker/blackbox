#!/usr/bin/env python3
"""Entrega de la cosecha del foro de NVIDIA a la carpeta de investigaciones de Atlas (FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01).

Patron de la entrega del 2026-10-11 (FEATURE-ATLAS-REINDEX-PAQUETE-GB10-01): archivos Markdown bajo
`Atlas/knowledge/investigations/<carpeta>/` con frontmatter de SOLO CADENAS (el indexador de Atlas fallo con otros tipos),
un manifiesto con el SHA-256 de cada archivo, y NADA mas: no se ejecuta el build de Atlas (usa GPU) ni se hace commit en su repo.
bb no importa codigo de Atlas: el contrato es la carpeta de archivos.

Entra cada tema candidato (oleada 1 con utilidad alta o media, oleada 2 con candidato si o quizas) con su resultado
estructurado y su texto, truncado a TOPE_TEXTO caracteres (el frontmatter lo dice). Salen ademas un indice y un catalogo
de mecanismos por proposito.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

TOPE_TEXTO = 60000
PROPOSITOS = ("monitorear", "medir", "rastrear", "solucionar", "prevenir", "omision_nvidia")


def slug(titulo: str, largo: int = 60) -> str:
    s = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:largo] or "sin_titulo"


def q(valor: Any) -> str:
    """Cadena YAML segura: JSON entre comillas (todo valor del frontmatter es una cadena)."""
    return json.dumps(str(valor), ensure_ascii=False)


def frontmatter(campos: dict[str, Any]) -> str:
    return "---\n" + "\n".join(f"{k}: {q(v)}" for k, v in campos.items()) + "\n---\n"


def candidatos(evidencia: Path, hilos1: Path, hilos2: Path, inv: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for f in sorted((evidencia / "ola1-resultados").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d["utilidad_atom"] in ("alta", "media"):
            out.append({"id": d["id"], "fuente": "oleada1", "res": d, "texto": hilos1 / "threads" / f"{d['id']}.txt", "nivel": d["utilidad_atom"]})
    for f in sorted((evidencia / "ola2-triaje").glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d["candidato"] in ("si", "quizas"):
            out.append({"id": d["id"], "fuente": "oleada2", "res": d, "texto": hilos2 / "threads" / f"{d['id']}.txt", "nivel": d["candidato"]})
    for c in out:
        c["inv"] = inv.get(c["id"], {})
    return out


def cuerpo(c: dict[str, Any]) -> tuple[str, bool]:
    r = c["res"]
    partes = ["## Resultado del analisis\n"]
    if c["fuente"] == "oleada1":
        partes.append(f"Clase: {r['clase']} · utilidad: {r['utilidad_atom']} · lectura: {r.get('lectura', 'no declarada')}\n\n{r['razon']}\n")
        for m in r.get("mecanismos", []):
            partes.append(f"- **{m.get('que', '')}** — `{m.get('como', '')}` (post {m.get('fuente_post')}; repositorio: {m.get('repositorio')}; licencia: {m.get('licencia')}; riesgo: {m.get('riesgo')})\n")
        if r.get("omision_nvidia"):
            partes.append(f"\nOmision de NVIDIA: {r['omision_nvidia']}\n")
    else:
        partes.append(f"Triaje: {r['candidato']} · senales: {', '.join(r.get('senales', []))}\n\n{r['una_frase']}\n\n_Lectura corta (mensaje 1, personal de NVIDIA y mensajes con comandos); no es el analisis completo del tema._\n")
    try:
        texto = c["texto"].read_text(encoding="utf-8")
    except OSError:
        texto = "(texto no disponible)"
    truncado = len(texto) > TOPE_TEXTO
    partes.append("\n## Texto del tema\n\n" + texto[:TOPE_TEXTO] + ("\n\n[...truncado...]" if truncado else "") + "\n")
    return "".join(partes), truncado


def escribe(destino: Path, cands: list[dict[str, Any]], fecha: str, cobertura: dict[str, Any]) -> dict[str, str]:
    destino.mkdir(parents=True, exist_ok=True)
    manifiesto: dict[str, str] = {}

    def guarda(nombre: str, contenido: str) -> None:
        (destino / nombre).write_text(contenido, encoding="utf-8")
        manifiesto[nombre] = hashlib.sha256(contenido.encode("utf-8")).hexdigest()

    por_prop: dict[str, list[str]] = {p: [] for p in PROPOSITOS}
    for c in cands:
        r, inv = c["res"], c["inv"]
        titulo = inv.get("titulo") or r.get("titulo") or f"tema {c['id']}"
        texto, trunc = cuerpo(c)
        props = r.get("proposito", [])
        guarda(f"hilo_{c['id']}_{slug(titulo)}.md", frontmatter({
            "id": c["id"], "titulo": titulo, "url": f"https://forums.developer.nvidia.com/t/{c['id']}", "fuente": c["fuente"],
            "nivel": c["nivel"], "proposito": ",".join(props), "texto_truncado": "si" if trunc else "no", "fecha_cosecha": fecha,
            "tipo": "derivado_de_foro_publico_de_nvidia"}) + f"\n# {titulo}\n\n" + texto)
        linea = f"- [{titulo}](hilo_{c['id']}_{slug(titulo)}.md) ({c['fuente']}, {c['nivel']}): " + (r.get("una_frase") or r.get("razon", "")).replace("\n", " ")[:220]
        for p in props:
            if p in por_prop:
                por_prop[p].append(linea)
    cat = [frontmatter({"titulo": "Catalogo de mecanismos del foro de NVIDIA por proposito", "fecha_cosecha": fecha, "tipo": "derivado"}),
           "\n# Catalogo de mecanismos por proposito\n\nUn tema aparece en cada proposito que declara. Es un indice de lo que dicen usuarios y personal del foro; NO esta verificado en la maquina salvo donde se indica en el indice.\n"]
    for p in PROPOSITOS:
        cat.append(f"\n## {p} ({len(por_prop[p])})\n\n" + "\n".join(por_prop[p]) + "\n")
    guarda("catalogo_mecanismos.md", "".join(cat))
    guarda("00_INDICE.md", frontmatter({"titulo": "Cosecha del foro de NVIDIA (2026-10-12): indice y cobertura", "fecha_cosecha": fecha, "tipo": "derivado"}) + f"""
# Cosecha del foro de NVIDIA — indice

- Categorias: 721 (DGX Spark / GB10), 722 (Announcements), 723 (Projects) y Docker con GPU. Total 3043 temas con texto completo descargado.
- Esta carpeta contiene los {len(cands)} temas candidatos (oleada 1: utilidad alta o media; oleada 2: triaje si o quizas) con su texto truncado a {TOPE_TEXTO} caracteres.
- Cobertura medida con `tools/verifica_cosecha_foro.py` sobre el sujeto: {json.dumps(cobertura, ensure_ascii=False)}
- Limites: la oleada 2 es una lectura corta; en hilos largos un `no` significa "no lo vi en lo leido". Las afirmaciones son de usuarios y de personal del foro, no verificadas por esta maquina salvo el reloj atascado (`bb reloj`) y la memoria por cgroup (`bb gpumem`).
- Catalogo por proposito: `catalogo_mecanismos.md`. Manifiesto con SHA-256 de cada archivo: en el repositorio blackbox, `tasks/evidence/FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01/entrega_atlas_manifiesto.sha256`.
""")
    return manifiesto


def main(argv: list[str] | None = None) -> int:
    a = argv if argv is not None else sys.argv[1:]
    if len(a) != 1:
        print("uso: python -m tools.entrega_cosecha_foro <carpeta-destino-en-Atlas>", file=sys.stderr)
        return 2
    raiz = Path(__file__).resolve().parent.parent
    ev = raiz / "tasks/evidence/FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01"
    inv: dict[int, dict[str, Any]] = {}
    for n in ("inventario.json", "inventario-721-33.json"):
        for t in json.loads((ev / n).read_text(encoding="utf-8"))["temas"]:
            inv[t["id"]] = t
    datos = Path.home() / ".local/share/blackbox"
    cobertura = {"oleada1": json.loads((ev / "ola1-verificacion.json").read_text(encoding="utf-8")).get("cobertura_completa"),
                 "oleada2": json.loads((ev / "ola2-verificacion.json").read_text(encoding="utf-8")).get("cobertura_completa")}
    cands = candidatos(ev, datos / "foro-722-723", datos / "foro-721-33", inv)
    m = escribe(Path(a[0]), cands, "2026-10-12", cobertura)
    # formato de `sha256sum` (verificable con `cd <destino> && sha256sum -c <manifiesto>`): el JSON con el hash tras el nombre
    # del archivo disparaba la regla generic-api-key de gitleaks (nombres con "api" y un hash largo en la misma linea)
    (ev / "entrega_atlas_manifiesto.sha256").write_text("".join(f"{h}  {n}\n" for n, h in sorted(m.items())), encoding="utf-8")
    print(f"{len(m)} archivos escritos en {a[0]}; manifiesto con {len(m)} SHA-256")
    return 0


if __name__ == "__main__":
    sys.exit(main())
