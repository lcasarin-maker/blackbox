Thanks, Zeke. This replaces the plan I had a week ago: I have since booted 7.0.0-1025 on this unit, so I can answer with data instead of caution. Your list in order, then what is new.

**What is new since my last post (all from my own boot ledger and kernel journal, unit on driver 580.178.04, packaged module):**

| Boot (id) | Kernel | Duration | Ended | Hard cut? |
|---|---|---|---|---|
| dd28a981 | 6.17.0-1032 | 3.08 d | ordered reboot (2026-11-09 15:30) | no |
| ad826111 | 6.17.0-1032 | 21 min | `grub-reboot` I ran to try 1025 | no |
| 0acf5c1e | **7.0.0-1025** | **3 h 28 min** | `sudo reboot` I ran (19:20) | no |
| 316ca4f0 | 6.17.0-1032 | 1 h 58 min | **GSP Xid 119 at +10 s, GPU in reset-required for 2 h, then silent cut at 21:20, BERT present** | **yes** |
| 21836d3b | 6.17.0-1032 | 54 s | Xid 119 again at +14 s; ordered power-off (21:22) | no |
| 71503798 | 6.17.0-1032 | 5.99 d | ordered reboot (2026-11-15 21:27) | no |
| 6d1d5b71 | 6.17.0-1032 | running, about 24 h | n/a | n/a |

1. **7.0.0-1025 booted on 2026-11-09 (15:53 to 19:21) and showed none of the faults reported for 1024.** The kernel journal of that boot has zero Xid, Oops, soft lockup, BUG, or list-corruption lines. It was not idle: vLLM was running, GPU utilization reached 96% (2388 of 2455 telemetry samples above 50%), peak GPU temperature was 68 C. Same `nvidia.ko` srcversion as 6.17 (B9F87D2C66AEAE721A6DFF6, 580.178.04, packaged, no local patch). Command line of that boot included `initcall_blacklist=tegra234_cbb_init,power_wrap_init kho=off iommu.passthrough=0 init_on_alloc=0 panic=30`. So `power_wrap_init` was already blacklisted on this unit, which may matter for the 1025 reports (thread 388215) that did not have it. This is one 3.5 hour boot, not a long soak, and I do not claim 1025 is safe: the oops reports in that thread may come from a different workload or unit, and I cannot tell which.
2. **A GSP timeout on 6.17.0-1032, right after warm-rebooting back from 7.0.0-1025, and a hard cut two hours later.** This is the data you asked for under "hard cuts". The first 6.17 boot after the 1025 test (boot 316ca4f0, 19:21:57, packaged module, GPU at PCI:000f:01:00) logged this **10 seconds after boot**, with Xorg as the client:

```
19:22:07 kernel: NVRM: _kgspLogXid119: ***** GSP Timeout *****
19:22:07 kernel: NVRM: Xid (PCI:000f:01:00): 119, pid=4069, name=Xorg, Timeout after 6s of waiting for RPC response from GPU0 GSP! Expected function 76 (GSP_RM_CONTROL) sequence 461 (0x7302a6 0xc).
19:22:07 kernel: NVRM:     task watchdog timeout @ pc:0x1af90e2, partition:4#0, task:3
19:22:07 kernel: NVRM:     Reported by libos partition:4#5 kernel v3.1 [0] @ ts:53
```

After that the GPU never recovered in that boot. The journal holds 13,884 `nvAssertFailedNoLog ... (status == NV_OK) || (status == NV_ERR_GPU_IN_FULLCHIP_RESET)` lines and 2,884 `NV_ERR_RESET_REQUIRED` lines (plus `nvidia-modeset: Failed to query display engine channel state` repeating, and USB `device descriptor read/64, error -32`). The machine stayed reachable for 1 h 58 min and then cut hard at 21:20:18 (netconsole and journal both end there). The last kernel lines before the cut, from the netconsole stream:

```
21:20:14 kernel: NVRM: nvAssertFailedNoLog: Assertion failed: (status == NV_OK) || (status == NV_ERR_GPU_IN_FULLCHIP_RESET) @ rs_server.c:259
21:20:18 kernel: NVRM: nvAssertFailedNoLog: Assertion failed: rmStatus == NV_OK @ kern_disp.c:311
21:20:18 kernel: NVRM: nvCheckOkFailedNoLog: Check failed: Reset required [NV_ERR_RESET_REQUIRED] (0x00000062) returned from pRmApi->Control(... NV2080_CTRL_CMD_INTERNAL_I...
```

The unit was back up at 21:22:05. That boot hit the **same** Xid 119 at 21:22:19 (14 s after boot, `pid=4024 Xorg`, function 76, sequence 460) and was powered off at 21:22:50 (ordered, via logind). After that full power-off the next boot (21:47) ran **5.99 days** with no Xid and ended in an ordered reboot, and the current one has run about 24 h. So on this unit, twice in a row, a warm reboot left the GSP in a failed state and only a power-off cleared it. It started on the 6.17 side, after a 7.0 boot; I have not tested whether a warm reboot 6.17 to 6.17 is affected (the earlier 15:30 warm reboot 6.17 to 6.17 was clean, boot ad826111). Two instances, not a statistic. My ledger had classified the 21:20 cut as undetermined with "PSI 0"; that classification missed that the GPU had been failing for two hours before it.

3. **Patched module data point (relevant to open-gpu-kernel-modules#1358, where I suggested a dmem backport).** On 2026-10-30, on **7.0.0-1024**, a locally built `nvidia.ko` with that dmem/memacct backport gave **four hard cuts in 25 minutes** (8 min, 2 min 13 s, 1 min 43 s, 1 min 55 s; the fourth coincided with a forced stop of a 40 GB container on my side, so it is not independent evidence). The packaged module on the same kernel ran 1 h 50 min under the same vLLM load. This is correlation from one boot of the packaged module, not a proof that the patch is the cause (firmware SOCFW/EC/USBPD below OTA2610 is a standing candidate). I am running **no patch today**: packaged module only.

**Your list:**

**1. Packages.** Nothing upgradable; installed kernels 6.17.0-1032 (running, held), 7.0.0-1024, 7.0.0-1025. GRUB default is 6.17.0-1032, held on purpose with `dgx-spark-ota-update-meta`.

**2. OTA / firmware.** `nvidia-spark-ota-check summary` (2026-11-06): detected OTA2607; against OTA2610, 147 of 155 pass; failing: `nvidia-mlnx-tools`, `nvidia-system-station-apps`, `nvidia-system-station-games`, `kernel` (held on purpose), `SOCFW`, `EC`, `EC Unfused`, `USBPD`. I have still not tried to raise SOCFW/EC/USBPD to OTA2610. `dmidecode -t 45` (thread 386060): BIOS 5.36_0ACUM08 (07/02/2026), EC 3.5.11, PD0/PD1 FW1, FLASH SBP:R:2.155.14, UEFI OEM_UEFI_0.0.8.

**3. nvidia-bug-report.** On the 7.0.0-1024 loop boots it never ran: most of them lasted under a minute. On the 1025 boot there was no Xid at all, so there was nothing to capture; the Xid I did see afterwards on 6.17 was 119 (GSP Timeout), not 154, and I have no bug report from that boot. I will run it on the next Xid 154 boot that stays up.

**4. Which nvidia.ko.** 6.17.0-1032 and 7.0.0-1025 both loaded the packaged module, srcversion B9F87D2C66AEAE721A6DFF6. For the 1024 loop boots (2026-11-02/03) I did not record the module; my recorder logs it per boot only since 2026-11-03.

**5. netconsole.** Running (UDP 6666 to a separate PC, one line per datagram, fsync). For the 2026-11-03 08:50 cut the stream shows no Xid, Oops, panic, hung task or thermal line before it stops; the only non-routine output was a cgroup OOM kill of a 64 MB `python3` three minutes earlier. That fits a reset from below the kernel but does not prove one. The BERT record of that cut has word `0x00000020`, which I cannot interpret; your team's reading would help.

**6. Same-allocator data point.** On 2026-11-05 19:58 on 6.17.0-1032 the kernel logged `NVRM: nvCheckOkFailedNoLog: Check failed: Out of memory [NV_ERR_NO_MEMORY] (0x00000051) ... mem_desc.c:1359` and available memory fell from about 42 GB to under 6% in seconds. The host did not wedge; the userspace OOM killer reacted and memory recovered in about a minute. Same error as #1358, different outcome.

**Question for NVIDIA, still open:** does anything in 1025 beyond the one `ipv4: free inet_opt and ireq_opt after an RCU grace period` change touch the GSP RPC timeout / Xid 154 path? My 1025 boot did not reproduce the 1024 faults under vLLM load in 3.5 hours, but the first warm reboot out of it hit Xid 119 (item 2 above), so I cannot separate a real fix from a workload difference or from reboot-path state.

Everything (boot ledger, recovery command `sudo panic`, per-boot module recorder) is in the open-source repo: https://github.com/lcasarin-maker/blackbox. I am a lawyer, not an engineer, so corrections are welcome.
