---
id: DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01
kind: task
domain: VERDICT
title: "Validar forum cutlass sm121 isa gate 01"
status: done
closed_at: 2026-10-15
closure_type: relocated_prior_verification
reason: "El parser de identidad del verificador, la prueba y la captura real (canario 1 250 000/1 250 000, control negativo de ISA) se commitearon en el commit anterior; este commit solo mueve la ficha. Control negativo: con el parser viejo el verificador da unknown (fail.txt), con canary completed = requests-1 da fail (e2e.txt)."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01/e2e.txt"}
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

## Avance 2026-10-14: build CUTLASS v4.8.0 fijado, canario SM121 y negativo reproducidos; falta `dmidecode` (root)
Autorizado por Luis (2026-10-14). Lab fuera del repo: `~/.cache/bb-trabajo/cutlass-lab/` (CUTLASS `v4.8.0` = `098de2a652cf8f00fd70b2df54051c7eccbb855a`, CuTe va en el mismo arbol; nvcc 13.0.88, `-arch=121a`, cmake+ninja). Recolector: `tasks/evidence/DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01/capture.py` -> `commands.json`, `canary.json`, `experiment-plan.json`. Canario: ejemplo 79a (GEMM NVFP4 con escalas por bloque, ruta MMA SM120/121, no tcgen05) parcheado para volcar 32 salidas del dispositivo y de la referencia host; 1 250 000 iteraciones, 22.31 s de GPU, `Disposition: Passed`, error maximo 0.0. Negativo `tcgen05.fence` con `-arch=sm_121` rechazado por ptxas (rc 255) y control positivo (kernel vacio, rc 0) en la misma corrida.
Verificador despues: `unknown` (could_not_run=1), razon `manufacturer/product/BIOS tuple incomplete`: `dmidecode -t system` exige root (`/sys/firmware/dmi/tables/smbios_entry_point: Permission denied`), sin sudo no se puede capturar. Diagnostico sintetico (NO es evidencia, `verifier-diagnostics-synthetic-dmi.txt`): inyectando la salida de dmidecode, el resto pasa y los controles negativos del verificador (negativo aceptado, fila negativa ausente, logit perturbado) fallan como deben. Limites declarados: el canario es un GEMM, no logits de un modelo en vLLM ni requests/batching reales (batch=1, concurrency=1); soak de 20 s declarado en el plan. Cierre pendiente: Luis ejecuta `sudo python3 tasks/evidence/DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01/capture.py 1250000` (o captura dmidecode con root) y corre el verificador. La ficha sigue abierta.

## Root Cause
La ficha no tenia sujeto medido: faltaba una compilacion y un canario reales de CUTLASS en SM121 con la revision fijada, y el verificador `tools/hardware_batch02_controls.py` no podia leer la identidad de una maquina real. `_identity` buscaba la clave literal `BIOS Version`, que `dmidecode` nunca imprime (imprime `Version:` dentro del bloque `BIOS Information`); sus pruebas usaban datos sinteticos con esa clave inventada, asi que ninguna captura real habria pasado.

## Regression Test
`tests/test_hardware_batch02_controls.py::test_identity_reads_bios_version_from_the_real_dmidecode_bios_block`: usa salida con la forma real de `dmidecode` y comprueba que la `Version:` del bloque de sistema NO se toma como version de BIOS (control negativo dentro de la prueba). Sin el arreglo la prueba falla (medido con el cambio retirado: `1 failed`). El `close_check` original (`test_delta_forum_cutlass_sm121_isa_gate_01`) corre el verificador sobre `tasks/evidence/DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01/` y pasa.

## Verification Evidence
Captura real del 2026-10-15 con `capture.py` bajo sudo de Luis: GIGABYTE AI TOP ATOM, BIOS 5.36_0ACUM08, kernel 6.17.0-1032-nvidia, nvcc 13.0.88, CUTLASS v4.8.0 (`098de2a6...`), `cutlass3x_sm120_collective_builder` NVFP4 block-scaled GEMM 1024^3. Canario: 1 250 000 de 1 250 000 iteraciones completadas, logits identicos a la referencia (error maximo 0.0), 23.0 s de GPU. Control negativo del ISA: compilar `tcgen05` para `sm_121` falla con exit 255 mientras el kernel vacio compila. Veredicto del verificador: `pass`; con `completed = requests - 1` da `fail` (e2e.txt). Antes del arreglo: `unknown` (fail.txt). Serie y UUID de `dmidecode` redactados en `commands.json`. Limite declarado: el canario prueba la ruta SM120/SM121 soportada y la negativa de `tcgen05`; no mide rendimiento ni sustituye una prueba con vLLM. Los reportes del foro siguen sin validacion de terceros.
