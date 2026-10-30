---
id: FEATURE-RESIDENTES-INACTIVOS-CONTRA-CALOR-01
kind: task
domain: GPU
title: "Medir si los modelos residentes inactivos cuestan calor y rendimiento en esta ATOM (idea de descargar tras un rato de reposo de Athena's Engine)"
status: done
closed_at: 2026-10-30
closure_type: verified
reason: "Medido sobre 135908 muestras de telemetria y 3440 filas de historial: el residente nemotron-server estuvo en 135819 de 135889 muestras con residencia conocida, reposo del motor >= 10 min en 149 ventanas (31039 muestras, 43.1 h) y 0 de ellas sin residente, asi que el costo del residente inactivo es NO CALCULABLE (sin control), no nulo; piso de ruido p95 7.2 C en tmax; no corresponde ficha de accion."
evidence: {"pass": "tasks/evidence/FEATURE-RESIDENTES-INACTIVOS-CONTRA-CALOR-01/pass.txt", "fail": "tasks/evidence/FEATURE-RESIDENTES-INACTIVOS-CONTRA-CALOR-01/fail.txt", "e2e": "tasks/evidence/FEATURE-RESIDENTES-INACTIVOS-CONTRA-CALOR-01/e2e.txt"}
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-30
close_check: {"cmd": "grep -qx residentes_medido tasks/evidence/FEATURE-RESIDENTES-INACTIVOS-CONTRA-CALOR-01/medicion.txt", "expect": "exit_zero", "porque": "Especificacion pendiente: el archivo no existe hoy, asi que grep sale 2. Pasa solo cuando medicion.txt traiga, con comando y salida literales, el cruce de residencia, inactividad y temperatura, y la linea completa residentes_medido (con -x, para que una frase que contenga el centinela no cierre en falso, como paso en FEATURE-VLLM-ENDURECIMIENTO-DE-MEMORIA-GB10-01)."}
---

## Idea de origen y hueco propio

Athena carga cada servicio la primera vez que se pide y lo devuelve cuando lleva un rato en reposo (`Atlas/knowledge/references/github_com_xangel82_Athena_Engine.md`). El hueco de bb esta en `FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION`: el hilo 348760 reporta, con la medicion de un solo autor y adjuntos sin revisar, que detener tres modelos residentes inactivos baja la temperatura y sube el rendimiento. En esta maquina no hay medicion local: la ficha dice "0 cambios de compuerta, 0 A/B y 0 claims de throughput".

## Adaptacion

bb ya guarda lo necesario por separado: `tools/gpumem_historial.py` escribe quien tiene memoria de GPU, su pico y cuando termino (`gpumem_historial.jsonl`), y `tools/atom_gpu_telemetry.py` guarda temperatura y potencia cada 5 s. Falta cruzarlos con una senal de INACTIVIDAD del residente y mirar si el calor sube con residentes inactivos. Todo en `observar`: no se detiene nada.

## Para cerrar

1. Definir la inactividad con una senal que ya se mida (utilizacion de GPU del proceso o peticiones del motor), a elegir en la ficha y escribir cual.
2. Cruzar residencia x inactividad x temperatura sobre el historico y reportar el resultado aunque sea nulo. Un cruce sin efecto es un resultado valido y se documenta como tal.
3. Solo si hay efecto medido, abrir una ficha de accion (descargar tras reposo); descargar un modelo de Atlas o del motor es decision de Luis.

## Limites declarados

El calor depende tambien de ambiente, ventilador y carga; la ficha `FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION` exige control sin modelos residentes antes de afirmar mejora.

## Resultado (2026-10-30)

Senal de inactividad: peticiones del motor vLLM en cero (running y waiting) sostenidas >= 10 min. Cruce completo en `tasks/evidence/FEATURE-RESIDENTES-INACTIVOS-CONTRA-CALOR-01/medicion.txt` (script `mide_residentes.py` en el mismo directorio). No concluyente: el residente estuvo presente en todo el periodo, hay 0 muestras de reposo sin residente, asi que no hay control y no se puede afirmar ni negar costo. El reposo largo casi no ocurre (racha maxima 60 min; 7 muestras pasan de 60 min). Sin efecto medido, no corresponde ficha de accion (descargar tras reposo); si Luis quiere el control, exige descargar el modelo durante un periodo con ambiente y carga previa comparables, y esa es su decision.
