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
close_check: {"cmd": "grep -q sobre_100 tasks/evidence/FEATURE-FRENO-Y-ACCION-AUTOMATICA-TERMICA-01/decision_sobre_100.md", "expect": "exit_zero", "porque": "Hecho el 2026-10-11: gate de bb bloquea sostenida/sobre_100/estado ausente; bb congela la unidad que Atlas declara en atlas-carga/1 (accion_termica.py, commit dc1e7f4); Atlas publica la declaracion y su job nocturno consulta el gate (Atlas 474b1551a). Falta: (1) decidir y construir las acciones de sobre_100 y dejar la decision en decision_sobre_100.md, (2) verificar de punta a punta con un congelado REAL de liberation_job.scope (solo se probo con un scope de prueba y dobles), (3) decidir si ingest_batch a los 1800 s y --force-free siguen siendo excepciones deliberadas."}
---

## Medido por el analisis bb/Atlas (2026-10-11)

- `mitigar()` solo recibe alarmas de flanco (`temp_critica`), nunca `sostenida` ni `sobre_100`; el log tiene 205 alarmas con carga y 0 pausas.
- Entradas que NO consultan el freno: nightly de las 03:30 (`build_incremental --full`), `ingest_batch` a los 1800 s (tambien con bb ausente), `--force-free`, CLI directa, vLLM y clientes ajenos a Atlas.
- Un job que empieza frio y se calienta no se detiene: el gate se evalua antes del job, no durante.
- Acciones de `sobre_100` (decision pendiente del dueno): `-lgc 300,1500` requiere root (hoy no delegado), `docker pause nemotron-server` congela peticiones en vuelo, `stop ai-nemotron` corta sesiones.

## Decidido por el dueno

Con `sostenida`: dejar de admitir carga (hecho en bb) y congelar el scope de Atlas. Contrato por archivo `bb-estado-termico/2`.

## Que falta (actualizado)

1. Acciones de `sobre_100`: `-lgc 300,1500` (root), `docker pause nemotron-server`, `stop ai-nemotron`; decision del dueno.
2. Congelado real de `liberation_job.scope` con un job vivo: hasta hoy solo hay un scope de prueba (10 lineas -> congelado -> 20) y tests con doble de systemctl.
3. `ingest_batch` sigue tras 1800 s caliente por decision de DGX-342 y `--force-free` es modo de pruebas: confirmar o cambiar.
