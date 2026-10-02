"""Small CUDA full-buffer readback and allocation-reuse check."""
from __future__ import annotations

import argparse
import concurrent.futures
import ctypes as C
import ctypes.util
import json
import shutil
import subprocess
import sys
import time
import uuid

MAX_WORKERS = 4
MAX_WORKER_BYTES = 4 * 1024 * 1024
ROUNDS = 4


def check(rc: int, operation: str) -> None:
    if rc:
        raise RuntimeError(f"{operation} returned CUDA error {rc}")


def verify_bytes(actual: bytes, expected: bytes) -> None:
    if actual != expected:
        mismatch = next((i for i, (left, right) in enumerate(zip(actual, expected))
                         if left != right), min(len(actual), len(expected)))
        raise ValueError(f"readback mismatch at byte {mismatch}: got {len(actual)} bytes, "
                         f"expected {len(expected)}")


def allocate_slot(lib, slots, size: int, value: int, label: str) -> None:
    ptr = C.c_void_p()
    check(lib.cudaMalloc(C.byref(ptr), size), f"cudaMalloc {label}")
    address = ptr.value
    if address is None:
        raise RuntimeError(f"cudaMalloc {label} returned a null pointer")
    if address in slots:
        raise RuntimeError(f"cudaMalloc {label} returned an already live pointer {address}")
    slots[address] = (ptr, size, value)
    check(lib.cudaMemset(ptr, value, size), f"cudaMemset {label}")


def verify_slots(slots, host, copy, sync, label: str) -> None:
    for ptr, size, value in slots.values():
        check(copy(host, ptr, size, 2), f"cudaMemcpy device-to-host {label}")
        check(sync(), f"cudaDeviceSynchronize {label}")
        verify_bytes(C.string_at(host, size), bytes([value]) * size)


def release_slots(slots, keys, free, label: str) -> None:
    for ptr_key in keys:
        ptr, _, _ = slots.pop(ptr_key)
        try:
            check(free(ptr), f"cudaFree {label}")
        except Exception as exc:
            exc.add_note(f"allocation {ptr_key} has uncertain device state; cleanup will not retry it")
            raise


def cleanup_slots(slots, free, sync) -> list[str]:
    errors = []
    for ptr_key, (ptr, _, _) in list(slots.items()):
        try:
            check(free(ptr), "cudaFree cleanup")
        except Exception as exc:
            errors.append(f"pointer {ptr_key}: {exc}")
        finally:
            # A failed free has uncertain device state; never risk a double-free.
            del slots[ptr_key]
    try:
        check(sync(), "cudaDeviceSynchronize cleanup")
    except Exception as exc:
        errors.append(str(exc))
    return errors


def configure(lib: C.CDLL) -> None:
    alloc = lib.cudaMalloc
    alloc.argtypes = [C.POINTER(C.c_void_p), C.c_size_t]
    alloc.restype = C.c_int
    free = lib.cudaFree
    free.argtypes = [C.c_void_p]
    free.restype = C.c_int
    memset = lib.cudaMemset
    memset.argtypes = [C.c_void_p, C.c_int, C.c_size_t]
    memset.restype = C.c_int
    copy = lib.cudaMemcpy
    copy.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t, C.c_int]
    copy.restype = C.c_int
    sync = lib.cudaDeviceSynchronize
    sync.argtypes = []
    sync.restype = C.c_int


def run_worker(lib: C.CDLL, index: int, rounds: int, worker_bytes: int) -> int:
    alloc = lib.cudaMalloc
    free = lib.cudaFree
    memset = lib.cudaMemset
    copy = lib.cudaMemcpy
    sync = lib.cudaDeviceSynchronize
    # Each worker owns four 1 MiB allocations: 16 MiB maximum in aggregate.
    slots: dict[int, tuple[C.c_void_p, int, int]] = {}
    host = C.create_string_buffer(worker_bytes)
    made = 0
    primary_error: BaseException | None = None
    try:
        for round_index in range(rounds):
            for slot_index in range(4):
                size = worker_bytes // 4
                value = (index * 37 + round_index * 19 + slot_index + 1) % 255
                allocate_slot(lib, slots, size, value, "initial allocation")
            check(sync(), "cudaDeviceSynchronize before readback")
            verify_slots(slots, host, copy, sync, "before reuse")
            # Leave alternating allocations live while freed slots are reused.
            release_slots(slots, list(slots)[::2], free, "hole")
            for slot_index in (0, 2):
                value = (index * 41 + round_index * 23 + slot_index + 7) % 255
                allocate_slot(lib, slots, worker_bytes // 4, value, "hole reuse")
            check(sync(), "cudaDeviceSynchronize after hole reuse")
            # Read every live slot again so writes into reused holes cannot alias survivors.
            verify_slots(slots, host, copy, sync, "after reuse")
            release_slots(slots, list(slots), free, "round release")
            check(sync(), "cudaDeviceSynchronize after release")
            made += 6
    except BaseException as exc:
        primary_error = exc
        raise
    finally:
        cleanup_errors = cleanup_slots(slots, free, sync)
        if cleanup_errors:
            message = "CUDA cleanup failures: " + "; ".join(cleanup_errors)
            if primary_error is None:
                raise RuntimeError(message)
            primary_error.add_note(message)
    return made


def run(rounds: int = ROUNDS, workers: int = MAX_WORKERS,
        worker_bytes: int = MAX_WORKER_BYTES) -> dict[str, object]:
    if not 1 <= workers <= MAX_WORKERS:
        raise ValueError(f"workers must be between 1 and {MAX_WORKERS}")
    if not 1 <= rounds <= ROUNDS:
        raise ValueError(f"rounds must be between 1 and {ROUNDS}")
    if worker_bytes != MAX_WORKER_BYTES:
        raise ValueError(f"worker_bytes must equal {MAX_WORKER_BYTES}")
    libname = ctypes.util.find_library("cudart")
    if not libname:
        return {"status": "could_not_run", "reason": "libcudart unavailable"}
    lib = C.CDLL(libname)
    lib.cudaGetDeviceCount.argtypes = [C.POINTER(C.c_int)]
    lib.cudaGetDeviceCount.restype = C.c_int
    device_count = C.c_int()
    rc = lib.cudaGetDeviceCount(C.byref(device_count))
    if rc or not device_count.value:
        return {"status": "could_not_run", "reason": "no usable CUDA device",
                "cuda_error": rc, "device_count": device_count.value}
    configure(lib)
    start = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_worker, lib, index, rounds, worker_bytes)
                   for index in range(workers)]
        allocations = sum(future.result(timeout=30) for future in futures)
    return {"status": "pass", "library": libname, "workers": workers,
            "max_aggregate_allocation_bytes": workers * worker_bytes,
            "rounds_per_worker": rounds, "allocations": allocations,
            "full_buffer_readback": True, "release_between_rounds": True,
            "seconds": time.monotonic() - start}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--rounds", type=int, default=ROUNDS)
    parser.add_argument("--_bounded-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args._bounded_worker:
        systemd_run = shutil.which("systemd-run")
        if not systemd_run:
            result = {"status": "could_not_run", "reason": "systemd-run unavailable"}
            print(json.dumps(result, sort_keys=True))
            return 2
        unit = "bb-cuda-integrity-" + uuid.uuid4().hex[:12]
        command = [systemd_run, "--user", "--scope", "--quiet", "--unit", unit,
                   "--property=MemoryMax=512M", "--property=CPUQuota=50%",
                   "--property=RuntimeMaxSec=60s", sys.executable, __file__,
                   "--_bounded-worker", "--workers", str(args.workers),
                   "--rounds", str(args.rounds)]
        try:
            proc = subprocess.run(command, text=True, capture_output=True, timeout=75, check=False)
            if proc.stdout.strip():
                print(proc.stdout.strip().splitlines()[-1])
            else:
                print(json.dumps({"status": "could_not_run", "command": command,
                                  "returncode": proc.returncode, "stderr": proc.stderr.strip()}))
            return proc.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            try:
                subprocess.run(["systemctl", "--user", "stop", f"{unit}.scope"],
                               text=True, capture_output=True, timeout=10, check=False)
            except (OSError, subprocess.TimeoutExpired):
                pass
            print(json.dumps({"status": "could_not_run", "command": command,
                              "error": f"{type(exc).__name__}: {exc}"}))
            return 2
    try:
        result = run(args.rounds, args.workers)
    except Exception as exc:
        result = {"status": "fail", "error": f"{type(exc).__name__}: {exc}",
                  "notes": getattr(exc, "__notes__", [])}
    print(json.dumps(result, sort_keys=True))
    if result["status"] == "pass":
        return 0
    return 2 if result["status"] == "could_not_run" else 1


if __name__ == "__main__":
    raise SystemExit(main())
