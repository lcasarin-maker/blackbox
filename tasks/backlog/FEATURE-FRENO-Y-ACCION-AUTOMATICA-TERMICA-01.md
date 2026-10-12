---
id: FEATURE-FRENO-Y-ACCION-AUTOMATICA-TERMICA-01
kind: task
domain: GPU
title: "El calor sostenido debe disparar acciones automaticas: congelar la carga pausable de Atlas y cerrar las entradas sin freno"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "grep -q 'atlas-carga/1' SPEC.md", "expect": "exit_zero", "porque": "Hecho el 2026-10-11: el gate de bb lee estado_termico (bb-estado-termico/2) y bloquea sostenida, sobre_100 y estado ausente o viejo. Falta la ACCION: con sostenida, `systemctl --user freeze` del scope pausable de Atlas (revierte con thaw) y evento emitido aunque no actue. bb no puede nombrar la unidad: Atlas debe declararla como dato (atlas-carga/1: unidad y si es pausable). Cierra cuando SPEC documente atlas-carga/1 y exista el freeze con su test y control negativo."}
---

## Medido por el analisis bb/Atlas (2026-10-11)

- `mitigar()` solo recibe alarmas de flanco (`temp_critica`), nunca `sostenida` ni `sobre_100`; el log tiene 205 alarmas con carga y 0 pausas.
- Entradas que NO consultan el freno: nightly de las 03:30 (`build_incremental --full`), `ingest_batch` a los 1800 s (tambien con bb ausente), `--force-free`, CLI directa, vLLM y clientes ajenos a Atlas.
- Un job que empieza frio y se calienta no se detiene: el gate se evalua antes del job, no durante.
- Acciones de `sobre_100` (decision pendiente del dueno): `-lgc 300,1500` requiere root (hoy no delegado), `docker pause nemotron-server` congela peticiones en vuelo, `stop ai-nemotron` corta sesiones.

## Decidido por el dueno

Con `sostenida`: dejar de admitir carga (hecho en bb) y congelar el scope de Atlas. Contrato por archivo `bb-estado-termico/2`.

## Que falta

1. Atlas publica `atlas-carga/1` y cierra sus entradas sin freno (cambios en el repo de Atlas).
2. bb congela esa unidad en `sostenida` y la descongela al volver a `normal`, con evento propio.
3. Decidir las acciones de `sobre_100`.
