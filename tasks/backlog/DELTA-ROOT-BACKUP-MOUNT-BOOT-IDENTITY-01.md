---
id: DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01
kind: task
domain: VERDICT
title: "Validar root backup mount boot identity 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_root_backup_mount_boot_identity_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01 — Validar el destino de respaldo tras reinicio

Fuente: [hilo 375954](https://forums.developer.nvidia.com/t/375954); cuerpos capturados leídos, sin auditoría de binarios ni repos externos.

SanDisk Extreme 55DD 8 TB desaparece tras reinicio en kernel 6.17-1026: EPROTO -71 antes de enumerar UAS. Replug restaura el disco; OTA, autosuspend y varios cables no resuelven. Un ASM2464 distinto monta a USB2 y negocia Gen2x2 tras replug. NVIDIA sigue investigando; causa y parche permanecen pendientes.

Propuesta: Antes del respaldo y del restore, verificar UUID, dispositivo esperado, mountpoint real y disponibilidad; ante ausencia, abortar con evidencia y conservar datos. Evitar escribir al directorio vacío sobre el filesystem raíz. Capturar estado antes/después de replug y distinguir enumeración, montaje y permisos.

Riesgo: Reenumerar USB durante escritura puede perder datos; cable o firmware como causa permanece hipótesis.

Cierre: Fixture con disco ausente y mountpoint existente bloquea escritura; prueba tras reinicio valida identidad y lectura del respaldo. Recuperación conserva datos y requiere resultado verificable.


Fuentes: tasks/backlog/FEATURE-FORUM-RESCUE-RUNBOOK-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El selector original ya está integrado y llama a `tools.hardware_batch03_controls.verify` para este ID exacto. La ejecución del 2026-10-04 devolvió UNKNOWN, fail=0, could_not_run=1 por captura requerida ausente o contrato incompleto. El comando literal y su salida están registrados en `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch03-integration/original-selectors-after-reader-hardening.json`. Los tests de fixtures verifican el control; el cierre requiere el sujeto real y su evidencia específica.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Nota de instrumentación readonly (2026-10-03)

El guard `tools.host_diagnostics --check-backup-destination` exige mountpoint, source y UUID explícitos y bloquea ausencia o discrepancia; los controles locales están en `tests/test_boot_storage_inventory.py`. La captura local queda `unknown` porque no existe identidad esperada autorizada; ningún backup/restore se ejecutó. Detalles: `docs/evidence/BB-INSTRUMENTS-boot.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `user_decision`.
- Impedimento: Selector dio UNKNOWN/fail=0/CNR=1 y la guard local necesita UUID/source esperados; no existe identidad de destino esperada autorizada, y ningún backup/restore fue corrido.
- Evidencia faltante para cierre: Selector dio UNKNOWN/fail=0/CNR=1 y la guard local necesita UUID/source esperados; no existe identidad de destino esperada autorizada, y ningún backup/restore fue corrido.
- Siguiente acción: Luis: declarar el UUID y origen esperados del destino de respaldo; coordinación BB: entonces ejecutar guard de sólo lectura y fixture de discrepancia, sin iniciar backup. Ref explícita: tasks/backlog/DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01.md y tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_03.json.
- Responsable del siguiente paso: Luis decide/aporta la identidad esperada del recurso antes de validar..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01.md`, `docs/evidence/BB-INSTRUMENTS-boot.md`, `tests/test_boot_storage_inventory.py`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_03.json`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
