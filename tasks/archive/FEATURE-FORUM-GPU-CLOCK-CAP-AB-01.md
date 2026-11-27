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

## Trabajo en la ATOM

A/B opt-in en la ATOM. Fijar la carga de `nemotron-local`, la duración, las repeticiones y los umbrales antes de empezar. Medir reloj, potencia, temperaturas e interrupciones. El rango de partida y el de restauración se eligen con evidencia de la sesión actual.

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/dgx-spark-system-hardware-crashes-at-around-75w-system-reboots-repeatedly-wattage-cap-workaround-found/380669/1
- https://forums.developer.nvidia.com/t/gb10-abruptly-powers-off-under-heavy-gpu-load-nvidia-smi-lgc-300-2200-prevents-it/384492/1
- https://forums.developer.nvidia.com/t/dgx-spark-silent-hard-freeze-under-sustained-llama-cpp-inference-no-xid-oom-panic-10-second-telemetry-captured-warranty-ends-oct-14-requesting-cas/383624/9
- https://forums.developer.nvidia.com/t/363323
- https://forums.developer.nvidia.com/t/376039
- https://forums.developer.nvidia.com/t/371037
- https://forums.developer.nvidia.com/t/371537
- https://forums.developer.nvidia.com/t/dgx-spark-performance-degradation-gpu-power-draw-issue/361294
- https://forums.developer.nvidia.com/t/glm-5-2-on-a-4-gb10-cluster-22-tok-s-decode-256k-ctx-recipe/374125/166
- https://forums.developer.nvidia.com/t/gemma-4-models-which-vllm-version-any-prs-spotted/365490/64

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Blackbox coverage and gap

The historical review observed `atom-clock-lock` declaring `300,2800` at boot. The unit can now declare a different range. `atom_gpu_telemetry.py` records GPU power, clock, temperature and throttle signals; `bb scan` reports clock/throttle anomalies. This review did not verify the effective driver range on the live system, and no local A/B establishes whether a lower range prevents the reported failures. The forum reports support a controlled prevention experiment, not a default change or proof that power spikes caused the outages.

## Scope

On each supported OEM and driver stack, compare the original effective policy with an operator-approved lower cap under the same bounded, reproducible inference workload. Select a supported ceiling below the measured original ceiling and preserve the original floor. Record OEM, firmware, BIOS, kernel, driver/module, workload version, effective clock, board/GPU power signals available, temperatures, journal/pstore evidence, performance, run duration and any interruption.

Keep the experiment opt-in. Runtime rollback must restore the full original range observed in the same window. A generic reset can restore a different range. Leave the persistent service configuration intact during the experiment.

## Closure evidence

Provide matched baseline/capped runs on a named GB10 OEM, including sustained inference and model load/unload phases, an idle/control period, and a repeated run. Where possible, use identical units as a control group. Report failure counts, exact elapsed soak, request latency/throughput, temperature and power observations, applied-clock confirmation, and all `could_not_run` signals. Demonstrate rollback to the original effective range and verify it in the driver's response. A stability claim requires a predeclared soak duration and repeat; the forum's 13-minute test and 96-hour single-owner report alone do not close the local result.

## Limits

The two positive reports come from different OEMs and driver/kernel versions. The mechanism is unknown; thermal airflow may explain some cases. A clock cap trades peak performance for a possible stability benefit and requires per-OEM evidence.

## Avance de ejecución 2026-10-02

Consulta real confirma declaración 300,2800; 0 ensayos A/B, 0 cambios de clock. Falta workload, soak predeclarado, cap aplicado y rollback verificado. Mantener opt-in.

Evidencia y pendientes: `tasks/evidence/FEATURE-FORUM-GPU-CLOCK-CAP-AB-01/progress.txt`. Conserva `open`; la captura de estado verifica el instrumento y deja pendiente el ensayo de recuperación/prevención requerido.

## Consulta nativa de capacidades 2026-10-04

`readonly-clock-capability-current.json` conserva comandos de solo lectura. Driver 580.178.04 sobre GB10/kernel 6.17.0-1032-nvidia: `clocks.min.graphics` se rechaza con rc2; `--query-supported-clocks=memory,graphics` retorna rc0 pero `[N/A], [N/A]`, por lo que permanece semánticamente could_not_run. Total could_not_run=2, fail=0. Consulta válida de current/max devuelve 2418/3003 MHz, 11.20 W, 41 °C, 2% utilización; max no prueba rango bloqueado. El servicio declara 300,2800 y aparece active/exited; esa declaración tampoco es readback del rango efectivo. No hubo cambio de clocks, workload A/B, reinicio ni rollback. La falta de consulta nativa requerida se conserva como pendiente del verificador.

## Defecto de entrada CLI detectado (2026-10-04)

La ejecución literal del close_check termina con código 0 y stdout vacío porque el módulo tiene API `verify` pero carece de entrada `main/__main__`. La llamada API sobre la misma captura devuelve UNKNOWN; el código de salida actual no acredita cierre. Recibo: `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/direct-29-original-close-current-run.json`.

El agente hardware tiene asignada la entrada CLI con JSON literal y códigos 0/1/2 para PASS/FAIL/UNKNOWN, respectivamente; el código 0 exige could_not_run=0. Se requieren pruebas de proceso real para la captura ausente, argumentos y controles positivos/negativos. El close_check se conserva y la ficha sigue abierta.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: El recibo del host dice 0 ensayos A/B y 0 cambios de clock; no contiene workload, soak ni rollback.
- Evidencia faltante para cierre: GPU/OEM/driver; cap actual/aplicado; carga y soak preregistrados; throughput/estabilidad/temperaturas antes/después; rollback verificado.
- Siguiente acción: Solicitar ensayo A/B opt-in en GPU de laboratorio con identidad/cap original, workload y umbrales preregistrados, estabilidad/throughput/temp antes/después y restauración verificada.
- Responsable del siguiente paso: BB; operador Luis para workload/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FEATURE-FORUM-GPU-CLOCK-CAP-AB-01.md`, `tasks/evidence/FEATURE-FORUM-GPU-CLOCK-CAP-AB-01/progress.txt`, `tools/verify_gpu_clock_cap_ab.py`, `tools/hardware_evidence.py`, `tests/test_debt_registration_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Criterios ejecutables de `tools.verify_gpu_clock_cap_ab` (2026-10-14)
Los criterios ejecutables de `tools.verify_gpu_clock_cap_ab` se miden en esta ficha: su `close_check` corre ese verificador contra la captura real del sujeto. La meta-ficha `DEBT-CLOSE-CHECK-VERIFY-GPU-CLOCK-CAP-AB-01`, que pedia implementarlos, se cerro el 2026-10-14 como `duplicate` (voto de Luis: consolidar en la ficha sujeto): el verificador existe y hoy, sin esa captura, sale con could_not_run (rc=2); conseguir la captura es trabajo de esta ficha.

## Pendiente después de integrar el gate por impacto

1. Identificar una interfaz soportada que lea el mínimo y máximo efectivos del bloqueo de reloj en el GB10. En el driver 580.178.04, `nvidia-smi -q -d CLOCK` sale con código 0 y muestra frecuencias instantáneas, máximas y de aplicación. La consulta `clocks.min.graphics` sale con código 2. El rango declarado por el servicio acredita la configuración solicitada.
2. Conectar esa lectura al verificador. Comprobar una lectura válida y los rechazos de lectura ausente, rango incorrecto y restauración sin confirmación. Mantener `could_not_run` si la interfaz falta.
3. Con ventana autorizada y rango de partida confirmado, capturar la misma carga antes y después del cap de prueba. Confirmar la restauración del rango original y aportar el inventario térmico de esa misma ventana a la [ficha de tradeoff](DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01.md).

Estado de la captura real: `fail=0`, `could_not_run=1`. La ficha conserva su `close_check` y permanece abierta.

## Excepción de publicación del 2026-11-22

Luis autorizó una sola publicación de `master` con la fila `clock-gpu-ab-required` en `COULD_NOT_RUN` por la captura física ausente. Antes del push se ejecuta el pre-push oficial sobre el SHA y el rango exactos. Sólo se permite continuar si esa fila es el único impedimento y las demás filas requeridas pasan. La excepción se consume al intentar ese único push y no aplica a publicaciones posteriores. La ficha conserva su criterio de cierre.

Orden de pruebas para cerrar la ficha:

1. Medir la lectura del rango efectivo en modo sólo lectura. Comprobar que el verificador rechaza una lectura ausente, un rango distinto y una restauración sin confirmación.
2. Acreditar el rango inicial y reservar la ventana autorizada. Ejecutar la misma carga con el rango inicial y con el cap de prueba. Registrar zonas térmicas, rendimiento y estabilidad dentro de la ventana.
3. Restaurar el rango inicial y comprobarlo con la misma interfaz. Correr este `close_check` y el de la ficha de tradeoff sobre ambas capturas. Mantener las dos fichas abiertas si alguna prueba falla o queda sin ejecutar.

## Avance histórico del 2026-10-14

El lote dejó agendada una ventana de 60 minutos para comparar el rango de partida y un techo menor con la misma carga, bajo autorización del operador. La receta asumía los rangos declarados en esa fecha. Las condiciones siguientes reemplazan esa receta operativa.

## Condiciones vigentes antes de reservar la ventana

La ventana requiere autorización del operador y comparte captura con DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01. Ejecutar `bb status clock lock` en sólo lectura para cotejar la declaración del servicio con la confirmación de su arranque. Obtener además una lectura independiente del rango activo y la lista de relojes admitidos por el driver del equipo del ensayo. La confirmación del arranque acredita aquella aplicación. El reloj instantáneo, el máximo nominal y la confirmación histórica dejan sin acreditar el rango activo.

Si alguna lectura falta, discrepa o devuelve `N/A`, conservar `COULD_NOT_RUN` y detener la preparación antes de cualquier escritura de reloj. Si las lecturas concuerdan, fijar el rango original completo como destino de restauración. Al terminar, repetir la misma lectura independiente y exigir coincidencia exacta. El cierre sigue a cargo de `python3 -m tools.verify_gpu_clock_cap_ab --evidence tasks/evidence/FEATURE-FORUM-GPU-CLOCK-CAP-AB-01`.
