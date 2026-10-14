---
id: DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01
kind: task
domain: VERDICT
title: "Validar forum qwen service oomd cache fail 01"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "Qwen no se sirve aqui: el motor sirve solo nemotron-local y no hay servicio Qwen, Spark Studio ni Hermes que systemd-oomd pueda matar (los pesos Qwen descargados en disco no estan servidos). systemd-oomd esta activo y no registra kills desde 2026-09-01. Decision de Luis 2026-10-14: cerrar sin sujeto; reabrir si se sirve Qwen o si systemd-oomd mata un servicio."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a tests/test_debt_registration_controls.py::test_delta_forum_qwen_service_oomd_cache_fail_01, un xfail que se retira con el cierre."}
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

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: Relato externo sin versiones, logs ni A/B; provocar presión/OOMD local conlleva ensayo de workload no disponible en lectura segura.
- Evidencia faltante para cierre: versiones e imágenes efectivas; PSI/swap/UMA; journal de oomd y dependientes; positivo/negativo A/B en canario; recuperación
- Siguiente acción: Fijar modelo/stack y diseñar canario recuperable con captura redactada de presión y oomd; comprobar rollback sin desactivar oomd global.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_02.json`, `tasks/evidence/DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01/ (directorio ausente al inspeccionar)`.
- Impedimentos de inspección: 1. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

systemd-oomd matando un servicio bajo presion es un mecanismo valido en este host (DEBT-DESPLIEGUES lista 'decisiones de oomd'; SPEC.md menciona oomd); el sujeto Qwen/Spark Studio/Hermes no existe aqui.

Version para un solo nodo Gigabyte AI TOP ATOM: Registrar kills de systemd-oomd (journal) junto con PSI/swap en las muestras de bb sample y su efecto sobre servicios dependientes; sin desactivar oomd.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Root Cause
No aplica a este equipo: el reporte es un servicio Qwen3.8 con Hermes muerto por systemd-oomd bajo presion de cache. Aqui `/v1/models` lista solo nemotron-local, no hay unidad qwen/hermes/studio y el journal de systemd-oomd no tiene ningun kill desde 2026-09-01. Hay tres directorios de pesos Qwen en `/srv/ai/models/llm` que no sirve nadie.

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. Los tests que la vigilaban (`tests/test_debt_registration_controls.py::test_delta_forum_qwen_service_oomd_cache_fail_01` y la parametrizacion `tests/test_runtime_batch03_controls.py::test_real_capture_close_gate_needs_actual_runtime_record[DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01]` (la filtra `_ficha_abierta`)) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (perfil medido: modelo servido, contenedores, directorios de pesos, systemd-oomd activo con 0 kills, con control positivo) y `e2e` (la decision registrada). Para reabrirla si el sujeto aparece: `git mv tasks/done/DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01.md tasks/backlog/` y `status: open`.
