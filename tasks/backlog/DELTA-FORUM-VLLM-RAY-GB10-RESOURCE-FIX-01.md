---
id: DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01
kind: task
domain: VERDICT
title: "Validar forum vllm ray gb10 resource fix 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_vllm_ray_gb10_resource_fix_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01.** Un reporte de diciembre de 2025 dijo que Ray marcaba GB10 solo como `accelerator_type:GB10`, sin clave genérica `GPU`, y que vLLM devolvía “Current node has no GPU available”; el mismo hilo contiene confusión sobre imágenes usadas y una respuesta señala que el nodo del autor corría `nvcr.io/nvidia/vllm:25.11-py3`, no el contenedor de la receta referenciada. TensorRT-LLM NVFP4 también falló por kernel SM121 ausente en ese stack. Un update posterior indica que el playbook se actualizó y el fix se verificó con vLLM 26.01 ([355126, post 36](https://forums.developer.nvidia.com/t/355126/36)). Registrar como regresión/corrección por versión, no como estado presente: el verificador debe guardar imagen digest/tag, Ray resource map por nodo, backend vLLM, SM, kernel y resultado de smoke. No mantener como verdad actual el fallo de 25.11 ni declarar resuelto en otros tags sin ejecutar el caso positivo/negativo con el tuple elegido. El adjunto de benchmark NCCL de 35.5 MB y repos/scripts comunitarios no se inspeccionaron.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
