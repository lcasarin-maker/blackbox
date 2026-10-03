---
id: DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01
kind: task
domain: VERDICT
title: "Validar forum minimax toolcall functional canary 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_minimax_toolcall_functional_canary_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01

Fuente: https://forums.developer.nvidia.com/t/minimax-m2-7-nfvp4-recipe-benchmarks/366324 (127/127 cuerpos revisados).

Un operador informa que `health 200`, la carga de 15 shards, CUDA graphs y una generación simple pasaron en `vllm/vllm-openai:latest`, pero la segunda petición —la primera llamada de herramienta— se bloqueó con timeout de shared-memory broadcast y `EngineDeadError`. Tras reiniciar, también se bloquearon peticiones simples. El mismo operador reporta después éxito con `nvcr.io/nvidia/vllm:26.06-py3` / vLLM 0.22.1 y Ray instalado; cambió varias piezas a la vez, así que el hilo no demuestra cuál resolvió el fallo. También hay relatos de caracteres insertados en llamadas de herramienta en versiones específicas de vLLM/FlashInfer, con configuraciones y resultados posteriores distintos. No hay reproducción independiente ni auditoría de repositorios, imágenes y adjuntos enlazados.

Extender el gate existente para separar readiness HTTP de readiness funcional. En cada digest fijado de imagen, driver, vLLM, Ray, FlashInfer, cuantización y parser, ejecutar en el mismo proceso: texto simple → llamada mock de herramienta con nombre de archivo puntuado → texto simple. Verificar argumentos byte-exactos, resultado del mock, finish reason y vida del proceso; conservar logs de timeout/RPC y comprobar rollback. Un health 200 o una sola generación no basta para promover la pila.

**`BB-QWEN38-DUALSPARK-CUDAGRAPH-STARTUP-GATE`.** En Qwen3.8-Flash-Next FP8 sobre dos GB10, TP=2 y expert parallel, el autor de la receta dice que la captura CUDA Graph bloqueaba el warmup en `shm_broadcast` durante collectives cross-node; el mismo owner informa que `--enforce-eager` arranca el mismo cluster después de una bisección (#40). La versión indicada es vLLM `0.1.dev20073+g8e685d198`; el build y la causa no se verificaron independientemente. Añadir captura por rank de fase/progreso y un watchdog acotado que bloquee admisión si el warmup queda atascado; comparar eager y graph solo en esta tupla y hacer un canary semántico antes de abrir tráfico. Cualquier reintento debe conservar logs. No convertir eager ni tamaños de grafo en default global. Ver también los deltas de carga picos UMA y PLE mixto de este hilo bajo `FORUM-00-CHECKPOINT-LOADER-UMA-BUDGET`. Source: [381440/40](https://forums.developer.nvidia.com/t/qwen3-8-flash-fp8-dual-sparks/381440/40), y contexto de versión [381440/69](https://forums.developer.nvidia.com/t/qwen3-8-flash-fp8-dual-sparks/381440/69). ID literal `BB-QWEN38-DUALSPARK-CUDAGRAPH-STARTUP-GATE`.

**Delta `FORUM-00-CHECKPOINT-LOADER-UMA-BUDGET` — 381440.** Un owner reporta que safetensors eager dejó ambos nodos sin SSH/HTTP al cargar Qwen3.8-Flash-Next FP8; requirió power-cycle. Con `--safetensors-load-strategy lazy` el load completó a util `.83`, con mínimo ~8 GiB libres (post62). Es una mitigación reportada por un solo stack, no un umbral universal; incluir modo de loader y pico de page-cache/UMA en cold-load canary, obtener logs por nodo y retener rollback antes de recomendar una modalidad. Además, un owner identifica que checkpoint NVFP4 conserva shards PLE FP8 y escala BF16 pese a ruta de config mixta; vLLM falla por faltar `ngram_embedding.weight_scale` (post69). El autor advierte que descartar la escala corrompe embeddings; el gate de loader debe comprobar coherencia config↔tensor y fallar con claridad, y el parche sugerido espera revisión/A-B antes de adopción. No se auditaron repos ni diffs externos.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
