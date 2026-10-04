---
id: DEBT-CLOSE-CHECK-VERIFY-GPU-CLOCK-CAP-AB-01
kind: task
domain: VERDICT
title: "Implementar criterios ejecutables de tools.verify_gpu_clock_cap_ab"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_close_check_verify_gpu_clock_cap_ab_01", "expect": "exit_zero", "porque": "Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Registro inicial: módulo ausente citado por 1 fichas. El módulo y el selector original ya están disponibles. Esta ficha agrupa la implementación compartida; las investigaciones originales conservan sus ensayos y no se duplican.

- tasks/backlog/FEATURE-FORUM-GPU-CLOCK-CAP-AB-01.md

Fuentes: tasks/backlog/FEATURE-FORUM-GPU-CLOCK-CAP-AB-01.md.

## Criterio de cierre y control negativo

Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas.

## Estado del verificador

La ficha permanece abierta. El selector original ya ejecuta el evaluador sobre la captura de su sujeto: status=unknown, fail=0, could_not_run=1. Motivo: raw timestamped GPU clock-cap command capture missing or malformed. Recibo: tasks/evidence/CLOSURE-CONTROLS-2026-10-03/three-hardware-original-selectors-primary-run.json. La cobertura del paquete permanece parcial; la investigación requiere evidencia real.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: El close_check es implementado y el selector actual usa el verificador existente; el recibo más reciente del 2026-10-04 devuelve status=unknown, fail=0, could_not_run=1 porque falta la captura cruda de comandos con timestamp del ensayo GPU. El sujeto no tiene A/B de clocks, soak, telemetría ni rollback.
- Evidencia faltante para cierre: captura nativa completa commands.json con plan predeclarado, identidad de host/driver/firmware, cap stock y capped, muestras telemetry/workload positivas y comparación; rollback medido
- Siguiente acción: Conservar UNKNOWN y el criterio abierto hasta que el operador prepare y ejecute el A/B físico en GPU canary con timestamps, workload, rollback y capturas crudas; después volver a correr el selector original.
- Responsable del siguiente paso: coordinación BB prepara el protocolo; operador Luis ejecuta el ensayo en GPU/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-GPU-CLOCK-CAP-AB-01.md`, `tools/verify_gpu_clock_cap_ab.py`, `tests/test_debt_registration_controls.py::test_debt_close_check_verify_gpu_clock_cap_ab_01`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/three-hardware-original-selectors-primary-run.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DEBT-CLOSE-CHECK-VERIFY-GPU-CLOCK-CAP-AB-01-current-selector.log`, `tasks/evidence/FEATURE-FORUM-GPU-CLOCK-CAP-AB-01/progress.txt`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
