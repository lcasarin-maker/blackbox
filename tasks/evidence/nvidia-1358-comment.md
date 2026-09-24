# Comentario para NVIDIA/open-gpu-kernel-modules#1358

Redactado 2026-09-24. Todos los numeros salen de comandos corridos en esta
maquina; ninguno es estimado. **Lo publica Luis, no el agente.**

URL: https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1358

---

Fourth independent reproduction, on a workload unlike the three already
reported (no vLLM, no hashcat, no NCCL): ordinary CI-style `pytest` fan-out
from coding-agent sessions. Adding it because it widens the trigger surface
further, and because I have two measurements nobody in this thread has taken
yet: a PSI profile of the wedge, and a direct measurement of the cgroup
accounting gap that @reinaertvdc inferred.

## Setup

- DGX Spark (GB10), 121.7 GiB unified memory, Ubuntu 24.04 (DGX OS), aarch64
- `nvidia-driver-580-open` **580.178.04** (newer than the 580.173.02 / 595.84
  already reported here — same signature)
- Kernel **7.0.0-1019-nvidia** (the one @fuomag9 identifies as bad; I also have
  6.17.0-1032-nvidia installed and have not yet switched)
- `nvidia_uvm.uvm_global_oversubscription = 1` (default, not yet changed)
- Secure Boot on, 16 GiB swap

## Three wedges, same signature

| # | window | duration |
|---|---|---|
| 1 | 2026-09-22 05:45 → 23:30 | 1042 min |
| 2 | 2026-09-22 23:49 → 09-23 05:44 | 292 min |
| 3 | 2026-09-24 00:02 → 05:56 | 354 min |

All three required a manual power cycle. The boot that ended in wedge #1 has
**203 occurrences** of

```
NVRM: nvCheckOkFailedNoLog: Check failed: Out of memory [NV_ERR_NO_MEMORY]
(0x00000051) returned from _memdescAllocInternal(pMemDesc) @ mem_desc.c:1359
```

Wedges #2 and #3 have **zero** in their journals — consistent with what this
thread already describes about journald losing the ability to persist: wedge
#3 recorded **1 kernel line in 57 minutes** while journald as a whole still
wrote 684 lines in the same window. The kernel log going quiet is not evidence
the kernel was quiet.

## Trigger

No inference server involved. Two coding-agent sessions running `python -m
pytest` (some with `pytest-xdist`), each worker importing a backend and
initializing CUDA. Per-minute sampling caught the onset of wedge #3:

```
ts          PSI mem_full   mem available   load1   procs with GPU mem
00:00:02          0.0        60.8 GB         4.8            2
00:01:03          0.08       47.5 GB        12.8            4
00:02:03         19.28        3.8 GB        24.9           23   <- 68.5 GB held
00:03:54         92.42       46.0 GB        79.8           14
```

Processes holding GPU memory went **2 → 23 in about 60 seconds**, 22 of them
inside a single desktop-app cgroup scope. This agrees with @reinaertvdc's point
that the trigger does not need a large framework: what it needs is several
processes each initializing CUDA at once.

Note line 4: available memory is back up to **46 GB** while PSI is still at 92.
Freeing memory does not release the stall.

## PSI profile — not reported in this thread so far

Throughout all three wedges, `/proc/pressure/memory`:

```
full avg10 = 98.7 – 99.0, sustained for the entire window
```

`sar` over the same window, wedge #3:

```
%user 0.13   %system 99.42–99.54   %iowait 0.03
ldavg-1 103–110      plist-sz 3211 (vs ~490 on a healthy boot)
kbmemfree 38.3 GiB   kbavail 40.8 GiB   %memused 61.96   %commit 106
swap 100 % used from 00:24 onward, and it stayed full
```

So: 20 cores at 99.5 % **system** time, 0.13 % user, ~38 GB of RAM free, swap
exhausted. This is not RAM exhaustion — it is the reclaim path spinning.

## The cgroup accounting gap, measured

@reinaertvdc wrote that a container `memory.max` did not contain the blast
radius and that "cgroup accounting doesn't seem to see this memory either". I
measured it directly. Same process, so the fixed cost of the CUDA context
cancels out:

```python
import torch, pathlib
cg = pathlib.Path("/sys/fs/cgroup/.../memory.current")
torch.cuda.init()
torch.empty(1, dtype=torch.float16, device="cuda")   # context created
base = int(cg.read_text())
# then allocate 1, then +2, then +4 GiB and re-read
```

Result on this host:

```
torch holds 1 GiB of GPU  ->  cgroup memory.current +1 MiB
torch holds 3 GiB of GPU  ->  cgroup memory.current +6 MiB
torch holds 7 GiB of GPU  ->  cgroup memory.current +15 MiB
```

**7 GiB allocated, 15 MiB charged: 0.2 %.** Driver memory is essentially not
charged to the requesting process's memcg. Any mitigation built on
`memory.max`, `MemoryMax=` or container limits cannot contain this.

## `dmem` is present and unused

This kernel has `CONFIG_CGROUP_DMEM=y`; `dmem` appears in
`/sys/fs/cgroup/cgroup.controllers`, and all six helpers are exported:

```
dmem_cgroup_register_region      EXPORT_SYMBOL_GPL
dmem_cgroup_unregister_region    EXPORT_SYMBOL_GPL
dmem_cgroup_try_charge           EXPORT_SYMBOL_GPL
dmem_cgroup_uncharge             EXPORT_SYMBOL_GPL
dmem_cgroup_state_evict_valuable EXPORT_SYMBOL_GPL
dmem_cgroup_pool_state_put       EXPORT_SYMBOL_GPL
```

`/sys/fs/cgroup/dmem.capacity` is **empty**: no region registered.
`grep -r dmem_cgroup` over the installed driver source (31 MB): **zero hits**.
The driver is `Dual MIT/GPL`, so linking these GPL-only symbols is not a
licensing obstacle.

Registering a region in `nvidia-drm` would at least make the memory visible;
charging it at the allocation site would give operators a real, kernel-enforced
limit and would turn "silent whole-host wedge" into `-ENOMEM` at a point where
userspace can see it — which is what this issue asks for. Filing that as an
observation, not a demand: I understand the allocation path lives in RM, not in
the kernel-interface layer that ships as source in the DKMS package.

## A mitigation that works, and does not depend on the driver

Since neither cgroup limits nor `MemAvailable` can see this condition, but PSI
can, I wired a systemd service-watchdog to PSI instead of to an allocation
probe:

- Probe every 30 s. If `/proc/pressure/memory` `full avg10` stays at or above
  10 % for 300 s, stop calling `sd_notify(WATCHDOG=1)`.
- `WatchdogSec=360`, `FailureAction=reboot-immediate`.

Worst case from onset to reboot: **~11 minutes**, versus 5 h 32 min for the
wedge that prompted it.

Two details that may save someone else time:

1. **An allocation probe does not detect this.** My first version allocated
   64 MiB and touched it every 30 s, on the assumption that during a wedge the
   allocation would not return. It returns in **18–21 ms** while PSI sits at
   99.0 and the box is unusable. That watchdog logged the collapse for five
   hours and never acted.
2. **Level alone is not enough; duration is.** Over 19 696 samples on this host
   there are 7 healthy excursions above 10 %, two of which reached 90.69 % and
   98.53 % for 2 minutes. A level-only trigger would reboot on those. With
   `>= 10 % sustained >= 5 min`, calibration against the three real wedges gives
   0 false positives and 0 missed incidents.

Happy to supply `nvidia-bug-report.log.gz`, the raw per-minute samples, or the
`sar` binaries for any of the three windows.
