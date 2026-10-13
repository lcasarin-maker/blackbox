---
id: DELTA-FORUM-CX7-FW-UPDATE-GUARD-01
kind: task
domain: VERDICT
title: "Validar forum cx7 fw update guard 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Sin HCA CX7 expuesto en la ATOM Gigabyte (sin /sys/class/infiniband); el cambio de firmware lo detecta tools/huella_host.py (sonda_firmware_cx7) y la guarda de paquetes APT criticos la lleva FEATURE-APT-CRITICAL-METAPACKAGE-GUARD. Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01.md", "expect": "exit_zero", "porque": "Cerrada por aplicabilidad (void_wontfix, decision de Luis 2026-10-13): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a un test por ficha que se retiro con la deprecacion."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-CX7-FW-UPDATE-GUARD-01.** En ASUS GX10 PSID NVD0000000087, el dueño atribuye a `dpkg --configure -a`/`mlnx-fw-updater 25.10-1.7.1.0` un flash CX7 de 28.45.4028 a 28.47.1088; después informa ambas NIC en `pre-init`, timeout `-110` y ninguna recuperación con reinstalación. NVIDIA dice que ingeniería sigue investigando. Los logs, `mstdump` y el diagnóstico adjunto no se leyeron, por lo que mecanismo y causalidad siguen sin confirmación ([373900](https://forums.developer.nvidia.com/t/373900)). Hacer que el preflight detecte escrituras de firmware CX7 invocadas indirectamente, verifique OEM/PSID/versión exacta, prerequisitos BME/DMA y canal firmado autorizado, y falle cerrado si falta evidencia. Ensayar primero en hardware reemplazable con captura pre/post y ruta de recuperación; nunca flashear para reproducir.

Fuentes: tasks/backlog/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Avance de instrumentación 2026-10-03

El inventario usa PCI/sysfs para identidad y binding; firmware RDMA se leería de `fw_ver` solo cuando sysfs exponga ese dispositivo. Este host no expuso HCA RDMA, y el firmware de `enP7s7` queda `UNKNOWN` porque no hay atributo genérico disponible; no se ejecutó ni validó ninguna actualización/guard. Evidencia: [BB-INSTRUMENTS-network](../../docs/evidence/BB-INSTRUMENTS-network.md). La ficha permanece abierta; `close_check` y `status` no cambiaron.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: Inventario local no expuso HCA RDMA; fw_ver de interfaz queda UNKNOWN y no hubo actualización/guard validado sobre hardware CX7.
- Evidencia faltante para cierre: Inventario local no expuso HCA RDMA; fw_ver de interfaz queda UNKNOWN y no hubo actualización/guard validado sobre hardware CX7.
- Siguiente acción: Coordinación BB: definir lectura/guard según interfaz soportada; operador Luis: aportar inventario de CX7 y firmware/OEM, y ejecutar canario de actualización sólo con rollback documentado. Ref explícita: tasks/backlog/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01-original-selector-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_06.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01-original-selector-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: Esta ATOM no expone HCA RDMA (/sys/class/infiniband no existe) y la ficha misma registra firmware 'UNKNOWN' por falta de dispositivo. tools/huella_host.py ya tiene sonda_firmware_cx7 y detecta cambio de firmware; la deteccion de escrituras indirectas via dpkg la cubre FEATURE-APT-CRITICAL-METAPACKAGE-GUARD. (aplicabilidad ya_cubierta, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_forum_cx7_fw_update_guard_01`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01.md tasks/backlog/` y `status: open`.
