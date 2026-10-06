---
id: DEBT-RENDERER-PROBE-SLEEP-01
kind: task
domain: VERDICT
title: "Sustituir los time.sleep del probe de terminacion diferida del renderer por esperas por evento"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-05
close_check: {"cmd": "python3 -m pytest -q tests/test_renderer_probe_sleep.py", "expect": "exit_zero", "porque": "El probe espera la senal real (marcador de proceso visible, llamada killpg observada) en vez de tiempo fijo, y su control negativo sigue distinguiendo la terminacion diferida de la inmediata. Mientras haya sleeps, el cierre sigue pendiente."}
---

## Registro y responsable

Registro creado por /clean el 2026-10-05 para dar ticket a los dos `time.sleep` (lineas 50 y 64) del probe `renderer-delayed-probe.py`, que zero-debt bloqueaba sin ticket. Responsable: Luis Casarin. Decision de Luis (boleta 2026-10-05): abrir ficha en vez de reemplazar el sleep o quitar el probe.

## Evidencia y alcance

- tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-sunset/renderer-delayed-probe.py

El sleep de la linea 50 es intervalo de sondeo dentro de un bucle con deadline explicito. El de la linea 64 es el retraso que es el sujeto de la prueba. Ninguno es una espera de sincronizacion ciega, pero ambos son tiempo fijo y no senal.

## Criterio de cierre y control negativo

El cierre exige sustituir ambos sleeps por esperas sobre senal real y repetir el control negativo: la terminacion inmediata debe seguir distinguirse de la diferida.

## Estado

Abierta. La justificacion en el codigo cita esta ficha; no demuestra por si sola que el probe sea correcto.
