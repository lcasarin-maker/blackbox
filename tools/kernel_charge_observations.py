"""Parse literal output from ``tools/kernel_charges.bt`` captures.

This validates probe output structure and derived executor-scope counts. It
cannot attribute the charged memcg: the probe itself reports ``owner=unknown``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

READY = re.compile(
    r"^READY abi=linux-6\.17-kmem-page-charge page_size=(\d+) "
    r"scope_cgroup_id=(\d+) attribution=executor-cgroup-only owner=unknown$"
)
SNAPSHOT = re.compile(r"^SNAPSHOT t=(\d+) owner=unknown attribution=executor-task-cgroup$")
FINAL = "FINAL owner=unknown attribution=executor-task-cgroup"
MAP_ROW = re.compile(r"^@([a-z][a-z0-9_]*)(?:\[(.*)\])?:\s*(-?\d+)$")
MAP_EMPTY = re.compile(r"^@([a-z][a-z0-9_]*):\s*(?:empty|\{\})$")
MAPS = {
    "live_bytes_by_executor", "live_pages_by_executor", "charge_events",
    "uncharge_events", "charge_failures", "duplicate_charge", "replaced_bytes",
    "order_mismatch", "page_bytes", "pending_page", "pending_bytes",
    "pending_executor_cgroup", "pending_comm",
}
REQUIRED_FINAL = {
    "live_bytes_by_executor", "live_pages_by_executor", "charge_events",
    "uncharge_events", "charge_failures", "duplicate_charge", "order_mismatch",
    "page_bytes", "pending_page",
}


class _Incomplete(ValueError):
    pass


class _Contradiction(ValueError):
    pass


def _result(status: str, findings: list[str], **data: Any) -> dict[str, Any]:
    return {"status": status, "fail": int(status == "fail"),
            "could_not_run": int(status == "unknown"), "findings": findings,
            "owner": "unknown", "closure": "open", **data}


def _map_rows(lines: list[str], section: str) -> dict[str, dict[str, int]]:
    maps: dict[str, dict[str, int]] = {}
    for line in lines:
        empty = MAP_EMPTY.fullmatch(line)
        if empty:
            name = empty.group(1)
            if name not in MAPS:
                raise _Contradiction(f"unknown map in {section}: {name}")
            if name in maps:
                raise _Contradiction(f"repeated map declaration in {section}: {name}")
            maps[name] = {}
            continue
        match = MAP_ROW.fullmatch(line)
        if not match:
            raise _Contradiction(f"malformed map row in {section}: {line}")
        name, key, raw_value = match.groups()
        if name not in MAPS:
            raise _Contradiction(f"unknown map in {section}: {name}")
        if name not in maps:
            maps[name] = {}
        normalized_key = key if key is not None else "<scalar>"
        if normalized_key in maps[name]:
            raise _Contradiction(f"duplicate map key in {section}: {name}[{normalized_key}]")
        maps[name][normalized_key] = int(raw_value)
    return maps


def _nonnegative(maps: dict[str, dict[str, int]], section: str) -> None:
    for name, rows in maps.items():
        if any(value < 0 for value in rows.values()):
            raise _Contradiction(f"negative observed counter in {section}: {name}")


def parse_stdout(stdout: str, stderr: str = "", returncode: int = 0) -> dict[str, Any]:
    """Parse READY/SNAPSHOT/FINAL and derive counts from printed map rows."""
    if type(returncode) is not int:
        return _result("unknown", ["probe exit code unavailable"])
    if returncode != 0 or stderr:
        return _result("unknown", [f"probe execution unavailable: rc={returncode}; stderr_present={bool(stderr)}"])
    if not isinstance(stdout, str) or not stdout.strip():
        return _result("unknown", ["probe stdout absent"])
    try:
        return _parse(stdout)
    except _Incomplete as exc:
        return _result("unknown", [str(exc)])
    except _Contradiction as exc:
        return _result("fail", [str(exc)])


def _parse(stdout: str) -> dict[str, Any]:
    lines = [line.rstrip("\r") for line in stdout.splitlines()]
    sections = _Sections()
    for line in lines:
        sections.feed(line)
    ready, snapshots, final_lines = sections.finish()
    page_size, cgroup_id = (int(value) for value in ready.groups())
    if page_size <= 0 or cgroup_id <= 0:
        raise _Contradiction("READY page size or executor cgroup ID is invalid")
    snapshot_maps = [(timepoint, _map_rows(rows, f"snapshot t={timepoint}"))
                     for timepoint, rows in snapshots]
    final_maps = _map_rows(final_lines, "FINAL")
    return _final_result(page_size, cgroup_id, snapshot_maps, final_maps)


class _Sections:
    def __init__(self) -> None:
        self.ready_rows: list[tuple[str, re.Match[str] | None]] = []
        self.snapshots: list[tuple[int, list[str]]] = []
        self.section: list[str] | None = None
        self.final_lines: list[str] | None = None
        self.current_time: int | None = None
        self.seen_final = False

    def feed(self, line: str) -> None:
        if line.startswith("READY "):
            self.ready_rows.append((line, READY.fullmatch(line)))
            return
        snap = SNAPSHOT.fullmatch(line)
        if snap:
            self._snapshot(snap)
            return
        if line.startswith("SNAPSHOT "):
            raise _Contradiction("malformed SNAPSHOT header")
        if line == FINAL:
            self._final()
            return
        if line.startswith("@"):
            self._map_line(line)
        elif line and not line.startswith("READY "):
            raise _Contradiction(f"unexpected stdout line: {line}")

    def _snapshot(self, snap: re.Match[str]) -> None:
        if self.seen_final:
            raise _Contradiction("snapshot appears after FINAL")
        if self.current_time is not None:
            self.snapshots.append((self.current_time, self.section or []))
        self.current_time = int(snap.group(1))
        if self.snapshots and self.current_time <= self.snapshots[-1][0]:
            raise _Contradiction("snapshot times are repeated or out of order")
        self.section = []

    def _final(self) -> None:
        if self.seen_final:
            raise _Contradiction("repeated FINAL section")
        if self.current_time is not None:
            self.snapshots.append((self.current_time, self.section or []))
        self.final_lines = []
        self.section = self.final_lines
        self.seen_final = True
        self.current_time = None

    def _map_line(self, line: str) -> None:
        if self.section is None:
            raise _Contradiction("map output precedes READY or a snapshot")
        self.section.append(line)

    def finish(self) -> tuple[re.Match[str], list[tuple[int, list[str]]], list[str]]:
        if len(self.ready_rows) != 1:
            raise _Incomplete("one valid READY ABI/identity line required")
        raw_ready, ready = self.ready_rows[0]
        if ready is None:
            if "owner=unknown" not in raw_ready:
                raise _Contradiction("READY claims unsupported memcg owner attribution")
            raise _Contradiction("READY ABI or executor identity malformed")
        if self.current_time is not None:
            self.snapshots.append((self.current_time, self.section or []))
        if not self.seen_final or self.final_lines is None:
            raise _Incomplete("FINAL section absent; capture may be truncated")
        return ready, self.snapshots, self.final_lines


def _final_result(page_size: int, cgroup_id: int,
                  snapshots: list[tuple[int, dict[str, dict[str, int]]]],
                  final_maps: dict[str, dict[str, int]]) -> dict[str, Any]:
    for timepoint, maps in snapshots:
        _nonnegative(maps, f"snapshot t={timepoint}")
    _nonnegative(final_maps, "FINAL")
    missing = REQUIRED_FINAL - final_maps.keys()
    if missing:
        raise _Incomplete("FINAL lacks printed maps: " + ", ".join(sorted(missing)))
    pending = sum(final_maps["pending_page"].values())
    if pending:
        raise _Incomplete(f"FINAL has {pending} pending charge return(s)")
    charge = sum(final_maps["charge_events"].values())
    uncharge = sum(final_maps["uncharge_events"].values())
    live_bytes = sum(final_maps["live_bytes_by_executor"].values())
    live_pages = sum(final_maps["live_pages_by_executor"].values())
    page_bytes = sum(final_maps["page_bytes"].values())
    if live_bytes != page_bytes or live_pages != len(final_maps["page_bytes"]):
        raise _Contradiction("live aggregate differs from outstanding page ledger")
    if charge - uncharge != live_pages:
        raise _Contradiction("charge/uncharge event delta differs from outstanding page count")
    if live_bytes < 0 or live_pages < 0:
        raise _Contradiction("final live totals are negative")
    metrics = {name: sum(final_maps[name].values()) for name in
               ("charge_failures", "duplicate_charge", "order_mismatch")}
    findings = [f"{name}={count}" for name, count in metrics.items() if count]
    status = "fail" if findings else "pass"
    return _result(
        status, findings, page_size=page_size, executor_cgroup_id=cgroup_id,
        snapshots=[{"seconds": t, "maps": len(m)} for t, m in snapshots],
        charge_events=charge, uncharge_events=uncharge,
        charge_failures=metrics["charge_failures"],
        duplicate_charges=metrics["duplicate_charge"],
        order_mismatches=metrics["order_mismatch"],
        outstanding_pages=live_pages, outstanding_bytes=live_bytes,
        attribution="executor cgroup only; active owner memcg unknown",
        scope="stdout consistency only; no proof that the probe saw every allocation",
    )


def verify_directory(evidence: Path) -> dict[str, Any]:
    """Read exact stdout/stderr/exit sidecars; absence remains could_not_run."""
    stdout_path = evidence / "kernel-charges.stdout"
    stderr_path = evidence / "kernel-charges.stderr"
    exit_path = evidence / "kernel-charges.exit"
    try:
        stdout = stdout_path.read_text(encoding="utf-8")
        stderr = stderr_path.read_text(encoding="utf-8")
        raw_exit = exit_path.read_text(encoding="ascii").strip()
    except (OSError, UnicodeError) as exc:
        return _result("unknown", [f"raw probe capture unavailable: {exc}"])
    if not re.fullmatch(r"-?\d+", raw_exit):
        return _result("unknown", ["probe exit sidecar malformed"])
    return parse_stdout(stdout, stderr, int(raw_exit))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args(argv)
    result = verify_directory(args.evidence)
    print(json.dumps(result, sort_keys=True))
    return {"pass": 0, "fail": 1, "unknown": 2}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
