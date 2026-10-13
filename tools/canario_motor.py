#!/usr/bin/env python3
"""
# max_tokens 512/256: el motor razona antes de responder (medido 2026-10-13: 185 tokens para `{"ok": true}`); con 32 daba content=None y una FALLA falsa.Canario FUNCIONAL del motor de inferencia local (vLLM), en modo observar.

Valida en vivo afirmaciones de hilos del foro de NVIDIA: (a) el nombre servido coincide con el esperado (404 por
served-model-name distinto, hilo OpenClaw); (b) JSON estricto; (c) llamada de herramienta con `finish_reason`
`tool_calls` (no `stop` con cero tool_calls, hilo QWEN-LONG-AGENT-STOP); (d) latencia y tokens.

Veredicto por prueba: OK / FALLA / NOT_COLLECTED. Un motor que no responde es NOT_COLLECTED (instrumento sin sujeto), nunca
FALLA del modelo y nunca sano. Es produccion: una peticion corta por prueba, UNA ronda por ejecucion, sin reintentos; si
`/v1/models` no responde no se envian las otras.
Interruptor `canario_motor`: off / observar / actuar. `actuar` esta UNSUPPORTED: no hay nada que el canario deba hacer.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from typing import Any, Callable

from tools import interruptores

NOMBRE = "canario_motor"
TIMEOUT_S = 60
URL_MODELOS = os.environ.get("BLACKBOX_GATEWAY_URL", "http://127.0.0.1:8000/v1/models")
URL_CHAT = os.environ.get("BLACKBOX_GATEWAY_CHAT", "http://127.0.0.1:8000/v1/chat/completions")
OK, FALLA, NC = "OK", "FALLA", "NOT_COLLECTED"

TOOLS = [{"type": "function", "function": {"name": "suma", "description": "Suma dos numeros", "parameters": {"type": "object", "properties": {"a": {"type": "number"}, "b": {"type": "number"}}, "required": ["a", "b"]}}}]


def consulta(url: str, cuerpo: dict[str, Any] | None = None, abre: Callable[..., Any] = urllib.request.urlopen, timeout: float = TIMEOUT_S) -> dict[str, Any] | None:
    """GET (sin cuerpo) o POST JSON. Devuelve el JSON, o None si el motor no responde o responde basura. Nunca reintenta."""
    datos = None if cuerpo is None else json.dumps(cuerpo).encode()
    req = urllib.request.Request(url, data=datos, headers={"Content-Type": "application/json"})
    try:
        with abre(req, timeout=timeout) as r:
            out = json.loads(r.read().decode("utf-8"))
    except (OSError, ValueError):  # URLError y TimeoutError son OSError
        return None
    return out if isinstance(out, dict) else None


def _choice(resp: dict[str, Any]) -> dict[str, Any]:
    c = resp.get("choices")
    return c[0] if isinstance(c, list) and c and isinstance(c[0], dict) else {}


def _tokens(resp: dict[str, Any]) -> int | None:
    t = (resp.get("usage") or {}).get("total_tokens")
    return t if isinstance(t, int) else None


def _prueba_modelo(resp: dict[str, Any] | None, esperado: str | None) -> dict[str, Any]:
    if resp is None:
        return {"estado": NC, "motivo": "/v1/models no responde"}
    data = resp.get("data")
    nombre = data[0].get("id") if isinstance(data, list) and data and isinstance(data[0], dict) else None
    if not nombre:
        return {"estado": FALLA, "motivo": "/v1/models sin modelos", "servido": None}
    if esperado and nombre != esperado:
        return {"estado": FALLA, "motivo": f"servido {nombre!r} != esperado {esperado!r}", "servido": nombre}
    return {"estado": OK, "servido": nombre, "esperado": esperado}


def _prueba_json(resp: dict[str, Any] | None) -> dict[str, Any]:
    if resp is None:
        return {"estado": NC, "motivo": "sin respuesta"}
    txt = _choice(resp).get("message", {}).get("content")
    try:
        ok = json.loads(txt) == {"ok": True}
    except (TypeError, ValueError):
        return {"estado": FALLA, "motivo": f"no parsea como JSON: {str(txt)[:80]!r}", "tokens": _tokens(resp)}
    return {"estado": OK if ok else FALLA, "tokens": _tokens(resp), **({} if ok else {"motivo": f"JSON distinto de {{'ok': true}}: {str(txt)[:80]!r}"})}


def _prueba_tool(resp: dict[str, Any] | None) -> dict[str, Any]:
    if resp is None:
        return {"estado": NC, "motivo": "sin respuesta"}
    ch = _choice(resp)
    calls = ch.get("message", {}).get("tool_calls") or []
    fin = ch.get("finish_reason")
    base = {"finish_reason": fin, "n_tool_calls": len(calls), "tokens": _tokens(resp)}
    if not calls:
        return {**base, "estado": FALLA, "motivo": f"cero tool_calls (finish_reason={fin!r})"}
    try:
        args = json.loads(calls[0]["function"]["arguments"])
    except (KeyError, TypeError, ValueError):
        return {**base, "estado": FALLA, "motivo": "argumentos de tool_call no son JSON valido"}
    if fin != "tool_calls":
        return {**base, "estado": FALLA, "motivo": f"finish_reason={fin!r}, se esperaba 'tool_calls'"}
    if not isinstance(args, dict):
        return {**base, "estado": FALLA, "motivo": "argumentos no son un objeto"}
    return {**base, "estado": OK}


def evalua(respuesta_modelos: dict[str, Any] | None, resp_json: dict[str, Any] | None, resp_tool: dict[str, Any] | None, esperado: str | None = None) -> dict[str, Any]:
    """Pura, sin E/S. None en una respuesta = el motor no contesto = NOT_COLLECTED."""
    pruebas = {"modelo": _prueba_modelo(respuesta_modelos, esperado), "json": _prueba_json(resp_json), "tool": _prueba_tool(resp_tool)}
    estados = {p["estado"] for p in pruebas.values()}
    general = FALLA if FALLA in estados else NC if NC in estados else OK
    toks = [p["tokens"] for p in pruebas.values() if isinstance(p.get("tokens"), int)]
    return {"estado_general": general, "pruebas": pruebas, "tokens": sum(toks) if toks else None, "habria_actuado": general == FALLA}


def ronda(abre: Callable[..., Any] = urllib.request.urlopen, esperado: str | None = None, reloj: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """Una ronda: models primero; si no responde, las otras dos peticiones NO se envian."""
    t0 = reloj()
    modelos = consulta(URL_MODELOS, None, abre)
    rj = rt = None
    if modelos is not None:
        data = modelos.get("data")
        nombre = data[0].get("id") if isinstance(data, list) and data and isinstance(data[0], dict) else None
        if nombre:
            rj = consulta(URL_CHAT, {"model": nombre, "messages": [{"role": "user", "content": 'Responde exactamente con este JSON y nada mas: {"ok": true}'}], "temperature": 0, "max_tokens": 512}, abre)
            rt = consulta(URL_CHAT, {"model": nombre, "messages": [{"role": "user", "content": "Usa la herramienta suma para sumar 2 y 3."}], "tools": TOOLS, "tool_choice": "auto", "temperature": 0, "max_tokens": 256}, abre)
    r = evalua(modelos, rj, rt, esperado)
    r["latencia_s"] = round(reloj() - t0, 3)
    return r


def paso(modo_actual: str, abre: Callable[..., Any] = urllib.request.urlopen, esperado: str | None = None, directorio: Any = None) -> dict[str, Any] | None:
    """off -> None, sin consultar ni escribir. observar -> corre la ronda y la registra. actuar -> UNSUPPORTED."""
    if modo_actual == "off":
        return None
    if modo_actual == "actuar":
        raise NotImplementedError("UNSUPPORTED: canario_motor no tiene modo actuar")
    r = {"modo": modo_actual, **ronda(abre, esperado)}
    interruptores.registra(NOMBRE, r, directorio)
    return r


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="canario_motor")
    ap.add_argument("--paso", action="store_true", help="registra segun el interruptor canario_motor (lo corre bb-canario-motor.timer)")
    a = ap.parse_args(argv)
    esperado = os.environ.get("BLACKBOX_MOTOR_MODELO") or None
    if a.paso:
        r = paso(interruptores.modo(NOMBRE), urllib.request.urlopen, esperado)
        if r is None:
            print(json.dumps({"modo": "off", "estado_general": None}))
            return 0
    else:
        r = {"modo": "observar", **ronda(urllib.request.urlopen, esperado)}
    print(json.dumps(r, indent=1, ensure_ascii=False))
    return {OK: 0, FALLA: 1}.get(r["estado_general"], 2)


if __name__ == "__main__":
    sys.exit(main())
