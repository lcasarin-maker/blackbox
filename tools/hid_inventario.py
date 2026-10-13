"""Sensor de solo lectura: inventario USB-HID por kernel y deteccion de HID_PERDIDO.

Lee /sys/bus/usb/devices/*/ (interfaces con bInterfaceClass 03) y
/proc/bus/input/devices. Guarda por kernel el conjunto de HID vistos y, cuando
cambia el kernel (o un HID visto pierde su driver), reporta HID_PERDIDO.
Primera corrida: solo linea base. Sin HID conectado y sin antecedente: INDETERMINADO.
No carga modulos, no escribe fuera del archivo de estado.

Salida: JSON. rc 0 = BASELINE / SIN_HALLAZGOS, 1 = HID_PERDIDO, 2 = INDETERMINADO.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

SYS_USB = Path("/sys/bus/usb/devices")
PROC_INPUT = Path("/proc/bus/input/devices")
RC = {"BASELINE": 0, "SIN_HALLAZGOS": 0, "HID_PERDIDO": 1, "INDETERMINADO": 2}


def estado_por_defecto() -> Path:
    base = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))
    return base / "hid_inventario.json"


def _leer(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8").strip()
    except OSError:
        return ""  # atributo sysfs ausente: campo vacio, no es error del sensor


def _puertos_input(proc_input: Path, errores: list[str]) -> dict[str, int]:
    """Cuenta nodos de entrada por puerto USB ('1.3') segun Phys=usb-...-<puerto>/inputN."""
    try:
        texto = proc_input.read_text(encoding="utf-8")
    except OSError as exc:
        errores.append(f"input_ilegible:{exc.__class__.__name__}")
        return {}
    cuenta: dict[str, int] = {}
    for m in re.finditer(r"^P: Phys=usb-.*-([0-9.]+)/input\d+", texto, re.M):
        cuenta[m.group(1)] = cuenta.get(m.group(1), 0) + 1
    return cuenta


def inventario(sys_usb: Path = SYS_USB, proc_input: Path = PROC_INPUT) -> dict[str, Any]:
    """Devuelve {'hid': {vid:pid: {...}}, 'errores': [...]}; clave unica por vid:pid."""
    errores: list[str] = []
    if not sys_usb.is_dir():
        return {"hid": {}, "errores": ["sysfs_usb_ausente"]}
    entradas = _puertos_input(proc_input, errores)
    hid: dict[str, dict[str, Any]] = {}
    for iface in sorted(sys_usb.glob("*:*")):
        if _leer(iface / "bInterfaceClass") != "03":
            continue
        dev = sys_usb / iface.name.split(":")[0]
        vidpid = f"{_leer(dev / 'idVendor')}:{_leer(dev / 'idProduct')}"
        drv = (iface / "driver").resolve().name if (iface / "driver").exists() else ""
        puerto = dev.name.split("-", 1)[-1]
        r = hid.setdefault(vidpid, {"nombre": _leer(dev / "product"), "puertos": [],
                                    "drivers": [], "sin_driver": 0, "input": 0})
        if puerto not in r["puertos"]:
            r["puertos"].append(puerto)
            r["input"] += entradas.get(puerto, 0)
        if drv:
            if drv not in r["drivers"]:
                r["drivers"].append(drv)
        else:
            r["sin_driver"] += 1
    return {"hid": hid, "errores": errores}


def evaluar(actual: dict[str, Any], estado: dict[str, Any], kernel: str) -> tuple[str, list[dict[str, str]], dict[str, Any]]:
    """Compara contra el estado; devuelve (veredicto, hallazgos, estado_nuevo)."""
    hid = actual["hid"]
    nuevo = json.loads(json.dumps(estado)) if estado else {"kernels": {}, "ultimo": ""}
    previo = estado.get("ultimo", "") if estado else ""
    ref_k = estado.get("kernels", {}).get(previo) if previo else None
    hallazgos: list[dict[str, str]] = []

    if actual["errores"] and not hid:
        return "INDETERMINADO", [{"motivo": e} for e in actual["errores"]], nuevo
    if ref_k is None:
        if not hid:
            return "INDETERMINADO", [{"motivo": "sin_hid_conectado_y_sin_linea_base"}], nuevo
        nuevo["kernels"][kernel] = {"vistos": hid, "heredados": {}}
        nuevo["ultimo"] = kernel
        return "BASELINE", [], nuevo

    cambio_kernel = previo != kernel
    esperados = ref_k["vistos"]
    heredados = {**ref_k.get("heredados", {}), **esperados} if cambio_kernel else ref_k.get("heredados", {})
    retenidos: dict[str, Any] = {}  # hallazgos que siguen abiertos: se heredan hasta que se resuelvan
    for clave in {**heredados, **esperados}:
        ref = heredados.get(clave) or esperados[clave]
        ahora = hid.get(clave)
        motivo = ""
        if ahora is None:
            if cambio_kernel or clave in heredados:
                motivo = "ausente_tras_cambio_de_kernel"
        elif ref["drivers"] and not ahora["drivers"]:
            motivo = "sin_driver"
        elif ref["input"] > 0 and ahora["input"] == 0 and (cambio_kernel or clave in heredados):
            motivo = "sin_nodo_input"
        if motivo:
            hallazgos.append({"hallazgo": "HID_PERDIDO", "dispositivo": clave,
                              "nombre": ref["nombre"] or clave, "motivo": motivo})
            retenidos[clave] = ref
    if not hid and not hallazgos:
        return "INDETERMINADO", [{"motivo": "sin_hid_conectado"}], nuevo
    entrada = nuevo["kernels"].setdefault(kernel, {"vistos": {}, "heredados": {}})
    entrada["heredados"] = retenidos
    # ponytail: un HID retirado a mano tras un cambio de kernel alerta hasta que reaparezca, techo: un solo operador, disparador: falsas alarmas reportadas
    entrada["vistos"] = hid if hid else entrada["vistos"]
    nuevo["ultimo"] = kernel
    return ("HID_PERDIDO" if hallazgos else "SIN_HALLAZGOS"), hallazgos, nuevo


def _guardar(ruta: Path, estado: dict[str, Any]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ruta.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(estado, fh, sort_keys=True)
    os.replace(tmp, ruta)


def correr(sys_usb: Path, proc_input: Path, ruta: Path, kernel: str, guardar: bool = True) -> dict[str, Any]:
    estado: dict[str, Any] = {}
    if ruta.exists():
        try:
            estado = json.loads(ruta.read_text(encoding="utf-8"))
            if not isinstance(estado, dict):
                raise ValueError("estado no es objeto")
        except (OSError, ValueError) as exc:
            # estado ilegible: no se sobrescribe ni se afirma nada
            return {"veredicto": "INDETERMINADO", "kernel": kernel, "hallazgos": [{"motivo": f"estado_ilegible:{exc.__class__.__name__}"}],
                    "hid": {}, "could_not_run": 1}
    actual = inventario(sys_usb, proc_input)
    veredicto, hallazgos, nuevo = evaluar(actual, estado, kernel)
    if guardar and nuevo.get("ultimo") and nuevo != estado:
        _guardar(ruta, nuevo)
    return {"veredicto": veredicto, "kernel": kernel, "hallazgos": hallazgos, "hid": actual["hid"],
            "errores": actual["errores"], "could_not_run": int(veredicto == "INDETERMINADO" and bool(actual["errores"]))}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sys-usb", type=Path, default=SYS_USB)
    ap.add_argument("--input", type=Path, default=PROC_INPUT)
    ap.add_argument("--estado", type=Path, default=None)
    ap.add_argument("--kernel", default=platform.release())
    ap.add_argument("--no-guardar", action="store_true")
    a = ap.parse_args(argv)
    out = correr(a.sys_usb, a.input, a.estado or estado_por_defecto(), a.kernel, not a.no_guardar)
    print(json.dumps(out, sort_keys=True, ensure_ascii=False))
    return RC[out["veredicto"]]


if __name__ == "__main__":
    sys.exit(main())
