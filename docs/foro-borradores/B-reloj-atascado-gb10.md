# [DRAFT B] Category: DGX Spark / GB10
**Title:** Stuck GPU clock on GB10 (500–800 MHz, zero throttle reasons): a measured case on a Gigabyte AI TOP ATOM, a detector, and a heat side-effect

This is another confirmed case of the state described in threads 376039, 376239, 366944, 362737, 375687, 376542, 378150 and 382897, with numbers and a detector.

**Unit**: Gigabyte AI TOP ATOM (GB10), DGX OS 7.2.3, driver 580.178.04, kernel 6.17.0-1032-nvidia, PD firmware 5.22/5.0.

**Timeline (same day)**
- 16:59 local: last healthy sample under load, 2073 MHz, 28.3 W.
- 17:17: first stuck sample, 676 MHz, 8.5 W.
- It appeared between two boots (healthy 16:55–17:08, stuck from 17:08 on). The three following boots: 100 % of the samples with GPU utilisation ≥ 80 % were below 1000 MHz.

**Stuck state**: SM clock 663 MHz (max 3003, default application clock 2418), 16.4 W, utilisation 95 %, throttle reasons `0x0`, 23.5 TFLOPS on an fp16 8192×8192 matmul. `nvidia-smi -lgc` is accepted and ignored. A reboot does not clear it.

**Remedy** (as reported by NVIDIA staff in 376039/376239; one user in the threads reports it was not enough for them): power off, unplug the AC adapter from the wall, hold the power button ~10 s, wait a few minutes, reconnect. On my unit it cleared: 2080 MHz, 67 W, 77.4 TFLOPS on the same test. I have no healthy baseline from before, so 77.4 is a post-fix reading, not a spec.

**Side-effect I could not rule out (hypothesis, not proven)**: threads 381549 and 383821 say the fan curve follows GPU temperature. With the GPU stuck and cold, the CPU/SoC zones heated with the fans low. My unit also cut power once after hours in that state. I have no evidence that the stuck clock caused the cut.

**Detector** (open, part of https://github.com/lcasarin-maker/blackbox): `bb reloj --prueba` runs a ~15 s matmul and samples clock/power/throttle with `nvidia-smi`. Three verdicts: STUCK (median < 1000 MHz with load and no throttle reasons), HEALTHY (≥ 1400 MHz, the threshold used by the tool in 362737), INDETERMINATE (no load or in between; it never reports healthy without load). A boot-time timer runs it six minutes after boot, because this time it took me ~8 hours to notice. It uses the smoke test from 366944 and the 1400 MHz threshold from 362737.

**Not known**: the root cause (power delivery / PD negotiation?), why some units do not recover, and whether 7.2.3 changes anything.

**Questions for NVIDIA**
1. Can the driver report a throttle reason (or any signal) for this state?
2. Is there a firmware/PD fix planned, or should the power cycle be the documented procedure?
3. Can the fan curve also consider CPU/SoC temperature on partner units?
