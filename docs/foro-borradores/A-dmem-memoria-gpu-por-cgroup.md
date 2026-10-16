# [PUBLISHED as topic 386057 (edited 2026-10-16 with the measured rejection type)] [DRAFT A v2.2] Category: Projects
**Title:** Per-cgroup GPU memory limits on GB10 (580 driver): a `memacct` backport, which cgroup pays for which CUDA allocation, and a request for review

> Status: unpublished draft for Luis. Replaces the 2026-10-13 version. Every number comes from a command run on one unit; raw captures and the verifier are in the repo.

**The problem.** On GB10 with the 580.178.04 open modules, `nvidia-smi` reports `Memory-Usage: Not Supported` for the GPU as a whole (NVIDIA's DGX Spark known-issues page calls this expected on iGPUs; thread 367765 discusses it) and gives nothing per cgroup or per container, and, in my first measurement, holding 7 GiB through PyTorch raised that process's `memory.current` by 15 MiB. So `MemoryMax=` and `docker --memory` do not contain `cudaMalloc` memory, and nothing I found says which container holds how much. When the pool is exhausted the whole host stalls (issue #1358 and the threads linked there), so a per-cgroup limit on GPU memory is a containment tool, not a nicety.

**What exists upstream.** 615.71.09 has `memacct`: it registers a `dmem` region and charges allocations. 580 does not (root `dmem.capacity` is empty). I ported it to 580.178.04 and added what GB10 needs. I have **not** run 615 on GB10, so I cannot say whether its hook catches GB10 allocations (see the question below).

## What the patch does
- Registers the `dmem` region (sized without dedicated video memory).
- On GB10 `cudaMalloc` enters RM class `0x3e` (`NV01_MEMORY_SYSTEM`), not `VideoMemory` (ioctl sweep of the user-space calls). `video_mem.c`, where 615 charges, is not on that path, so the charge is taken in `sysmemConstruct` and released in `sysmemDestruct`; copy-constructs share the charge by refcount.
- `NV_ERR_RESOURCE_ACCOUNTING_HARD_LIMIT_EXCEEDED` (0x8D) is translated to `NV_ERR_NO_MEMORY`, because the 580 `libcuda` does not know 0x8D and otherwise reports `cudaErrorUnknown`. **Measured on the loaded module (2026-10-16): with `dmem.max` = 512 MiB, a 1 GiB `cudaMalloc` fails as an out-of-memory error, not `cudaErrorUnknown`; the same request with no limit, or with a 2 GiB limit, succeeds; `dmem.current` is back to 0 after the process exits. My first build, measured on 2026-10-12, still returned `cudaErrorUnknown`.**

## Which cgroup pays for what (measured 2026-10-16)
12 runs, each in its own systemd user scope; driver API (`cuMemAlloc`, `cuMemAllocManaged`, `cuMemHostAlloc`); pages touched. Control row "nothing" reads ~0, so the instrument sees zero.

| allocation | delta of `dmem.current` | delta of `memory.current` | asking 2 GiB inside `MemoryMax=1G` |
|---|---|---|---|
| nothing (control) | ~0 | ~0 | n/a |
| device (`cuMemAlloc`) | +256 MiB | ~0 | survives: `memory.max` does not stop it; `dmem.max` does |
| managed (`cuMemAllocManaged`) | ~0 | +257 MiB | killed (exit 137, `oom-kill` in the journal) |
| pinned (`cuMemHostAlloc`) | ~0 | +257 MiB | killed (exit 137, `oom-kill` in the journal) |

So the answer to "cgroups do not see CUDA memory" is: true for device memory, false for managed and pinned on this stack. Each class has its own limit: `dmem.max` for device, `memory.max` for managed and pinned. A 512 MiB managed allocation under the same `MemoryMax=1G` succeeds.

Other measurements: a vLLM container shows `dmem.current` = 19483439376 B against 19482542080 B from `nvidia-smi` for the same process (0.005 % apart). With `dmem.max` = 512 MiB, a 1 GiB request is rejected; the same request with no limit, or with a limit that fits, succeeds, and the process stays usable. After exit `dmem.current` returns to 0 (no leak in the cases above).

## Warnings (read before loading anything)
- This is **not** NVIDIA-supported. A wrong kernel module can hang the driver, the display and SSH. Do not load it on a machine you cannot reach physically.
- **I am not publishing binaries.** The modules I run are signed with my own MOK key, so they are useless to you and unsafe to trust. Build from the 580.178.04 tag yourself: `tools/dmem_reconstruye.sh --seco` first (checks the patch applies, builds nothing).
- Secure Boot needs your own MOK enrolment. The install script **does not reboot** and does not unload running modules.
- Rollback exists and is tested in a scratch directory, not yet in a real failed boot: `bb-dmem-guardia.service` rolls back by itself if the GPU does not answer within 120 s after boot; manually `sudo bash tools/dmem_modulo.sh retrocede`.
- It applies to 580.178.04 and 580.173.02. It does **not** apply to 615 (already has its own).
- Measured only on one Gigabyte AI TOP ATOM, kernel 6.17.0-1032-nvidia, `uvm_disable_hmm=Y`. Untested: other OEM units, other kernels, HMM enabled, PyTorch and the CUDA runtime API (I used the driver API), untouched managed reservations.

## What I would like help with
1. **Read the patch** (`data/dmem/memacct-580.patch`, ~1400 lines, mostly NVIDIA's own `memacct` files): the refcount in the copy-construct path and the release on every failure path are the parts I trust least.
2. **Run `tools/dmem_prueba_completa.sh` on another GB10 unit** and send the output, including failures.
3. **Run 615 on GB10** and check whether `cudaMalloc` is charged. If it is not, the hook in `video_mem.c` misses the GB10 path.
4. Tell me which allocation classes I did not measure.

Patch, build script, per-cgroup report (`bb gpumem`), the capture and its verifier: https://github.com/lcasarin-maker/blackbox (`data/dmem/`, `tools/dmem_reconstruye.sh`, `tools/dmem_prueba_completa.sh`, `tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01/`). The ported files keep NVIDIA's MIT headers; see `NOTICE`.

## Questions for NVIDIA
1. Is `memacct` planned for the 580 branch that DGX OS ships, or only 615+?
2. In 615, is the GB10 path (`NV01_MEMORY_SYSTEM`, class `0x3e`) charged? From reading the 615.71.09 source I believe the charge is only in `video_mem.c`; I have not run it.
3. Is translating 0x8D to `NV_ERR_NO_MEMORY` acceptable, or would you rather update `libcuda` to understand it?
