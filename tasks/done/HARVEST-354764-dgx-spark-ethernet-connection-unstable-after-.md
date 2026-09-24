---
id: HARVEST-354764-dgx-spark-ethernet-connection-unstable-after-
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (354764-dgx-spark-ethernet-connection-unstable-after-november-2025-upda)"
status: done
closure_type: adopted_prior_implementation
closed_at: 2026-09-23
evidence: {"verificado_el_destino": "$ # el close_check de la ficha que lleva el trabajo, corrido el 2026-09-23\n$ grep -q 'red y CPU por nucleo (muestras de blackbox)' bin/bb\nrc=0  (0 = pasa)", "evidencia_del_destino": "Los 3 ficheros de tasks/done/FEATURE-RED-CPU-SCAN.md, comprobados presentes el 2026-09-23: tasks/evidence/FEATURE-RED-CPU-SCAN/e2e.txt, tasks/evidence/FEATURE-RED-CPU-SCAN/fail.txt, tasks/evidence/FEATURE-RED-CPU-SCAN/pass.txt", "limite_declarado": "El close_check de FEATURE-RED-CPU-SCAN.md es un grep sobre su propio texto: comprueba que la ficha diga lo que dice, no que la funcion sirva. Lo que sostiene el cierre son sus ficheros de evidencia, que traen comando, salida y control negativo.", "e2e": "tasks/evidence/FEATURE-RED-CPU-SCAN/e2e.txt", "fail": "tasks/evidence/FEATURE-RED-CPU-SCAN/fail.txt", "pass": "tasks/evidence/FEATURE-RED-CPU-SCAN/pass.txt"}
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-354764-dgx-spark-ethernet-connection-unstable-after-.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
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

- El documento describe el mecanismo de autonegresis EEE y transición de estados LPI (Low Power Idle) tras la OTA 7.3.1, donde EEE entra en estados de bajo poder agresivamente provocando `Tx LPI: 19 (us)` y `Tx LPI: 12 (us)`, lo cual rompe la continuidad física del enlace Ethernet causando congelamiento silencioso del tráfico y caída de paquetes. — `knowledge/references/forum_nvidia_354764_dgx-spark-ethernet-connection-unstable-after-november-2025-update-eee-energy-eff.md:"1. **Autonegresis EEE y transición de estados LPI (Low Power Idle):** El documento describe cómo después de la OTA 7.3.1, la EEE entra en estados de bajo poder demasiado agresivamente, provocando "Tx LPI: 19 (us)" y "Tx LPI: 12 (us)". Esto genera una transición de estado PHY que rompe la continuidad del enlace Ethernet, causando la observación de que "traffic silently stalls" y los "packets drop" después de unos minutos de conectividad."`
- Para el Paso 2, respecto a las fallas de la flota: el problema de inestabilidad ataca una categoría de falla de "inestabilidad de enlace por transición agresiva de ahorro de energía / regresión de gestión de energía a nivel PHY" que afecta directamente a DGX Spark en enlaces directos PC↔Spark tras actualizaciones OTA. — `knowledge/references/forum_nvidia_354764_dgx-spark-ethernet-connection-unstable-after-november-2025-update-eee-energy-eff.md:"El proyecto DGX Spark es el receptor directo de la falla de estabilidad de Ethernet y la solución propuesta ataca directamente la regresión de power-management introducida en la OTA 7.3.1. El "pain point" es la interferencia de EEE en la estabilidad del enlace PHY en modo direct PC↔Spark."`
- Para el Paso 2, el mecanismo de servicio systemd para ajustes persistentes de hardware mapea al paradigma de Atlas de configuración persistente de singularidades de hardware a nivel de nodo ("persistent node configuration quirks"). — `knowledge/references/forum_nvidia_354764_dgx-spark-ethernet-connection-unstable-after-november-2025-update-eee-energy-eff.md:"Aunque el documento no menciona Atlas explícitamente, el mecanismo de servicio systemd para "disable-eee" mapea al paradigma de Atlas de "persistent node configuration quirks" (por ejemplo, ajustes de firmware o estado de hardware al arranque)."`
- El veredicto técnico es COS (cosechado), detonando un ítem de backlog en DGX Spark para adoptar/endurecer la corrección en la imagen base; el disparador de reevaluación documentado es verificar si la próxima actualización OTA subsana el problema o si es necesario desactivar/bloquear EEE por defecto en el build de DGX Spark. — `knowledge/references/forum_nvidia_354764_dgx-spark-ethernet-connection-unstable-after-november-2025-update-eee-energy-eff.md:"El disparador de reevaluación es verificar si la próxima OTA subsana el problema o si es necesario blacklistear/desactivar EEE por defecto en la build de DGX Spark."`

## Por qué se sugiere para blackbox en concreto

El patron de deteccion de regresion de red post-OTA por polling se atribuye a 'Liberation Watchdog' ('monitoreo continuo de salud del sistema/regresiones de red'), y el servicio systemd persistente se atribuye a un 'paradigma de Atlas' generico -- ambos mecanismos (systemd + polling de metricas de hardware) son el dominio real de blackbox.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-ethernet-connection-unstable-after-november-2025-update-eee-energy-efficient-ethernet-workaround/354764
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_354764_dgx-spark-ethernet-connection-unstable-after-november-2025-update-eee-energy-eff.md`
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
