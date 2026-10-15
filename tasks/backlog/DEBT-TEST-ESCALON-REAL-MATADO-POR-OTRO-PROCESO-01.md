---
id: DEBT-TEST-ESCALON-REAL-MATADO-POR-OTRO-PROCESO-01
kind: task
domain: VERDICT
title: "El test real del escalon pierde su acaparador por un SIGKILL ajeno en el pre-push"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-15
close_check: {"cmd": "python3 -m pytest -q tests/test_escalon_app_slice.py -p no:cacheprovider", "expect": "exit_zero", "porque": "Hoy pasa solo (8 de 8) y con 4 copias en paralelo (12 de 12); falla en el pre-push completo con xdist. El cierre real exige identificar al emisor del SIGKILL y aislarlo, no relanzar hasta que pase."}
---

## Medido (2026-10-15, push 51)
El pre-push fallo en `tests/test_escalon_app_slice.py:427` (`assert {p.pid for p in mios} == {hog.pid, senuelo.pid}`): el candidato `hog` (pid 1956399) ya no existia, solo el senuelo. `tasks`/logs: `$BLACKBOX_DATA/sigterm.jsonl` registra `SIGKILL` a la victima `1956399` a las 14:38:52Z (08:38:52 local), emisor pid 1952419 (`/opt/miniforge3/bin/python3.12`, ppid 1952263), es decir un proceso python de otro worker de pytest, UN SEGUNDO ANTES de que este test llegara a su propio kill. El `hog` se lanzo a las 08:38:49 (journal de usuario).
No se reprodujo: 8 de 8 solo y 12 de 12 con cuatro copias simultaneas. Ningun otro test de `tests/` hace kill real sobre scopes `app-com.anthropic.Claude-*` que se haya encontrado con `grep`; el emisor sigue sin identificar.

## Que falta
1. Identificar al emisor: en el siguiente fallo, correr el pre-push con `ps -eo pid,ppid,args | grep 1952263`-equivalente guardado al instante, o activar un trace que anote el comando del emisor (sigterm.jsonl solo da pid y comm).
2. Aislar: que el test acote su seleccion a sus dos scopes y no dependa de que nadie mas toque procesos python del uid, o marcarlo para correr solo (`xdist_group`).
No se relanza hasta que pase como cierre.

## Avance 2026-10-15: segundo fallo igual, mitigado con el carril serial (no cerrada)
El push 52 repitio el fallo: hog 2091742 muerto por `SIGKILL` de otro `python3.12` (pid 2088002, ppid 2087894) a las 08:47:54, otra vez a pid positivo (no killpg) y antes del kill propio del test. Con la compuerta de cobertura corrida sola (`python .simplecode/run.py simplecode.verification.coverage_target -q`, 08:56) el test PASA (3627 passed): el emisor aparece solo con otros hooks o workers en paralelo; el poller de procesos de esa corrida limpia (17549 pids vistos) no capturo ninguno porque no hubo fallo. Mitigacion: el test lleva el marcador `mutates_real_source` (registrado en pytest.ini), asi la compuerta lo corre solo en su fase 2 serial (medido: `1 passed, 3643 deselected`). Sigue abierta: el emisor no esta identificado; si el pre-push vuelve a fallar con este test, el siguiente paso es ejecutar el pre-push completo con el poller (`scratchpad/poller.py` en la sesion) y leer `sigterm.jsonl` por la victima.
