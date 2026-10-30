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

## Correccion 2026-10-30 (despues de sondear en vivo): no es una regresion de proteccion

`echo 1 | sudo tee /proc/sys/kernel/nmi_watchdog` en vivo: el mismo error 524, asi que no es de orden de arranque.
`journalctl -k` del 6.17 (arranque del 27-oct) y del 7.0 traen las mismas dos lineas: `watchdog: NMI not fully supported` y
`watchdog: Hard watchdog permanently disabled`. Los dos kernels tienen la misma configuracion (`HARDLOCKUP_DETECTOR_PERF=y`, `ARM64_PSEUDO_NMI=y`) y la linea de
comandos no trae opcion de NMI. Conclusion: el detector de bloqueo duro NUNCA estuvo activo aqui; `hardlockup_panic=1` siempre fue letra muerta. Lo nuevo en el 7.0
es solo que la escritura devuelve error y deja `systemd-sysctl` en `failed`. `hung_task` y `softlockup` si estan activos (`softlockup_panic=1`, `hung_task_panic=1`).

## Por hacer

1. HECHO en el repo: la copia adoptada marca la linea con `-` (systemd ignora el fallo de esa escritura, `man sysctl.d`) y explica el motivo en un comentario.
2. Instalar la copia en `/etc/sysctl.d/` (lo hace Luis con sudo, sin reiniciar) y reiniciar la unidad; `close_check` pasa cuando la unidad queda `active`.
3. Declarar en SPEC.md, con una fila NUEVA (las existentes no se editan), que el bloqueo duro no tiene detector: la fila de `99-freeze-panic` dice que el kernel entra en panic ante hardlockup, y es falso.
4. Opcional y aparte (ficha nueva si se quiere): probar `irqchip.gicv3_pseudo_nmi=1` en la linea de comandos para tener un detector real. Cambia el manejo de interrupciones
   de toda la maquina y pide un reinicio propio; no se mezcla con el reinicio de la Fase 2.
