---
id: DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01
kind: task
domain: VERDICT
title: "Validar forum qwen service oomd cache fail 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_qwen_service_oomd_cache_fail_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01.** En un Spark single-node corriendo Qwen3.8 con Hermes, un dueño reporta que tras varias horas el modelo cambió de tarea mientras la prompt cache rondaba 95%; durante presión de memoria `systemd-oomd` mató el servicio Spark Studio y cayó Hermes. El dueño dice que añadió guard de cache específico del modelo y endureció el servicio, pero no hay versiones, logs ni A/B independiente ([381228, post 193](https://forums.developer.nvidia.com/t/381228/193)). Registrar PSI/swap/UMA, systemd-oomd kill y dependientes; preservar estado redactado antes de recovery. No desactivar OOMD globalmente ni reiniciar mientras persiste presión.

Fuentes: tasks/backlog/FEATURE-1358-CGROUP-05-CUELGUES.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
## Evaluación de instrumentos 2026-10-03

Reusa telemetría general para memoria/swap/PSI, pero no captura OOMD kill de systemd, servicio dependiente, ni estado de cache ligado al cambio de tarea. No hay logs/versions locales. Estado `deferred_lab`: canario de larga duración con versión fija, PSI/UMA/swap, eventos OOMD/servicio/dependencias redactados y recovery medido; no desactivar OOMD ni actuar durante presión.
