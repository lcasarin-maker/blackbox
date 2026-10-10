---
id: DEBT-GUARDIA-PROCESO-MUERE-EN-SILENCIO-01
kind: task
domain: SYSTEMD
title: "La guardia de procesos muere por senal externa y nada la levanta ni lo avisa"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-10
close_check: {"cmd": "grep -q Restart=always systemd/bb-guardia-proceso.service", "expect": "exit_zero", "porque": "Con Restart=on-failure una senal TERM externa cuenta como salida limpia y systemd no la levanta; la politica debe cubrir ese caso, y la prueba de reinicio debe cambiar a la par."}
---

## Medido (2026-10-10, journal de la unit de usuario desde 2026-09-28)

`bb-guardia-proceso` estuvo parada del 09-oct 05:28:17 al 10-oct 07:00:42, 25 h 32 min, sin que nada lo dijera. `bb-parada-diagnostico` si registro la parada en `paradas.log` (`exit_status=TERM service_result=success`), pero ningun instrumento lee ese archivo.

No es la primera vez. Los arranques que no coinciden con un boot son rastros de reinicios manuales: 2026-09-29 14:35 y 15:01, 2026-10-03 22:09, 2026-10-06 01:58 y 09:35, y el de hoy. El SPEC llego a registrar `enabled, inactive` el 2026-10-03 sin que eso disparara nada. El 2026-10-06 03:08 murio por KILL y esa vez si la levanto systemd (`Scheduled restart job`).

## Causa probable, sin probar

systemd cuenta SIGTERM como salida limpia por defecto, y `Restart=on-failure` no reinicia tras una salida limpia: una TERM externa mata a la guardia y se queda muerta. La ficha cerrada `DEBT-GUARDIA-PROCESO-REINICIO-NO-LIMPIO-01` configuro justo `on-failure` y su prueba lo fija.

Quien envio la TERM no se sabe: el anillo de audit desbordaba (ver `DEBT-AUDIT-ANILLO-DESBORDADO-SIN-LIMITE-01`) y no guardo al emisor.

## Ya hecho

`bb status` tiene desde 2026-10-10 la fila "guardia de procesos (frena un proceso desbocado)", con su control negativo. Faltan dos cosas: cambiar la politica a `Restart=always` (y la prueba `tests/test_guardia_proceso_reinicio.py`) y averiguar quien manda la TERM.
