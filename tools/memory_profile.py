"""Capture the host page and NVIDIA UVM profile with per-source read status."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


def read_text(path: Path) -> dict[str, str | None]:
    try:
        return {"status": "ok", "value": path.read_text(encoding="utf-8").strip(), "error": None}
    except FileNotFoundError as exc:
        return {"status": "absent", "value": None, "error": str(exc)}
    except PermissionError as exc:
        return {"status": "read_denied", "value": None, "error": str(exc)}
    except (OSError, UnicodeError) as exc:
        return {"status": "collection_failed", "value": None,
                "error": f"{type(exc).__name__}: {exc}"}


def command(argv: list[str]) -> dict[str, object]:
    try:
        result = subprocess.run(argv, text=True, capture_output=True, timeout=5, check=False)
    except FileNotFoundError as exc:
        return {"status": "unsupported", "command": argv, "value": None, "error": str(exc)}
    except PermissionError as exc:
        return {"status": "read_denied", "command": argv, "value": None, "error": str(exc)}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "collection_failed", "command": argv, "value": None,
                "error": f"{type(exc).__name__}: {exc}"}
    status = "ok" if result.returncode == 0 else "collection_failed"
    return {"status": status, "command": argv, "returncode": result.returncode,
            "value": result.stdout.strip() if result.returncode == 0 else None,
            "stderr": result.stderr.strip() or None}


def capture(root: Path = Path("/"), page_size_bytes: int | None = None) -> dict[str, object]:
    module = root / "sys/module/nvidia_uvm"
    parameters = module / "parameters"
    loaded = module.exists()
    version = read_text(module / "version") if loaded else {
        "status": "module_not_loaded", "value": None, "error": None}
    srcversion = read_text(module / "srcversion") if loaded else {
        "status": "module_not_loaded", "value": None, "error": None}
    parameter_path = parameters / "uvm_pack_sysmem_leaf_tables"
    parameter = read_text(parameter_path) if loaded else {
        "status": "module_not_loaded", "value": None, "error": None}
    if loaded and parameter["status"] == "absent":
        parameter["status"] = "unsupported"
    disk = command(["modinfo", "-F", "version", "nvidia_uvm"])
    disk_srcversion = command(["modinfo", "-F", "srcversion", "nvidia_uvm"])
    return {
        "schema": 1,
        "kernel": {"release": platform.uname().release,
                   "page_size_bytes": (page_size_bytes if page_size_bytes is not None
                                       else os.sysconf("SC_PAGE_SIZE")),
                   "page_size_source": "os.sysconf(SC_PAGE_SIZE)"},
        "uvm": {"loaded": loaded, "loaded_version": version,
                "loaded_srcversion": srcversion, "disk_version": disk,
                "disk_srcversion": disk_srcversion, "packing_parameter": parameter,
                "packing_parameter_source": str(parameter_path)},
        "thp": {"enabled": read_text(root / "sys/kernel/mm/transparent_hugepage/enabled"),
                "defrag": read_text(root / "sys/kernel/mm/transparent_hugepage/defrag")},
        "host_reserve_context": {"meminfo": read_text(root / "proc/meminfo"),
                                 "cmdline": read_text(root / "proc/cmdline")},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--root", type=Path, default=Path("/"),
                        help="filesystem root for fixture use")
    args = parser.parse_args()
    record = capture(args.root)
    payload = json.dumps(record, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
