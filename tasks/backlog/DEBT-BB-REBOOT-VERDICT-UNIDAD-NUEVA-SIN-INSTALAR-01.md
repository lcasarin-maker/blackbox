---
id: DEBT-BB-REBOOT-VERDICT-UNIDAD-NUEVA-SIN-INSTALAR-01
kind: task
domain: VERDICT
title: "bb-reboot-verdict con --pendientes y OnBootSec=20s esta en el repo y no instalado"
status: open
severity: P1
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-02
close_check: {"cmd": "cmp systemd/bb-reboot-verdict.timer \"$HOME/.config/systemd/user/bb-reboot-verdict.timer\" && cmp systemd/bb-reboot-verdict.service \"$HOME/.config/systemd/user/bb-reboot-verdict.service\"", "expect": "exit_zero", "porque": "Cierra cuando las dos unidades instaladas son byte a byte las del repo. Hoy sale 1: la instalada corre `--ultimos 1 --escribe` una sola vez a los 3 min (y el servicio instalado ni siquiera trae los ExecStartPre del repo)."}
---

## Que falta
La rama del arreglo de `tools/reboot_verdict.py` (2026-11-02) cambio `systemd/bb-reboot-verdict.{service,timer}` y sus
gemelas en `adopted/systemd-user/`: `ExecStart=... --pendientes --escribe` y `OnBootSec=20s` + `OnBootSec=3min`. Un
agente no instala unidades. Pasos (los da Luis, sin sudo):

    cp systemd/bb-reboot-verdict.service systemd/bb-reboot-verdict.timer ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user list-timers bb-reboot-verdict.timer   # proxima corrida: en el proximo arranque

Primera corrida esperada: `--pendientes --escribe` anade una fila por cada boot de `journalctl --list-boots` sin fila
(23 el 2026-11-02, medido con la corrida de solo lectura `python3 -m tools.reboot_verdict --pendientes`), salvo el vivo
y salvo los dos boots con fila falsa (ver DEBT-REBOOTS-JSONL-DOS-FILAS-ERRONEAS-SIN-CORRECCION-01).

Sin verificar: que la unidad dispare a los 20 s en un arranque real (`systemd-analyze verify --user` acepta los dos
`OnBootSec`; no se reinicio nada para medirlo).
