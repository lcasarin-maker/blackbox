---
id: HARVEST-366125-ethernet-port-on-dgx-spark-is-not-working
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (366125-ethernet-port-on-dgx-spark-is-not-working)"
status: done
closure_type: adopted_prior_implementation
closed_at: 2026-09-23
evidence: {"verificado_el_destino": "$ # el close_check de la ficha que lleva el trabajo, corrido el 2026-09-23\n$ grep -q 'red y CPU por nucleo (muestras de blackbox)' bin/bb\nrc=0  (0 = pasa)", "evidencia_del_destino": "Los 3 ficheros de tasks/done/FEATURE-RED-CPU-SCAN.md, comprobados presentes el 2026-09-23: tasks/evidence/FEATURE-RED-CPU-SCAN/e2e.txt, tasks/evidence/FEATURE-RED-CPU-SCAN/fail.txt, tasks/evidence/FEATURE-RED-CPU-SCAN/pass.txt", "limite_declarado": "El close_check de FEATURE-RED-CPU-SCAN.md es un grep sobre su propio texto: comprueba que la ficha diga lo que dice, no que la funcion sirva. Lo que sostiene el cierre son sus ficheros de evidencia, que traen comando, salida y control negativo.", "e2e": "tasks/evidence/FEATURE-RED-CPU-SCAN/e2e.txt", "fail": "tasks/evidence/FEATURE-RED-CPU-SCAN/fail.txt", "pass": "tasks/evidence/FEATURE-RED-CPU-SCAN/pass.txt"}
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-366125-ethernet-port-on-dgx-spark-is-not-working.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
reason: "CERRADA 2026-09-23 como adopted_prior_implementation. La adopcion de esta sugerencia se implemento con codigo real en un commit ANTERIOR y ese trabajo vive en tasks/done/FEATURE-RED-CPU-SCAN.md, cerrada con su propia evidencia (3 ficheros, los 3 presentes). Esta ficha era la EVALUACION, no el trabajo: su trigger era un puntero a trabajo ya terminado, no una vigilancia, asi que cerrarla no apaga nada. Verificado antes de cerrar: el close_check de FEATURE-RED-CPU-SCAN.md corre y pasa."
---

## Qué es esto

Sugerencia de cosecha, no un defecto. Atlas (la KB compartida de la flota) leyó una fuente
externa y encontró mecanismos que podrían servirle a **este proyecto** específicamente, por
dominio. Nadie de blackbox pidió esta evaluación -- es cosecha pasiva. **La decisión
de adoptar, adaptar o descartar es 100% de este proyecto.**

Cruzada antes de escribirse contra `.simplecode/fork_own.json` de este repo (si existe) para
evitar sugerir algo que ya está vendorizado -- ver DGX-505 en Atlas, donde `own_chats` cazó 3
falsos positivos de este tipo en el primer lote.

## Mecanismos encontrados, con su cita (tal como Atlas los verificó)

- El primer mecanismo es la extracción de reportes forenses y análisis del estado del enlace mediante herramientas del sistema (`nvidia-bug-report` y `ethtool enP7s7`), lo que permite obtener parámetros de negociación, velocidad y presencia de señal física — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:7`
- El segundo mecanismo es el diagnóstico de interrupciones de hardware mediante el conteo de vectores MSI-X, verificando si el dispositivo genera actividad tras la inicialización del driver — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:9`
- El tercer mecanismo es la validación de registros VPD y EEPROM en el driver de red para comprobar la integridad de datos de firmware/hardware requeridos — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:11`
- Para el mecanismo de inspección por `ethtool` y logs de diagnóstico: ataca la categoría de falla de desconexión física no detectada o fallo de negociación de enlace (enlace en NO-CARRIER pese a driver activo); a nuestra escala se traduce de un diagnóstico manual a scripts o sondas locales de inspección periódica de estado de interfaces; y formaliza diagnósticos de conectividad que se ejecutan ad-hoc — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:7-17`
- Para el mecanismo de conteo de vectores MSI-X: ataca la categoría de falla de fallo silencioso de inicialización de hardware (el driver carga pero el dispositivo queda inerte sin despachar interrupciones); a nuestra escala se mapea de inspección manual de `/proc/interrupts` a heurísticas del watchdog local que alertan si un periférico inicializado mantiene sus contadores en cero; y nombra la verificación de vida útil de interrupciones que antes no se cuantificaba — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:9-19`
- Para el mecanismo de validación de VPD y EEPROM: ataca la categoría de falla de corrupción o discrepancia de firmware/configuración de hardware base; a nuestra escala pasa de análisis forense post-mortem en logs a validaciones de arranque (sanity checks al inicializar el nodo); y nombra la inspección de flags de integridad de hardware que se asumían implícitamente correctos — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:11-15`
- El documento clasifica formalmente la fuente con un veredicto de producto cosechable por documentar el patrón forense de diagnóstico ante fallos de hardware localizados en unidades específicas — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:23`
- El disparador de reevaluación declarado para este veredicto es la revisión de firmware/BIOS o el reemplazo de EEPROM para la unidad afectada — `knowledge/references/forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md:26`

## Por qué se sugiere para blackbox en concreto

Los tres mecanismos (ethtool/nvidia-bug-report, conteo de vectores MSI-X, validación VPD/EEPROM) son diagnóstico forense y heurísticas de watchdog de hardware -- dominio exacto de blackbox ('monitoreo de hardware, logs'); el dictamen sólo consideró la lista rota (DGX Spark/Atlas/Liberation Watchdog) en 'lo que no se pudo determinar' y nunca a blackbox.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/ethernet-port-on-dgx-spark-is-not-working/366125
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_366125_ethernet-port-on-dgx-spark-is-not-working.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.

## Root Cause

Atlas cosecho un mecanismo de una fuente externa y lo sugirio para blackbox por
dominio. **Nadie de blackbox pidio esta evaluacion** -- es cosecha pasiva, y la
ficha existe para dejar constancia de la DECISION, no para hacer el trabajo.

La decision fue ADOPTAR. El trabajo real se escribio como codigo y vive en
`tasks/done/FEATURE-RED-CPU-SCAN.md`, cerrada por su cuenta y con su propia evidencia. Esta
ficha no tenia codigo que escribir: su entregable era decidir, y decidio.

Por eso el `closure_type` es `adopted_prior_implementation` y no
`void_wontfix` (seria falso: SI se hizo trabajo) ni `duplicate` (no lo es: la
evaluacion y la implementacion son cosas distintas) ni
`relocated_prior_verification` (presupone que esta ficha ya estaba `done` en un
commit anterior, y seguia abierta).

## Regression Test

El de la ficha que lleva el trabajo, que es donde vive el sujeto:

```
grep -q 'red y CPU por nucleo (muestras de blackbox)' bin/bb
```

Corrido el 2026-09-23 antes de cerrar esta: **pasa**. Si esa verificacion
dejara de pasar, la que se reabre es `FEATURE-RED-CPU-SCAN.md` -- ahi esta el codigo --, no esta
evaluacion, que no tiene nada que arreglar.

## Verification Evidence

La de `tasks/done/FEATURE-RED-CPU-SCAN.md`, comprobada presente el 2026-09-23 (3 de 3 ficheros):

- `tasks/evidence/FEATURE-RED-CPU-SCAN/e2e.txt`
- `tasks/evidence/FEATURE-RED-CPU-SCAN/fail.txt`
- `tasks/evidence/FEATURE-RED-CPU-SCAN/pass.txt`

LIMITE DECLARADO: el `close_check` de `FEATURE-RED-CPU-SCAN.md` es un `grep` sobre su propio
texto en la mayoria de estas fichas, o sea que comprueba que la ficha diga lo
que dice, no que la funcion sirva. Lo que sostiene el cierre de verdad son sus
ficheros de evidencia, que traen comando, salida y control negativo. Se dice
en vez de presentar el `grep` como si fuera una prueba funcional.
