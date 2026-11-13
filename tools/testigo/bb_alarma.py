#!/usr/bin/env python3
"""bb-alarma: alarma EXTERNA de la ATOM. Un solo archivo de Python stdlib (3.8+) que corre en OTRO equipo (la Dell).

Prueba cada `intervalo_s` segundos varios caminos hacia la ATOM (SSH por la red de casa, SSH por Tailscale, RustDesk) y avisa
por ntfy cuando uno falla `umbral` veces seguidas. Existe por el 2026-11-05: `tailscaled` y `NetworkManager` murieron a las
19:59 y nadie lo supo en 17,6 h porque todo lo que vigila corria dentro de la ATOM o solo miraba el SSH de la red de casa.

Configuracion (`alarma.json` en el directorio de datos; NO va al repo porque lleva el tema de ntfy, que es el secreto):
  {"checks": [{"nombre": "ssh-casa", "host": "192.0.2.25", "puerto": 22}, ...],
   "ntfy_url": "https://ntfy.sh/<tema-aleatorio>", "umbral": 3, "intervalo_s": 30,
   "recordatorio_s": 3600, "latido_diario_s": 86400}

Uso: `bb_alarma.py run --datos DIR [--ciclos N]` | `bb_alarma.py probar --datos DIR` (envia un aviso de prueba y sale).
Cada ciclo escribe una fila en `alarma.jsonl`; un aviso que no se pudo enviar se reintenta en el ciclo siguiente.
Limite declarado: si la Dell o su red caen, la alarma calla; por eso el `latido_diario_s` ("alarma viva") llega cada dia y
su ausencia es la senal.
"""
import argparse
import json
import socket
import sys
import time
import urllib.request
from pathlib import Path

DEFECTO = {"umbral": 3, "intervalo_s": 30, "recordatorio_s": 3600, "latido_diario_s": 86400, "timeout_s": 3.0}


def decide(estado, resultados, ahora, cfg):
    """PURA. `estado` = {"fallos": {nombre: n}, "avisado": {nombre: epoch}, "ultimo_latido": epoch, "desde": {nombre: epoch}};
    `resultados` = {nombre: bool}. Devuelve (estado_nuevo, [(clave, texto)]): cada mensaje lleva una clave para confirmar su envio."""
    fallos = dict(estado.get("fallos", {}))
    avisado = dict(estado.get("avisado", {}))
    desde = dict(estado.get("desde", {}))
    msgs = []
    for nombre, ok in resultados.items():
        if ok:
            if nombre in avisado:
                msgs.append((("vuelve", nombre), f"ATOM: {nombre} volvio (caido desde {_hora(desde.get(nombre, ahora))})"))
            fallos[nombre] = 0
            if nombre not in avisado:  # con aviso de caida pendiente de "vuelve", se conserva hasta confirmarlo
                desde.pop(nombre, None)
            continue
        fallos[nombre] = fallos.get(nombre, 0) + 1
        if fallos[nombre] == 1:
            desde[nombre] = ahora
        if fallos[nombre] >= cfg["umbral"] and (nombre not in avisado or ahora - avisado[nombre] >= cfg["recordatorio_s"]):
            vivos = sorted(n for n, v in resultados.items() if v)
            sigue = f"; responden: {', '.join(vivos)}" if vivos else "; no responde ningun camino"
            msgs.append((("cae", nombre), f"ATOM: {nombre} caido desde {_hora(desde[nombre])}{sigue}"))
    ult = estado.get("ultimo_latido", 0)
    if ahora - ult >= cfg["latido_diario_s"]:
        msgs.append((("latido", ""), "Alarma de la ATOM viva en la Dell; caminos: " + ", ".join(f"{n}={'ok' if v else 'CAIDO'}" for n, v in sorted(resultados.items()))))
    return {"fallos": fallos, "avisado": avisado, "desde": desde, "ultimo_latido": ult}, msgs


def confirma(estado, clave, ahora):
    """Marca como enviado un mensaje (solo si el envio salio bien): asi uno fallido se reintenta."""
    tipo, nombre = clave
    if tipo == "cae":
        estado["avisado"][nombre] = ahora
    elif tipo == "latido":
        estado["ultimo_latido"] = ahora
    elif tipo == "vuelve":
        estado["avisado"].pop(nombre, None)
        estado["desde"].pop(nombre, None)
    return estado


def _hora(epoch):
    return time.strftime("%H:%M:%S", time.localtime(epoch))


def tcp_ok(host, puerto, timeout):
    try:
        with socket.create_connection((host, puerto), timeout=timeout):
            return True
    except OSError:
        return False


def envia(url, texto, titulo="bb-alarma"):
    req = urllib.request.Request(url, data=texto.encode("utf-8"), method="POST",
                                 headers={"Title": titulo.encode("ascii", "ignore").decode(), "Priority": "high", "Tags": "warning"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return 200 <= r.status < 300


def carga(datos):
    cfg = dict(DEFECTO)
    cfg.update(json.loads((Path(datos) / "alarma.json").read_text(encoding="utf-8")))
    if not cfg.get("checks") or not str(cfg.get("ntfy_url", "")).startswith("https://"):
        raise SystemExit("alarma.json: faltan 'checks' o 'ntfy_url' https")
    return cfg


def ciclo(estado, cfg, ahora, sonda=tcp_ok, manda=envia):
    res = {c["nombre"]: sonda(c["host"], c["puerto"], cfg["timeout_s"]) for c in cfg["checks"]}
    estado, msgs = decide(estado, res, ahora, cfg)
    enviados, errores = [], []
    for clave, texto in msgs:
        try:
            if manda(cfg["ntfy_url"], texto):
                estado = confirma(estado, clave, ahora)
                enviados.append(texto)
            else:
                errores.append(f"{clave}: respuesta no 2xx")
        except Exception as e:  # red caida o ntfy caido: se reintenta en el ciclo siguiente
            errores.append(f"{clave}: {type(e).__name__}")
    return estado, {"ts": ahora, "caminos": res, "enviados": enviados, "errores": errores}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Alarma externa de la ATOM (ver el docstring).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("run", "probar"):
        p = sub.add_parser(n)
        p.add_argument("--datos", required=True)
    sub.choices["run"].add_argument("--ciclos", type=int, default=0, help="N ciclos y salir (pruebas); 0 = para siempre")
    a = ap.parse_args(argv)
    cfg = carga(a.datos)
    if a.cmd == "probar":
        print("enviado" if envia(cfg["ntfy_url"], "Aviso de prueba: la alarma de la ATOM llega a este telefono.") else "no enviado")
        return 0
    estado, n = {"fallos": {}, "avisado": {}, "desde": {}, "ultimo_latido": 0}, 0
    log = Path(a.datos) / "alarma.jsonl"
    while True:
        estado, fila = ciclo(estado, cfg, time.time())
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
        n += 1
        if a.ciclos and n >= a.ciclos:
            return 0
        time.sleep(cfg["intervalo_s"])


if __name__ == "__main__":
    sys.exit(main())
