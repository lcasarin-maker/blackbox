---
id: DEBT-CALIBRA-PSI-CORTE-INVALIDO-INCIDENTE-11-OCT-22-02-NO-DETECTADO-01
kind: debt
domain: GPU
title: "calibra_psi: CORTE INVALIDO, no detecta el incidente del 11-oct 22:02 y hoy suma 2 falsos positivos"
status: open
severity: P2
origin: detected
detector: {"rule": "python3 -m tools.calibra_psi sale rc 1 con VEREDICTO: CORTE INVALIDO (incidentes no detectados: 1); con muestras solo hasta 2026-10-15 ya daba 0 falsos positivos y 1 incidente no detectado", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-16
close_check: {"cmd": "python3 -m tools.calibra_psi", "expect": "exit_zero", "porque": "El instrumento que valida el corte de bb-usable (PSI >= 10 % sostenido 300 s) contra los incidentes etiquetados dice hoy CORTE INVALIDO. Cierra cuando sale 0: o el incidente del 11-oct 22:02 se detecta (o se demuestra y se documenta por que cae fuera del corpus), y los falsos positivos del 16-oct dejan de serlo (ver DEBT-COLAPSO-CONFINADO-A-APP-SLICE-REINICIA-LA-MAQUINA-ENTERA-01). No se cierra editando INCIDENTES para que cuadre."}
---

## Hueco
`python3 -m tools.calibra_psi` (corrida del 2026-10-16, 26952 muestras, 2026-10-01 -> 2026-10-16 12:39) sale rc 1, `VEREDICTO: CORTE INVALIDO`:
- **1 incidente no detectado:** la ventana declarada `2026-10-11 22:02 -> 22:12` en `INCIDENTES`. Las excursiones sobre el 10 % que el corpus si ve son 10-05 00:18 (7 min), 10-11 22:44 (8 min) y 10-16 10:37 (6 min).
- **2 falsos positivos (nuevos hoy):** 10-16 10:37-10:43 y 10:44-10:54, el atasco confinado a `app.slice` que reinicio la maquina con el motor sano.
- Control medido el mismo dia: con muestras SOLO hasta 2026-10-15 el resultado ya era CORTE INVALIDO con 0 falsos positivos y 1 incidente no detectado. Es decir, el incidente no detectado es anterior a hoy y nadie lo tenia en una ficha; los falsos positivos son de hoy.

## No se sabe
Por que la ventana del 11-oct 22:02 no tiene una excursion detectable en las muestras: si el muestreador no escribio PSI (hueco), si la excursion fue de menos de 5 min o si la ventana esta mal etiquetada. No se investigo.

## Relacion
Los 2 falsos positivos de hoy los cubre `DEBT-COLAPSO-CONFINADO-A-APP-SLICE-REINICIA-LA-MAQUINA-ENTERA-01`; `tools/control_racha.py` los excluye con una excepcion que caduca con esa ficha, pero `calibra_psi` no tiene esa excepcion y sigue en rojo. Hoy ningun gate de push ejecuta `calibra_psi`.
