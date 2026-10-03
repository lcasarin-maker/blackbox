---
id: FORUM-00-REALTEK-EEE-DIRECT-LINK
kind: task
domain: NETWORK
title: "Detect and validate EEE link stalls on DGX Spark direct Ethernet"
status: open
severity: P2
origin: asserted
satd_family: PREVENTION
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FORUM-00-REALTEK-EEE-DIRECT-LINK --evidence tasks/evidence/FORUM-00-REALTEK-EEE-DIRECT-LINK", "expect": "exit_zero", "porque": "Confirm the exact link-partner/kernel/driver combination, reproduce EEE-related stalls, verify a bounded opt-in mitigation and prove rollback and unaffected-link controls."}
---

## Fallo y mitigación reportados

En el hilo NVIDIA [354764, posts 1–13](https://forums.developer.nvidia.com/t/dgx-spark-ethernet-connection-unstable-after-november-2025-update-eee-energy-efficient-ethernet-workaround/354764), DGX Spark con DGX OS 7.2.3/OTA 7.3.1 (2025-11-30), kernel `6.14.0-1015-nvidia`, NetworkManager 1.46.0 y NIC Realtek `r8127` versión `11.014.00-NAPI` pierde o estanca el tráfico después de minutos en enlace Ethernet directo a Windows 11 con Intel I225-V. SSH/NVIDIA Sync caen, `r8127` registra link down/up y puede quedar IPv4 rota/IPv6 link-local; DHCP/static no cambia el caso. El autor observa EEE activo/inactivo y partner no reportado en los estados problemáticos. Dice que `sudo ethtool --set-eee enP7s7 eee off` detuvo el flapping y estabilizó Ethernet. Un usuario de Lenovo ThinkStation PGX confirma que el mismo cambio le resolvió una conexión inestable, pero no proporciona versiones.

La atribución EEE no es universal: otro Spark en kernel `6.14.0-1013-nvidia`, mismo DGX OS/driver, conectado a un switch Netgear, muestra EEE activo y no tiene problema. La topología sin switch y el Intel I225-V son un caso límite plausible; el participante enlaza una nota de Intel sobre problemas EEE con I225-V. La evidencia apoya una prueba A/B acotada, no desactivar EEE globalmente.

Los hilos [357212](https://forums.developer.nvidia.com/t/ethernet-connection-to-dgx-spark-is-unstable/357212) y [358212](https://forums.developer.nvidia.com/t/dgx-spark-network-issue/358212) describen pérdida de Ethernet/SSH/Sync o ausencia de IP con WLAN aún activa y remiten a este contexto, pero no añaden resultados de prueba. El hilo [358982](https://forums.developer.nvidia.com/t/dgx-spark-does-not-automatically-reconnect-to-saved-wi-fi-network/358982) trata recuperación Wi-Fi separada y su sugerencia NetworkManager no está validada.

## Cobertura y brecha

`FEATURE-FORUM-WIFI-ISOLATION-01` cubre separación entre salud local y reachability remota para aislamiento WLAN. Este caso es diferente: negociación de enlace Ethernet, EEE, driver y partner. Blackbox debe conservar la diferencia entre host local sano, pérdida de route/IP y caída del enlace; una sonda SSH ausente no diagnostica por sí sola el hardware/PHY. La instrumentación de red existente no verifica EEE ni ata link-down/up de `r8127` a la conectividad restaurada.

## Prueba preventiva, riesgos y rollback

En laboratorio con DGX Spark identificado y partner Intel I225-V, capturar OEM/BIOS/EC/SoC/PD, DGX OS/OTA, kernel, driver `ethtool -i`, partner firmware/OS, `ethtool --show-eee`, link modes, DHCP/static y los logs de `r8127`/NetworkManager. Ejecutar ciclos repetidos de enlace directo con EEE activo e inactivo, además de control por switch conocido estable. Medir link resets, packet loss, tiempo sin IPv4/IPv6, reconnect SSH/Sync, temperatura/consumo y estabilidad bajo soak. Verificar el aviso Intel y el alcance de firmware/driver vigente antes de atribuir causa.

Mantener la mitigación opt-in y limitada al NIC/topología afectados. El ejemplo de systemd del foro fuerza `enP7s7` en cada boot; antes de adoptarlo, confirmar nombre de interfaz estable, estado EEE soportado y que la pareja de enlace negocia correctamente. No deshabilitar EEE en NICs con switch estable, pues cambia consumo/latencia del enlace. Rollback debe desactivar la unidad/configuración añadida, restaurar EEE a su negociación original y confirmar `ethtool --show-eee` más conectividad en ambos sentidos. No activar autorrecuperación de red con reboot.

## Cierre

Cerrar con reproducción y A/B repetido en la topología reportada o con resultado negativo que limite alcance; validación de una fuente primaria de Intel/NVIDIA para la combinación soportada; controles de switch/EEE y recuperación/rollback comprobados. Si `ethtool` o contadores del partner no están disponibles, declarar `could_not_run` sin inferir que EEE está desactivado o que el host está sano. Registrar toda la evidencia por modelo de NIC, kernel y versión exacta de driver.

## Delta separado: deadlines de red tras actualización

[382184](https://forums.developer.nvidia.com/t/382184) reporta OAI/USRP X310 en Spark FE, OS7.5/kernel6.17-1029/r8127: antes funcionaban20/40MHz, después hay late packets;10MHz aún funciona. Falta versión r8127 y respuesta ethtool pedida por NVIDIA; USB B210 es control de otro hardware. Separar deadline/loss de link flap y EEE. Reutilizar ethtool, drops/softnet stats y timestamps OAI, con carga/topología exactas y A/B de versión soportada o CX7; probar EEE solo si la evidencia lo relaciona. PREEMPT_RT o rollback driver exigen soporte OEM y recuperación. La detección existente de HARVEST354764 trata carga CPU de red; el delta preventivo EEE/deadlines permanece pendiente.


## Índice de propuestas registradas del swarm NVIDIA categoría 721

- **`FORUM-REALTIME-RTL8127-STREAM-DEADLINES`** — One user reports an OAI RAN workload with USRP X310 on RTL8127/r8127 stopped sustaining 20/40 MHz sample rates after DGX OS updates, producing late-packet warnings and eventual application failure; 10 MHz still works. Reported stack:… Fuente: [382184](https://forums.developer.nvidia.com/t/issues-with-real-time-sample-streaming-on-dgx-spark-rtl8127-nic/382184/1).

## Estado de publicación de esta investigación

Propuesta abierta. Los comandos de cierre describen el verificador y evidencia requeridos; esta rama publica investigación y fichas, sin implementación ni resultados de ejecución de los mecanismos propuestos.
