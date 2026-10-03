---
id: DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01
kind: task
domain: VERDICT
title: "Validar root triton allocator patch state gate 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_root_triton_allocator_patch_state_gate_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
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
