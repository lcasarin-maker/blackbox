---
id: FORUM-02-PSTORE-KERNEL-REGRESSION
kind: task
domain: KERNEL
title: "Leer pstore y validar una corrección de kernel para reinicios FPAC/PSCI en GB10"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FORUM-02-PSTORE-KERNEL-REGRESSION --evidence tasks/evidence/FORUM-02-PSTORE-KERNEL-REGRESSION", "expect": "exit_zero", "porque": "Verificador específico pendiente: debe validar captura pstore, identidad de la pila, resolución del vendor y recomendación de rollback/actualización con control."}
---

## Fuente y evidencia

Hilo NVIDIA [354205](https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205), especialmente posts [29–37](https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205/29), [43–47](https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205/43) y la lectura de pstore en [post 45](https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205/45).

En un DGX Spark P4242 con BIOS `5.36_0ACUM018`, kernel `6.17.0-1014-nvidia` y driver `580.142`, el hilo reporta reinicios incluso en idle tras reinstalar OS y ejecutar Field Diagnostics. Se probaron cambios secundarios: `nvidia-spark-realtek-mod-options` hizo cargar `r8127` en vez de `r8169` y se arreglaron las zonas térmicas, pero los reinicios siguieron. Una lectura independiente de pstore atribuyó dos registros a una carrera FPAC/PSCI/NMI durante entrada ACPI LPI y a `SBSA Generic Watchdog timeout`; también reportó que la carrera aparecía en `6.17.0-1008` y seguía en `6.17.0-1014`. En ese mismo caso había además fallos DOE durante enumeración PCIe y enlace de GPU a x0 después de actualizar SoC/EC firmware; el soporte de NVIDIA pidió tramitar RMA.

La identificación FPAC/PSCI es un análisis de participante del foro, no una confirmación de NVIDIA ni prueba de que afecte a otros OEM. NVIDIA no publicó en el hilo una versión corregida o workaround confirmado. El host Blackbox actual informa kernel `6.17.0-1032-nvidia`, por lo que no coincide con el kernel reportado; la exposición del firmware local queda sin comprobar.

`FEATURE-KDUMP-PSTORE-PREAPAGADO` lee capturas de kdump, pero deja pstore sin evaluar porque `/sys/fs/pstore` no era legible sin privilegios. `bb hw` conserva la versión de kernel, pero Blackbox no interpreta pstore para relacionar una firma persistente con la pila que la produjo. Esa brecha impide verificar el mecanismo y decidir entre actualización de vendor, selección temporal de kernel conocido o RMA.

## Trabajo

Con privilegios de solo lectura, comprobar si el firmware/kernel de la máquina expone `/sys/fs/pstore`; registrar permisos, capacidad, rotación y contenido sin cambiar la configuración. Añadir captura con identidad de boot, kernel, BIOS/EC, driver y timestamp. Analizar las firmas FPAC/PSCI/NMI, SBSA timeout y DOE/link x0 como señales separadas; un watchdog timeout por sí solo no demuestra que Firefox u otra aplicación causó el reinicio.

Para la combinación exacta de OEM/BIOS/EC/kernel, revisar changelog o confirmación del fabricante sobre la corrección de la carrera y del fallo DOE. Si la pila coincide con una combinación afectada, proponer únicamente una actualización o rollback soportado y reversible; si el dispositivo persiste en DOE abort/link x0 tras la actualización soportada, emitir recomendación de escalación/RMA con el paquete de evidencia. No pinnear kernel, desactivar watchdog ni alterar parámetros de idle en la máquina protegida desde esta ficha.

## Riesgos y cierre

Pstore puede rotar o no existir en ciertos OEM y no registra una pérdida instantánea de alimentación sin panic. Los registros pueden incluir datos del sistema y necesitan acceso mínimo. Un rollback puede retirar parches de seguridad o no arrancar con el firmware local; preparar selección de kernel anterior y recuperación antes de probarlo. Las conclusiones de DGX Spark FE no se trasladan a ASUS/Gigabyte sin medir sus versiones.

Cerrar solo después de leer evidencia real de pstore, comprobar la identidad completa de la pila local y documentar la aplicabilidad con una fuente del vendor sobre la versión corregida o el diagnóstico/RMA. Si pstore no existe o el acceso falla, la ficha conserva `open` y registra `could_not_run`; esa ausencia no acredita prevención ni resolución. Si se ejecuta A/B, conservar el resultado con kernel/firmware anterior y corregido, pruebas sanas en idle y bajo carga, pstore/journal y rollback. Un host en `6.17.0-1032` no se declara afectado solo por el hilo.

## Avance de ejecución 2026-10-02

bb recovery conserva boot/kernel/sysctl, fingerprints de pstore y firmas FPAC/PSCI/NMI/SBSA/DOE/RCU independientes si son legibles. Lectura local pstore denegada: 0 registros inspeccionados, could_not_run=1 para ese interfaz. Falta confirmación vendor aplicable y prueba persistente, no pinnear kernel ni recomendar versión corregida sin fuente.

Evidencia y pendientes: `tasks/evidence/FORUM-02-PSTORE-KERNEL-REGRESSION/progress.txt`. Conserva `open`; la captura de estado verifica el instrumento y deja pendiente el ensayo de recuperación/prevención requerido.

**Correlación del hallazgo `BB-FIELDDIAG-REAL-WORKLOAD-COVERAGE-GAP`.** En el hilo [354205, posts 43–47](https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205/43), hay texto pstore pegado en post45 para kernel `6.17.0-1014-nvidia`: registros separados de FPAC/PSCI/NMI y `SBSA Generic Watchdog timeout`; una lectura del participante relaciona DOE/mailbox y PCIe x0 con GPU sin cargar. NVIDIA no confirma el análisis y al final deriva el caso a RMA. Se probaron updates, reinicio en frío y binding `r8127`, pero persiste el fallo. Adjuntos SOS, pstore y journal del hilo no se inspeccionaron; no presentar como root cause confirmada ni como bug universal.


## Índice de propuestas del lote 00

- `FORUM-00-ABRUPT-RESET-OFFBOX-TELEMETRY` — [Pair local reset evidence with durable receiver-side telemetry](https://forums.developer.nvidia.com/t/spark-abruptly-shuts-down/377478); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.

## Avance de ejecución 2026-10-03

Se reutilizó el lector de firmas pstore existente y se vinculó a identidad kernel/boot readonly. El acceso local a `/sys/fs/pstore` fue denegado (`could_not_run=1`); no hay record observado ni prueba de regresión/corrección vendor. El verificador específico de cierre, resolución OEM y recomendación probada siguen pendientes.

Evidencia: `docs/evidence/BB-INSTRUMENTS-kernel.md` y `tasks/evidence/BB-INSTRUMENTS-2026-10-03/kernel-capture.json`. Sigue abierta.
