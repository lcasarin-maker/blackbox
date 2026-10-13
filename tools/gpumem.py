#!/usr/bin/env python3
"""`bb gpumem`: memoria de GPU por contenedor/cgroup en la GB10, y el asesor "¿cabe?".

`nvidia-smi` no reporta memoria en GB10 (memoria unificada; NVIDIA lo confirma como diseno, hilo 367765) y los monitores de
la comunidad no dicen como obtener la memoria de GPU por proceso (hilos 358869, 385664). Con el modulo NVIDIA parcheado
(FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01) el kernel cobra cada `cudaMalloc` al cgroup del proceso: `dmem.current`
de cada cgroup es su memoria de GPU. Medido 2026-10-12: 19483439376 B en `dmem.current` del contenedor de vLLM contra
19482542080 B de `nvidia-smi` para su proceso (0.005 %).
Sin el modulo parcheado `dmem.capacity` esta vacio: el comando lo declara (SIN_REGION) y no inventa cifras.
Unidades: todo en GiB (binario). Techo utilizable de la maquina = 128e9 B = 119.2 GiB (hilo 352962: GB contra GiB, no memoria perdida).

`--cabe GIB`: dice si un pedido cabe contra MemAvailable con un margen (la misma linea dura del vigilante memavail, 8 GiB).
Limite declarado: pinned (cudaHostAlloc) y managed (cudaMallocManaged) no se cobran; solo ve lo que entra por la clase RM 0x3e.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

GIB = 1 << 30
MARGEN_GIB = 8.0  # igual que vigilante_memavail.LINEA_GIB
TECHO_GIB = 128e9 / GIB
SCOPE = re.compile(r"^docker-([0-9a-f]{64})\.scope$")


def _pares(texto: str) -> dict[str, int]:
    """`dmem.current` / `dmem.capacity`: lineas `<region> <bytes>`."""
    out: dict[str, int] = {}
    for ln in texto.splitlines():
        partes = ln.split()
        if len(partes) == 2 and partes[1].isdigit():
            out[partes[0]] = int(partes[1])
    return out


def capacidad(raiz: Path) -> dict[str, int]:
    try:
        return _pares((raiz / "dmem.capacity").read_text(encoding="utf-8"))
    except OSError:
        return {}


def escanea(raiz: Path, region: str, profundidad: int = 5) -> list[tuple[str, int]]:
    """Cgroups HOJA con carga de `region` > 0 (`dmem.current` es jerarquico: el padre suma a sus hijos)."""
    cargas: dict[str, int] = {}

    def baja(d: Path, rel: str, nivel: int) -> None:
        try:
            v = _pares((d / "dmem.current").read_text(encoding="utf-8")).get(region, 0)
        except OSError:
            v = 0
        if v > 0:
            cargas[rel] = v
        if nivel >= profundidad:
            return
        try:
            hijos = sorted(p for p in d.iterdir() if p.is_dir())
        except OSError:
            return
        for h in hijos:
            baja(h, f"{rel}/{h.name}".lstrip("/"), nivel + 1)

    baja(raiz, "", 0)
    rutas = list(cargas)

    def es_padre(r: str, o: str) -> bool:
        return o != r and (r == "" or o.startswith(r + "/"))  # la raiz ("") es padre de todo

    return [(r, cargas[r]) for r in rutas if not any(es_padre(r, o) for o in rutas)]


def nombres_docker() -> dict[str, str]:
    try:
        r = subprocess.run(["docker", "ps", "--no-trunc", "--format", "{{.ID}} {{.Names}}"], capture_output=True, text=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    return dict(ln.split(" ", 1) for ln in r.stdout.splitlines() if " " in ln)


def etiqueta(ruta: str, docker: dict[str, str]) -> str:
    m = SCOPE.match(ruta.rsplit("/", 1)[-1])
    if m:
        return f"contenedor {docker.get(m.group(1), m.group(1)[:12])}"
    return ruta or "(raiz)"


def informe(raiz: Path, docker: dict[str, str] | None = None) -> dict[str, object]:
    cap = capacidad(raiz)
    if not cap:
        return {"estado": "SIN_REGION", "motivo": "dmem.capacity vacio: corre el modulo de Canonical o el parche no dio region"}
    region = sorted(cap)[0]
    try:
        total = _pares((raiz / "dmem.current").read_text(encoding="utf-8")).get(region, 0)
    except OSError:
        total = 0
    docker = nombres_docker() if docker is None else docker
    filas = [{"quien": etiqueta(r, docker), "ruta": r, "gib": round(v / GIB, 2)} for r, v in sorted(escanea(raiz, region), key=lambda x: -x[1])]
    return {
        "estado": "OK",
        "region": region,
        "capacidad_gib": round(cap[region] / GIB, 1),
        "cobrado_total_gib": round(total / GIB, 2),
        "hojas": filas,
        "sin_atribuir_gib": round(max(0, total - sum(f["gib"] * GIB for f in filas)) / GIB, 2),
    }


def lee_mem_available_kb(ruta: Path = Path("/proc/meminfo")) -> int | None:
    try:
        m = re.search(r"^MemAvailable:\s+(\d+) kB", ruta.read_text(encoding="utf-8"), re.M)
    except OSError:
        return None
    return int(m.group(1)) if m else None


def cabe(pedido_gib: float, mem_avail_kb: int | None, margen_gib: float = MARGEN_GIB) -> dict[str, object]:
    """Pura. Cabe si lo pedido mas el margen entra en MemAvailable (MemFree no: excluye cache reclamable, hilo 350714)."""
    if mem_avail_kb is None:
        return {"cabe": False, "motivo": "NOT_COLLECTED: MemAvailable"}
    disponible = mem_avail_kb / 1048576
    return {
        "cabe": pedido_gib + margen_gib <= disponible,
        "pedido_gib": pedido_gib,
        "margen_gib": margen_gib,
        "disponible_gib": round(disponible, 2),
        "sobra_gib": round(disponible - pedido_gib - margen_gib, 2),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bb gpumem")
    ap.add_argument("--cabe", type=float, metavar="GIB", help="¿cabe un pedido de GIB GiB contra MemAvailable?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--raiz", default="/sys/fs/cgroup")
    a = ap.parse_args(argv)
    if a.cabe is not None:
        r = cabe(a.cabe, lee_mem_available_kb())
        print(json.dumps(r) if a.json else f"{'CABE' if r['cabe'] else 'NO CABE'}: {r}")
        return 0 if r["cabe"] else 1
    r = informe(Path(a.raiz))
    if a.json:
        print(json.dumps(r, indent=1))
    elif r["estado"] != "OK":
        print(f"{r['estado']}: {r['motivo']}")
    else:
        print(f"region {r['region']}  cobrado {r['cobrado_total_gib']} GiB de {r['capacidad_gib']} GiB (techo utilizable de la maquina {TECHO_GIB:.1f} GiB)")
        hojas = r["hojas"]
        assert isinstance(hojas, list)
        for f in hojas:
            print(f"  {f['gib']:8.2f} GiB  {f['quien']}")
        print(f"  {r['sin_atribuir_gib']:8.2f} GiB  sin atribuir a una hoja")
    return 0 if r.get("estado", "OK") == "OK" else 3


if __name__ == "__main__":
    sys.exit(main())
