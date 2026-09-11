---
id: HARVEST-379303-severe-one-way-rdma-performance-regression-on
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (379303-severe-one-way-rdma-performance-regression-on-asus-ascent-gx10-)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-379303-severe-one-way-rdma-performance-regression-on.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip)"}
reason: "Diagnostico de red RDMA/ConnectX-7 para clustering GB10<->GB10 -- multi-nodo, fuera de alcance de una caja negra de una sola maquina sin esa topologia."
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

- Mecanismo 1 (Asimetría en la ruta de RDMA Write en el kernel 6.17.0-1029-nvidia): Una regresión de kernel afecta el tráfico de entrada (ingress) o escrituras DMA PCIe en sistemas ConnectX-7 GB10, provocando una caída unidireccional de rendimiento (~111 Gbit/s a ~13 Gbit/s) únicamente en la dirección DGX Spark -> ASUS GX10 — `knowledge/references/forum_nvidia_379303_severe-one-way-rdma-performance-regression-on-asus-ascent-gx10-with-kernel-6-17-.md:"1. **RDMA Write path asimetría en el kernel 6.17.0-1029-nvidia**: Regressión que afecta el tráfico de entrada (ingress) o las escrituras DMA PCIe en dispositivos ConnectX-7 GB10, provocando un desplome de throughput unidireccional de ~111 Gbit/s a ~13 Gbit/s. El problema se restringe a la dirección DGX Spark -> ASUS GX10 y no afecta la dirección inversa."`
- Mecanismo 2 (Revisión de PCIe AER y configuración IOMMU/SMMU): Descarte metódico de fallos de capa física/enlace de hardware leyendo contadores de error AER y revisando la configuración de la IOMMU para aislar la causa raíz en la capa de software y kernel — `knowledge/references/forum_nvidia_379303_severe-one-way-rdma-performance-regression-on-asus-ascent-gx10-with-kernel-6-17-.md:"2. **Configuración PCIe AER y IOMMU/SMMU sin errores reportados**: Se descartaron errores de hardware/PCIe a través de la revisión de contadores AER y configuración IOMMU, dejando la causa raíz en la capa de software/kernel."`
- Interrogatorio DGX Spark (Paso 2): Afecta la categoría de saturación/cuello de botella de I/O DMA entrante en el nodo Spark receptor (13.2 Gbit/s inbound vs 111.6 Gbit/s outbound), remediable mediante reversión de versión de kernel — `knowledge/references/forum_nvidia_379303_severe-one-way-rdma-performance-regression-on-asus-ascent-gx10-with-kernel-6-17-.md:"- **DGX Spark**: El hardware objetivo (ASUS Ascent GX10) es un form factor DGX Spark. El mecanismo de regresión kernel 6.17.0-1029 afecta directamente a la capacidad de RDMA Write entrante en Spark, que es el cuello de botella reportado (13.2 Gbit/s inbound vs 111.6 Gbit/s outbound). La solución (revertir a 6.17.0-1026) restaura el rendimiento esperado de 200 Gbit/s."`
- Interrogatorio Cuenza (Paso 2): La degradación unidireccional de enlace RDMA impactaría a la categoría de desincronización y latencia asimétrica en validación transaccional distribuida si se usaran configuraciones GB10 dual — `knowledge/references/forum_nvidia_379303_severe-one-way-rdma-performance-regression-on-asus-ascent-gx10-with-kernel-6-17-.md:"- **Cuenza**: La validación estructurada JSON/tablas no aplica; el mecanismo es el diagnóstico de regresión de rendimiento unidireccional en links RDMA, que podría impactar pipelines de validación de transacciones distribuidas si se desplegaran Cuenza nodes en configuraciones GB10 dual."`

## Por qué se sugiere para blackbox en concreto

Los mecanismos (regresión de kernel en ruta RDMA Write, descarte de fallos PCIe AER/IOMMU, control de versión de kernel como variable de control) son diagnóstico y monitoreo de hardware/red a nivel de nodo GB10 -- dominio de blackbox -- pero el interrogatorio solo consideró DGX Spark (hardware), Atlas y Cuenza (estirado, 'el dominio legal no aplica'), sin considerar blackbox.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/severe-one-way-rdma-performance-regression-on-asus-ascent-gx10-with-kernel-6-17-0-1029-nvidia/379303
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_379303_severe-one-way-rdma-performance-regression-on-asus-ascent-gx10-with-kernel-6-17-.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
