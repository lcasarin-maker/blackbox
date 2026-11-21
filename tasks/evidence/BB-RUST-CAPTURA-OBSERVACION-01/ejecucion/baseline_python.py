#!/usr/bin/env python3
"""Baseline auténtico: herramientas.ultimo_aliento sobre el fixture compartido."""
import argparse
import json
import os
import resource
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools import ultimo_aliento as ua  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", type=Path, required=True)
    ap.add_argument("--ring", type=Path, required=True)
    ap.add_argument("--samples", type=int, default=256)
    args = ap.parse_args()
    inventory = ua.descubrir(str(args.fixture))
    previous = str(args.ring) + ".previo"
    if os.path.lexists(args.ring) or os.path.lexists(previous):
        print(json.dumps({"status": "COULD_NOT_RUN", "error": "destino o .previo preexistente; se conserva evidencia"},
                         sort_keys=True, separators=(",", ":")))
        return 2
    try:
        reservation = os.open(args.ring, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        print(json.dumps({"status": "COULD_NOT_RUN", "error": "destino existente; se conserva evidencia"},
                         sort_keys=True, separators=(",", ":")))
        return 2
    ring = ua.Anillo(str(args.ring))
    try:
        notes = ring.abrir()
    finally:
        os.close(reservation)
    boot = ua.leer_boot_id(str(args.fixture))
    durations = []
    fields = None
    write_errors = 0
    try:
        for i in range(args.samples):
            start = time.perf_counter_ns()
            body = ua.muestrear(str(args.fixture), inventory)
            record = {"seq": i, "ts": 1_000_000_000.0 + i * 0.25, "boot": boot,
                      "tipo": "muestra", **body}
            try:
                ring.escribir(record)
            except OSError:
                write_errors += 1
            durations.append(time.perf_counter_ns() - start)
            if fields is None:
                fields = record
    finally:
        ring.cerrar()
    persisted = ua.leer_anillo(str(args.ring))
    stored_samples = [row for row in persisted["registros"] if row.get("tipo") == "muestra"]
    seqs = [row["seq"] for row in stored_samples]
    losses = args.samples - len(stored_samples)
    result = {
        "harness": "baseline-python/1",
        "implementation": "tools/ultimo_aliento.py::descubrir+muestrear+Anillo",
        "samples_requested": args.samples,
        "samples_persisted": len(stored_samples),
        "losses": losses,
        "write_errors": write_errors,
        "persisted_seqs": seqs,
        "persisted_seq_first_last": [seqs[0], seqs[-1]] if seqs else None,
        "boot": boot,
        "seq_first_last": [0, args.samples - 1],
        "raw_fields": fields,
        "latency_ms": {
            "p50": round(statistics.median(durations) / 1e6, 6),
            "p95": round(sorted(durations)[int((len(durations) - 1) * 0.95)] / 1e6, 6),
            "max": round(max(durations) / 1e6, 6),
        },
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 3),
        "ring": {"format": ua.FORMATO_ANILLO, "bytes": ua.TAMANO_ANILLO,
                 "header_bytes": ua.ENCABEZADO_BYTES, "slot_bytes": ua.REGISTRO_BYTES,
                 "slots": ua._encabezado(ua.TAMANO_ANILLO, ua.ENCABEZADO_BYTES, ua.REGISTRO_BYTES)["ranuras"]},
        "ring_open_notes": notes,
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if losses == 0 and write_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
