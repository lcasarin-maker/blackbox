---
id: HARVEST-373251-dgx-spark-gb10-reproducibly-hard-powers-off-u
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (373251-dgx-spark-gb10-reproducibly-hard-powers-off-under-gpu-load-full)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-373251-dgx-spark-gb10-reproducibly-hard-powers-off-u.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-KDUMP-PSTORE-PREAPAGADO.md, no en esta ficha de evaluacion"}
reason: "kdump/pstore para capturar estado de kernel antes de un apagado duro por corte VRM/PMIC es exactamente el hueco que motivo fundar este repo, un nivel mas abajo (kernel, no solo userspace). enable-privileged.sh hoy solo arma coredump de procesos de usuario. Se consolida en FEATURE-KDUMP-PSTORE-PREAPAGADO."
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

- Paso 1 (Mecanismos): El primer mecanismo documentado es la regulación térmica y corte de protección de entrega de energía (VRM/PMIC), donde el corte ocurre a nivel de hardware (EC/PMC) o umbral de corriente ante un salto de potencia súbito de 15W a 82W bajo carga — `knowledge/references/forum_nvidia_373251_dgx-spark-gb10-reproducibly-hard-powers-off-under-gpu-load-fully-updated-zero-cr.md:"El usuario describe un apagado duro (power-off completo) cuando la GPU alcanza ~82W bajo carga, con temperaturas de 79°C en la muestra final. La ausencia de trips térmicos registrados y la falta de logs de Xid NVRM apuntan a un corte de protección a nivel de hardware (EC/PMC) o limiar de corriente en el regulador de voltaje, precediendo a cualquier evento de sobrecalentamiento logado."`
- Paso 1 (Mecanismos): El tercer mecanismo corresponde a la gestión de energía por Embedded Controller (EC) y actualización vía firmware OTA, cuya lógica o umbrales de corriente/voltaje pueden presentar regresiones bajo cargas del silicio GB10 — `knowledge/references/forum_nvidia_373251_dgx-spark-gb10-reproducibly-hard-powers-off-under-gpu-load-fully-updated-zero-cr.md:"Esto sugiere que la lógica de gestión de energía del Embedded Controller (EC) o el firmware de la unidad de potencia puede tener un bug de regresión en el umbral de corriente/voltaje bajo carga de GPU GB10, o que la OTA actual no incluye la versión de EC necesaria para estabilizar el rails de 12V/3.3V bajo la carga del GB10."`
- Paso 2 (Interrogatorio - Mecanismo 1): Ataca la categoría de falla conocida de disparo intempestivo de protección térmica o de sobrecorriente por entrega de potencia bajo carga transitoria de acelerador; mapea al hardware y regulación de potencia de la plataforma — `knowledge/references/forum_nvidia_373251_dgx-spark-gb10-reproducibly-hard-powers-off-under-gpu-load-fully-updated-zero-cr.md:"El proyecto DGX Spark es el destinatario directo, ya que involucra el hardware GB10 específico, el regulator de potencia y la gestión térmica. La justificación es que el síntoma (power-off bajo carga) es intrinsicamente un problema de hardware/EC de la plataforma DGX Spark."`
- Paso 2 (Interrogatorio - Mecanismo 2): Ataca la categoría de falla de pérdida silenciosa de telemetría y diagnósticos post-mortem por corte de alimentación en caliente; se investiga si kdump o pstore son viables en la arquitectura del nodo — `knowledge/references/forum_nvidia_373251_dgx-spark-gb10-reproducibly-hard-powers-off-under-gpu-load-fully-updated-zero-cr.md:"Esto es crítico para el diagnóstico en DGX Spark, ya que sin datos de crashkernel, cualquier análisis de causa raíz es ciego. El proyecto debe asegurar que la configuración de kdump sea compatible con la arquitectura GB10 y el firmware EC presente."`
- Paso 2 (Interrogatorio - Mecanismo 3): Ataca la categoría de falla de regresión de firmware o desajuste de umbrales en controladores embebidos no corregidos por actualizaciones de distribución estándar — `knowledge/references/forum_nvidia_373251_dgx-spark-gb10-reproducibly-hard-powers-off-under-gpu-load-fully-updated-zero-cr.md:"Esto ataca la capacidad del ciclo de actualización de OTA de DGX Spark para corregir bugs de bajo nivel del EC. Si la OTA actual no resuelve el umbral de corriente, el proyecto debe investigar si se necesita una versión de firmware EC no pública o una revisión de SBIOS."`

## Por qué se sugiere para blackbox en concreto

El texto dice explícitamente 'El proyecto DGX Spark es el destinatario directo' (nombre falso) para un corte de protección VRM/PMIC y regresión de firmware EC -- ese mecanismo de telemetría/protección de hardware es el dominio literal de blackbox, nunca interrogado.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-gb10-reproducibly-hard-powers-off-under-gpu-load-fully-updated-zero-crash-capture/373251
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_373251_dgx-spark-gb10-reproducibly-hard-powers-off-under-gpu-load-fully-updated-zero-cr.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
