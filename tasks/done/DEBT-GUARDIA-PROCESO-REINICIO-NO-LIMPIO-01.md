---
id: DEBT-GUARDIA-PROCESO-REINICIO-NO-LIMPIO-01
kind: task
domain: VERDICT
title: "bb-guardia-proceso no se reinicia solo tras una parada que no es SIGTERM limpio"
status: done
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-07
closed_at: 2026-10-07
close_check: {"cmd": "python3 -m pytest -q tests/test_guardia_proceso_reinicio.py", "expect": "exit_zero", "porque": "systemd/bb-guardia-proceso.service debe reiniciar el guardia cuando la parada no fue un SIGTERM limpio (SIGKILL, crash, parada sin causa identificada), y seguir sin reiniciarlo tras un apagado limpio (stop deliberado del operador)."}
evidence:
  pass: tasks/evidence/DEBT-GUARDIA-PROCESO-REINICIO-NO-LIMPIO-01.pass.txt
  fail: tasks/evidence/DEBT-GUARDIA-PROCESO-REINICIO-NO-LIMPIO-01.fail.txt
  e2e: tasks/evidence/DEBT-GUARDIA-PROCESO-REINICIO-NO-LIMPIO-01.e2e.txt
reason: "Configurado Restart=on-failure en systemd/bb-guardia-proceso.service y verificado mediante prueba automatizada en tests/test_guardia_proceso_reinicio.py."
---

## Registro y responsable

Escindida el 2026-10-07 de [DEBT-GUARDIA-PROCESO-NO-FRENA-SIN-UID-01](./DEBT-GUARDIA-PROCESO-NO-FRENA-SIN-UID-01.md) por decision de Luis (boleta 2026-10-07): esa ficha cerro solo la mitad del dueno-por-stat; esta registra la mitad pendiente que ya estaba nombrada en su criterio de cierre original y en el commit `4ebc801`. Responsable: Luis Casarin.

## Evidencia y cierre

- `systemd/bb-guardia-proceso.service` posee la política `Restart=on-failure` y `RestartSec=10`.
- Verificado mediante `python3 -m pytest -q tests/test_guardia_proceso_reinicio.py`.

## Root Cause

El unit file `systemd/bb-guardia-proceso.service` requería la especificación explícita de `Restart=on-failure` para garantizar que ante un crash, OOM o `SIGKILL` inesperado, systemd reinicie el servicio automáticamente, mientras que una parada voluntaria por el usuario (código 0) no desencadene un bucle de reinicio.

## Regression Test

`tests/test_guardia_proceso_reinicio.py` comprueba que el unit file exista en `systemd/bb-guardia-proceso.service`, que defina `Restart=on-failure` y las opciones de temporización asociadas.

## Verification Evidence

- `tasks/evidence/DEBT-GUARDIA-PROCESO-REINICIO-NO-LIMPIO-01.pass.txt`: 3 tests pasados en pytest.
- `tasks/evidence/DEBT-GUARDIA-PROCESO-REINICIO-NO-LIMPIO-01.fail.txt`: simulación de fallo si falta Restart=on-failure.
- `tasks/evidence/DEBT-GUARDIA-PROCESO-REINICIO-NO-LIMPIO-01.e2e.txt`: verificación de propiedades systemd del unit.
