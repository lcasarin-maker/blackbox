---
id: DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01
kind: task
domain: VERDICT
title: "Validar forum 8node nccl interface mtu 01"
status: open
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
