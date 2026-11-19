---
id: DEBT-BB-USABLE-INACTIVO-DEJA-CIEGO-EL-WATCHDOG-01
kind: task
domain: MONITORING
title: "bb-usable esta cargado pero inactivo: el watchdog de hardware sigue ciego ante una maquina inservible"
status: open
severity: P2
origin: detected
detector: {"rule": "bin/bb status", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-11-18
close_check: {"cmd": "! bin/bb status 2>&1 | grep -E 'FALTA +bb-usable|CIEGO +watchdog'", "expect": "exit_zero", "porque": "Medido 2026-11-18 fuera del sandbox: bb status da FALTA bb-usable (LoadState=loaded ActiveState=inactive) y CIEGO watchdog de hardware (vigila PID 1, sano 17h45m y 5h55m en los congelamientos). El cierre exige que ninguna de las dos lineas aparezca."}
---

## Medido (2026-11-18)
- `bin/bb status` (con acceso al bus de systemd): `FALTA bb-usable ... ActiveState=inactive: sudo ./enable-privileged.sh`, y `CIEGO watchdog de hardware (1min)` cuyo remedio dice armar bb-usable.
- Armarlo exige `sudo ./enable-privileged.sh`; un agente no usa sudo. Lo ejecuta Luis tras leer el script.

## Aparte, sin ficha propia hoy
`CIEGO earlyoom ante agotamiento de memoria unificada`: su umbral lee MemAvailable, que marco 56 % durante los congelamientos del 2026-09-22/23 (ver `bin/bb status`). Es un limite conocido del instrumento; si se quiere cerrar, abrir ficha con un umbral que no dependa de MemAvailable.
