# `memacct` backport for NVIDIA open modules 580 (GB10): read this first

**Status: experimental, unsupported, one unit tested.** It makes the NVIDIA 580.178.04 open kernel modules charge GPU memory to the cgroup `dmem` controller on GB10 (DGX Spark / Gigabyte AI TOP ATOM), so `dmem.max` can limit a cgroup and `dmem.current` says who holds what. It is a port of the `memacct` code that NVIDIA publishes in 615.71.09, plus changes GB10 needs. See `NOTICE` for what is NVIDIA's (MIT) and what is not.

## Risks
- **A wrong kernel module can hang the driver, the display and SSH.** Do not load it on a machine you cannot reach physically. Keep a way to boot the stock module (the install script keeps the Canonical modules untouched and rolls back by deleting what it copied).
- **No binaries are published.** The modules the author runs are signed with the author's own MOK key: useless to you and unsafe to trust. Build your own.
- **Secure Boot** needs your own MOK enrolment (a reboot and a console). Nothing here reboots the machine for you.
- **Updates.** The patch applies to 580.178.04 (built and measured) and 580.173.02 (applies, not built); it does **not** apply to 615 (`parche.json`). After a kernel or driver update the module must be rebuilt: `tools/dmem_reconstruye.sh`.
- **Tested on:** one Gigabyte AI TOP ATOM, kernel 6.17.0-1032-nvidia, `uvm_disable_hmm=Y`. Not tested: other units or OEMs, other kernels, HMM enabled, PyTorch, the CUDA runtime API, untouched managed reservations.
- **Known limit:** the charge is taken for allocations that reach RM class `0x3e` (`cudaMalloc`, `expandable_segments`, `cudaMallocAsync`, CUDA graphs). Managed and pinned memory are **not** charged to `dmem`; they are charged to the memory controller, so `memory.max` limits them (measured 2026-10-16, `tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01/`).

## Files
| file | what it is |
|---|---|
| `memacct-580.patch` | the patch (~1400 lines; most of it is NVIDIA's own `memacct` files) |
| `parche.json` | where it applies and where it does not, with the check that was run |
| `../../tools/dmem_reconstruye.sh` | build for your kernel/driver, no root; `--seco` only checks that the patch applies |
| `../../tools/dmem_modulo.sh` | sign (your MOK), install, **roll back** (`retrocede`); never reboots |
| `bb-dmem-guardia.service` (installed by the script) | rolls the module back by itself if the GPU does not answer 120 s after boot |
| `../../tools/dmem_prueba_completa.sh` | one run that measures what is charged, limit enforcement with negative controls, and leaks (root) |
| `../../tools/gpumem.py` (`bb gpumem`) | per-cgroup / per-container GPU memory report |

## Order of use
1. `bash tools/dmem_reconstruye.sh --seco` (does the patch apply to your tag?).
2. Build, sign with your MOK, install: read `tools/dmem_modulo.sh` first; it prints what it will copy and where.
3. Reboot by hand, then `sudo bash tools/dmem_modulo.sh verifica` and `sudo bash tools/dmem_prueba_completa.sh`.
4. Roll back at any time: `sudo bash tools/dmem_modulo.sh retrocede`, then reboot.

## Help wanted
Review of the refcount in the copy-construct path and the release on every failure path; the same test script on another GB10 unit (send the output, failures included); a run of 615 on GB10 to see whether `cudaMalloc` is charged there. Open an issue in this repository.
