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

## Trabajo en la ATOM

Dar acceso de lectura a pstore (unit o sudoers de solo lectura) y registrar las firmas FPAC/PSCI/SBSA tras cada reinicio no limpio en `reboot_verdict`; sin fijar kernel.

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205
- https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205/29
- https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205/43
- https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205/45
- https://forums.developer.nvidia.com/t/spark-abruptly-shuts-down/377478

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Trabajo

Con privilegios de solo lectura, comprobar si el firmware/kernel de la máquina expone `/sys/fs/pstore`; registrar permisos, capacidad, rotación y contenido sin cambiar la configuración. Añadir captura con identidad de boot, kernel, BIOS/EC, driver y timestamp. Analizar las firmas FPAC/PSCI/NMI, SBSA timeout y DOE/link x0 como señales separadas; un watchdog timeout por sí solo no demuestra que Firefox u otra aplicación causó el reinicio.

Para la combinación exacta de OEM/BIOS/EC/kernel, revisar changelog o confirmación del fabricante sobre la corrección de la carrera y del fallo DOE. Si la pila coincide con una combinación afectada, proponer únicamente una actualización o rollback soportado y reversible; si el dispositivo persiste en DOE abort/link x0 tras la actualización soportada, emitir recomendación de escalación/RMA con el paquete de evidencia. No pinnear kernel, desactivar watchdog ni alterar parámetros de idle en la máquina protegida desde esta ficha.

## Riesgos y cierre

Pstore puede rotar o no existir en ciertos OEM y no registra una pérdida instantánea de alimentación sin panic. Los registros pueden incluir datos del sistema y necesitan acceso mínimo. Un rollback puede retirar parches de seguridad o no arrancar con el firmware local; preparar selección de kernel anterior y recuperación antes de probarlo. Las conclusiones de DGX Spark FE no se trasladan a ASUS/Gigabyte sin medir sus versiones.

Cerrar solo después de leer evidencia real de pstore, comprobar la identidad completa de la pila local y documentar la aplicabilidad con una fuente del vendor sobre la versión corregida o el diagnóstico/RMA. Si pstore no existe o el acceso falla, la ficha conserva `open` y registra `could_not_run`; esa ausencia no acredita prevención ni resolución. Si se ejecuta A/B, conservar el resultado con kernel/firmware anterior y corregido, pruebas sanas en idle y bajo carga, pstore/journal y rollback. Un host en `6.17.0-1032` no se declara afectado solo por el hilo.

## Avance de ejecución 2026-10-02

bb recovery conserva boot/kernel/sysctl, fingerprints de pstore y firmas FPAC/PSCI/NMI/SBSA/DOE/RCU independientes si son legibles. Lectura local pstore denegada: 0 registros inspeccionados, could_not_run=1 para ese interfaz. Falta confirmación vendor aplicable y prueba persistente, no pinnear kernel ni recomendar versión corregida sin fuente.

Evidencia y pendientes: `tasks/evidence/FORUM-02-PSTORE-KERNEL-REGRESSION/progress.txt`. Conserva `open`; la captura de estado verifica el instrumento y deja pendiente el ensayo de recuperación/prevención requerido.

## Avance de ejecución 2026-10-03

Se reutilizó el lector de firmas pstore existente y se vinculó a identidad kernel/boot readonly. El acceso local a `/sys/fs/pstore` fue denegado (`could_not_run=1`); no hay record observado ni prueba de regresión/corrección vendor. El verificador específico de cierre, resolución OEM y recomendación probada siguen pendientes.

Evidencia: `docs/evidence/BB-INSTRUMENTS-kernel.md` y `tasks/evidence/BB-INSTRUMENTS-2026-10-03/kernel-capture.json`. Sigue abierta.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `privileged_access`.
- Impedimento: Lector local reportó /sys/fs/pstore denegado (CNR=1), cero registros observados; falta lectura real tras reboot y fuente vendor aplicable a la pila exacta.
- Evidencia faltante para cierre: Lector local reportó /sys/fs/pstore denegado (CNR=1), cero registros observados; falta lectura real tras reboot y fuente vendor aplicable a la pila exacta.
- Siguiente acción: Coordinación BB: recopilar fuente OEM/versiones y preparar lector; operador Luis: habilitar captura autorizada de pstore en canary y entregar identidad completa. Ref explícita: tasks/backlog/FORUM-02-PSTORE-KERNEL-REGRESSION.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/FORUM-02-PSTORE-KERNEL-REGRESSION.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FORUM-02-PSTORE-KERNEL-REGRESSION-direct-close-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FORUM-02-PSTORE-KERNEL-REGRESSION.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_03.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FORUM-02-PSTORE-KERNEL-REGRESSION-direct-close-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

El hilo es DGX Spark FE con kernel 1014; aqui kernel 6.17.0-1032 y OEM Gigabyte, sin exposicion demostrada. Lo util es la lectura de pstore tras un reinicio inesperado (bb recovery, kernel_capture existen) pero /sys/fs/pstore da Permiso denegado.

Version para un solo nodo Gigabyte AI TOP ATOM: Dar acceso de lectura a pstore (unit o sudoers de solo lectura) y registrar firmas FPAC/PSCI/SBSA tras cada reinicio no limpio en reboot_verdict; sin pinnear kernel.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Criterios ejecutables de `tools.verify_forum_finding` (2026-10-14)
Los criterios ejecutables de `tools.verify_forum_finding` se miden en esta ficha: su `close_check` corre ese verificador contra la captura real del sujeto. La meta-ficha `DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01`, que pedia implementarlos, se cerro el 2026-10-14 como `duplicate` (voto de Luis: consolidar en la ficha sujeto): el verificador existe y hoy, sin esa captura, sale con could_not_run (rc=2); conseguir la captura es trabajo de esta ficha.
