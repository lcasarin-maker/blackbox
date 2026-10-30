---
id: FEATURE-RESIDENTES-INACTIVOS-CONTROL-SIN-RESIDENTE-01
kind: task
domain: GPU
title: "Medir el control que falta: reposo SIN modelo residente contra reposo CON residente en esta ATOM"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-30
close_check: {"cmd": "grep -qx control_sin_residente_medido tasks/evidence/FEATURE-RESIDENTES-INACTIVOS-CONTROL-SIN-RESIDENTE-01/medicion.txt", "expect": "exit_zero", "porque": "Especificacion pendiente: el archivo no existe hoy (grep sale 2). Pasa solo cuando medicion.txt traiga, con comando y salida literales, al menos 30 muestras de reposo >= 10 min sin residente y 30 con residente, en condiciones de ambiente y carga previa comparables, y termine con la linea completa control_sin_residente_medido (-x: una frase que lo contenga no cierra)."}
---

## Origen

Seguimiento de `FEATURE-RESIDENTES-INACTIVOS-CONTRA-CALOR-01` (cerrada 2026-10-30). Esa medicion corrio completa sobre el historico y dio NO CONCLUYENTE: de 31039 muestras de reposo (149 ventanas de 10 min o mas, 43.1 h de 188.6 h), 0 estaban sin residente. El contraste "reposo con residente contra reposo sin residente" es NO CALCULABLE, no un efecto nulo. Reproducido por el orquestador de `/cerrar-deuda` el 2026-10-30 con `python3 -I tasks/evidence/FEATURE-RESIDENTES-INACTIVOS-CONTRA-CALOR-01/mide_residentes.py`: 149 ventanas, 0 sin residente.

Lo que la medicion dejo establecido y se reutiliza: senal de inactividad (vLLM con `running==0` y `waiting==0` por 10 min o mas), piso de ruido por ventanas (`|delta tmax|` p95 = 7.2 C, placebo de 300 particiones), y la mediana de tmax en reposo cambia 16.3 C entre boots (43.8 a 60.1 C): el ambiente y el boot dominan, asi que el control debe comparar dentro de condiciones parecidas.

## Por que esta bloqueada

El control exige DESCARGAR el modelo del motor durante una ventana de reposo, y el motor sirve a Atlas y a otros proyectos. Esa ventana la decide Luis. Ningun agente puede producirla.

## Para cerrar

1. Luis fija una ventana en que se puede detener el motor (por ejemplo `docker stop` del contenedor residente, con reinicio posterior) durante al menos 30 min de reposo, con la maquina en un estado comparable al de las ventanas con residente (misma temperatura de arranque aproximada, mismo ambiente).
2. Reusar `mide_residentes.py` y comparar contra el piso de ruido de 7.2 C; el efecto solo cuenta si lo supera.
3. Si hay efecto medido, abrir una ficha de accion (descargar tras reposo); descargar el motor sigue siendo decision de Luis.
