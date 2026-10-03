"""Read-only provenance extraction for captured vLLM Prometheus text."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


METRICS = {
    "vllm:num_requests_running": "vllm_num_requests_running",
    "vllm:num_requests_waiting": "vllm_num_requests_waiting",
    "vllm:num_requests_waiting_by_reason": "vllm_num_requests_waiting_by_reason",
    "vllm:kv_cache_usage_perc": "vllm_kv_cache_usage_perc",
    "vllm:num_preemptions_total": "vllm_num_preemptions_total",
}
SAMPLE_START = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{(.*)\})?\s+([^\s]+)(?:\s+([^\s]+))?$")
IDENTIFIER = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
VALID_TYPES = {"counter", "gauge", "histogram", "summary", "untyped"}
INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1


@dataclass
class Capture:
    types: dict[str, str] = field(default_factory=dict)
    helps: dict[str, str] = field(default_factory=dict)
    seen_samples: set[tuple[str, tuple[tuple[str, str], ...]]] = field(default_factory=set)
    sample_seen_metrics: set[str] = field(default_factory=set)
    seen_type_declarations: set[str] = field(default_factory=set)
    declared_type_values: dict[str, str] = field(default_factory=dict)
    seen_help_declarations: set[str] = field(default_factory=set)
    indeterminate_types: set[str] = field(default_factory=set)
    samples: list[dict[str, Any]] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    unreadable_observation_count: int = 0


def _label_at(raw: str, position: int) -> tuple[str, str, int] | None:
    name = IDENTIFIER.match(raw, position)
    if name is None:
        return None
    position = name.end()
    while position < len(raw) and raw[position].isspace():
        position += 1
    if position >= len(raw) or raw[position] != "=":
        return None
    position += 1
    while position < len(raw) and raw[position].isspace():
        position += 1
    if position >= len(raw) or raw[position] != '"':
        return None
    position += 1
    value: list[str] = []
    while position < len(raw) and raw[position] != '"':
        char = raw[position]
        position += 1
        if char == "\\":
            if position >= len(raw) or raw[position] not in '\\"n':
                return None
            escaped = raw[position]
            position += 1
            value.append("\n" if escaped == "n" else escaped)
        else:
            value.append(char)
    if position >= len(raw):
        return None
    return name.group(), "".join(value), position + 1


def _labels(raw: str | None) -> dict[str, str] | None:
    if raw is None or raw == "":
        return {}
    labels: dict[str, str] = {}
    position = 0
    while position < len(raw):
        label = _label_at(raw, position)
        if label is None or label[0] in labels:
            return None
        name, value, position = label
        labels[name] = value
        while position < len(raw) and raw[position].isspace():
            position += 1
        if position == len(raw):
            break
        if raw[position] != ",":
            return None
        position += 1
        while position < len(raw) and raw[position].isspace():
            position += 1
        if position == len(raw):
            break
    return labels


def _timestamp(raw: str | None) -> int | None | bool:
    if raw is None:
        return None
    if not re.fullmatch(r"[+-]?\d+", raw):
        return False
    value = int(raw)
    if not INT64_MIN <= value <= INT64_MAX:
        return False
    return value


def _sample(line: str, number: int, capture_path: str, state: Capture
            ) -> tuple[dict[str, Any] | None, str | None, bool]:
    match = SAMPLE_START.fullmatch(line)
    if match is None:
        if any(name in line for name in METRICS):
            return None, f"line {number}: malformed sample", True
        return None, None, False
    name, raw_labels, raw_value, raw_timestamp = match.groups()
    if name not in METRICS:
        return None, None, False
    labels = _labels(raw_labels)
    timestamp = _timestamp(raw_timestamp)
    if labels is None or timestamp is False:
        return None, f"line {number}: invalid labels or timestamp for {name}", True
    try:
        float(raw_value)
    except ValueError:
        return None, f"line {number}: invalid numeric value for {name}", True
    identity = (name, tuple(sorted(labels.items())))
    if identity in state.seen_samples:
        return None, f"line {number}: duplicate metric and labels for {name}", True
    state.seen_samples.add(identity)
    samples = {
        "capture_path": capture_path,
        "capture_path_provenance": "caller_supplied_unverified",
        "observation_source": "captured_prometheus_text",
        "observed_metric_name": name,
        "sampler_field": METRICS[name],
        "observed_type": state.types.get(name, "untyped"),
        "type_provenance": "declared" if name in state.types else "default_untyped",
        "type_interpretation": "indeterminate" if name in state.indeterminate_types else "observed",
        "observed_help": state.helps.get(name),
        "semantic_unit_status": "not_declared_in_capture",
        "labels": labels,
        "raw_value": raw_value,
    }
    if timestamp is not None:
        samples["timestamp_ms"] = timestamp
    return samples, None, False


def _type_line(line: str, number: int, state: Capture) -> None:
    parts = line.split(maxsplit=3)
    if len(parts) < 3 or parts[2] not in METRICS:
        if len(parts) < 4:
            state.issues.append(f"line {number}: malformed TYPE declaration")
        return
    name = parts[2]
    if name in state.seen_type_declarations:
        state.issues.append(f"line {number}: duplicate TYPE declaration for {name}")
        if len(parts) == 4 and parts[3] in VALID_TYPES and state.declared_type_values.get(name) != parts[3]:
            state.issues.append(f"line {number}: conflicting TYPE declaration for {name}")
            state.indeterminate_types.add(name)
            affected = [sample for sample in state.samples if sample["observed_metric_name"] == name]
            for sample in affected:
                sample["type_interpretation"] = "indeterminate"
            state.unreadable_observation_count += len(affected)
        return
    state.seen_type_declarations.add(name)
    if len(parts) != 4 or parts[3] not in VALID_TYPES:
        state.issues.append(f"line {number}: malformed TYPE declaration for {name}")
    else:
        state.declared_type_values[name] = parts[3]
        if name in state.sample_seen_metrics:
            state.issues.append(f"line {number}: TYPE declaration after first sample for {name}")
        else:
            state.types[name] = parts[3]


def _help_line(line: str, number: int, state: Capture) -> None:
    parts = line[2:].split(maxsplit=2)
    if len(parts) < 2 or parts[1] not in METRICS:
        return
    name = parts[1]
    if name in state.seen_help_declarations:
        state.issues.append(f"line {number}: duplicate HELP declaration for {name}")
    else:
        state.seen_help_declarations.add(name)
        state.helps[name] = parts[2] if len(parts) == 3 else ""


def _consume_line(line: str, number: int, capture_path: str, state: Capture) -> None:
    if not line:
        return
    if line.startswith("# TYPE "):
        _type_line(line, number, state)
        return
    if line.startswith("# HELP "):
        _help_line(line, number, state)
        return
    if line.startswith("#"):
        return
    sample, issue, unreadable = _sample(line, number, capture_path, state)
    if sample is not None:
        state.samples.append(sample)
        state.sample_seen_metrics.add(sample["observed_metric_name"])
        if sample["type_interpretation"] == "indeterminate":
            state.unreadable_observation_count += 1
    if issue is not None:
        state.issues.append(issue)
    state.unreadable_observation_count += int(unreadable)


def _result(state: Capture) -> dict[str, Any]:
    if not state.samples:
        state.issues.append("capture contains no recognized vLLM metric samples")
        status = "unknown"
        could_not_run_count = max(1, state.unreadable_observation_count)
    elif state.issues:
        status = "partial"
        could_not_run_count = state.unreadable_observation_count
    else:
        status = "observed"
        could_not_run_count = 0
    return {"status": status, "samples": state.samples, "issues": state.issues,
            "unreadable_observation_count": state.unreadable_observation_count,
            "could_not_run_count": could_not_run_count}


def parse_capture(text: str, capture_path: str) -> dict[str, Any]:
    """Extract exact known samples; path provenance is supplied and unverified."""
    state = Capture()
    for number, raw_line in enumerate(text.splitlines(), 1):
        _consume_line(raw_line.strip(), number, capture_path, state)
    return _result(state)


def analyze_file(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return {"status": "unknown", "samples": [], "issues": [f"cannot read capture: {exc}"],
                "unreadable_observation_count": 0, "could_not_run_count": 1}
    return parse_capture(text, str(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path, help="saved Prometheus text capture")
    args = parser.parse_args(argv)
    result = analyze_file(args.capture)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "observed" else 2


if __name__ == "__main__":
    sys.exit(main())
