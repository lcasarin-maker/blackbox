---
id: DEBT-RELOJ-VERIFICADOR-SIN-LECTURA-DEL-RANGO-LGC-APLICADO-01
kind: task
domain: THERMAL
title: "El verificador A/B de topes de reloj no puede leer el rango -lgc aplicado: GB10 no lo expone"
status: open
severity: P3
origin: detected
satd_family: BLIND_INSTRUMENT
created: 2026-10-16
close_check: {"cmd": "python3 -c \"import sys; from tools import verify_gpu_clock_cap_ab as v; sys.exit(0 if v._csv_policy({'stdout': '300, 2200'}) is not None else 1)\"", "expect": "exit_zero", "porque": "Medido 2026-10-16: tools/verify_gpu_clock_cap_ab.py::_csv_policy devuelve None siempre porque nvidia-smi en GB10 expone relojes actual/maximo y soportados, no el rango bloqueado con -lgc. Sin lectura nativa del rango aplicado, las lecturas de stock/tope/rollback del A/B quedan unknown y la ficha de topes de reloj no puede cerrar. Cierra cuando exista una fuente nativa del rango aplicado, con test que rechace una lectura falsa, o se decida con evidencia que no existe."}
---

## Medido
`tools/verify_gpu_clock_cap_ab.py` linea 95: `_csv_policy` borra su argumento y devuelve `None`; el comentario dice que una consulta `min.graphics` no esta soportada en GB10. La prueba positiva de `tests/test_clock_tradeoff_composed_pass.py` pasa solo a traves de un sustituto de `_csv_policy` (el mismo que usan los tests g3), nunca sobre la maquina.

## Que falta
Buscar una fuente nativa del rango aplicado (sysfs, NVML o `nvidia-smi -q`) y medirla con y sin `-lgc` en una ventana tuya; si no existe, cerrar la ficha con esa evidencia y un criterio alternativo votado. Origen: `DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01`.
