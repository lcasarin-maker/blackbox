---
id: DEBT-OBSERVADOR-ULTIMO-ALIENTO-INSTALADO-01
kind: task
domain: SYSTEM
title: "bb-ultimo-aliento (muestreador de 250 ms con anillo fijo) instalado y activo como unidad de sistema"
status: done
severity: P1
origin: split
split_from: DEBT-OBSERVADORES-CONSTRUIDOS-SIN-INSTALAR-01
created: 2026-11-16
closed_at: 2026-11-16
close_check: {"cmd": "systemctl is-active --quiet bb-ultimo-aliento.service && systemctl is-enabled --quiet bb-ultimo-aliento.service && test \"$(stat -c %s /var/lib/bb-ultimo-aliento/anillo.bin)\" = 4194304", "expect": "exit_zero", "porque": "Unidad de sistema activa, habilitada y con el anillo de 4 MiB. Control negativo: con una unidad inexistente el mismo patron sale distinto de cero."}
---

Hija de `DEBT-OBSERVADORES-CONSTRUIDOS-SIN-INSTALAR-01` (division votada por Luis, 2026-11-16).

Medido 2026-11-16 ~21:36 -0600: `is-active` active, `is-enabled` enabled, MainPID vivo desde 14:37:32 (0 reinicios), memoria 17.8 MB
(tope 96 MB), `/usr/local/lib/blackbox/ultimo_aliento.py` y la unidad en `/etc/systemd/system/` identicas (cmp) al repo, anillo
4 194 304 bytes con mtime avanzando (21:35 y 21:36:02) y `/run/bb-ultimo-aliento/estado_maquina.json` con PSI, memoria y 7 zonas
termicas. Luis reejecuto los cinco comandos de instalacion; no cambiaron nada material (ya estaba instalada).
Limite: la ausencia de `hwmon` de potencia queda declarada por el propio estado (`sin power/in/curr*_input`).
