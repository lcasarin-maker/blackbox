#!/usr/bin/env python3
"""Hasta que etapa llego el arranque ANTERIOR, leido de las marcas de `bb-etapa@.service`.

Cada etapa de arranque de sistema (adopted/system-units/, LEEME-etapas.md) deja una linea
`{boot_id, etapa, monotonic, realtime}` en /var/lib/blackbox/arranque/etapas.jsonl (y la anterior
generacion en `.1`). En el primer arranque SANO (el actual llego a `multi-user`) esto anota una fila
en `$BLACKBOX_DATA/etapas_arranque.jsonl` con hasta donde llego el arranque previo y el contexto del
actual: bootstatus y estado sysfs de cada watchdog (sin abrir /dev/watchdog), la linea de comandos
del kernel, srcversion y firmante del modulo nvidia y dmem.capacity. Una fila por arranque: correrlo
otra vez en el mismo arranque no escribe nada. Lo corre `systemd/bb-reboot-verdict.service` como
`ExecStartPre` (a los 3 min del arranque, cuando ya llego a multi-user); su rc no frena el veredicto.

Esquema de la fila (lo lee otro paquete; `esquema` sube si cambia):
  esquema, ts, boot_id_actual, etapas_actual, boot_id_anterior, ultima_etapa_anterior,
  anterior {boot_id, ultima_etapa, cadena {etapa: monotonic}, ramas {rama: monotonic|null},
            faltan, sesiones_sistema, otras, marcas}, contexto {...}, descartadas, limite.
Un valor que no se pudo leer es la cadena "NOT_COLLECTED: <motivo>", nunca un vacio.

La cadena es el camino critico (local-fs < basic < multi-user < gdm < graphical < sesion-usuario);
network-online y gpu-lista son ramas en paralelo y no cuentan para `ultima_etapa`. `sesion-<uid>`
con uid >= 1000 es la sesion de una persona; con uid menor es el saludo de GDM (sesiones_sistema).

Limite: un arranque que no llego a local-fs no deja marca en disco, y el resumen no lo distingue de
uno que no existio: ese caso solo se ve por la ausencia de `bb-etapa` en la consola serie o pstore.

rc: 0 fila escrita o ya anotada; 1 el arranque actual aun no es sano (nada escrito);
2 COULD_NOT_RUN (sin boot_id actual o etapas.jsonl ilegible).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NC = "NOT_COLLECTED"
ESQUEMA = 1
ETAPAS = Path("/var/lib/blackbox/arranque/etapas.jsonl")
CADENA = ("local-fs", "basic", "multi-user", "gdm", "graphical", "sesion-usuario")
RAMAS = ("network-online", "gpu-lista")
ETAPA_SANA = "multi-user"
UID_MIN = 1000  # /etc/login.defs de Ubuntu: por debajo, usuarios de sistema (gdm incluido)
WATCHDOG_ATRIBUTOS = ("identity", "state", "status", "timeout", "timeleft", "pretimeout", "nowayout", "bootstatus")
LIMITE = ("un arranque que no llego a local-fs no deja marca en disco: no se distingue de uno que no existio; "
          "solo lo delata la ausencia de `bb-etapa` en la consola serie o en pstore")

Correr = Callable[..., subprocess.CompletedProcess[str]]


def _nc(motivo: str) -> str:
    return f"{NC}: {motivo}"


def _lee(ruta: Path) -> str | None:
    try:
        return ruta.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def _numero(v: object) -> bool:
    return v is None or (isinstance(v, (int, float)) and not isinstance(v, bool))


def leer_marcas(archivo: Path) -> tuple[list[dict[str, Any]], int]:
    """(marcas validas en orden, lineas descartadas): primero la generacion `.1`, luego la vigente.

    OSError si la vigente no se puede leer; una `.1` ausente es lo normal hasta la primera rotacion.
    """
    textos = []
    viejo = archivo.with_name(archivo.name + ".1")
    if viejo.exists():
        textos.append(viejo.read_text(encoding="utf-8", errors="replace"))
    textos.append(archivo.read_text(encoding="utf-8", errors="replace"))
    marcas: list[dict[str, Any]] = []
    descartadas = 0
    for linea in (ln for t in textos for ln in t.splitlines() if ln.strip()):
        try:
            m = json.loads(linea)
        except ValueError:
            descartadas += 1
            continue
        if (isinstance(m, dict) and isinstance(m.get("boot_id"), str) and isinstance(m.get("etapa"), str)
                and _numero(m.get("monotonic")) and _numero(m.get("realtime"))):
            marcas.append({k: m.get(k) for k in ("boot_id", "etapa", "monotonic", "realtime")})
        else:
            descartadas += 1
    return marcas, descartadas


def por_arranque(marcas: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Marcas agrupadas por boot_id, en el orden en que cada arranque aparece por primera vez."""
    grupos: dict[str, list[dict[str, Any]]] = {}
    for m in marcas:
        grupos.setdefault(m["boot_id"], []).append(m)
    return grupos


def canonica(etapa: str) -> str:
    """`sesion-<uid>` -> `sesion-usuario` (uid >= UID_MIN) o `sesion-sistema`; el resto, tal cual."""
    if etapa.startswith("sesion-") and etapa[7:].isdigit():
        return "sesion-usuario" if int(etapa[7:]) >= UID_MIN else "sesion-sistema"
    return etapa


def resumir(boot_id: str, marcas: list[dict[str, Any]]) -> dict[str, Any]:
    cadena: dict[str, Any] = {}
    ramas: dict[str, Any] = {r: None for r in RAMAS}
    sistema: list[str] = []
    otras: list[str] = []
    for m in marcas:
        c = canonica(m["etapa"])
        if c in CADENA:
            cadena.setdefault(c, m["monotonic"])
        elif c in RAMAS:
            ramas[c] = m["monotonic"] if ramas[c] is None else ramas[c]
        elif c == "sesion-sistema":
            sistema.append(m["etapa"])
        else:
            otras.append(m["etapa"])
    alcanzadas = [e for e in CADENA if e in cadena]
    return {"boot_id": boot_id, "ultima_etapa": alcanzadas[-1] if alcanzadas else None,
            "cadena": {e: cadena[e] for e in alcanzadas}, "ramas": ramas,
            "faltan": [e for e in CADENA if e not in cadena], "sesiones_sistema": sistema,
            "otras": otras, "marcas": marcas}


def _modinfo(correr: Correr, campo: str) -> str:
    try:
        r = correr(["modinfo", "-F", campo, "nvidia"], capture_output=True, text=True, check=False, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        return _nc(f"modinfo -F {campo} nvidia no corrio ({type(e).__name__})")
    salida = str(r.stdout).strip()
    if r.returncode != 0 or not salida:
        return _nc(f"modinfo -F {campo} nvidia rc={r.returncode} sin salida")
    return salida.splitlines()[0]


def contexto(raiz: Path, correr: Correr) -> dict[str, Any]:
    """Lo del arranque ACTUAL que explica al anterior; solo lectura, sin root."""
    watchdog: dict[str, dict[str, str]] = {}
    for wd in sorted((raiz / "sys/class/watchdog").glob("*")):
        watchdog[wd.name] = {a: _lee(wd / a) or _nc(f"{a} ilegible o vacio") for a in WATCHDOG_ATRIBUTOS}
    dmem = _lee(raiz / "sys/fs/cgroup/dmem.capacity")
    return {
        "cmdline": _lee(raiz / "proc/cmdline") or _nc("/proc/cmdline ilegible"),
        "bootstatus": {n: w["bootstatus"] for n, w in watchdog.items()} or _nc("sin /sys/class/watchdog/*"),
        "watchdog": watchdog or _nc("sin /sys/class/watchdog/*"),
        "nvidia": {
            "srcversion_cargado": _lee(raiz / "sys/module/nvidia/srcversion") or _nc("nvidia no cargado"),
            "version_cargado": _lee(raiz / "sys/module/nvidia/version") or _nc("nvidia no cargado"),
            # el firmante no esta en sysfs: es el del archivo que modprobe elegiria para el kernel en marcha
            "archivo": _modinfo(correr, "filename"),
            "srcversion_archivo": _modinfo(correr, "srcversion"),
            "firmante_archivo": _modinfo(correr, "signer"),
        },
        "dmem_capacity": dmem if dmem is not None else _nc("sin /sys/fs/cgroup/dmem.capacity"),
    }


def fila(marcas: list[dict[str, Any]], descartadas: int, boot_actual: str, raiz: Path,
         correr: Correr, ahora: datetime) -> dict[str, Any] | None:
    """La fila del arranque actual, o None si aun no es sano (no llego a ETAPA_SANA)."""
    grupos = por_arranque(marcas)
    actual = grupos.get(boot_actual, [])
    if ETAPA_SANA not in {canonica(m["etapa"]) for m in actual}:
        return None
    previos = [b for b in grupos if b != boot_actual]
    anterior: dict[str, Any] | str = (resumir(previos[-1], grupos[previos[-1]]) if previos
                                      else _nc("sin marcas de un arranque anterior en etapas.jsonl"))
    return {
        "esquema": ESQUEMA,
        "ts": ahora.isoformat(timespec="seconds"),
        "boot_id_actual": boot_actual,
        "etapas_actual": [m["etapa"] for m in actual],
        "boot_id_anterior": anterior["boot_id"] if isinstance(anterior, dict) else anterior,
        "ultima_etapa_anterior": (anterior["ultima_etapa"] or _nc("el anterior no llego a ninguna etapa de la cadena")
                                  if isinstance(anterior, dict) else anterior),
        "anterior": anterior,
        "contexto": contexto(raiz, correr),
        "descartadas": descartadas,
        "limite": LIMITE,
    }


def ya_anotado(salida: Path, boot_actual: str) -> bool:
    try:
        texto = salida.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return False
    for linea in texto.splitlines():
        try:
            if json.loads(linea).get("boot_id_actual") == boot_actual:
                return True
        except (ValueError, AttributeError):
            continue
    return False


def salida_por_defecto() -> Path:
    return Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox")) / "etapas_arranque.jsonl"


def main(argv: list[str] | None = None, correr: Correr = subprocess.run) -> int:
    p = argparse.ArgumentParser(prog="etapas_arranque", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--etapas", type=Path, default=ETAPAS, help="etapas.jsonl que escribe bb-etapa@.service")
    p.add_argument("--out", type=Path, default=None, help="JSONL de salida (defecto $BLACKBOX_DATA/etapas_arranque.jsonl)")
    p.add_argument("--raiz", type=Path, default=Path("/"), help="raiz de /proc y /sys (pruebas)")
    p.add_argument("--imprime", action="store_true", help="imprime la fila sin escribirla")
    a = p.parse_args(argv)
    salida = a.out or salida_por_defecto()
    boot = _lee(a.raiz / "proc/sys/kernel/random/boot_id")
    if not boot:
        print("[etapas] COULD_NOT_RUN: sin boot_id del arranque actual", file=sys.stderr)
        return 2
    try:
        marcas, descartadas = leer_marcas(a.etapas)
    except OSError as e:
        print(f"[etapas] COULD_NOT_RUN: {a.etapas} ilegible ({e.strerror})", file=sys.stderr)
        return 2
    if not a.imprime and ya_anotado(salida, boot):
        print(f"[etapas] el arranque {boot} ya esta anotado en {salida}")
        return 0
    f = fila(marcas, descartadas, boot, a.raiz, correr, datetime.now(timezone.utc))
    if f is None:
        print(f"[etapas] el arranque actual aun no llego a {ETAPA_SANA}: nada que anotar todavia")
        return 1
    texto = json.dumps(f, ensure_ascii=False, sort_keys=True)
    if a.imprime:
        print(texto)
        return 0
    salida.parent.mkdir(parents=True, exist_ok=True)
    with salida.open("a", encoding="utf-8") as fh:
        fh.write(texto + "\n")
    print(f"[etapas] anotado: el arranque anterior llego a {f['ultima_etapa_anterior']} -> {salida}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
