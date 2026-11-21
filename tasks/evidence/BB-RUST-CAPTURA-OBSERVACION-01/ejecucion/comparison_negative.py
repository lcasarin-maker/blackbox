#!/usr/bin/env python3
"""Controles adversos del comparador sobre anillos sintéticos."""
import copy
import json
import shutil
import subprocess
import sys
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SCRATCH_ROOT = Path(os.environ.get("BB_CAPTURE_SCRATCH", Path.home() / "scratch/blackbox")).resolve(strict=True)
ALLOWED = (Path.home() / "scratch/blackbox").resolve(strict=True)
if not SCRATCH_ROOT.is_relative_to(ALLOWED):
    raise SystemExit("COULD_NOT_RUN: BB_CAPTURE_SCRATCH fuera de HOME/scratch/blackbox")
if not SCRATCH_ROOT.is_dir():
    raise SystemExit("COULD_NOT_RUN: BB_CAPTURE_SCRATCH no es directorio")
SCRATCH = SCRATCH_ROOT / f"comparison-negative-{os.getpid()}-{time.time_ns()}"
SCRATCH.mkdir(parents=True, exist_ok=True)
PY_RING = SCRATCH_ROOT / "python.bin"
RUST_RING = SCRATCH_ROOT / "rust.bin"
PY_REPORT = ROOT / "tasks/evidence/BB-RUST-CAPTURA-OBSERVACION-01/ejecucion/final-python-report.json"
RUST_REPORT = ROOT / "tasks/evidence/BB-RUST-CAPTURA-OBSERVACION-01/ejecucion/final-rust-report.json"
COMPARATOR = ROOT / "tasks/evidence/BB-RUST-CAPTURA-OBSERVACION-01/ejecucion/compare_rings.py"
sys.path.insert(0, str(ROOT))
from tools import ultimo_aliento as ua


def invoke(py_ring=PY_RING, rust_ring=RUST_RING, py_report=PY_REPORT, rust_report=RUST_REPORT):
    return subprocess.run(["python3", "-B", "-I", str(COMPARATOR), "--python-ring", str(py_ring),
        "--rust-ring", str(rust_ring), "--python-report", str(py_report), "--rust-report", str(rust_report)],
        text=True, capture_output=True, check=False)


def report_copy(name, source, mutate):
    data = json.loads(source.read_text())
    mutate(data)
    path = SCRATCH / f"{name}.json"
    path.write_text(json.dumps(data, allow_nan=True))
    return path


def check_invalid_metrics():
    mutations = {
        "negative_p95": lambda d: d["latency_ms"].update(p95=-1),
        "bool_p95": lambda d: d["latency_ms"].update(p95=True),
        "bool_rss": lambda d: d.update(peak_rss_mib=True),
        "nan_p95": lambda d: d["latency_ms"].update(p95=float("nan")),
        "null_latency": lambda d: d.update(latency_ms=None),
        "missing_p95": lambda d: d["latency_ms"].pop("p95"),
        "missing_rss": lambda d: d.pop("peak_rss_mib"),
        "zero_rss": lambda d: d.update(peak_rss_mib=0),
    }
    for side, source in (("python", PY_REPORT), ("rust", RUST_REPORT)):
        for name, mutation in mutations.items():
            invalid = report_copy(f"{side}-{name}", source, mutation)
            result = invoke(py_report=invalid) if side == "python" else invoke(rust_report=invalid)
            data = json.loads(result.stdout)
            if result.returncode != 2 or data.get("status") != "COULD_NOT_RUN" or not data.get("could_not_run"):
                raise AssertionError(f"{side}/{name}: rc={result.returncode} output={result.stdout!r}")
    over = report_copy("valid-limit-exceeded", RUST_REPORT, lambda d: d["latency_ms"].update(p95=25.1))
    result = invoke(rust_report=over)
    data = json.loads(result.stdout)
    if result.returncode != 1 or data.get("status") != "FAIL" or not any(x.get("kind") == "rust_latency_limit" for x in data["failures"]):
        raise AssertionError(f"valid exceeded limit: rc={result.returncode} output={result.stdout!r}")
    incomplete = report_copy("missing-build-profile", RUST_REPORT, lambda d: d.pop("build_profile"))
    result = invoke(rust_report=incomplete)
    data = json.loads(result.stdout)
    if result.returncode != 2 or data.get("status") != "COULD_NOT_RUN" or not data.get("could_not_run"):
        raise AssertionError(f"missing build_profile: rc={result.returncode} output={result.stdout!r}")
    print("[negative-control] PASS: 17 informes inválidos/incompletos dan COULD_NOT_RUN rc=2; exceso válido da FAIL rc=1")


def check_missing_sequence():
    mutated = SCRATCH / "missing-seq-17.bin"
    shutil.copyfile(RUST_RING, mutated)
    with mutated.open("r+b") as ring:
        ring.seek(ua.ENCABEZADO_BYTES + 17 * ua.REGISTRO_BYTES)
        ring.write(bytes(ua.REGISTRO_BYTES))
    result = invoke(rust_ring=mutated)
    data = json.loads(result.stdout)
    if result.returncode != 1 or data["sequence_discrepancy_count"] != 1 or data["field_mismatch_count"] != 0:
        raise AssertionError(f"lost seq 17: rc={result.returncode} output={result.stdout!r}")
    print("[negative-control] PASS: pérdida de seq 17 produce discrepancia estructural=1 y campos=0")

    missing_both_py, missing_both_rs = SCRATCH / "python-missing-seq-17.bin", SCRATCH / "rust-missing-seq-17.bin"
    for source, destination in ((PY_RING, missing_both_py), (RUST_RING, missing_both_rs)):
        shutil.copyfile(source, destination)
        with destination.open("r+b") as ring:
            ring.seek(ua.ENCABEZADO_BYTES + 17 * ua.REGISTRO_BYTES)
            ring.write(bytes(ua.REGISTRO_BYTES))
    result = invoke(missing_both_py, missing_both_rs)
    data = json.loads(result.stdout)
    if result.returncode != 1 or data["sequence_discrepancy_count"] != 1 or data["records_compared"] != 255:
        raise AssertionError(f"both lost seq 17: rc={result.returncode} output={result.stdout!r}")
    print("[negative-control] PASS: seq 17 ausente en ambos cuenta una anomalía estructural y 255 comparados")


def check_field_mutation():
    mutated = SCRATCH / "changed-field.bin"
    shutil.copyfile(RUST_RING, mutated)
    readback = ua.leer_anillo(str(mutated))
    sample = copy.deepcopy(next(r for r in readback["registros"] if r.get("tipo") == "muestra" and r["seq"] == 17))
    sample["mem_kb"]["MemAvailable"] += 1
    with mutated.open("r+b") as ring:
        ring.seek(ua.ENCABEZADO_BYTES + 17 * ua.REGISTRO_BYTES)
        ring.write(ua.serializar(sample, readback["cabecera"]["registro"]))
    result = invoke(rust_ring=mutated)
    data = json.loads(result.stdout)
    if result.returncode != 1 or data["sequence_discrepancy_count"] != 0 or data["field_mismatch_count"] != 1:
        raise AssertionError(f"changed field: rc={result.returncode} output={result.stdout!r}")
    print("[negative-control] PASS: campo alterado produce discrepancias estructurales=0 y campos=1")


if __name__ == "__main__":
    check_invalid_metrics()
    check_missing_sequence()
    check_field_mutation()
