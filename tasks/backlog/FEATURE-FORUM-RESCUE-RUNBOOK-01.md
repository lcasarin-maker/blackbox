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

[358789](https://forums.developer.nvidia.com/t/msi-edgexpert-is-down/) adds an unresolved MSI EdgeXpert post-upgrade screen failure; support asks whether SSH/NVIDIA Sync still work to collect logs. Its screenshot remains unread, so preserve status as unknown rather than prescribe rollback or reimage based on the body alone.

[354729](https://forums.developer.nvidia.com/t/dgx-spark-not-powering-on/) reports a Spark FE with no lights/fan after a month fully powered off, despite the adapter having power; holding the button for 60 seconds did not help. Support asks for monitor/wired HID to inspect PON output and says a failed PON may require RMA. Add power-present/no-boot to the runbook: confirm proper button/adapter, collect PON/console evidence, and escalate to OEM rather than repeatedly reimaging a unit that never reaches recovery.

[372348](https://forums.developer.nvidia.com/t/spark-cluster-pxe-boot-microtik-routeros-app/) describes an operator's management-plane design: a router-hosted VLAN endpoint and VPN path remain accessible when a Spark or AI agent breaks its own network, with a cellular hotspot as internet fallback. This is not an NVIDIA-validated design and the post discusses a mixed homelab/PXE project. Use only as a design prompt for an independently reachable console/management path, separated credentials and a tested offline fallback; do not assume a remote VPN or Internet route survives a shared router failure.

[358484](https://forums.developer.nvidia.com/t/monitor-doesnt-wake-up-from-sleep/) reports both Samsung LS27A600 monitors blank after idle while SSH remains available on DGX Spark; reboot restores display, with no logs or final fix. Support asks about monitor deep sleep, cable/model and a bug report over SSH, then suggests hotplug/DisplayPort OSD tests. Record local display loss separately from host freeze and preserve SSH log capture / alternate console before power-cycling. [360492](https://forums.developer.nvidia.com/t/wake-on-lan-wol-on-dgx-spark/) has conflicting owner reports about WoL: `ethtool` shows `Supports Wake-on: pumbg`/`Wake-on: g`, while another Spark owner says WoL does not work and describes BIOS “power on after power failure” plus smart plug. Do not claim WoL is a guaranteed recovery channel; validate the exact interface/BIOS/OEM, and design an external power/control path with a safe shutdown and restoration test.

[348086](https://forums.developer.nvidia.com/t/dgx-spark-os-iso-download/348086) reports that booting a full DGX OS installation ISO begins disk reinstallation without a cancel path; ASUS media is nested as an ISO inside tar/ZIP, and a user’s direct USB creation was not bootable until they extracted the ISO. Treat installation and recovery media as distinct paths: identify OEM/image and exact action, check the recovery USB, require a verified backup before destructive installation, and test on a blank/replacement drive. These are owner reports; the thread does not validate the full current recovery flow. [347717](https://forums.developer.nvidia.com/t/should-i-buy-asus-gx10-instead-nvidia-dgx-spark/347717/29) also reports a black screen while trying GX10 recovery; a reply recommends USB-C-to-HDMI for another case but does not confirm this recovery was fixed.


[363536](https://forums.developer.nvidia.com/t/363536) relata que el DGX Spark quedó con pantalla negra/Xorg roto tras cambios del usuario; arrancar desde una imagen USB oficial 1.120.36 y reinstalar recuperó el equipo, confirmado por el dueño. La reinstalación puede borrar el SSD interno y el hilo menciona que el proyecto tenía respaldo en GitHub. Documentar imagen y checksum, distinguir recovery de instalación destructiva y exigir verificar respaldo e identidad del medio antes de seguir; el video del hilo no fue inspeccionado.

[363805](https://forums.developer.nvidia.com/t/unable-to-configure-the-ascent-gx10-on-first-startup/363805) adds an OOBE external-check failure affecting several ASUS GX10/FE owners: Ethernet or Wi-Fi could be connected while setup still could not advance. NVIDIA linked the incident to Canonical's connectivity-check service; Canonical announced a partial outage on 21 March 2026 and mitigations, and NVIDIA later said it was resolved. The same thread also contains heterogeneous Wi-Fi/client and recovery outcomes; do not assign every setup failure to that outage. The failed health-check path should distinguish `link/IP up, external check down` from Wi-Fi association failure and offer an explicit supported retry/offline route. [364255](https://forums.developer.nvidia.com/t/364255) later describes a community binary patch that forces `HasInternet()` true; it is not a supported fix and masks external reachability. Its linked script is version/byte guarded, but lacks an artifact hash/backup and ignores filesystem-check exit status. Do not apply it to BB recovery media.
