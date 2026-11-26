---
id: DEBT-RELOJ-VERIFICADOR-ETIQUETAS-DE-SENSORES-INCOMPLETAS-01
kind: task
domain: THERMAL
title: "El verificador de topes de reloj no da pasa: solo 3 de 11 sensores tienen etiqueta"
status: done
closed_at: 2026-10-20
closure_type: fixed
closure_reason: "Segunda boleta de Luis 2026-10-20 (opcion 1): el name del hwmon (chip_name) identifica una entrada sin label solo si ese dispositivo tiene UNA sola temp*_input y el nombre es no vacio y unico entre los hwmon. Sobre la captura real hwmon2/temp1_input (mt7925_phy0) queda identificada: 11 de 11, sensor_labels=pass y el close_check pasa de rc 1 a rc 0. Los tests de la regla se ponen rojos contra el verificador de master y contra un mutante por cada restriccion quitada. El verificador completo sigue en unknown por matched_clock_runs, rollback y same_window, que no son de esta ficha."
evidence:
  fail: tasks/evidence/DEBT-RELOJ-VERIFICADOR-ETIQUETAS-DE-SENSORES-INCOMPLETAS-01/fail.txt
  pass: tasks/evidence/DEBT-RELOJ-VERIFICADOR-ETIQUETAS-DE-SENSORES-INCOMPLETAS-01/pass.txt
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

## Medido 2026-10-20 (tras el voto de Luis: identificar por `thermal_zone*/type`)
Implementado en `tools/verify_clock_cap_tradeoff.py::_unidentified_sensors`: una entrada sin `temp*_label`
cuenta como identificada solo por el puente thermal_hwmon del kernel (un unico hwmon cuyo `name` es el type
de la zona, con tantas `temp*_input` como zonas de ese type). Tests en `tests/test_clock_tradeoff_composed_pass.py`
(positivo, zona sin label ni type, dispositivo sin thermal_zone, conteo distinto o nombre ambiguo).

Sobre la captura real el resultado es 10 de 11 identificadas; queda una:
`unidentified: ['/sys/class/hwmon/hwmon2/temp1_input']` y `sensor_labels: unknown`. Es `mt7925_phy0`
(radio Wi-Fi MediaTek, `device -> .../ieee80211/phy0`); la lectura de solo lectura de `/sys/class/thermal`
el 2026-10-20 muestra 7 zonas, todas `acpitz`, ninguna para el Wi-Fi. El `type` no puede identificarla:
la ficha sigue abierta. Evidencia literal: `tasks/evidence/DEBT-RELOJ-VERIFICADOR-ETIQUETAS-DE-SENSORES-INCOMPLETAS-01/fail.txt`.

Limite declarado de la identificacion por type: las 7 zonas se llaman `acpitz`; el type las vincula a
`thermal_zone0..6` pero no dice que componente fisico mide cada una.

Falta una decision de Luis sobre la entrada del Wi-Fi:
1. Aceptar el `name` del hwmon (ya capturado como `chip_name`) como identificador cuando el dispositivo tiene una
   sola `temp*_input`. Costo: ~10 lineas y un test rojo/verde; no requiere captura nueva. Riesgo: amplia la fuente
   de identidad mas alla de `thermal_zone*/type`; un nombre de driver identifica el chip, no el componente.
2. Extender `tools.thermal_coverage` para guardar `readlink hwmon*/device` y aceptar como identidad el dispositivo
   del kernel (aqui `ieee80211/phy0`). Costo: cambio del capturador, captura nueva de solo lectura y sus tests;
   la captura nueva cae fuera de la ventana A/B actual (`same_window` ya es unknown).
3. Dejarlo como esta. Costo: `verify_clock_cap_tradeoff` nunca da pass en este equipo mientras exista el Wi-Fi.
Excluir del requisito los dispositivos fuera del subsistema thermal baja el requisito y queda fuera sin voto explicito.

## Cerrada 2026-10-20 (segunda boleta de Luis: opcion 1)
`_unidentified_sensors` acepta el `chip_name` del hwmon como identificador cuando el dispositivo tiene una sola
`temp*_input`, el nombre existe, es no vacio y no se repite en otro hwmon. Nada mas: no se excluye ningun
dispositivo ni se baja otro requisito. Sobre la captura real: 11 de 11 identificadas, `sensor_labels: pass`.
Limite declarado (aceptado en la boleta): un nombre de driver identifica el chip, no el componente de la placa.
Tests: `test_single_input_device_identified_by_unique_chip_name_pass` y
`test_chip_name_rule_restrictions_keep_unknown[no_chip_name|chip_name_absent|chip_name_blank|chip_name_repeated|two_inputs]`;
reemplazan a `test_unlabelled_device_without_thermal_zone_is_not_pass`, que fijaba la politica anterior al voto.
Evidencia literal y controles negativos: `tasks/evidence/DEBT-RELOJ-VERIFICADOR-ETIQUETAS-DE-SENSORES-INCOMPLETAS-01/pass.txt`.
