---
id: DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01
kind: task
domain: VERDICT
title: "Validar forum vllm ray gb10 resource fix 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Fallo de Ray (sin clave generica GPU en GB10) de dic-2025 en la imagen vllm:25.11, declarado corregido por el propio hilo en 26.01; este equipo no usa Ray ni cluster. Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01/e2e.txt"}
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

### Evidencia de instrumento (2026-10-03)

Estado: parcial, reutilizando del capture runtime los image refs e image IDs ya recolectados. No hay mapa de recursos Ray por nodo ni resultado de admisión positivo/negativo, por lo que la prueba funcional queda `could_not_run`. La ficha sigue abierta y su `close_check` original no cambió. Informe: `docs/evidence/BB-INSTRUMENTS-runtime.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: No hay mapa Ray por nodo ni admisión positiva/negativa con imagen y backend fijados.
- Evidencia faltante para cierre: image digest; mapa de recursos Ray/node; backend/SM/kernel; smoke positivo y negativo; rollback
- Siguiente acción: Ejecutar smoke de admisión y generación en canario GB10 con los tags fijados y guardar recursos Ray, kernel y resultado; comparar control sin GPU genérica.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_02.json`, `tasks/evidence/DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01/ (directorio ausente al inspeccionar)`.
- Impedimentos de inspección: 1. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: Reporte de dic-2025 sobre Ray marcando GB10 solo como accelerator_type; el propio hilo lo atribuye a la imagen vllm:25.11-py3 equivocada y un update dice corregido en 26.01. Aqui no hay Ray ni cluster y el contenedor vLLM de nemotron-local lo cubre el canario/huella (tools/canario_motor.py, tools/huella_host.py). (aplicabilidad otro_hardware, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_forum_vllm_ray_gb10_resource_fix_01`, `test_real_capture_close_gate_needs_actual_runtime_record[DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01]`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01.md tasks/backlog/` y `status: open`.
