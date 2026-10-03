---
id: FEATURE-FORUM-RCU-PANIC-PSTORE-01
kind: task
domain: KERNEL_RECOVERY
title: "Validate RCU-stall panic and persistent capture as a GB10 recovery path"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_rcu_panic_pstore --evidence tasks/evidence/FEATURE-FORUM-RCU-PANIC-PSTORE-01", "expect": "exit_zero", "porque": "Must verify the active RCU sysctl and persistent capture path on the target stack, prove rollback, and distinguish a tested panic path from an unobserved natural RCU recovery."}
---

## Failure and proposed mitigation

[NVIDIA forum thread 381655, posts 1–2](https://forums.developer.nvidia.com/t/dgx-spark-gb10-hard-freeze-under-sustained-load-rcu-stall-on-cpu-11-watchdog-kdump-both-fail-working-pstore-only-crash-capture-recipe-eviden/381655/1) reports an ASUS/NVIDIA DGX Spark, BIOS GX10DGX.0103.2026.0129.1152, Ubuntu 24.04, kernel 6.17.0-1008-nvidia, driver 580.142, and a roughly 2h16m hard freeze during mixed GPU/host workload. The owner reports 44 RCU stall messages, a failed kdump path, and an SBSA watchdog IRQ path blocked during the lockup. They then configured `kernel.panic_on_rcu_stall=1`, `kernel.panic=30`, `crash_kexec_post_notifiers=1`, and EFI pstore; a manually injected panic captured pstore output. The author did not demonstrate that a later natural RCU stall successfully panicked and rebooted.

The follow-up distinguishes the kernel RCU stall from a later power-path event. The September power interruption had no RCU, Xid, OOM, thermal or panic evidence. `panic_on_rcu_stall` cannot be assumed to recover a physical power cut or a CPU lockup that prevents the panic path from running.

## Blackbox coverage and gap

The adopted `99-freeze-panic.conf` enables `hung_task_panic`, `softlockup_panic`, and `hardlockup_panic`; it does not set `kernel.panic_on_rcu_stall`. `99-blackbox-panic.conf` sets the panic timeout. Blackbox checks kdump and reads its saved dmesg, but [FEATURE-KDUMP-PSTORE-PREAPAGADO](FEATURE-KDUMP-PSTORE-PREAPAGADO.md) explicitly leaves pstore support and access unverified. The forum case adds an RCU-specific trigger and an experimentally exercised pstore path, but it does not prove recovery from a naturally occurring RCU stall on this project's OEM/kernel.

## Scope

On the local GB10 and any proposed additional OEM, read the exact kernel, BIOS, module, sysctl, watchdog, crash-kernel and pstore state before recommending a change. Assess the interaction among `panic_on_rcu_stall`, `kernel.panic`, existing kdump, `crash_kexec_post_notifiers`, the EFI pstore backend, and `systemd-pstore`. Preserve the current kdump path unless an experiment demonstrates a conflict and documents why changing it improves recovery.

The proposed prevention is opt-in until tested: panic and auto-reboot on an RCU stall may restore access sooner than a permanent lock, while pstore may retain the last kernel messages. Do not infer that SBSA watchdog will recover this CPU/IRQ stall; the thread reports the opposite. Do not claim recovery of a power cut from a forced software panic test.

## Closure evidence

Provide the active sysctl and boot parameters from the target machine, pstore backend and permissions, plus a reversible configuration and verified rollback. On a disposable or owner-approved canary, run an arrival-side forced-panic test and verify pstore survives reboot and `bb scan` can read the resulting record. Include a control proving the current kdump path remains armed or precisely documenting any justified replacement. Preserve all `could_not_run` results. Natural RCU-stall recovery remains unverified until an actual incident or controlled fault injection exercises that trigger; mark the report accordingly rather than using the forced-panic result as proof.

## Risks and limits

An RCU panic causes an immediate machine-wide reboot after the configured timeout and can lose unsaved work. EFI pstore, crash-kernel kdump, Secure Boot, kernel cmdline and systemd-pstore behavior vary by OEM and image. The thread's causal explanation for why kdump fails and why the CPU lockup blocks the watchdog remains partly hypothesized.


## Estado de publicación de esta investigación

Propuesta abierta. Los comandos de cierre describen el verificador y evidencia requeridos; esta rama publica investigación y fichas, sin implementación ni resultados de ejecución de los mecanismos propuestos.
