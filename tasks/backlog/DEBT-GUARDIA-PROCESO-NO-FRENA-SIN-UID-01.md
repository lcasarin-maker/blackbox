---
id: DEBT-GUARDIA-PROCESO-NO-FRENA-SIN-UID-01
kind: task
domain: VERDICT
title: "bb-guardia-proceso se niega a frenar cuando no puede leer el dueno del proceso"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-06
close_check: {"cmd": "python3 -m pytest -q tests/test_guardia_proceso_uid.py", "expect": "exit_zero", "porque": "El guardia debe poder frenar a un proceso del mismo usuario aunque /proc/<pid>/status no sea legible, resolviendo el dueno por otra via, y seguir negandose con root o con pid 1."}
---

## Registro y responsable

Registro del 2026-10-06 tras investigar las paradas de la guardia. Responsable: Luis Casarin. Esta guardia existe porque el 2026-09-28 la maquina se reinicio dos veces por un solo proceso que crecio hasta mas de 30 GiB (ver DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES).

## Evidencia y alcance

- bin/bb-guardia-proceso, funcion `_uid_de` (linea 150) y `_es_intocable` (linea 198): si `/proc/<pid>/status` no se puede leer, devuelve "no se pudo leer ... no se toca".
- Journal 2026-09-28: el guardia escribio varias veces `NO SE TOCA pid=320489 ... no se pudo leer /proc/<pid>/status/Uid` mientras ese proceso tenia 34 GiB de RSS: no lo freno.
- tests/test_guardia_proceso_uid.py reproduce la negativa (fallo hoy, marcado xfail).
- Paradas de 2026-10-06: 03:08 SIGKILL a la guardia (el driver NVRM registro OOM de GPU 03:07:49-03:07:56); 03:34 SIGTERM sin causa identificada. Ninguna de las dos causas esta probada.

## Criterio de cierre

Con status ilegible y dueno legible por otra via, el guardia puede frenar a un proceso del mismo usuario. Sigue negandose con root y pid 1. La prueba pasa sin xfail. Ademas, el reinicio automatico debe cubrir las paradas por causa distinta de SIGTERM limpio.

## Estado

Abierta. 2026-10-06, parte del uid hecha, sin commit (lo revisa Luis):

- `_es_intocable`: si `_uid_de` da None, el dueno sale de `os.stat("/proc/<pid>").st_uid` (`_uid_por_stat`). Por esa via solo se acepta uid 0 (sigue en "root") o el uid del guardian; otro usuario se rechaza (kill daria EPERM, y `_enviar_senal` solo atrapa ProcessLookupError). Sin status y sin stat sigue "no se toca".
- La prueba de cierre fallaba por su cargador, no por el guardia: sin registrar el modulo en `sys.modules`, `@dataclass` revienta con AttributeError al importar. Su version de HEAD falla igual con el arreglo aplicado. Cargador corregido; entrada quitada de tests/known_failures.json.
- Controles negativos en tests/test_guardia_proceso_uid.py (12 pruebas): root con y sin status (incluye pid 2 real), PID 1, el propio guardian, pid > pid_max sin mocks, otro usuario por stat. Seis mutantes de la funcion (respaldo neutralizado, respaldo permisivo, sin chequeo de otro usuario, de root, de PID 1, y el archivo de HEAD) hacen fallar al menos una prueba cada uno.
- Pendiente para cerrar: la segunda mitad del criterio (reinicio automatico ante paradas distintas de SIGTERM limpio) no esta tocada; vive en systemd/bb-guardia-proceso.service, fuera de este cambio. El caso real con status ilegible no se reprodujo en la maquina; su causa del 2026-09-28 sigue sin probar.
