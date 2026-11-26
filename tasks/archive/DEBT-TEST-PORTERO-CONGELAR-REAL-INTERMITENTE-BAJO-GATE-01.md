---
id: DEBT-TEST-PORTERO-CONGELAR-REAL-INTERMITENTE-BAJO-GATE-01
kind: task
domain: MEMORY
title: "tests/test_portero.py::test_real_mover_topar_en_caliente_congelar_y_control_negativo falla de forma intermitente bajo la puerta paralela"
status: done
closed_at: 2026-10-20
closure_type: fixed
closure_reason: "Causa medida: el portero vivo (modo actuar) descongela todo scope bb-portero-<clase>-<pid>.scope congelado cuando hay turno libre, y el scope desechable de la prueba (bb-portero-suite-<pid>) casaba con esa regla; su log tiene 2 filas de descongelar con el perfil de la prueba (1 proceso, 2 MB, edad 0.2 s), una sobre el scope 3817592 que cita la ficha. No era el plazo (0.000 s en 10 lecturas) ni otra prueba. Arreglo: la prueba usa el prefijo bbtest-portero- (monkeypatch de po.PREFIJO_UNIDAD) y el demonio no la reconoce. Con un demonio emulado el test original falla 10 de 10 y el arreglado pasa 10 de 10; la puerta paralela completa con el arreglo dio 0 fallos en 10 corridas (la tasa base propia sin arreglo fue 0 de 5, asi que esas corridas solas no discriminan)."
evidence:
  fail: tasks/evidence/DEBT-TEST-PORTERO-CONGELAR-REAL-INTERMITENTE-BAJO-GATE-01/fail.txt
  pass: tasks/evidence/DEBT-TEST-PORTERO-CONGELAR-REAL-INTERMITENTE-BAJO-GATE-01/pass.txt
  medicion: tasks/evidence/DEBT-TEST-PORTERO-CONGELAR-REAL-INTERMITENTE-BAJO-GATE-01/medicion.txt
severity: P3
origin: detected
satd_family: BLIND_INSTRUMENT
created: 2026-10-20
close_check: {"cmd": "grep -qx test_portero_congelar_estable tasks/evidence/DEBT-TEST-PORTERO-CONGELAR-REAL-INTERMITENTE-BAJO-GATE-01/medicion.txt", "expect": "exit_zero", "porque": "Cierra cuando la puerta pytest paralela (-n 4) corra N veces seguidas sin este fallo y medicion.txt lo declare con la linea exacta test_portero_congelar_estable, con el numero de corridas y el control negativo (una corrida con el escenario de carga que lo hace fallar)."}
---

## Medido 2026-10-20 (corrida de /cerrar-deuda)

Dos corridas seguidas de la puerta de producto (`python3 -m pytest -q -n 4 -m "not slow and not e2e and not mutates_real_source" --ignore=tests/test_bb_bash.py`):

- Corrida 1: `1 failed, 3703 passed, 3 skipped, 14 xfailed`. El fallo: `tests/test_portero.py:462`, `assert _espera_evento(destino, "frozen 1")` sobre el scope `bb-portero-suite-3817592.scope` (falso: el cgroup no reporto `frozen 1` en su plazo).
- Corrida 2: `3704 passed, 3 skipped, 14 xfailed`.
- La misma prueba sola: `1 passed` dos veces en este arbol y una en un worktree de `HEAD` limpio.

Los cambios de esa sesion tocaron solo fichas de `tasks/`, asi que el fallo no viene de ellos. Es una prueba que congela un cgroup real y espera un evento con plazo; bajo cuatro workers y otras pruebas de la clase de cgroups el plazo no alcanza una vez de dos.

## Actualizacion 2026-10-20 (cuatro corridas de la puerta en la misma sesion)

Corridas 1 y 3 fallaron con este test (`1 failed, 3703 passed` y `2 failed, 3706 passed`; en la 3 el otro fallo era un archivo con el hostname, ya corregido en 4992fb9f). Corridas 2 y 4 pasaron (`3704 passed` y `3708 passed`). Total medido: 2 fallos de 4 corridas.

## Que falta

Medir cuantas corridas de la puerta fallan en una serie (N fijo y declarado), identificar si el plazo de `_espera_evento` es el limite o si otra prueba mueve el cgroup, y marcar la prueba para el carril serial (`mutates_real_source`, como `DEBT-TEST-ESCALON-REAL-MATADO-POR-OTRO-PROCESO-01`) o dar a la espera un plazo medido. Una prueba que falla al azar en la puerta de push bloquea publicar sin que nada este roto; pasarla a ciegas con un reintento es el cierre por supresion que la ley prohibe.
