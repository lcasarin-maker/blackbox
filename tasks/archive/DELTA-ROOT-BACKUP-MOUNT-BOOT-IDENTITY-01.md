---
id: DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01
kind: task
domain: VERDICT
title: "Validar root backup mount boot identity 01"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "Sin destino de respaldo configurado: fstab solo trae / , /boot/efi y swap, no hay montaje de red ni USB, unidad .mount/.automount ni trabajo de respaldo. Hay un NAS QNAP en la LAN (SMB en 445 con acceso anonimo denegado, sin NFS), pero el equipo no lo usa. Decision de Luis 2026-10-14 ('busca el NAS; si no, cerrar sin sujeto'): reabrir si se configura un respaldo al NAS (hace falta credencial de SMB y punto de montaje/UUID)."
evidence: {"pass": "tasks/evidence/DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01/pass.txt", "fail": "tasks/evidence/DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01/fail.txt", "e2e": "tasks/evidence/DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a tests/test_debt_registration_controls.py::test_delta_root_backup_mount_boot_identity_01, un xfail que se retira con el cierre."}
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

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: la ficha pide verificar UUID, dispositivo y mountpoint de un destino de respaldo tras el arranque. Medido 2026-10-14 en solo lectura: no existe ese destino. El NAS de la LAN responde por mDNS y SMB pero sus recursos exigen credencial y ningun montaje ni trabajo apunta a el; Deja Dup tiene backend google, nunca respaldo y sin periodicidad.

## Regression Test
Ninguno: la ficha se cierra por no tener sujeto aqui. Los tests que la vigilaban (`tests/test_debt_registration_controls.py::test_delta_root_backup_mount_boot_identity_01`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`. El guard `tools.host_diagnostics --check-backup-destination` y `tools/hardware_batch03_controls.py` siguen vivos para cuando exista un destino.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (perfil medido: fstab, NAS por mDNS, puertos 445/443/8080 abiertos y 2049/22 cerrados, SMB anonimo denegado, sin NFS, timers y Deja Dup, con control positivo (IP, MAC y nombre del NAS redactados)) y `e2e` (la decision registrada). Para reabrirla si el sujeto aparece: `git mv tasks/done/DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01.md tasks/backlog/` y `status: open`.
