---
id: DEBT-TEST-PORTERO-DROPIN-REAL-FALLA-EN-EL-PRE-PUSH-01
kind: task
domain: MEMORY
title: "test_real_dropin_por_prefijo_topa_el_scope_al_crearse_y_no_a_otro falla en el pre-push y pasa suelto: carrera con systemd real"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-30
close_check: {"cmd": "grep -qx dropin_real_estable_en_prepush tasks/evidence/DEBT-TEST-PORTERO-DROPIN-REAL-FALLA-EN-EL-PRE-PUSH-01/medicion.txt", "expect": "exit_zero", "porque": "Especificacion pendiente: el archivo no existe hoy (grep sale 2). El test pasa suelto (3 de 3), en serie (67 de 67) y con xdist -n 4, asi que un pytest sobre el no discrimina; lo que falla es el pre-push. Pasa cuando medicion.txt traiga, con comando y salida literales, 5 pre-push consecutivos en verde incluyendo uno inmediatamente despues de un commit (con el job post-commit en curso), y termine con la linea completa dropin_real_estable_en_prepush."}
---

## Medido (2026-10-30, sesion de /cerrar-deuda)

Dos `git push` consecutivos fallaron en el gate `pytest` del pre-push, por la misma prueba y el mismo mensaje:

```
tests/test_portero.py::test_real_dropin_por_prefijo_topa_el_scope_al_crearse_y_no_a_otro
assert ('max', '152777') == ('37580963840', '1230')
```

El scope desechable `app-bbprobe<tag>-1` se creo SIN el tope del drop-in (memory.max `max`, pids.max el valor por defecto 152777). El segundo intento fallo tambien en el carril serial (`-m mutates_real_source`), asi que no era una carrera con otras pruebas del mismo xdist.

Lo que si pasa: la prueba suelta 3 de 3; `tests/test_portero.py` completo en serie (67 passed); el grupo de portero con `-n 4` (145 passed); la etapa serial del gate corrida a mano con el mismo entorno minimo (`env -i`, solo `XDG_RUNTIME_DIR` y `DBUS_SESSION_BUS_ADDRESS` heredados): `rc=0`.

## Causa probable (NO medida)

Cada commit lanza un job post-commit en segundo plano que corre las mismas pruebas; ambos pushes ocurrieron minutos despues de un commit. Dos corridas con systemd real comparten `~/.config/systemd/user` y `systemctl --user daemon-reload`: un `daemon-reload` concurrente mientras la otra corrida crea su scope transitorio puede dejarlo sin el drop-in. Tambien hay otras sesiones de Claude en esta maquina haciendo pre-push al mismo tiempo (se vio un `run_when_quiet.sh` de otro proyecto).

## Lo que se intento y no resolvio la causa

Se marco la prueba `mutates_real_source` (carril serial) en `ba604567`. El marcador es coherente con el precedente de `DEBT-TEST-ESCALON-REAL-MATADO-POR-OTRO-PROCESO-01`, pero el segundo push fallo igual, asi que NO ataca esta causa.

## Para cerrar

1. Reproducir la carrera de forma controlada (dos corridas concurrentes con `daemon-reload` intercalado) para confirmar o descartar la causa.
2. Aislar la prueba: directorio de unidades propio (por ejemplo `systemd-run --user --scope` con un drop-in por `--property` en vez de escribir en `~/.config/systemd/user`) o un flock compartido entre corridas.
3. Medir 5 pre-push consecutivos en verde, uno justo tras un commit.

Mientras esta ficha este abierta, `/clean` puede encontrar el push bloqueado por esta prueba: no se reintenta a ciegas.
