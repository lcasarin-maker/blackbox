---
id: DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01
kind: task
domain: VERDICT
title: "Validar forum cx7 rdma asymmetry retest 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Requiere dos hosts con CX7 enlazados y ib_write_bw bidireccional; este equipo es un nodo unico sin HCA RDMA ni peer, y el kernel/firmware ya se vigilan en tools/huella_host.py. Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01.md", "expect": "exit_zero", "porque": "Cerrada por aplicabilidad (void_wontfix, decision de Luis 2026-10-13): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a un test por ficha que se retiro con la deprecacion."}
---

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/379303

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

### Evidencia de instrumento (2026-10-03)

Estado: `deferred_lab`. El inventario de red existente informa cero HCA RDMA, `ip link` inaccesible, conexión física `UNKNOWN` y transporte no probado. Falta retest bidireccional `ib_write_bw` entre ambos hosts fijados antes/después de reboot individual/secuencial y hotplug, con cable PN, CX7 fw y comandos/resultados. No se alteró host ni se generó tráfico. La ficha sigue abierta y `close_check` intacto. Informe: `docs/evidence/BB-INSTRUMENTS-feasibility-runtime.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: Inventario informa cero HCA RDMA, ip link inaccesible y enlace físico UNKNOWN; falta retest bidireccional ib_write_bw en ambos hosts con reboot individual/secuencial.
- Evidencia faltante para cierre: Inventario informa cero HCA RDMA, ip link inaccesible y enlace físico UNKNOWN; falta retest bidireccional ib_write_bw en ambos hosts con reboot individual/secuencial.
- Siguiente acción: Coordinación BB: preparar captura/criterio de simetría; operador Luis: aportar ambos hosts CX7 y correr prueba bidireccional/reboots seguros con resultados literales. Ref explícita: tasks/backlog/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01.md y tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_09.json.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01.md`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01-original-selector-current.log`, `docs/evidence/BB-INSTRUMENTS-network.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_09.json`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: Prueba ib_write_bw bidireccional entre dos GX10; aqui el inventario reporta cero HCA RDMA y no hay peer. (aplicabilidad otro_hardware, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_forum_cx7_rdma_asymmetry_retest_01`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01.md tasks/backlog/` y `status: open`.
