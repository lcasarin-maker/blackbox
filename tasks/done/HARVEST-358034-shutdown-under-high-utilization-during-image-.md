---
id: HARVEST-358034-shutdown-under-high-utilization-during-image-
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (358034-shutdown-under-high-utilization-during-image-generation-using-q)"
status: done
closure_type: adopted_prior_implementation
closed_at: 2026-09-23
evidence: {"verificado_el_destino": "$ # el close_check de la ficha que lleva el trabajo, corrido el 2026-09-23\n$ grep -q 'clasificador de causa' tasks/done/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR.md\nrc=0  (0 = pasa)", "evidencia_del_destino": "Los 3 ficheros de tasks/done/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR.md, comprobados presentes el 2026-09-23: tasks/evidence/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR/e2e.txt, tasks/evidence/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR/fail.txt, tasks/evidence/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR/pass.txt", "limite_declarado": "El close_check de FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR.md es un grep sobre su propio texto: comprueba que la ficha diga lo que dice, no que la funcion sirva. Lo que sostiene el cierre son sus ficheros de evidencia, que traen comando, salida y control negativo.", "e2e": "tasks/evidence/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR/e2e.txt", "fail": "tasks/evidence/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR/fail.txt", "pass": "tasks/evidence/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR/pass.txt"}
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-358034-shutdown-under-high-utilization-during-image-.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
reason: "CERRADA 2026-09-23 como adopted_prior_implementation. La adopcion de esta sugerencia se implemento con codigo real en un commit ANTERIOR y ese trabajo vive en tasks/done/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR.md, cerrada con su propia evidencia (3 ficheros, los 3 presentes). Esta ficha era la EVALUACION, no el trabajo: su trigger era un puntero a trabajo ya terminado, no una vigilancia, asi que cerrarla no apaga nada. Verificado antes de cerrar: el close_check de FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR.md corre y pasa."
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

- Mecanismo 2 (Consumo de memoria y límite de VRAM): la carga de ~36 GB de memoria en arquitectura GB10 con 384 GB/s induce estabilidad térmica en VRAM provocando corte antes que el TDP — `knowledge/references/forum_nvidia_358034_shutdown-under-high-utilization-during-image-generation-using-qwen.md:"2. **Consumo de memoria y límite de VRAM (36 GB / arquitectura GB10):** La generación de imagen con Qwen carga ~36 GB de memoria de GPU. El modelo GB10 posee 384 GB/s de ancho de banda y una configuración de VRAM que, bajo carga sostenida, alcanza el límite de utilidad de memoria. La presión sobre el controlador de memoria induce estabilidad térmica en la región de los VRAMs, provocando el corte antes que el limitador de potencia (TDP) puro."`
- Paso 2 para Mecanismo 1: ataca la categoría de falla conocida de "corte de energía por sobrecalentamiento no gestionado / apagado abrupto por thermal throttling" en Atlas — `knowledge/references/forum_nvidia_358034_shutdown-under-high-utilization-during-image-generation-using-qwen.md:"| Protección térmica de GPU | **Atlas** | Enrutamiento incorrecto de carga de trabajo cuando la temperatura supera el umbral de 80°C en hardware consumer (GB10), causando interrupción de inferencia RAG o fine-tuning. |"`
- Paso 2 para Mecanismo 2: ataca la categoría de falla conocida de "agotamiento de memoria unificada / saturación térmica de VRAM" mapeado a Cuenza — `knowledge/references/forum_nvidia_358034_shutdown-under-high-utilization-during-image-generation-using-qwen.md:"| Consumo de memoria / límite VRAM | **Cuenza** | Validación estructurada de cargas de trabajo FinTech que exceden los 36 GB de VRAM en servidores de inferencia; requiere particionamiento o offloading a multi-GPU. |"`
- Paso 2 para Mecanismo 3: ataca la categoría de falla conocida de "condición de carrera en gestión de energía / shutdowns no graciosos" en Liberation Watchdog — `knowledge/references/forum_nvidia_358034_shutdown-under-high-utilization-during-image-generation-using-qwen.md:"| Ruteo de interrupciones / gestión de energía | **Liberation Watchdog** | Detector de bucles térmicos falsos o shutdowns no graciosos en nodos offline; necesidad de *heartbeat* y flags de supervivencia de hardware. |"`
- La prueba con gpu_burn confirma el fallo térmico del dispositivo GB10 alcanzando 85°C antes de apagarse no graciosamente — `knowledge/references/forum_nvidia_358034_shutdown-under-high-utilization-during-image-generation-using-qwen.md:"Running gpu_burn is enough to show that this is simply a thermal issue. The unit heats then dies (non gracefully). Seems like a bad thermal design."`

## Por qué se sugiere para blackbox en concreto

Mecanismo 3 (ruteo de interrupciones/ACPI, detección de apagados no graciosos coincidentes con init de BT/USB) se mapeó a 'Liberation Watchdog', satélite inexistente; el dominio de monitoreo de hardware/telemetría del GB10 y detección de shutdowns no graciosos corresponde a blackbox ('telemetria de la AI TOP ATOM: monitoreo de hardware, logs, systemd units').

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/shutdown-under-high-utilization-during-image-generation-using-qwen/358034
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_358034_shutdown-under-high-utilization-during-image-generation-using-qwen.md`
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
`tasks/done/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR.md`, cerrada por su cuenta y con su propia evidencia. Esta
ficha no tenia codigo que escribir: su entregable era decidir, y decidio.

Por eso el `closure_type` es `adopted_prior_implementation` y no
`void_wontfix` (seria falso: SI se hizo trabajo) ni `duplicate` (no lo es: la
evaluacion y la implementacion son cosas distintas) ni
`relocated_prior_verification` (presupone que esta ficha ya estaba `done` en un
commit anterior, y seguia abierta).

## Regression Test

El de la ficha que lleva el trabajo, que es donde vive el sujeto:

```
grep -q 'clasificador de causa' tasks/done/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR.md
```

Corrido el 2026-09-23 antes de cerrar esta: **pasa**. Si esa verificacion
dejara de pasar, la que se reabre es `FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR.md` -- ahi esta el codigo --, no esta
evaluacion, que no tiene nada que arreglar.

## Verification Evidence

La de `tasks/done/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR.md`, comprobada presente el 2026-09-23 (3 de 3 ficheros):

- `tasks/evidence/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR/e2e.txt`
- `tasks/evidence/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR/fail.txt`
- `tasks/evidence/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR/pass.txt`

LIMITE DECLARADO: el `close_check` de `FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR.md` es un `grep` sobre su propio
texto en la mayoria de estas fichas, o sea que comprueba que la ficha diga lo
que dice, no que la funcion sirva. Lo que sostiene el cierre de verdad son sus
ficheros de evidencia, que traen comando, salida y control negativo. Se dice
en vez de presentar el `grep` como si fuera una prueba funcional.
