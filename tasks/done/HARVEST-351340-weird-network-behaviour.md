---
id: HARVEST-351340-weird-network-behaviour
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (351340-weird-network-behaviour)"
status: done
closure_type: adopted_prior_implementation
closed_at: 2026-09-23
evidence: {"verificado_el_destino": "$ # el close_check de la ficha que lleva el trabajo, corrido el 2026-09-23\n$ grep -q 'red y CPU por nucleo (muestras de blackbox)' bin/bb\nrc=0  (0 = pasa)", "evidencia_del_destino": "Los 3 ficheros de tasks/done/FEATURE-RED-CPU-SCAN.md, comprobados presentes el 2026-09-23: tasks/evidence/FEATURE-RED-CPU-SCAN/e2e.txt, tasks/evidence/FEATURE-RED-CPU-SCAN/fail.txt, tasks/evidence/FEATURE-RED-CPU-SCAN/pass.txt", "limite_declarado": "El close_check de FEATURE-RED-CPU-SCAN.md es un grep sobre su propio texto: comprueba que la ficha diga lo que dice, no que la funcion sirva. Lo que sostiene el cierre son sus ficheros de evidencia, que traen comando, salida y control negativo.", "e2e": "tasks/evidence/FEATURE-RED-CPU-SCAN/e2e.txt", "fail": "tasks/evidence/FEATURE-RED-CPU-SCAN/fail.txt", "pass": "tasks/evidence/FEATURE-RED-CPU-SCAN/pass.txt"}
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-351340-weird-network-behaviour.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
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

- El segundo mecanismo descrito corresponde a la gestión de swap e I/O de discos, donde la extensión del swapfile a 80GB mitiga la ausencia de swap por defecto pero introduce E/S de disco pesada cuando se agota la memoria, congestionando la red local al competir por el mismo bus PCIe/M.2 — `knowledge/references/forum_nvidia_351340_weird-network-behaviour.md:"2.  **Gestión de Swap e I/O Discos:** Ausencia de swap configurada por defecto y dependencia de memoria física. Extensión del swapfile a 80GB (Post #6) introduce I/O de disco pesado cuando la memoria se agota, creando picos de E/S que congestionan la red local compitiendo por el mismo bus PCIe/M.2. [Fuente: Post #6]."`
- Para el interrogatorio (Paso 2), el mecanismo 1 ataca la categoría de falla conocida de agotamiento de memoria unificada / inanición de E/S de red frente a contención de bus en inferencia, mapeándose al proyecto Atlas para políticas de prioridad de memoria en pipelines RAG — `knowledge/references/forum_nvidia_351340_weird-network-behaviour.md:"*   **Mecanismo 1 (Contención de Memoria):** **Atlas** — Enruteo y gestión de pipelines RAG donde la inferencia de LLM grandes compite por los recursos de memoria sistémica con las solicitudes de red entrantes, requiriendo políticas de prioridad de memoria."`
- Para el mecanismo 2, ataca la categoría de falla de degradación por thrashing / saturación de bus de almacenamiento que bloquea subsistemas adyacentes, vinculándose a la estructuración y límites de I/O en pipelines de datos — `knowledge/references/forum_nvidia_351340_weird-network-behaviour.md:"*   **Mecanismo 2 (Gestión de Swap e I/O):** **Cuenza** — Validación y optimización de estructuras JSON/tablas y pipelines de datos. El problema de swap revela una necesidad de configuración estructurada de límites de I/O para evitar cuellos de botella en la ingestión de datos."`
- Para el mecanismo 3, ataca la categoría de falla de partición de conectividad / pérdida de plano de control de gestión frente a saturación de plano de datos, mapeándose a Liberation Watchdog para verificación y aislamiento del tráfico de administración — `knowledge/references/forum_nvidia_351340_weird-network-behaviour.md:"*   **Mecanismo 3 (Enrutamiento IPv6):** **Liberation Watchdog** — Monitoreo de conectividad y salud de la red. Los conflictos de prioridad de red entran en el dominio de verificación de watchdog para asegurar que el tráfico de gestión no se ahogue por cargas de trabajo de IA."`
- El disparador de reevaluación establecido es el monitoreo de métricas de uso de VRAM vs. ancho de banda de red durante carga de inferencia en configuraciones DGX Spark vanilla — `knowledge/references/forum_nvidia_351340_weird-network-behaviour.md:"Disparador de reevaluación: Monitoreo de métricas de uso de VRAM vs. ancho de banda de red durante carga de inferencia en configuraciones DGX Spark vanilla."`

## Por qué se sugiere para blackbox en concreto

Mecanismo 3 se asigna a 'Liberation Watchdog -- Monitoreo de conectividad y salud de la red... para asegurar que el tráfico de gestión no se ahogue por cargas de trabajo de IA'; ese es exactamente el dominio de blackbox ('telemetria de la AI TOP ATOM: monitoreo de hardware, logs, systemd units'), miembro real nunca considerado por la lista rota de 5.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/weird-network-behaviour/351340
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_351340_weird-network-behaviour.md`
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
