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

## Trabajo en la ATOM

Registrar en la ATOM un estado de usabilidad de red que separe host vivo con Wi-Fi aislado (asociacion, razon del supplicant, `no-secrets` de NetworkManager, ruta por defecto, endpoint de gestion) de un cuelgue real; recuperacion opt-in con rollback y A/B de cada workaround antes de recomendarlo.

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/spark-hangs-requires-a-hard-reset-physically-unplugging/358951/14
- https://forums.developer.nvidia.com/t/364326
- https://forums.developer.nvidia.com/t/354604
- https://forums.developer.nvidia.com/t/374231

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Blackbox gap

`bb sample` already records per-interface traffic counters and default-gateway observations, and `bb scan` analyzes traffic rates. `service_probe.py` checks an SSH banner on loopback when explicitly enabled. These signals can show that the host is alive, but they do not record Wi-Fi association state, the supplicant's authentication reason, NetworkManager's terminal `no-secrets` state, or whether the management path remains reachable. `bb-usable` can therefore remain healthy locally while a remote operator loses access; a human can mistake isolation for a machine freeze and take an unnecessary hard reset.

## Scope

Reuse journal/systemd, `nmcli`/NetworkManager state when available, and existing sample timestamps. Add an explicit network-usability record that correlates local-host responsiveness, interface/link state, association state, NetworkManager failure reason, default route, and an operator-configured management endpoint. Keep a failed remote probe distinct from a failed local host probe. Declare permission, executable, timeout, and stale-data failures as `could_not_run`.

Define a reversible recovery policy for headless Wi-Fi systems. Evaluate wired Ethernet as the preferred recovery path. On the cited stack, A/B-test the author's BSSID/band-steering and unlimited-autoconnect/dispatcher suggestions before recommending them as effective. Do not silently write NetworkManager connection settings or restart services; provide a documented opt-in setting and rollback command only after the experiment passes. Record the exact adapter firmware, driver, kernel, DGX OS, AP/roaming configuration, and NetworkManager/wpa_supplicant versions.

## Closure evidence

Provide a captured or faithful fixture sequence for (1) the cited WPA handshake timeout followed by `WRONG_KEY` and `no-secrets` while local host probes remain healthy, and (2) a real local host/service failure. `bb scan` must distinguish the two, preserve missing evidence, and avoid issuing a host-wide restart for a network-only failure. On the cited OEM/driver stack, run a bounded roam/soak A/B for each proposed workaround, report reconnection time and recurrence count with the literal commands and output, and include rollback verification. The forum's proposed workarounds alone do not close the prevention claim.

## Limits

Evidence is one owner's report and one identified hardware/software stack. The Wi-Fi workaround and firmware/driver fix remain unvalidated. Other OEMs and Wi-Fi chipsets need separate evidence.

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

## Avance 2026-10-13

- close_check antes: rc=2, `status: unknown`, could_not_run=1 (falta `commands.json` de captura cruda). Sin cambio: requiere captura real de roam/soak en el stack citado, que implica tocar la red de la maquina.
- Hecho: la regla de clasificacion aislamiento vs cuelgue (`tools/incident_report.py::clasifica_hueco_de_red`, ver FEATURE-BB-FALSO-CUELGUE-POR-AISLAMIENTO-WIFI-01). Falta: A/B de workarounds, fixture/captura del WRONG_KEY+no-secrets, recuperacion opt-in con rollback.

## Criterios ejecutables de `tools.verify_wifi_isolation` (2026-10-14)
Los criterios ejecutables de `tools.verify_wifi_isolation` se miden en esta ficha: su `close_check` corre ese verificador contra la captura real del sujeto. La meta-ficha `DEBT-CLOSE-CHECK-VERIFY-WIFI-ISOLATION-01`, que pedia implementarlos, se cerro el 2026-10-14 como `duplicate` (voto de Luis: consolidar en la ficha sujeto): el verificador existe y hoy, sin esa captura, sale con could_not_run (rc=2); conseguir la captura es trabajo de esta ficha.
