---
id: DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01
kind: task
domain: VERDICT
title: "Validar forum 8node nccl interface mtu 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Reporte de operador sobre un cluster de 8 GB10 con NCCL; este equipo es un solo nodo sin CX7 en pareja ni NCCL multinodo. La captura de MTU por interfaz ya existe en tools/host_diagnostics.py (BB-INSTRUMENTS-network). Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_8node_nccl_interface_mtu_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01.** En un clúster de ocho GB10 con Ubuntu 24.04.4, kernel 6.17.0-1018-nvidia, driver 580.159.03/CUDA 13.2, NCCL 2.30.6a2 y vLLM eugr dev277/TF5, el dueño reporta que Kimi K2.6 NVFP4 se quedaba en inicialización/warmup: GPU 96% a 22–23W, QP receiver loop creciendo, sin endpoint API ni logs nuevos; `--enforce-eager` y modos CUDAGraph no resolvieron ese síntoma. Después identificó MTU incorrecto en una interfaz de un nodo; al corregirlo reporta que el servicio llegó a ~16 tok/s ([369446, posts 22–24](https://forums.developer.nvidia.com/t/369446/22)). Añadir preflight que compare MTU efectivo por interfaz/nodo con el plan de red del OEM/topología antes de NCCL y valide una operación NCCL más la primera inferencia con endpoint y logs por rank. El hilo usa tanto ejemplos de 1500 como otras topologías jumbo; no codificar valor universal. Resultado/fix de operador, sin reproducción ni logs auditados.

Fuentes: tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Avance de instrumentación 2026-10-03

`tools.host_diagnostics` ahora registra MTU reportado por `ip -j link` y sysfs sin fijar un umbral universal. Esta captura local leyó MTU 1500 de `enP7s7` por sysfs, pero `ip -j link` no pudo abrir netlink; no compara ocho nodos ni valida NCCL/primera inferencia. Evidencia: [BB-INSTRUMENTS-network](../../docs/evidence/BB-INSTRUMENTS-network.md). La ficha permanece abierta; `close_check` y `status` no cambiaron.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: La captura de red actual lee MTU sysfs de un solo netdev y netlink no disponible; no representa ocho nodos.
- Evidencia faltante para cierre: MTU por interfaz y nodo contra topología/OEM; corrida NCCL sana y negativa; primera inferencia, endpoint/logs por rank, stack y rollback.
- Siguiente acción: Solicitar al operador del clúster mapa OEM de ocho nodos y capturas MTU por interfaz; después correr NCCL y primera inferencia con endpoint/log por rank, caso sano y rollback.
- Responsable del siguiente paso: BB; operador Luis para hardware/peer.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01.md`, `docs/evidence/BB-INSTRUMENTS-network.md`, `tools/runtime_batch01_controls.py`, `tools/host_diagnostics.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: El sintoma (Kimi K2.6 en 8 GB10, NCCL 2.30.6a2, warmup colgado por MTU de una interfaz) exige 8 nodos con NCCL; este equipo no tiene cluster ni /sys/class/infiniband. Lo reusable (leer MTU por interfaz) ya lo hace tools/host_diagnostics.py (MTU 1500 de enP7s7 por sysfs, 2026-10-03). Nota: la decision del dueno del 2026-10-11 dejo abiertas las fichas con xfail por no cerrar con un xfail, no por aplicabilidad; si prefiere conservarla, pasar a mantener. (aplicabilidad otro_hardware, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_forum_8node_nccl_interface_mtu_01`, `test_real_capture_close_gate_requires_actual_capture[DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01]`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01.md tasks/backlog/` y `status: open`.
