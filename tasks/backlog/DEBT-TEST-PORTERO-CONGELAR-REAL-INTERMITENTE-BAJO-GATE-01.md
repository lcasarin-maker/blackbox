---
id: DEBT-TEST-PORTERO-CONGELAR-REAL-INTERMITENTE-BAJO-GATE-01
kind: task
domain: MEMORY
title: "tests/test_portero.py::test_real_mover_topar_en_caliente_congelar_y_control_negativo falla de forma intermitente bajo la puerta paralela"
status: open
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

## Que falta

Medir cuantas corridas de la puerta fallan en una serie (N fijo y declarado), identificar si el plazo de `_espera_evento` es el limite o si otra prueba mueve el cgroup, y marcar la prueba para el carril serial (`mutates_real_source`, como `DEBT-TEST-ESCALON-REAL-MATADO-POR-OTRO-PROCESO-01`) o dar a la espera un plazo medido. Una prueba que falla al azar en la puerta de push bloquea publicar sin que nada este roto; pasarla a ciegas con un reintento es el cierre por supresion que la ley prohibe.
