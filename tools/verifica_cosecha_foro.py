#!/usr/bin/env python3
"""Verificador de cobertura de la cosecha del foro de NVIDIA (FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01).

La completitud se prueba sobre el SUJETO, no sobre lo que informan los agentes (regla de enjambre): cada tema del
inventario debe tener (1) el texto descargado COMPLETO y (2) un resultado de analisis con el esquema valido.
Patron tomado de Twiner (resultado de tres estados y completitud sustantiva, sin importar su codigo):
  descargado        recibo `fetched` con todos los mensajes y texto no vacio
  vacio_del_producto el foro respondio 403/404 (tema borrado o privado): informacion, no fallo
  no_se_pudo        cualquier otra cosa (red, 5xx, mensajes faltantes): cuenta como fallo y NO se traga
Un informe con `no_se_pudo` o con temas sin resultado NO es limpio, aunque la mayoria pase.

    python -m tools.verifica_cosecha_foro --inventario inv.json --hilos <dir> --resultados <dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOLERANCIA_MENSAJES = 2  # el conteo del foro (posts_count) incluye mensajes ocultos; el texto puede traer 1-2 menos
PROPOSITOS = {"monitorear", "medir", "rastrear", "solucionar", "prevenir", "omision_nvidia"}
CLASES = {"mecanismo", "diagnostico", "anuncio_oficial", "ruido", "pregunta_sin_respuesta"}
UTILIDAD = {"alta", "media", "baja", "ninguna"}


def estado_descarga(hilos: Path, tid: int) -> tuple[str, str]:
    """(estado, motivo) para un tema: descargado | vacio_del_producto | no_se_pudo."""
    recibo = hilos / "threads" / f"{tid}.fetch.json"
    try:
        r = json.loads(recibo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "no_se_pudo", "sin recibo de descarga"
    if r.get("status") == "fetched":
        if r.get("posts_fetched") != r.get("posts_expected") or not r.get("posts_fetched"):
            return "no_se_pudo", f"mensajes {r.get('posts_fetched')} de {r.get('posts_expected')}"
        try:
            texto = (hilos / "threads" / f"{tid}.txt").read_text(encoding="utf-8")
        except OSError:
            return "no_se_pudo", "recibo dice fetched pero falta el texto"
        if len(texto.split("POST ")) < 2 or len(texto.strip()) < 40:
            return "no_se_pudo", "texto vacio"
        return "descargado", ""
    err = str(r.get("error", ""))
    if "404" in err or "403" in err:
        return "vacio_del_producto", err[:80]
    return "no_se_pudo", err[:80] or "sin detalle"


def mensajes_reales(hilos: Path, tid: int) -> int:
    """Mensajes del tema segun el texto descargado (marcas `POST n |`)."""
    try:
        texto = (hilos / "threads" / f"{tid}.txt").read_text(encoding="utf-8")
    except OSError:
        return 0
    return texto.count("\nPOST ") + (1 if texto.startswith("POST ") else 0)


def valida_resultado(d: Any, tid: int) -> list[str]:
    """Lista de problemas del resultado de analisis de un tema (vacia = valido)."""
    if not isinstance(d, dict):
        return ["no es un objeto JSON"]
    malos: list[str] = []
    if d.get("id") != tid:
        malos.append(f"id {d.get('id')!r} distinto de {tid}")
    if d.get("leido") is not True or not isinstance(d.get("posts_leidos"), int) or d["posts_leidos"] < 1:
        malos.append("leido/posts_leidos no demuestran lectura")
    if d.get("lectura") not in ("completa", "parcial"):
        malos.append("lectura debe ser completa o parcial (declara lo que NO leiste)")
    if d.get("clase") not in CLASES:
        malos.append(f"clase invalida {d.get('clase')!r}")
    if d.get("utilidad_atom") not in UTILIDAD:
        malos.append(f"utilidad_atom invalida {d.get('utilidad_atom')!r}")
    prop = d.get("proposito")
    if not isinstance(prop, list) or not set(prop) <= PROPOSITOS:
        malos.append("proposito debe ser una lista dentro de " + "/".join(sorted(PROPOSITOS)))
    if not isinstance(d.get("razon"), str) or len(d["razon"].strip()) < 20:
        malos.append("razon ausente o vacia")
    mec = d.get("mecanismos")
    if not isinstance(mec, list):
        malos.append("mecanismos debe ser una lista")
        mec = []
    for i, m in enumerate(mec):
        if not isinstance(m, dict) or not str(m.get("que", "")).strip() or not str(m.get("como", "")).strip() or not isinstance(m.get("fuente_post"), int):
            malos.append(f"mecanismo {i}: faltan que/como/fuente_post")
    if d.get("clase") == "mecanismo" and not mec:
        malos.append("clase mecanismo sin mecanismos")
    if d.get("utilidad_atom") == "alta" and not mec:
        malos.append("utilidad alta sin ningun mecanismo con comando o formula")
    return malos


def verifica(inventario: list[dict[str, Any]], hilos: Path, resultados: Path) -> dict[str, Any]:
    cuenta = {"descargado": 0, "vacio_del_producto": 0, "no_se_pudo": 0}
    sin_resultado: list[int] = []
    parciales: dict[int, str] = {}
    de_mas: dict[int, str] = {}
    contabilidad: dict[int, str] = {}
    invalidos: dict[int, list[str]] = {}
    fallos: dict[int, str] = {}
    for it in inventario:
        tid = int(it["id"])
        est, motivo = estado_descarga(hilos, tid)
        cuenta[est] += 1
        if est == "no_se_pudo":
            fallos[tid] = motivo
        if est == "vacio_del_producto":
            continue  # el tema no existe para nosotros: no se analiza ni cuenta como hueco
        ruta = resultados / f"{tid}.json"
        try:
            d = json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            sin_resultado.append(tid)
            continue
        malos = valida_resultado(d, tid)
        if malos:
            invalidos[tid] = malos
            continue
        reales = mensajes_reales(hilos, tid)
        leidos = d["posts_leidos"]
        if leidos > reales + TOLERANCIA_MENSAJES:
            de_mas[tid] = f"declara {leidos} mensajes leidos y el tema tiene {reales}"
        elif d["lectura"] == "parcial" or leidos < reales - TOLERANCIA_MENSAJES:
            parciales[tid] = f"leyo {leidos} de {reales}"
        elif leidos != reales:
            contabilidad[tid] = f"declara {leidos}, el texto trae {reales}"
    limpio = not fallos and not sin_resultado and not invalidos and not parciales and not de_mas
    return {
        "temas": len(inventario),
        "descarga": cuenta,
        "fallos_de_descarga": fallos,
        "sin_resultado": sin_resultado,
        "resultados_invalidos": invalidos,
        "lectura_parcial_por_completar": parciales,
        "lectura_declarada_de_mas": de_mas,
        "diferencia_de_contabilidad_tolerada": contabilidad,
        "cobertura_completa": limpio,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventario", type=Path, required=True)
    ap.add_argument("--hilos", type=Path, required=True)
    ap.add_argument("--resultados", type=Path, required=True)
    a = ap.parse_args(argv)
    raw = json.loads(a.inventario.read_text(encoding="utf-8"))
    inv = raw["temas"] if isinstance(raw, dict) else raw
    r = verifica(inv, a.hilos, a.resultados)
    print(json.dumps(r, indent=1, ensure_ascii=False))
    return 0 if r["cobertura_completa"] else 1


if __name__ == "__main__":
    sys.exit(main())
