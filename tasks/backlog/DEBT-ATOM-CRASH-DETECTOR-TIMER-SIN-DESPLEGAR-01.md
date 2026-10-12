---
id: DEBT-ATOM-CRASH-DETECTOR-TIMER-SIN-DESPLEGAR-01
kind: task
domain: HARDWARE
title: "Desplegar el atom-crash-detector.timer a 4 min, despues de bb-reboot-verdict"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "grep -qx OnBootSec=4min /home/lcasarin/.config/systemd/user/atom-crash-detector.timer", "expect": "exit_zero", "porque": "La copia versionada ya dice OnBootSec=4min; la instalada sigue en OnBootSec=2min. Pasa cuando la instalada corre a 4 min, despues de bb-reboot-verdict."}
---

## Por que

Desde `DEBT-CONTRATO-ATLAS-INSTRUMENTOS-EN-BLACKBOX-01` (2026-10-11),
`Atlas/tools/detect_atom_crash.py` ya no mide: lee la fila que
`bb-reboot-verdict` (timer a 3 min del arranque) escribe en `reboots.jsonl`. El
timer instalado del detector corre a los 2 min, ANTES de que exista esa fila:
el crash del boot recien caido se dictamina un arranque tarde (o dias, si la
maquina no se reinicia). La copia versionada en `adopted/` ya esta a 4 min; la
instalada no se toco porque cambiar unidades vivas de la maquina requiere el
visto bueno del dueno.

## Como cerrar

```
cp adopted/systemd-user/atom-crash-detector.timer ~/.config/systemd/user/
systemctl --user daemon-reload
```

Despues, `bb drift` deja de marcar la diferencia y el close_check pasa. La fila
del inventario de propiedad de SPEC.md para `bb-reboot-verdict.timer` dice
"(despues del `atom-crash-detector`)": desde este cambio es al reves y la fila
debe corregirse en la misma pasada.
