---
id: DEBT-PORTERO-IGNORA-SU-INTERRUPTOR-01
kind: task
domain: MEMORY
title: "El portero actua siempre: tools/portero.py no lee su interruptor (observar/actuar/off)"
status: open
severity: P2
origin: detected
detector: {"rule": "grep -c interruptores tools/portero.py == 0 mientras interruptores.json declara un modo 'portero'", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-14
close_check: {"cmd": "python3 -m pytest -q tests/test_portero.py::test_demonio_respeta_el_interruptor", "expect": "exit_zero", "porque": "Cierra cuando el demonio consulta interruptores.modo('portero') y una prueba demuestra las tres ramas: en off no hace nada, en observar registra lo que haria sin crear scopes ni congelar, en actuar adopta. Hoy la prueba no existe (rc=4) porque el demonio no tiene esa rama."}
---

## Medido (2026-10-14)
Resto declarado al cerrar `DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01` (ver su `medicion.txt`):

- `python3 -c "from tools import interruptores as i;print(i.modo('portero'))"` -> `actuar`.
- `grep -c interruptores tools/portero.py` -> `0` (rc=1). `cmd_demonio` llama a `_ciclo`, que llama a `aplica` sin condicion: el demonio crea scopes y congela con cualquier modo.
- Consecuencia medida: `tasks/evidence/FEATURE-PORTERO-UNIVERSAL-DE-LA-MAQUINA-01/medicion.txt` dice "el demonio esta en observar, solo registra", y ese mismo dia el portero ya actuaba (los tres `turno`/`fin` y, desde 13:54 UTC, `congelar`/`descongelar` en `portero.jsonl`). La boleta de Luis del 2026-10-14 pedia observar primero y descartaba actuar directo: el interruptor no podia garantizarlo.

## Arreglo propuesto
`cmd_demonio` lee `interruptores.modo("portero")` en cada vuelta (es un archivo de pocos bytes): `off` no observa ni actua; `observar` registra las acciones con `"modo": "observar"` sin llamar a `_adopta`/`congela`; `actuar` como hoy. Prueba con `Efectos` falsos y un `interruptores.json` temporal para las tres ramas, y control negativo: en `observar` el ejecutor falso no recibe ninguna llamada.
