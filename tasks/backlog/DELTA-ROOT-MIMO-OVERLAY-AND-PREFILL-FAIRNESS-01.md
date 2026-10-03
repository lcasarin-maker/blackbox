---
id: DELTA-ROOT-MIMO-OVERLAY-AND-PREFILL-FAIRNESS-01
kind: task
domain: VERDICT
title: "Validar root mimo overlay and prefill fairness 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_root_mimo_overlay_and_prefill_fairness_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-ROOT-MIMO-OVERLAY-AND-PREFILL-FAIRNESS-01

Fuentes: https://forums.developer.nvidia.com/t/373669.

Post132 modelo cargado sin errores emite ASCII aleatorio y acceptance de draft casi cero; overlay ausente publicado después permite funcionar (135–139), sin causa kernel aislada. Posts161/163 sesión350K segunda petición reprocess prompt/stall y prefill de una detiene decode de otra. Load_model OOM antecede KV(40/44); bajar utilización KV omite ese pico.

Acción: Manifiesto efectivo por nodo de imagen, checkpoint, overlay, draft, tokenizer y mods con hashes; resolver symlinks en mounts y probar artefactos antes de cargar. Canary semántico real y por modalidad, per-rank y etapas. Admisión incluye coldload/draft previo KV. Escenario concurrente con prefill largo y decode corto, progreso y límites de espera; comparar chunked-prefill/batch como candidatos con riesgo de memoria, sin umbral universal.

Cierre: Fixture overlay ausente/symlink roto falla antes de servir. Respuesta semántica real y error específico en modalidad no validada. Soak prefill/decode simultáneo mide espera por petición y recuperación acotada; retorno a digest/config anterior probado.

Riesgos: Mods publicados tarde y recetas contradicen eager/Ray/comando; código externo no auditado; Éxito de un owner no resuelve todos los OOM ni demuestra calidad omnimodal.

**`BB-DSPARK-DRAFT-QUANTIZATION-FAIL-CLOSED`.** [371652, post 49](https://forums.developer.nvidia.com/t/step-3-7-flash-is-supported-in-community-docker-on-dgx-spark/371652/49) aporta un caso distinto al de DeepSeek: en Step-3.7 Flash NVFP4, un operador de 2×Spark TP=2 reporta que el cargador MTP intenta copiar el vocabulario completo de ancho 4096 a un shard local de ancho 2048 y aborta; el serving sin MTP funciona en el mismo montaje. La causa observada es incompatibilidad de forma/sharding al cargar el draft, sin parche ni corrección posterior auditados. Añadir un test de carga distribuida TP=2 que compruebe cada tensor contra la forma local por rank y falle antes de activar MTP, con nombre, formas y rank en el error; TP=8 no cubre TP=2. La conversación también contiene informes contradictorios sobre `libtorch_cuda.so` en rebuilds comunitarios (posts 42, 44–45), así que sirven para probar la matriz exacta de imagen/runtime, sin atribuir una regresión general. No se auditaron contenedores, código ni artefactos enlazados. Hallazgo literal: `BB-DSPARK-DRAFT-QUANTIZATION-FAIL-CLOSED`.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
