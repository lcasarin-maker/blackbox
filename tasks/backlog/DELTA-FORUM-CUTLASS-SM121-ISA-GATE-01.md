---
id: DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01
kind: task
domain: VERDICT
title: "Validar forum cutlass sm121 isa gate 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_cutlass_sm121_isa_gate_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01.** Un hilo de CUTLASS/Python CuTe debate que las operaciones `tcgen05`/block-scaled FP4 están limitadas intencionalmente a arquitecturas SM100/SM110 y que SM12x (GB10/SM121) no implementa ese instruction path; un maintainer responde que FP4 en SM120/SM121 debe usar sus rutas MMA soportadas, no etiquetar la GPU como SM100 para pasar un guard ([359598, post 18](https://forums.developer.nvidia.com/t/359598/18)). Otra respuesta NVIDIA dice que el trabajo de rendimiento NVFP4 se concentra en backends CUTLASS/FlashInfer/vLLM, sin dar fecha o aceptar una configuración final ([post 40](https://forums.developer.nvidia.com/t/359598/40)). Antes de usar kernels externos, revisar el ISA/arch efectivo y gatear el backend por capacidad real; nunca forzar `CUTE_DSL_ARCH=sm_100a` para ocultar mismatch. El canary debe verificar compilación, logits finitos, exactitud contra referencia, requests/batching y soak bajo SM121. Los enlaces upstream y resultados de terceros del hilo no fueron auditados; no se demuestra rendimiento actual ni un fix listo.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

### Evidencia de instrumento (2026-10-03)

Estado: `needs_contract`. Antes del gate se debe fijar revisión CUTLASS/CuTe/backend, operación exacta y arquitectura compilada, y definir cómo source/build evidencia que ISA requerido está soportado o bloqueado antes del primer request. No se crea allowlist por nombre SM ni compatibilidad supuesta. Luego requiere canario SM121 con control de logits/exactitud. La ficha sigue abierta y `close_check` intacto. Informe: `docs/evidence/BB-INSTRUMENTS-feasibility-runtime.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: No hay build/smoke real para el target SM121 y stack/imagen fijados; el kernel faltante es específico de GPU/runtime.
- Evidencia faltante para cierre: digest/tag, GPU/SM efectiva, versión Cutlass/DSL y salida literal de kernel sano y control incompatible
- Siguiente acción: Ejecutar matriz mínima de compilación y canario funcional en nodo SM121 con versión fijada, usando target incompatible como negativo y guardando rollback.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_05.json`, `tasks/evidence/DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01/ (directorio ausente al inspeccionar)`.
- Impedimentos de inspección: 1. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: baja · lectura: completa.

GB10 es SM121 y el contenedor vLLM trae sus propios kernels; la ficha pide gatear backend por capacidad real y ficha reconoce 'No hay build/smoke real para SM121'. Sin kernels CUTLASS externos en uso local, el riesgo es latente.

Version para un solo nodo Gigabyte AI TOP ATOM: Registrar en tools/huella_host.py la capacidad de computo efectiva (nvidia-smi compute_cap) y la arch con que se compilo el wheel/imagen del contenedor, y alertar si difieren.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Avance 2026-10-13: control negativo de ISA producido y probado
`tasks/evidence/DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01/isa-negativo-local-20261013.txt`: con nvcc 13.0.88 un kernel vacio compila con `-arch=sm_121` (rc 0, `ok.sm_121.cubin`) y una instruccion `tcgen05.fence` (sm_100) falla en ptxas con `not supported on .target 'sm_121'` (rc 255). Cubre solo el control negativo de ISA; faltan el build de CUTLASS con commit fijado y el canario con soak en la GPU compartida con produccion, que exigen tocar el motor.
