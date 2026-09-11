---
id: HARVEST-374274-suddenly-much-lower-gpu-performance-in-infere
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (374274-suddenly-much-lower-gpu-performance-in-inference)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-374274-suddenly-much-lower-gpu-performance-in-infere.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-CLOCK-THROTTLE-CRUZADO.md, no en esta ficha de evaluacion"}
reason: "sm_clk_mhz/pstate se capturan cada 5s pero, verificado en codigo, bb scan nunca los cruza contra la bandera throttle -- el mismo hueco que HARVEST-364166/376039. El 'reset de power delivery' que propone la misma ficha es mitigacion activa y queda fuera. Se consolida en FEATURE-CLOCK-THROTTLE-CRUZADO."
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
