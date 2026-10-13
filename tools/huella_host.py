#!/usr/bin/env python3
"""Huella de identidad y estado del host (un solo nodo GB10) con deteccion de cambios (interruptor `huella_host`).

Sirve para validar en vivo, sin intervenir, afirmaciones de hilos del foro de NVIDIA: version de SO, kernel, driver,
paquetes OTA, firmware del CX7, driver por interfaz de red (binding equivocado de Realtek tras reinicio), velocidad USB
(caida a 480 Mbps), fuentes apt (mezcla archive y ports en arm64), watchdog, GSP/GPU, pstore y clock lock.

Cada sonda devuelve un valor o la cadena "NOT_COLLECTED: <motivo>": nunca un valor inventado ni un vacio silencioso.
Todas son de solo lectura, sin sudo, con la raiz y el ejecutor inyectables. `diferencias` compara dos huellas y
no oculta una sonda que pierde o recupera su lectura. En `observar` registra "habria actuado" cuando algo cambio; en
`actuar` NO hay accion cableada: declara UNSUPPORTED.
Limite declarado: el watchdog reporta solo lo leido; quien es su propietario no se infiere.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tools import interruptores

NOMBRE = "huella_host"
NC = "NOT_COLLECTED"
PAQUETES_OTA = ("dgx-spark-ota-update-meta", "nvidia-spark-ota-check")

Correr = Callable[..., Any]


def _nc(motivo: str) -> str:
    return f"{NC}: {motivo}"


def es_nc(valor: Any) -> bool:
    return isinstance(valor, str) and valor.startswith(NC)


def _lee(ruta: Path) -> str | None:
    try:
        return ruta.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def _comando(correr: Correr, args: list[str]) -> str | None:
    """Salida estandar de un comando, o None si no corre, falla o excede 10 s."""
    try:
        r = correr(args, capture_output=True, text=True, check=False, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return str(r.stdout).strip()


def _hijos(directorio: Path, patron: str) -> list[Path]:
    return sorted(directorio.glob(patron))  # un directorio ausente da lista vacia


def sonda_os_release(raiz: Path, correr: Correr) -> Any:
    txt = _lee(raiz / "etc/os-release")
    if txt is None:
        return _nc("/etc/os-release ilegible")
    m = re.search(r'^PRETTY_NAME="?([^"\n]*)"?', txt, re.M)
    out: dict[str, str] = {"pretty_name": m.group(1) if m else _nc("sin PRETTY_NAME")}
    dgx = _lee(raiz / "etc/dgx-release")
    if dgx is not None:
        # el numero de serie no entra a la huella: el archivo viaja a evidencias y a posts publicos
        out["dgx_release"] = "\n".join(l for l in dgx.splitlines() if "SERIAL" not in l.upper())
    return out


def sonda_kernel(raiz: Path, correr: Correr) -> Any:
    return platform.release() or _nc("platform.release vacio")


def sonda_driver_nvidia(raiz: Path, correr: Correr) -> Any:
    txt = _lee(raiz / "proc/driver/nvidia/version")
    if not txt:
        return _nc("/proc/driver/nvidia/version ausente o vacio")
    return txt.splitlines()[0]


def sonda_ota(raiz: Path, correr: Correr) -> Any:
    out: dict[str, str] = {}
    for p in PAQUETES_OTA:
        v = _comando(correr, ["dpkg-query", "-W", "-f=${Version}", p])
        out[p] = v if v else _nc(f"{p} no instalado o dpkg-query no corre")
    return out


def sonda_firmware_cx7(raiz: Path, correr: Correr) -> Any:
    out: dict[str, dict[str, str]] = {}
    for fw in _hijos(raiz / "sys/class/infiniband", "*/fw_ver"):
        dev = fw.parent
        v = _lee(fw)
        psid = _lee(dev / "board_id")
        out[dev.name] = {"fw_ver": v or _nc("fw_ver ilegible"), "psid": psid or _nc("psid no expuesto")}
    return out or _nc("sin /sys/class/infiniband/*/fw_ver")


def sonda_driver_red(raiz: Path, correr: Correr) -> Any:
    out: dict[str, str] = {}
    for iface in _hijos(raiz / "sys/class/net", "*"):
        enlace = iface / "device/driver"
        if enlace.is_symlink():
            out[iface.name] = os.path.basename(os.readlink(enlace))
    return out or _nc("ninguna interfaz con device/driver")


def sonda_usb(raiz: Path, correr: Correr) -> Any:
    out: dict[str, dict[str, str]] = {}
    for s in _hijos(raiz / "sys/bus/usb/devices", "*/speed"):
        dev = s.parent
        out[dev.name] = {"speed_mbps": _lee(s) or _nc("speed ilegible"), "product": _lee(dev / "product") or _nc("sin product")}
    return out or _nc("sin /sys/bus/usb/devices/*/speed")


def _fuentes_apt(raiz: Path) -> list[Path]:
    base = raiz / "etc/apt"
    return [base / "sources.list", *_hijos(base / "sources.list.d", "*.sources"), *_hijos(base / "sources.list.d", "*.list")]


def sonda_apt(raiz: Path, correr: Correr) -> Any:
    textos = [t for t in (_lee(f) for f in _fuentes_apt(raiz)) if t is not None]
    if not textos:
        return _nc("sin fuentes apt legibles")
    todo = "\n".join(l for t in textos for l in t.splitlines() if not l.lstrip().startswith("#"))
    archive, ports = "archive.ubuntu.com" in todo, "ports.ubuntu.com" in todo
    return {"archive": archive, "ports": ports, "mezcla_archive_y_ports": archive and ports}


def sonda_watchdog(raiz: Path, correr: Correr) -> Any:
    sysfs: dict[str, dict[str, str]] = {}
    for wd in _hijos(raiz / "sys/class/watchdog", "*"):
        sysfs[wd.name] = {k: _lee(wd / k) or _nc(f"{k} ilegible") for k in ("identity", "state")}
    dev = [p.name for p in _hijos(raiz / "dev", "watchdog*")]
    if not sysfs and not dev:
        return _nc("sin /sys/class/watchdog ni /dev/watchdog*")
    return {"sysfs": sysfs, "dev": dev}


def _smi(correr: Correr, consulta: str, extra: str = "") -> str | None:
    return _comando(correr, ["nvidia-smi", f"--query-gpu={consulta}", f"--format=csv,noheader{extra}"])


def sonda_gpu(raiz: Path, correr: Correr) -> Any:
    smi = _smi(correr, "name,driver_version,vbios_version")
    pci = [p.name for p in _hijos(raiz / "sys/bus/pci/devices", "*") if (_lee(p / "vendor") or "") == "0x10de" and (_lee(p / "class") or "").startswith("0x03")]
    if not smi:
        return {"smi": _nc("nvidia-smi sin salida"), "pci_nvidia": pci}
    return {"smi": smi, "pci_nvidia": pci}


def sonda_pstore(raiz: Path, correr: Correr) -> Any:
    out: dict[str, Any] = {}
    for rel in ("sys/fs/pstore", "var/lib/systemd/pstore"):
        d = raiz / rel
        try:
            out[rel] = len(list(d.iterdir()))
        except OSError:
            out[rel] = _nc(f"{rel} ausente o ilegible")
    return out


def sonda_clock_lock(raiz: Path, correr: Correr) -> Any:
    v = _smi(correr, "clocks.max.sm", ",nounits")
    return v if v else _nc("nvidia-smi sin salida")


SONDAS: dict[str, Callable[[Path, Correr], Any]] = {
    "os_release": sonda_os_release,
    "kernel": sonda_kernel,
    "driver_nvidia": sonda_driver_nvidia,
    "ota": sonda_ota,
    "firmware_cx7": sonda_firmware_cx7,
    "driver_red": sonda_driver_red,
    "usb": sonda_usb,
    "apt": sonda_apt,
    "watchdog": sonda_watchdog,
    "gpu": sonda_gpu,
    "pstore": sonda_pstore,
    "clock_lock": sonda_clock_lock,
}


def recoge(raiz: Path = Path("/"), correr: Correr = subprocess.run) -> dict[str, Any]:
    """Una lectura de todas las sondas; una sonda que lanza se registra como NOT_COLLECTED, no tumba la huella."""
    out: dict[str, Any] = {}
    for nombre, f in SONDAS.items():
        try:
            out[nombre] = f(raiz, correr)
        except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError) as e:  # una sonda rota (lectura, formato, subproceso) no oculta las demas
            out[nombre] = _nc(f"{type(e).__name__}: {e}")
    return out


def diferencias(previo: dict[str, Any], ahora: dict[str, Any]) -> list[dict[str, Any]]:
    """Pura. Una entrada por sonda cuyo valor cambio; pasar a/desde NOT_COLLECTED lleva etiqueta propia."""
    out: list[dict[str, Any]] = []
    for sonda in sorted(set(previo) | set(ahora)):
        antes = previo.get(sonda, _nc("sonda ausente en la huella previa"))
        despues = ahora.get(sonda, _nc("sonda ausente en la huella actual"))
        if antes == despues:
            continue
        fila: dict[str, Any] = {"sonda": sonda, "antes": antes, "despues": despues}
        if es_nc(despues) and not es_nc(antes):
            fila["etiqueta"] = "perdida_de_lectura"
        elif es_nc(antes) and not es_nc(despues):
            fila["etiqueta"] = "lectura_recuperada"
        out.append(fila)
    return out


def _ruta_huella() -> Path:
    return Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox")) / "huella_host.json"


def paso(modo_actual: str, ahora: dict[str, Any] | None = None, estado: Path | None = None, directorio: Path | None = None) -> dict[str, Any] | None:
    """`off` no lee ni escribe. En `observar` guarda siempre la huella; registra un evento si es la primera o si hubo cambios."""
    if modo_actual == "off":
        return None
    ahora = recoge() if ahora is None else ahora
    estado = estado or _ruta_huella()
    try:
        previo = json.loads(estado.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previo = None
    estado.parent.mkdir(parents=True, exist_ok=True)
    estado.write_text(json.dumps(ahora, indent=1, ensure_ascii=False), encoding="utf-8")
    if not isinstance(previo, dict):
        ev: dict[str, Any] = {"modo": modo_actual, "primera": True, "habria_actuado": False}
    else:
        difs = diferencias(previo, ahora)
        if not difs:
            return None
        ev = {"modo": modo_actual, "primera": False, "habria_actuado": True, "diferencias": difs}
    if modo_actual == "actuar":
        ev["accion"] = "UNSUPPORTED: sin accion cableada; la huella solo observa"
    interruptores.registra(NOMBRE, ev, directorio)
    return ev


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="huella_host")
    ap.add_argument("--paso", action="store_true", help="un paso segun el interruptor huella_host (lo corre bb-huella.timer)")
    a = ap.parse_args(argv)
    if a.paso:
        paso(interruptores.modo(NOMBRE))
    else:
        print(json.dumps(recoge(), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
