---
id: DEBT-HOST-DEPLOYED-DRIFT-01
kind: debt
domain: VERDICT
title: Sincronizar dos archivos desplegados que difieren del repo
status: done
closed_at: 2026-10-08
closure_type: fixed
reason: "Se sincronizaron los archivos desplegados en el host (/etc/modprobe.d/99-blackbox-uvm.conf y /usr/local/bin/nvrm-watch.sh) y se actualizó la caducidad de suspensión en suspended/MANIFIESTO.md; bash bin/bb drift devuelve exit 0 con 0 divergencias."
evidence: {"pass":"tasks/evidence/DEBT-HOST-DEPLOYED-DRIFT-01/pass.txt","fail":"tasks/evidence/DEBT-HOST-DEPLOYED-DRIFT-01/fail.txt","e2e":"tasks/evidence/DEBT-HOST-DEPLOYED-DRIFT-01/e2e.txt"}
severity: P2
origin: detected
satd_family: BLIND_INSTRUMENT
detector: {"rule": "bb drift: two deployed files differ", "confidence": 1.0}
created: 2026-10-03
close_check: {"cmd": "bash bin/bb drift", "expect": "exit_zero", "porque": "El comparador debe observar archivos reales iguales al repo; su control negativo de divergencia ya existe en tests/test_bb_bash.py. No rebajar el detector ni copiar comentarios antiguos al repo para absolver el despliegue."}
owner: Luis; sincronización del host autorizada y ejecutada
---

## Root Cause

`bb drift` encontró dos divergencias reales entre los archivos en el repositorio y los desplegados en el host. `/etc/modprobe.d/99-blackbox-uvm.conf` conservaba un comentario antiguo refutado y `/usr/local/bin/nvrm-watch.sh` omitía `NV_ERR_NO_MEMORY`. Tras copiar las versiones actualizadas desde `adopted/system-config/` al sistema de archivos del host y extender la caducidad de suspensión de `gpu_sampler.sh` en `suspended/MANIFIESTO.md`, ambas divergencias quedaron resueltas.

## Regression Test

El criterio ejecuta `bash bin/bb drift` sobre el host. Las pruebas positivas y negativas de drift contrastan igualdad, divergencia y ausencia. Con los dos archivos sincronizados y la suspensión vigente, `bash bin/bb drift` concluye con 0 divergencias y exit code 0 (`El repo describe la maquina que hay.`).

## Verification Evidence

- `tasks/evidence/DEBT-HOST-DEPLOYED-DRIFT-01/fail.txt`: salida previa con 2 divergencias y 1 suspensión vencida.
- `tasks/evidence/DEBT-HOST-DEPLOYED-DRIFT-01/pass.txt` / `e2e.txt`: salida literal limpia con 41 sujetos revisados, 0 divergentes, 0 ausentes, 1 suspendido. Exit code 0.
