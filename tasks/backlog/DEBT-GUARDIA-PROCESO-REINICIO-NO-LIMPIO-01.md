---
id: DEBT-GUARDIA-PROCESO-REINICIO-NO-LIMPIO-01
kind: task
domain: VERDICT
title: "bb-guardia-proceso no se reinicia solo tras una parada que no es SIGTERM limpio"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-07
close_check: {"cmd": "python3 -m pytest -q tests/test_guardia_proceso_reinicio.py", "expect": "exit_zero", "porque": "systemd/bb-guardia-proceso.service debe reiniciar el guardia cuando la parada no fue un SIGTERM limpio (SIGKILL, crash, parada sin causa identificada), y seguir sin reiniciarlo tras un apagado limpio (stop deliberado del operador)."}
---

## Registro y responsable

Escindida el 2026-10-07 de [DEBT-GUARDIA-PROCESO-NO-FRENA-SIN-UID-01](./DEBT-GUARDIA-PROCESO-NO-FRENA-SIN-UID-01.md) por decision de Luis (boleta 2026-10-07): esa ficha cerro solo la mitad del dueno-por-stat; esta registra la mitad pendiente que ya estaba nombrada en su criterio de cierre original y en el commit `4ebc801`. Responsable: Luis Casarin.

## Evidencia y alcance

- Esta guardia existe porque el 2026-09-28 la maquina se reinicio dos veces por un solo proceso que crecio hasta mas de 30 GiB (ver DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES).
- Paradas de 2026-10-06 sin reinicio automatico: 03:08 SIGKILL a la guardia (el driver NVRM registro OOM de GPU 03:07:49-03:07:56); 03:34 SIGTERM sin causa identificada. Ninguna de las dos causas esta probada; ninguna disparo un reinicio.
- `systemd/bb-guardia-proceso.service` (o el unit adoptado equivalente) no trae hoy una politica de `Restart=` que distinga una parada limpia (stop deliberado, `SIGTERM` que el proceso atiende y termina rc=0) de una que no lo es (SIGKILL, crash, señal no atendida).
- Editar el unit systemd de este guardia toco antes el clasificador de permisos de Claude Code ("judged this action dangerous", sin explicacion) en una sesion previa; puede requerir que el usuario aplique el cambio de systemd el mismo, aunque el codigo/prueba se preparen en el repo.

## Criterio de cierre y control negativo

El guardia se reinicia solo cuando la parada NO fue un SIGTERM limpio (SIGKILL, OOM del propio guardia, crash, señal no atendida). Un stop deliberado del operador (systemctl stop, o el propio proceso saliendo rc=0 tras SIGTERM) NO dispara un reinicio. Control negativo: simular ambos casos (parada limpia vs sucia) y confirmar que el unit systemd distingue -- `systemctl --user show bb-guardia-proceso -p Restart,RestartForceExitStatus,SuccessExitStatus` mas una parada real de cada clase.

## Estado

Abierta. Nada de este cambio esta hecho; vive en configuracion de systemd (`ExecStopPost=`/`Restart=`), no en `bin/bb-guardia-proceso`. El caso real con status ilegible del 2026-09-28 tampoco se reprodujo en la maquina para probar su causa.
