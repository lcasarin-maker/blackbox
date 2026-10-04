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

## Fuente y evidencia

[372358](https://forums.developer.nvidia.com/t/372358). Un dueño Dell Pro Max dice F7→ESC→GRUB y systemd.unit=rescue.target permitieron desactivar un servicio rogue. El servicio y causa quedan sin identificar; las teclas dependen de OEM.

## Delta y prevención/resolución

Reutilizar systemd/GRUB y el plan de recuperación del gate de actualización; este entregable es un runbook verificable.

Documentar entrada nativa, disponibilidad de consola, autenticación y captura de journal. Identificar la unidad culpable; una suspensión usa rename con sha256, modo, caducidad y responsable, y restore verifica antes de tocar. Conservar datos y drivers.

## Validación, riesgo y cierre

Equipo canary Dell y otro OEM objetivo: entrar rescue, suspender exclusivamente una unidad canary, boot normal, restaurar y verificar. Señalar rutas OEM pendientes y posible ausencia de red en rescue. No generalizar F7/ESC.

El verificador de close_check todavía debe implementarse; ejecutar esta ficha exige evidencia adicional y deja registradas las consultas que no pueden correr. Ningún cambio del host se aplica al registrar la propuesta. Detalle fuente preservado en tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_*.json y threads/.

[368474](https://forums.developer.nvidia.com/t/368474) añade red/LACP precediendo GUI UnexpectedError y TTY2 sin shell; GRUBrecovery sugerido sin éxito confirmado. [357487](https://forums.developer.nvidia.com/t/357487) aporta dependencia NFS en boot y participante advierte fstab sin nofail puede impedir arranque. Probar consola/rescue y retorno ante dependencia de red caída; no modificar mount policy sin identificar su criticidad. En multinodo, [366021](https://forums.developer.nvidia.com/t/366021) relata powercycle de otros tres nodos al colgar uno: definir target por nodo y capturar primero si es accesible; el relato no valida ese alcance como recuperación correcta ni WoL.

[352528](https://forums.developer.nvidia.com/t/352528) reports the recovery image can ignore Enter/Esc from some keyboards even when the keyboard works in BIOS; Apple wired Magic Keyboard and Cherry Stream 3.0 are named, while a generic USB-A keyboard through USB-C adapter works for one owner. Another setup mouse failure cleared with a generic mouse. NVIDIA did not reproduce the Apple case. The report includes an official remote-network setup path. Preserve an alternative setup/recovery route and verify exact HID model, adapter/hub and recovery-image version before treating the unit as bricked; this is a compatibility report, not a universal keyboard rule.

[363979](https://forums.developer.nvidia.com/t/nvidia-dgx-is-not-recognizing-my-usb-drive-for-recovery-file/363979) distinguishes copying a recovery archive from preparing boot media: a response points to the official `CreateUSBKeyMacOS.sh` inside the recovery image, which creates a BOOTME MBR/FAT32 partition, copies the `usb/` directory and writes a recovery marker. The script prompts before erasing the selected external disk. A later post refers to image 1.120.38 and UEFI “DGX OS Recovery” validation, but the owner does not confirm a successful reinstall. Document exact image/version, checksum and official media script; require disk identity plus destructive confirmation and verify boot recognition before recovery. Do not automate formatting.

[372713](https://forums.developer.nvidia.com/t/dgx-spark-system-recovery-completes-with-errors-then-boots-to-grub/) reports recovery reaching “completed” despite `e2fsck: aborted`, `resize2fs` inode-bitmap checksum mismatch and missing root/grub files, followed by a `grub>` prompt. The same failure reportedly occurred with macOS and Windows recovery-media scripts; UEFI NVMe extended self-test passed and the supplier planned inspection. Treat completion text as insufficient: check recovery logs for filesystem mount, `fstab` and `grub.cfg` creation, then boot-verify before declaring recovery done. Screenshot evidence is unread and hardware cause remains open.

[374806](https://forums.developer.nvidia.com/t/dgx-spark-shuts-down-within-minutes-after-os-reinstall-kernel-panic-during-first-boot-update/) reports first-boot panic/update and later apparent shutdown; support saw a power-key event immediately after a Logitech receiver event. The owner eventually got display output using a different monitor and says it must be connected before power-on; peripheral isolation was not confirmed. Runbook diagnosis should separate actual power-key input, headless display initialization and kernel panic before reimaging. The referenced journal and bug report are absent from the evidence bundle.

[358789](https://forums.developer.nvidia.com/t/msi-edgexpert-is-down/) adds an unresolved MSI EdgeXpert post-upgrade screen failure; support asks whether SSH/NVIDIA Sync still work to collect logs. The inspected screenshot shows GNOME's “Oh no! Something has gone wrong” session-recovery page. It confirms a desktop-session failure, not a kernel/firmware cause or completed rollback. Preserve remote log capture and session state before recovery; do not prescribe reimage from the screenshot alone. Evidence copy: `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/attachments-root/358789-attachment.jpeg`.

[354729](https://forums.developer.nvidia.com/t/dgx-spark-not-powering-on/) reports a Spark FE with no lights/fan after a month fully powered off, despite the adapter having power; holding the button for 60 seconds did not help. Support asks for monitor/wired HID to inspect PON output and says a failed PON may require RMA. Add power-present/no-boot to the runbook: confirm proper button/adapter, collect PON/console evidence, and escalate to OEM rather than repeatedly reimaging a unit that never reaches recovery.

[372348](https://forums.developer.nvidia.com/t/spark-cluster-pxe-boot-microtik-routeros-app/) describes an operator's management-plane design: a router-hosted VLAN endpoint and VPN path remain accessible when a Spark or AI agent breaks its own network, with a cellular hotspot as internet fallback. This is not an NVIDIA-validated design and the post discusses a mixed homelab/PXE project. Use only as a design prompt for an independently reachable console/management path, separated credentials and a tested offline fallback; do not assume a remote VPN or Internet route survives a shared router failure.

[358484](https://forums.developer.nvidia.com/t/monitor-doesnt-wake-up-from-sleep/) reports both Samsung LS27A600 monitors blank after idle while SSH remains available on DGX Spark; reboot restores display, with no logs or final fix. Support asks about monitor deep sleep, cable/model and a bug report over SSH, then suggests hotplug/DisplayPort OSD tests. Record local display loss separately from host freeze and preserve SSH log capture / alternate console before power-cycling. [360492](https://forums.developer.nvidia.com/t/wake-on-lan-wol-on-dgx-spark/) has conflicting owner reports about WoL: `ethtool` shows `Supports Wake-on: pumbg`/`Wake-on: g`, while another Spark owner says WoL does not work and describes BIOS “power on after power failure” plus smart plug. Do not claim WoL is a guaranteed recovery channel; validate the exact interface/BIOS/OEM, and design an external power/control path with a safe shutdown and restoration test.

[348086](https://forums.developer.nvidia.com/t/dgx-spark-os-iso-download/348086) reports that booting a full DGX OS installation ISO begins disk reinstallation without a cancel path; ASUS media is nested as an ISO inside tar/ZIP, and a user’s direct USB creation was not bootable until they extracted the ISO. Treat installation and recovery media as distinct paths: identify OEM/image and exact action, check the recovery USB, require a verified backup before destructive installation, and test on a blank/replacement drive. These are owner reports; the thread does not validate the full current recovery flow. [347717](https://forums.developer.nvidia.com/t/should-i-buy-asus-gx10-instead-nvidia-dgx-spark/347717/29) also reports a black screen while trying GX10 recovery; a reply recommends USB-C-to-HDMI for another case but does not confirm this recovery was fixed.


[363536](https://forums.developer.nvidia.com/t/363536) relata que el DGX Spark quedó con pantalla negra/Xorg roto tras cambios del usuario; arrancar desde una imagen USB oficial 1.120.36 y reinstalar recuperó el equipo, confirmado por el dueño. La reinstalación puede borrar el SSD interno y el hilo menciona que el proyecto tenía respaldo en GitHub. Documentar imagen y checksum, distinguir recovery de instalación destructiva y exigir verificar respaldo e identidad del medio antes de seguir; el video del hilo no fue inspeccionado.

[363805](https://forums.developer.nvidia.com/t/unable-to-configure-the-ascent-gx10-on-first-startup/363805) adds an OOBE external-check failure affecting several ASUS GX10/FE owners: Ethernet or Wi-Fi could be connected while setup still could not advance. NVIDIA linked the incident to Canonical's connectivity-check service; Canonical announced a partial outage on 21 March 2026 and mitigations, and NVIDIA later said it was resolved. The same thread also contains heterogeneous Wi-Fi/client and recovery outcomes; do not assign every setup failure to that outage. The failed health-check path should distinguish `link/IP up, external check down` from Wi-Fi association failure and offer an explicit supported retry/offline route. [364255](https://forums.developer.nvidia.com/t/364255) later describes a community binary patch that forces `HasInternet()` true; it is not a supported fix and masks external reachability. Its linked script is version/byte guarded, but lacks an artifact hash/backup and ignores filesystem-check exit status. Do not apply it to BB recovery media.

### Delta de recuperación ante freeze y hard reset

**DELTA-FORUM-RECOVERY-APT-UPDATE-01.** Un usuario informa freeze tras actualización APT y luego un bloqueo durante vLLM en Docker con `--restart always`; tras hard resets describe UEFI/USB/SSH poco fiables, flags GRUB/ACPI añadidos por su cuenta y recomendación NVIDIA de recuperación oficial o RMA ([359198](https://forums.developer.nvidia.com/t/359198)). No hay logs suficientes para atribuir causa a APT, Docker o workload. Extender la runbook con captura preservable antes del reset, identificación de último kernel/driver/paquete, vía de consola externa, medio OEM verificado y criterio de recovery/RMA; cualquier rollback de paquetes se ensaya en copia/canary.

[347963](https://forums.developer.nvidia.com/t/347963) contiene el reconocimiento oficial de un despliegue de actualización que entregó estado incompleto a algunos equipos por diferencia entre cualificación y producción; la recuperación oficial indicada fue reflash solo para Spark afectados. El mismo hilo registra fallas del script macOS de recovery luego corregidas, teclado sin entrada y USB de recovery que no arranca. Antes de un rollout amplio, exigir canario del entorno de producción con verificación de boot, driver GPU y recovery media; para rescate, registrar versión/checksum del medio y probar teclado cableado compatible y entrada UEFI. Los números 57, 59 y 73 no aparecen en el stream descargado; imágenes no inspeccionadas.

[363185](https://forums.developer.nvidia.com/t/asus-gx10-iso-image/363185) reinforces that an ASUS Ascent OS update ISO and the NVIDIA recovery archive have different USB creation paths. The ASUS update ISO was written via Balena Etcher/Raspberry Pi Imager; NVIDIA recovery media uses the bundled `CreateUSBKey.sh` and its own BIOS validation. A user who first used the recovery helper against a different image got `Boot Loader Files Present FAIL`; after using a bootable base USB plus recovery script, the BIOS validation passed, but the thread does not confirm that recovery/install completed. Preserve the exact OEM image, checksum and official writer, then read BIOS validation before boot/reinstall. ASUS remains responsible for UEFI/EC update ownership according to the forum reply even when the DGX OS image is used. Do not confuse writing a USB with successful recovery or apply fwupd commands from the thread without a versioned OEM target. Attachments remain uninspected.

### Reparación que conserve datos: brecha pendiente, propuesta no validada

[370981](https://forums.developer.nvidia.com/t/request-dgx-spark-os-recovery-without-wiping-user-data/370981) informa un DGX Spark que quedó en VFS panic tras “Update Now” y volvió a servicio mediante restore completo, con más de 14 horas para recuperar el baseline. El post 6 enlaza el caso separado de [kernel panic por initramfs ausente](https://forums.developer.nvidia.com/t/recovery-from-kernel-panic-after-dashboard-update-unable-to-mount-root-fs-on-unknown-block-0-0/368939). Los posts proponen reparación/reinstalación que preserve datos; la arquitectura de particiones incluida está marcada por el autor como strawman asistido por IA, sin implementación ni validación. Otro participante refiere live USB para montar NVMe y copiar datos antes de wipe, que sirve como recuperación de datos y no demuestra reparación del SO.

Investigar primero capacidades OEM existentes. Para una ruta futura, capturar estado de boot/paquetes, validar por lectura el disco y las particiones objetivo, ofrecer acceso de datos read-only/copia verificable y probar reparación de initramfs antes de reinstalar. Previsualizar alcance y separar la acción destructiva. No crear particiones, tocar GRUB o ejecutar chroot/repair scripts a partir del strawman del foro. Cierre requiere matriz de fallos en imágenes desechables y con datos centinela por OEM, verificación de hash preservado, negativo de disco/partición destino, boot posterior, rollback y aprobación del soporte OEM. Hasta entonces la ficha registra una capacidad pendiente, no una función soportada.


## Índice de propuestas registradas del swarm NVIDIA categoría 721

- **`BB-RECOVERY-IMAGE-DESTRUCTIVE-BOOT`** — A GX10 owner could not boot a USB made from an ASUS recovery archive; another owner reports the DGX OS full ISO starts reinstall and wipes the SSD without a cancel path. Fuente: [348086](https://forums.developer.nvidia.com/t/348086/1).
- **`BB-RECOVERY-POSTFLASH-FIRSTBOOT-VALIDATION`** — A DGX Spark recovery with image 1.105.17 reportedly restored SSH/Sync but left only a black screen; a reply says image 1.120.36 includes display detection fixes. After using 1.120.36 the author reports a purple/crown screen, no… Fuente: [361008](https://forums.developer.nvidia.com/t/361008/1).
- **`BB-OOBE-NETWORK-RECOVERY-VALIDATION`** — A new DGX Spark FE with UEFI 2.22.1295 reportedly cannot complete OOBE because Wi-Fi client join fails (Error 500/Unable to Join); Ethernet is present but wizard still requires Wi-Fi. Recovery image 1.120.36 did not help. A user… Fuente: [364255](https://forums.developer.nvidia.com/t/364255/1).
- **`BB-RECOVERY-IMAGE-AND-BACKUP-RESTORE-VERIFICATION`** — Owner reports NVIDIA recovery USB returns the system to day-one state; Deja Dup covers user files, while Timeshift and scripts are community alternatives. Backups were configured but their real restore was explicitly not yet tested. No… Fuente: [348169](https://forums.developer.nvidia.com/t/what-ive-learned-so-far-as-a-non-tech-day-1-dgx-spark-adopter/348169/1).
- **`BB-DATA-PRESERVING-OS-RECOVERY-PATH`** — A DGX Spark owner reports an update-induced VFS kernel panic followed by full restore that erased local data and took more than 14 hours to return to baseline. The discussion links a separate kernel/initramfs recovery account and… Fuente: [370981](https://forums.developer.nvidia.com/t/request-dgx-spark-os-recovery-without-wiping-user-data/370981/1).


## Índice de hallazgos asociados

- **`BB-RESCUE-TARGET-RUNBOOK`** — A Dell Pro Max Spark owner could not use the normal desktop workflow because they needed to disable a rogue service. They entered GRUB via repeated F7 then ESC and booted `systemd.unit=rescue.target`; the user reported the issue was… Fuente: [372358](https://forums.developer.nvidia.com/t/dell-pro-max-version-of-spark/372358/1).


## Índice de propuestas del lote 00

- `FORUM-00-OOBE-RECOVERY-PREFLIGHT` — [Keep a validated recovery path during headless first boot and platform updates](https://forums.developer.nvidia.com/t/347825/1); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-PXE-RECOVERY-STATIC-IP-GATE` — [Validate PXE recovery arguments and verify the recovered system actually boots](https://forums.developer.nvidia.com/t/381099/1); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-PCIE-NVME-WRITE-FAILURE-RMA` — [Escalate persistent PCIe data-path write failures instead of repeating destructive recovery](https://forums.developer.nvidia.com/t/365094/1); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-DISPLAY-HOTPLUG-UPDATE-VISIBILITY` — [Keep a validated HDMI console attached during firmware and reboot sequences](https://forums.developer.nvidia.com/t/380326/1); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.

### DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01 — Validar el destino de respaldo tras reinicio

Fuente: [hilo 375954](https://forums.developer.nvidia.com/t/375954); cuerpos capturados leídos, sin auditoría de binarios ni repos externos.

SanDisk Extreme 55DD 8 TB desaparece tras reinicio en kernel 6.17-1026: EPROTO -71 antes de enumerar UAS. Replug restaura el disco; OTA, autosuspend y varios cables no resuelven. Un ASM2464 distinto monta a USB2 y negocia Gen2x2 tras replug. NVIDIA sigue investigando; causa y parche permanecen pendientes.

Propuesta: Antes del respaldo y del restore, verificar UUID, dispositivo esperado, mountpoint real y disponibilidad; ante ausencia, abortar con evidencia y conservar datos. Evitar escribir al directorio vacío sobre el filesystem raíz. Capturar estado antes/después de replug y distinguir enumeración, montaje y permisos.

Riesgo: Reenumerar USB durante escritura puede perder datos; cable o firmware como causa permanece hipótesis.

Cierre: Fixture con disco ausente y mountpoint existente bloquea escritura; prueba tras reinicio valida identidad y lectura del respaldo. Recuperación conserva datos y requiere resultado verificable.

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
