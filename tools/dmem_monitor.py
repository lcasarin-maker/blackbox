#!/usr/bin/env python3
"""Monitor del parche dmem del modulo NVIDIA (decision de Luis 2026-10-12: sin bloquear actualizaciones, con monitor y reparador).

Compara lo que corre y lo que hay instalado contra el parche: un kernel nuevo, un driver nuevo, o un modulo parcheado que
no es el cargado. No cambia nada: escribe `$BLACKBOX_DATA/dmem_parche.jsonl` y dice que comando del reparador correr
(`tools/dmem_reconstruye.sh`). Sin leer lo que necesita, no concluye y lo declara (NOT_COLLECTED).
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Estado:
    kernel: str
    driver_stock: str | None          # version del modulo de Canonical para ESTE kernel
    parche_version: str | None        # version del modulo en updates/ (None = no hay)
    parche_vermagic: str | None
    parche_srcversion: str | None
    cargado_version: str | None
    cargado_srcversion: str | None
    dmem_con_region: bool | None


def evalua(e: Estado) -> list[dict]:
    """Pura. Una lista de hallazgos {codigo, gravedad, motivo, accion}; vacia no existe: siempre dice algo."""
    h: list[dict] = []
    reparar = f"bash tools/dmem_reconstruye.sh {e.kernel}"
    if e.driver_stock is None:
        return [{"codigo": "NOT_COLLECTED", "gravedad": "alta", "motivo": "no se pudo leer la version del modulo de Canonical", "accion": None}]
    if e.parche_version is None:
        return [{"codigo": "sin_parche", "gravedad": "info", "motivo": "no hay modulo parcheado en updates/ para este kernel", "accion": None}]
    if e.parche_vermagic is not None and not e.parche_vermagic.startswith(e.kernel):
        h.append({"codigo": "kernel_nuevo", "gravedad": "alta", "motivo": f"el parche se hizo para '{e.parche_vermagic.split()[0]}' y corre {e.kernel}: el kernel no lo cargara", "accion": reparar})
    if e.parche_version != e.driver_stock:
        h.append({"codigo": "driver_nuevo", "gravedad": "alta", "motivo": f"parche de driver {e.parche_version}, Canonical ofrece {e.driver_stock}", "accion": f"{reparar} {e.driver_stock}"})
    if e.cargado_srcversion is not None and e.parche_srcversion is not None and e.cargado_srcversion != e.parche_srcversion:
        h.append({"codigo": "cargado_no_es_el_parche", "gravedad": "media", "motivo": "el modulo cargado no es el de updates/ (arranque anterior o retroceso)", "accion": "reiniciar o revisar dmem_modulo.sh estado"})
    if not h:
        h.append({"codigo": "vigente", "gravedad": "info", "motivo": f"parche {e.parche_version} para {e.kernel} y cargado; dmem con region: {e.dmem_con_region}", "accion": None})
    return h


def _modinfo(ruta: Path, campo: str) -> str | None:
    try:
        r = subprocess.run(["modinfo", "-F", campo, str(ruta)], capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip().splitlines()[0] if r.returncode == 0 and r.stdout.strip() else None


def _lee(ruta: Path) -> str | None:
    try:
        return ruta.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def lee_estado(modulos: Path | None = None, sys_nvidia: Path = Path("/sys/module/nvidia"), cap: Path = Path("/sys/fs/cgroup/dmem.capacity")) -> Estado:
    kernel = os.uname().release
    base = modulos or Path("/lib/modules") / kernel
    stock = _modinfo(base / "kernel/nvidia-580-open/nvidia.ko", "version")
    upd = base / "updates/nvidia.ko"
    existe = upd.is_file()
    capacidad = _lee(cap)
    return Estado(kernel, stock,
                  _modinfo(upd, "version") if existe else None,
                  _modinfo(upd, "vermagic") if existe else None,
                  _modinfo(upd, "srcversion") if existe else None,
                  _lee(sys_nvidia / "version"), _lee(sys_nvidia / "srcversion"),
                  None if capacidad is None else bool(capacidad))


def main() -> int:
    e = lee_estado()
    hallazgos = evalua(e)
    datos = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))
    datos.mkdir(parents=True, exist_ok=True)
    with (datos / "dmem_parche.jsonl").open("a", encoding="utf-8") as fh:
        for x in hallazgos:
            fh.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), "kernel": e.kernel, **x}, ensure_ascii=False) + "\n")
    for x in hallazgos:
        print(f"[dmem-monitor] {x['gravedad']:5s} {x['codigo']}: {x['motivo']}" + (f"  -> {x['accion']}" if x["accion"] else ""))
    return 1 if any(x["gravedad"] == "alta" for x in hallazgos) else 0


if __name__ == "__main__":
    raise SystemExit(main())
