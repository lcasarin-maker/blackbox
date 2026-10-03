# DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01

## Root cause

The prior `memory_profile` captured the running kernel and NVIDIA UVM module identity, but omitted the effective DGX OTA release, the loaded base NVIDIA driver versus its on-disk module version, `MemAvailable`, and memory PSI. Those observations now come from the current host through read-only proc/sysfs and bounded `modinfo` queries. The comparison reports unknown when either side is unavailable or unparsable.

## Regression test

`python3 -m pytest -q tests/test_memory_capture_and_cuda_integrity.py`

Literal result: `32 passed in 0.11s` (exit 0). Positive coverage exercises consistent loaded/on-disk driver versions and complete memory records. Negative coverage exercises a loaded/on-disk version mismatch, malformed `MemAvailable`, and successful reads with non-text values.

## Verification evidence

**pass:** `python3 -m tools.memory_profile` exited 0 on the current local host. The captured tuple is DGX Spark / AI TOP ATOM, DGX software build 7.2.3 with OTA 7.6.0, kernel `6.17.0-1032-nvidia`, loaded and disk NVIDIA driver `580.178.04` (match), loaded and disk UVM versions match, and `MemAvailable` was 47,709,648 kB at capture. The evidence summary omits serial number, boot UUID and full memory map.

**fail:** The test's altered disk-driver version produces `driver_comparison.match=false`; malformed meminfo produces `memavailable.status=collection_failed`. A preceding read-only general diagnostics capture could not communicate with the NVIDIA driver using `nvidia-smi` in this execution context (return 9), so this evidence does not certify a CUDA workload.

**e2e:** This host observation does not validate the DGX OEM-supported OTA/kernel/driver tuple, firmware/carveout adoption, a post-update workload, recovery boot, or OEM rollback. No package, module, firmware, OTA, reboot, or security setting was changed. The literal close-check selector was run before implementation and failed with pytest `not found` (exit 4); it remains a pending specification and this task stays open.

**Static and schema checks:** Pyright on `tools/memory_profile.py` and `tests/test_memory_capture_and_cuda_integrity.py`: `0 errors, 0 warnings, 0 informations`. Ruff: `All checks passed!`. Ledger schema: `checked=282 passed=282 failed=0 unverified=0 ... avisos=80 could_not_run=0`; the 80 advisories remain printed and are not reported as a clean project-wide result.
