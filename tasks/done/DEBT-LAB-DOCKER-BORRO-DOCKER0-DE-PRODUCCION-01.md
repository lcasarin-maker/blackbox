---
id: DEBT-LAB-DOCKER-BORRO-DOCKER0-DE-PRODUCCION-01
kind: task
domain: HARDWARE
title: "El dockerd del laboratorio borro el puente docker0 de produccion al arrancar con --bridge=none"
status: done
closed_at: 2026-10-12
evidence: {"pass": "tasks/evidence/DEBT-LAB-DOCKER-BORRO-DOCKER0-DE-PRODUCCION-01/pass.txt", "fail": "tasks/evidence/DEBT-LAB-DOCKER-BORRO-DOCKER0-DE-PRODUCCION-01/fail.txt", "e2e": "tasks/evidence/DEBT-LAB-DOCKER-BORRO-DOCKER0-DE-PRODUCCION-01/e2e.txt"}
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q 'bridge=bblab0' tools/portero_docker_lab.sh", "expect": "exit_zero", "porque": "El script del laboratorio (tools/portero_docker_lab.sh) arrancaba su dockerd con --bridge=none. Pasa cuando usa su propio puente bblab0 con su propia subred y no la bandera que elimina el docker0 del host."}
---

## Root Cause
El segundo `dockerd` del laboratorio nivel 2 arrancaba con `--bridge=none`. Con el puente desactivado Docker elimina el `docker0` del host (es un netdev global, no del daemon). `docker0` desaparecio a las 07:55:30 del 2026-10-12, segundos despues del primer `up`, y `atlas-pgvector` (red bridge) quedo sin red 5 h hasta que Luis reinicio Docker a las 13:16. El script declaraba "unico contacto con produccion: docker save": falso. Atribucion: por coincidencia de hora y comportamiento conocido de dockerd; no se reprodujo en un host aparte (exigiria root).

## Regression Test
`tests/test_lab_no_toca_docker0.py`: el script no contiene `--bridge=none` en codigo, usa `--bridge=bblab0 --bip=172.31.250.1/24`, `up` aborta si `docker0` existia antes y ya no, y `down` borra solo `bblab0`. Control negativo corrido: con la bandera vieja fallan 2 de 3.

## Verification Evidence
Ver pass.txt, fail.txt y e2e.txt. Limite declarado: las pruebas leen el script; probar el `dockerd` real exige root y un `up` del laboratorio, que debe correr Luis con la guarda nueva (que apaga el laboratorio si `docker0` desaparece).
