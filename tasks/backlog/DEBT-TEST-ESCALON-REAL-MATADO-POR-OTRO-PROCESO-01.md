---
id: DEBT-TEST-ESCALON-REAL-MATADO-POR-OTRO-PROCESO-01
kind: task
domain: VERDICT
title: "tests/test_escalon_app_slice.py::test_control_real_elige_y_mata_al_acaparador... falla en el pre-push cuando alguien mata a su acaparador antes de tiempo"
status: open
severity: P3
origin: measured
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
