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

La ficha permanece abierta. El selector original ya está integrado y llama a `tools.hardware_batch03_controls.verify` para este ID exacto. La ejecución del 2026-10-04 devolvió UNKNOWN, fail=0, could_not_run=1 por captura requerida ausente o contrato incompleto. El comando literal y su salida están registrados en `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch03-integration/original-selectors-after-reader-hardening.json`. Los tests de fixtures verifican el control; el cierre requiere el sujeto real y su evidencia específica.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: La inspección fotográfica prueba montaje reportado, no humedad/punto de rocío, presión UMA, carga sostenida ni baseline matched; falta canario comparable con rollback.
- Evidencia faltante para cierre: La inspección fotográfica prueba montaje reportado, no humedad/punto de rocío, presión UMA, carga sostenida ni baseline matched; falta canario comparable con rollback.
- Siguiente acción: Coordinación BB: fijar protocolo de ambiente/UMA/performance; operador Luis: aportar lecturas de ambiente y ejecutar canario reversible bajo carga previamente aprobada. Ref explícita: tasks/backlog/DELTA-ROOT-SUBAMBIENT-COOLING-AND-UMA-CANARY-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-ROOT-SUBAMBIENT-COOLING-AND-UMA-CANARY-01.md y tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_03.json.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-ROOT-SUBAMBIENT-COOLING-AND-UMA-CANARY-01.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_03.json`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
