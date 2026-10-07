---
id: DEBT-GUARDIA-PROCESO-NO-FRENA-SIN-UID-01
kind: task
domain: VERDICT
title: "bb-guardia-proceso se niega a frenar cuando no puede leer el dueno del proceso"
status: done
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-06
closed_at: 2026-10-07
closure_type: relocated_prior_verification
reason: "El fix (resolver el dueno por stat cuando /proc/<pid>/status no es legible) y sus 12 pruebas ya estaban commiteados desde el 2026-10-06 en 4ebc801; esta ficha solo mueve el archivo y agrega la evidencia/secciones de cierre. Decision de Luis (2026-10-07, boleta): cerrar la mitad hecha y abrir DEBT-GUARDIA-PROCESO-REINICIO-NO-LIMPIO-01 para la segunda mitad del criterio original (reinicio automatico tras parada que no sea SIGTERM limpio), que vive en systemd y no se toco aqui."
evidence:
  fail: tasks/evidence/DEBT-GUARDIA-PROCESO-NO-FRENA-SIN-UID-01.fail.txt
  pass: tasks/evidence/DEBT-GUARDIA-PROCESO-NO-FRENA-SIN-UID-01.pass.txt
  e2e: tasks/evidence/DEBT-GUARDIA-PROCESO-NO-FRENA-SIN-UID-01.e2e.txt
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

Con status ilegible y dueno legible por otra via, el guardia puede frenar a un proceso del mismo usuario. Sigue negandose con root y pid 1. La prueba pasa sin xfail. **Alcance recortado el 2026-10-07 (decision de Luis):** esta ficha cierra solo esta mitad; el reinicio automatico ante paradas distintas de SIGTERM limpio queda registrado aparte en [DEBT-GUARDIA-PROCESO-REINICIO-NO-LIMPIO-01](./DEBT-GUARDIA-PROCESO-REINICIO-NO-LIMPIO-01.md).

## Estado

Cerrada el 2026-10-07. La parte del UID se commiteo el 2026-10-06 en `4ebc801` (sin que esta ficha se moviera a `done/` en ese momento):

- `_es_intocable`: si `_uid_de` da None, el dueno sale de `os.stat("/proc/<pid>").st_uid` (`_uid_por_stat`). Por esa via solo se acepta uid 0 (sigue en "root") o el uid del guardian; otro usuario se rechaza (kill daria EPERM, y `_enviar_senal` solo atrapa ProcessLookupError). Sin status y sin stat sigue "no se toca".
- La prueba de cierre fallaba por su cargador, no por el guardia: sin registrar el modulo en `sys.modules`, `@dataclass` revienta con AttributeError al importar. Su version de HEAD falla igual con el arreglo aplicado. Cargador corregido; entrada quitada de tests/known_failures.json.
- Controles negativos en tests/test_guardia_proceso_uid.py (12 pruebas): root con y sin status (incluye pid 2 real), PID 1, el propio guardian, pid > pid_max sin mocks, otro usuario por stat. Seis mutantes de la funcion (respaldo neutralizado, respaldo permisivo, sin chequeo de otro usuario, de root, de PID 1, y el archivo de HEAD) hacen fallar al menos una prueba cada uno.
- La segunda mitad (reinicio automatico ante paradas distintas de SIGTERM limpio, en systemd/bb-guardia-proceso.service) no se toco aqui; vive en DEBT-GUARDIA-PROCESO-REINICIO-NO-LIMPIO-01. El caso real con status ilegible no se reprodujo en la maquina; su causa del 2026-09-28 sigue sin probar.

## Root Cause

`_es_intocable` (bin/bb-guardia-proceso) solo leia el dueno de `/proc/<pid>/status`; si esa lectura fallaba, se negaba a actuar por precaucion ("no se pudo leer ... no se toca"), aunque el proceso fuera del mismo usuario que corre el guardia. El journal del 2026-09-28 muestra esa negativa repetida sobre un proceso de 34 GiB de RSS que el guardia nunca freno.

## Regression Test

`tests/test_guardia_proceso_uid.py` (12 pruebas): reproduce el caso real (status ilegible, dueno resuelto por `stat` del mismo usuario -> se toca) y sus negativos (root con y sin status, PID 1, pid inexistente, otro usuario por stat -> ninguno se toca). Seis mutantes de `_uid_por_stat`/`_es_intocable` (respaldo neutralizado o permisivo, sin chequeo de root/PID 1/otro usuario) hacen fallar al menos una prueba cada uno.

## Verification Evidence

`tasks/evidence/DEBT-GUARDIA-PROCESO-NO-FRENA-SIN-UID-01.fail.txt`: las mismas 12 pruebas contra `bin/bb-guardia-proceso` en el commit `d188581` (antes del arreglo) -- 9 failed, 3 passed (AttributeError: no existe `_uid_por_stat`). `.pass.txt`: 12 passed contra HEAD. `.e2e.txt`: las dos pruebas que mandan una senal real a un proceso hijo real del mismo usuario -- 2 passed.
