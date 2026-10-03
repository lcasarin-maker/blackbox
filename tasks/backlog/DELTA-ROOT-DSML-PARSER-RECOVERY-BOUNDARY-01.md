---
id: DELTA-ROOT-DSML-PARSER-RECOVERY-BOUNDARY-01
kind: task
domain: VERDICT
title: "Validar root dsml parser recovery boundary 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_root_dsml_parser_recovery_boundary_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

## DELTA-ROOT-DSML-PARSER-RECOVERY-BOUNDARY-01

[Hilo 378784](https://forums.developer.nvidia.com/t/378784): el dueño reporta filtraciones DSML desde 60K de contexto y un estado roto a 150K después de aplicar PR #49117. La descripción incrustada del PR declara validación del parser, sin ensayo de servicio con el modelo; también reconoce que un marcador citado como prosa, idéntico a una herramienta declarada, puede convertirse en una invocación. Otro dueño reporta un proxy saludable con una imagen diferente: esa comparación requiere controlar el resto del stack.

Propuesta: conservar el historial que reproduce el fallo y probar streaming y respuestas completas, reasoning inconcluso, argumentos truncados, `tool_choice=none` y marcadores citados. Registrar qué queda fuera de la recuperación. El parche y el proxy siguen como candidatos; sus fuentes enlazadas quedaron sin auditar.

Riesgos: invocaciones espurias al interpretar prosa como herramienta y una nueva superficie de fallo al añadir un proxy. Close check: fixture del historial real y ensayo prolongado con contexto largo demuestran recuperación sin llamadas espurias ni pérdida de texto. El rollback restaura los digests y la configuración previa del parser y del proxy.

[368726](https://forums.developer.nvidia.com/t/368726) records a failed four-node switchless ConnectX-7 lane-split experiment: after MFT/MFT firmware configuration created an additional interface, the author found F2 aliased to F0 and able to pass traffic despite no physical connection; the mesh proposal was abandoned. A separate owner later says a four-node ring worked with custom networking/vLLM patches at a 10–20% performance cost, but the repository was not audited. Add an exact-OEM preflight after any CX7 lane/MFT changes that maps PCI BDF ↔ physical connector ↔ netdev and proves each intended link by disconnect/loopback control and sustained peer traffic, then runs NCCL collectives on the intended topology before workload admission. Preserve BIOS/MFT state, Secure Boot implications and recovery path; never infer physical paths from visible interfaces or adopt the community split commands as a supported fix. **DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01**.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
