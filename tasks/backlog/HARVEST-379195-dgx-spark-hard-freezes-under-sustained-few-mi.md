---
id: HARVEST-379195-dgx-spark-hard-freezes-under-sustained-few-mi
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (379195-dgx-spark-hard-freezes-under-sustained-few-minutes-inference-po)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-379195-dgx-spark-hard-freezes-under-sustained-few-mi.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "revisado a fondo (codigo + fuente citada) y sin valor incremental hoy -- reabrir si aparece un caso real medido en esta maquina que lo contradiga"}
reason: "PowerStress es benchmarking sintetico, excluido. La fan curve del EC no tiene interfaz al SO (misma limitacion que HARVEST-377044). El clock-cap ya esta aplicado como limite registrado (300-2800 MHz)."
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

- PASO 1 (Mecanismo 1): Diagnóstico de hardware y monitoreo de límites térmicos vía PowerStress y firma de firmware `MODS-020000610139`, que detecta violación de límites térmicos aceptables o sensores descalibrados provocando un hard-freeze de protección a nivel de hardware — `knowledge/references/forum_nvidia_379195_dgx-spark-hard-freezes-under-sustained-few-minutes-inference-powerstress-thermal.md:"PowerStress fails with MODS-020000610139: acceptable temperature limits exceeded or thermal sensor broken/miscalibrated"`
- PASO 1 (Mecanismo 2): Gestión térmica pasiva / política de curva de ventiladores (*fan curve*), donde la disipación no reacciona con suficiente agresividad térmica bajo carga sostenida y no recupera el reposo en 30 segundos — `knowledge/references/forum_nvidia_379195_dgx-spark-hard-freezes-under-sustained-few-minutes-inference-powerstress-thermal.md:"All well below throttling thresholds; fan curve not aggressive enough"`
- PASO 1 (Mecanismo 3): Mitigación y control de carga por fijación de frecuencia de reloj (*clock locking*) o downgrade de firmware para limitar el consumo pico y la excursión térmica — `knowledge/references/forum_nvidia_379195_dgx-spark-hard-freezes-under-sustained-few-minutes-inference-powerstress-thermal.md:"resolved the issue by downgrading the firmware to an earlier version and locking the maximum clock speed to 2000 MHz."`
- PASO 2 (Interrogatorio Mecanismo 1): Ataca la categoría de falla conocida de "cuelgue duro silencioso por protección térmica de hardware" sin kernel panic ni excepción; a nuestra escala corresponde a monitoreo local de sensores de hardware y telemetría de fallos catastróficos en un solo nodo; y nombra lo que hacemos informalmente como validación de hardware bajo estrés previo a producción — `knowledge/references/forum_nvidia_379195_dgx-spark-hard-freezes-under-sustained-few-minutes-inference-powerstress-thermal.md:"MiniMax-H3 864×480/5-second inference hard-freezes the complete system, without OOM, NVIDIA Xid, kernel panic, or application exception"`
- PASO 2 (Interrogatorio Mecanismo 2): Ataca la categoría de falla conocida de "embalamiento térmico / degradación por ventilación insuficiente"; a nuestra escala equivale a perfiles de control estático o heurístico de ventiladores por umbral de potencia/temperatura en host; y nombra lo que hacemos como ajuste manual de perfiles de refrigeración — `knowledge/references/forum_nvidia_379195_dgx-spark-hard-freezes-under-sustained-few-minutes-inference-powerstress-thermal.md:"to recover to idle temps within 30s post-render — sustained workloads"`
- PASO 2 (Interrogatorio Mecanismo 3): Ataca la categoría de falla conocida de "inestabilidad operativa por consumo y frecuencia sin limitador térmico dinámico"; a nuestra escala equivale a límites estáticos de potencia/reloj configurados vía script local en lugar de control adaptativo complejo; y nombra lo que hacemos como limitación manual de frecuencias operativas (power cap / clock cap) — `knowledge/references/forum_nvidia_379195_dgx-spark-hard-freezes-under-sustained-few-minutes-inference-powerstress-thermal.md:"managing the clock speed based on its load and temp. that should be fixed."`

## Por qué se sugiere para blackbox en concreto

Los tres mecanismos (diagnóstico térmico vía PowerStress/firma de firmware, política de fan curve, clock locking) son monitoreo y telemetría de hardware puros ('monitoreo local de sensores de hardware y telemetría de fallos catastróficos') -- exactamente la misión de blackbox (telemetría de la AI TOP ATOM GB10: monitoreo de hardware) -- pero el dictamen interroga solo genéricamente ('nosotros') sin considerar ningún satélite real.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-hard-freezes-under-sustained-few-minutes-inference-powerstress-thermal-failure-support-portal-unavailable/379195
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_379195_dgx-spark-hard-freezes-under-sustained-few-minutes-inference-powerstress-thermal.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
