---
id: HARVEST-366147-collective-operations-timeout-on-dual-spark-d
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (366147-collective-operations-timeout-on-dual-spark-during-distributed-)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-366147-collective-operations-timeout-on-dual-spark-d.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "hardware/escenario distinto -- reabrir si ATOM cambia de configuracion (cluster, rack, otro chip)"}
reason: "Explicitamente multi-nodo (NCCL entre dos Sparks via QSFP56) -- fuera de alcance de una sola maquina. El submecanismo de 'crash no trazable post-mortem' ya esta resuelto por systemd-coredump + agrupacion de bb scan, motivo fundacional de este repo."
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

- Para el primer mecanismo (Fallo de símbolos MLX5 / proxy ops NCCL), la categoría de falla que ataca en la flota es la inestabilidad por fallback a CPU en comunicación inter-nodo ante la ausencia de soporte oficial de drivers OFED/GPU Direct RDMA. — `knowledge/references/forum_nvidia_366147_collective-operations-timeout-on-dual-spark-during-distributed-training.md:"| **Fallo de símbolos MLX5 / proxy ops NCCL** | **DGX Spark** | Falta de drivers Mellanox OFED oficiales y compatibles con Ubuntu 24.04 ARM64 en la plataforma DGX Spark; NCCL se ve forzado al path CPU inestable para comunicación dual-node. |"`
- Para el segundo mecanismo (Configuración NCCL_SOCKET_IFNAME), la categoría de falla corresponde a colisiones o condiciones de conflicto dual-path en el descubrimiento de interfaces de red bajo topología QSFP56. — `knowledge/references/forum_nvidia_366147_collective-operations-timeout-on-dual-spark-during-distributed-training.md:"| **Configuración NCCL_SOCKET_IFNAME** | **DGX Spark** | Configuración manual de interfaz para evitar dual-path / conflictos de IB/Socket en la topología de dos DGX Spark conectadas via QSFP56. |"`

## Por qué se sugiere para blackbox en concreto

El mecanismo 3 (fallo de FlightRecorder al no capturar el SIGSEGV como evento trazable, ceguera del watchdog para debugging post-mortem) fue mapeado explícitamente a 'Liberation Watchdog' (nombre falso); el dominio real -- captura de crashes, trazabilidad post-mortem -- es exactamente blackbox ('monitoreo de hardware, logs, systemd units').

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/collective-operations-timeout-on-dual-spark-during-distributed-training/366147
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_366147_collective-operations-timeout-on-dual-spark-during-distributed-training.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
