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

## Fallo observado

En el hilo [NVIDIA 383450](https://forums.developer.nvidia.com/t/dgx-spark-kernel-panic-after-oobe-update-missing-initrd-for-7-0-0-1019-nvidia-and-dkms-arm64-aarch64-conflict/383450), DGX Spark con DGX OS sobre Ubuntu 24.04, kernel nuevo `7.0.0-1019-nvidia`, driver `580.178.04`, Secure Boot habilitado y `nvidia-dkms-580-open` quedó sin `initrd.img-7.0.0-1019-nvidia` tras update/OOBE. El kernel anterior `6.17.0-1014-nvidia` seguía siendo arrancable. El autor relaciona la configuración DKMS fallida con las cadenas de arquitectura `arm64` y `aarch64`; el reporte describe el estado, pero la causa interna no está confirmada independientemente.

NVIDIA indicó que distribuía una mitigación y publicó recuperación: instalar `linux-modules-nvidia-580-open-nvidia-hwe-24.04` y retirar `nvidia-dkms-580-open` en la misma transacción para que el módulo firmado reemplace al proveedor DKMS; revisar `dpkg --audit`, `apt-get check` y que el initrd exista antes de reiniciar. Un usuario confirmó que resolvió su máquina. La recuperación desde VFS panic requirió arrancar manualmente el kernel anterior desde la consola GRUB; el usuario no pudo obtener shell con la consola de live USB. Versión exacta de OEM/BIOS no indicada.

## Hueco y prevención

Un chequeo de salud posterior al arranque llega tarde si el próximo kernel no puede montar root. Evaluar un preflight de transacción/reinicio que, para la versión kernel objetivo, verifique estado consistente de dpkg, provider de módulos NVIDIA instalado, módulo construido/firmado compatible con Secure Boot, `vmlinuz` e initrd presentes/no vacíos, y disponibilidad real de un kernel anterior arrancable. Aprovechar paquetes de módulos precompilados firmados cuando el proveedor confirme compatibilidad. La receta NVIDIA es específica de ese stack; no purgar DKMS ni instalar paquetes a ciegas en otros OEM.

El host Blackbox observado por el coordinador estaba en `6.17.0-1032-nvidia`, con `linux-modules-nvidia-580-open-nvidia-hwe24.04 7.0.0-1019.19~24.04.2+1` instalado y `nvidia-dkms-580-open` ausente; initrd y vmlinuz de kernels 6.11, 6.17 y 7.0 estaban presentes. Esta diferencia local prueba que el sistema inspeccionado no coincide con el estado DKMS reportado, no demuestra que el gate sea innecesario para futuras actualizaciones.

## Riesgo y cierre

Un gate mal diseñado puede impedir una actualización arrancable por falsos positivos de DKMS frente a módulos built-in, Secure Boot u OEM. Antes de cualquier reinicio, la comprobación debe dejar el sistema sin cambios; las correcciones requieren confirmación de paquetes/versiones compatibles y plan explícito para conservar el kernel anterior. Probar fixtures de DKMS roto, módulo firmado válido, Secure Boot, initrd ausente/vacío, paquetes a medio configurar y kernel sano; ensayo de update en equipo de laboratorio identificado; reboot solo tras copia/recuperación verificada; rollback al kernel anterior y captura de resultado. Registrar versiones completas de OS, kernel, OEM, firmware, driver y origen del paquete. Relacionar este gate con `FEATURE-USB-HID-POSTUPDATE-CHECK`, que cubre pérdida de acceso HID tras actualizaciones, sin duplicar su comprobación de entrada USB.

## Fuentes y alcance consolidados del lote 02

Esta ficha concentra también la propuesta `FORUM-02-OTA-KERNEL-DRIVER-GATE`,
conservada en la evidencia del swarm como propuesta fusionada. Hay un solo
entregable de coherencia de actualización y arranque.

- [383505, Dell Pro Max GB10](https://forums.developer.nvidia.com/t/kernel-panic-on-dell-pro-max-gb10-after-update/383505): VFS panic tras Dashboard; NVIDIA pide comprobar dpkg, dependencias e initrd antes del reboot. La atribución a initrd ausente requiere evidencia del equipo afectado.
- [383312, actualización kernel/driver](https://forums.developer.nvidia.com/t/latest-update-pulls-in-mis-matched-kernal-driver/383312): rechazo de módulos DKMS por Secure Boot y paquetes incompletos; el rollback descrito se simuló y quedó sin ejecutar.
- [383563, GDM y librería ausente](https://forums.developer.nvidia.com/t/dgx-spark-regression-after-updating-to-kernel-7-0-0-1019-nvidia-gdm-no-longer-boots-correctly-fixed/383563): `nvidia-persistenced` falla por `libnvidia-cfg.so.1`; un usuario migra a 595, que NVIDIA declara sin soporte para Spark en ese hilo. Una GPU enumerada por `nvidia-smi` deja pendientes la carga real, persistenced y el escritorio.
- [384257, problemas del actualizador](https://forums.developer.nvidia.com/t/three-dgx-dashboard-update-problems-with-a-working-reference-implementation/384257): relato de snapshot de actualizaciones obsoleto, reinicio forzado y firmware cuya versión física permanece igual pese al mensaje de éxito. La herramienta comunitaria enlazada requiere revisión propia antes de adopción.
- [383254, advisory NVIDIA](https://forums.developer.nvidia.com/t/dgx-spark-update-advisory/383254): advertencia para multi-nodo NCCL/RoCE en `7.0.0-1019-nvidia`, workaround `kho=off` y anuncio posterior de mitigaciones. Verificar el estado soportado actual por OEM y workload, preservando fecha y versión de la recomendación.
- [380503, cápsula bloqueada por password UEFI](https://forums.developer.nvidia.com/t/dgx-spark-capsule-firmware-update-blocked-by-uefi-administrator-password-never-set/380503): actualización detenida; soporte dirige a RMA. Conservar el estado y una salida soportada; cualquier bypass de autenticación queda fuera de esta propuesta.

Ampliar el preflight con la simulación APT, identidad activa/candidata de
kernel y módulos, firma y enrollment cuando corresponda, fuente de soporte
OEM y recuperación accesible. Verificar después del arranque el módulo real,
el acceso GPU del workload, persistenced y GDM según el perfil de uso. Comparar
firmware físico con historial fwupd; registrar GUID/PSID y componentes SoC,
EC y USB-PD por separado. La evidencia de un Spark FE requiere validación
propia antes de recomendar un cambio en otro OEM.

Controles adicionales: módulo para otro kernel, firma sin enrollment,
dependencias incompletas, biblioteca de usuario ausente, firmware que conserva
la versión y receta de driver fuera de soporte. Cada consulta ilegible cuenta
como `could_not_run`; la compatibilidad pendiente mantiene esa parte abierta.
Las correcciones en laboratorio deben preservar Secure Boot, la recuperación
del sistema y el estado anterior; los cambios temporales llevan responsable,
caducidad y vigilancia según el contrato de suspensión del proyecto.

## Reinicio y recuperación operables

[374224](https://forums.developer.nvidia.com/t/374224) relata reinicios durante cómputo sin identificar actor ni logs. Correlacionar actor/boot-cause y workload activo antes de atribuirlo a OTA; probar ventana de mantenimiento y veto de reboot con trabajo activo en el actualizador soportado. Incorporar preparación de medio oficial con versión/hash y prueba OEM de consola/entrada; OOBE recuperado mediante nueva imagen (347825/347951/347962/348223) deja pendiente aislar causa. El runbook rescue.target se registra en FEATURE-FORUM-RESCUE-RUNBOOK-01; conservar kernels/datos y comprobar que el camino de recuperación realmente arranca.

[383464](https://forums.developer.nvidia.com/t/383464) añade kernel FIPS6.8 desde Ubuntu Pro y login bloqueado; el autor regresó desde GRUB a kernel7 y NVIDIA declara kernel FIPS incompatible con Spark en ese hilo. Verificar soporte explícito para el kernel/OEM: compilar FIPS por cuenta propia o usar wolfSSL no demuestra equivalencia de compliance ni recuperación del host.

## Provisioning y coherencia de fuentes

[352228](https://forums.developer.nvidia.com/t/352228) relata Signed-By conflict al instalar repo CUDA13.0.2 sobre DGX y restauración al retirar la fuente duplicada. Validar fuentes/keyrings idempotentes y proveedor DGX antes de recomendar instalador local; conservar ficheros, hash/modo y rollback verificable. [365280](https://forums.developer.nvidia.com/t/365280) combina apt upgrade/kernel6.17 y driver570-server fuera de soporte con EFI stub hangs y recovery fallido; la mezcla reportada requiere evidencia de paquetes para atribuir causa.

[374930](https://forums.developer.nvidia.com/t/374930) enlaza el [advisory oficial CVE-2026-24218](https://nvidia.custhelp.com/app/answers/detail/a_id/5835): claves SSH e identidad clonadas en imágenes previas a OTA0. Verificar actualización soportada y unicidad de identidad del canal de recuperación cuando haya golden image o varios hosts; una instalación moderna no prueba automáticamente qué identidad heredó. No exportar claves privadas ni regenerar identificadores de un host remoto a ciegas: preservar autenticación, known_hosts y consola de recuperación. Este subcaso protege la confianza del acceso de diagnóstico, con referencia de mitigación oficial y sin auditoría de seguridad general añadida.

[368678](https://forums.developer.nvidia.com/t/368678) reporta Dell BIOS5.36_2.1.0 con dos fechas de build: unidad09/23 congela prefill200k4/4 y otra10/08 pasa0/2, mismo kernel6.17-1014/driver580.142/modelo según autor. fwupd no ofrecía actualización a la primera; mem_desc1359 apareció en un incidente anterior. Registrar fecha/build/identidad física además de versión string y usar reproducer de largo contexto en el gate, sin atribuir causalidad al BIOS desde unidades diferentes ni flashear firmware FE en Dell. Falta fix disponible/confirmación del fabricante.

[383222](https://forums.developer.nvidia.com/t/383222) añade regresión de presupuesto en DGX OS 7.5 OTA: kernel 7.0.0-1019/UEFI 5.36_0ACUM027 presentó 7.20 GiB menos RAM disponible en nueve boots; otro FE con el mismo UEFI y kernel 6.17 mostró ~9.3 GiB más disponible/CMA 128 MiB. NVIDIA atribuye parte de la reserva a KHO habilitado en la actualización y dice que se distribuye mitigación. Registrar memoria/reserved/CMA antes y después junto a kernel/UEFI; verificar mitigación en cada OEM y versión. No recomendar `kho=off`, `cma=` ni rollback manual a partir del foro.

[364160](https://forums.developer.nvidia.com/t/364160) añade cápsula ASUS Ascent GX10 v0103 (SoC 0x305, EC 2.78.18.3, USB-PD 5.7, TPM 7.2.4.1): el Dashboard dejó una cápsula USB-PD fallida en dos unidades; el autor informa que ASUS Support indicó usar el `capsule_update.sh` incluido en su ZIP oficial y que el readback de BIOS confirmó versión. Link speed y temperatura mejorados son observaciones sin A/B controlado; otra unidad reporta menor consumo/temperatura sin metodología. Añadir readback por componente y gate/rollback OEM. No convertir la invocación shell ni diferencias térmicas/velocidad en recomendación global.

[371537](https://forums.developer.nvidia.com/t/371537) reports an MSI EdgeXpert USB-PD firmware defect associated with a 600 MHz GPU cap; an owner says an incorrect DGX Dashboard capsule corrupted EC and the correct capsule appeared on LVFS weeks later. Exact component versions and logs are missing. Keep this as an OEM/component-specific case: preflight compatible EC/PD capsule identity, read back physical versions and validate GPU clocks before closing; never cross-flash a Founders Edition payload into an OEM.

[348195](https://forums.developer.nvidia.com/t/348195) reports CUDA 12 replacing the supplied CUDA 13 stack, then CUDA 13 `dpkg` overwrite conflicts. The owner says `--override` and Secure Boot MOK enrollment restored driver installation, but exact command, key/provider and package transaction are absent. Do not copy this workaround globally; extend package preflight with dpkg conflict and Secure Boot enrollment state, and use the signed OEM-supported modules/recovery route.

[367605](https://forums.developer.nvidia.com/t/kernel-hang-on-large-nvme-writes-ext4-soft-lockup-in-ext4-buffered-write-iter-bug-at-inode-c-2176-asus-ascent-gx10-kernel-6-17-0-1014-nvidia/367605) reports an ASUS Ascent GX10 (NVMe ESL01TBTLCZ-27J2-TYN, firmware ERFM12.0), kernel 6.17.0-1014-nvidia/driver 580.142, hard ext4 BUG during ≥10GB buffered writes and an indefinite ext4 soft lockup. The owner reports healthy NVMe SMART/fsck; NVIDIA did not reproduce and requested kernel logs/bug report plus FieldDiag. This is not yet an established kernel regression. Add large-file filesystem write soak and post-hard-reset integrity checks to a canary update acceptance test; preserve the prior bootable kernel and data. Do not recommend XFS, O_DIRECT or lower parallelism until tested on supported OEM/kernel combinations. The topic text contains placeholders for some direct-I/O results and its proposed cause remains the owner's hypothesis.

[370198](https://forums.developer.nvidia.com/t/dgx-spark-runs-hot-and-firmware-update-keeps-repeating/370198) adds a distinct update-state control: Dashboard repeated the same firmware update five times on one of two FE units, while CLI `apt dist-upgrade` and `fwupdmgr refresh/upgrade` reportedly completed it. The unit remained 10–15°C hotter at idle despite FieldDiag r9.257.3 PASS. Require component version inventory and before/after verification to establish update completion; a PASS does not close a thermal report. The diagnostic output is in the body; comparison images are unread.

## Progreso de preflight (2026-10-02)

Se implementó `python3 -m tools.preflight kernel <snapshot.json>` para exigir dpkg/APT coherentes, vmlinuz e initrd, módulo firmado y kernel anterior arrancable. `dpkg --audit` está vacío; los archivos de arranque 6.11, 6.17 y 7.0 existen; Secure Boot está habilitado; el módulo NVIDIA de 7.0.0-1019 tiene vermagic AArch64 y `modinfo` reporta `Canonical Ltd. Kernel Module Signing`; la confianza/enrollment no se comprobó por separado. El kernel activo 6.17.0-1032 ya arrancó. `apt-get check` no pudo obtener el lock, así que el resultado queda `unknown`. Comandos y salidas literales: `tasks/evidence/FORUM-00-KERNEL-INITRD-UPDATE-GATE/commands.json`; evaluación: `preflight.json` y `validator-run.json`.

La ficha sigue abierta: falta `apt-get check` con privilegio válido y un ensayo de update/selección de recuperación/rollback en laboratorio OEM. No se reinició ni se modificó el estado de paquetes.

[348942](https://forums.developer.nvidia.com/t/what-is-test-img-on-the-root-filesystem/) documents a 10GB `/test.img` found on several owner Spark installs; a responder says it is not in DGX OS/recovery and attributes it to a factory QA script left behind. This is owner/support testimony rather than a checked image manifest. Include root-filesystem headroom in pre-update checks and, if this exact artifact appears, identify it and preserve/hash it before any operator-approved cleanup. Never delete an arbitrary `test.img` solely by name.

[349491](https://forums.developer.nvidia.com/t/one-of-my-two-dgx-sparks-bricked-after-update/349491) reports an automatic update followed by intermittent boot/video failure; one FE entered the OS only by opening UEFI and selecting “Save Changes & Exit,” then went to RMA. A second owner says a reinstall restored service for days before the blank screen returned; community suggestions to purge GDM or drain standby power are not validated fixes. Gate update completion on direct cold boot, another warm boot, display, SSH and GPU checks; preserve logs and firmware/build data before recovery.

[351828](https://forums.developer.nvidia.com/t/dgx-spark-nvidia-driver-issue/351828) reports `nvidia-smi` unable to reach the driver after dashboard updates on DGX OS 7.2.3 build 2025-09-10/commit 833b4a7, driver 580.95.05, Secure Boot active. A later OTA identity appeared but did not resolve the report; the owner says disabling Secure Boot was their solution without posting a successful post-change driver check. Include signed-module/Secure Boot state and `nvidia-smi` in the update acceptance gate. Preserve Secure Boot policy; the forum report does not validate disabling it as an OEM fix.


[366300](https://forums.developer.nvidia.com/t/366300) aporta un caso Lenovo ThinkStation PGX: el Dashboard pareció quedar detenido en dos intentos de firmware y las versiones seguían EC 2.66.3 / UEFI 2.0.11, aunque `LastAttemptStatus=0x0`. El dueño confirmó éxito cuando conectó monitor y teclado e inició localmente la actualización: EC 2.78.24 / UEFI 2.0.12. El gate debe registrar componente/versión antes y después y comprobar progreso/arranque; el caso no valida que monitor/teclado resuelva otros OEM ni que el estado 0 implique versión aplicada.

[370503](https://forums.developer.nvidia.com/t/dgx-spark-stuck-in-boot-loop-after-first-update-cannot-access-uefi-bios-or-boot-recovery-usb/370503) reports a first-boot automatic update followed by an overnight NVIDIA-logo loop; the owner could no longer reach UEFI or boot a prepared official recovery USB. NVIDIA staff restated UEFI defaults, factory Secure Boot keys and Boot Override as the documented route, warned against interrupting initial updates, and recommends support/RMA when UEFI is inaccessible. A second owner says removing USB devices/hub stopped a similar loop, with no confirmation from the original. Add first-OTA completion and recovery-entry checks to the gate; peripheral isolation stays a test control, not a diagnosis.
