---
id: DELTA-FORUM-NEMOTRON-SM121-PREBUILT-KERNEL-01
kind: task
domain: VERDICT
title: "Validar forum nemotron sm121 prebuilt kernel 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_nemotron_sm121_prebuilt_kernel_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-NEMOTRON-SM121-PREBUILT-KERNEL-01.** En DGX Spark GB10/SM121 con kernel 6.14.0-1015 y driver 580.95.05, un operador probó SGLang `:spark` (config Nemotron vieja) y `:latest`: el primer tag no conocía `NemotronHConfig`; el segundo cargó BF16 pero falló en primera inferencia por `sgl_kernel` RMSNorm sin kernel compatible. FP8 falló en quant op por la misma falta de código precompilado SM121. Cambiar `TRITON_PTXAS_PATH` al ptxas del sistema no lo resolvió: el error posterior provenía de extensiones `sgl_kernel`, no del ptxas. `llama.cpp` con Nemotron-H support branch compilada localmente a SM121 respondió; luego el main del repo incorporó soporte y un usuario confirmó que reconstruir desde main corrigió `unknown model architecture` ([354771, posts 4, 9, 40–42](https://forums.developer.nvidia.com/t/354771)). NVIDIA después anunció el playbook llama.cpp y trabajo SGLang/vLLM, pero este hilo no valida los tags posteriores. Gatear por arquitectura cada op requerida para modelo/backend (incluyendo load, primera inferencia y calidad de salida); `cuda available`, modelo cargado y server-ready no bastan. FP8 que genere basura debe bloquearse por salida/reference check. No generalizar el fallback llama.cpp ni recomendar `--enforce-eager` como fix de kernels ausentes.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
## Evaluación de instrumentos 2026-10-03

Reuso disponible: perfiles de runtime/host existentes no asocian una arquitectura SM121 con kernels compilados por operación y salida correcta. No hay evidencia local de builds/tags del hilo ni control de logits/salida. Estado `deferred_lab`: fijar modelo/backend/build y operaciones requeridas; canario de load, primera inferencia y referencia de salida contra build/control SM121, preservando el resultado. “CUDA available” o ready no son admisión.
