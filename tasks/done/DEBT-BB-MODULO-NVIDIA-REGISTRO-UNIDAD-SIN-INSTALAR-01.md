---
id: DEBT-BB-MODULO-NVIDIA-REGISTRO-UNIDAD-SIN-INSTALAR-01
kind: task
domain: VERDICT
title: "bb-modulo-nvidia-registro (ruta, sha256 y srcversion del nvidia.ko por arranque) esta en el repo y no instalado"
status: done
severity: P1
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-02
close_check: {"cmd": "cmp systemd/bb-modulo-nvidia-registro.timer \"$HOME/.config/systemd/user/bb-modulo-nvidia-registro.timer\" && cmp systemd/bb-modulo-nvidia-registro.service \"$HOME/.config/systemd/user/bb-modulo-nvidia-registro.service\"", "expect": "exit_zero", "porque": "Cierra cuando las dos unidades instaladas son byte a byte las del repo. Hoy sale 1 (cmp: No such file): un agente no instala unidades."}
closed_at: 2026-11-07
closure_type: verified_closed
closure_reason: "El close_check de la ficha sale 0 hoy (corrido por /debt el 2026-11-07); la ficha seguia abierta aunque su condicion ya se cumplia. Salida en la evidencia."
evidence:
  pass: tasks/evidence/DEBT-BB-MODULO-NVIDIA-REGISTRO-UNIDAD-SIN-INSTALAR-01/pass.txt
---

## Que falta
`tools/modulo_nvidia_registro.py` y `systemd/bb-modulo-nvidia-registro.{service,timer}` (gemelas en
`adopted/systemd-user/`) existen; ninguna unidad esta instalada. Sin ella, `reboot_verdict` escribe
`modulo_nvidia_* = "NOT_COLLECTED"` en toda fila nueva, y los arranques anteriores no se pueden reconstruir.
Pasos (los da Luis, sin sudo):

    cp systemd/bb-modulo-nvidia-registro.service systemd/bb-modulo-nvidia-registro.timer ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable --now bb-modulo-nvidia-registro.timer
    python3 -m tools.modulo_nvidia_registro            # solo lectura: imprime la linea de este arranque

Efecto: en cada arranque (a los 5, 20 y 60 s) una linea en `~/.local/share/blackbox/modulo_nvidia_por_arranque.jsonl`
(solo-anexar, idempotente por boot_id; si nvidia aun no esta cargado sale rc 1 sin escribir y reintenta).
`reboot_verdict` la lee y rellena `modulo_nvidia_{ruta,sha256,version,srcversion,parchado,fuente}`.

Sin verificar: que la unidad dispare en un arranque real y que a los 5 s `/sys/module/nvidia` ya exista
(`systemd-analyze verify --user` pasa; no se reinicio nada). Limite: el usuario manager de systemd puede arrancar
despues de los 5 s; `OnBootSec` cuenta desde el arranque del kernel y dispara de inmediato lo vencido.
