---
id: DELTA-FORUM-QWEN38-LONG-RUN-JSON-CORRECTNESS-CANARY-01
kind: task
domain: VERDICT
title: "Validar forum qwen38 long run json correctness canary 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_qwen38_long_run_json_correctness_canary_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-QWEN38-LONG-RUN-JSON-CORRECTNESS-CANARY-01.** [380248, posts 27, 34, 36–38](https://forums.developer.nvidia.com/t/380248/27) contiene un reporte aislado de Qwen3.8-27B: un operador dice que varios proveedores/quant mostraron salidas JSON cada vez menos válidas durante tareas autónomas largas, con aproximadamente 3/4 malformadas tras 30 minutos; no presenta prompts, respuestas ni hashes que permitan atribuirlo a AutoRound, FP8 KV, temperatura o MTP. Otros participantes expresan preocupación por deriva de calidad en procesos largos y por diferencias de BF16/FP8, pero reconocen que son observaciones subjetivas y no ofrecen pares controlados. En la misma discusión, la ficha inicial permite `max_model_len=1010000`, aunque sus pruebas visibles de throughput terminan a profundidad 8192; ese número de configuración no prueba integridad a un millón de tokens. Conservar como señal para la canaria semántica de runtime: sobre una versión/modelo exactos, ejecutar tareas largas repetidas que requieran JSON validable, guardar checksums/digest del checkpoint, backend, tokenizer, template, sampling, KV y MTP, y comparar control BF16 contra candidato cuantizado/FP8 si el stack lo soporta. Rechazar degradación objetiva de formato o contenido bajo criterios definidos antes del ensayo; mantener rollback de imagen/checkpoint. Cierre requiere fixtures reproducibles con respuestas completas y comparación pareada/soak; la anécdota por sí sola no demuestra regresión ni prescribe BF16.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

### Evidencia de instrumento (2026-10-03)

Estado: `blocked` para exactitud JSON de tareas largas. `tools/chat_sse_capture.py` preserva deltas de texto, pero no reconstruye/valida la respuesta completa ni dispone de fixtures/captura nativa pareada; no aporta evidencia sobre deriva semántica. La ficha sigue abierta y su `close_check` original no cambió. Informe: `docs/evidence/BB-INSTRUMENTS-contracts.md`.
