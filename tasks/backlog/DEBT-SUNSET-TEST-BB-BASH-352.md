---
id: DEBT-SUNSET-TEST-BB-BASH-352
kind: task
domain: VERDICT
title: "Revisar sunset en test_bb_bash.py:352"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_sunset_test_bb_bash_352", "expect": "exit_zero", "porque": "Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Sitio: `tests/test_bb_bash.py:352`; función/contexto: test_bb_bash.

```text
time.sleep(2)  # blocking-sleep: dt de bin/bb tiene resolucion de SEGUNDO ENTERO (`date +%s`) -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 2.1 -- relectura 2026-10-02: objetivo y expresion sin cambios frente a git show 7049dce^:tests/test_bb_bash.py; Las razones de delta entero y sondeo con deadline que siguen conservan su sujeto. Comparacion por linea en tasks/evidence/RELEASE-2.1.0/sunset-review.json. Revision anterior 2.0: sin cambios desde la revision de 1.9 horas antes, mismo dia, mismas evidencias -- SE QUEDA, y con razon MAS FUERTE que antes: instrumentado bin/bb directamente el 2026-09-28 (`dt=$(( ahora_s - antes_s ))` en la seccion de swap/cputop), sleep(0) dio dt=0 en 3 de 6 corridas -- exactamente esos 3 saltan el bloque `[ "$dt" -gt 0 ]` entero y dejan swpin_s/swpout_s en su default 0 SIN pasar por el clamp `(v>0?v:0)` que el test dice verificar. O sea que sin la espera, la mitad de las corridas pasarian por el camino EQUIVOCADO -- vacuamente, no por el mecanismo. Ya no es "argumento estructural solo": es una puerta de tiempo medida y su fallo reproducido. Evidencia: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/dt-resolucion-entera-2026-09-28.txt
```

Clasificación: revisión de una exclusión/captura, no bug demostrado. No retirar automáticamente una protección o cleanup.

Fuentes: tests/test_bb_bash.py:352.

## Criterio de cierre y control negativo

Revalidar la justificación y el alcance exacto de la excepción sunset antes de su vencimiento, con comando literal y control negativo. Si es pausa de arnés/sampler, medir timeout/bounded scope/cancelación; si es test, conservar sensibilidad al delta observado. Retirar la excepción innecesaria o registrar revisión válida con responsable y expiración concreta, sin suspensión permanente.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
