---
id: DELTA-ROOT-SUBAMBIENT-COOLING-AND-UMA-CANARY-01
kind: task
domain: VERDICT
title: "Validar root subambient cooling and uma canary 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_root_subambient_cooling_and_uma_canary_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

## DELTA-ROOT-SUBAMBIENT-COOLING-AND-UMA-CANARY-01 — refrigeración subambiente y presión UMA

Fuente: https://forums.developer.nvidia.com/t/375158. Revisados los 7 cuerpos y las 5 imágenes. El montaje usa ducto de cartón/cinta desde aire acondicionado a dos unidades apiladas. La captura AI TOP ATOM muestra CPU 74 °C, GPU 65 °C y RAM 95.8%; falta baseline comparable y duración. El relato de menor temperatura sigue siendo una afirmación del autor.

Acción propuesta: evaluar ambiente, humedad/punto de rocío, flujo y CPU/SoC/GPU junto con admisión UMA y salud de escritorio/SSH antes de aceptar una intervención subambiente. Riesgos: condensación, obstrucción y presión de memoria pese a GPU fría. Cierre: canario prolongado del workload y stack exactos, raw logs y comparación controlada; restaurar montaje y parámetros previos si falla. La revisión visual registra evidencia, no valida el montaje ni su eficacia.

Fuentes: tasks/backlog/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
