# [DRAFT A] Category: Projects
**Title:** Per-cgroup GPU memory accounting on GB10 with the 580 driver: a `memacct` backport (patch + measurements + limits)

On GB10 with the 580.178.04 open modules, `nvidia-smi` shows no per-process memory (unified memory, confirmed as by-design in thread 367765), and a CUDA allocation is invisible to the cgroup `memory` controller: in my first measurement, holding 7 GiB through PyTorch raised that process's `memory.current` by 15 MiB. So neither `MemoryMax=` nor `docker --memory` contain GPU memory, and no tool I found can say which container holds how much.

The 615.71.09 open release already has the mechanism: `memacct`, which registers a `dmem` region and charges/uncharges allocations. On 580 the root `dmem.capacity` is empty. I ported `memacct` to 580.178.04 and added what GB10 needs.

**What the patch does**
- Registers the `dmem` region (sized without dedicated video memory).
- On GB10 `cudaMalloc` enters RM class `0x3e` (`NV01_MEMORY_SYSTEM`), not `VideoMemory`, so the charge is taken in `sysmemConstruct` and released in `sysmemDestruct`; copy-constructs share the charge by refcount.
- `NV_ERR_RESOURCE_ACCOUNTING_HARD_LIMIT_EXCEEDED` (0x8D) is translated to `NV_ERR_NO_MEMORY`: the 580 libcuda does not know 0x8D and otherwise reports `cudaErrorUnknown`.

**Measured on my unit** (kernel 6.17.0-1032-nvidia, driver 580.178.04, module built from the 580.178.04 tag, signed with my own MOK key)
- Charged: `empty`, `expandable`, `async` and graph allocations (each +~256 MiB for a 256 MiB request, plus the CUDA context).
- Not charged: `cudaHostAlloc` (pinned) and `cudaMallocManaged`. This is a real limit, not a footnote.
- A vLLM container: `dmem.current` = 19483439376 B vs `nvidia-smi` for the same process = 19482542080 B (0.005 % apart).
- Limit enforcement: a cgroup with a 512 MiB `dmem.max` asking for 1 GiB is rejected; the same request with no limit, or with a limit that fits, succeeds; the process stays usable afterwards.
- After the process exits, `dmem.current` returns to 0 (no leak in the cases above).

**Not claimed**: it is not NVIDIA-supported or upstream, I have not tested other GB10 boards or driver versions, and I do not know whether 615+ behaves the same on GB10. Loading a self-built, self-signed module is your risk; Secure Boot needs your own MOK.

Patch, build script, per-cgroup report (`bb gpumem`) and the test script are in https://github.com/lcasarin-maker/blackbox (`data/dmem/memacct-580.patch`, `tools/dmem_reconstruye.sh`, `tools/dmem_prueba_completa.sh`). The ported files keep NVIDIA's MIT headers; see `NOTICE`.

**Questions for NVIDIA**
1. Is `memacct` planned for the 580 branch that DGX OS ships, or only 615+?
2. Should pinned and managed memory be charged on GB10, and is there a reason they are not in 615?
3. Is translating 0x8D to `NV_ERR_NO_MEMORY` acceptable, or would you rather update libcuda to understand it?
