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
- Kernel: wedges 1-4 all happened on **7.0.0-1019-nvidia** (the one @fuomag9
  identifies as bad). Since 2026-09-24 14:11 this host runs
  **6.17.0-1032-nvidia** with `nvidia_uvm.uvm_global_oversubscription = 0`;
  no wedge yet, but that is only hours of uptime and I am not claiming it as
  a fix.
- Secure Boot on, 16 GiB swap

## Four wedges, same signature

| # | window | duration | ended by |
|---|---|---|---|
| 1 | 2026-09-22 05:45 → 23:30 | 1042 min | manual power cycle |
| 2 | 2026-09-22 23:49 → 09-23 05:44 | 292 min | manual power cycle |
| 3 | 2026-09-24 00:02 → 05:56 | 354 min | manual power cycle |
| 4 | 2026-09-24 13:59 → 14:09 | **10.6 min** | **PSI watchdog, automatic** |

The first three required a manual power cycle. The fourth is described at the
end of this comment: same failure, but the host recovered on its own. The boot that ended in wedge #1 has
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

Worst case from onset to reboot: ~11 minutes, versus 5 h 32 min for the wedge
that prompted it.

**It fired for real on 2026-09-24, and the predicted number held.** Wedge #4,
same host, same kernel 7.0.0-1019, before the kernel/regkey change:

```
13:58:04  PSI mem_full 0.0    58.0 GB available   load  4.64   3 GPU procs
13:59:05  PSI mem_full 0.04   36.9 GB available   load 24.9    3 GPU procs
13:59:34  [bb-usable] PSI 12.1 >= 10 -- streak 1/10
14:00:04  [bb-usable] PSI 92.8 >= 10 -- streak 2/10
14:06:04  [bb-usable] COLLAPSE: sustained 300s -- withholding the watchdog ping
14:09:34  systemd: bb-usable.service: Watchdog timeout (limit 6min)!
14:09:38  systemd: Failed with result 'watchdog' -> Rebooting.
```

Onset 13:59:04 to automatic reboot 14:09:38: **10.6 minutes, no human
involved.** The operator was on another continent at the time; wedges 1-3 had
each required someone physically present.

Worth noting for anyone reproducing: this fourth one had only **3** processes
holding GPU memory, not the 22 of wedge #3, and 21 GB of availability vanished
in a single 60-second sampling interval. Per-minute sampling was not enough
resolution to attribute it. So the trigger surface is wider than "many CUDA
processes at once" — which is consistent with @reinaertvdc reproducing it from
`hashcat -I`.

This does not fix anything. The allocation still fails, the host still becomes
unusable, and a reboot still loses whatever was running. It only bounds the
outage, and it does so from outside the driver, using the one signal that both
reflects the condition and is available to userspace.

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

## The allocation path, read from the shipped source — and a regkey that targets it

`_memdescAllocInternal` is inside `nv-kernel.o_binary` and not patchable
locally, but the path it ends in **is** shipped as source, in
`nvidia/os-interface.c::os_alloc_pages_node()`:

```c
gfp_mask = __GFP_THISNODE | GFP_HIGHUSER_MOVABLE | __GFP_COMP | __GFP_NOWARN;

#if defined(__GFP_RETRY_MAYFAIL)
    /*
     * __GFP_RETRY_MAYFAIL :  Used to avoid the Linux kernel OOM killer.
     *                        To help PMA on paths where UVM might be
     *                        in memory over subscription. ...
     */
    gfp_mask |= __GFP_RETRY_MAYFAIL;
#endif

#if defined(__GFP_RECLAIM)
    if (flag & NV_ALLOC_PAGES_NODE_SKIP_RECLAIM)
        gfp_mask &= ~(__GFP_RECLAIM);
#endif

    alloc_addr = alloc_pages_node(nid, gfp_mask, order);
```

`__GFP_RETRY_MAYFAIL` asks the kernel to retry reclaim hard **and to not invoke
the OOM killer**. On a unified-memory part where the "GPU" allocation is system
memory and the request is tens of GiB, that is a very good description of what
we measured: 99.5 % system time, swap driven to 100 %, no OOM kill ever, and
tens of GiB nominally free the whole time. The intent (don't let the OOM killer
shoot the user's processes) is reasonable; the outcome on GB10 is that nothing
stops it either.

The `SKIP_RECLAIM` branch is the escape, and it is driven by a registry key.
Disassembling `pmaNumaAllocate` in the blob, the flag is computed as:

```
ldr  w1, [x27, #712]     ; RmNumaAllocSkipReclaimPercent
ldr  x3, [x27, #608]     ; total
ldr  x0, [x27, #616]     ; free
mul  x1, x1, x3
lsl  x1, x1, #5
cmp  x1, x2, lsl #2      ; (pct * total * 32) vs (100 * free)
cset w19, hi             ; -> NV_ALLOC_PAGES_NODE_SKIP_RECLAIM
```

i.e. **skip reclaim once free memory drops below `RmNumaAllocSkipReclaimPercent`
of the pool**, and then `alloc_pages_node` fails fast and RM returns
`NV_ERR_NO_MEMORY` — which is exactly the clean failure this issue is asking
for, and exactly the error we see 203 of in the wedge-1 journal. So the good
path exists; on this hardware it appears to engage too late, or not at all,
before the reclaim spin has already taken the host.

On this host `/proc/driver/nvidia/params` shows `RegistryDwords: ""` and
`EnableUserNUMAManagement: 1` — no regkey set, stock behaviour.

**Questions for NVIDIA, which is why I am reporting this rather than just
tuning it:**

1. What is the default of `RmNumaAllocSkipReclaimPercent` on GB10, and is it
   intended to be tuned on unified-memory parts?
2. Is `__GFP_RETRY_MAYFAIL` the right choice when the NUMA node being
   allocated from is the *only* system memory? Avoiding the OOM killer there
   means there is no backstop at all.
3. Would a `dmem` region registration (the controller is present and its six
   helpers are `EXPORT_SYMBOL_GPL`; the driver is Dual MIT/GPL) be considered?
   It would give operators a supported ceiling instead of leaving them to
   discover that `memory.max` does not apply.

I have not tuned the regkey here yet, because reproducing takes a wedge and a
power cycle per iteration, and I would rather have the intended default from
you than guess at it.

Happy to supply `nvidia-bug-report.log.gz`, the raw per-minute samples, or the
`sar` binaries for any of the three windows.
