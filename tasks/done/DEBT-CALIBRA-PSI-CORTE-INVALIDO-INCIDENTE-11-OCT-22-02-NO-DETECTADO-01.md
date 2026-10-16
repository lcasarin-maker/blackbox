---
id: DEBT-CALIBRA-PSI-CORTE-INVALIDO-INCIDENTE-11-OCT-22-02-NO-DETECTADO-01
kind: debt
domain: GPU
title: "calibra_psi: CORTE INVALIDO, no detecta el incidente del 11-oct 22:02 y hoy suma 2 falsos positivos"
status: done
closed_at: 2026-10-16
closure_type: fixed
reason: "calibra_psi observa las ventanas de incidente sin muestras por el journal de bb-usable (el detector real): la del 2026-10-11 22:02 pasa de sin observar a OBSERVADA y DETECTADA (bb-usable declara COLAPSO 22:07:07, el watchdog reinicia 22:12:33). bb-usable vivo sin declarar COLAPSO cuenta como incidente no detectado (rc 1); journal ilegible es COULD_NOT_RUN (rc 2), nunca limpio."
evidence: {"fail": "tasks/evidence/DEBT-CALIBRA-PSI-CORTE-INVALIDO-INCIDENTE-11-OCT-22-02-NO-DETECTADO-01.fail.txt", "pass": "tasks/evidence/DEBT-CALIBRA-PSI-CORTE-INVALIDO-INCIDENTE-11-OCT-22-02-NO-DETECTADO-01.pass.txt", "e2e": "tasks/evidence/DEBT-CALIBRA-PSI-CORTE-INVALIDO-INCIDENTE-11-OCT-22-02-NO-DETECTADO-01.e2e.txt"}
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

## Cierre (2026-10-16)
- **Por que la ventana no tenia excursion en las muestras:** hueco de muestreo. CERO muestras de bin/bb con ts en [22:02, 22:12] (el mismo patron cuenta 5 a las 22:00 y 49 en [22:44, 22:54]). El detector real si la vio: el journal de `bb-usable` da `PSI memory full avg10=42.6 >= 10 -- racha 1/10` a las 22:02:07, `COLAPSO: ... sostenido 300s >= 300s` a las 22:07:07, y systemd `Watchdog timeout (limit 6min)!` a las 22:12:33. Lineas literales en la evidencia e2e.
- **Arreglo:** `tools/calibra_psi.py` consulta el journal (`lee_journal`, `eventos_journal`, `observa_journal`) SOLO para las ventanas sin muestras dentro. Detectada = bb-usable declara COLAPSO dentro de la ventana (misma regla de disparo que las muestras); reiniciar se imprime aparte. bb-usable vivo y sin COLAPSO -> `no_detectados` -> CORTE INVALIDO. Journal ilegible -> `COULD_NOT_RUN` impreso junto al veredicto y rc 2. El corte (10 % / 300 s) no se toco; INCIDENTES no se edito salvo el comentario del septimo (22:08:18 -> 22:07:07, la primera declaracion real de COLAPSO).
- **Lo que queda abierto, con su ficha:** los 3 falsos positivos del 16-oct siguen como deuda impresa, atados a `DEBT-COLAPSO-CONFINADO-A-APP-SLICE-REINICIA-LA-MAQUINA-ENTERA-01` (FALSOS_POSITIVOS_CONOCIDOS); por eso el veredicto es `CALIBRADO, con deuda impresa arriba` y no `CALIBRADO`.

## Root Cause
`calibra_psi` solo leia las muestras de `bb sample`, que dejo de escribir a las 22:00:34 del 2026-10-11, durante el stall que tenia que medir. Sin otra fuente, la ventana 22:02-22:12 era inobservable: primero salia `no_detectados` (afirmaba un fallo del corte sobre muestras inexistentes) y despues `sin_muestras_en_ventana` (verde sin haber validado el corte contra el incidente).

## Regression Test
`tests/test_calibra_psi.py`: `test_control_negativo_bb_usable_vivo_sin_declarar_colapso_es_no_detectado` (con el codigo anterior sale rc 0, `assert 0 == 1`), `test_control_negativo_colapso_declarado_despues_de_la_ventana_no_la_detecta`, `test_el_journal_observa_la_ventana_sin_muestras_declara_colapso_y_reinicia`, `test_declarar_colapso_y_reiniciar_se_imprimen_por_separado`, `test_journal_ilegible_es_could_not_run_junto_al_veredicto`, y los de `lee_journal` (journalctl ausente, timeout, rc != 0, aviso de permisos -> motivo, nunca lista vacia).

## Verification Evidence
`tasks/evidence/DEBT-CALIBRA-PSI-CORTE-INVALIDO-INCIDENTE-11-OCT-22-02-NO-DETECTADO-01.{fail,pass,e2e}.txt`: fail = close_check antes (rc 0 por reclasificacion) y los tests nuevos contra el codigo anterior; pass = 60 tests, pyright 0 errores, close_check despues rc 0 con la ventana `declara COLAPSO 22:07:07, reinicia 22:12:33 (watchdog)`; e2e = lineas literales del journal (hostname -> HOST), 0 muestras en la ventana con su control (5 a las 22:00, 49 en 22:44-22:54), y el control negativo real sin journalctl en PATH: COULD_NOT_RUN, rc 2.
