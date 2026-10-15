---
id: DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01
kind: task
domain: VERDICT
title: "Validar forum dualspark power reset recovery 01"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "Exige dos o mas nodos Spark enlazados por CX7; este equipo es un solo nodo GIGABYTE AI TOP ATOM sin dispositivo Mellanox/InfiniBand (los modulos mlx5 estan cargados pero /sys/class/infiniband esta vacio y lspci no lista ConnectX). Decision de Luis 2026-10-14: cerrar sin sujeto; reabrir si se anade un segundo nodo."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior era `python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_dualspark_power_reset_recovery_01`, un xfail que se retira con el cierre."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01.** En el hilo de dos GB10 [361639, post 293](https://forums.developer.nvidia.com/t/361639/293), un usuario de Qwen3.5-122B-FP8 reportó que, después de apagar y desconectar alimentación USB-C, recuperó SCP sobre ConnectX a >700 MB/s, respuesta general del sistema y benchmark llama-benchy (p. ej. tg32 ~32.5 tok/s en esa configuración). No publicó A/B repetido ni aisló el estado del suministro, CX7, clocks, cableado o workload; cuenta como recuperación reportada, no como causa/fix universal. Añadir la secuencia a la investigación existente de baja potencia/rendimiento: guardar muestras y logs fuera del host, comparar clocks/potencia/rendimiento y enlace CX7 antes/después, y ejecutar shutdown limpio según OEM antes de retirar/reconectar alimentación en un nodo canary. No ejecutar ciclo automático ni recomendarlo como intervención general; preservar datos y rollback de cualquier cambio de cable/configuración.
- **`BB-GX10-HIGHCONTEXT-NO-POST-POWERON`** — An ASUS GX10 owner reports a high-context workload freeze near 120K tokens followed by power-on ending after about two seconds without BIOS; overnight power drain and a second Spark adapter did not restore boot. The proposed internal… Fuente: [383964](https://forums.developer.nvidia.com/t/383964/4).
- **`BB-GB10-OEM-SHUTDOWN-AND-IDLE-THERMAL-CONTROLS`** — Across user reports in a mixed Spark/Gigabyte AI Top Atom discussion: one shutdown attributed to thermal behavior reportedly stopped after BIOS update (versions not stated); a separate owner of two Atoms and two Sparks says both OEMs… Fuente: [372608](https://forums.developer.nvidia.com/t/372608/5).
- **`BB-GB10-THERMAL-SILENT-LOCK-RMA-VALIDATION`** — One A.7 Spark reports repeatable hard power loss under GPU load without pstore, vmcore, OOM, Xid or thermal-trip logs; idle GPU reported at 47–48C and last sample at 79C/82W. In a separate two-FE case, 12 silent locks during 262K… Fuente: [373251](https://forums.developer.nvidia.com/t/373251/1).
- **`BB-FE-THERMAL-FIELDDIAG-POWER-CUTOFF-COVERAGE`** — An MSI GX10 owner reports hard power cutoff around GPU burn temperature 80C and attached no-boot thermal FieldDiag code 020000021139; FE Spark owners elsewhere report similar silent cutoff even while generic FieldDiag passes. Another… Fuente: [358034](https://forums.developer.nvidia.com/t/358034/1).

Fuentes: tasks/backlog/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Evaluación de instrumentos 2026-10-03

No existe evidencia local del par Spark aislado, del perfil OEM de power reset ni de observaciones previas/posteriores; inventario/hostdiag no prueba recuperación causal. Estado `deferred_lab`: requiere procedimiento OEM aprobado, series externas antes/después y controles repetidos que separen power/CX7/clocks/workload, con rollback/criterio seguro. No se efectuó power cycle ni se alteró estado del host.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: No se puede demostrar ciclo de corte/reset y recuperación de dos unidades sin lab físico y participación del operador.
- Evidencia faltante para cierre: modelos/OEM/firmware exactos; estados antes/después de power reset; tráfico sano/negativo y rollback
- Siguiente acción: Ejecutar ciclo A/B en dos nodos canary aprobados, capturar estado de energía/enlace y tráfico y demostrar rollback OEM.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_05.json`, `tasks/evidence/DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01/ (directorio ausente al inspeccionar)`.
- Impedimentos de inspección: 1. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

El reporte es de dos GB10 con CX7 (SCP >700 MB/s tras apagar y desconectar USB-C), parte pareada inaplicable. Pero tools/reloj_atascado.py ya imprime como remedio el ciclo de corriente completo y se confirmo el reloj atascado en esta maquina el 2026-10-12 (663 MHz bajo carga), asi que la mitad de un solo nodo (rendimiento bajo y recuperacion tras ciclo de corriente) existe.

Version para un solo nodo Gigabyte AI TOP ATOM: Con un ciclo de corriente completo ejecutado por Luis segun el OEM Gigabyte, correr `bb reloj --prueba` antes y despues y guardar clocks, potencia y tflops fuera del host; sin parte CX7 ni ciclo automatico.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Root Cause
No aplica a este equipo: el reporte es de dos nodos GB10 enlazados por CX7. Aqui hay un solo nodo (GIGABYTE AI TOP ATOM): lspci no lista ConnectX, `/sys/class/infiniband` esta vacio aunque los modulos mlx5 esten cargados, y `/etc/hosts` nombra un solo host. La mitad de un nodo (reloj atascado y recuperacion tras ciclo de corriente) la lleva `tools/reloj_atascado.py` (`bb reloj`).

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. El test que la vigilaba (`tests/test_debt_registration_controls.py::test_delta_forum_dualspark_power_reset_recovery_01`) se retira junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (perfil medido, con control positivo de que las mismas herramientas encuentran lo que si existe) y `e2e` (la decision registrada). Datos de la maquina redactados con el PATRON de `tests/test_sin_datos_privados.py`. Para reabrirla si el sujeto aparece: `git mv tasks/done/DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01.md tasks/backlog/` y `status: open`.
