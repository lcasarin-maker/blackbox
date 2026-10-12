---
id: FEATURE-INCIDENTE-CAMPOS-NO-COLECTADOS-01
kind: task
domain: INCIDENT_CAPTURE
title: "Que bb incident mida la fase de carga, el progreso del engine y arme los adjuntos para NVIDIA"
status: done
closed_at: 2026-10-11
evidence: {"fail": "tasks/evidence/FEATURE-INCIDENTE-CAMPOS-NO-COLECTADOS-01.fail.txt", "pass": "tasks/evidence/FEATURE-INCIDENTE-CAMPOS-NO-COLECTADOS-01.pass.txt", "e2e": "tasks/evidence/FEATURE-INCIDENTE-CAMPOS-NO-COLECTADOS-01.e2e.txt"}
closure_type: fixed
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "python3 -m pytest -q tests/test_incident_report.py -k fase_de_carga", "expect": "exit_zero", "porque": "Hoy `bb incident` declara NOT_COLLECTED en cuatro campos que la issue NVIDIA #1358 pide: fase de carga, progreso del engine, primera respuesta de aplicacion tras el boot y adjuntos. Los tests no existen: el cierre exige implementarlos con su control negativo."}
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

## Root Cause

`bb incident` armaba el reporte solo con la telemetria de 5 s, que guarda peticiones en curso y KV%, y con `NOT_COLLECTED` literal en cuatro campos de la issue NVIDIA #1358. Las fuentes ya existian en la maquina y nadie las leia: `bb sample` guarda cada minuto los contadores de tokens de vLLM (`gw_salud`), la memoria de GPU por proceso (`gpu`) y el `boot_id`; la telemetria de 5 s no guardaba los contadores. Los adjuntos tampoco se miraban: el reporte no comprobaba si la herramienta, el permiso o el archivo existian.

## Regression Test

`tests/test_incident_report.py -k fase_de_carga` (11 tests; los controles negativos corren dentro de cada uno: boot sin carga no sale con fase de carga, sin /metrics y memoria quieta sale `indeterminada`, motor con peticiones y generacion avanzando no es S11, contador que baja no da tok/s negativo, adjunto de otro incidente no cuenta). Mas `tests/test_atom_gpu_telemetry.py::test_leer_vllm_metrics_*` para los dos contadores nuevos, con un decoy `prompt_tokens_cached_total`. Las 8 mutaciones del codigo (listadas en el e2e) hacen fallar su test.

## Verification Evidence

`tasks/evidence/FEATURE-INCIDENTE-CAMPOS-NO-COLECTADOS-01.fail.txt` (antes, rc=5: el test no existia), `.pass.txt` (rc=0, 11 passed) y `.e2e.txt` (informe real del boot 54b71618 con los cuatro campos y las mutaciones).

## Resolucion por campo (2026-10-11)

1. **Fase de carga**: `fase_de_carga` clasifica carga/descarga de modelo (memoria de GPU por proceso sube o baja >= 256 MiB en 5 min con /metrics caido), prefill, decode, inactivo y motor detenido (S11). En el boot del corte sale `decode (la generacion avanza)`. `training` y `NCCL setup` salen `UNSUPPORTED`: ningun contador de bb los distingue de decode. Umbral de 256 MiB y ventana de 5 min son constantes sin calibrar con un boot cortado en carga.
2. **Progreso del engine**: `progreso_del_engine` deriva tok/s de prompt y de generacion de los contadores. En el boot del corte: generacion 97-127 tok/s, prompt 7075-9160 tok/s, 31 peticiones en curso, S11 `NO` en 5 pares. `atom_gpu_telemetry` guarda ahora `vllm_generation_tokens_total` y `vllm_prompt_tokens_total` (aditivo); hasta que el servicio se reinicie con el codigo nuevo las filas de 5 s no los traen y el reporte cae a `bb sample` (1 min) y lo dice en `fuente`. Esto cubre el pedido de la ampliacion (tok/s por ventana); el A/B de caps de GPU/CPU no se corrio aqui.
3. **Primera respuesta de aplicacion tras el boot siguiente**: primera lectura de /metrics que responde, 263.6 s despues de la primera muestra del boot siguiente (+-5 s). Es una lectura de metricas, no una peticion de usuario.
4. **Adjuntos**: bb no puede ejecutar `sudo nvidia-bug-report.sh` ni `partnerdiag`; reconoce los archivos si el operador los deja como `<incident_id>.nvidia-bug-report.log.gz` y `<incident_id>.fieldiag-summary.json` junto al reporte, y si faltan dice por que (herramienta instalada, root, Secure Boot enabled bloquea fieldiag, el bug-report describe el boot actual y no el del incidente). Sigue `NOT_COLLECTED` en esta maquina porque nadie los ha generado.
