---
id: DEBT-GUARDIA-PROCESO-MUERE-EN-SILENCIO-01
kind: task
domain: SYSTEMD
title: "La guardia de procesos muere por senal externa y nada la levanta ni lo avisa"
status: done
closed_at: 2026-10-13
closure_type: relocated_prior_verification
reason: "La unit usa Restart=always (una TERM externa ya no la deja muerta), esta desplegada y activa, y bb status tiene su fila. Control con unidades transitorias: Restart=on-failure queda inactive tras TERM y Restart=always se levanta con otro pid. La atribucion de quien envia la TERM sigue en DEBT-AUDIT-ANILLO-DESBORDADO-SIN-LIMITE-01 (el anillo de audit desborda y no guarda al emisor)."
evidence: {"pass": "tasks/evidence/DEBT-GUARDIA-PROCESO-MUERE-EN-SILENCIO-01/pass.txt", "fail": "tasks/evidence/DEBT-GUARDIA-PROCESO-MUERE-EN-SILENCIO-01/fail.txt", "e2e": "tasks/evidence/DEBT-GUARDIA-PROCESO-MUERE-EN-SILENCIO-01/e2e.txt"}
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

`bb status` tiene desde 2026-10-10 la fila "guardia de procesos (frena un proceso desbocado)", con su control negativo. La política de reinicio y su prueba ya están actualizadas. Sigue pendiente identificar quién envió la TERM y desplegar/verificar el archivo actualizado en el servicio vivo.

## Decision y avance (2026-10-10)

Luis priorizo reparar la politica de reinicio antes de investigar el emisor de SIGTERM. La unit usa ahora `Restart=always` y la prueba verifica esa politica; `systemctl stop` explicito conserva su excepcion nativa de systemd. La ficha sigue abierta: falta atribuir quien envio la TERM y desplegar/verificar la unit actualizada en el servicio vivo. No se reinicio el servicio como parte de esta decision.

## Root Cause
systemd cuenta SIGTERM como salida limpia y Restart=on-failure no reinicia tras salida limpia: una TERM externa dejo a la guardia muerta 25 h 32 min (09-oct 05:28 a 10-oct 07:00) sin que nada lo dijera.

## Regression Test
`tests/test_guardia_proceso_reinicio.py` (fija Restart=always) y la fila de `bb status` con su control negativo (`tests/test_bb_bash.py`).

## Verification Evidence
fail.txt: unidad transitoria con Restart=on-failure muere con TERM y queda inactive; pass.txt: con Restart=always systemd la levanta (pid nuevo) y el archivo desplegado es identico al del repo; e2e.txt: la guardia viva (Restart=always, active/running), su test y la fila de bb status. Pendiente fuera de esta ficha: atribuir al emisor de la TERM (DEBT-AUDIT-ANILLO-DESBORDADO-SIN-LIMITE-01).
