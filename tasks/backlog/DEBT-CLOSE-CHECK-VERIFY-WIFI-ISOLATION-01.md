---
id: DEBT-CLOSE-CHECK-VERIFY-WIFI-ISOLATION-01
kind: task
domain: VERDICT
title: "Implementar criterios ejecutables de tools.verify_wifi_isolation"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_close_check_verify_wifi_isolation_01", "expect": "exit_zero", "porque": "Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Registro inicial: módulo ausente citado por 1 fichas. El módulo y el selector original ya están disponibles. Esta ficha agrupa la implementación compartida; las investigaciones originales conservan sus ensayos y no se duplican.

- tasks/backlog/FEATURE-FORUM-WIFI-ISOLATION-01.md

Fuentes: tasks/backlog/FEATURE-FORUM-WIFI-ISOLATION-01.md.

## Criterio de cierre y control negativo

Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas.

## Estado del verificador

La ficha permanece abierta. El selector original ya ejecuta el evaluador sobre la captura de su sujeto: status=unknown, fail=0, could_not_run=1. Motivo: raw command capture missing or malformed; current snapshot cannot prove a roam sequence. Recibo: tasks/evidence/CLOSURE-CONTROLS-2026-10-03/three-hardware-original-selectors-primary-run.json. La cobertura del paquete permanece parcial; la investigación requiere evidencia real.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: El selector existe; el recibo disponible declara captura cruda de comando ausente/malformada y no acredita una secuencia roam.
- Evidencia faltante para cierre: Captura raw de identidad/asociación/rutas/DNS/conectividad positiva y aislamiento negativo/rollback; selector focal passing.
- Siguiente acción: Solicitar al operador una secuencia roam con interfaz/AP identificados, asociación/ruta/DNS/conectividad e intento aislado negativo; correr el selector Wi-Fi existente sobre el recibo crudo.
- Responsable del siguiente paso: BB.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-WIFI-ISOLATION-01.md`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/three-hardware-original-selectors-primary-run.json`, `tools/verify_wifi_isolation.py`, `tests/test_debt_registration_controls.py`, `tools/hardware_evidence.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
