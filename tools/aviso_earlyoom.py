#!/usr/bin/env python3
"""Aviso de intervencion de earlyoom (interruptor `aviso_earlyoom`): FEATURE-DELL-BRAZO-DE-BB-REPARACION-REMOTA-01, parte de aviso.

earlyoom mata procesos cuando la memoria baja del 10 %, y hasta hoy nadie se enteraba: el 2026-11-05 envio 54 senales y el
2026-11-06 otras 59, sobre ChatGPT y Chrome mientras un contenedor de GPU tenia 87 GiB. Este vigilante lee el diario de
earlyoom, agrupa las senales en una rafaga (20 s sin senales nuevas la cierran) y manda UN aviso por rafaga con quien murio, la
memoria minima vista y los mayores consumidores de GPU con la etiqueta `lanzado_por` de su contenedor.

`off` no hace nada; `observar` registra el aviso que habria enviado; `actuar` ademas lo manda por ntfy. La direccion de ntfy
(con su tema secreto) vive en `~/.config/blackbox/ntfy_url` (modo 600), nunca en el repo.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from tools import interruptores

NOMBRE = "aviso_earlyoom"
QUIETO_S = 20.0
KILL = re.compile(r'sending (SIG[A-Z]+) to process (\d+) uid (\d+) "(.*)": badness (\d+), VmRSS (\d+) MiB')
AVAIL = re.compile(r"mem avail:\s*(\d+) of (\d+) MiB \(\s*([\d.]+)%\)")


def parsea(linea: str) -> dict[str, Any] | None:
    m = KILL.search(linea)
    if m:
        return {"senal": m[1], "pid": int(m[2]), "uid": int(m[3]), "nombre": m[4], "badness": int(m[5]), "rss_mib": int(m[6])}
    m = AVAIL.search(linea)
    if m:
        return {"avail_pct": float(m[3])}
    return None


class Rafaga:
    """Acumula las senales de una intervencion. Una linea de memoria solo cuenta mientras hay una rafaga abierta."""

    def __init__(self, quieto_s: float = QUIETO_S) -> None:
        self.quieto_s = quieto_s
        self.kills: list[dict[str, Any]] = []
        self.min_pct: float | None = None
        self.ultimo = 0.0

    def alimenta(self, linea: str, t: float) -> None:
        ev = parsea(linea)
        if ev is None:
            return
        if "senal" in ev:
            self.kills.append(ev)
            self.ultimo = t
        elif self.kills:
            self.min_pct = ev["avail_pct"] if self.min_pct is None else min(self.min_pct, ev["avail_pct"])

    def lista(self, t: float) -> bool:
        return bool(self.kills) and t - self.ultimo >= self.quieto_s

    def cierra(self) -> dict[str, Any]:
        nombres = Counter(k["nombre"] for k in self.kills)
        res = {"senales": len(self.kills), "sigkill": sum(k["senal"] == "SIGKILL" for k in self.kills),
               "nombres": nombres.most_common(5), "min_pct": self.min_pct}
        self.kills, self.min_pct = [], None
        return res


def texto(res: dict[str, Any], gpu: list[dict[str, Any]]) -> str:
    quien = ", ".join(f"{n}x{c}" for n, c in res["nombres"])
    pct = f"; memoria libre minima {res['min_pct']:.1f} %" if res["min_pct"] is not None else ""
    base = f"earlyoom mato {res['senales']} procesos ({res['sigkill']} con SIGKILL): {quien}{pct}."
    if not gpu:
        return base + " GPU: sin consumidores legibles."
    top = "; ".join(f"{g['nombre']} {g['gib']:.1f} GiB (lanzado_por={g['lanzado_por']})" for g in gpu)
    return base + " Mayor GPU ahora: " + top


def culpables_gpu(run: Callable[..., Any] = subprocess.run, cgroup_de: Callable[[int], str] | None = None) -> list[dict[str, Any]]:
    """Los 3 mayores consumidores de GPU, con el nombre y la etiqueta `lanzado_por` de su contenedor Docker si lo tienen."""
    cgroup_de = cgroup_de or (lambda pid: Path(f"/proc/{pid}/cgroup").read_text(encoding="utf-8"))
    try:
        r = run(["nvidia-smi", "--query-compute-apps=pid,used_memory", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return []
    filas = []
    for linea in (r.stdout or "").splitlines():
        try:
            pid, mib = (int(x) for x in linea.split(","))
        except ValueError:
            continue
        filas.append((mib, pid))
    out = []
    for mib, pid in sorted(filas, reverse=True)[:3]:
        nombre, etiqueta = f"pid {pid}", "?"
        try:
            m = re.search(r"docker-([0-9a-f]{12})", cgroup_de(pid))
            if m:
                i = run(["docker", "inspect", "--format", '{{.Name}}|{{index .Config.Labels "lanzado_por"}}', m[1]],
                        capture_output=True, text=True, timeout=20, check=False)
                n, _, e = (i.stdout or "").strip().partition("|")
                nombre, etiqueta = n.lstrip("/") or nombre, e or "sin etiqueta"
        except (OSError, subprocess.SubprocessError):
            pass
        out.append({"nombre": nombre, "gib": mib / 1024, "lanzado_por": etiqueta})
    return out


def url_ntfy() -> str | None:
    try:
        u = (Path.home() / ".config/blackbox/ntfy_url").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return u if u.startswith("https://") else None


def manda(url: str, mensaje: str) -> bool:
    req = urllib.request.Request(url, data=mensaje.encode("utf-8"), method="POST",
                                 headers={"Title": "bb-earlyoom", "Priority": "high", "Tags": "skull"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return 200 <= r.status < 300


def procesa(res: dict[str, Any], gpu: list[dict[str, Any]], modo: str, url: str | None,
            envia: Callable[[str, str], bool] = manda, registra: Callable[..., None] = interruptores.registra) -> dict[str, Any]:
    """Un aviso por rafaga segun el modo. Devuelve lo registrado."""
    msg = texto(res, gpu)
    fila: dict[str, Any] = {"modo": modo, "habria_avisado": modo != "off", "mensaje": msg, "senales": res["senales"], "enviado": False}
    if modo == "actuar":
        if url is None:
            fila["error"] = "sin ~/.config/blackbox/ntfy_url"
        else:
            try:
                fila["enviado"] = envia(url, msg)
            except Exception as e:  # ntfy o la red caidos: queda en el registro, no tumba al vigilante
                fila["error"] = type(e).__name__
    if modo != "off":
        registra(NOMBRE, fila)
    return fila


def main() -> int:  # pragma: no cover  (bucle sobre `journalctl -f`; la logica esta en Rafaga/procesa y se prueba aparte)
    import select

    p = subprocess.Popen(["journalctl", "-u", "earlyoom", "-f", "-n", "0", "-o", "cat"],
                         stdout=subprocess.PIPE, text=True, bufsize=1)
    assert p.stdout is not None
    rafaga = Rafaga()
    while True:
        listo, _, _ = select.select([p.stdout], [], [], 5.0)
        ahora = time.monotonic()
        if listo:
            linea = p.stdout.readline()
            if not linea:
                return 1  # journalctl termino: systemd reinicia la unidad
            rafaga.alimenta(linea, ahora)
        if rafaga.lista(ahora):
            res = rafaga.cierra()
            modo = interruptores.modo(NOMBRE)
            if modo != "off":
                procesa(res, culpables_gpu(), modo, url_ntfy())


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main() if os.environ.get("BB_AVISO_EARLYOOM_DESACTIVADO") is None else 0)
