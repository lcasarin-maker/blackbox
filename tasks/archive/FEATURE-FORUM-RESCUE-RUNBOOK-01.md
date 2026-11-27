---
id: FEATURE-FORUM-RESCUE-RUNBOOK-01
kind: task
domain: RECOVERY
title: "Preparar acceso rescue.target y reversión de un servicio que impide arrancar"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FEATURE-FORUM-RESCUE-RUNBOOK-01 --evidence tasks/evidence/FEATURE-FORUM-RESCUE-RUNBOOK-01", "expect": "exit_zero", "porque": "Verificador propuesto pendiente: requiere evidencia del caso positivo, controles negativos, compatibilidad OEM y recuperación/rollback; la ficha registra trabajo abierto."}
---

## Trabajo en la ATOM

Runbook verificable para la ATOM: entrada a `rescue.target` por su UEFI, suspender una unidad canario con rename + sha256, medio de recuperacion con checksum y guarda de mountpoint/UUID del respaldo.

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/372358
- https://forums.developer.nvidia.com/t/368474
- https://forums.developer.nvidia.com/t/357487
- https://forums.developer.nvidia.com/t/366021
- https://forums.developer.nvidia.com/t/352528
- https://forums.developer.nvidia.com/t/nvidia-dgx-is-not-recognizing-my-usb-drive-for-recovery-file/363979
- https://forums.developer.nvidia.com/t/dgx-spark-system-recovery-completes-with-errors-then-boots-to-grub/
- https://forums.developer.nvidia.com/t/dgx-spark-shuts-down-within-minutes-after-os-reinstall-kernel-panic-during-first-boot-update/
- https://forums.developer.nvidia.com/t/msi-edgexpert-is-down/
- https://forums.developer.nvidia.com/t/dgx-spark-not-powering-on/
- https://forums.developer.nvidia.com/t/spark-cluster-pxe-boot-microtik-routeros-app/
- https://forums.developer.nvidia.com/t/monitor-doesnt-wake-up-from-sleep/
- https://forums.developer.nvidia.com/t/wake-on-lan-wol-on-dgx-spark/
- https://forums.developer.nvidia.com/t/dgx-spark-os-iso-download/348086
- https://forums.developer.nvidia.com/t/should-i-buy-asus-gx10-instead-nvidia-dgx-spark/347717/29
- https://forums.developer.nvidia.com/t/363536
- https://forums.developer.nvidia.com/t/unable-to-configure-the-ascent-gx10-on-first-startup/363805
- https://forums.developer.nvidia.com/t/364255
- https://forums.developer.nvidia.com/t/359198
- https://forums.developer.nvidia.com/t/347963
- https://forums.developer.nvidia.com/t/asus-gx10-iso-image/363185
- https://forums.developer.nvidia.com/t/request-dgx-spark-os-recovery-without-wiping-user-data/370981
- https://forums.developer.nvidia.com/t/recovery-from-kernel-panic-after-dashboard-update-unable-to-mount-root-fs-on-unknown-block-0-0/368939
- https://forums.developer.nvidia.com/t/348086/1
- https://forums.developer.nvidia.com/t/361008/1
- https://forums.developer.nvidia.com/t/364255/1
- https://forums.developer.nvidia.com/t/what-ive-learned-so-far-as-a-non-tech-day-1-dgx-spark-adopter/348169/1
- https://forums.developer.nvidia.com/t/request-dgx-spark-os-recovery-without-wiping-user-data/370981/1
- https://forums.developer.nvidia.com/t/dell-pro-max-version-of-spark/372358/1
- https://forums.developer.nvidia.com/t/347825/1
- https://forums.developer.nvidia.com/t/381099/1
- https://forums.developer.nvidia.com/t/365094/1
- https://forums.developer.nvidia.com/t/380326/1
- https://forums.developer.nvidia.com/t/375954

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Delta y prevención/resolución

Reutilizar systemd/GRUB y el plan de recuperación del gate de actualización; este entregable es un runbook verificable.

Documentar entrada nativa, disponibilidad de consola, autenticación y captura de journal. Identificar la unidad culpable; una suspensión usa rename con sha256, modo, caducidad y responsable, y restore verifica antes de tocar. Conservar datos y drivers.

## Validación, riesgo y cierre

Equipo canary Dell y otro OEM objetivo: entrar rescue, suspender exclusivamente una unidad canary, boot normal, restaurar y verificar. Señalar rutas OEM pendientes y posible ausencia de red en rescue. No generalizar F7/ESC.

El verificador de close_check todavía debe implementarse; ejecutar esta ficha exige evidencia adicional y deja registradas las consultas que no pueden correr. Ningún cambio del host se aplica al registrar la propuesta. Detalle fuente preservado en tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_*.json y threads/.

### Reparación que conserve datos: brecha pendiente, propuesta no validada

Investigar primero capacidades OEM existentes. Para una ruta futura, capturar estado de boot/paquetes, validar por lectura el disco y las particiones objetivo, ofrecer acceso de datos read-only/copia verificable y probar reparación de initramfs antes de reinstalar. Previsualizar alcance y separar la acción destructiva. No crear particiones, tocar GRUB o ejecutar chroot/repair scripts a partir del strawman del foro. Cierre requiere matriz de fallos en imágenes desechables y con datos centinela por OEM, verificación de hash preservado, negativo de disco/partición destino, boot posterior, rollback y aprobación del soporte OEM. Hasta entonces la ficha registra una capacidad pendiente, no una función soportada.

## Nota de instrumentación readonly (2026-10-03)

Se reutilizó la captura existente de sesiones/servicios; no se entró a rescue.target ni se probó reversión de servicios. La ficha sigue abierta. Evidencia y límites: `docs/evidence/BB-INSTRUMENTS-boot.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: La barrera protectora de destino vacío/UUID y fixtures de disco ausente se puede completar localmente; los casos OEM concretos quedan etiquetados aparte.
- Evidencia faltante para cierre: La barrera protectora de destino vacío/UUID y fixtures de disco ausente se puede completar localmente; los casos OEM concretos quedan etiquetados aparte.
- Siguiente acción: Coordinación BB: implementar/verificar las guardas de mountpoint, identidad UUID y abort seguro usando fixture ausente/incorrecto. Ref explícita: tasks/backlog/FEATURE-FORUM-RESCUE-RUNBOOK-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/FEATURE-FORUM-RESCUE-RUNBOOK-01.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FEATURE-FORUM-RESCUE-RUNBOOK-01-direct-close-current.log.
- Responsable del siguiente paso: Coordinación BB; para recuperación de históricos, custodio del artifact store si corresponde..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FEATURE-FORUM-RESCUE-RUNBOOK-01.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_00.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FEATURE-FORUM-RESCUE-RUNBOOK-01-direct-close-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

Ficha de 21 KB con casos Dell/ASUS/MSI/HP y multinodo; para esta Gigabyte con DGX OS 7.2.3 aplica la parte de rescue.target, captura previa al reset, medio de recuperacion verificado y guarda de mountpoint. bb recovery (tools/recovery_profile.py) cubre solo RCU/watchdog/pstore.

Version para un solo nodo Gigabyte AI TOP ATOM: Reducir a un runbook verificable para la ATOM Gigabyte: entrada a rescue.target por su UEFI, suspender una unidad canary con rename+sha256, medio de recuperacion con checksum, y guarda de mountpoint/UUID de respaldo; descartar casos OEM ajenos y multinodo.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Criterios ejecutables de `tools.verify_forum_finding` (2026-10-14)
Los criterios ejecutables de `tools.verify_forum_finding` se miden en esta ficha: su `close_check` corre ese verificador contra la captura real del sujeto. La meta-ficha `DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01`, que pedia implementarlos, se cerro el 2026-10-14 como `duplicate` (voto de Luis: consolidar en la ficha sujeto): el verificador existe y hoy, sin esa captura, sale con could_not_run (rc=2); conseguir la captura es trabajo de esta ficha.
