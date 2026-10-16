# [PUBLISHED 2026-10-16 as issuecomment-6220079056, edited the same day] [DRAFT C] Comment for NVIDIA/open-gpu-kernel-modules#1358
URL: https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1358

> Status: unpublished draft for Luis. Third comment of lcasarin-maker in this thread (previous: 2026-09-24, 2026-10-02 x2). Short on purpose; the long version is draft A.

Follow-up on the cgroup accounting question from my 09-24 comment, now with a per-class measurement and a correction.

**Correction.** I said CUDA memory is invisible to cgroup accounting. That is true for **device** memory (`cudaMalloc`) and **false for managed and pinned memory** on this stack. Measured 2026-10-16 on a Gigabyte AI TOP ATOM, driver 580.178.04 (with my `memacct` backport loaded), kernel 6.17.0-1032-nvidia, `uvm_disable_hmm=Y`; 12 runs, one systemd user scope each, 256 MiB requests, pages touched, driver API:

| allocation | `dmem.current` | `memory.current` | 2 GiB inside `MemoryMax=1G` |
|---|---|---|---|
| nothing (control) | ~0 | ~0 | n/a |
| device | +256 MiB | ~0 | survives (only `dmem.max` stops it) |
| managed | ~0 | +257 MiB | OOM-killed (exit 137) |
| pinned | ~0 | +257 MiB | OOM-killed (exit 137) |

So `MemoryMax=` / `docker --memory` already bound managed and pinned memory; they do not bound device memory, which is what a vLLM-style workload mostly allocates. Raw captures and a verifier that recomputes the verdict: https://github.com/lcasarin-maker/blackbox/tree/master/tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01

**Allocation path on GB10.** `cudaMalloc` reaches the RM as class `0x3e` (`NV01_MEMORY_SYSTEM`), not as video memory (ioctl sweep). In 615.71.09 the `memacct` charge is in `video_mem.c` according to my reading of the source; **I have not run 615**, so I cannot say whether it covers this path on GB10. Has anyone? If the charge is only in `video_mem.c`, that would leave device memory uncharged on GB10 even with `dmem` registered.

**Limit enforcement (580 backport).** With `dmem.max` = 512 MiB, a 1 GiB `cudaMalloc` is rejected and the process stays usable; with no limit, or a limit that fits, it succeeds. The rejection status (0x8D) is unknown to the 580 `libcuda`, so my first build (measured 2026-10-12) surfaced it as `cudaErrorUnknown`. The patch maps it to `NV_ERR_NO_MEMORY`; with that mapping in the loaded module (measured 2026-10-16, same test) the 1 GiB request under a 512 MiB `dmem.max` fails as an out-of-memory error, the same request with no limit or with a 2 GiB limit succeeds, and `dmem.current` is 0 after the process exits.

**What this is and is not.** It is a containment tool: it can stop one cgroup from taking the whole pool. It does not show that the wedge in this thread has a single cause, and I have no data that a limit prevents the wedge. I plan to observe a cap (engine 40 GiB, everything else 8 GiB, out of a 50.1 GiB region) for a week before enforcing it and will report what the log shows.

**Help wanted.** The patch is public (`data/dmem/memacct-580.patch`, with a README that lists the risks). I would value (1) a review of the refcount and failure paths, (2) a run of `tools/dmem_prueba_completa.sh` on another GB10 unit, (3) a 615 run on GB10. I am not publishing binaries: mine are signed with my own MOK.
