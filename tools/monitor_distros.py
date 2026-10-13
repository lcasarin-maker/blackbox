#!/usr/bin/env python3
"""Monitor de distros alternas para GB10 (interruptor `monitor_distros`): FEATURE-MONITOR-DISTROS-ALTERNAS-GB10-01.

Decision de Luis 2026-10-12: la ATOM se queda en DGX OS oficial y se MONITOREAN las distros alternas. Este modulo compara,
por cada fuente de `data/distros_alternas.json`, la cabeza del repo (`git ls-remote`, sin descargar codigo) o el numero de
mensajes del hilo del foro (JSON publico de Discourse) contra la lectura anterior. Una fuente con cambio publica un hallazgo
`bb-hallazgo/1` (tipo `medicion`) en la bandeja de bb; Atlas lo recoge por su cuenta. Las guias y articulos no tienen
comparador: salen `NOT_COLLECTED`, nunca "sin cambio".
Limite declarado: detecta ACTIVIDAD, no juzga si el mecanismo sirve; eso lo mide una ficha propia con control negativo.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable

from tools import hallazgo, interruptores

NOMBRE = "monitor_distros"
RAIZ = Path(__file__).resolve().parent.parent
FUENTES = RAIZ / "data" / "distros_alternas.json"
_HILO = re.compile(r"^(https://forums\.developer\.nvidia\.com)/t/(?:[\w-]+/)?(\d+)$")
Correr = Callable[..., Any]
Abre = Callable[[str], bytes]


def _abre(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=20) as r:
        return bytes(r.read())


def lee(fuente: dict[str, Any], correr: Correr = subprocess.run, abre: Abre = _abre) -> str:
    """Marca actual de una fuente: sha de la cabeza (repo) o `posts=N` (hilo); `NOT_COLLECTED: ...` si no se pudo o no hay comparador."""
    tipo, url = fuente.get("tipo"), str(fuente.get("url", ""))
    if tipo == "repo":
        try:
            r = correr(["git", "ls-remote", url, "HEAD"], capture_output=True, text=True, check=False, timeout=30)
        except (OSError, subprocess.SubprocessError) as e:
            return f"NOT_COLLECTED: git ls-remote {type(e).__name__}"
        sha = str(r.stdout).split("\t")[0].strip()
        return sha if r.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", sha) else "NOT_COLLECTED: git ls-remote sin cabeza"
    m = _HILO.match(url) if tipo == "hilo" else None
    if m:
        try:
            return f"posts={int(json.loads(abre(f'{m.group(1)}/t/{m.group(2)}.json'))['posts_count'])}"
        except (OSError, ValueError, KeyError, TypeError) as e:
            return f"NOT_COLLECTED: hilo {type(e).__name__}"
    return f"NOT_COLLECTED: tipo '{tipo}' sin comparador"


def compara(previo: str | None, ahora: str) -> str:
    """`primera_lectura` | `sin_cambio` | `cambio` | `no_recogido` (una lectura NOT_COLLECTED nunca cuenta como cambio ni como sin cambio)."""
    if ahora.startswith("NOT_COLLECTED"):
        return "no_recogido"
    if previo is None or previo.startswith("NOT_COLLECTED"):
        return "primera_lectura"
    return "sin_cambio" if previo == ahora else "cambio"


def _hallazgo(fuente: dict[str, Any], previo: str, ahora: str, hoy: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(fuente["id"]).lower()).strip("-")[:40]
    return hallazgo.construye(hallazgo.Hallazgo(
        id=f"bb-{hoy}-distros-{slug}", tipo="medicion", confianza="medido", generado=hoy, por="tools/monitor_distros.py",
        nodo=hallazgo.nodo_anonimo(), datos=f"{fuente['id']}: {previo} -> {ahora}", atlas_refs=(),
        fuentes=f"- La fuente `{fuente['id']}` ({fuente.get('url')}) cambio de `{previo}` a `{ahora}`; lista en `data/distros_alternas.json`.",
        inferencia="- [inferencia] Hay actividad nueva en la fuente; si trae un mecanismo cosechable para la ATOM lo decide una ficha propia con control negativo."))


@dataclass(frozen=True)
class Entorno:
    """Lo que `paso` toca fuera de si mismo; los tests lo sustituyen entero."""

    correr: Correr = subprocess.run
    abre: Abre = _abre
    bandeja: Path | None = None
    directorio: Path | None = None
    hoy: str | None = None


def paso(modo_actual: str, fuentes: list[dict[str, Any]], estado: Path, entorno: Entorno = Entorno()) -> dict[str, Any] | None:
    """Una pasada. `off` no lee nada. En `observar` y `actuar` guarda las marcas, publica un hallazgo por fuente con cambio y registra el resumen."""
    if modo_actual == "off":
        return None
    try:
        previas = json.loads(estado.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previas = {}
    dia, veredictos, nuevas = entorno.hoy or date.today().isoformat(), {}, dict(previas)
    for f in fuentes:
        marca = lee(f, entorno.correr, entorno.abre)
        veredictos[f["id"]] = compara(previas.get(f["id"]), marca)
        if veredictos[f["id"]] == "cambio":
            hallazgo.publica(_hallazgo(f, previas[f["id"]], marca, dia), entorno.bandeja)
        if veredictos[f["id"]] != "no_recogido":
            nuevas[f["id"]] = marca
    estado.parent.mkdir(parents=True, exist_ok=True)
    estado.write_text(json.dumps(nuevas, indent=1), encoding="utf-8")
    ev = {"modo": modo_actual, "habria_actuado": "cambio" in veredictos.values(), "veredictos": veredictos,
          "no_recogidas": sorted(k for k, v in veredictos.items() if v == "no_recogido")}
    interruptores.registra(NOMBRE, ev, entorno.directorio)
    return ev


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="monitor_distros")
    ap.add_argument("--paso", action="store_true", help="una pasada segun el interruptor monitor_distros (lo corre bb-monitor-distros.timer)")
    ap.add_argument("--forzar", action="store_true", help="una pasada en modo observar aunque el interruptor este en off (primera pasada de prueba)")
    a = ap.parse_args(argv)
    modo = "observar" if a.forzar else interruptores.modo(NOMBRE)
    ev = paso(modo, json.loads(FUENTES.read_text(encoding="utf-8"))["fuentes"], interruptores._datos() / "monitor_distros_estado.json")
    print(json.dumps(ev, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
