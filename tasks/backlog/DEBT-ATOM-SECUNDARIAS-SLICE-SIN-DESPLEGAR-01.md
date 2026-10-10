---
id: DEBT-ATOM-SECUNDARIAS-SLICE-SIN-DESPLEGAR-01
kind: task
domain: SYSTEMD
title: "Desplegar atom-secundarias.slice en /etc/systemd/system (hoy bb drift lo marca AUSENTE)"
status: open
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
