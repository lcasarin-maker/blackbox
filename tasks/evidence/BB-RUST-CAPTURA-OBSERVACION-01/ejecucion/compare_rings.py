#!/usr/bin/env python3
"""Compara anillos cerrados usando el lector consumidor versionado."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools import ultimo_aliento as ua  # noqa: E402

FIELDS = ("seq", "boot", "ts", "tipo", "ausente", "psi", "mem_kb", "temp_c", "loadavg")
EXPECTED = list(range(256))


def metric(report, label):
    if not isinstance(report, dict):
        raise ValueError(f"{label}: report must be an object")
    latency = report.get("latency_ms")
    if not isinstance(latency, dict):
        raise ValueError(f"{label}: latency_ms must be an object")
    p95 = latency.get("p95")
    rss = report.get("peak_rss_mib")
    for name, value in (("latency_ms.p95", p95), ("peak_rss_mib", rss)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{label}: {name} must be a number")
        try:
            finite = math.isfinite(value)
        except (OverflowError, TypeError):
            finite = False
        if not finite:
            raise ValueError(f"{label}: {name} must be finite")
    if p95 < 0:
        raise ValueError(f"{label}: latency_ms.p95 must be nonnegative")
    if rss <= 0:
        raise ValueError(f"{label}: peak_rss_mib must be positive")
    if label == "rust report" and report.get("build_profile") not in ("debug", "release"):
        raise ValueError("rust report: build_profile is missing or invalid")
    return p95, rss


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
        py_p95, py_rss = metric(py_report, "python report")
        rust_p95, rust_rss = metric(rs_report, "rust report")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "COULD_NOT_RUN", "could_not_run": [f"{type(exc).__name__}: {exc}"],
                          "failures": [], "crash_durability": "OUT_OF_SCOPE"}, sort_keys=True))
        return 2
    py_rows = [r for r in py["registros"] if r.get("tipo") == "muestra"]
    rs_rows = [r for r in rs["registros"] if r.get("tipo") == "muestra"]
    py_seq = [r.get("seq") for r in py_rows]
    rs_seq = [r.get("seq") for r in rs_rows]
    py_by_seq = {r["seq"]: r for r in py_rows if isinstance(r.get("seq"), int) and not isinstance(r.get("seq"), bool)}
    rs_by_seq = {r["seq"]: r for r in rs_rows if isinstance(r.get("seq"), int) and not isinstance(r.get("seq"), bool)}
    failures = []
    if py_seq != EXPECTED:
        failures.append({"ring": "python", "kind": "sequence", "actual_count": len(py_seq),
                         "missing_count": len(set(EXPECTED) - set(py_by_seq))})
    if rs_seq != EXPECTED:
        failures.append({"ring": "rust", "kind": "sequence", "actual_count": len(rs_seq),
                         "missing_count": len(set(EXPECTED) - set(rs_by_seq))})
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
    if rust_p95 > 25.0:
        failures.append({"kind": "rust_latency_limit", "limit_ms": 25.0, "actual_ms": rust_p95})
    if rust_rss > 48.0:
        failures.append({"kind": "rust_process_rss_limit", "limit_mib": 48.0, "actual_mib": rust_rss})
    mismatches = []
    py_valid_count = sum(isinstance(r.get("seq"), int) and not isinstance(r.get("seq"), bool) for r in py_rows)
    rs_valid_count = sum(isinstance(r.get("seq"), int) and not isinstance(r.get("seq"), bool) for r in rs_rows)
    py_duplicates, rs_duplicates = py_valid_count - len(py_by_seq), rs_valid_count - len(rs_by_seq)
    py_invalid, rs_invalid = len(py_rows) - py_valid_count, len(rs_rows) - rs_valid_count
    if py_duplicates:
        failures.append({"ring": "python", "kind": "duplicate_sequence_keys", "count": py_duplicates})
    if rs_duplicates:
        failures.append({"ring": "rust", "kind": "duplicate_sequence_keys", "count": rs_duplicates})
    if py_invalid:
        failures.append({"ring": "python", "kind": "invalid_sequence_keys", "count": py_invalid})
    if rs_invalid:
        failures.append({"ring": "rust", "kind": "invalid_sequence_keys", "count": rs_invalid})
    for seq in sorted(py_by_seq.keys() & rs_by_seq.keys()):
        py_row, rs_row = py_by_seq[seq], rs_by_seq[seq]
        for field in FIELDS:
            if py_row.get(field) != rs_row.get(field):
                mismatches.append({"seq": py_row.get("seq"), "field": field,
                                   "python": py_row.get(field), "rust": rs_row.get(field)})
    if mismatches:
        failures.append({"kind": "field_mismatches", "count": len(mismatches), "first": mismatches[:5]})
    missing = (set(EXPECTED) - py_by_seq.keys()) | (set(EXPECTED) - rs_by_seq.keys())
    unexpected = (py_by_seq.keys() - set(EXPECTED)) | (rs_by_seq.keys() - set(EXPECTED))
    sequence_anomalies = sorted(missing | unexpected)
    structural_count = len(sequence_anomalies) + py_duplicates + rs_duplicates + py_invalid + rs_invalid
    if sequence_anomalies or py_duplicates or rs_duplicates or py_invalid or rs_invalid:
        failures.append({"kind": "sequence_discrepancies", "count": structural_count,
                         "first": sequence_anomalies[:5]})
    output = {
        "status": "PASS" if not failures else "FAIL",
        "python_readback": "re-read from ring after process exit",
        "rust_readback": "re-read from ring after process exit",
        "rust_build_profile": rs_report.get("build_profile"),
        "python_p95_latency_ms": py_p95,
        "rust_p95_latency_ms": rust_p95,
        "python_peak_process_rss_mib": py_rss,
        "rust_peak_process_rss_mib": rust_rss,
        "acceptance_limits": {"rust_p95_latency_ms_max": 25.0, "rust_peak_process_rss_mib_max": 48.0},
        "crash_durability": "OUT_OF_SCOPE; sample fdatasync not run",
        "records_compared": len(py_by_seq.keys() & rs_by_seq.keys()),
        "python_persisted": len(py_rows), "rust_persisted": len(rs_rows),
        "python_sequence": py_seq, "rust_sequence": rs_seq,
        "python_ring_sha256": hashlib.sha256(args.python_ring.read_bytes()).hexdigest(),
        "rust_ring_sha256": hashlib.sha256(args.rust_ring.read_bytes()).hexdigest(),
        "python_losses": 256 - len(py_rows), "rust_losses": 256 - len(rs_rows),
        "python_illegible_slots": py["ilegibles"], "rust_illegible_slots": rs["ilegibles"],
        "sequence_complete": py_seq == EXPECTED and rs_seq == EXPECTED,
        "geometry_match": geometry, "fields_per_record": list(FIELDS),
        "field_mismatch_count": len(mismatches), "could_not_run": [], "failures": failures,
        "sequence_discrepancy_count": structural_count,
    }
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
