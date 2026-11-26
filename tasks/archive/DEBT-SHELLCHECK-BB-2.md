---
id: DEBT-SHELLCHECK-BB-2
kind: task
domain: VERDICT
title: "Revalidar excepción ShellCheck de bb:2"
status: done
closed_at: 2026-10-02
closure_type: fixed
reason: "Condiciones de status registran éxito/fallo con if; se elimina la exclusión global SC2319."
evidence: {"pass": "tasks/evidence/DEBT-SHELLCHECK-BB-2.pass.txt", "fail": "tasks/evidence/DEBT-SHELLCHECK-BB-2.fail.txt", "e2e": "tasks/evidence/DEBT-SHELLCHECK-BB-2.e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_shellcheck_bb_2", "expect": "exit_zero", "porque": "Ejecutar ShellCheck del fragmento/sujeto y controles de retorno/quoting. Demostrar la advertencia sin excepción y su relación con el comportamiento real. Retirar el disable innecesario o conservar justificación específica, vigía y revisión fechada. No desactivar reglas globales ni debilitar las pruebas para obtener verde."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Exclusión activa: `# shellcheck disable=SC2319`. Sitio `bin/bb:2`. Revisar la razón existente; un disable no implica defecto por sí solo.

Fuentes: bin/bb:2.

## Criterio de cierre y control negativo

Ejecutar ShellCheck del fragmento/sujeto y controles de retorno/quoting. Demostrar la advertencia sin excepción y su relación con el comportamiento real. Retirar el disable innecesario o conservar justificación específica, vigía y revisión fechada. No desactivar reglas globales ni debilitar las pruebas para obtener verde.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Verificación realizada

Close_check falla sobre el código anterior y pasa sobre el nuevo; status conserva ARMADO/FALTA con cadenas sanas y memory.low=0. La prueba de SC2086 usa la raíz de cgroups con espacios y detecta el fallo anterior. Las reglas SC2319/SC2086 y bash -n pasan; ShellCheck completo conserva hallazgos independientes preexistentes, registrados por separado. Pruebas existentes de status en evidencia e2e.

## Root Cause

Capturar la condición con $? necesitaba una exclusión global SC2319; if registra directamente el resultado.

## Regression Test

El selector del close_check evalúa el script real con cadenas protegidas/rotas. SC2319 se comprueba sin la exclusión, y SC2086 se controla con una raíz con espacios.

## Verification Evidence

Las tres rutas evidence guardan resultados literales antes/después y cinco pruebas existentes de status. ShellCheck del script completo tiene otros hallazgos documentados por separado.
