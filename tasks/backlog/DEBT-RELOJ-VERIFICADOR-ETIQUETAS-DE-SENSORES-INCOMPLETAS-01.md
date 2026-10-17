---
id: DEBT-RELOJ-VERIFICADOR-ETIQUETAS-DE-SENSORES-INCOMPLETAS-01
kind: task
domain: THERMAL
title: "El verificador de topes de reloj no da pasa: solo 3 de 11 sensores tienen etiqueta"
status: open
severity: P3
origin: detected
detector: {"rule": "tests/test_reloj_verificador_limites.py::test_etiquetas_de_sensores_completas_en_la_captura_real", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-16
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider --runxfail tests/test_reloj_verificador_limites.py::test_etiquetas_de_sensores_completas_en_la_captura_real", "expect": "exit_zero", "porque": "Medido 2026-10-16 por el agente del verificador: sensor_labels=unknown con la captura del 2026-10-03; los sensores acpitz no exponen temp*_label. Mientras sea unknown, verify_clock_cap_tradeoff no puede dar pass en este equipo aunque se haga la ventana del motor. Cierra cuando una captura nueva etiquete todas las zonas o se decida con evidencia como identificar las que no traen etiqueta."}
---

## Medido
En la captura `THERMAL_CAPTURE` hay 11 entradas `temp*_input` en hwmon y solo 3 traen `temp*_label`. `python3 -c "from tools import verify_clock_cap_tradeoff as v; print(v.verify()['checks'])"` -> `sensor_labels: unknown`. Origen: `DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01` (voto de Luis 2026-10-16, ruta a PASS).

## Que falta
Decidir si las zonas sin etiqueta se identifican por `thermal_zone*/type` o por otra fuente, con un test que muestre rojo cuando una zona queda sin identificar. No se baja el requisito de etiquetas para que pase.
