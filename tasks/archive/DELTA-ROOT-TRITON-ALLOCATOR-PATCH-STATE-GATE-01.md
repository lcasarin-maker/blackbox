---
id: DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01
kind: task
domain: VERDICT
title: "Validar root triton allocator patch state gate 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Hilo 359571: parche de allocator Triton para Ray TP2; este equipo no usa Ray ni TP2 y no aplica ese parche. Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01/pass.txt", "fail": "tasks/evidence/DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01/fail.txt", "e2e": "tasks/evidence/DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01.md", "expect": "exit_zero", "porque": "Cerrada por aplicabilidad (void_wontfix, decision de Luis 2026-10-13): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a un test por ficha que se retiro con la deprecacion."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01

Fuente: https://forums.developer.nvidia.com/t/359571/38 y /50–63, /87–92.

Ray TP2 falla con allocator Triton; eager permite cargar pero degrada. Post38 propone NullAllocator.__call__ global via .pth y torch.cuda.caching_allocator_alloc con except Exception:pass. Mantenedor confirma funcionar en50, pero necesita commit previo13397841ab469cecf1ed425c3f52a9ffc38139b5 además, pues startupfix solo deja1–2tok/s. Patches crash/performance después upstream integrados/revertidos fallan hunks y se ignoran(57–63). Baseimagebump causa torch._opaque_base ausente(87–88); freshbuildowner92recupera.

Acción: Catalogar patch como candidato específico por commit/Triton/Ray; detectar estado ausente/aplicado/supersedido/incompatible y verificar extensión efectiva en cada rank/hilo. Excepción silenciosa y patchskipping no certifican corrección. Probar carga, primera petición fría, generación semántica, warmup y prefix hit repetido. Preservar digest previo; rollback no toca otras imágenes.

Cierre: Fixture patch falla silenciosamente o fue supersedido identifica estado real; canary distingue startup arreglado de regresión y coldwarmup de hang con progreso. Auditoría de código y propiedad de memoria/alignment/stream antes de recomendar monkeypatch global; rollback probado.

Riesgos: Modifica allocatorglobal y se ejecuta por .pth; fragmento no prueba gestión/lifetime de memoria; Casos posteriores contradicen recetas anteriores; commits y wheel efectivo deben fijarse.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: El estado de patch/allocator no se valida por existencia de archivos; faltan replay funcional y control negativo en runtime compatible.
- Evidencia faltante para cierre: commit/digest del parche; stack GPU; asignación sana y caso de allocator defectuoso; salida y rollback
- Siguiente acción: Fijar revisión Triton/driver/modelo y ejecutar canario funcional más negativo de estado de patch; archivar diff efectivo y recuperación.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_05.json`, `tasks/evidence/DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01/ (directorio ausente al inspeccionar)`.
- Impedimentos de inspección: 1. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: El parche NullAllocator via .pth es para Ray TP2 con allocator Triton (hilo 359571); aqui no hay Ray ni TP2. La ficha misma anota directorio de evidencia ausente. (aplicabilidad otro_hardware, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_root_triton_allocator_patch_state_gate_01`, `test_real_capture_close_gate_requires_runtime_evidence[DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01]`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01.md tasks/backlog/` y `status: open`.
