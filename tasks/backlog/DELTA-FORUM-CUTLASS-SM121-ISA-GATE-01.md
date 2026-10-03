---
id: DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01
kind: task
domain: VERDICT
title: "Validar forum cutlass sm121 isa gate 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_cutlass_sm121_isa_gate_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01.** Un hilo de CUTLASS/Python CuTe debate que las operaciones `tcgen05`/block-scaled FP4 están limitadas intencionalmente a arquitecturas SM100/SM110 y que SM12x (GB10/SM121) no implementa ese instruction path; un maintainer responde que FP4 en SM120/SM121 debe usar sus rutas MMA soportadas, no etiquetar la GPU como SM100 para pasar un guard ([359598, post 18](https://forums.developer.nvidia.com/t/359598/18)). Otra respuesta NVIDIA dice que el trabajo de rendimiento NVFP4 se concentra en backends CUTLASS/FlashInfer/vLLM, sin dar fecha o aceptar una configuración final ([post 40](https://forums.developer.nvidia.com/t/359598/40)). Antes de usar kernels externos, revisar el ISA/arch efectivo y gatear el backend por capacidad real; nunca forzar `CUTE_DSL_ARCH=sm_100a` para ocultar mismatch. El canary debe verificar compilación, logits finitos, exactitud contra referencia, requests/batching y soak bajo SM121. Los enlaces upstream y resultados de terceros del hilo no fueron auditados; no se demuestra rendimiento actual ni un fix listo.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
