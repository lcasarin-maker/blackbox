---
id: HARVEST-351579-reinstalling-the-nvidia-driver-on-dgx-spark
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (351579-reinstalling-the-nvidia-driver-on-dgx-spark)"
status: done
closure_type: adopted_prior_implementation
closed_at: 2026-09-23
evidence: {"verificado_el_destino": "$ # el close_check de la ficha que lleva el trabajo, corrido el 2026-09-23\n$ grep -q 'nvidia-container-runtime\\\\|prestart hook' tasks/done/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK.md\nrc=0  (0 = pasa)", "evidencia_del_destino": "Los 3 ficheros de tasks/done/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK.md, comprobados presentes el 2026-09-23: tasks/evidence/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK/e2e.txt, tasks/evidence/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK/fail.txt, tasks/evidence/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK/pass.txt", "limite_declarado": "El close_check de FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK.md es un grep sobre su propio texto: comprueba que la ficha diga lo que dice, no que la funcion sirva. Lo que sostiene el cierre son sus ficheros de evidencia, que traen comando, salida y control negativo.", "e2e": "tasks/evidence/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK/e2e.txt", "fail": "tasks/evidence/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK/fail.txt", "pass": "tasks/evidence/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK/pass.txt"}
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-351579-reinstalling-the-nvidia-driver-on-dgx-spark.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
reason: "CERRADA 2026-09-23 como adopted_prior_implementation. La adopcion de esta sugerencia se implemento con codigo real en un commit ANTERIOR y ese trabajo vive en tasks/done/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK.md, cerrada con su propia evidencia (3 ficheros, los 3 presentes). Esta ficha era la EVALUACION, no el trabajo: su trigger era un puntero a trabajo ya terminado, no una vigilancia, asi que cerrarla no apaga nada. Verificado antes de cerrar: el close_check de FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK.md corre y pasa."
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

- Mecanismo 3 (Paso 1): Ejecución del hook de contenedor en runtime OCI (`prestart hook #0`) con fallback a modo legacy ante la falta de carga del driver NVML — `knowledge/references/forum_nvidia_351579_reinstalling-the-nvidia-driver-on-dgx-spark.md:"error running prestart hook #0: exit status 1, stdout: , stderr: Auto-detected mode as 'legacy'"`
- Mecanismo 4 (Paso 1): Generación y recolección de diagnósticos y registros del sistema mediante script automatizado para soporte — `knowledge/references/forum_nvidia_351579_reinstalling-the-nvidia-driver-on-dgx-spark.md:"sudo nvidia-bug-report.sh"`
- Interrogatorio (Paso 2): El mecanismo de hook de inicio de contenedor ataca la categoría de falla de fallo de inicialización de runtime de contenedor por driver de GPU no cargado o no firmado bajo arranque seguro — `knowledge/references/forum_nvidia_351579_reinstalling-the-nvidia-driver-on-dgx-spark.md:"El fallo de init de contenedor debido a incoherencia de driver. Aunque el hilo es DGX Spark, el síntoma (driver no cargado para contenedor) es un caso de uso típico para Liberation Watchdog"`

## Por qué se sugiere para blackbox en concreto

'el síntoma (driver no cargado para contenedor) es un caso de uso típico para Liberation Watchdog' -- detección de fallo de driver/hardware vía hooks OCI y logs de diagnóstico (nvidia-bug-report.sh) es monitoreo de hardware/systemd, dominio explícito de blackbox, miembro real nunca considerado por la lista rota.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/reinstalling-the-nvidia-driver-on-dgx-spark/351579
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_351579_reinstalling-the-nvidia-driver-on-dgx-spark.md`
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
`tasks/done/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK.md`, cerrada por su cuenta y con su propia evidencia. Esta
ficha no tenia codigo que escribir: su entregable era decidir, y decidio.

Por eso el `closure_type` es `adopted_prior_implementation` y no
`void_wontfix` (seria falso: SI se hizo trabajo) ni `duplicate` (no lo es: la
evaluacion y la implementacion son cosas distintas) ni
`relocated_prior_verification` (presupone que esta ficha ya estaba `done` en un
commit anterior, y seguia abierta).

## Regression Test

El de la ficha que lleva el trabajo, que es donde vive el sujeto:

```
grep -q 'nvidia-container-runtime\\|prestart hook' tasks/done/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK.md
```

Corrido el 2026-09-23 antes de cerrar esta: **pasa**. Si esa verificacion
dejara de pasar, la que se reabre es `FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK.md` -- ahi esta el codigo --, no esta
evaluacion, que no tiene nada que arreglar.

## Verification Evidence

La de `tasks/done/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK.md`, comprobada presente el 2026-09-23 (3 de 3 ficheros):

- `tasks/evidence/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK/e2e.txt`
- `tasks/evidence/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK/fail.txt`
- `tasks/evidence/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK/pass.txt`

LIMITE DECLARADO: el `close_check` de `FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK.md` es un `grep` sobre su propio
texto en la mayoria de estas fichas, o sea que comprueba que la ficha diga lo
que dice, no que la funcion sirva. Lo que sostiene el cierre de verdad son sus
ficheros de evidencia, que traen comando, salida y control negativo. Se dice
en vez de presentar el `grep` como si fuera una prueba funcional.
