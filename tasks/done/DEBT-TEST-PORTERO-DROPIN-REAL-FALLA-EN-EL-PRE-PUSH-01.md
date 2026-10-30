---
id: DEBT-TEST-PORTERO-DROPIN-REAL-FALLA-EN-EL-PRE-PUSH-01
kind: task
domain: MEMORY
title: "test_real_dropin_por_prefijo_topa_el_scope_al_crearse_y_no_a_otro falla en el pre-push y pasa suelto: carrera con systemd real"
status: done
closed_at: 2026-10-30
closure_type: fixed
reason: "Causa medida: el runner del pre-push fija HOME=/tmp/.tmpXXXX y el drop-in iba a ~/.config del HOME temporal; la prueba usa ahora $XDG_RUNTIME_DIR/systemd/user. El test viejo con HOME temporal da rc=1, el nuevo rc=0; el push 465123ae..752012bc paso los gates tras 3 fallos identicos."
evidence: {"pass": "tasks/evidence/DEBT-TEST-PORTERO-DROPIN-REAL-FALLA-EN-EL-PRE-PUSH-01/pass.txt", "fail": "tasks/evidence/DEBT-TEST-PORTERO-DROPIN-REAL-FALLA-EN-EL-PRE-PUSH-01/fail.txt", "e2e": "tasks/evidence/DEBT-TEST-PORTERO-DROPIN-REAL-FALLA-EN-EL-PRE-PUSH-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-30
close_check: {"cmd": "HOME=$(mktemp -d) PYTHONUSERBASE=/home/lcasarin/.local python3 -m pytest -q -p no:cacheprovider tests/test_portero.py::test_real_dropin_por_prefijo_topa_el_scope_al_crearse_y_no_a_otro", "expect": "exit_zero", "porque": "Enmienda 2026-10-30 con la causa MEDIDA: el runner del pre-push corre con HOME en un directorio temporal y la prueba escribia su drop-in en Path.home()/.config/systemd/user, que el gestor real no lee. El comando original (grep de un centinela) se sustituye por el que reproduce la condicion del gate: con HOME temporal el test viejo da rc=1 y el nuevo rc=0 (evidencia en fail.txt y pass.txt)."}
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

## Cierre 2026-10-30 (/clean): la hipotesis de arriba estaba equivocada

- **Causa real (medida):** `HOME=/tmp/.tmpXXXX` bajo el runner del pre-push. `Path.home()` apuntaba al directorio temporal, el drop-in nunca llego al gestor real y el scope nacia sin tope. Se midio instrumentando la asercion en un commit desechable (`bcca7d3e`, rama ya borrada) y corriendo `simple verify --hook pre-push`.
- **Refutado:** la carrera con el job post-commit. El tercer push fallo igual sin ningun job de bb en curso.
- **Arreglo:** `tests/test_portero.py` usa `$XDG_RUNTIME_DIR/systemd/user` (en la ruta de busqueda de `systemd-analyze --user unit-paths`) y se salta sin `XDG_RUNTIME_DIR`. El marcador `mutates_real_source` se conserva porque la prueba sigue recargando el gestor real; su comentario `ponytail:` dice ese motivo.
- **Por que paso desapercibido:** la prueba pasaba en cualquier shell con HOME real (3 de 3 sueltas, 67 en serie, 145 con xdist).
