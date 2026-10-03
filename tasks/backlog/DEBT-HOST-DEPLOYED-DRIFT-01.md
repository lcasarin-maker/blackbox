---
id: DEBT-HOST-DEPLOYED-DRIFT-01
kind: debt
domain: VERDICT
title: Sincronizar dos archivos desplegados que difieren del repo
status: open
severity: P2
origin: detected
satd_family: BLIND_INSTRUMENT
detector: {"rule": "bb drift: two deployed files differ", "confidence": 1.0}
created: 2026-10-03
close_check: {"cmd": "./bin/bb drift", "expect": "exit_zero", "porque": "El comparador debe observar archivos reales iguales al repo; su control negativo de divergencia ya existe en tests/test_bb_bash.py. No rebajar el detector ni copiar comentarios antiguos al repo para absolver el despliegue."}
owner: Luis; sincronización del host pendiente de autorización
---

## Root Cause

`bb drift` encontró dos divergencias reales. `/etc/modprobe.d/99-blackbox-uvm.conf` conserva el parámetro correcto pero describe una garantía de supervivencia que la investigación refutó. `/usr/local/bin/nvrm-watch.sh` conserva el patrón antiguo que omite `NV_ERR_NO_MEMORY` y presenta el error como predictor de freeze en lugar de evidencia.

## Regression Test

El criterio ejecuta el comparador nativo sobre el host. Las pruebas positivas y negativas de drift contrastan igualdad, divergencia y ausencia. El script actualizado debe pasar `bash -n`; su alcance es registrar, sin actuar sobre procesos ni cargar el driver.

## Verification Evidence

Salida literal de 41 sujetos, 2 divergencias, 0 ausencias, 1 suspensión: tasks/evidence/DEBT-HOST-DEPLOYED-DRIFT-01/fail.txt. Hashes y modos de ambos lados en source.json. La autorización de reinicio de bb-usable se mantiene separada de esta sincronización.
