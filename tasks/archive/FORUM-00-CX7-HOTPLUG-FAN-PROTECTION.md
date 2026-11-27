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

## Trabajo en la ATOM

Sensor de solo lectura en la ATOM: presencia de `/etc/nvidia/cx7-hotplug-enabled`, estado del endpoint PCIe CX7 y journal de `cx7-pcie-hotplug`, correlacionado con la temperatura en reposo; no aplicar blacklist.

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/dgx-spark-fans-stop-when-the-screen-goes-dark-or-running-from-ssh-box-gets-so-hot-to-touch-fire-hazard/378945/19
- https://forums.developer.nvidia.com/t/dgx-spark-shut-down-without-rebooting/
- https://forums.developer.nvidia.com/t/dgx-spark-cluster-what-cable-do-you-use/356366
- https://forums.developer.nvidia.com/t/asus-gx10-connectx-7-not-showing/
- https://forums.developer.nvidia.com/t/super-slow-connection-between-2-sparks/
- https://forums.developer.nvidia.com/t/connectx-7-wont-come-online/
- https://forums.developer.nvidia.com/t/368025
- https://forums.developer.nvidia.com/t/371031
- https://forums.developer.nvidia.com/t/363193
- https://forums.developer.nvidia.com/t/379303
- https://forums.developer.nvidia.com/t/369446/22
- https://forums.developer.nvidia.com/t/370035/1
- https://forums.developer.nvidia.com/t/373387/5
- https://forums.developer.nvidia.com/t/dgx-spark-fan-control/380995/1
- https://forums.developer.nvidia.com/t/369230
- https://forums.developer.nvidia.com/t/one-of-four-dgx-sparks-shows-35-lower-nccl-bandwidth-cant-figure-out-why/360591
- https://forums.developer.nvidia.com/t/367221
- https://forums.developer.nvidia.com/t/373900

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Hueco y acción preventiva

El repo ya documenta que `hwmon` y `nvidia-smi` no exponen RPM del fan (`FEATURE-FAN-RPM`, done). Eso no cubre el fallo de control térmico cuando el fan no responde a temperatura ni detecta una intervención que quite del bus el CX7. `bb` mide temperaturas y eventos térmicos, pero la falta de RPM impide confirmar giro con una señal local estándar. No inferir seguridad a partir de baja potencia GPU o de un field diagnostic PASS en estado sano.

Prioridad: obtener de NVIDIA/ASUS una explicación y corrección soportada para la combinación exacta de BIOS/EC/driver/kernel del reporte. En laboratorio de un DGX Spark FE identificado, comparar con CX7 conectado/desconectado y hotplug activo/bloqueado; registrar cada segundo la presencia PCIe, `journalctl` de `cx7-pcie-hotplug`, temperatura SoC/GPU, consumo desde un medidor externo y estado observable del fan. Incluir headless, DPMS on/off, cable conectado, idle y carga térmica, cada uno con control repetido y soak predefinido. Confirmar operación de networking CX7 y que los cuatro puertos necesarios reaparezcan después de rollback.

El workaround del foro deja la NIC encendida sin cable y puede consumir más energía, interferir con firmware/diagnóstico o cambiar comportamiento de red. No aplicarlo globalmente ni convertirlo en default a partir de un solo caso. Si hace falta probarlo localmente, mantenerlo opt-in con vigía/fecha de expiración; suspender módulos mediante rename, registrar sha256 y modo del archivo, y restaurar solo tras verificar esos valores conforme al contrato de suspensión. El ejemplo de borrar la configuración del post no sirve como procedimiento de rollback del repo. No desactivar controles térmicos ni automatizar `modprobe` sin verificar el OEM, el estado de conexión y la recuperación.

## Cierre

Cerrar con una corrección de firmware/driver confirmada por vendor y validada en el OEM/stack exacto, o con un workaround reversible que pase pruebas A/B y soak en el estado standalone/idle más adverso; ningún caso puede superar límites térmicos ni dejar CX7/red degradados sin aviso. Adjuntar resultados literales, temperaturas, consumo, estado PCIe/fan y rollback verificado. Si el vendor no ofrece una interfaz que confirme el giro del fan, declarar ese límite explícitamente y no convertir temperaturas estables de una sola ejecución en prueba de protección.

## Avance de ejecución 2026-10-02

Conservado lspci local en capture-commands.json. Sin intervención sobre hotplug/DPMS/NIC. 0 ensayos fan/CX7 y 0 lecturas RPM soportadas nuevas. Faltan fan observable, medidor externo, identidad firmware completa y canary A/B; no aplicar blacklist del foro.

Evidencia y pendientes: `tasks/evidence/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION/progress.txt`. Conserva `open`; la captura de estado verifica el instrumento y deja pendiente el ensayo de recuperación/prevención requerido.

## Preferencia por el control nativo

La lectura local del handler instalado (`/opt/nvidia/dgx-spark-mlnx-hotplug/mtk-hotplug-handler.sh`, evidencia `native-cx7-handler-read.txt` del swarm) muestra que la ausencia de `/etc/nvidia/cx7-hotplug-enabled` hace escribir `0` en `hotplug_enabled` y salir antes de retirar endpoints PCIe. Antes de introducir un blacklist de módulo, evaluar este control nativo en el OEM/versiones exactos del canary. La prueba temporal debe renombrar el marcador y conservar manifest con sha256, modo, expiración y vigía; comprobar estado efectivo, fan, consumo y red, y verificar restauración. Leer el código prueba la existencia del mecanismo; quedan pendientes su efecto térmico y la equivalencia frente al workaround del foro. En esta investigación el handler tuvo 0 ejecuciones y el marcador tuvo 0 cambios.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: No hay canal local de RPM/fan validado ni A/B de hotplug/DPMS/CX7 sobre la tupla OEM; evidencia del foro parcialmente inspeccionada no acredita mitigación.
- Evidencia faltante para cierre: No hay canal local de RPM/fan validado ni A/B de hotplug/DPMS/CX7 sobre la tupla OEM; evidencia del foro parcialmente inspeccionada no acredita mitigación.
- Siguiente acción: Coordinación BB: precisar sensores/fixtures y guardas de admisión; operador Luis: capturar tuple OEM y ejecutar A/B reversible sólo en unidad canary con medida fan externa/OEM. Ref explícita: tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION-direct-close-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_06.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION-direct-close-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: alta · lectura: completa.

Severidad P1: ficha 'standalone DGX Spark' es este caso (un nodo sin cable CX7, cx7-pcie-hotplug presente); riesgo de fan detenido en idle con temperaturas altas. Sin RPM de fan en hwmon, pero termico_predictivo y huella_host ya observan temperatura; el modelo es FE y este equipo es Gigabyte ATOM, por lo que hace falta verificar si el handler existe aqui. El grueso de la ficha (CX7 en malla, NCCL, firmware) es otro hardware.

Version para un solo nodo Gigabyte AI TOP ATOM: Sensor de solo lectura: presencia de /etc/nvidia/cx7-hotplug-enabled, estado del endpoint PCIe CX7 y journal de cx7-pcie-hotplug, correlacionado con temperatura en idle; no aplicar blacklist.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Criterios ejecutables de `tools.verify_forum_finding` (2026-10-14)
Los criterios ejecutables de `tools.verify_forum_finding` se miden en esta ficha: su `close_check` corre ese verificador contra la captura real del sujeto. La meta-ficha `DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01`, que pedia implementarlos, se cerro el 2026-10-14 como `duplicate` (voto de Luis: consolidar en la ficha sujeto): el verificador existe y hoy, sin esa captura, sale con could_not_run (rc=2); conseguir la captura es trabajo de esta ficha.

## Avance 2026-10-16 (lectura de solo lectura en el ATOM; responde la pregunta abierta de la adaptacion 2026-10-13)
El handler existe aqui y el sintoma del foro se reproduce en este equipo standalone: `journalctl -k -b -o short-monotonic` muestra `mlx5_core` con firmware CX7 28.45.4028 a 32.0 GT/s x4 en [1.24], `Cable unplugged` y `insufficient power on the PCIe slot (27W)` en [1.63], `cx7-pcie-hotplug ... Hotplug enabled` en [9.06] y `Cable removal` en [28.19] (~19 s despues); `lspci -d 15b3:` sale vacio y `/etc/nvidia/cx7-hotplug-enabled` esta presente. Kernel 6.17.0-1032-nvidia, driver 580.178.04, DMI GIGABYTE / AI TOP ATOM. `ls /sys/class/hwmon/*/` cuenta 0 entradas `fan*_input` frente a 11 `temp*_input`: no hay tacometro, asi que la rama `fan_rpm` del verificador queda could_not_run por construccion. close_check re-corrido hoy: `{"checks": {}, "could_not_run": 1, "fail": 0, ... "reason": "raw case capture unavailable ..."}` rc=2. 0 cambios de marcador, 0 hotplug, 0 blacklist. Siguen faltando: tacometro de fan (OEM/externo), medidor externo de pared identificado, tupla de firmware UEFI/EC/SoC/PD con fuente OEM que la cite y el A/B en canary con rollback; la ficha sigue `open`.

## Avance 2026-10-26: el mecanismo del hilo 378945 esta armado en esta unidad (medido)

Lectura de solo lectura en la AI TOP ATOM de este repo, un solo nodo y sin cable en el CX7:

- `journalctl -k -b 0`: `oct 24 23:53:51 ... cx7-pcie-hotplug MTKP0001:00: Hotplug enabled` y, 19 s despues, `23:54:10 ... Cable removal`. Boot anterior: `08:12:28 ... Hotplug enabled`, `08:12:48 ... Cable removal`. Dos de dos arranques revisados, mismo intervalo (~20 s) que el hilo (~16 s).
- `/etc/nvidia/cx7-hotplug-enabled` existe (root, 278 bytes, 2026-07-12) y `bb huella` registra `cx7_hotplug = {"marcador": true, "hotplug_enabled": "1"}`: es la configuracion que el handler nativo lee para retirar los endpoints.
- `lsmod`: `mtk_pcie_hotplug` cargado. `/sys/bus/arm_ffa/devices/arm-ffa-17` existe con el UUID `884a63a0-...` que usa el modulo `nvfancontrol` de Z841973620: no es senal de compatibilidad (ver abajo).
- Sin sensor de ventilador: `/sys/class/hwmon` solo tiene `acpitz`, `nvme`, `mt7925_phy0`; ningun `acpi_fan`; los 26 `cooling_device` son 20 `Processor` y 6 `PCIe_Port_Link_Speed`, ninguno de ventilador.
- Lectura puntual con el motor vLLM cargado y la GPU a 9.04 W, 47 C: zonas ACPI 49.7 a 56.7 C. No es una medicion en reposo limpio ni demuestra ventilador detenido; sin RPM no se puede saber.

Esto no prueba que el ventilador de esta unidad se detenga: prueba que las dos condiciones del mecanismo reportado (CX7 retirado tras el boot, sin cable) se cumplen aqui. Falta ensayo A/B con medidor externo (ver arriba). No cargar `nvfancontrol` en esta unidad: su fuente fija la direccion fisica `0x933dd000` (pagina compartida de una unidad FE con EC 0x03000508), esta unidad tiene EC 0x0300050b, y Secure Boot esta activo.
