"""Compare caller-declared recipe memory with a host MemAvailable observation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
from collections.abc import Mapping
from typing import Any, cast

from tools.memory_profile import capture

COMPONENTS = ("weights", "kv_cache", "staging", "graphs", "draft", "buffers")


def assess(components: Mapping[str, int | None], available_bytes: int | None,
           reserve_bytes: int | None) -> dict[str, Any]:
    """Return unknown for missing terms; a complete result is only a comparison."""
    missing = [name for name in (*COMPONENTS, "reserve")
               if (components.get(name) if name != "reserve" else reserve_bytes) is None]
    invalid = [name for name in COMPONENTS if components.get(name) is not None and
               (type(components[name]) is not int or cast(int, components[name]) < 0)]
    if reserve_bytes is not None and (type(reserve_bytes) is not int or reserve_bytes < 0):
        invalid.append("reserve")
    if available_bytes is None:
        missing.append("MemAvailable")
    elif type(available_bytes) is not int or available_bytes < 0:
        invalid.append("MemAvailable")
    if invalid:
        return {"status": "invalid", "invalid_fields": invalid, "missing_fields": missing}
    if missing:
        return {"status": "unknown", "missing_fields": missing}
    assert available_bytes is not None and reserve_bytes is not None
    required = sum(cast(int, components[name]) for name in COMPONENTS) + reserve_bytes
    return {"status": "comparison_only",
            "comparison": "within_declared_budget" if required <= available_bytes
            else "exceeds_available",
            "required_bytes": required, "available_bytes": available_bytes,
            "headroom_bytes": available_bytes - required}


def collect(components: dict[str, int | None], reserve_bytes: int | None,
            root: Path = Path("/")) -> dict[str, Any]:
    host = capture(root)
    host_context = cast(dict[str, Any], host["host_reserve_context"])
    memory = cast(dict[str, Any], host_context["memavailable"])
    kib = memory.get("kib")
    available = kib * 1024 if memory.get("status") == "ok" and type(kib) is int else None
    assessment = assess(components, available, reserve_bytes)
    record: dict[str, Any] = {
        "schema": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": {"system": platform.system(), "release": platform.release(),
                 "machine": platform.machine()},
        "recipe_components_bytes": components,
        "component_provenance": "caller_supplied_unverified",
        "host_memavailable": memory,
        "assessment": assessment,
        "source": "tools.memory_profile.capture",
        "raw_host_capture": host,
    }
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    record["record_sha256"] = hashlib.sha256(canonical).hexdigest()
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in COMPONENTS:
        parser.add_argument(f"--{name.replace('_', '-')}-bytes", type=int)
    parser.add_argument("--reserve-bytes", type=int)
    parser.add_argument("--root", type=Path, default=Path("/"), help="host root; fixture use")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    components = {name: getattr(args, f"{name}_bytes") for name in COMPONENTS}
    record = collect(components, args.reserve_bytes, args.root)
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0 if record["assessment"]["status"] == "comparison_only" else 2


if __name__ == "__main__":
    raise SystemExit(main())
