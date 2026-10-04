---
id: FEATURE-FORUM-WIFI-ISOLATION-01
kind: task
domain: HOST_USABILITY
title: "Detect and recover Wi-Fi isolation without misclassifying a live host as frozen"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_wifi_isolation --evidence tasks/evidence/FEATURE-FORUM-WIFI-ISOLATION-01", "expect": "exit_zero", "porque": "Must prove the recorded NetworkManager and supplicant failure is distinguished from a host freeze, test a bounded recovery policy on the cited stack, and preserve rollback evidence."}
---

## Failure and evidence

In [NVIDIA forum thread 358951, post 14](https://forums.developer.nvidia.com/t/spark-hangs-requires-a-hard-reset-physically-unplugging/358951/14), an ASUS Ascent GX10 (GB10), DGX OS 7.5.0, driver 580.173.02, kernel 6.17.0-1029-nvidia, MediaTek MT7925/`mt7925e`, NetworkManager, and `wpa_supplicant` lost Wi-Fi after an AP band-steer roam from 2.4 to 5 GHz. The author reports an association handshake timeout classified as `WRONG_KEY`, followed by NetworkManager `failed (reason 'no-secrets')` on a headless host with no agent to answer. No further reconnect attempts occurred. A local fsyncing logger recorded 1,473 healthy samples for about 90 minutes while SSH was unreachable; the operator power-cycled the machine.

The report supports network isolation, not an idle host freeze. Its separate genuine host freeze occurred during a deep-context vLLM run and is covered by the existing unified-memory investigation. The author proposed wired Ethernet, pinning one BSSID or disabling band steering, and unlimited autoconnect retries with a dispatcher fallback; those workarounds were proposals, not reported A/B results. NVIDIA later linked the Wi-Fi case to another investigation in post 15.

## Blackbox gap

`bb sample` already records per-interface traffic counters and default-gateway observations, and `bb scan` analyzes traffic rates. `service_probe.py` checks an SSH banner on loopback when explicitly enabled. These signals can show that the host is alive, but they do not record Wi-Fi association state, the supplicant's authentication reason, NetworkManager's terminal `no-secrets` state, or whether the management path remains reachable. `bb-usable` can therefore remain healthy locally while a remote operator loses access; a human can mistake isolation for a machine freeze and take an unnecessary hard reset.

## Scope

Reuse journal/systemd, `nmcli`/NetworkManager state when available, and existing sample timestamps. Add an explicit network-usability record that correlates local-host responsiveness, interface/link state, association state, NetworkManager failure reason, default route, and an operator-configured management endpoint. Keep a failed remote probe distinct from a failed local host probe. Declare permission, executable, timeout, and stale-data failures as `could_not_run`.

Define a reversible recovery policy for headless Wi-Fi systems. Evaluate wired Ethernet as the preferred recovery path. On the cited stack, A/B-test the author's BSSID/band-steering and unlimited-autoconnect/dispatcher suggestions before recommending them as effective. Do not silently write NetworkManager connection settings or restart services; provide a documented opt-in setting and rollback command only after the experiment passes. Record the exact adapter firmware, driver, kernel, DGX OS, AP/roaming configuration, and NetworkManager/wpa_supplicant versions.

## Closure evidence

Provide a captured or faithful fixture sequence for (1) the cited WPA handshake timeout followed by `WRONG_KEY` and `no-secrets` while local host probes remain healthy, and (2) a real local host/service failure. `bb scan` must distinguish the two, preserve missing evidence, and avoid issuing a host-wide restart for a network-only failure. On the cited OEM/driver stack, run a bounded roam/soak A/B for each proposed workaround, report reconnection time and recurrence count with the literal commands and output, and include rollback verification. The forum's proposed workarounds alone do not close the prevention claim.

## Limits

Evidence is one owner's report and one identified hardware/software stack. The Wi-Fi workaround and firmware/driver fix remain unvalidated. Other OEMs and Wi-Fi chipsets need separate evidence.

[364326](https://forums.developer.nvidia.com/t/364326) añade recovery1.120.38 en OOBE Wi-Fi loop incluso con Ethernet; NVIDIA lo relaciona con caída del connectivity-check Canonical el21-Mar. Distinguir dependencia externa del chequeo frente a NIC/ruta/host; comprobar consola y alternativa local antes de reimage o reset de red.

[354604](https://forums.developer.nvidia.com/t/354604) reports a Netplan/NetworkManager YAML file with NUL corruption; applying a QSFP network update removed management SSH, and renaming the damaged file restored access. NVIDIA asks for port references, with no final fix in the thread. Add a recoverable network configuration path: preserve original bytes/mode, validate before apply, use a separate management channel, and schedule a timed rollback that the operator cancels only after connectivity is verified. Do not replace or rewrite files automatically based on this report.


## Índice de propuestas del lote 00

- `FORUM-00-MT7925-PTK-AND-5GHZ-FAILURE-DIAGNOSTIC` — [Distinguish MT7925 pairwise-key installation failure and 5 GHz roam loops from wrong-password or host failure](https://forums.developer.nvidia.com/t/374231); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.


## Defecto de entrada CLI detectado (2026-10-04)

La ejecución literal del close_check termina con código 0 y stdout vacío porque el módulo tiene API `verify` pero carece de entrada `main/__main__`. La llamada API sobre la misma captura devuelve UNKNOWN; el código de salida actual no acredita cierre. Recibo: `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/direct-29-original-close-current-run.json`.

El agente hardware tiene asignada la entrada CLI con JSON literal y códigos 0/1/2 para PASS/FAIL/UNKNOWN, respectivamente; el código 0 exige could_not_run=0. Se requieren pruebas de proceso real para la captura ausente, argumentos y controles positivos/negativos. El close_check se conserva y la ficha sigue abierta.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: La observación del host no acredita aislamiento de fallos NM/supplicant frente a freeze ni política recuperable sobre stack citado.
- Evidencia faltante para cierre: capturas de fallo y host liveness; versiones NM/supplicant/kernel; recuperación acotada y rollback
- Siguiente acción: Ejecutar en canario con acceso de rescate un fallo acotado de NM/supplicant, distinguirlo de freeze y demostrar recuperación/rollback.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/FEATURE-FORUM-WIFI-ISOLATION-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_02.json`, `tasks/evidence/FEATURE-FORUM-WIFI-ISOLATION-01/host-observation.txt`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
