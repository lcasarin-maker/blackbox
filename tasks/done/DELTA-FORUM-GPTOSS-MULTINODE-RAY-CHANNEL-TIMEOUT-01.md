---
id: DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01
kind: task
domain: VERDICT
title: "Validar forum gptoss multinode ray channel timeout 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Requiere dos nodos con vLLM/Ray y placement group multinodo; este equipo sirve un solo vLLM (nemotron-local) sin Ray y sin segundo nodo, y el criterio nunca tuvo verificador real (xfail). Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_gptoss_multinode_ray_channel_timeout_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01.** [358382, posts 18–23](https://forums.developer.nvidia.com/t/358382/18) documentan un fallo concreto en dos Spark con GPT-OSS-120B y vLLM V1/Ray: la solicitud deja el worker inactivo y el proceso termina con `RayChannelTimeoutError` tras `RAY_CGRAPH_get_timeout=300`, mientras logs previos muestran mismatch entre el TP=2 requerido y un placement group con 1 GPU reservada por nodo. El usuario inicialmente probó una imagen anterior a un cambio MXFP4; en post 20 el fallo continúa después de reconstruir, y en post 23 reporta éxito con imagen fechada `20260130`, `--rebuild-deps` y el build MXFP4, junto con `ray status`, carga completa y respuesta terminada. Esto no demuestra que el cambio específico resolviera la causa, ni que las recomendaciones de subnet/MTU fueran necesarias; los logs/configuración se publicaron en línea y no se ejecutaron ni auditaron. Para el gate multi-node del runtime, conservar una prueba de placement group/rank/GPU efectivo antes de admitir la carga, y una inferencia acotada que registre actividad por nodo, primer token/fin y timeout Ray. Anclar evidencia al tag/digest, commit y wheels reales. Cierre: con dos GB10 y el mismo checkpoint, verificar recursos asignados y una petición semántica repetida bajo imagen anterior/candidata cuando sea reproducible; la candidata debe completar sin timeout y registrar versiones efectivas. Mantener el digest anterior para rollback; no aumentar el timeout ni fijar MTU/NCCL como remedio sin A/B causal.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
## Evaluación de instrumentos 2026-10-03

Reusa `tools/provider_trace.py` solo para identidad/latencia provider-worker, sin observar placement groups, asignación TP/GPU por nodo ni estados de Ray. No hay Ray trace ni carga multi-node adjunta. Estado `deferred_lab`: necesitaría dos nodos fijados, placement/resource snapshot por rank/nodo, request acotado con actividad/finish por nodo y control negativo del timeout, conservando digests y rollback; no se ejecutó carga ni se cambió imagen.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: La evidencia actual dice que provider_trace no observa placement groups ni recursos TP por nodo; no hay Ray trace de dos nodos.
- Evidencia faltante para cierre: Dos nodos y digests fijados; placement/resource snapshot por nodo/rank; request con progreso por nodo; negativo del timeout y rollback.
- Siguiente acción: Solicitar corrida Ray de dos nodos con snapshot placement/resource por nodo/rank y request de progreso, incluyendo control del timeout sin aumentarlo; usar evaluador existente.
- Responsable del siguiente paso: BB; operador Luis para workload/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01.md`, `tools/provider_trace.py`, `tools/runtime_batch02_controls.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: El fallo es RayChannelTimeoutError con TP=2 y placement group de 1 GPU por nodo en dos Spark con GPT-OSS-120B; aqui no hay Ray, ni segundo nodo, ni ese modelo. Su close_check es un xfail y tools/provider_trace.py no observa placement groups. Nota: el dueno decidio el 2026-10-11 dejarla abierta; se pide reconsiderar. (aplicabilidad otro_hardware, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_forum_gptoss_multinode_ray_channel_timeout_01`, `test_real_capture_close_gate_requires_raw_capture[DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01]`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01.md tasks/backlog/` y `status: open`.
