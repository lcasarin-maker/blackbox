---
id: DEBT-CLOSE-CHECK-VERIFY-NETCONSOLE-01
kind: task
domain: VERDICT
title: "Implementar criterios ejecutables de tools.verify_netconsole"
status: done
closed_at: 2026-10-14
closure_type: duplicate
reason: "Duplicada de su(s) ficha(s) sujeto FEATURE-FORUM-NETCONSOLE-01: pedia implementar los criterios ejecutables de tools.verify_netconsole, que ya existe y es el close_check de esas fichas; su propio close_check era un xfail de relleno. Decision de Luis 2026-10-14: consolidar; la medicion la lleva la ficha sujeto."
evidence: {"pass": "tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-NETCONSOLE-01/pass.txt", "fail": "tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-NETCONSOLE-01/fail.txt", "e2e": "tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-NETCONSOLE-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DEBT-CLOSE-CHECK-VERIFY-NETCONSOLE-01.md", "expect": "exit_zero", "porque": "Cerrada como duplicate (decision de Luis 2026-10-14: consolidar en la ficha sujeto): no hay fix propio que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior era `python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_close_check_verify_netconsole_01`, un xfail de relleno que se retira con el cierre; los criterios ejecutables los mide el close_check de la ficha sujeto."}
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

## Lector offline 2026-10-03 — revisión raíz integrada

Se añadió `tools.netconsole_marker` como lector mínimo de un log de receptor y un marcador literal indicados por el operador. Clasifica `present`, `incomplete` (prefijo literal al final del log), `absent` y `unknown` (archivo ilegible); la procedencia de log y marcador queda `caller_supplied_unverified` y la salida conserva `closure: open`. El control positivo usa un fixture de test, no evidencia del host. No se ejecutó contra un log real del receptor.

Comandos de validación: `python3 -m pytest -q tests/test_netconsole_marker.py` → `3 passed`; `python3 -m ruff check tools/netconsole_marker.py tests/test_netconsole_marker.py` → `All checks passed!`; `python3 -m pyright tools/netconsole_marker.py tests/test_netconsole_marker.py` → `0 errors, 0 warnings, 0 informations`.

El lector sólo cubre clasificación textual. El close check de esta ficha sigue pendiente: falta integrar controles negativos de ruta/receptor, estado de Secure Boot y firma, persistencia, correlación y rollback, todos respaldados por evidencia real. La revisión raíz se registra a continuación; el lector conserva alcance textual y la investigación abierta.

Revisión raíz: el lector se nombra `netconsole_marker` para separar su alcance del verificador completo ausente. Lee hasta 1 MiB y admite marcadores de 1..1024 caracteres; entradas mayores quedan unknown/could_not_run. Conserva hashes exactos de captura y marcador sin imprimir el contenido. Los controles ampliados CLI/UTF-8/límites/hash pasan: `7 passed in 0.04s`. El cierre original y su interfaz --evidence siguen pendientes.

Resultado final del lector: ocho pruebas, incluidas CLI/entrypoint y recibo sin contenido. La suite completa pasa 1118 pruebas con 5060/5060 sentencias Python; ver `docs/evidence/SWARM-TENS-2026-10-03.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: El selector existe; la captura kernel actual marca explícitamente que la entrega al receptor no fue observada.
- Evidencia faltante para cierre: Prueba focal por configuración estática/target y receptor real; control negativo; salida literal del selector.
- Siguiente acción: Con el operador, ejecutar una captura de entrega netconsole hacia receptor de laboratorio y registrar el mensaje recibido, control negativo y configuración/rollback; conservar el selector focal existente.
- Responsable del siguiente paso: BB.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DEBT-CLOSE-CHECK-VERIFY-NETCONSOLE-01.md`, `tools/kernel_capture.py`, `docs/evidence/BB-INSTRUMENTS-kernel.md`, `tasks/evidence/BB-INSTRUMENTS-2026-10-03/kernel-capture.json`, `tests/test_debt_registration_controls.py`, `tests/test_closure_kernel_selectors.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: media · lectura: completa.

tools/kernel_capture.py y tools/netconsole_marker.py ya existen; falta la entrega real al receptor (el selector termina en xfail, decision del dueno 2026-10-11: dejarla abierta). En un solo nodo con red r8127 por cable es viable con un receptor UDP en otro equipo de la LAN; la utilidad es captar el ultimo log de un cuelgue duro sin pstore.

Version para un solo nodo Gigabyte AI TOP ATOM: Prueba de entrega netconsole del nodo a un receptor de laboratorio en la misma LAN (cable r8127), con marcador literal, control negativo (receptor apagado) y rollback de la configuracion configfs; sin cluster.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Root Cause
Meta-ficha sin sujeto propio: pedia implementar los criterios ejecutables de `tools.verify_netconsole`. El verificador existe (`tools/verify_netconsole.py`) y es el close_check de `FEATURE-FORUM-NETCONSOLE-01`; hoy sale con rc=2 (could_not_run) porque falta la captura real del sujeto, que es el trabajo de esas fichas, no de esta. Su propio close_check era un selector xfail que no podia cerrar nada.

## Regression Test
Ninguno propio: la ficha se cierra como duplicada. Se retira `tests/test_debt_registration_controls.py::test_debt_close_check_verify_netconsole_01`, xfail de relleno, junto con sus entradas de `tests/known_failures.json` y el selector `tests/test_closure_kernel_selectors.py::closure_selector_netconsole_01` (y `open_closures`), que solo usaba ese test; las pruebas unitarias de `tools.verify_netconsole` siguen corriendo.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: el close_check de cada ficha sujeto sale hoy con rc distinto de 0, el verificador sabe decir que no), `pass` (el verificador existe, cada ficha sujeto lo nombra y sus pruebas unitarias pasan: control positivo) y `e2e` (la decision registrada). Cada ficha sujeto lleva una nota que dice que los criterios de `tools.verify_netconsole` se miden alli. Para reabrirla: `git mv tasks/done/DEBT-CLOSE-CHECK-VERIFY-NETCONSOLE-01.md tasks/backlog/` y `status: open`.
