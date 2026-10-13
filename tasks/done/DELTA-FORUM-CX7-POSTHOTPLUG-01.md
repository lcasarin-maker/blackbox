---
id: DELTA-FORUM-CX7-POSTHOTPLUG-01
kind: task
domain: VERDICT
title: "Validar forum cx7 posthotplug 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Ficha de cluster CX7 con NCCL/RDMA post-hotplug; este equipo es un solo nodo Gigabyte sin InfiniBand/CX7 en pareja ni NCCL (/sys/class/infiniband no existe), por lo que el sujeto no existe. Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-CX7-POSTHOTPLUG-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-CX7-POSTHOTPLUG-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-CX7-POSTHOTPLUG-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-CX7-POSTHOTPLUG-01.md", "expect": "exit_zero", "porque": "Cerrada por aplicabilidad (void_wontfix, decision de Luis 2026-10-13): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a un test por ficha que se retiro con la deprecacion."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-CX7-POSTHOTPLUG-01.** En un clúster GB10 con CX7 firmware 28.45.4028, kernel 6.17.0-1018-nvidia, driver 580.159.03 y mlx5 26.01-1.0.0, el dueño reporta que tras desconectar/reconectar una NIC el all-gather NCCL cae de ~192 a ~25 Gbit/s; `mlxlink` conserva Active/200G y el dueño muestra AER y reenumeración PCIe, mientras reiniciar restaura throughput ([371031](https://forums.developer.nvidia.com/t/371031)). En [363193](https://forums.developer.nvidia.com/t/363193) hay relatos separados de root-port retraining/endpoint ausente y enlace/cable caído; FieldDiag PASS coexistió con NIC no disponible. El adjunto nvidia-bug-report.log.gz no fue leído y las causas siguen abiertas. Añadir un canary post-hotplug que compruebe tráfico NCCL/RDMA extremo a extremo, endpoint PCIe, AER y resultado/frescura de FieldDiag; el estado Active/200G o 27W aislados no cierran salud. Riesgo: reinicio o cambio de marcador altera el estado; registrar versión/cable/firmware y probar en nodo canary con rollback por OEM.

Fuentes: tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Avance de instrumentación 2026-10-03

`tools.host_diagnostics` captura MTU, carrier, operstate, binding PCI/driver y, si hay sysfs RDMA, GID/netdev/firmware por puerto. No provoca hotplug ni valida throughput, recovery o NCCL; la captura actual no expuso dispositivos RDMA y `ip -j link` quedó inaccesible. Evidencia: [BB-INSTRUMENTS-network](../../docs/evidence/BB-INSTRUMENTS-network.md). La ficha permanece abierta; `close_check` y `status` no cambiaron.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: No hay ensayo PCIe/CX7 post-hotplug; estado Active/200G o FieldDiag no prueba tráfico extremo a extremo.
- Evidencia faltante para cierre: stack/cable/firmware; tráfico RDMA/NCCL antes/después; endpoint PCIe/AER; FieldDiag fresco y rollback
- Siguiente acción: Ejecutar hotplug en nodo CX7 canary con tráfico funcional, capturar endpoint/AER y diagnóstico nuevo, y verificar rollback OEM.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-CX7-POSTHOTPLUG-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_08.json`, `tasks/evidence/DELTA-FORUM-CX7-POSTHOTPLUG-01/ (directorio ausente al inspeccionar)`.
- Impedimentos de inspección: 1. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: Requiere dos nodos con CX7 en pareja, trafico NCCL/RDMA y AER tras hotplug (hilos 371031, 363193); este equipo es un solo nodo sin InfiniBand ni NCCL, y la ficha anota 'directorio ausente' y 'la captura no expuso dispositivos RDMA'. (aplicabilidad otro_hardware, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_forum_cx7_posthotplug_01`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-FORUM-CX7-POSTHOTPLUG-01.md tasks/backlog/` y `status: open`.
