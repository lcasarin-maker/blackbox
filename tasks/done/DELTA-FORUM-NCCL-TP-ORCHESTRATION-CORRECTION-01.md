---
id: DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01
kind: task
domain: VERDICT
title: "Validar forum nccl tp orchestration correction 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Exige dos nodos con NCCL/TP=2 (hilo 366127); este equipo es un solo GB10 sin InfiniBand/CX7 en pareja, sin Ray y con vLLM de un nodo. Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01.md", "expect": "exit_zero", "porque": "Cerrada por aplicabilidad (void_wontfix, decision de Luis 2026-10-13): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a un test por ficha que se retiro con la deprecacion."}
---

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/366127

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Evaluación de instrumentos 2026-10-03

Reusa `tools/provider_trace.py` solo para worker/proveedor; no observa el launcher por nodo, variables/interfaz efectiva, NCCL microtest ni CUDA Graph. No hay captura local de launcher/logs por rango; el registro existente `root-qwen-image-review.json` corresponde a otras imágenes y declara casos sin A/B, por lo que no cubre esta ficha. Estado `deferred_lab`: stack dual fijado, microtest y comparación receta/manual con logs por nodo y control de salida, antes de atribuir causalidad a NCCL/Ray.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: La corrección de orquestación requiere jobs NCCL/TP reales y control de fallo del coordinador; no se halló resultado local en la evidencia específica.
- Evidencia faltante para cierre: stack/digests; logs rank/node/collective; positivo multi-GPU y negativo de orquestación; rollback
- Siguiente acción: Preparar job NCCL/TP en canario multi-GPU con topología y digests fijados; probar coordinación sana y negativa y archivar trazas completas.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_05.json`, `tasks/evidence/DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01/ (directorio ausente al inspeccionar)`.
- Impedimentos de inspección: 1. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: Hilo 366127: TP=2 entre dos Spark con NCCL/launch-cluster.sh; /sys/class/infiniband no existe aqui y no hay cluster, Ray ni TP. La ficha misma dice que el directorio de evidencia no existe y que no hay captura local. (aplicabilidad otro_hardware, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_forum_nccl_tp_orchestration_correction_01`, `test_real_capture_close_gate_requires_raw_capture[DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01]`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01.md tasks/backlog/` y `status: open`.
