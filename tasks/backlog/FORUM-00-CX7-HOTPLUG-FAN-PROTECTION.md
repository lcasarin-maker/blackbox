---
id: FORUM-00-CX7-HOTPLUG-FAN-PROTECTION
kind: task
domain: THERMAL
title: "Prevent idle fan stall after CX7 hotplug powers down on standalone DGX Spark"
status: open
severity: P1
origin: asserted
satd_family: HARVEST_SUGGESTION
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FORUM-00-CX7-HOTPLUG-FAN-PROTECTION --evidence tasks/evidence/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION", "expect": "exit_zero", "porque": "Prove the reported hotplug/fan mechanism and validate a vendor-supported preventive fix or bounded reversible workaround with thermal safety, network controls, and rollback."}
---

## Incidente y evidencia del foro

En [NVIDIA forum thread 378945, post 19](https://forums.developer.nvidia.com/t/dgx-spark-fans-stop-when-the-screen-goes-dark-or-running-from-ssh-box-gets-so-hot-to-touch-fire-hazard/378945/19), un propietario de cinco DGX Spark FE, board P4242 A04, DGX OS 7.6.0, driver 580.178.04, BIOS 5.36_0ACUM027, EC 0x03000508, SoC 0x02009b0b y USB-C PD 0x516, informa que en su unidad standalone el fan funciona al boot y se detiene minutos después; la caja se calienta en idle y el fan vuelve al apagar. En los cuatro equipos conectados a un switch CX7 no observaba el problema.

El autor reporta que `mlx5_core` detecta el CX7 y que, unos 16 s después, `cx7-pcie-hotplug` (`mtk_pcie_hotplug`) registra `Cable removal`, retira el dispositivo del bus y hace que desaparezca de `lspci` y `fwupdmgr get-devices`. Su hipótesis enlaza el CX7 apagado con el control de ventilador en idle basado en consumo eléctrico. Reporta como workaround bloquear `mtk_pcie_hotplug` mediante una regla `blacklist`/`install /bin/false`, reconstruir initramfs y reiniciar: CX7 queda encendido sin cable y fan activo. El coste de unos 17 W adicionales procede de otro hilo citado por el autor; no es una medición de esta máquina ni de ese ensayo. El workaround se probó en una unidad, no valida otras marcas, firmware o lotes.

El hilo previo contiene evidencia de apoyo: con GX10 BIOS 5.36_0ACUM018, kernel 6.17.0-1029, driver 580.173.02, un usuario reproduce fan detenido por DPMS/headless, GPU a 52 C (límite reportado 43 C), zonas a 52–56 C y fan sin RPM detectable; el comportamiento es intermitente entre unidades y un usuario confirma corrección tras cambiar firmware EC, mientras otros observan diferencias de driver/consumo. Esa respuesta no demuestra que DPMS, driver o EC sean causa universal. Los adjuntos binarios del hilo (historial fwupd e imagen) no se analizaron en esta investigación.

## Hueco y acción preventiva

El repo ya documenta que `hwmon` y `nvidia-smi` no exponen RPM del fan (`FEATURE-FAN-RPM`, done). Eso no cubre el fallo de control térmico cuando el fan no responde a temperatura ni detecta una intervención que quite del bus el CX7. `bb` mide temperaturas y eventos térmicos, pero la falta de RPM impide confirmar giro con una señal local estándar. No inferir seguridad a partir de baja potencia GPU o de un field diagnostic PASS en estado sano.

Prioridad: obtener de NVIDIA/ASUS una explicación y corrección soportada para la combinación exacta de BIOS/EC/driver/kernel del reporte. En laboratorio de un DGX Spark FE identificado, comparar con CX7 conectado/desconectado y hotplug activo/bloqueado; registrar cada segundo la presencia PCIe, `journalctl` de `cx7-pcie-hotplug`, temperatura SoC/GPU, consumo desde un medidor externo y estado observable del fan. Incluir headless, DPMS on/off, cable conectado, idle y carga térmica, cada uno con control repetido y soak predefinido. Confirmar operación de networking CX7 y que los cuatro puertos necesarios reaparezcan después de rollback.

El workaround del foro deja la NIC encendida sin cable y puede consumir más energía, interferir con firmware/diagnóstico o cambiar comportamiento de red. No aplicarlo globalmente ni convertirlo en default a partir de un solo caso. Si hace falta probarlo localmente, mantenerlo opt-in con vigía/fecha de expiración; suspender módulos mediante rename, registrar sha256 y modo del archivo, y restaurar solo tras verificar esos valores conforme al contrato de suspensión. El ejemplo de borrar la configuración del post no sirve como procedimiento de rollback del repo. No desactivar controles térmicos ni automatizar `modprobe` sin verificar el OEM, el estado de conexión y la recuperación.

## Cierre

Cerrar con una corrección de firmware/driver confirmada por vendor y validada en el OEM/stack exacto, o con un workaround reversible que pase pruebas A/B y soak en el estado standalone/idle más adverso; ningún caso puede superar límites térmicos ni dejar CX7/red degradados sin aviso. Adjuntar resultados literales, temperaturas, consumo, estado PCIe/fan y rollback verificado. Si el vendor no ofrece una interfaz que confirme el giro del fan, declarar ese límite explícitamente y no convertir temperaturas estables de una sola ejecución en prueba de protección.

## Avance de ejecución 2026-10-02

Conservado lspci local en capture-commands.json. Sin intervención sobre hotplug/DPMS/NIC. 0 ensayos fan/CX7 y 0 lecturas RPM soportadas nuevas. Faltan fan observable, medidor externo, identidad firmware completa y canary A/B; no aplicar blacklist del foro.

Evidencia y pendientes: `tasks/evidence/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION/progress.txt`. Conserva `open`; la captura de estado verifica el instrumento y deja pendiente el ensayo de recuperación/prevención requerido.

[356366](https://forums.developer.nvidia.com/t/dgx-spark-cluster-what-cable-do-you-use/356366) records NVIDIA's supported cable P/Ns: Amphenol NJAAKK0006 and Luxshare LMTQF022-SD-R. NVIDIA warns unsupported active cables can consume additional power and affect the thermal/power envelope; owner reports that an FS QSFP56 works as a physical failover, without OEM validation. Include cable type/P/N, active/passive and node OEM in the lab matrix; do not treat link success or reported throughput as thermal validation.

[376825](https://forums.developer.nvidia.com/t/asus-gx10-connectx-7-not-showing/) shows ConnectX-7 endpoints present in the PCI enumeration/dmesg even though `ifconfig` omitted them and no cable was connected; `mlx5_core` logged cable unplugged and a 27W slot-power warning. A reply says CX7 hotplug is enabled by `/etc/nvidia/cx7-hotplug-enabled`, but suggests deleting that marker; another says disabling hotplug or connecting a cable nearly doubles idle draw. Prefer vendor-supported behavior; any temporary test must rename and manifest the marker (sha256/mode, expiry, watcher), canary the exact GX10 and measure idle power/network/fan, then verify restore. Do not use the forum `rm` command as a reversible procedure.

[383649](https://forums.developer.nvidia.com/t/super-slow-connection-between-2-sparks/) reports dual Spark links at only 13.19 Gbps on the first CX7 DAC setup; after powering both machines off and disconnecting wall power for one minute, the owner reports 110.88 Gbps. Another user says a full power drain can trigger a first-use ConnectX reconfiguration, but the cause and “never repeats” claim are unverified. Keep this as an operator-reported recovery step for link bring-up only: capture link stats/config and exact cable/firmware before and after, use a supported shutdown procedure, and do not turn recurring cold power-cycles into unattended remediation.

[365584](https://forums.developer.nvidia.com/t/connectx-7-wont-come-online/) reports two new Sparks with ConnectX-7 ports unavailable across three cables (NADDOD, FS.com, Micro Center) that sellers tested; a post says the ports only appeared after disabling the hotplug behavior, but then `mlx5` logged DOE mailbox reset/create errors (`-5`) and resource claim failures. NVIDIA requested a bug-report bundle; no diagnosis or fix is published. Treat cable substitution and marker changes as unproven; capture exact OEM/firmware, PCI enumeration, DOE logs and the bundle before deciding whether to RMA. Do not repeatedly suspend hotplug across units.


## Preferencia por el control nativo

La lectura local del handler instalado (`/opt/nvidia/dgx-spark-mlnx-hotplug/mtk-hotplug-handler.sh`, evidencia `native-cx7-handler-read.txt` del swarm) muestra que la ausencia de `/etc/nvidia/cx7-hotplug-enabled` hace escribir `0` en `hotplug_enabled` y salir antes de retirar endpoints PCIe. Antes de introducir un blacklist de módulo, evaluar este control nativo en el OEM/versiones exactos del canary. La prueba temporal debe renombrar el marcador y conservar manifest con sha256, modo, expiración y vigía; comprobar estado efectivo, fan, consumo y red, y verificar restauración. Leer el código prueba la existencia del mecanismo; quedan pendientes su efecto térmico y la equivalencia frente al workaround del foro. En esta investigación el handler tuvo 0 ejecuciones y el marcador tuvo 0 cambios.


[368025](https://forums.developer.nvidia.com/t/368025) reporta que un MSI EdgeXpert redujo aproximadamente a la mitad el throughput de un clúster de dos Spark tras una actualización. El dueño dice que `fwupdmgr downgrade` restauró sus mediciones; una respuesta de NVIDIA señala corrección posterior y recomienda CX7 firmware >=28.45.4028 y UEFI 1.107.26 para ese MSI. Verificar versiones exactas y comparar throughput, enlace y potencia en canary OEM; no degradar firmware como receta general ni extrapolar a GX10/FE. Los adjuntos del hilo no se leyeron.
