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

[369716](https://forums.developer.nvidia.com/t/dgx-spark-shut-down-without-rebooting/) adds a separate shutdown report whose kernel log shows ConnectX-7 enumerated at 32 GT/s x4, then E-Switch unload/disable/cleanup immediately after `cx7-pcie-hotplug` enables; `Cable removal` and correctable PCIe RxErr follow, and the author says logs stop about two seconds later. The author suspected overheating, but no shutdown cause was isolated and no controlled post-fix soak was reported. The diagnostic ZIP, nested anomaly log, summary JSON and HTML were later inspected: for a 223-second/99-sample window, UMA was 112.4/121.7 GiB with 4.3 GiB swap active and PSI full zero; GPU peak was 79 C and CPU peak 90.8 C in the summary. The HTML reports two brief 91 C CPU/package peaks and clocks holding 2450–2463 MHz without sustained throttle. This sample does not establish memory thrash or heat as shutdown cause. Forum photos/screenshots remain unread because direct CDN URLs are inaccessible to the web viewer. Treat this as a compound CX7/PCIe/thermal/memory capture case, not proof that heat or hotplug alone caused power-off. Keep the close check focused on correlated timestamps and independent host/PCIe/fan/thermal signals before recommending a thermal modification. Treat this as a compound CX7/PCIe/thermal/memory capture case, not proof that heat or hotplug alone caused power-off. Keep the close check focused on correlated timestamps and independent host/PCIe/fan/thermal signals before recommending a thermal modification.

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

### Delta de corpus NVIDIA, lectura 2026-10-02

**DELTA-FORUM-CX7-POSTHOTPLUG-01.** En un clúster GB10 con CX7 firmware 28.45.4028, kernel 6.17.0-1018-nvidia, driver 580.159.03 y mlx5 26.01-1.0.0, el dueño reporta que tras desconectar/reconectar una NIC el all-gather NCCL cae de ~192 a ~25 Gbit/s; `mlxlink` conserva Active/200G y el dueño muestra AER y reenumeración PCIe, mientras reiniciar restaura throughput ([371031](https://forums.developer.nvidia.com/t/371031)). En [363193](https://forums.developer.nvidia.com/t/363193) hay relatos separados de root-port retraining/endpoint ausente y enlace/cable caído; FieldDiag PASS coexistió con NIC no disponible. El adjunto nvidia-bug-report.log.gz no fue leído y las causas siguen abiertas. Añadir un canary post-hotplug que compruebe tráfico NCCL/RDMA extremo a extremo, endpoint PCIe, AER y resultado/frescura de FieldDiag; el estado Active/200G o 27W aislados no cierran salud. Riesgo: reinicio o cambio de marcador altera el estado; registrar versión/cable/firmware y probar en nodo canary con rollback por OEM.

**DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01.** Un hilo atribuyó una caída direccional RDMA Write (Spark→ASUS GX10 ~13.2 Gbit/s frente a ~111.6 Gbit/s inversa) al kernel ASUS 6.17.0-1029 y reportó vuelta a 6.17.0-1026 ([379303](https://forums.developer.nvidia.com/t/379303)). La atribución pierde fuerza en el propio hilo: tras actualizar/reiniciar el mismo ASUS siguió en 1029 y `ib_write_bw` volvió a ~111.7 Gbit/s; un segundo dueño no reprodujo en Founder Edition. El problema reapareció una vez tras reiniciar y luego se restauró con reinicios de ambos GX10, mientras el propietario sospechó una condición de conectar el DAC con nodos encendidos; esa hipótesis no se controló y otro participante reporta diferencia con cable Amphenol frente a FS.com. No fijar kernel 1026 como workaround. En canary de CX7 compare direcciones en frío, tras reboot individual/secuencial y hotplug, guardando comando/perftest, cable/PN, fw CX7, kernel por OEM, interfaz/IP y estado PCIe/firmware. El resultado de ~13G es reporte temporal de operador; no se leyó issue/bundle externo.

**DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01.** En un clúster de ocho GB10 con Ubuntu 24.04.4, kernel 6.17.0-1018-nvidia, driver 580.159.03/CUDA 13.2, NCCL 2.30.6a2 y vLLM eugr dev277/TF5, el dueño reporta que Kimi K2.6 NVFP4 se quedaba en inicialización/warmup: GPU 96% a 22–23W, QP receiver loop creciendo, sin endpoint API ni logs nuevos; `--enforce-eager` y modos CUDAGraph no resolvieron ese síntoma. Después identificó MTU incorrecto en una interfaz de un nodo; al corregirlo reporta que el servicio llegó a ~16 tok/s ([369446, posts 22–24](https://forums.developer.nvidia.com/t/369446/22)). Añadir preflight que compare MTU efectivo por interfaz/nodo con el plan de red del OEM/topología antes de NCCL y valide una operación NCCL más la primera inferencia con endpoint y logs por rank. El hilo usa tanto ejemplos de 1500 como otras topologías jumbo; no codificar valor universal. Resultado/fix de operador, sin reproducción ni logs auditados.


## Índice de propuestas registradas del swarm NVIDIA categoría 721

- **`BB-CX7-LOW-THROUGHPUT-RING-RECOVERY-CONTROLS`** — A direct two-Spark QSFP setup reportedly negotiated 200 Gbps while iperf/RDMA achieved ~13 Gbps. Owner reports CX7 firmware update to 1.108.20 improved to 111 Gbps; after forming a 3-node ring, it fell to ~10 Gbps with fatal AER. Full… Fuente: [370035](https://forums.developer.nvidia.com/t/370035/1).
- **`BB-CX7-ROCE-LOW-BANDWIDTH-COLD-CYCLE`** — A 3-node direct-cable Spark mesh reports raw `ib_write_bw` stuck around 12.8Gb/s despite 200G ethtool/Gen5x4. The owner reports err-110 from an old NCCL 2.30.4 shim hardcoded in `LD_PRELOAD`; explicitly forcing NCCL 2.30u1 and unsetting… Fuente: [373387](https://forums.developer.nvidia.com/t/373387/5).


## Índice de hallazgos asociados

- **`FORUM-FAN-CONTROL-OEM-GATE`** — NVIDIA says Spark has no supported OS fan-control method. A community kernel module writes an EC command using a fixed mailbox address; testing is anecdotal, OEM compatibility is unclear, and users cite possible high RPM/wear. One GX10… Fuente: [380995](https://forums.developer.nvidia.com/t/dgx-spark-fan-control/380995/1).


## Índice de propuestas del lote 00

- `FORUM-00-GX10-CX7-SOC-EC-VERSION-CANARY` — [Verify paired SoC and EC firmware state before diagnosing absent ConnectX-7 ports on GX10](https://forums.developer.nvidia.com/t/369230); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-CX7-NCCL-FIRMWARE-REGRESSION` — [Canary ConnectX-7 bandwidth regressions by OEM firmware release](https://forums.developer.nvidia.com/t/one-of-four-dgx-sparks-shows-35-lower-nccl-bandwidth-cant-figure-out-why/360591); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.

### DELTA-ROOT-GX10-SOC-EC-CABLE-RECOVERY-CANDIDATE-01 — Candidato OEM de recuperación de cables

Fuente: [hilo 367221](https://forums.developer.nvidia.com/t/367221).

En varios GX10, desactivar hotplug o forzar plug-in restaura las funciones PCI, pero permanece NO-CARRIER y error EIO al leer EEPROM. FieldDiag PASS coexistió con el fallo. El propietario reporta reconocimiento de cables persistente tras reinicios/reconfiguración con SoC 3000007 + EC 20000006 de LVFS testing y switch CRS804. Cambió dos componentes juntos; falta auditoría de los bundles y duración de soak.

Propuesta: Registrar ese tuple como candidato específico GX10 y canal testing. Comparar firmware efectivo antes/después, estado nativo hotplug, presencia/EEPROM del cable, negociación y tráfico funcional tras arranque frío/caliente. Conservar recuperación OEM y versiones anteriores verificables; evaluar componentes separados cuando sea viable. La hipótesis de direcciones iomem ausentes/DOE no demuestra causa. No trasladar firmware GX10 a ATOM ni suspender handlers sin manifest, expiry y vigía.

Riesgo: firmware de prueba puede dejar la red o el arranque inoperables; traslado entre OEM incompatible.

Cierre: Fixture distingue PCI visible, módulo presente y enlace/tráfico operativo. A/B con tuple exacto y regresiones tras reboot; rollback probado. Adjuntos 367221 revisados parcialmente: el bug report, metadatos y hotplug-handler del nodo 3 muestran ASUS GX10, OTA 7.5, kernel 6.17.0-1014, CX7 FW 28.45.4028, MNG FW opcode 1024, velocidad de cable 0x0 y EEPROM EIO; el tercero desaparece del bus después del evento `Hotplug enabled`. Los dumps propietarios de registros se descargaron pero no pudieron interpretarse sin decodificador/vendor; por eso se conserva la limitación de causa, no un fix confirmado.

### Adjuntos CX7 auditados — 363193 y 373900

363193: bugreport central descargado y descomprimido (1535850 bytes); barrido de firmas y secciones PCI/kernel confirma retraining failed de root ports, frente a otros casos del mismo hilo de cable unplugged o hotplug esperado. FieldDiag PASS coexiste con fallo operativo.

373900: bugreport y 9 TXT revisados, incluidos 6 dumps comparados estructuralmente (233842 pares por archivo, 0 inválidos y 0 duplicados). Logs de kernels 6.17-1021 y 6.17-1029 confirman CX7 enumerado, firmware 28.47.1088, pre-init 120000 ms y probe -110 en ambos BDF, sin interfaces CX7. Firmware EC/UEFI y marcador hotplug están presentes. Confirma síntoma persistente; la causa de actualización DOCA y la interpretación de registros propietarios siguen abiertas.

Validación propuesta: OEM/PSID/repositorio y actualizador exactos antes de admisión; después exigir binding, carrier y canario de red, además de enumeración, manteniendo gestión independiente y rollback soportado. Manifest y firmas: `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/attachments-root/`. Fuentes: https://forums.developer.nvidia.com/t/363193 y https://forums.developer.nvidia.com/t/373900.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: No hay canal local de RPM/fan validado ni A/B de hotplug/DPMS/CX7 sobre la tupla OEM; evidencia del foro parcialmente inspeccionada no acredita mitigación.
- Evidencia faltante para cierre: No hay canal local de RPM/fan validado ni A/B de hotplug/DPMS/CX7 sobre la tupla OEM; evidencia del foro parcialmente inspeccionada no acredita mitigación.
- Siguiente acción: Coordinación BB: precisar sensores/fixtures y guardas de admisión; operador Luis: capturar tuple OEM y ejecutar A/B reversible sólo en unidad canary con medida fan externa/OEM. Ref explícita: tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION-direct-close-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_06.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION-direct-close-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
