---
id: DEBT-RUFF-ATOM-GPU-TELEMETRY-01
kind: task
domain: VERDICT
title: "Resolver infracciones Ruff en atom_gpu_telemetry.py"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m ruff check tools/atom_gpu_telemetry.py", "expect": "exit_zero", "porque": "Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Defecto confirmado.

## Evidencia y alcance

Comando medido: `python3 -m ruff check tools tests --output-format=json`. 5 infracciones en este archivo:

- Línea 1396: C901 — `mitigar` is too complex (17 > 10)
- Línea 1396: PLR0913 — Too many arguments in function definition (6 > 5)
- Línea 1396: PLR0912 — Too many branches (17 > 12)
- Línea 1396: PLR0915 — Too many statements (64 > 50)
- Línea 1582: C901 — `main` is too complex (12 > 10)

Fuentes: tools/atom_gpu_telemetry.py.

## Criterio de cierre y control negativo

Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar.

## Estado del verificador

La ficha permanece abierta. El comando ya existe; se conserva el fallo actual y falta resolver el sujeto.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
