---
id: FEATURE-CALIBRAR-CALOR-SOSTENIDO-01
kind: task
domain: GPU
title: "Calibrar el detector de calor sostenido con mas boots y con un boot sano bajo carga pesada"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "grep -q 'boot sano' tasks/evidence/FEATURE-CALIBRAR-CALOR-SOSTENIDO-01/medicion.txt", "expect": "exit_zero", "porque": "Las constantes de temp_sostenida (banda umbral-5 C, 80 % de 60 lecturas) salen de UN boot de 22 h y no hay ningun boot SANO bajo carga pesada para medir falsos positivos. Cierra con la medicion de al menos 3 boots mas y de un boot sano cargado, con las constantes re-derivadas de los datos."}
---

## Que se sabe (2026-10-11)

La primera version del detector (banda a umbral-2 C) no disparo nunca en la reproduccion sobre los datos reales; con umbral-5 C marca 65.8 min de las 22 h del boot del corte en 3 episodios (uno 33 min antes del corte) y no marca el tramo frio. En 8 boots, el calor sostenido de la zona 0 estaba activo al morir en los 4 cortes abruptos y en el poweroff del 10-oct, y no en los 3 boots de poca carga.

## Que falta

1. **Control sano bajo carga:** todos los boots largos y cargados de los datos terminaron en corte o poweroff, asi que no se puede medir cuanto dispara el detector en una maquina que NO esta a punto de cortarse. El boot actual (vivo) ya acumulo episodios: el indicador no separa por si solo.
2. **Mas boots** (el A/B del cap de CPU, `FEATURE-BB-EVALUAR-CAP-DE-CPU-01`, los producira) para re-derivar la banda y la fraccion en vez de heredarlas de un caso.
3. **Prueba con un `sobre_100` real**, que no ha ocurrido (maximo historico de zona 98.6 C).

Medicion en `tasks/evidence/FEATURE-CALIBRAR-CALOR-SOSTENIDO-01/medicion.txt`; debe usar la frase `boot sano` solo si existe ese boot.
