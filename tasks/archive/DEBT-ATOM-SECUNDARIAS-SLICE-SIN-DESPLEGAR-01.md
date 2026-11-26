---
id: DEBT-ATOM-SECUNDARIAS-SLICE-SIN-DESPLEGAR-01
kind: task
domain: SYSTEMD
title: "Desplegar atom-secundarias.slice en /etc/systemd/system (hoy bb drift lo marca AUSENTE)"
status: done
closed_at: 2026-10-13
closure_type: relocated_prior_verification
reason: "El slice adoptado esta desplegado e identico en /etc/systemd/system (desde 2026-10-10 07:05) y bb drift lo marca igual; la ficha seguia abierta tras el despliegue. Control negativo: el mismo cmp contra una copia con un byte alterado sale 1."
evidence: {"pass": "tasks/evidence/DEBT-ATOM-SECUNDARIAS-SLICE-SIN-DESPLEGAR-01/pass.txt", "fail": "tasks/evidence/DEBT-ATOM-SECUNDARIAS-SLICE-SIN-DESPLEGAR-01/fail.txt", "e2e": "tasks/evidence/DEBT-ATOM-SECUNDARIAS-SLICE-SIN-DESPLEGAR-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: INFRASTRUCTURE_GOVERNANCE
created: 2026-10-10
close_check: {"cmd": "bash tools/verifica_slice_desplegado.sh", "expect": "exit_zero", "porque": "El slice adoptado debe existir y ser identico en la maquina; mientras no, bb drift sale con exit 1 y el timer diario de drift reporta fallo."}
---

## Hueco

`FEATURE-ADOPT-ATOM-SECUNDARIAS-SLICE` dejo el slice versionado, probado e inventariado, pero copiarlo a `/etc/systemd/system` exige root y `sudo -n` pide contrasena. `bb drift` imprime `AUSENTE /etc/systemd/system/atom-secundarias.slice` y sale con exit 1 hasta que se despliegue.

## Remedio

```bash
sudo ./enable-privileged.sh
```

El bloque nuevo copia el slice y recarga systemd. No reinicia nada ni habilita nada: un slice solo actua cuando algo se lanza con `systemd-run --slice=atom-secundarias.slice`.

## Nota

El slice no entra en el presupuesto de compromisos de memoria del repo (system 12G, docker 14G, app 42G). Si algo empieza a usarlo, sus 48G de `MemoryMax` hay que sumarlos a ese presupuesto.

## Root Cause
El slice estaba versionado pero no desplegado: copiarlo a /etc/systemd/system exige root y bb drift lo marcaba AUSENTE con exit 1.

## Regression Test
`tools/verifica_slice_desplegado.sh` (el close_check) y `bb drift`, que compara lo adoptado con lo instalado.

## Verification Evidence
fail.txt: cmp contra una copia alterada sale 1 (el check discrimina); pass.txt: el slice instalado es identico al adoptado; e2e.txt: archivo presente (root, 2026-10-10), LoadState=loaded y `bb drift` igual.
