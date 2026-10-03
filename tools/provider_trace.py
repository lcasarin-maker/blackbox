"""Read-only analysis of request-scoped JSONL provider traces.

Each non-empty line is an object with an ``event`` field. Supported events
are request (request_id, requested_provider), worker (request_id, worker_id,
pid), provider (request_id, worker_id, provider), latency (request_id,
worker_id, milliseconds), and restart (request_id, old_worker_id,
new_worker_id). Lines are chronological; a provider observation after a
restart must belong to the replacement worker.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


GPU_PROVIDERS = {"gpu", "cuda", "cudaexecutionprovider", "tensorrtexecutionprovider"}
CPU_PROVIDERS = {"cpu", "cpuexecutionprovider"}


def _result(status: str, findings: list[str] | None = None, unknowns: list[str] | None = None,
            could_not_run_count: int = 0) -> dict[str, Any]:
    return {"status": status, "findings": findings or [], "unknowns": unknowns or [],
            "could_not_run_count": could_not_run_count}


def _unknown(*reasons: str, could_not_run_count: int = 0) -> dict[str, Any]:
    return _result("unknown", unknowns=list(reasons), could_not_run_count=could_not_run_count)


def _canonical_provider(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    name = value.strip().casefold()
    if name in GPU_PROVIDERS:
        return "gpu"
    if name in CPU_PROVIDERS:
        return "cpu"
    return None


def analyze_lines(lines: list[str]) -> dict[str, Any]:
    """Classify trace lines while keeping every observation scoped to a request."""
    requests: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for line_number, raw in enumerate(lines, start=1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            errors.append(f"line {line_number}: malformed or truncated JSON")
            continue
        if not isinstance(record, dict):
            errors.append(f"line {line_number}: event must be a JSON object")
            continue
        _consume(record, requests, errors, line_number)

    blocks: list[str] = []
    unknowns: list[str] = errors.copy()
    for request_id, state in requests.items():
        findings, unknown = _classify_request(request_id, state)
        blocks.extend(findings)
        unknowns.extend(unknown)
    if blocks:
        return _result("block", findings=blocks, unknowns=unknowns)
    if unknowns:
        return _result("unknown", unknowns=unknowns)
    if not requests:
        return _unknown("trace contains no request events")
    return _result("pass")


def _consume(record: dict[str, Any], requests: dict[str, dict[str, Any]], errors: list[str], line: int) -> None:
    event = record.get("event")
    request_id = record.get("request_id")
    if event not in ("request", "worker", "provider", "latency", "restart"):
        errors.append(f"line {line}: unknown event type")
        return
    if not isinstance(request_id, str) or not request_id.strip():
        errors.append(f"line {line}: missing request_id")
        return
    if event == "request":
        _request_event(record, requests, errors, request_id)
        return
    state = requests.get(request_id)
    if state is None:
        errors.append(f"line {line}: event references unknown request {request_id}")
        return
    if event == "worker":
        _worker_event(record, state, errors, line, request_id)
    elif event == "provider":
        _provider_event(record, state, errors, request_id)
    elif event == "latency":
        _latency_event(record, state, errors, request_id)
    else:
        _restart_event(record, state, errors, request_id)


def _request_event(record: dict[str, Any], requests: dict[str, dict[str, Any]], errors: list[str], request_id: str) -> None:
    requested = _canonical_provider(record.get("requested_provider"))
    if request_id in requests:
        errors.append(f"request {request_id}: duplicate request event")
    elif requested is None:
        errors.append(f"request {request_id}: unknown requested provider")
    else:
        requests[request_id] = {"requested": requested, "worker": None, "pid": None,
                                "provider_events": [], "provider": None, "provider_worker": None,
                                "latency": None, "latency_worker": None,
                                "restart_seen": False}


def _provider_event(record: dict[str, Any], state: dict[str, Any], errors: list[str], request_id: str) -> None:
    provider = _canonical_provider(record.get("provider"))
    worker_id = record.get("worker_id")
    if provider is None:
        errors.append(f"request {request_id}: unknown observed provider")
    elif not _worker_matches(state, worker_id):
        errors.append(f"request {request_id}: provider has missing or stale worker_id")
    else:
        state["provider_events"].append((worker_id, provider))
        state["provider"] = provider
        state["provider_worker"] = worker_id


def _latency_event(record: dict[str, Any], state: dict[str, Any], errors: list[str], request_id: str) -> None:
    worker_id = record.get("worker_id")
    latency = record.get("milliseconds")
    if not _worker_matches(state, worker_id):
        errors.append(f"request {request_id}: latency has missing or stale worker_id")
    elif not isinstance(latency, (int, float)) or isinstance(latency, bool) or latency < 0 or latency > sys.float_info.max or not math.isfinite(latency):
        errors.append(f"request {request_id}: invalid latency")
    else:
        state["latency"] = latency
        state["latency_worker"] = worker_id


def _restart_event(record: dict[str, Any], state: dict[str, Any], errors: list[str], request_id: str) -> None:
    old_worker = record.get("old_worker_id")
    new_worker = record.get("new_worker_id")
    if not _worker_matches(state, old_worker) or not isinstance(new_worker, str) or not new_worker.strip() or old_worker == new_worker:
        errors.append(f"request {request_id}: invalid worker restart transition")
    else:
        state["worker"] = new_worker
        state["pid"] = None
        state["restart_seen"] = True


def _worker_matches(state: dict[str, Any], worker_id: object) -> bool:
    return bool(isinstance(worker_id, str) and worker_id.strip() and worker_id == state["worker"])


def _worker_event(record: dict[str, Any], state: dict[str, Any], errors: list[str], line: int, request_id: str) -> None:
    worker_id = record.get("worker_id")
    pid = record.get("pid")
    if not isinstance(worker_id, str) or not worker_id.strip() or type(pid) is not int or pid <= 0:
        errors.append(f"line {line}: invalid worker identity or pid for request {request_id}")
    elif state["worker"] is not None and worker_id != state["worker"]:
        errors.append(f"request {request_id}: worker changed without restart event")
    elif state["pid"] is not None and pid != state["pid"]:
        errors.append(f"request {request_id}: worker pid changed without restart event")
    else:
        state["worker"] = worker_id
        state["pid"] = pid


def _classify_request(request_id: str, state: dict[str, Any]) -> tuple[list[str], list[str]]:
    unknown: list[str] = []
    if state["worker"] is None or state["pid"] is None:
        unknown.append(f"request {request_id}: worker identity is incomplete")
    if state["provider"] is None or state["provider_worker"] != state["worker"]:
        unknown.append(f"request {request_id}: provider observation is missing or stale after worker change")
    if state["latency"] is None or state["latency_worker"] != state["worker"]:
        unknown.append(f"request {request_id}: latency observation is missing or stale after worker change")
    if state["restart_seen"] and state["pid"] is None:
        unknown.append(f"request {request_id}: replacement worker pid is missing")
    findings = [f"request {request_id}: GPU request was served by CPU on worker {worker_id}"
                for worker_id, provider in state["provider_events"]
                if state["requested"] == "gpu" and provider == "cpu"]
    return findings, unknown


def analyze_file(path: Path) -> dict[str, Any]:
    """Read a UTF-8 JSONL trace, mapping I/O and decoding failures to unknown."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return _unknown(f"cannot read trace: {exc}", could_not_run_count=1)
    return analyze_lines(content.splitlines())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path, help="UTF-8 JSONL request trace")
    args = parser.parse_args(argv)
    result = analyze_file(args.trace)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    sys.exit(main())
