---
id: DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01
kind: task
domain: VERDICT
title: "Validar root tokenizer patch semantic gate 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_root_tokenizer_patch_semantic_gate_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01

Fuentes: https://forums.developer.nvidia.com/t/380244 (26 cuerpos capturados), https://forums.developer.nvidia.com/t/362824 (33 cuerpos). En 380244 el tokenizer limitaba silenciosamente texto a 2048 tokens y rechazaba imágenes de 2280 tokens; el dueño confirma después el fix del proveedor idéntico al cambio de `truncation` a `null`. En 362824 el patch MXFP4 pasa por retractaciones, reparación declarada de una carrera Marlin y cambios de precisión por capa; el último ensayo independiente conserva regresiones de calidad y timeouts. Throughput y arranque exitoso requieren un canary funcional adicional.

Propuesta: registrar revision/hash efectivos de tokenizer, checkpoint, imagen y patch; probar recepción completa de un prompt largo con centinelas verificables, imágenes por encima y debajo del antiguo límite, herramientas/Harmony y generación sostenida. Ante pérdida semántica, rechazar la promoción del candidato y conservar el runtime conocido. Riesgo: cambiar tokenizer completo altera otras reglas; preferir artefacto corregido del proveedor y comparar el delta exacto. Rollback: retirar overlay identificado y restaurar el snapshot/digest previo; verificar el mismo canary. `close_check`: fixture afectado reproduce truncamiento; fixture corregido conserva todos los centinelas y el conteo esperado; patch MXFP4 candidato pasa casos funcionales y soak con resultados/errores explícitos. Parches externos y ensayos en host siguen pendientes; esta ficha registra investigación.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
