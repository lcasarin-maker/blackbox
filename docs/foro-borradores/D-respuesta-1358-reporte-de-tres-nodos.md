# [PUBLISHED 2026-10-17 as issuecomment-6234458522] [DRAFT D] Reply to Croxatte's 16 October three-node update, NVIDIA/open-gpu-kernel-modules#1358
URL: https://github.com/NVIDIA/open-gpu-kernel-modules/issues/1358 (reply to comment 6229928325)

> Status: unpublished draft for Luis. Fourth comment of lcasarin-maker in this thread. Uses only numbers measured on one unit; nothing from the other nodes is restated as ours.

Thanks for the careful update and for separating the process-level Xid 31 faults from the whole-host freeze signature.

Two things that may save you work.

**1. A free check that needs no patch.** On driver 580 the `dmem` cgroup region does not exist, so `cat /sys/fs/cgroup/dmem.capacity` should print nothing on your nodes. If one of them prints a region, that is a different build than the one I measured and worth saying here. I have not seen it on 580.178.04 without my backport.

**2. If you ever want to reproduce the class measurement.** Raw captures and the 12-run script (driver API, 256 MiB per run, pages touched, one systemd user scope each) are in `tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01/` of https://github.com/lcasarin-maker/blackbox. The script reads `dmem.current`, so it needs the `memacct` region and therefore the backport. The patch applies to 580.173.02 (`git apply --check` rc 0, which is what your nodes run) but I have only **built and run it on 580.178.04**. I do not suggest loading it on a production node, and I agree with your rule that a request is not authorization to patch a running service.

On your question 1: my only data on the `dmem` path for GB10 is the one-unit measurement above (device allocations reach RM class `0x3e`, `NV01_MEMORY_SYSTEM`; I have not run 615).
