---
id: DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01
kind: task
domain: VERDICT
title: "Validar root glm53 queued request progress gate 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_root_glm53_queued_request_progress_gate_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01

Fuente: https://forums.developer.nvidia.com/t/382939/178 y https://forums.developer.nvidia.com/t/382939/181.

Posts 178/181: tras más de 40 horas, una petición decodifica mientras hasta siete quedan sin prefill durante 14 minutos. Reducir max_num_seqs de 8 a 4 reproduce antes; segundo episodio declara KV máximo 37%, frente a 99% del primero. Endpoint vivo y porcentaje KV por sí solos omiten este hang parcial.

Acción preventiva/correctiva: Canario por petición y etapa: antigüedad de cola, inicio/progreso de prefill, tokens decodificados, concurrencia real y terminación/cancelación. Retención de prefix cache y recompilación se validan con prompts reales repetidos; TTFT largo esperado se distingue por progreso. Cuotas de concurrencia y recuperación acotada deben preservar otras peticiones y registrar causa desconocida.

Cierre: Soak multiusuario por digest/commit/modelo con fixture de una petición activa y otras bloqueadas. Detectar bloqueo con KV bajo, permitir prefill lento que progresa, limitar reintentos y probar rollback. Benchmarks breves o TEB no cierran estabilidad del host.

Riesgo y límites: Un solo propietario; recetas cambiantes y logs externos sin auditoría. Diagnóstico externo central sobre freezes de driver permanece `could_not_run`; ausencia de causa aislada impide convertir una versión de driver en fix universal.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
