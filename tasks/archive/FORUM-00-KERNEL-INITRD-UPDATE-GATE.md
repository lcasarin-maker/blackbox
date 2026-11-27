---
id: FORUM-00-KERNEL-INITRD-UPDATE-GATE
kind: task
domain: KERNEL
title: "Validar módulos e initramfs antes de reiniciar tras una actualización DGX OS"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FORUM-00-KERNEL-INITRD-UPDATE-GATE --evidence tasks/evidence/FORUM-00-KERNEL-INITRD-UPDATE-GATE", "expect": "exit_zero", "porque": "Demostrar un gate previo al reboot que detecta estado dpkg/DKMS incoherente, ausencia de initrd/módulo para el kernel objetivo y una recuperación arrancable; incluir negativos de kernel sano y rollback."}
---

## Trabajo en la ATOM

Antes de reiniciar tras una actualizacion de kernel, `tools/update_boot_coherence.py` verifica dpkg, modulo NVIDIA del kernel objetivo, vmlinuz/initrd no vacios y entrada de arranque; falta la prueba de arranque del kernel objetivo con su recuperacion.

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/dgx-spark-kernel-panic-after-oobe-update-missing-initrd-for-7-0-0-1019-nvidia-and-dkms-arm64-aarch64-conflict/383450
- https://forums.developer.nvidia.com/t/kernel-panic-on-dell-pro-max-gb10-after-update/383505
- https://forums.developer.nvidia.com/t/latest-update-pulls-in-mis-matched-kernal-driver/383312
- https://forums.developer.nvidia.com/t/dgx-spark-regression-after-updating-to-kernel-7-0-0-1019-nvidia-gdm-no-longer-boots-correctly-fixed/383563
- https://forums.developer.nvidia.com/t/three-dgx-dashboard-update-problems-with-a-working-reference-implementation/384257
- https://forums.developer.nvidia.com/t/dgx-spark-update-advisory/383254
- https://forums.developer.nvidia.com/t/dgx-spark-capsule-firmware-update-blocked-by-uefi-administrator-password-never-set/380503
- https://forums.developer.nvidia.com/t/how-to-solve-the-problem-that-dgx-spark-automatically-enters-bios-upon-startup/368301
- https://forums.developer.nvidia.com/t/lets-optimize-nvidia-glm-5-3-flash-nvfp4-for-2x-dgx-spark/382939/69
- https://forums.developer.nvidia.com/t/374224
- https://forums.developer.nvidia.com/t/383464
- https://forums.developer.nvidia.com/t/352228
- https://forums.developer.nvidia.com/t/365280
- https://forums.developer.nvidia.com/t/374930
- https://nvidia.custhelp.com/app/answers/detail/a_id/5835
- https://forums.developer.nvidia.com/t/368678
- https://forums.developer.nvidia.com/t/383222
- https://forums.developer.nvidia.com/t/364160
- https://forums.developer.nvidia.com/t/371537
- https://forums.developer.nvidia.com/t/348195
- https://forums.developer.nvidia.com/t/kernel-hang-on-large-nvme-writes-ext4-soft-lockup-in-ext4-buffered-write-iter-bug-at-inode-c-2176-asus-ascent-gx10-kernel-6-17-0-1014-nvidia/367605
- https://forums.developer.nvidia.com/t/dgx-spark-runs-hot-and-firmware-update-keeps-repeating/370198
- https://forums.developer.nvidia.com/t/what-is-test-img-on-the-root-filesystem/
- https://forums.developer.nvidia.com/t/one-of-my-two-dgx-sparks-bricked-after-update/349491
- https://forums.developer.nvidia.com/t/dgx-spark-nvidia-driver-issue/351828
- https://forums.developer.nvidia.com/t/366300
- https://forums.developer.nvidia.com/t/dgx-spark-stuck-in-boot-loop-after-first-update-cannot-access-uefi-bios-or-boot-recovery-usb/370503
- https://forums.developer.nvidia.com/t/uefi-firmware-upgrade-failing-constantly/369572
- https://forums.developer.nvidia.com/t/dgx-spark-capsule-firmware-update-blocked-by-uefi-administrator-password-never-set/380503/1
- https://forums.developer.nvidia.com/t/349491/1
- https://forums.developer.nvidia.com/t/351828/1
- https://forums.developer.nvidia.com/t/370503/1
- https://forums.developer.nvidia.com/t/376981/1
- https://forums.developer.nvidia.com/t/379141/1
- https://forums.developer.nvidia.com/t/383118/1
- https://forums.developer.nvidia.com/t/374985/1
- https://forums.developer.nvidia.com/t/365116/1
- https://forums.developer.nvidia.com/t/368939/1
- https://forums.developer.nvidia.com/t/uefi-firmware-upgrade-failing-constantly/369572/1
- https://forums.developer.nvidia.com/t/383926
- https://forums.developer.nvidia.com/t/369711
- https://forums.developer.nvidia.com/t/copyfail-dirtyfrag-lpe-kernel-patches/369489
- https://ubuntu.com/blog/copy-fail-vulnerability-fixes-available
- https://lists.ubuntu.com/archives/noble-changes/2026-May/055912.html

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Hueco y prevención

Un chequeo de salud posterior al arranque llega tarde si el próximo kernel no puede montar root. Evaluar un preflight de transacción/reinicio que, para la versión kernel objetivo, verifique estado consistente de dpkg, provider de módulos NVIDIA instalado, módulo construido/firmado compatible con Secure Boot, `vmlinuz` e initrd presentes/no vacíos, y disponibilidad real de un kernel anterior arrancable. Aprovechar paquetes de módulos precompilados firmados cuando el proveedor confirme compatibilidad. La receta NVIDIA es específica de ese stack; no purgar DKMS ni instalar paquetes a ciegas en otros OEM.

El host Blackbox observado por el coordinador estaba en `6.17.0-1032-nvidia`, con `linux-modules-nvidia-580-open-nvidia-hwe24.04 7.0.0-1019.19~24.04.2+1` instalado y `nvidia-dkms-580-open` ausente; initrd y vmlinuz de kernels 6.11, 6.17 y 7.0 estaban presentes. Esta diferencia local prueba que el sistema inspeccionado no coincide con el estado DKMS reportado, no demuestra que el gate sea innecesario para futuras actualizaciones.

## Riesgo y cierre

Un gate mal diseñado puede impedir una actualización arrancable por falsos positivos de DKMS frente a módulos built-in, Secure Boot u OEM. Antes de cualquier reinicio, la comprobación debe dejar el sistema sin cambios; las correcciones requieren confirmación de paquetes/versiones compatibles y plan explícito para conservar el kernel anterior. Probar fixtures de DKMS roto, módulo firmado válido, Secure Boot, initrd ausente/vacío, paquetes a medio configurar y kernel sano; ensayo de update en equipo de laboratorio identificado; reboot solo tras copia/recuperación verificada; rollback al kernel anterior y captura de resultado. Registrar versiones completas de OS, kernel, OEM, firmware, driver y origen del paquete. Relacionar este gate con `FEATURE-USB-HID-POSTUPDATE-CHECK`, que cubre pérdida de acceso HID tras actualizaciones, sin duplicar su comprobación de entrada USB.

## Progreso de preflight (2026-10-02)

Se implementó `python3 -m tools.preflight kernel <snapshot.json>` para exigir dpkg/APT coherentes, vmlinuz e initrd, módulo firmado y kernel anterior arrancable. `dpkg --audit` está vacío; los archivos de arranque 6.11, 6.17 y 7.0 existen; Secure Boot está habilitado; el módulo NVIDIA de 7.0.0-1019 tiene vermagic AArch64 y `modinfo` reporta `Canonical Ltd. Kernel Module Signing`; la confianza/enrollment no se comprobó por separado. El kernel activo 6.17.0-1032 ya arrancó. `apt-get check` no pudo obtener el lock, así que el resultado queda `unknown`. Comandos y salidas literales: `tasks/evidence/FORUM-00-KERNEL-INITRD-UPDATE-GATE/commands.json`; evaluación: `preflight.json` y `validator-run.json`.

La ficha sigue abierta: falta `apt-get check` con privilegio válido y un ensayo de update/selección de recuperación/rollback en laboratorio OEM. No se reinició ni se modificó el estado de paquetes.

## Nota de instrumentación readonly (2026-10-03)

Se registró el kernel en ejecución y presencia de sus archivos vmlinuz/initrd; presencia no acredita paquete coherente ni bootability y no se evaluó kernel objetivo de actualización. Evidencia: `tasks/evidence/BB-INSTRUMENTS-2026-10-03/boot.capture.json` y `docs/evidence/BB-INSTRUMENTS-boot.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `privileged_access`.
- Impedimento: La ficha declara pendientes apt-get check con privilegio válido y ensayo de actualización/selección de recuperación/rollback; no hay autorización/acceso root ni laboratorio OEM para esos pasos.
- Evidencia faltante para cierre: La ficha declara pendientes apt-get check con privilegio válido y ensayo de actualización/selección de recuperación/rollback; no hay autorización/acceso root ni laboratorio OEM para esos pasos.
- Siguiente acción: Coordinación BB: preparar el protocolo y recopilar fuente de compatibilidad OEM; operador Luis: habilitar ventana/lab y ejecutar con privilegio y rollback comprobado. Ref explícita: tasks/backlog/FORUM-00-KERNEL-INITRD-UPDATE-GATE.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/FORUM-00-KERNEL-INITRD-UPDATE-GATE.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FORUM-00-KERNEL-INITRD-UPDATE-GATE-direct-close-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FORUM-00-KERNEL-INITRD-UPDATE-GATE.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_00.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FORUM-00-KERNEL-INITRD-UPDATE-GATE-direct-close-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Avance 2026-10-13: observaciones de solo lectura
`tasks/evidence/FORUM-00-KERNEL-INITRD-UPDATE-GATE/observaciones-solo-lectura-20261013.txt`: `dpkg --audit` vacio, `apt-get -s check` rc 0, modulo firmado 580.178.04, initrd y vmlinuz del 6.17.0-1032 presentes y no vacios, y la sonda `arranque_tras_actualizacion` con `dpkg_consistente: True`. Hallazgo: `GRUB_DEFAULT` esta FIJADO a `6.17.0-1032-nvidia`; el 7.0.0-1019 esta instalado pero no arranca solo (NVIDIA avisa de una regresion en ese kernel, hilo 383185). Limite de la sonda, a corregir: `kernel_nuevo` toma el kernel mas alto instalado (7.0.0-1019) y no el que GRUB arrancara. Sigue abierta: falta la prueba de arranque del kernel anterior tras un reinicio y el caso negativo de un incidente real.
Corregido el limite de la sonda (2026-10-13): `arranque_tras_actualizacion` evalua ahora el kernel que `GRUB_DEFAULT` fija (`kernel_grub`), y el mas alto instalado solo si GRUB no fija ninguno; test con control negativo en `tests/test_huella_host.py`.

## Criterios ejecutables de `tools.verify_forum_finding` (2026-10-14)
Los criterios ejecutables de `tools.verify_forum_finding` se miden en esta ficha: su `close_check` corre ese verificador contra la captura real del sujeto. La meta-ficha `DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01`, que pedia implementarlos, se cerro el 2026-10-14 como `duplicate` (voto de Luis: consolidar en la ficha sujeto): el verificador existe y hoy, sin esa captura, sale con could_not_run (rc=2); conseguir la captura es trabajo de esta ficha.

## Avance 2026-10-16: el gate ya puede cerrar; falta solo la prueba de arranque
`tools/update_boot_coherence.py` (solo lectura) recaptura `commands.json`/`preflight.json` para el kernel objetivo `7.0.0-1019-nvidia` (instalado, no fijado en GRUB) con previo `6.17.0-1032-nvidia`: `dpkg --audit` vacio, `apt-get -s check` rc 0 (simulacion, sin lock: el hueco `apt_check` de 2026-10-02 queda cubierto), vmlinuz/initrd no vacios, modulo `nvidia` del objetivo con vermagic propio y firma `Canonical Ltd. Kernel Module Signing`, Secure Boot habilitado. El verificador ahora deriva el snapshot de las filas crudas (un snapshot registrado que las contradiga da `fail`), exige que el gate bloquee siete negativos de incidente construidos mutando esas filas (dpkg a medio configurar, dependencias rotas, vmlinuz ausente, initrd vacio, modulo sin firmar con Secure Boot, modulo de otro kernel, sin kernel previo; un gate ciego a cualquiera da `fail`) y solo da `pass` con `recovery-trial.json`: tres arranques con boot_id distinto, el ultimo y el primero en el kernel previo y el del medio en otro kernel elegido a mano. Antes de este cambio el verificador no tenia ninguna ruta a `pass` (terminaba siempre en `unknown`). Tests: `tests/test_update_boot_coherence.py` (sano, 7 negativos, prueba rota en 5 formas, gate ciego por mutacion, snapshot mentiroso, captura sin hostname).
Disparador (Luis, consola local): `python3 -m tools.update_boot_coherence trial --phase antes --out tasks/evidence/FORUM-00-KERNEL-INITRD-UPDATE-GATE`; `sudo grub-reboot "Advanced options for DGX OS GNU/Linux>DGX OS GNU/Linux, with Linux 6.11.0-1016-nvidia" && sudo reboot` (o elegir 6.11 a mano en el menu GRUB; el nombre de la entrada se infiere de `GRUB_DEFAULT`, `grub.cfg` es 0600 root); tras arrancar, `... trial --phase recuperacion ...` y `sudo reboot`; tras volver a 6.17, `... trial --phase restaurado ...`; despues el close_check.
