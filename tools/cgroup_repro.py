#!/usr/bin/env python3
"""Bounded cgroup accounting reproduction for CPU and CUDA allocation paths."""
from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import hashlib
import json
import logging
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import uuid
from typing import Any

try:
    from tools.memory_profile import capture as capture_memory_profile
except ModuleNotFoundError as exc:
    if exc.name != "tools":
        raise
    from memory_profile import capture as capture_memory_profile

CGROUP_ROOT = Path("/sys/fs/cgroup")
PROC_ROOT = Path("/proc")

def read(path: Path) -> tuple[str | None, str | None]:
    try:
        return path.read_text(encoding="utf-8").strip(), None
    except (OSError, UnicodeError) as exc:
        return None, f"{type(exc).__name__}: {exc}"

def snapshot(pid: int) -> dict:
    cgroup, err = read(PROC_ROOT / str(pid) / "cgroup")
    cgpath = None
    if cgroup:
        for row in cgroup.splitlines():
            if row.startswith("0::"):
                cgpath = CGROUP_ROOT / row[3:].lstrip("/")
    names = ["memory.current", "memory.events", "memory.pressure", "dmem.capacity", "dmem.current", "cpu.stat"]
    files = {}
    for name in names:
        source = CGROUP_ROOT / name if name == "dmem.capacity" else cgpath / name if cgpath else None
        value, ferr = read(source) if source else (None, "cgroup v2 path unavailable")
        files[name] = {"value": value, "error": ferr}
    avail, avail_err = read(PROC_ROOT / "meminfo")
    if avail:
        avail = next((line for line in avail.splitlines() if line.startswith("MemAvailable:")), None)
    psi, psi_err = read(PROC_ROOT / "pressure/memory")
    return {"pid": pid, "proc_cgroup": cgroup, "proc_cgroup_error": err,
            "cgroup_path": str(cgpath) if cgpath else None, "files": files,
            "mem_available": avail, "mem_available_error": avail_err,
            "host_memory_pressure": psi, "host_memory_pressure_error": psi_err,
            "monotonic_ns": time.monotonic_ns()}

def configure_cuda(rt):
    rt.cudaMalloc.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_size_t]
    rt.cudaMalloc.restype = ctypes.c_int
    rt.cudaMallocManaged.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_size_t, ctypes.c_uint]
    rt.cudaMallocManaged.restype = ctypes.c_int
    rt.cudaMemset.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t]
    rt.cudaMemset.restype = ctypes.c_int
    rt.cudaFree.argtypes = [ctypes.c_void_p]
    rt.cudaFree.restype = ctypes.c_int
    rt.cudaDeviceSynchronize.argtypes = []
    rt.cudaDeviceSynchronize.restype = ctypes.c_int

def cuda_allocate(rt, api: str, size: int):
    ptr = ctypes.c_void_p()
    if api == "cuda_malloc":
        rc = rt.cudaMalloc(ctypes.byref(ptr), ctypes.c_size_t(size))
    else:
        rc = rt.cudaMallocManaged(ctypes.byref(ptr), ctypes.c_size_t(size), ctypes.c_uint(1))
    if rc: raise RuntimeError(f"allocation returned CUDA error {rc}")
    return ptr


def cuda_use_allocation(rt: Any, ptr: Any, api: str, size: int, name: str) -> None:
    try:
        rc = rt.cudaDeviceSynchronize()
        if rc: raise RuntimeError(f"cudaDeviceSynchronize returned CUDA error {rc}")
        rc = rt.cudaMemset(ptr, 1, ctypes.c_size_t(size))
        if rc: raise RuntimeError(f"cudaMemset returned CUDA error {rc}")
        rc = rt.cudaDeviceSynchronize()
        if rc: raise RuntimeError(f"allocation synchronize returned CUDA error {rc}")
        print(json.dumps({"phase": "held", "api": api, "requested_bytes": size, "cuda_runtime": name,
                          "touch": "cudaMemset byte pattern 1 over full allocation; synchronized", **snapshot(os.getpid())}), flush=True)
        time.sleep(2)  # blocking-sleep: retain allocation for cgroup observation -- DEBT-ESCRITORIO-Y-ARNESES-COMPARTEN-CGROUP  # sunset-reviewed: 2.6 -- el worker acotado retiene la asignación durante la ventana de observación; positivo alcanza 2 s y neutralizado queda debajo. Ver tasks/evidence/CLEAN-2026-10-03/renew-sleeps.txt#RENEW-14-16
    except BaseException as primary:
        # Keep teardown secondary to the allocation failure, including cancellation.
        cleanup_errors = _release_cuda_allocation(rt, ptr)
        if cleanup_errors:
            primary.add_note("CUDA cleanup failures: " + "; ".join(map(str, cleanup_errors)))
        raise
    else:
        cleanup_errors = _release_cuda_allocation(rt, ptr)
        if cleanup_errors:
            cancellation = next((error for error in cleanup_errors if not isinstance(error, Exception)), None)
            if cancellation is not None:
                raise cancellation.with_traceback(cancellation.__traceback__)
            raise RuntimeError("CUDA cleanup failures: " + "; ".join(map(str, cleanup_errors)))

def cuda_worker(api: str, mib: int) -> int:
    name = ctypes.util.find_library("cudart")
    if not name:
        print(json.dumps({"phase": "error", "error": "libcudart not found"}), flush=True)
        return 32
    try:
        rt = ctypes.CDLL(name)
        configure_cuda(rt)
        # Initialize the context first so its fixed charge is a separate baseline.
        rc = rt.cudaFree(None)
        if rc: raise RuntimeError(f"CUDA context warmup returned error {rc}")
        rc = rt.cudaDeviceSynchronize()
        if rc: raise RuntimeError(f"warmup synchronize returned CUDA error {rc}")
        print(json.dumps({"phase": "before_allocation", "api": api, "requested_bytes": mib * 1024 * 1024,
                          "touch": "cudaMemset byte pattern 1 over full allocation", **snapshot(os.getpid())}), flush=True)
        size = mib * 1024 * 1024
        ptr = cuda_allocate(rt, api, size)
        cuda_use_allocation(rt, ptr, api, size, name)
    except Exception as exc:
        logging.error("Allocation worker failed: %s", exc)
        print(json.dumps({"phase": "error", "error": f"{type(exc).__name__}: {exc}",
                          "notes": getattr(exc, "__notes__", [])}), flush=True)
        return 33
    print(json.dumps({"phase": "after_release", **snapshot(os.getpid())}), flush=True)
    return 0

def _release_cuda_allocation(rt: Any, ptr: Any) -> list[BaseException]:
    errors: list[BaseException] = []
    try:
        rc = rt.cudaFree(ptr)
        if rc:
            errors.append(RuntimeError(f"cudaFree returned CUDA error {rc}; pointer state is uncertain and will not be retried"))
    except BaseException as exc:
        # The pointer state is unknown after a free failure; still synchronize, never retry.
        exc.add_note("pointer state is uncertain; cleanup will not retry cudaFree")
        errors.append(exc)
    try:
        rc = rt.cudaDeviceSynchronize()
        if rc:
            errors.append(RuntimeError(f"release cudaDeviceSynchronize returned CUDA error {rc}"))
    except BaseException as exc:
        errors.append(exc)
    return errors


def release_torch_allocation(torch: Any, allocated: bool, *, report: bool = True) -> list[BaseException]:
    if not allocated or torch is None:
        return []
    errors: list[BaseException] = []
    for label, cleanup in (("synchronize before empty_cache", torch.cuda.synchronize),
                           ("empty_cache", torch.cuda.empty_cache),
                           ("synchronize after empty_cache", torch.cuda.synchronize)):
        try:
            cleanup()
        except BaseException as exc:
            # Attempt every allocator cleanup phase and report all failures together.
            errors.append(exc)
    if not errors and report:
        print(json.dumps({"phase": "allocator_cache_released", **snapshot(os.getpid())}), flush=True)
    return errors

def torch_worker(mib: int) -> int:
    torch: Any = None
    tensor = None
    try:
        import torch
        if not torch.cuda.is_available(): raise RuntimeError("torch.cuda.is_available() is false")
        torch.cuda.init()
        warmup = torch.empty((1024,), dtype=torch.float16, device="cuda")
        warmup.fill_(1)
        torch.cuda.synchronize()
        del warmup
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        print(json.dumps({"phase": "before_allocation", "api": "torch.empty", "torch_version": torch.__version__,
                          "allocator": "PyTorch CUDA caching allocator", **snapshot(os.getpid())}), flush=True)
        tensor = torch.empty((mib * 1024 * 1024 // 2,), dtype=torch.float16, device="cuda")
        tensor.fill_(1)
        torch.cuda.synchronize()
        print(json.dumps({"phase": "held", "api": "torch.empty", "requested_bytes": mib * 1024 * 1024,
                          "pytorch_version": torch.__version__, "allocator": "PyTorch CUDA caching allocator",
                          "touch": "tensor.fill_(1); torch.cuda.synchronize()", **snapshot(os.getpid())}), flush=True)
        time.sleep(2)  # blocking-sleep: retain allocation for cgroup observation -- DEBT-ESCRITORIO-Y-ARNESES-COMPARTEN-CGROUP  # sunset-reviewed: 2.6 -- el worker acotado retiene la asignación durante la ventana de observación; positivo alcanza 2 s y neutralizado queda debajo. Ver tasks/evidence/CLEAN-2026-10-03/renew-sleeps.txt#RENEW-14-16
    # Preserve worker failures and cancellation while attaching teardown failures.
    except BaseException as primary:
        allocated = tensor is not None
        tensor = None
        cleanup_errors = release_torch_allocation(torch, allocated, report=False)
        if cleanup_errors:
            primary.add_note("PyTorch cleanup failures: " + "; ".join(map(str, cleanup_errors)))
        if isinstance(primary, Exception):
            logging.error("Allocation worker failed: %s", primary)
            print(json.dumps({"phase": "error", "error": f"{type(primary).__name__}: {primary}",
                              "notes": getattr(primary, "__notes__", [])}), flush=True)
            if allocated and not cleanup_errors:
                print(json.dumps({"phase": "allocator_cache_released", **snapshot(os.getpid())}), flush=True)
            return 30
        raise
    else:
        allocated = tensor is not None
        tensor = None
        cleanup_errors = release_torch_allocation(torch, allocated)
        if cleanup_errors:
            cancellation = next((error for error in cleanup_errors if not isinstance(error, Exception)), None)
            if cancellation is not None:
                raise cancellation.with_traceback(cancellation.__traceback__)
            exc = RuntimeError("PyTorch cleanup failures: " + "; ".join(map(str, cleanup_errors)))
            logging.error("Allocation worker failed: %s", exc)
            print(json.dumps({"phase": "error", "error": f"{type(exc).__name__}: {exc}", "notes": []}), flush=True)
            return 30
    print(json.dumps({"phase": "after_release", **snapshot(os.getpid())}), flush=True)
    return 0

def memory_worker(api: str, mib: int) -> int:
    buf = bytearray(mib * 1024 * 1024) if api == "cpu_touch" else None
    if buf is not None:
        for i in range(0, len(buf), 4096): buf[i] = 1
    print(json.dumps({"phase": "held", "api": api, "requested_bytes": len(buf) if buf is not None else 0,
                      **snapshot(os.getpid())}), flush=True)
    time.sleep(2)  # blocking-sleep: retain allocation for cgroup observation -- DEBT-ESCRITORIO-Y-ARNESES-COMPARTEN-CGROUP  # sunset-reviewed: 2.6 -- el worker acotado retiene la asignación durante la ventana de observación; positivo alcanza 2 s y neutralizado queda debajo. Ver tasks/evidence/CLEAN-2026-10-03/renew-sleeps.txt#RENEW-14-16
    del buf
    print(json.dumps({"phase": "after_release", **snapshot(os.getpid())}), flush=True)
    return 0

def worker(api: str, mib: int) -> int:
    print(json.dumps({"phase": "before", **snapshot(os.getpid())}), flush=True)
    if api in ("cpu_touch", "none"):
        return memory_worker(api, mib)
    if api in ("cuda_malloc", "cuda_malloc_managed"):
        return cuda_worker(api, mib)
    if api == "pytorch_empty":
        return torch_worker(mib)
    raise ValueError(f"unknown API: {api}")

def parse_worker_output(stdout: str, worker_api: str) -> list[str]:
    failures = []
    phases = set()
    for line in stdout.splitlines():
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            failures.append(f"invalid JSON worker output: {line}")
            continue
        if not isinstance(parsed, dict):
            failures.append("worker output must be a JSON object")
            continue
        phase = parsed.get("phase")
        if phase: phases.add(phase)
        if phase == "error": failures.append(parsed.get("error", "worker reported error"))
        for filename, observation in parsed.get("files", {}).items():
            if observation.get("error"):
                failures.append(f"{filename}: {observation['error']}")
    expected = {
        "none": {"before", "held", "after_release"},
        "cpu_touch": {"before", "held", "after_release"},
        "cuda_malloc": {"before", "before_allocation", "held", "after_release"},
        "cuda_malloc_managed": {"before", "before_allocation", "held", "after_release"},
        "pytorch_empty": {"before", "before_allocation", "held", "allocator_cache_released", "after_release"},
    }[worker_api]
    for phase in sorted(expected - phases):
        failures.append(f"missing observation phase: {phase}")
    return sorted(set(failures))

def run_case(api: str, worker_api: str, mib: int) -> dict:
    unit = "bb-cgroup-repro-" + uuid.uuid4().hex[:12]
    child = [sys.executable, __file__, "--worker", worker_api, "--mib", str(mib)]
    cmd = ["systemd-run", "--user", "--scope", "--quiet", "--unit", unit,
           "--property=MemoryMax=512M", "--property=CPUQuota=50%", "--property=RuntimeMaxSec=60s", *child]
    started_ns = time.monotonic_ns()
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=90)
        failures = parse_worker_output(proc.stdout, worker_api)
        if proc.returncode:
            failures.append("systemd-run returned failure")
        result = {"api": api, "worker_api": worker_api, "requested_mib": mib, "unit": unit, "command": cmd,
                  "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr,
                  "could_not_run": sorted(set(failures))}
    except (OSError, subprocess.TimeoutExpired) as exc:
        cleanup_cmd = ["systemctl", "--user", "stop", f"{unit}.scope"]
        try:
            cleanup = subprocess.run(cleanup_cmd, text=True, capture_output=True, timeout=10)
            cleanup_result = {"command": cleanup_cmd, "returncode": cleanup.returncode,
                              "stdout": cleanup.stdout, "stderr": cleanup.stderr}
        except (OSError, subprocess.TimeoutExpired) as cleanup_exc:
            cleanup_result = {"command": cleanup_cmd, "returncode": None, "stdout": "",
                              "stderr": f"{type(cleanup_exc).__name__}: {cleanup_exc}"}
        result = {"api": api, "worker_api": worker_api, "requested_mib": mib, "unit": unit, "command": cmd,
                  "returncode": None, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}",
                  "cleanup": cleanup_result,
                  "could_not_run": [f"systemd-run collection: {type(exc).__name__}: {exc}"] +
                                   (["unit stop failed: " + cleanup_result["stderr"]] if cleanup_result["returncode"] not in (0, 5) else [])}
    result["started_monotonic_ns"] = started_ns
    result["finished_monotonic_ns"] = time.monotonic_ns()
    return result

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=["cpu_touch", "none", "pytorch_empty", "cuda_malloc", "cuda_malloc_managed"])
    parser.add_argument("--mib", type=int, default=32)
    parser.add_argument("--output", type=Path, default=Path("tasks/evidence/FEATURE-1358-CGROUP-01-REPRO/run.json"))
    args = parser.parse_args()
    if args.mib < 1 or args.mib > 32: parser.error("--mib must be between 1 and 32")
    if args.worker: return worker(args.worker, args.mib)
    started_ns = time.monotonic_ns()
    record = {"schema": 1, "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "host": {"uname": platform.uname()._asdict(), "python": sys.version,
              "boot_id": read(Path("/proc/sys/kernel/random/boot_id"))[0], "controllers": read(CGROUP_ROOT / "cgroup.controllers")[0],
              "dmem_capacity": read(CGROUP_ROOT / "dmem.capacity")[0], "nvidia_smi": None,
              "memory_profile": capture_memory_profile()}, "runs": []}
    smi = shutil.which("nvidia-smi")
    host_failures = []
    if smi:
        try:
            p = subprocess.run([smi], text=True, capture_output=True, timeout=10)
            record["host"]["nvidia_smi"] = {"command": [smi], "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
            if p.returncode:
                host_failures.append(f"nvidia-smi returned {p.returncode}: {p.stderr.strip()}")
        except (OSError, subprocess.TimeoutExpired) as exc:
            host_failures.append(f"nvidia-smi collection: {type(exc).__name__}: {exc}")
            record["host"]["nvidia_smi"] = {"command": [smi], "could_not_run": host_failures[-1]}
    else:
        host_failures.append("nvidia-smi executable unavailable")
        record["host"]["nvidia_smi"] = {"command": ["nvidia-smi"], "could_not_run": host_failures[-1]}
    cases = [("none", "none"), ("cpu_touch", "cpu_touch"), ("cuda_malloc", "cuda_malloc"),
             ("cuda_malloc_repeat", "cuda_malloc"), ("cuda_malloc_managed", "cuda_malloc_managed"),
             ("pytorch_empty", "pytorch_empty")]
    for api, worker_api in cases:
        record["runs"].append(run_case(api, worker_api, args.mib))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    record["started_monotonic_ns"] = started_ns
    record["finished_monotonic_ns"] = time.monotonic_ns()
    all_missing = sorted({reason for run in record["runs"] for reason in run["could_not_run"]} | set(host_failures))
    record["could_not_run"] = all_missing
    record["status"] = "partial" if all_missing else "observations_recorded"
    if not record["host"]["dmem_capacity"]:
        record["host"]["dmem_registration"] = "capacity file empty; no regions registered"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"evidence": str(args.output), "runs": len(record["runs"]), "status": record["status"], "could_not_run": all_missing}))
    return 2 if all_missing else 0

if __name__ == "__main__":
    raise SystemExit(main())
