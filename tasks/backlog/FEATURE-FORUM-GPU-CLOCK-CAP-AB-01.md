---
id: FEATURE-FORUM-GPU-CLOCK-CAP-AB-01
kind: task
domain: GPU
title: "Validate lower GPU clock caps as an opt-in defense against silent power-offs"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_gpu_clock_cap_ab --evidence tasks/evidence/FEATURE-FORUM-GPU-CLOCK-CAP-AB-01", "expect": "exit_zero", "porque": "Must compare a lower cap against the currently applied cap on an identified OEM/driver stack, preserve stability and performance results, and prove restoration of the original clock policy."}
---

## Failure and reported mitigation

Two owners report abrupt GB10 system power-offs under GPU load followed by stability with a lower GPU clock cap:

- [DGX Spark thread 380669, post 1](https://forums.developer.nvidia.com/t/dgx-spark-system-hardware-crashes-at-around-75w-system-reboots-repeatedly-wattage-cap-workaround-found/380669/1) reports repeated failures around 75 W and operation without repeated reboots after `sudo nvidia-smi -lgc 300,2100`; the author says `sudo nvidia-smi -rgc` restores the full range. The report does not identify an OEM model or give a soak duration.
- [HP ZGX Nano G1n thread 384492, posts 1–2](https://forums.developer.nvidia.com/t/gb10-abruptly-powers-off-under-heavy-gpu-load-nvidia-smi-lgc-300-2200-prevents-it/384492/1) reports kernel 7.0.0-1019-nvidia, open driver 580.178.04 and repeated abrupt power loss during continuous vLLM vision requests, with no clean shutdown, panic, Xid, OOM or thermal record. The author reports over 96 hours without an outage after `sudo nvidia-smi -lgc 300,2200`, while explicitly leaving the root cause unproven. A second owner says improved airflow let their different unit run at full clocks, so the cap is not established as a universal fix.
- [DGX Spark Founders Edition thread 383624, post 9](https://forums.developer.nvidia.com/t/dgx-spark-silent-hard-freeze-under-sustained-llama-cpp-inference-no-xid-oom-panic-10-second-telemetry-captured-warranty-ends-oct-14-requesting-cas/383624/9) adds three same-image/BIOS/driver units as a control group: two had 14–15 days without a stop while one had 14 unrecoverable stops in four days. The author reports 79,100 one-second samples; high temperature alone and low memory alone did not precede the observed failures, while the conjunction had two failures in eight episodes. Four timestamped stops occurred during model load/unload. A `300,2100` clock cap changed temperatures in matched workloads, and an escalating 13-minute test had zero failures, but this short run is explicitly not a full-day proof.

## Blackbox coverage and gap

The adopted `atom-clock-lock` unit declares `nvidia-smi -lgc 300,2800` at boot. `atom_gpu_telemetry.py` records GPU power, clock, temperature and throttle signals; `bb scan` reports clock/throttle anomalies. This review did not verify the effective driver range on the live system, and no local A/B establishes whether a lower range prevents the reported failures. The forum reports support a controlled prevention experiment, not a default change or proof that power spikes caused the outages.

## Scope

On each supported OEM and driver stack, compare the declared 300,2800 range with an owner-selected lower cap under the same bounded, reproducible inference workload. Start with the reported 2200 MHz cap on the HP ZGX Nano configuration and a 2100 MHz cap only when the device identity and driver confirm that range is accepted. Record OEM, firmware, BIOS, kernel, driver/module, workload version, effective clock, board/GPU power signals available, temperatures, journal/pstore evidence, performance, run duration and any interruption.

Keep the experiment opt-in. Do not lower the installed 2800 MHz ceiling globally from these reports alone. Record how the persistent service would accept an explicitly configured cap and restore the prior value. The runtime rollback must restore the actual policy (`300,2800` under the current Blackbox unit), since `-rgc` alone returns to the driver's maximum and the unit may reapply its configured range at the next start.

## Closure evidence

Provide matched baseline/capped runs on a named GB10 OEM, including sustained inference and model load/unload phases, an idle/control period, and a repeated run. Where possible, use identical units as a control group. Report failure counts, exact elapsed soak, request latency/throughput, temperature and power observations, applied-clock confirmation, and all `could_not_run` signals. Demonstrate rollback to the original effective range and verify it in the driver's response. A stability claim requires a predeclared soak duration and repeat; the forum's 13-minute test and 96-hour single-owner report alone do not close the local result.

## Limits

The two positive reports come from different OEMs and driver/kernel versions. The mechanism is unknown; thermal airflow may explain some cases. A clock cap trades peak performance for a possible stability benefit and requires per-OEM evidence.

## Índice de propuestas del lote 00

- `FORUM-00-OEM-PD-DEGRADED-LOW-POWER-STATE` — [Gate degraded GB10 low-power state by OEM firmware and measured workload](https://forums.developer.nvidia.com/t/dgx-spark-performance-degradation-gpu-power-draw-issue/361294); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.


**`BB-GLM52-LOW-CLOCK-UNPLUG-RECOVERY-CANARY`.** En un clúster GLM-5.2, el dueño reporta que uno de sus Spark quedó en 667 MHz y que retirar alimentación/desconectar y reiniciar restauró clocks normales y throughput promedio cercano a 25 tok/s ([374125, posts 161, 166](https://forums.developer.nvidia.com/t/glm-5-2-on-a-4-gb10-cluster-22-tok-s-decode-256k-ctx-recipe/374125/166)). No publicó serie de clocks antes/después, OEM/driver, códigos de throttle ni reproducción; otro participante solo sugirió revisar clocks. Añadir comparación de clock efectivo y throughput por nodo bajo carga fija, guardar Xid/throttle/power disponibles fuera del equipo y capturar antes de recuperar. El desenchufe/reinicio del autor es relato sin RCA: no automatizarlo y no asumir que un cap arregla un estado a 667 MHz.


**Señal relacionada para `BB-GLM52-LOW-CLOCK-UNPLUG-RECOVERY-CANARY`.** Otro dueño reportó Gemma4 con GPU PD throttle a 611 MHz y menos de 10 W, tras lo que reconectar PSU mejoró la velocidad de benchmark; una persona distinta dice que una receta de 26B dejó el Spark sin respuesta hasta retirar alimentación ([365490, posts 64, 82, 111](https://forums.developer.nvidia.com/t/gemma-4-models-which-vllm-version-any-prs-spotted/365490/64)). Sin telemetría, identidad exacta o A/B, no vincular las dos quejas ni atribuirlas a PD. Registrar clock/power/throttle y captura previa a cualquier ciclo eléctrico.

## Estado de publicación de esta investigación

Propuesta abierta. Los comandos de cierre describen el verificador y evidencia requeridos; esta rama publica investigación y fichas, sin implementación ni resultados de ejecución de los mecanismos propuestos.
