---
id: DEBT-CLOSE-CHECK-VERIFY-MEMORY-SAVER-01
kind: task
domain: VERDICT
title: "Implementar criterios ejecutables de tools.verify_memory_saver"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_close_check_verify_memory_saver_01", "expect": "exit_zero", "porque": "Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

El módulo citado por 2 fichas ya está implementado; su presencia acredita disponibilidad, mientras el cierre exige capturas reales. Esta ficha agrupa la implementación compartida; las investigaciones originales conservan sus ensayos y no se duplican.

- tasks/backlog/FEATURE-MEMORYSAVER-02-TRAZADOR.md
- tasks/backlog/FEATURE-MEMORYSAVER-04-PACKING-4K.md

Fuentes: tasks/backlog/FEATURE-MEMORYSAVER-02-TRAZADOR.md, tasks/backlog/FEATURE-MEMORYSAVER-04-PACKING-4K.md.

## Criterio de cierre y control negativo

Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas.

## Estado del verificador

La ficha permanece abierta. El selector original ya existe y ejecuta ambas fases. Resultado actual: 0 PASS, 0 FAIL, 2 UNKNOWN y 2 could_not_run por captura ausente. El lector seguro y sus negativos pasan con la suite focal (92 pruebas); la evidencia experimental sigue pendiente. Recibo: tasks/evidence/CLOSURE-CONTROLS-2026-10-03/memory-original-selector-primary-run.json.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `privileged_access`.
- Impedimento: Selector ya implementado; recibo registra 0 PASS, 0 FAIL, 2 UNKNOWN, 2 could_not_run por captura ausente. Evidencia experimental runtime/cuda requiere bpftrace root y probes accesibles.
- Evidencia faltante para cierre: Selector ya implementado; recibo registra 0 PASS, 0 FAIL, 2 UNKNOWN, 2 could_not_run por captura ausente. Evidencia experimental runtime/cuda requiere bpftrace root y probes accesibles.
- Siguiente acción: Coordinación BB: preservar/verificar el recibo y especificar schema; operador Luis: aportar captura autorizada de runtime/probes sin alterar el host. Ref explícita: tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-MEMORY-SAVER-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-MEMORY-SAVER-01.md y tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_03.json.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-MEMORY-SAVER-01.md`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/memory-original-selector-primary-run.json`, `tasks/evidence/FEATURE-MEMORYSAVER-02-TRAZADOR/abi-check.txt`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_03.json`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
