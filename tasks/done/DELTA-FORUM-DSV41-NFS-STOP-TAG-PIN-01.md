---
id: DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01
kind: task
domain: VERDICT
title: "Validar forum dsv41 nfs stop tag pin 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Aplica a un cluster de cuatro Spark con DeepSeek-V4.1 y un stop.sh externo que no esta en el repo; este equipo no sirve DeepSeek ni exporta NFS. Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_dsv41_nfs_stop_tag_pin_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01.** En la migración de un clúster de 4 Spark a DeepSeek-V4.1, un operador reportó que `stop.sh` elimina por wildcard todos los contenedores `dsv41-*`, incluido el NFS exporter; los workers conservaban mounts persistentes y el siguiente `serve` quedaba bloqueado en doctor. El mismo cambio detectó un tag `dev-dsv41` flotante que apuntaba a una base distinta del digest fijado previamente ([382725, post 138](https://forums.developer.nvidia.com/t/382725/138)). Proteger exporter y dependencias con allowlist/orden de parada, validar mount/export antes del servicio y fijar digest/commit del canary. El reporte es de un operador; repos y logs no auditados.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Evaluación de instrumentos 2026-10-03

La evidencia local `docs/evidence/LUNA-98-2026-10-03-queue-04-11.md` señala que el script stop/export y el contrato externo no están en el repo; no existe captura local segura del procedimiento/stack. Estado `needs_capture`: obtener el stop.sh e invocación exacta, dependencias/orden, tag→digest y los campos mínimos de montaje/export necesarios; excluir Env/secretos. No se ejecutó Docker ni se leyó inspect.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `external_oem`.
- Impedimento: La inspección local confirma que stop.sh y contrato externo no están en repo; falta invocación exacta, orden/dependencias y tag→digest, sin exponer secretos.
- Evidencia faltante para cierre: La inspección local confirma que stop.sh y contrato externo no están en repo; falta invocación exacta, orden/dependencias y tag→digest, sin exponer secretos.
- Siguiente acción: Coordinación BB: solicitar al OEM/autor el stop.sh, contrato y pin tag→digest saneado; después implementar verificación con fixture. Ref explícita: tasks/backlog/DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01-original-selector-current.log.
- Responsable del siguiente paso: Coordinación BB solicita al OEM/autor y obtiene el contrato faltante; después implementa la verificación..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_03.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01-original-selector-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: Cluster de cuatro Spark con DeepSeek-V4.1, stop.sh y exporter NFS que no estan en el repo; aqui no se sirve DeepSeek ni hay NFS exporter. (aplicabilidad otro_hardware, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_forum_dsv41_nfs_stop_tag_pin_01`, `test_real_capture_close_gate_requires_actual_capture[DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01]`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01.md tasks/backlog/` y `status: open`.
