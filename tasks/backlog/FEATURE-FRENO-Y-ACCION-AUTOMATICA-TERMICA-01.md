---
id: FEATURE-FRENO-Y-ACCION-AUTOMATICA-TERMICA-01
kind: task
domain: GPU
title: "El calor sostenido debe disparar acciones automaticas sobre la carga externa pausable"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "grep -q thaw tasks/evidence/FEATURE-FRENO-Y-ACCION-AUTOMATICA-TERMICA-01/congelado_real.md", "expect": "exit_zero", "porque": "Falta: congelado real de liberation_job.scope (evidencia en congelado_real.md, con `thaw`) y decidir ingest_batch/--force-free. Hecho el 2026-10-11: gate de bb bloquea sostenida/sobre_100/estado ausente; bb congela la unidad que el consumidor de conocimiento declara en el contrato de carga externa (accion_termica.py, commit dc1e7f4); el consumidor de conocimiento publica la declaracion y su job nocturno consulta el gate (el consumidor de conocimiento 474b1551a). Falta: (1) decidir y construir las acciones de sobre_100 y dejar la decision en congelado_real.md, (2) verificar de punta a punta con un congelado REAL de liberation_job.scope (solo se probo con un scope de prueba y dobles), (3) decidir si ingest_batch a los 1800 s y --force-free siguen siendo excepciones deliberadas."}
---

## Medido por el analisis de frontera entre bb y el consumidor de conocimiento (2026-10-11)

- `mitigar()` solo recibe alarmas de flanco (`temp_critica`), nunca `sostenida` ni `sobre_100`; el log tiene 205 alarmas con carga y 0 pausas.
- Entradas que NO consultan el freno: nightly de las 03:30 (`build_incremental --full`), `ingest_batch` a los 1800 s (tambien con bb ausente), `--force-free`, CLI directa, vLLM y clientes ajenos al consumidor de conocimiento.
- Un job que empieza frio y se calienta no se detiene: el gate se evalua antes del job, no durante.
- Acciones de `sobre_100` (decision pendiente del dueno): `-lgc 300,1500` requiere root (hoy no delegado), `docker pause nemotron-server` congela peticiones en vuelo, `stop ai-nemotron` corta sesiones.

## Decidido por el dueno

Con `sostenida`: dejar de admitir carga (hecho en bb) y congelar el scope de la carga externa. Contrato por archivo `bb-estado-termico/2`.

## Que falta (actualizado)

1. ~~Acciones de `sobre_100`~~ DECIDIDO 2026-10-11: solo congelar la carga externa (lo mismo que con `sostenida`, ya construido). Descartado: `docker pause` de vLLM (congela peticiones en vuelo) y `-lgc 300,1500` (pide root no delegado). Reabrir si un `sobre_100` real muestra que congelar la carga externa no baja el calor.
2. Congelado real de `liberation_job.scope` con un job vivo: hasta hoy solo hay un scope de prueba (10 lineas -> congelado -> 20) y tests con doble de systemctl.
3. `ingest_batch` sigue tras 1800 s caliente por decision de una referencia externa y `--force-free` es modo de pruebas: confirmar o cambiar.

## Voto de Luis 2026-10-17: punto 3, `ingest_batch` a los 1800 s y `--force-free`
Se conservan como estan. `ingest_batch` sigue tras 1800 s caliente por la decision de una referencia externa y `--force-free` queda como modo de pruebas; el costo aceptado es que una ingesta puede seguir hasta 30 min con calor sostenido antes de ceder y que `--force-free` salta el freno. Descartado: hacer que consulte el freno como el resto (el cambio vive en el repo del consumidor de conocimiento y la ingesta puede quedar detenida con calor sostenido). Quedan abiertos los puntos 1 y 2 (acciones de `sobre_100` y el congelado real de `liberation_job.scope` con un job vivo).
