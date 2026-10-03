---
id: DELTA-FORUM-VLLM-GB10-ARCH-AND-BUILD-MATRIX-01
kind: task
domain: VERDICT
title: "Validar forum vllm gb10 arch and build matrix 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_vllm_gb10_arch_and_build_matrix_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-FORUM-VLLM-GB10-ARCH-AND-BUILD-MATRIX-01

[348862](https://forums.developer.nvidia.com/t/run-vllm-in-spark/348862) contains 159 available post bodies with distinct owner-reported failures across GB10 builds: unresolved CUTLASS symbols; Triton 3.5.0 PTX rejected for `sm_121a`; CUDA/architecture-specific CMake kernel selection; a vLLM 0.11.1rc4 TorchInductor autotune failure; and later vLLM 0.12.0 startup after community patch/dependency changes. NVFP4 performance and parser/model compatibility also vary by stack. The changes are confounded, so they do not establish a general fix.

Extend the exact-stack gate with compiler/PTXAS, architecture flags, wheel provenance and resolver output, model/quantization, and the selected backend. Require build/import, model load, functional generation and finite-output checks on pinned digests, with a mismatched-toolchain negative control and image rollback. Treat eager mode, nightly packages, architecture exclusions, and community patches as experiments until validated on the target model. Linked repositories, screenshots, and external log files were not audited; post 117 itself says its patch excerpt is truncated.

**`BB-MTP-SPECULATIVE-DECODE-LONG-SOAK`.** El hilo [374846, posts 13, 43, 56, 65, 69, 71, 75, 79, 82, 84, 87, 96–97, 103–104](https://forums.developer.nvidia.com/t/deepseek-v4-flash-dspark-on-2x-dgx-spark-gb10-big-single-stream-speed-boost-60-67-tok-s-1m-context-now-with-concurrency/374846/97) añade un caso de dos Spark con DeepSeek-V4-Flash-DSpark. Un operador informa CUDA illegal-memory-access/gibberish; otro midió caída sostenida de ~56 a ~34 tok/s, hasta 0.1–1.1 tok/s con dos agentes, KV 96–98%, OOM y recuperación temporal tras reiniciar el contenedor. Driver 580.159.03 y la teoría de starvación/corrupción de KV aparecen como hipótesis, sin logs de incidente ni A/B que pruebe causalidad. Hay contrapruebas de distinta carga/versiones: un batch nocturno 250K reportó cero abort/OOM/wedge (post 56), el autor anunció un runtime fix (71) mientras persiste tool leakage para otro usuario (75), una build comunitaria vLLM 0.23.1rc1 con fixes específicos pasó cuatro needle probes 300–500K (87), y una receta posterior v0.25.1 informa salida limpia pero menor rendimiento que custom images (104). Añadir soak de tráfico multiagente con pool KV/concurrency acotados, métricas de cola/espera por petición, finish reason, salud del proceso, CUDA/Xid, aceptación por posición y verificación de contenido/tools; introducir backpressure antes de caída y captura de evidencia antes de recovery. Comparar target-only frente a DSpark y probar cold-resume; fijar el soak sobre la duración observada. Un restart que restaura velocidad solo caracteriza recuperación, no identifica causa. Repositorios, PR #4, código y adjuntos externos no auditados; no endorsar recetas de topk ni limpieza de caché. ID literal `BB-MTP-SPECULATIVE-DECODE-LONG-SOAK`.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
