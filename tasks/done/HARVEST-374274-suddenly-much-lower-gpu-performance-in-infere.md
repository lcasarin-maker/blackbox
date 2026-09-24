---
id: HARVEST-374274-suddenly-much-lower-gpu-performance-in-infere
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (374274-suddenly-much-lower-gpu-performance-in-inference)"
status: done
closure_type: adopted_prior_implementation
closed_at: 2026-09-23
evidence: {"verificado_el_destino": "$ # el close_check de la ficha que lleva el trabajo, corrido el 2026-09-23\n$ grep -q 'clock.*throttle\\\\|throttle.*clock' tasks/done/FEATURE-CLOCK-THROTTLE-CRUZADO.md\nrc=0  (0 = pasa)", "evidencia_del_destino": "Los 3 ficheros de tasks/done/FEATURE-CLOCK-THROTTLE-CRUZADO.md, comprobados presentes el 2026-09-23: tasks/evidence/FEATURE-CLOCK-THROTTLE-CRUZADO/e2e.txt, tasks/evidence/FEATURE-CLOCK-THROTTLE-CRUZADO/fail.txt, tasks/evidence/FEATURE-CLOCK-THROTTLE-CRUZADO/pass.txt", "limite_declarado": "El close_check de FEATURE-CLOCK-THROTTLE-CRUZADO.md es un grep sobre su propio texto: comprueba que la ficha diga lo que dice, no que la funcion sirva. Lo que sostiene el cierre son sus ficheros de evidencia, que traen comando, salida y control negativo.", "e2e": "tasks/evidence/FEATURE-CLOCK-THROTTLE-CRUZADO/e2e.txt", "fail": "tasks/evidence/FEATURE-CLOCK-THROTTLE-CRUZADO/fail.txt", "pass": "tasks/evidence/FEATURE-CLOCK-THROTTLE-CRUZADO/pass.txt"}
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-374274-suddenly-much-lower-gpu-performance-in-infere.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
reason: "CERRADA 2026-09-23 como adopted_prior_implementation. La adopcion de esta sugerencia se implemento con codigo real en un commit ANTERIOR y ese trabajo vive en tasks/done/FEATURE-CLOCK-THROTTLE-CRUZADO.md, cerrada con su propia evidencia (3 ficheros, los 3 presentes). Esta ficha era la EVALUACION, no el trabajo: su trigger era un puntero a trabajo ya terminado, no una vigilancia, asi que cerrarla no apaga nada. Verificado antes de cerrar: el close_check de FEATURE-CLOCK-THROTTLE-CRUZADO.md corre y pasa."
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

- El primer mecanismo implementado es el reinicio de la máquina de estados de entrega de energía (Power Delivery State Machine Reset), donde la falla del controlador en reiniciar la frecuencia base y límites de potencia tras actualizaciones APT y reinicios suaves mantiene la GPU a baja frecuencia (~669 MHz), resolviéndose únicamente mediante un ciclo de apagado y desconexión física de la alimentación para forzar el reinicio de firmware — `knowledge/references/forum_nvidia_374274_suddenly-much-lower-gpu-performance-in-inference.md:"Firmware de entrega de energía (Power Delivery State Machine Reset):"`
- El segundo mecanismo es el escalado dinámico de voltaje y frecuencia (GPU Clock Gate/DVFS), que ante una condición anómala bloquea el incremento dinámico de frecuencias bajo carga de inferencia reduciendo el reloj drásticamente de ~2.4 GHz a 669 MHz — `knowledge/references/forum_nvidia_374274_suddenly-much-lower-gpu-performance-in-inference.md:"Ruteo de frecuencia dinámica (GPU Clock Gate/DVFS):"`
- El tercer mecanismo es la verificación de estado de controlador (Driver State Verification), que detecta discrepancias entre el estado del kernel/driver y el firmware tras actualizaciones del gestor de paquetes APT — `knowledge/references/forum_nvidia_374274_suddenly-much-lower-gpu-performance-in-inference.md:"Validación de Estado de Controlador (Driver State Verification):"`

## Por qué se sugiere para blackbox en concreto

Los tres mecanismos (reset de máquina de estados de entrega de energía, DVFS de reloj de GPU, verificación de estado de controlador/firmware) se repartieron entre 'DGX Spark', 'Atlas', 'Liberation Watchdog' y 'Nomad Offline' (los tres últimos falsos o mal encajados); es detección de anomalías de telemetría de hardware, dominio literal de blackbox, nunca interrogado.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/suddenly-much-lower-gpu-performance-in-inference/374274
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_374274_suddenly-much-lower-gpu-performance-in-inference.md`
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
`tasks/done/FEATURE-CLOCK-THROTTLE-CRUZADO.md`, cerrada por su cuenta y con su propia evidencia. Esta
ficha no tenia codigo que escribir: su entregable era decidir, y decidio.

Por eso el `closure_type` es `adopted_prior_implementation` y no
`void_wontfix` (seria falso: SI se hizo trabajo) ni `duplicate` (no lo es: la
evaluacion y la implementacion son cosas distintas) ni
`relocated_prior_verification` (presupone que esta ficha ya estaba `done` en un
commit anterior, y seguia abierta).

## Regression Test

El de la ficha que lleva el trabajo, que es donde vive el sujeto:

```
grep -q 'clock.*throttle\\|throttle.*clock' tasks/done/FEATURE-CLOCK-THROTTLE-CRUZADO.md
```

Corrido el 2026-09-23 antes de cerrar esta: **pasa**. Si esa verificacion
dejara de pasar, la que se reabre es `FEATURE-CLOCK-THROTTLE-CRUZADO.md` -- ahi esta el codigo --, no esta
evaluacion, que no tiene nada que arreglar.

## Verification Evidence

La de `tasks/done/FEATURE-CLOCK-THROTTLE-CRUZADO.md`, comprobada presente el 2026-09-23 (3 de 3 ficheros):

- `tasks/evidence/FEATURE-CLOCK-THROTTLE-CRUZADO/e2e.txt`
- `tasks/evidence/FEATURE-CLOCK-THROTTLE-CRUZADO/fail.txt`
- `tasks/evidence/FEATURE-CLOCK-THROTTLE-CRUZADO/pass.txt`

LIMITE DECLARADO: el `close_check` de `FEATURE-CLOCK-THROTTLE-CRUZADO.md` es un `grep` sobre su propio
texto en la mayoria de estas fichas, o sea que comprueba que la ficha diga lo
que dice, no que la funcion sirva. Lo que sostiene el cierre de verdad son sus
ficheros de evidencia, que traen comando, salida y control negativo. Se dice
en vez de presentar el `grep` como si fuera una prueba funcional.
