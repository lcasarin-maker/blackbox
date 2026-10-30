---
id: FEATURE-RESIDENTES-INACTIVOS-CONTRA-CALOR-01
kind: task
domain: GPU
title: "Medir si los modelos residentes inactivos cuestan calor y rendimiento en esta ATOM (idea de descargar tras un rato de reposo de Athena's Engine)"
status: open
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
