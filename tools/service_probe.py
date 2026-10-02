#!/usr/bin/env python3
"""Bounded loopback SSH banner probe used only when explicitly configured."""

from __future__ import annotations

import ipaddress
import json
import socket
import sys
import time


def probe(host: str, port_text: str, timeout_text: str) -> dict[str, object]:
    try:
        address = ipaddress.ip_address(host)
        port = int(port_text)
        timeout_s = float(timeout_text)
    except ValueError:
        return {"estado": "ERROR", "motivo": "dirección, puerto o timeout inválido"}
    if not address.is_loopback:
        return {"estado": "ERROR", "motivo": "solo se permiten direcciones loopback"}
    if not 1 <= port <= 65535 or not 0.05 <= timeout_s <= 10:
        return {"estado": "ERROR", "motivo": "puerto/timeout fuera de rango"}

    start = time.monotonic()
    deadline = start + timeout_s
    try:
        with socket.create_connection((str(address), port), timeout=max(0.001, deadline - time.monotonic())) as conn:
            data = bytearray()
            while len(data) < 256 and b"\n" not in data:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("overall probe deadline exceeded")
                conn.settimeout(remaining)
                chunk = conn.recv(min(64, 256 - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
        terminated = b"\n" in data
        banner = bytes(data).split(b"\n", 1)[0].rstrip(b"\r")
        elapsed = round((time.monotonic() - start) * 1000)
        parts = banner.split(b"-", 2)
        valid_ident = (terminated and len(banner) + 2 <= 255 and
                       len(parts) == 3 and parts[0] == b"SSH" and
                       parts[1] in (b"2.0", b"1.99") and bool(parts[2]) and
                       all(32 <= byte < 127 for byte in banner))
        if valid_ident:
            return {"estado": "OK", "ms": elapsed}
        return {"estado": "ERROR", "motivo": "respuesta sin identificación SSH completa", "ms": elapsed}
    except (OSError, TimeoutError) as exc:
        elapsed = round((time.monotonic() - start) * 1000)
        state = "TIMEOUT" if isinstance(exc, TimeoutError) or isinstance(exc, socket.timeout) else "ERROR"
        return {"estado": state, "motivo": type(exc).__name__, "ms": elapsed}


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(2)
    print(json.dumps(probe(*sys.argv[1:]), separators=(",", ":")))
