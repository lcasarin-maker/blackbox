---
id: DELTA-ROOT-GX10-SOC-EC-CABLE-RECOVERY-CANDIDATE-01
kind: task
domain: VERDICT
title: "Validar root gx10 soc ec cable recovery candidate 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_root_gx10_soc_ec_cable_recovery_candidate_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-ROOT-GX10-SOC-EC-CABLE-RECOVERY-CANDIDATE-01 — Candidato OEM de recuperación de cables

Fuente: [hilo 367221](https://forums.developer.nvidia.com/t/367221).

En varios GX10, desactivar hotplug o forzar plug-in restaura las funciones PCI, pero permanece NO-CARRIER y error EIO al leer EEPROM. FieldDiag PASS coexistió con el fallo. El propietario reporta reconocimiento de cables persistente tras reinicios/reconfiguración con SoC 3000007 + EC 20000006 de LVFS testing y switch CRS804. Cambió dos componentes juntos; falta auditoría de los bundles y duración de soak.

Propuesta: Registrar ese tuple como candidato específico GX10 y canal testing. Comparar firmware efectivo antes/después, estado nativo hotplug, presencia/EEPROM del cable, negociación y tráfico funcional tras arranque frío/caliente. Conservar recuperación OEM y versiones anteriores verificables; evaluar componentes separados cuando sea viable. La hipótesis de direcciones iomem ausentes/DOE no demuestra causa. No trasladar firmware GX10 a ATOM ni suspender handlers sin manifest, expiry y vigía.

Riesgo: firmware de prueba puede dejar la red o el arranque inoperables; traslado entre OEM incompatible.

Cierre: Fixture distingue PCI visible, módulo presente y enlace/tráfico operativo. A/B con tuple exacto y regresiones tras reboot; rollback probado. El nvidia-bug-report y tres paquetes se descargaron y leyeron parcialmente. El report confirma FW CX7 28.45.4028, MNG FW opcode 1024, cable speeds 0x0 y EEPROM EIO; el archive de node3 incluye el handler config-gated `/etc/nvidia/cx7-hotplug-enabled`, hotplug_enabled=1, y logs de removal de las funciones CX7. Metadatos node1/2: GX10 OTA 7.5, BIOS de 2026-01-29, kernel 6.17.0-1014 y PSID NVD0000000087. Los registros propietarios brutos no se decodificaron; el error exacto y la propuesta SoC+EC que cambia dos componentes siguen sin resolver y requieren respuesta OEM/A-B. No borrar ni bloquear el handler: en el equipo de Luis existe actualmente el flag nativo y se debe probar el control soportado antes de cualquier workaround.

Fuentes: tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
