#!/usr/bin/env python3
"""Resume hitos observados en journalctl -o json y muestras bb JSONL.

Ejemplo:
  journalctl -o json --since '2026-09-24 13:50' > journal.jsonl
  python3 tools/hitos_incidente.py --journal journal.jsonl \
      --samples /var/lib/blackbox/samples/2026-09-24.jsonl

Los hitos son observaciones con timestamp y boot cuando la fuente los aporta.
No estiman el inicio físico del problema ni establecen causalidad. Una fuente
ausente o ilegible aparece en ``could_not_run``; los arreglos conservan hitos
parciales disponibles.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ALLOCATOR = re.compile(r"NVRM:.*(?:_memdescAllocInternal|mem_desc\.c:\d+)", re.I)
OOM = re.compile(r"NVRM:.*(?:NV_ERR_NO_MEMORY|Out of memory)", re.IGNORECASE)
SERVICE_LOSS = re.compile(r"Main process exited|Failed with result", re.I)
SERVICE_RECOVERY = re.compile(r"Started .+\.service", re.I)
WATCHDOG = re.compile(
    r"Watchdog timeout|Failed with result ['\"]?watchdog", re.I)
BOOT = re.compile(r"Linux version |Command line:|systemd\[1\]: (?:Startup finished|Reached target)", re.I)


def _read_jsonl(path: Path, label: str, missing: list[str]) -> list[dict[str, Any]]:
    if not path.is_file():
        missing.append(f"{label}: falta {path}")
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    missing.append(f"{label}: JSON inválido en línea {number}: {exc.msg}")
                    continue
                if not isinstance(value, dict):
                    missing.append(f"{label}: línea {number} no es un objeto JSON")
                    continue
                rows.append(value)
    except (OSError, UnicodeError) as exc:
        missing.append(f"{label}: no se pudo leer {path}: {exc}")
    if not rows:
        missing.append(f"{label}: sin registros en {path}")
    return rows


def _journal_time(row: dict[str, Any]) -> str | None:
    raw = row.get("__REALTIME_TIMESTAMP")
    if raw is None:
        return None
    try:
        dt = datetime.fromtimestamp(int(raw) / 1_000_000, tz=timezone.utc)
    except (ValueError, TypeError, OverflowError, OSError):
        return None
    return dt.isoformat(timespec="microseconds")


def _sample_time(row: dict[str, Any]) -> str | None:
    raw = row.get("ts")
    if not isinstance(raw, str):
        return None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        return None
    return dt.astimezone(timezone.utc).isoformat(timespec="microseconds")


def _boot_id(row: dict[str, Any]) -> str | None:
    raw = row.get("_BOOT_ID", row.get("boot_id"))
    return raw if isinstance(raw, str) and raw.strip() else None


def _milestone(source: str, row: dict[str, Any], ts: str | None, **extra: Any) -> dict[str, Any]:
    return {
        "source": source,
        "timestamp": ts or row.get("ts") or None,
        "boot_id": _boot_id(row),
        **extra,
    }


def _event_sort_time(event: dict[str, Any]) -> str:
    timestamp = event.get("timestamp")
    if isinstance(timestamp, str):
        return _sample_time({"ts": timestamp}) or ""
    return ""


def _empty_result() -> dict[str, Any]:
    return {key: [] for key in (
        "nvrm", "psi_observations", "psi_signal", "service_observations", "service_loss",
        "service_recovery", "watchdog", "boot", "could_not_run")}


def _classify_journal_row(row: dict[str, Any], seen_boots: set[str], out: dict[str, Any]) -> None:
    message = str(row.get("MESSAGE", ""))
    timestamp = _journal_time(row)
    unit = row.get("UNIT") or row.get("_SYSTEMD_UNIT")
    boot_id = _boot_id(row)
    if boot_id and boot_id not in seen_boots:
        seen_boots.add(str(boot_id))
        out["boot"].append(_milestone(
            "journal", row, timestamp,
            message="Primera observación de este boot en el registro aportado",
            note="inicio exacto del boot desconocido"))
    if OOM.search(message):
        hit = _milestone("journal", row, timestamp, message=message, unit=unit,
                         allocator_signature=bool(ALLOCATOR.search(message)))
        if timestamp is None:
            hit["timestamp_status"] = "could_not_run: journal sin __REALTIME_TIMESTAMP válido"
        out["nvrm"].append(hit)
    if SERVICE_LOSS.search(message):
        out["service_loss"].append(_milestone("journal", row, timestamp, message=message, unit=unit))
    if SERVICE_RECOVERY.search(message) and (unit or row.get("UNIT")):
        out["service_recovery"].append(_milestone("journal", row, timestamp, message=message, unit=unit))
    if WATCHDOG.search(message) and unit:
        out["watchdog"].append(_milestone("journal", row, timestamp, message=message, unit=unit))
    if "[bb-usable] COLAPSO:" in message:
        out["psi_signal"].append(_milestone(
            "journal", row, timestamp, message=message, unit=unit,
            note="señal emitida por bb-usable; timestamp de detección, no inicio físico"))
    if BOOT.search(message):
        out["boot"].append(_milestone("journal", row, timestamp, message=message))


def _journal_events(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out = _empty_result()
    seen_boots: set[str] = set()
    ordered = sorted(rows, key=lambda row: _journal_time(row) or "")
    for row in ordered:
        _classify_journal_row(row, seen_boots, out)
    return out


def _psi_samples(rows: list[dict[str, Any]], out: dict[str, Any]) -> None:
    observed = False
    for row in rows:
        psi = row.get("psi")
        psi_value = (psi.get("mem_full") if isinstance(psi, dict) else None)
        if psi_value is None:
            psi_value = row.get("psi_mem_full_avg10")
        if psi_value is not None:
            try:
                valid_psi = math.isfinite(float(psi_value)) and 0 <= float(psi_value) <= 100
            except (ValueError, TypeError, OverflowError):
                valid_psi = False
            if valid_psi:
                observed = True
                out["psi_observations"].append(_milestone(
                    "bb_sample", row, row.get("ts"), mem_full=float(psi_value),
                    note="observación; el muestreo no fija el inicio físico ni causalidad"))
            else:
                out["could_not_run"].append("muestras: psi memory full inválido")
    if rows and not observed:
        out["could_not_run"].append("muestras: no hay ninguna observación válida de PSI memory full")


def _service_samples(rows: list[dict[str, Any]], out: dict[str, Any]) -> None:
    # Respuesta de SSH útil es una sonda opcional ya existente; estados ausentes
    # o desactivados no se convierten en servicio sano ni en una caída.
    previous = None
    previous_boot = None
    saw_service_field = False
    service_disabled = False
    for row in rows:
        boot_id = _boot_id(row)
        if boot_id != previous_boot:
            previous = None
            previous_boot = boot_id
        service = row.get("servicio_ssh")
        service_data = service if isinstance(service, dict) else {}
        state = service_data.get("estado")
        if state:
            saw_service_field = True
            state = str(state).upper()
            out["service_observations"].append(_milestone(
                "bb_sample", row, row.get("ts"), service_state=state,
                reason=service_data.get("motivo"), note="estado observado por la sonda SSH configurada"))
            if state in {"ERROR", "TIMEOUT"} and state != previous:
                out["service_loss"].append(_milestone(
                    "bb_sample", row, row.get("ts"), service_state=state,
                    reason=service_data.get("motivo"),
                    note="falló la sonda SSH configurada; no equivale a caída de todo el servicio"))
            elif state == "OK" and previous in {"ERROR", "TIMEOUT"}:
                out["service_recovery"].append(_milestone(
                    "bb_sample", row, row.get("ts"), service_state=state,
                    note="la sonda SSH respondió después de un estado ERROR/TIMEOUT"))
            elif state == "DESACTIVADO":
                service_disabled = True
            previous = state
    if rows and not saw_service_field:
        out["could_not_run"].append("muestras: falta servicio_ssh.estado (sonda opcional no observada)")
    elif service_disabled:
        out["could_not_run"].append("muestras: servicio_ssh figura DESACTIVADO")


def analyze(journal: Iterable[dict[str, Any]], samples: Iterable[dict[str, Any]]) -> dict[str, Any]:
    journal_rows, sample_rows = list(journal), list(samples)
    out = _journal_events(journal_rows)
    ordered_samples = sorted(sample_rows, key=lambda row: _sample_time(row) or "")
    _psi_samples(ordered_samples, out)
    _service_samples(ordered_samples, out)
    for key, events in out.items():
        if key != "could_not_run":
            events.sort(key=_event_sort_time)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--journal", required=True, type=Path,
                        help="JSONL producido por journalctl -o json")
    parser.add_argument("--samples", required=True, type=Path,
                        help="JSONL de muestras de bb; use un archivo vacío si no existe serie")
    args = parser.parse_args(argv)
    could_not_run: list[str] = []
    journal = _read_jsonl(args.journal, "journal", could_not_run)
    samples = _read_jsonl(args.samples, "muestras", could_not_run)
    result = analyze(journal, samples)
    could_not_run.extend(result.pop("could_not_run", []))
    for label, rows in (("journal", journal), ("muestras", samples)):
        if rows:
            missing_ts = sum(1 for row in rows if
                             (_journal_time(row) if label == "journal" else _sample_time(row)) is None)
            missing_boot = sum(1 for row in rows if
                               _boot_id(row) is None)
            if missing_ts:
                could_not_run.append(f"{label}: timestamp inválido/ausente en {missing_ts} registro(s)")
            if missing_boot:
                could_not_run.append(f"{label}: boot_id ausente en {missing_boot} registro(s)")
    result["could_not_run"] = could_not_run
    result["interpretation"] = "Hitos observados; sin inferencia de causalidad ni inicio físico."
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if could_not_run else 0


if __name__ == "__main__":
    sys.exit(main())
