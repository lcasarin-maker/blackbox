#!/usr/bin/env python3
"""Captura cruda para FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01: que cgroup paga cada clase de memoria de CUDA.

Cada fila corre `prueba.py <tipo>` en su propio scope de systemd de usuario, y guarda argv, codigo de salida, stdout, los
numeros que `prueba.py` imprime (delta de dmem.current de user.slice y delta de memory.current del scope) y la hora.
No escribe ningun veredicto: lo recalcula `python3 -m tools.verify_clases_memoria`.
Uso: python3 capture.py   (sin root; escribe raw.json junto a este archivo)
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PRUEBA = AQUI / "prueba.py"
FILA = re.compile(r"^(\w+)\s+rc=(\d+)\s+dmem_user_delta=\s*(-?[\d.]+) MiB\s+memory_current_delta=\s*(-?[\d.]+) MiB", re.M)


def corre(tipo: str, n_mib: int, memoria_max: str, rotulo: str) -> dict:
    argv = ["systemd-run", "--user", "--scope", "--quiet", "-p", f"MemoryMax={memoria_max}", "-p", "MemorySwapMax=0",
            "-E", f"N_MIB={n_mib}", sys.executable, "-I", str(PRUEBA), tipo]
    p = subprocess.run(argv, capture_output=True, text=True, timeout=300, check=False)
    m = FILA.search(p.stdout)
    return {"rotulo": rotulo, "tipo": tipo, "n_mib": n_mib, "memoria_max": memoria_max, "argv": argv, "exit": p.returncode,
            "stdout": p.stdout, "stderr": p.stderr[-400:], "capturado_en": datetime.now(timezone.utc).isoformat(),
            "cuda_rc": int(m.group(2)) if m else None, "dmem_delta_mib": float(m.group(3)) if m else None,
            "memcg_delta_mib": float(m.group(4)) if m else None}


filas = []
for rep in (1, 2):
    for tipo in ("nada", "device", "managed", "pinned"):
        filas.append(corre(tipo, 256, "2G", f"pequena-{rep}"))
for tipo in ("managed", "pinned", "device"):
    filas.append(corre(tipo, 2048, "1G", "sobre-el-tope"))
filas.append(corre("managed", 512, "1G", "bajo-el-tope"))
j = subprocess.run(["journalctl", "--user", "-n", "600", "--no-pager"], capture_output=True, text=True, timeout=60, check=False)
(AQUI / "raw.json").write_text(json.dumps({"schema": 1, "id": AQUI.name, "filas": filas,
                                           "journal_oom_kill_lineas": [x for x in j.stdout.splitlines() if "oom-kill" in x][-6:]},
                                          indent=1), encoding="utf-8")
print("filas", len(filas))
