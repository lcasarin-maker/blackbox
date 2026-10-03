---
id: DEBT-NO-COVER-CALIBRA-PSI-322
kind: task
domain: VERDICT
title: "Revisar no-cover en calibra_psi.py:322"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_no_cover_calibra_psi_322", "expect": "exit_zero", "porque": "Medir el camino excluido sin depender de la marca no cover. Si es entrypoint, ejecutar el script real con caso válido e inválido y comprobar stdout/rc; si es un fake, justificar qué camino es inalcanzable y comprobar esa afirmación. Control negativo: mutar el comportamiento del sujeto y demostrar rechazo. Quitar la marca o conservar una exclusión justificada sin afirmar cobertura de lo excluido."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Sitio: `tools/calibra_psi.py:322`; función/contexto: calibra_psi.

```text
if __name__ == "__main__":  # pragma: no cover -- entry point, ejercitado via main()
```

Clasificación: revisión de una exclusión/captura, no bug demostrado. No retirar automáticamente una protección o cleanup.

Fuentes: tools/calibra_psi.py:322.

## Criterio de cierre y control negativo

Medir el camino excluido sin depender de la marca no cover. Si es entrypoint, ejecutar el script real con caso válido e inválido y comprobar stdout/rc; si es un fake, justificar qué camino es inalcanzable y comprobar esa afirmación. Control negativo: mutar el comportamiento del sujeto y demostrar rechazo. Quitar la marca o conservar una exclusión justificada sin afirmar cobertura de lo excluido.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
