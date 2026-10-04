---
id: DEBT-CLOSE-CHECK-VERIFY-NETCONSOLE-01
kind: task
domain: VERDICT
title: "Implementar criterios ejecutables de tools.verify_netconsole"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_close_check_verify_netconsole_01", "expect": "exit_zero", "porque": "Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Módulo ausente citado por 1 fichas. Esta ficha agrupa la implementación compartida; las investigaciones originales conservan sus ensayos y no se duplican.

- tasks/backlog/FEATURE-FORUM-NETCONSOLE-01.md

Fuentes: tasks/backlog/FEATURE-FORUM-NETCONSOLE-01.md.

## Criterio de cierre y control negativo

Cada fase/id soportado evalúa su sujeto específico con capturas reales y controles negativos. Rechazar evidencia ausente, incorrecta, incompleta o controles neutralizados. Separar fail de could_not_run e imprimir ceros. No cerrar investigaciones por existencia de un informe ni por fixtures sanos. Compartir solo lógica realmente común; conservar comandos literales y demostrar discriminación entre fichas.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Avance de ejecución 2026-10-03

Se desarrolló `tools.kernel_capture` como captura readonly de identidad kernel, presencia de `netconsole=` y configuración de parámetros estáticos/targets configfs. El instrumento guarda hash de los valores de endpoint, no direcciones; distingue módulo ausente de acceso denegado, y siempre marca entrega al receptor como no observada. 12 pruebas focales y 100 % de sentencias/ramas del módulo nuevo; el selector específico de cierre sigue pendiente y esta captura no satisface la prueba de entrega exigida.

Evidencia: `docs/evidence/BB-INSTRUMENTS-kernel.md` y `tasks/evidence/BB-INSTRUMENTS-2026-10-03/kernel-capture.json`. La ficha permanece abierta.

## Propuesta de lector offline 2026-10-03 — pendiente de revisión raíz

Se añadió `tools.netconsole_marker` como lector mínimo de un log de receptor y un marcador literal indicados por el operador. Clasifica `present`, `incomplete` (prefijo literal al final del log), `absent` y `unknown` (archivo ilegible); la procedencia de log y marcador queda `caller_supplied_unverified` y la salida conserva `closure: open`. El control positivo usa un fixture de test, no evidencia del host. No se ejecutó contra un log real del receptor.

Comandos de validación: `python3 -m pytest -q tests/test_netconsole_marker.py` → `3 passed`; `python3 -m ruff check tools/netconsole_marker.py tests/test_netconsole_marker.py` → `All checks passed!`; `python3 -m pyright tools/netconsole_marker.py tests/test_netconsole_marker.py` → `0 errors, 0 warnings, 0 informations`.

El lector sólo cubre clasificación textual. El close check de esta ficha sigue pendiente: falta integrar controles negativos de ruta/receptor, estado de Secure Boot y firma, persistencia, correlación y rollback, todos respaldados por evidencia real. Se deja esta instrumentación para revisión raíz; no equivale a entrega off-host ni cierra la investigación.

Revisión raíz: el lector se nombra `netconsole_marker` para separar su alcance del verificador completo ausente. Lee hasta 1 MiB y admite marcadores de 1..1024 caracteres; entradas mayores quedan unknown/could_not_run. Conserva hashes exactos de captura y marcador sin imprimir el contenido. Los controles ampliados CLI/UTF-8/límites/hash pasan: `7 passed in 0.04s`. El cierre original y su interfaz --evidence siguen pendientes.
