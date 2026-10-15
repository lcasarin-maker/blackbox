---
id: DELTA-FORUM-MEMORY-RECOVERY-SOAK-01
kind: task
domain: VERDICT
title: "Validar forum memory recovery soak 01"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "No hay llama.cpp RPC aqui (ni servidor ni cliente ni imagen): el mecanismo reportado es la memoria retenida por llama-rpc-server remoto. Decision de Luis 2026-10-14: cerrar sin sujeto; reabrir si se instala llama.cpp RPC o si MemAvailable no vuelve a linea base tras detener el contenedor vLLM."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-MEMORY-RECOVERY-SOAK-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-MEMORY-RECOVERY-SOAK-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-MEMORY-RECOVERY-SOAK-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-MEMORY-RECOVERY-SOAK-01.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior era `python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_memory_recovery_soak_01`, que sin captura real del sujeto no puede pasar; sin sujeto aqui no hay captura posible."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-MEMORY-RECOVERY-SOAK-01.** Dos operadores reportan que `llama.cpp` RPC conserva memoria tras la inferencia y que matar el proceso principal no libera la memoria del nodo remoto; detener `llama-rpc-server` o reiniciar la recupera. No aportan series temporales/versiones y otro reporte del hilo trata aparte un error de configuración Marlin ([361862](https://forums.developer.nvidia.com/t/361862)). Añadir soak multihora con memoria UMA/swap/PSI, estado de proceso servidor y recuperación comprobada tras terminar cliente y servidor; evitar matar/reiniciar automáticamente sin capturar evidencia.

Fuentes: tasks/backlog/FEATURE-1358-CGROUP-05-CUELGUES.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
## Evaluación de instrumentos 2026-10-03

Reusa `tools/atom_gpu_telemetry.py` y `tools/memory_profile.py` para observaciones puntuales del host; no hay serie temporal, identidad de proceso RPC remoto ni recuperación atribuible adjunta. Estado `deferred_lab`: soak multihora en stack/servidor fijado, series UMA/swap/PSI/RSS y PID/vida del RPC server, cliente y servidor cerrados en orden con medición pre/post y control sano. No se mató proceso ni reinició nodo; no se convirtió memoria desconocida en cero.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: La ficha documenta solo telemetría puntual; falta serie temporal y PID/vida del RPC remoto.
- Evidencia faltante para cierre: Stack/servidor/versiones; series UMA/swap/PSI/RSS y PID RPC; cierre ordenado cliente/servidor con medidas antes/después y control sano.
- Siguiente acción: Pedir al operador soak en stack fijado con serie UMA/swap/PSI/RSS atribuida a PID y cierre cliente/servidor ordenado, midiendo recuperación contra control sano.
- Responsable del siguiente paso: BB; operador Luis para workload/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-MEMORY-RECOVERY-SOAK-01.md`, `tools/atom_gpu_telemetry.py`, `tools/memory_profile.py`, `tools/hardware_batch02_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

El mecanismo fuente (llama-rpc-server remoto reteniendo memoria) no existe: no hay llama.cpp RPC ni multinodo. La parte util es el soak multihora de liberacion de memoria UMA tras terminar el cliente, aplicable al contenedor vLLM y a gpumem_historial (tools/gpumem_historial.py) y vigilante_memavail.py.

Version para un solo nodo Gigabyte AI TOP ATOM: Soak multihora sobre el contenedor vLLM: tras detener cliente y luego el contenedor, comprobar que MemAvailable/PSI vuelven a linea base, usando gpumem_historial y memavail; sin RPC remoto.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Root Cause
No aplica a este equipo: la memoria retenida es del `llama-rpc-server` remoto de llama.cpp; aqui no hay llama.cpp (ni binario, ni proceso, ni imagen) ni RPC multinodo.

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. El test que la vigilaba (`tests/test_debt_registration_controls.py::test_delta_forum_memory_recovery_soak_01`, un xfail) se retira junto con su entrada de `tests/known_failures.json`. El verificador y sus pruebas unitarias con fixtures siguen vivos.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (perfil medido, con control positivo de que las mismas herramientas encuentran lo que si existe) y `e2e` (la decision registrada). Datos de la maquina redactados con el PATRON de `tests/test_sin_datos_privados.py`. Para reabrirla si el sujeto aparece: `git mv tasks/done/DELTA-FORUM-MEMORY-RECOVERY-SOAK-01.md tasks/backlog/` y `status: open`.
