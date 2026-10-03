---
id: DEBT-RUFF-SCAN-SAMPLES-01
kind: task
domain: VERDICT
title: "Resolver infracciones Ruff en scan_samples.py"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m ruff check tools/scan_samples.py", "expect": "exit_zero", "porque": "Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Defecto confirmado.

## Evidencia y alcance

Comando medido: `python3 -m ruff check tools tests --output-format=json`. 6 infracciones en este archivo:

- Línea 39: C901 — `asociar_cpu_gpu` is too complex (17 > 10)
- Línea 39: PLR0912 — Too many branches (18 > 12)
- Línea 39: PLR0915 — Too many statements (57 > 50)
- Línea 112: C901 — `preparar` is too complex (29 > 10)
- Línea 112: PLR0912 — Too many branches (30 > 12)
- Línea 112: PLR0915 — Too many statements (68 > 50)

Fuentes: tools/scan_samples.py.

## Criterio de cierre y control negativo

Ruff del archivo retorna cero con las reglas actuales y las pruebas del sujeto pasan. Reducir complejidad sin debilitar validación, seguridad ni controles negativos. No silenciar reglas ni añadir noqa para conseguir verde. Control negativo: variante temporal que exceda la regla vuelve a fallar.

## Estado del verificador

La ficha permanece abierta. El comando ya existe; se conserva el fallo actual y falta resolver el sujeto.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
