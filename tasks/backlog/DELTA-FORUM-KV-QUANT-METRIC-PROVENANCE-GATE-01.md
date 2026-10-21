---
id: DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01
kind: task
domain: VERDICT
title: "Validar forum kv quant metric provenance gate 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_kv_quant_metric_provenance_gate_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01

[364736](https://forums.developer.nvidia.com/t/why-turboquant-saves-dgx-twice/364736) includes a material correction: the author retracted a claim of 92.5% q4_0 prefill collapse and higher memory use after identifying that the original memory measurement used process RSS instead of the llama.cpp KV buffer. The corrected owner report gives 216 MiB q4_0 versus 768 MiB f16 KV, with no prefill cliff and about 37% lower decode rate at 110K context. Later TurboQuant/RotorQuant timings, quality and kernel claims vary by fork/config and remain unverified; external repositories and result files were not audited.

Keep RSS, cgroup, host available memory/swap, allocator residency and framework KV bytes as separately labeled counters. Compare the exact K/V mode, backend, model, context and concurrency with output correctness and prefill/decode measurements. A KV capacity win does not establish faster or correct generation; the reported values are not universal thresholds.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

### Evidencia de instrumento (2026-10-03)

Estado: parcial, con lector offline desarrollado para nombre exacto, TYPE/HELP, etiquetas, valor crudo y timestamp Prometheus; path indicado por el llamador queda sin autenticar. La captura runtime disponible no incluye texto crudo `/metrics`, así que su parseo nativo, comparación KV en el stack fijado, control negativo y cierre funcional quedan `could_not_run`. La ficha sigue abierta; su `close_check` original no cambió. Informe: `docs/evidence/BB-INSTRUMENTS-runtime.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: Lector de métricas parcial; la captura runtime carece de /metrics crudo y comparación de KV/corrección en stack fijado.
- Evidencia faltante para cierre: texto raw Prometheus /metrics; mode K/V, backend/model/context/concurrency; bytes KV, output correctness, prefill/decode y control negativo
- Siguiente acción: Recolectar /metrics crudo y ejecutar comparación f16/cuanti en workload fijado con correctness; separar RSS/cgroup/host/KV y archivar resultados.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_08.json`, `tasks/evidence/DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01/ (directorio ausente al inspeccionar)`.
- Impedimentos de inspección: 1. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: baja · lectura: completa.

El caso del foro es llama.cpp con KV q4_0/f16; aqui sirve vLLM, pero la regla (no mezclar RSS, cgroup, MemAvailable y bytes de KV como un solo contador) aplica a vLLM via /metrics. close_check es un xfail y el lector offline parcial no tiene /metrics crudo.

Version para un solo nodo Gigabyte AI TOP ATOM: Capturar /metrics crudo de nemotron-server (puerto 8000) y etiquetar por separado bytes de KV de vLLM, cgroup (dmem), MemAvailable y RSS; sin comparacion f16/cuantizada de llama.cpp.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Medido 2026-10-20 (boleta de Luis: cerrar void_wontfix solo con AUSENCIA MEDIDA): queda ABIERTA

Regla: `void_wontfix` solo si la ausencia del sujeto se mide en este equipo con control positivo. Solo lectura (sin sudo, sin cargas, sin reiniciar nada). Resultado: el sujeto EXISTE o no es observable desde la maquina, asi que no se cierra.

Sujeto de la ficha: contadores de KV separados del RSS/cgroup/MemAvailable (en el motor local, via `/metrics` de vLLM). Existe aqui:

```
$ curl -s -m 10 http://127.0.0.1:8000/metrics | grep -E '^# TYPE vllm:(kv_cache|gpu_cache|cache_config)' | head
# TYPE vllm:kv_cache_usage_perc gauge
# TYPE vllm:cache_config_info gauge
rc=0
$ curl -s -m 10 http://127.0.0.1:8000/metrics | grep -E '^vllm:cache_config_info' | cut -c1-260
vllm:cache_config_info{_block_size_resolved="True",block_size="4176",cache_dtype="fp8",calculate_kv_scales="False",enable_prefix_caching="True",engine="0",gpu_memory_utilization="0.3",is_attention_free="False",kv_cache_dtype_skip_layers="[]",kv_cache_max_concurrency="44.3125",kv_cache_memory_bytes="None",kv_cache_size_tokens="1452032",...
$ curl -s -m 10 http://127.0.0.1:8000/metrics | grep -c '^vllm:'
388
$ docker inspect nemotron-server --format '{{join .Config.Cmd " "}}' | grep -oE 'kv-cache-dtype [a-z0-9_]+'
kv-cache-dtype fp8
```

Lo que SI esta ausente (llama.cpp del hilo 364736), con control positivo de que el instrumento dice "presente":

```
$ which llama-server llama-cli           -> rc=1 (sin salida)
$ dpkg -l | grep -i llama                -> rc=1 (sin salida)
$ ps -eo pid,comm | grep -E 'llama|vllm' -> 3563182 vllm       (control positivo: el mismo grep encuentra vllm)
$ dpkg -l | grep -i docker | head -3     -> ii docker-buildx-plugin / docker-ce / docker-ce-cli   (control positivo del dpkg|grep)
$ which docker python3                   -> /usr/bin/docker  /opt/miniforge3/bin/python3          (control positivo del which)
```

Veredicto: ABIERTA. La mitad llama.cpp esta ausente, pero la ficha pide una regla de procedencia (no mezclar RSS, cgroup, MemAvailable y bytes de KV) que aplica a vLLM, y el motor local expone `kv_cache_usage_perc`, `cache_config_info` y KV en fp8 (cuantizado). El sujeto existe; cerrar como `void_wontfix` seria suprimir. Siguiente paso: capturar `/metrics` crudo y etiquetar los contadores por separado, segun la "Version para un solo nodo".
