---
id: DEBT-SYSCTL-NMI-WATCHDOG-NO-ESCRIBIBLE-EN-KERNEL-7-0-01
kind: task
domain: SYSTEM
title: "systemd-sysctl falla en el kernel 7.0: kernel.nmi_watchdog = 1 devuelve error 524 y el vigilante de bloqueos duros queda apagado"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-30
close_check: {"cmd": "systemctl is-active --quiet systemd-sysctl.service", "expect": "exit_zero", "porque": "Falla hoy: la unidad quedo en failed tras el arranque en el kernel 7.0.0-1024. Pasa cuando el sysctl se aplica sin error en el arranque."}
---

## Que se midio (2026-10-30, primer arranque en 7.0.0-1024-nvidia)

`journalctl -b -u systemd-sysctl`: `Couldn't write '1' to 'kernel/nmi_watchdog': Unknown error 524` y la unidad termina `failed`.
La linea sale de `/etc/sysctl.d/99-freeze-panic.conf` (copia adoptada en `adopted/system-config/etc_sysctl.d_99-freeze-panic.conf`).
Valores aplicados despues: `softlockup_panic=1`, `hung_task_panic=1`, `hardlockup_panic=1`, `panic=10`; `nmi_watchdog=0`.

## Por que importa

Esa red existe para convertir un congelamiento en un panic con rastro en pstore. Con `nmi_watchdog=0` en el 7.0, `hardlockup_panic=1` queda puesto
pero el detector que lo dispararia esta apagado: un bloqueo duro ya no produce panic. `hung_task` y `softlockup` siguen activos.
Ademas una unidad `failed` en cada arranque oculta la siguiente falla real de sysctl (instrumento ciego).

## Por hacer

1. Medir si el 7.0 ofrece otro mecanismo para el bloqueo duro (`/proc/sys/kernel/watchdog`, `watchdog_thresh`, detector "buddy"): leer el valor, no suponerlo.
2. Cambiar la linea o moverla para que el arranque no falle, y dejar en la copia adoptada el motivo y el kernel desde el que aplica.
3. Si el bloqueo duro queda sin detector, declararlo en SPEC.md y en el tablero de la red de congelamiento.
