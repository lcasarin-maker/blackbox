---
id: DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01
kind: task
domain: GPU
title: "Dos colapsos de memoria el 11-oct coinciden con suites pytest de Atlas sin techo de memoria"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q suites_pytest_con_techo tasks/evidence/DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01/medicion.md", "expect": "exit_zero", "porque": "Dos colapsos (boots 5461291a a las 22:02 y 7b217d8b a las 22:44, PSI memory full 98 % con 15-30 GB disponibles, reinicio por watchdog, BERT 0x10) arrancaron con una suite pytest de Atlas corriendo (scopes liberation_job_test_* a las 21:48 y 22:43), vLLM con 33 peticiones y, la primera vez, un pre-push de otro proyecto. En el segundo no corria ningun job de la cola. Cierra cuando haya una medicion con las suites bajo un scope con MemoryMax y el colapso no se reproduzca, escrita en medicion.md con la frase suites_pytest_con_techo."}
---

## Medido (2026-10-12)

- Colapso 1: PSI full 42 % a las 22:02:07 (boot 5461291a) hasta el reinicio de las 22:12:46. Corria el job 79_00 de Atlas, una suite de Atlas desde las 21:48 y un pre-push de otro proyecto desde las 21:51.
- Colapso 2: PSI full >= 10 sostenido desde ~22:44:12 (boot 7b217d8b), reinicio a las 22:54:41. Solo corrian jobs pequenos de la cola (terminaron 22:27) y una suite pytest de Atlas desde las 22:43:47.
- En ambos, `earlyoom` veia 15-30 GB disponibles: el disponible no predice este colapso.
- El job de reindexado 79_00 no es causa suficiente: el colapso 2 ocurrio sin el. Otro reindexado igual (68) llego a 15 GB disponibles y termino bien.
- Las 5 s de telemetria se cortan antes del colapso (el sampler se estrangula): no hay RSS por proceso dentro de la ventana.

## Que falta

1. Un tope de memoria por scope para suites y pushes (la sesion de Declutter propuso MemoryMax=20G sin swap).
2. Captura de los procesos mayores al entrar PSI full >= 10, antes de que el sampler se estrangule.
3. Reproducir con el tope puesto.
