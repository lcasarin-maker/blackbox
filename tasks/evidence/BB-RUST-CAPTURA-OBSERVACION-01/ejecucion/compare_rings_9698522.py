#!/usr/bin/env python3
"""Compara anillos cerrados usando el lector consumidor versionado."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools import ultimo_aliento as ua  # noqa: E402

FIELDS = ("seq", "boot", "ts", "tipo", "ausente", "psi", "mem_kb", "temp_c", "loadavg")
EXPECTED = list(range(256))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--python-ring", type=Path, required=True)
    ap.add_argument("--rust-ring", type=Path, required=True)
    ap.add_argument("--python-report", type=Path, required=True)
    ap.add_argument("--rust-report", type=Path, required=True)
    args = ap.parse_args()
    try:
        py = ua.leer_anillo(str(args.python_ring))
        rs = ua.leer_anillo(str(args.rust_ring))
        py_report = json.loads(args.python_report.read_text(encoding="utf-8"))
        rs_report = json.loads(args.rust_report.read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "COULD_NOT_RUN", "could_not_run": [f"{type(exc).__name__}: {exc}"],
                          "failures": [], "crash_durability": "OUT_OF_SCOPE"}, sort_keys=True))
        return 2
    py_rows = [r for r in py["registros"] if r.get("tipo") == "muestra"]
    rs_rows = [r for r in rs["registros"] if r.get("tipo") == "muestra"]
    py_seq = [r.get("seq") for r in py_rows]
    rs_seq = [r.get("seq") for r in rs_rows]
    failures = []
    if py_seq != EXPECTED:
        failures.append({"ring": "python", "kind": "sequence", "actual_count": len(py_seq)})
    if rs_seq != EXPECTED:
        failures.append({"ring": "rust", "kind": "sequence", "actual_count": len(rs_seq)})
    if py["ilegibles"]:
        failures.append({"ring": "python", "kind": "illegible_slots", "count": py["ilegibles"]})
    if rs["ilegibles"]:
        failures.append({"ring": "rust", "kind": "illegible_slots", "count": rs["ilegibles"]})
    geometry = (py["cabecera"].get("formato"), py["cabecera"].get("tamano"),
                py["cabecera"].get("encabezado"), py["cabecera"].get("registro"), py["cabecera"].get("ranuras")) == (
                rs["cabecera"].get("formato"), rs["cabecera"].get("tamano"),
                rs["cabecera"].get("encabezado"), rs["cabecera"].get("registro"), rs["cabecera"].get("ranuras"))
    if not geometry:
        failures.append({"kind": "geometry"})
    rust_p95 = rs_report.get("latency_ms", {}).get("p95")
    rust_rss = rs_report.get("peak_rss_mib")
    if not isinstance(rust_p95, (int, float)) or rust_p95 > 25.0:
        failures.append({"kind": "rust_latency_limit", "limit_ms": 25.0, "actual_ms": rust_p95})
    if not isinstance(rust_rss, (int, float)) or rust_rss <= 0 or rust_rss > 48.0:
        failures.append({"kind": "rust_process_rss_limit", "limit_mib": 48.0, "actual_mib": rust_rss})
    if rs_report.get("build_profile") not in ("debug", "release"):
        failures.append({"kind": "rust_build_profile_missing"})
    mismatches = []
    for py_row, rs_row in zip(py_rows, rs_rows):
        for field in FIELDS:
            if py_row.get(field) != rs_row.get(field):
                mismatches.append({"seq": py_row.get("seq"), "field": field,
                                   "python": py_row.get(field), "rust": rs_row.get(field)})
    if mismatches:
        failures.append({"kind": "field_mismatches", "count": len(mismatches), "first": mismatches[:5]})
    output = {
        "status": "PASS" if not failures else "FAIL",
        "python_readback": "re-read from ring after process exit",
        "rust_readback": "re-read from ring after process exit",
        "rust_build_profile": rs_report.get("build_profile"),
        "python_p95_latency_ms": py_report.get("latency_ms", {}).get("p95"),
        "rust_p95_latency_ms": rust_p95,
        "python_peak_process_rss_mib": py_report.get("peak_rss_mib"),
        "rust_peak_process_rss_mib": rust_rss,
        "acceptance_limits": {"rust_p95_latency_ms_max": 25.0, "rust_peak_process_rss_mib_max": 48.0},
        "crash_durability": "OUT_OF_SCOPE; sample fdatasync not run",
        "records_compared": min(len(py_rows), len(rs_rows)),
        "python_persisted": len(py_rows), "rust_persisted": len(rs_rows),
        "python_sequence": py_seq, "rust_sequence": rs_seq,
        "python_ring_sha256": hashlib.sha256(args.python_ring.read_bytes()).hexdigest(),
        "rust_ring_sha256": hashlib.sha256(args.rust_ring.read_bytes()).hexdigest(),
        "python_losses": 256 - len(py_rows), "rust_losses": 256 - len(rs_rows),
        "python_illegible_slots": py["ilegibles"], "rust_illegible_slots": rs["ilegibles"],
        "sequence_complete": py_seq == EXPECTED and rs_seq == EXPECTED,
        "geometry_match": geometry, "fields_per_record": list(FIELDS),
        "field_mismatch_count": len(mismatches), "could_not_run": [], "failures": failures,
    }
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
