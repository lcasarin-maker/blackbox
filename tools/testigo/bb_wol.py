#!/usr/bin/env python3
"""bb-wol: envia un paquete magico de Wake-on-LAN. Un solo archivo de Python stdlib (3.8+) que corre en la Dell.

Para que sirve: encender la ATOM tras un apagado completo (`poweroff`), que es la unica forma de cortar la alimentacion de la
GPU sin tocar el boton. El 2026-11-09 la vuelta de 7.0 a 6.17 con `reboot` dejo la GPU en GSP Timeout (Xid 119) y hubo que
apagar a mano; un apagado completo seguido de este paquete lo haria sin ir a la maquina.

Uso:
  BB_WOL_CONFIG=/ruta/privada/wol.json python bb_wol.py  # destino configurado localmente
  python bb_wol.py --mac 02-00-00-00-00-01 --broadcast 192.0.2.255 --puerto 9
  python bb_wol.py --seco           # no envia: imprime longitud y destino (para probar sin efecto)

Salida: 0 enviado (o --seco), 2 si la MAC o los argumentos son invalidos. Que la ATOM encienda NO lo prueba este programa:
solo una prueba real (ATOM apagada, paquete enviado, ATOM encendida) lo prueba.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import sys


def paquete_magico(mac: str) -> bytes:
    """6 bytes 0xFF y la MAC repetida 16 veces: 102 bytes. Una MAC que no son 6 octetos hex levanta ValueError."""
    partes = mac.replace("-", ":").split(":")
    if len(partes) != 6:
        raise ValueError(f"MAC invalida: {mac!r}")
    octetos = bytes(int(p, 16) for p in partes)  # ValueError si un octeto no es hex o pasa de 255
    return b"\xff" * 6 + octetos * 16


def envia(paquete: bytes, destino: str, puerto: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(paquete, (destino, puerto))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Wake-on-LAN")
    ap.add_argument("--mac", default=None)
    ap.add_argument("--broadcast", default=None)
    ap.add_argument("--puerto", type=int, default=9)
    ap.add_argument("--seco", action="store_true")
    a = ap.parse_args(argv)
    config = os.environ.get("BB_WOL_CONFIG")
    try:
        cfg = json.loads(Path(config).read_text()) if config else {}
    except (OSError, ValueError) as e:
        ap.error(f"configuracion WoL: {e}")
    if not isinstance(cfg, dict):
        ap.error("configuracion WoL: se espera un objeto JSON")
    a.mac = a.mac or cfg.get("mac")
    a.broadcast = a.broadcast or cfg.get("broadcast")
    if not a.mac or not a.broadcast:
        ap.error("configurar BB_WOL_CONFIG o indicar --mac y --broadcast")
    try:
        p = paquete_magico(a.mac)
    except ValueError as e:
        print(f"bb-wol: {e}", file=sys.stderr)
        return 2
    if a.seco:
        print(f"bb-wol: seco, {len(p)} bytes a {a.broadcast}:{a.puerto} para {a.mac}")
        return 0
    envia(p, a.broadcast, a.puerto)
    print(f"bb-wol: enviado, {len(p)} bytes a {a.broadcast}:{a.puerto} para {a.mac}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
