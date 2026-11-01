---
id: FORUM-00-REALTEK-EEE-DIRECT-LINK
kind: task
domain: NETWORK
title: "Detect and validate EEE link stalls on DGX Spark direct Ethernet"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "Exige un enlace Ethernet directo contra un Intel I225-V; la unica interfaz cableada (r8127, enP7s7) sale por una puerta de enlace DHCP (red con router, no enlace directo) y no hay I225 en el bus PCI. Decision de Luis 2026-10-14: cerrar sin sujeto; reabrir si se conecta un enlace directo."
evidence: {"pass": "tasks/evidence/FORUM-00-REALTEK-EEE-DIRECT-LINK/pass.txt", "fail": "tasks/evidence/FORUM-00-REALTEK-EEE-DIRECT-LINK/fail.txt", "e2e": "tasks/evidence/FORUM-00-REALTEK-EEE-DIRECT-LINK/e2e.txt"}
severity: P2
origin: asserted
satd_family: PREVENTION
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/FORUM-00-REALTEK-EEE-DIRECT-LINK.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior era `python3 -m tools.verify_forum_finding --id FORUM-00-REALTEK-EEE-DIRECT-LINK --evidence tasks/evidence/FORUM-00-REALTEK-EEE-DIRECT-LINK`, el verificador de hallazgos de foro, que sin captura real del sujeto sale con could_not_run; sin sujeto aqui no hay captura posible."}
---

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/dgx-spark-ethernet-connection-unstable-after-november-2025-update-eee-energy-efficient-ethernet-workaround/354764
- https://forums.developer.nvidia.com/t/ethernet-connection-to-dgx-spark-is-unstable/357212
- https://forums.developer.nvidia.com/t/dgx-spark-network-issue/358212
- https://forums.developer.nvidia.com/t/dgx-spark-does-not-automatically-reconnect-to-saved-wi-fi-network/358982
- https://forums.developer.nvidia.com/t/382184
- https://forums.developer.nvidia.com/t/issues-with-real-time-sample-streaming-on-dgx-spark-rtl8127-nic/382184/1

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Cobertura y brecha

`FEATURE-FORUM-WIFI-ISOLATION-01` cubre separación entre salud local y reachability remota para aislamiento WLAN. Este caso es diferente: negociación de enlace Ethernet, EEE, driver y partner. Blackbox debe conservar la diferencia entre host local sano, pérdida de route/IP y caída del enlace; una sonda SSH ausente no diagnostica por sí sola el hardware/PHY. La instrumentación de red existente no verifica EEE ni ata link-down/up de `r8127` a la conectividad restaurada.

## Prueba preventiva, riesgos y rollback

En laboratorio con DGX Spark identificado y partner Intel I225-V, capturar OEM/BIOS/EC/SoC/PD, DGX OS/OTA, kernel, driver `ethtool -i`, partner firmware/OS, `ethtool --show-eee`, link modes, DHCP/static y los logs de `r8127`/NetworkManager. Ejecutar ciclos repetidos de enlace directo con EEE activo e inactivo, además de control por switch conocido estable. Medir link resets, packet loss, tiempo sin IPv4/IPv6, reconnect SSH/Sync, temperatura/consumo y estabilidad bajo soak. Verificar el aviso Intel y el alcance de firmware/driver vigente antes de atribuir causa.

Mantener la mitigación opt-in y limitada al NIC/topología afectados. El ejemplo de systemd del foro fuerza `enP7s7` en cada boot; antes de adoptarlo, confirmar nombre de interfaz estable, estado EEE soportado y que la pareja de enlace negocia correctamente. No deshabilitar EEE en NICs con switch estable, pues cambia consumo/latencia del enlace. Rollback debe desactivar la unidad/configuración añadida, restaurar EEE a su negociación original y confirmar `ethtool --show-eee` más conectividad en ambos sentidos. No activar autorrecuperación de red con reboot.

## Cierre

Cerrar con reproducción y A/B repetido en la topología reportada o con resultado negativo que limite alcance; validación de una fuente primaria de Intel/NVIDIA para la combinación soportada; controles de switch/EEE y recuperación/rollback comprobados. Si `ethtool` o contadores del partner no están disponibles, declarar `could_not_run` sin inferir que EEE está desactivado o que el host está sano. Registrar toda la evidencia por modelo de NIC, kernel y versión exacta de driver.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: La captura local muestra EEE activo/inactivo, pero no anuncia partner EEE y excluye un A/B con enlace directo/peer.
- Evidencia faltante para cierre: Tupla OEM/kernel/driver/peer; múltiples repeticiones EEE on/off; control switch/no-EEE; stalls, SSH/tráfico y rollback.
- Siguiente acción: Solicitar a dueño NIC/peer capturas del stack exacto y ensayos repetidos EEE activado/desactivado/control switch, con estado de tráfico/SSH y rollback documentado.
- Responsable del siguiente paso: BB; operador Luis para hardware/peer.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FORUM-00-REALTEK-EEE-DIRECT-LINK.md`, `docs/evidence/BB-INSTRUMENTS-network.md`, `tools/forum_finding.py`, `tools/forum_hardware_subjects.py`, `tools/host_diagnostics.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: baja · lectura: completa.

Hay r8127 por cable (enP7s7) en este nodo, pero el caso es enlace directo contra un Windows con Intel I225-V y la topologia local no esta medida; otra variante del hilo sobre kernel 1013 con switch no tiene problema. El delta 382184 (USRP/OAI) es otra carga.

Version para un solo nodo Gigabyte AI TOP ATOM: Registrar en tools/huella_host.py o host_diagnostics.py el estado de 'ethtool --show-eee' y los link down/up de r8127 por boot; sin A/B con partner ni mitigacion automatica.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Root Cause
No aplica a este equipo: el atasco EEE reportado ocurre en un enlace Ethernet directo contra un Intel I225-V. Aqui la unica interfaz cableada (Realtek r8127, `enP7s7`, 10 Gb/s) lleva la ruta por defecto via una puerta de enlace DHCP, asi que es una red con router; no hay I225 en el bus.

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. No tenia test xfail propio; su close_check era `tools.verify_forum_finding`, que sigue vivo para las demas fichas de foro (y `tests/test_closure_hardware.py::test_forum_finding_supports_every_original_id` sigue comprobando que el verificador soporta este id).

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (perfil medido, con control positivo de que las mismas herramientas encuentran lo que si existe) y `e2e` (la decision registrada). Datos de la maquina redactados con el PATRON de `tests/test_sin_datos_privados.py`. Para reabrirla si el sujeto aparece: `git mv tasks/done/FORUM-00-REALTEK-EEE-DIRECT-LINK.md tasks/backlog/` y `status: open`.
