---
id: DEBT-BB-AVISO-GPU-RESET-UNIDAD-NUEVA-SIN-INSTALAR-01
kind: task
domain: GPU
title: "bb-aviso-gpu-reset (alarma de timeout del GSP / Xid 154) esta en el repo y no instalada"
status: done
severity: P1
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-02
close_check: {"cmd": "cmp systemd/bb-aviso-gpu-reset.timer \"$HOME/.config/systemd/user/bb-aviso-gpu-reset.timer\" && cmp systemd/bb-aviso-gpu-reset.service \"$HOME/.config/systemd/user/bb-aviso-gpu-reset.service\"", "expect": "exit_zero", "porque": "Cierra cuando las dos unidades instaladas son byte a byte las del repo. Hoy sale 1: no estan instaladas."}
closed_at: 2026-11-07
closure_type: verified_closed
closure_reason: "El close_check de la ficha sale 0 hoy (corrido por /debt el 2026-11-07); la ficha seguia abierta aunque su condicion ya se cumplia. Salida en la evidencia."
evidence:
  pass: tasks/evidence/DEBT-BB-AVISO-GPU-RESET-UNIDAD-NUEVA-SIN-INSTALAR-01/pass.txt
---

## Que falta
`tools/aviso_gpu_reset.py` (punto 2 de DEBT-NVRM-GSP-TIMEOUT-XID154-KERNEL-7-0-SIN-ALARMA-01) lee el journal de kernel
del arranque actual y, si trae `rpcRecvPoll timedout` o `Xid ...: 154`, avisa por notify-send y anota una fila por
boot_id en `~/.local/share/blackbox/aviso_gpu_reset.jsonl`. Un agente no instala unidades. Pasos (los da Luis, sin sudo):

    cp systemd/bb-aviso-gpu-reset.service systemd/bb-aviso-gpu-reset.timer ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable --now bb-aviso-gpu-reset.timer
    systemctl --user list-timers bb-aviso-gpu-reset.timer

Medido el 2026-11-02: contra 7cd0848b8fc742e982970cc9697c34e9 `detectado: true` (7057 asserts); contra el arranque
actual en 6.17 `detectado: false`. Sin verificar: el aviso real en pantalla (`notify-send` nunca se disparo en vivo) y
que el timer dispare a los 60 s en un arranque 7.0 real.
