# Follow-up for NVIDIA #1358 — 2026-10-02

Draft for Luis to publish. Journal and current service state checked on 2026-10-02. Historical excerpts below retain their original local timezone (UTC−06:00).

---

Follow-up to my earlier report: one observed automatic recovery from the sustained-PSI failure, and a clarification of the mitigation's scope.

These measurements come from [blackbox](https://github.com/lcasarin-maker/blackbox), our open-source forensic recorder for a GB10 host. It continuously records host samples, correlates them with existing journals and GPU telemetry, and makes unavailable checks explicit. It also includes a sustained-memory-PSI service watchdog to recover from the failure mode described below. The purpose is to preserve evidence for diagnosis after an incident and expose gaps in instrumentation before the next one.

We welcome collaboration from other GB10 operators: incident captures with memory PSI, reproductions on different kernels/drivers/OEM units, and review of our watchdog and diagnostic assumptions. Fast silent prefill failures are especially useful to compare against our sustained-PSI incidents. Please redact identifying data before sharing logs; contradictory results are valuable too.

On 2026-09-24, our fourth incident ended through the systemd **service watchdog** rather than a manual power cycle. This is distinct from PID 1's SBSA hardware watchdog: `bb-usable` probes memory PSI every 30 seconds, withholds `sd_notify(WATCHDOG=1)` after `memory full avg10 >= 10` persists for 300 seconds, and the unit uses `WatchdogSec=360` plus `FailureAction=reboot-immediate`.

Rechecked against the persistent journal today (times UTC−06:00):

```text
13:59:34  PSI memory full avg10=12.1 — first sample in the sustained streak
14:04:04  COLAPSO: PSI memory full avg10=98.0 sustained 300s — watchdog heartbeat withheld
14:09:34  systemd: bb-usable.service: Watchdog timeout (limit 6min)!
14:09:38  systemd: bb-usable.service: Failed with result 'watchdog'.
14:11:37  next boot begins (journalctl --list-boots)
14:11:52  systemd: Started bb-usable.service
```

The final watchdog failure occurred 10 min 4 s after the first above-threshold service sample; the next boot began 12 min 3 s after that sample. These are distinct timings: watchdog action and restored boot. The 30-second probe cadence also means the first sample is not the exact physical onset.

This demonstrates automatic recovery in **one incident** of our sustained-PSI failure mode. It does not establish coverage of the fast, silent long-prefill failures reported here, and it still terminates the running workload.

The earlier allocation probe alone was insufficient: it continued to allocate and touch 64 MiB in 18–21 ms while memory PSI stayed around 99% and the host was unusable. Sustained PSI supplied the discriminator in our incidents. Other reporters' planned PSI captures should help determine whether their failure shares that mechanism.

Our direct cgroup measurement remains relevant: allocating 7 GiB through CUDA increased the same process's `memory.current` by only 15 MiB. Ordinary `MemoryMax` limits therefore leave this allocation outside their effective containment on our tested stack.

I also want to narrow our interpretation: disabling `uvm_global_oversubscription` is a partial mitigation, not an established root cause or universal fix. The prefill counterexamples in this thread make that distinction clear. Likewise, our high-PSI/high-system-CPU observations support investigating reclaim, but do not prove a common cause for every failure collected here.

Current read-only check on our host: kernel `6.17.0-1032-nvidia`, driver `580.178.04`, `uvm_global_oversubscription=0`; `bb-usable` active with a six-minute service watchdog and `FailureAction=reboot-immediate`. We are not claiming incident-free operation since the configuration change.

Questions for NVIDIA:

1. What instrumentation would distinguish an allocation returning `NV_ERR_NO_MEMORY` cleanly from a reclaim stall or the silent prefill failure?
2. Is `RmNumaAllocSkipReclaimPercent` supported for testing on GB10, and what default/units should operators expect?
3. Is there a supported path to account and constrain these allocations with `dmem` or another controller?

We can supply the persistent-journal extracts and the existing PSI/cgroup measurements.
