---
id: DEBT-CLOSE-CHECK-VERIFY-WIFI-ISOLATION-01
kind: task
domain: VERDICT
title: "Implementar criterios ejecutables de tools.verify_wifi_isolation"
status: done
closed_at: 2026-10-14
closure_type: duplicate
reason: "Duplicada de su(s) ficha(s) sujeto FEATURE-FORUM-WIFI-ISOLATION-01: pedia implementar los criterios ejecutables de tools.verify_wifi_isolation, que ya existe y es el close_check de esas fichas; su propio close_check era un xfail de relleno. Decision de Luis 2026-10-14: consolidar; la medicion la lleva la ficha sujeto."
evidence: {"pass": "tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-WIFI-ISOLATION-01/pass.txt", "fail": "tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-WIFI-ISOLATION-01/fail.txt", "e2e": "tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-WIFI-ISOLATION-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DEBT-CLOSE-CHECK-VERIFY-WIFI-ISOLATION-01.md", "expect": "exit_zero", "porque": "Cerrada como duplicate (decision de Luis 2026-10-14: consolidar en la ficha sujeto): no hay fix propio que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior era `python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_close_check_verify_wifi_isolation_01`, un xfail de relleno que se retira con el cierre; los criterios ejecutables los mide el close_check de la ficha sujeto."}
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

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: aplica · utilidad: baja · lectura: completa.

El mt7925e wifi existe en este equipo, pero la ficha es un verificador (tools/verify_wifi_isolation.py ya existe) sin captura real de roam; el close_check termina en xfail y la ficha declara decision del dueno 2026-10-11 de dejarla abierta, no void_wontfix. Riesgo de aislamiento wifi es real solo si el equipo opera por wifi; hay cable r8127.

Version para un solo nodo Gigabyte AI TOP ATOM: Capturar una secuencia roam real en el mt7925e (interfaz/AP, ruta, DNS, intento aislado) y correr el selector existente; o fusionar con FEATURE-FORUM-WIFI-ISOLATION-01.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Root Cause
Meta-ficha sin sujeto propio: pedia implementar los criterios ejecutables de `tools.verify_wifi_isolation`. El verificador existe (`tools/verify_wifi_isolation.py`) y es el close_check de `FEATURE-FORUM-WIFI-ISOLATION-01`; hoy sale con rc=2 (could_not_run) porque falta la captura real del sujeto, que es el trabajo de esas fichas, no de esta. Su propio close_check era un selector xfail que no podia cerrar nada.

## Regression Test
Ninguno propio: la ficha se cierra como duplicada. Se retira `tests/test_debt_registration_controls.py::test_debt_close_check_verify_wifi_isolation_01` y `tests/test_closure_hardware.py::test_debt_close_check_verify_wifi_isolation_01`, xfail de relleno, junto con sus entradas de `tests/known_failures.json`; las pruebas unitarias de `tools.verify_wifi_isolation` siguen corriendo.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: el close_check de cada ficha sujeto sale hoy con rc distinto de 0, el verificador sabe decir que no), `pass` (el verificador existe, cada ficha sujeto lo nombra y sus pruebas unitarias pasan: control positivo) y `e2e` (la decision registrada). Cada ficha sujeto lleva una nota que dice que los criterios de `tools.verify_wifi_isolation` se miden alli. Para reabrirla: `git mv tasks/done/DEBT-CLOSE-CHECK-VERIFY-WIFI-ISOLATION-01.md tasks/backlog/` y `status: open`.
