#!/usr/bin/env python3
"""Mutación local de una muestra para probar que el comparador rechaza divergencias."""
import copy
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = Path.home() / "scratch/blackbox/2026-11-21-captura-observacion"
PY_RING = BASE / "python-final.bin"
RUST_RING = BASE / "rust-formal2.bin"
PY_REPORT = ROOT / "tasks/evidence/BB-RUST-CAPTURA-OBSERVACION-01/ejecucion/baseline-python.json"
RUST_REPORT = ROOT / "tasks/evidence/BB-RUST-CAPTURA-OBSERVACION-01/ejecucion/rust-run.json"
COMPARATOR = ROOT / "tasks/evidence/BB-RUST-CAPTURA-OBSERVACION-01/ejecucion/compare_rings.py"

with tempfile.TemporaryDirectory(prefix="comparison-negative-", dir=BASE) as temp:
    mutated = Path(temp) / "mutated-ring.bin"
    shutil.copyfile(PY_RING, mutated)
    import sys
    sys.path.insert(0, str(ROOT))
    from tools import ultimo_aliento as ua

    readback = ua.leer_anillo(str(mutated))
    sample = copy.deepcopy(next(r for r in readback["registros"] if r.get("tipo") == "muestra" and r["seq"] == 17))
    sample["mem_kb"]["MemAvailable"] += 1
    with mutated.open("r+b") as ring:
        ring.seek(ua.ENCABEZADO_BYTES + sample["seq"] % readback["cabecera"]["ranuras"] * readback["cabecera"]["registro"])
        ring.write(ua.serializar(sample, readback["cabecera"]["registro"]))
        ring.flush()
    result = subprocess.run([
        "python3", "-I", str(COMPARATOR), "--python-ring", str(PY_RING), "--rust-ring", str(mutated),
        "--python-report", str(PY_REPORT), "--rust-report", str(RUST_REPORT),
    ], text=True, capture_output=True, check=False)
    print(result.stdout, end="")
    report = json.loads(result.stdout)
    if result.returncode != 1 or report["field_mismatch_count"] != 1 or report["status"] != "FAIL":
        print("[negative-control] FAIL: el comparador no detectó la mutación")
        raise SystemExit(1)
    print("[negative-control] PASS: detectó la fila alterada")
