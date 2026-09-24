---
id: HARVEST-365609-nvidia-dgx-spark-continuously-freezing-hangin
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (365609-nvidia-dgx-spark-continuously-freezing-hanging-and-or-rebooting)"
status: done
closure_type: adopted_prior_implementation
closed_at: 2026-09-23
evidence: {"verificado_el_destino": "$ # el close_check de la ficha que lleva el trabajo, corrido el 2026-09-23\n$ grep -q 'USB/xHCI' tasks/done/FEATURE-USB-XHCI-FORENSICS.md\nrc=0  (0 = pasa)", "evidencia_del_destino": "Los 3 ficheros de tasks/done/FEATURE-USB-XHCI-FORENSICS.md, comprobados presentes el 2026-09-23: tasks/evidence/FEATURE-USB-XHCI-FORENSICS/e2e.txt, tasks/evidence/FEATURE-USB-XHCI-FORENSICS/fail.txt, tasks/evidence/FEATURE-USB-XHCI-FORENSICS/pass.txt", "limite_declarado": "El close_check de FEATURE-USB-XHCI-FORENSICS.md es un grep sobre su propio texto: comprueba que la ficha diga lo que dice, no que la funcion sirva. Lo que sostiene el cierre son sus ficheros de evidencia, que traen comando, salida y control negativo.", "e2e": "tasks/evidence/FEATURE-USB-XHCI-FORENSICS/e2e.txt", "fail": "tasks/evidence/FEATURE-USB-XHCI-FORENSICS/fail.txt", "pass": "tasks/evidence/FEATURE-USB-XHCI-FORENSICS/pass.txt"}
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-365609-nvidia-dgx-spark-continuously-freezing-hangin.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
reason: "CERRADA 2026-09-23 como adopted_prior_implementation. La adopcion de esta sugerencia se implemento con codigo real en un commit ANTERIOR y ese trabajo vive en tasks/done/FEATURE-USB-XHCI-FORENSICS.md, cerrada con su propia evidencia (3 ficheros, los 3 presentes). Esta ficha era la EVALUACION, no el trabajo: su trigger era un puntero a trabajo ya terminado, no una vigilancia, asi que cerrarla no apaga nada. Verificado antes de cerrar: el close_check de FEATURE-USB-XHCI-FORENSICS.md corre y pasa."
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

- Mecanismo 1 (Erosión del controlador xHCI/USB runtime-PM): en los logs verbatim se detecta falla en la gestión de energía runtime del controlador USB, impidiendo transitar entre estados activos e inactivos y causando reinicios forzosos al detectar periféricos. — `knowledge/references/forum_nvidia_365609_nvidia-dgx-spark-continuously-freezing-hanging-and-or-rebooting.md:"Erosión del controlador xHCI/USB runtime-PM"`
- Mecanismo 2 (Conflicto de enumeración de dispositivos USB en cadena): la topología de periféricos en cascada degrada la compatibilidad de handshake USB y genera conflictos de IDs y asignación de IRQ en xHCI. — `knowledge/references/forum_nvidia_365609_nvidia-dgx-spark-continuously-freezing-hanging-and-or-rebooting.md:"Conflicto de enumeración de dispositivos USB en cadena (hub + dongle + periférico)"`
- Mecanismo 3 (Kernel panic inducido por sobrecarga térmica en la zona USB-C): calentamiento localizado (>45°C en ~15 min) que dispara protecciones térmicas de firmware/BIOS forzando reinicios para proteger el controlador. — `knowledge/references/forum_nvidia_365609_nvidia-dgx-spark-continuously-freezing-hanging-and-or-rebooting.md:"Kernel panic inducido por sobrecarga térmica en la zona USB-C"`
- Paso 2 (Fallas que ataca): el problema ataca la categoría de inestabilidad térmica y de bus I/O en DGX Spark, fallas de estabilidad en boot/recovery en Atlas, y escenarios de bucle de reinicio fatal en Liberation Watchdog. — `knowledge/references/forum_nvidia_365609_nvidia-dgx-spark-continuously-freezing-hanging-and-or-rebooting.md:"Mapeo a Proyectos de la Flota"`

## Por qué se sugiere para blackbox en concreto

El mapeo a la flota atribuye "escenarios de bucle de reinicio fatal" a "Liberation Watchdog" (nombre falso); ese monitoreo de reinicios/estabilidad térmica es el dominio exacto de blackbox (telemetría de hardware, logs, systemd units); el veredicto COS no cambia, se sostiene vía los mecanismos de USB/térmico mapeados a DGX Spark/Atlas.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/nvidia-dgx-spark-continuously-freezing-hanging-and-or-rebooting/365609
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_365609_nvidia-dgx-spark-continuously-freezing-hanging-and-or-rebooting.md`
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
`tasks/done/FEATURE-USB-XHCI-FORENSICS.md`, cerrada por su cuenta y con su propia evidencia. Esta
ficha no tenia codigo que escribir: su entregable era decidir, y decidio.

Por eso el `closure_type` es `adopted_prior_implementation` y no
`void_wontfix` (seria falso: SI se hizo trabajo) ni `duplicate` (no lo es: la
evaluacion y la implementacion son cosas distintas) ni
`relocated_prior_verification` (presupone que esta ficha ya estaba `done` en un
commit anterior, y seguia abierta).

## Regression Test

El de la ficha que lleva el trabajo, que es donde vive el sujeto:

```
grep -q 'USB/xHCI' tasks/done/FEATURE-USB-XHCI-FORENSICS.md
```

Corrido el 2026-09-23 antes de cerrar esta: **pasa**. Si esa verificacion
dejara de pasar, la que se reabre es `FEATURE-USB-XHCI-FORENSICS.md` -- ahi esta el codigo --, no esta
evaluacion, que no tiene nada que arreglar.

## Verification Evidence

La de `tasks/done/FEATURE-USB-XHCI-FORENSICS.md`, comprobada presente el 2026-09-23 (3 de 3 ficheros):

- `tasks/evidence/FEATURE-USB-XHCI-FORENSICS/e2e.txt`
- `tasks/evidence/FEATURE-USB-XHCI-FORENSICS/fail.txt`
- `tasks/evidence/FEATURE-USB-XHCI-FORENSICS/pass.txt`

LIMITE DECLARADO: el `close_check` de `FEATURE-USB-XHCI-FORENSICS.md` es un `grep` sobre su propio
texto en la mayoria de estas fichas, o sea que comprueba que la ficha diga lo
que dice, no que la funcion sirva. Lo que sostiene el cierre de verdad son sus
ficheros de evidencia, que traen comando, salida y control negativo. Se dice
en vez de presentar el `grep` como si fuera una prueba funcional.
