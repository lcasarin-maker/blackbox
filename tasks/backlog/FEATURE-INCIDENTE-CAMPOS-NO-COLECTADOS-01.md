---
id: FEATURE-INCIDENTE-CAMPOS-NO-COLECTADOS-01
kind: task
domain: INCIDENT_CAPTURE
title: "Que bb incident mida la fase de carga, el progreso del engine y arme los adjuntos para NVIDIA"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "python3 -m pytest -q tests/test_incident_report.py -k 'fase_de_carga or progreso_del_engine or adjuntos'", "expect": "exit_zero", "porque": "Hoy `bb incident` declara NOT_COLLECTED en cuatro campos que la issue NVIDIA #1358 pide: fase de carga, progreso del engine, primera respuesta de aplicacion tras el boot y adjuntos. Los tests no existen: el cierre exige implementarlos con su control negativo."}
---

## Lo que el reporte declara y no mide (2026-10-11)

1. **Fase de carga** (`model load | unload | prefill | decode | training | NCCL setup`): hoy solo imprime peticiones en curso y KV%. La issue muestra que 4 de 4 cortes cronometrables de Croxatte ocurrieron en carga/descarga de modelo, no en inferencia.
2. **Progreso del engine**: la firma S11 del catalogo (throughput de prompt 0.0 tok/s con la peticion "Running", KV ~4 %) necesita el contador de tokens de vLLM; `atom_gpu_telemetry` solo guarda peticiones en curso y no puede ver un engine detenido.
3. **Primera respuesta de aplicacion tras el boot siguiente**: solo se registra la primera entrada del journal.
4. **Adjuntos para NVIDIA**: `nvidia-bug-report.log.gz` y el `summary.json` de `dgx-spark-fieldiag`, que la plantilla del repo de NVIDIA trata como obligatorios. Requieren root y fieldiag exige Secure Boot desactivado; el reporte debe decirlo, no omitirlo.

## Cierre

Cada campo con su medicion real y su caso negativo (un boot sin carga no debe salir con fase), o su `UNSUPPORTED` justificado. Reutilizar `tools/hitos_incidente.py` y las metricas de vLLM que `bb sample` ya consulta antes de crear codigo.

## Ampliacion (2026-10-11): el costo de un cap solo se mide con tokens por segundo

Medido el 11-oct: el cap de GPU a 2100 MHz bajo la potencia de GPU de 41.1 a 22.8 W y la GPU media de 72.2 a 59.5 C a uso similar, pero **no se puede decir cuanto rendimiento cuesta**: `atom_gpu_telemetry` guarda las peticiones de vLLM en curso y no el contador de tokens generados. Sin ese dato ningun A/B de caps (GPU o CPU, ver FEATURE-BB-EVALUAR-CAP-DE-CPU-01) cierra. Agregar a la telemetria el contador de tokens de `/metrics` de vLLM y derivar tokens/s por ventana.
