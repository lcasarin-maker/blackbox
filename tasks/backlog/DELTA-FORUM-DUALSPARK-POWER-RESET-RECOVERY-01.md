---
id: DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01
kind: task
domain: VERDICT
title: "Validar forum dualspark power reset recovery 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_dualspark_power_reset_recovery_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01.** En el hilo de dos GB10 [361639, post 293](https://forums.developer.nvidia.com/t/361639/293), un usuario de Qwen3.5-122B-FP8 reportó que, después de apagar y desconectar alimentación USB-C, recuperó SCP sobre ConnectX a >700 MB/s, respuesta general del sistema y benchmark llama-benchy (p. ej. tg32 ~32.5 tok/s en esa configuración). No publicó A/B repetido ni aisló el estado del suministro, CX7, clocks, cableado o workload; cuenta como recuperación reportada, no como causa/fix universal. Añadir la secuencia a la investigación existente de baja potencia/rendimiento: guardar muestras y logs fuera del host, comparar clocks/potencia/rendimiento y enlace CX7 antes/después, y ejecutar shutdown limpio según OEM antes de retirar/reconectar alimentación en un nodo canary. No ejecutar ciclo automático ni recomendarlo como intervención general; preservar datos y rollback de cualquier cambio de cable/configuración.
- **`BB-GX10-HIGHCONTEXT-NO-POST-POWERON`** — An ASUS GX10 owner reports a high-context workload freeze near 120K tokens followed by power-on ending after about two seconds without BIOS; overnight power drain and a second Spark adapter did not restore boot. The proposed internal… Fuente: [383964](https://forums.developer.nvidia.com/t/383964/4).
- **`BB-GB10-OEM-SHUTDOWN-AND-IDLE-THERMAL-CONTROLS`** — Across user reports in a mixed Spark/Gigabyte AI Top Atom discussion: one shutdown attributed to thermal behavior reportedly stopped after BIOS update (versions not stated); a separate owner of two Atoms and two Sparks says both OEMs… Fuente: [372608](https://forums.developer.nvidia.com/t/372608/5).
- **`BB-GB10-THERMAL-SILENT-LOCK-RMA-VALIDATION`** — One A.7 Spark reports repeatable hard power loss under GPU load without pstore, vmcore, OOM, Xid or thermal-trip logs; idle GPU reported at 47–48C and last sample at 79C/82W. In a separate two-FE case, 12 silent locks during 262K… Fuente: [373251](https://forums.developer.nvidia.com/t/373251/1).
- **`BB-FE-THERMAL-FIELDDIAG-POWER-CUTOFF-COVERAGE`** — An MSI GX10 owner reports hard power cutoff around GPU burn temperature 80C and attached no-boot thermal FieldDiag code 020000021139; FE Spark owners elsewhere report similar silent cutoff even while generic FieldDiag passes. Another… Fuente: [358034](https://forums.developer.nvidia.com/t/358034/1).

Fuentes: tasks/backlog/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Evaluación de instrumentos 2026-10-03

No existe evidencia local del par Spark aislado, del perfil OEM de power reset ni de observaciones previas/posteriores; inventario/hostdiag no prueba recuperación causal. Estado `deferred_lab`: requiere procedimiento OEM aprobado, series externas antes/después y controles repetidos que separen power/CX7/clocks/workload, con rollback/criterio seguro. No se efectuó power cycle ni se alteró estado del host.
