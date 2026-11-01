---
id: FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION
kind: task
domain: THERMAL
title: "Validar contención térmica para residencia de modelos y calor CPU o idle"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION --evidence tasks/evidence/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION", "expect": "exit_zero", "porque": "Verificador propuesto pendiente: requiere evidencia del caso positivo, controles negativos, compatibilidad OEM y recuperación/rollback; la ficha registra trabajo abierto."}
---

## Trabajo en la ATOM

Perfil termico CPU/GPU/ACPI con frescura para la admision de modelos en la ATOM, rama corroborada para calor de CPU en reposo y A/B del extractor de aire ya instalado.

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/348760
- https://forums.developer.nvidia.com/t/349668
- https://forums.developer.nvidia.com/t/dual-spark-ducted-cooling-cage/365302
- https://forums.developer.nvidia.com/t/deliberations-on-4-sparks-cluster-advantages/373482
- https://forums.developer.nvidia.com/t/369381
- https://forums.developer.nvidia.com/t/372469
- https://forums.developer.nvidia.com/t/380282
- https://forums.developer.nvidia.com/t/381029
- https://forums.developer.nvidia.com/t/dgx-spark-gb10-fans-do-not-spin-in-headless-boot-mode-temperature-rises-to-70-c/361960
- https://forums.developer.nvidia.com/t/dgx-spark-runs-hot-and-firmware-update-keeps-repeating/370198
- https://forums.developer.nvidia.com/t/unexpected-shutdown-during-comfyui-inference-on-dgx-spark-occurs-on-two-units/362277
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-aiden-recipe-from-reddit-1m-token-session-operational-cuda-12-1-tailored-for-dgx-spark-gb10/372268/415
- https://forums.developer.nvidia.com/t/running-hot-even-at-idle/364635
- https://forums.developer.nvidia.com/t/suggestions-for-reducing-idle-power-consumption/348562
- https://forums.developer.nvidia.com/t/381549
- https://forums.developer.nvidia.com/t/377044
- https://forums.developer.nvidia.com/t/371614
- https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205
- https://forums.developer.nvidia.com/t/msi-edgexpert-suddenly-power-off-during-llama-benchy-possible-pd-firmware-issue/362585
- https://forums.developer.nvidia.com/t/348562/1
- https://forums.developer.nvidia.com/t/366590/1
- https://forums.developer.nvidia.com/t/361639/293
- https://forums.developer.nvidia.com/t/383964/4
- https://forums.developer.nvidia.com/t/372608/5
- https://forums.developer.nvidia.com/t/373251/1
- https://forums.developer.nvidia.com/t/358034/1
- https://forums.developer.nvidia.com/t/dgx-spark-power-clarification/349668/1
- https://forums.developer.nvidia.com/t/375119/1
- https://forums.developer.nvidia.com/t/374791/1
- https://forums.developer.nvidia.com/t/376103
- https://forums.developer.nvidia.com/t/381192
- https://forums.developer.nvidia.com/t/383939
- https://forums.developer.nvidia.com/t/373199
- https://forums.developer.nvidia.com/t/372662
- https://forums.developer.nvidia.com/t/375158

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Delta y prevención/resolución

atom_gpu_telemetry.py lee zonas cada5s, corroboración exige carga GPU≥60W y mitigación se limita a tres jobs propios. La cobertura para calor CPU/idle y modelos residentes requiere prueba; esta auditoría del código deja pendiente demostrar un miss en incidente real.

Reutilizar muestras existentes para distinguir GPU/CPU/SoC, headroom por zona, residencia y concurrencia. Evaluar admisión y acciones sobre workloads con ownership explícito; conservar debounce/controles antispikes. Probar una rama corroborada CPU/idle y conectar fan/CX7; parar procesos por nombre o matar servicios compartidos carece de objetivo verificable.

## Validación, riesgo y cierre

calor CPU sostenido, fan detenido en idle, spike ACPI aislado, GPU caliente real y sensores ilegibles. A/B por OEM/firmware/modelos con presupuesto y soak declarados, medir throughput local antes de afirmar mejora; control sin modelos residentes y rollback de políticas. Dar una acción preventiva verificada o declarar limitación, jamás convertir permiso/sensor faltante en sano.

El verificador de close_check todavía debe implementarse; ejecutar esta ficha exige evidencia adicional y deja registradas las consultas que no pueden correr. Ningún cambio del host se aplica al registrar la propuesta. Detalle fuente preservado en tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_*.json y threads/.

## Avance de ejecución 2026-10-02

Revisión de _corroboracion confirma que historial caliente sostenido con carga GPU ociosa devuelve descarta. No existe medición local que calibre reemplazo seguro para CPU/idle; 0 cambios de compuerta, 0 A/B y 0 claims de throughput. Falta medir sensores independientes/CPU y fan con controles antispike antes de automatizar pausa.

Evidencia y pendientes: `tasks/evidence/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION/progress.txt`. Conserva `open`; la captura de estado verifica el instrumento y deja pendiente el ensayo de recuperación/prevención requerido.

## BB-LOCAL-EXTRACTOR-VALIDATION-01 — extractor instalado por Luis

Luis reportó el 2026-10-02 que instaló una solución casera con extractor de aire y observó una mejora de rendimiento. Montaje físico existente; magnitud y reducción de crashes/hangs pendientes de medición. Incorporar esta intervención local al diseño preventivo y de remediación de BB.

Validación: documentar OEM/equipo, montaje, orientación, alimentación y ambiente; conservar el montaje actual como referencia operativa. Comparar modelo, stack, contexto, concurrencia y duración equivalentes con throughput útil, latencia, temperaturas GPU/CPU/SoC, clocks, potencia y throttling, junto a UMA/swap/PSI, progreso del servicio y respuesta SSH/escritorio. Separar el efecto del extractor de cambios de clocks/software. Si falta una condición previa comparable, registrar la mejora cualitativa y medir estabilidad del montaje actual.

Cierre: prueba reproducible bajo carga sostenida con criterios de rendimiento y estabilidad; parametrizar margen térmico por OEM/workload a partir de evidencia. Riesgos: flujo obstruido o recirculación, polvo, vibraciones, alimentación y temperatura de la fuente. Rollback: conservar descripción del montaje original y restaurar parámetros verificados ante degradación. Este registro autoriza investigación; cualquier prueba disruptiva o modificación física requiere alcance específico.

## Revisión externa de fronteras de potencia — 2026-10-03

La revisión de la nota externa (una referencia externa) contrasta 140 W TDP SoC, 240 W fuente y 233,2 W Maximum Power del ensayo regulatorio NVIDIA P4242. Rechaza atribuir 233,2−140 a auxiliares por mezclar TDP y medición, corrige 240−140−100=0 W y conserva desconocida la frontera de ~164 W. Reutiliza BB-POWER-TELEMETRY-BOUNDARY: registrar contador/dominio, AC/DC, intervalo, OEM/workload y errores; ninguna resta sustituye medidas pareadas. Ensayo eléctrico local: 0; validación externa ~164 W: could_not_run=1. Status y close_check permanecen abiertos.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: No hay calibración local de sensores independientes/criterios OEM ni A/B/soak del workload térmico; reportes externos y un montaje existente no cuantifican estabilidad o throughput.
- Evidencia faltante para cierre: No hay calibración local de sensores independientes/criterios OEM ni A/B/soak del workload térmico; reportes externos y un montaje existente no cuantifican estabilidad o throughput.
- Siguiente acción: Coordinación BB: fijar perfiles OEM/workload y reglas para unknown/stale; operador Luis: ejecutar medición pareada de residencia/load con captura externa y rollback. Ref explícita: tasks/backlog/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION-direct-close-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_09.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION-direct-close-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: aplica · utilidad: alta · lectura: completa.

Ficha paraguas de 28 KB con decenas de hilos de otros OEM (ASUS, MSI, FE, clusters); el nucleo local es calor CPU/idle y modelos residentes en un ATOM con vLLM residente, donde atom_gpu_telemetry.py descarta calor sostenido con GPU ociosa y termico_predictivo ya esta en observar.

Version para un solo nodo Gigabyte AI TOP ATOM: Reducirla al caso de un nodo: perfil termico CPU/GPU/ACPI con frescura, rama corroborada para calor CPU/idle (hoy descartada por _corroboracion) y A/B del extractor ya instalado por Luis; mover los hilos de cluster, FieldDiag/RMA y enfriamiento ajeno a fichas hijas o deprecarlos.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Criterios ejecutables de `tools.verify_forum_finding` (2026-10-14)
Los criterios ejecutables de `tools.verify_forum_finding` se miden en esta ficha: su `close_check` corre ese verificador contra la captura real del sujeto. La meta-ficha `DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01`, que pedia implementarlos, se cerro el 2026-10-14 como `duplicate` (voto de Luis: consolidar en la ficha sujeto): el verificador existe y hoy, sin esa captura, sale con could_not_run (rc=2); conseguir la captura es trabajo de esta ficha.
