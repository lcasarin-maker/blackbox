---
id: FEATURE-FORUM-NVME-READONLY-01
kind: task
domain: STORAGE
title: "Detectar pérdida de escritura y preservar evidencia antes de recuperar un NVMe"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest tests/test_nvme_readonly.py -q", "expect": "exit_zero", "porque": "Prueba específica pendiente: debe distinguir errores de medio, remount read-only, consultas ilegibles y un dispositivo sano, con salida de evidencia utilizable sin escribir al medio sospechoso."}
---

## Fuente y evidencia

[354576](https://forums.developer.nvidia.com/t/354576) describe un Spark con filesystem read-only, GRUB incapaz de escribir sectores y NVMe de 4 TB visible en BIOS. La recuperación oficial v1.91.51-1 tardó unas diez horas según el autor, terminó con errores de checksum/read-only y dejó la unidad sin arranque; soporte la consideró candidata a RMA. Faltan identidad y firmware del NVMe, SMART y kernel logs: la causa física sigue sin demostrar. [371868](https://forums.developer.nvidia.com/t/371868) aporta orientación de soporte tras una prueba NVMe fallida; sus imágenes quedan sin inspeccionar. El análisis y límites originales están en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_01.json`.

Los hilos [354724](https://forums.developer.nvidia.com/t/354724), [362916](https://forums.developer.nvidia.com/t/362916) y [365609](https://forums.developer.nvidia.com/t/365609) añaden NVMe ausente en UEFI/recovery y self-test PASS/FAIL frente a fallo intermitente. Un PASS previo deja pendiente el estado del siguiente boot. [356091](https://forums.developer.nvidia.com/t/356091) relata RMA; sus screenshots siguen sin inspección. Conservar estas rutas como subcasos de presencia y recuperabilidad, separadas de corrupción buffered/O_DIRECT en GX10.

## Hueco y propuesta

BB captura journal y tiene trabajo de integridad de lecturas en `FORUM-02-GX10-READ-INTEGRITY`; falta distinguir pérdida de escritura/remount read-only y estado NVMe antes de perder el arranque. Reutilizar mensajes kernel, información de mounts y herramientas nativas `nvme-cli`/SMART cuando estén disponibles. Registrar identidad, firmware, valores crudos, timestamps y errores de consulta; una enumeración BIOS correcta o un self-test previo sano deja pendientes otras rutas de fallo.

Ante una señal corroborada, conservar evidencia y ofrecer recuperación/backup/RMA soportados antes de repetir reflashes o escrituras sobre un medio sospechoso. Preparar un destino externo operable cuando el disco local falla. La guía conserva los datos existentes y distingue fallo físico, filesystem y transporte; el reporte del foro por sí solo no identifica al SSD como culpable.

## Validación, riesgos y cierre

Fixtures de errores NVMe/I/O, remount read-only, permisos insuficientes, dispositivo ausente y control sano; comprobar que el análisis conserva el orden y separa boots. Ensayo de exportación y recuperación sobre copia o dispositivo de laboratorio, con identificación de OEM y ruta de retorno. Registrar comandos y resultados originales. Consultas de salud pueden requerir privilegios o exponer contadores distintos por OEM; la ausencia cuenta como `could_not_run`. Evitar self-tests destructivos, formateo y escrituras de reparación al dispositivo sospechoso. La suite propuesta todavía no existe; la ficha registra trabajo abierto, no protección implementada.

[373324](https://forums.developer.nvidia.com/t/373324) añade Samsung MZALC4T0HBL1-00B07 con degradación de72h, EFI fallido y lectura externa read-only con hangs/EIO; fsck -fn reportó EIO. El autor conservó datos evitando reimage y NVIDIA indicó backup/RMA. [383478](https://forums.developer.nvidia.com/t/383478) reporta recovery Completed pese a dd0bytes/EIO: validar escrituras/lecturas y boot efectivo, sin tomar el mensaje de UI como éxito. Estos relatos dejan pendiente determinar causa del medio, controlador o firmware.


## Índice de propuestas registradas del swarm NVIDIA categoría 721

- **`BB-NVME-PRESENCE-RMA-TRIAGE`** — One reported Spark could not find its NVMe in UEFI or recovery and was referred to RMA; a second report had inconsistent local EFI boot-path visibility/recovery, despite short and extended NVMe self-tests passing, and also ended in RMA.… Fuente: [354724](https://forums.developer.nvidia.com/t/dgx-spark-not-detecting-nvme-drive-not-booting-system-recovery-fails/354724/1).

## Avance de ejecución 2026-10-03

Se añadió `tools/nvme_readonly.py`: exige inventario NVMe con ruta y serial, una sola observación válida de `/`, y señal de error NVMe asociada en la misma línea; separa fail de consultas inaccesibles. La exportación de archivo regular a otro filesystem verifica dev/inode/size/mtime/ctime y SHA-256, rechaza overwrite y detecta cambios de ruta aun cuando el reemplazo conserva bytes y mtime. Un inventario y log sin error se informa como observación, no como prueba de salud física. Las pruebas validan el instrumento; el ensayo de exportación y recuperación sobre copia/dispositivo NVMe de laboratorio sigue pendiente. Estado permanece `open`.

## Ensayo sobre copia regular — 2026-10-03

Ejecutado `python3 -m tools.nvme_readonly --export-source <archivo-controlado> --destination-dir <destino>` entre dos filesystems reales: origen `/tmp` (`st_dev=66306`) y destino `/dev/shm` (`st_dev=31`). Archivo sintético de 4096 bytes; exportación y retorno pasan con SHA-256 idéntico (`c8f5d0341d54d951a71b136e6e2afcb14d11ed8489a7ae126a8fee0df6ecf193`). Inode, tamaño, mtime y ctime del origen conservados. Dos controles negativos rechazan sobrescritura y destino en el mismo filesystem: ambos devuelven rc2/`could_not_run`, preservados como tales. Conteos: pass=2, fail=0, could_not_run=2 (negativos intencionales), resultados inesperados=0.

Los comandos literales, timestamps, stdout/stderr y códigos están en `tasks/evidence/FEATURE-FORUM-NVME-READONLY-01/export-copy-lab/run.json`. Se eliminaron solamente los directorios temporales creados por este ensayo después de leer y verificar el retorno. El ensayo acredita copia/retorno de archivo regular; la identidad OEM, capturas de fallo NVMe y recuperación de un dispositivo siguen pendientes. La ficha conserva `open`.


## Control de cierre real integrado — 2026-10-04

El comando original conserva su texto y ahora incluye el selector `test_nvme_real_incident_close_check_requires_raw_device_and_recovery_evidence`. El lector exige recibos crudos acotados, identidad de namespace/serial/modelo/firmware, contadores SMART con tipos exactos, journal asociado al dispositivo y boot, observaciones de mounts ordenadas, copia/retorno con hashes y filesystem, y ruta OEM ligada al sujeto. Los casos sintéticos completos y sus mutaciones comprueban el lector; la copia regular existente conserva su alcance de laboratorio.

Revalidación en primary: `python3 -m pytest tests/test_nvme_readonly.py -q` → `1 failed, 28 passed in 0.22s`. El único fallo es `UNKNOWN/CNR` por siete capturas ausentes bajo `incident/`: `device-identity.json`, `smart-health.json`, `kernel-journal.json`, `mount-transitions.json`, `recovery-and-rollback.json`, `backup.json` y `rollback.json`. Es un ensayo físico pendiente; el reporte de cierre sigue incompleto. No se ejecutaron consultas privilegiadas ni escrituras al NVMe.

Recibo de integración y logs: `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/nvme-real-selector-primary-integration.json`. Los contraejemplos y rechecks de archivos vacíos están en el mismo directorio. Estado `open`; el criterio original permanece intacto.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: El ensayo existente es copia/restauración de archivo regular; el selector requiere evidencia de incidente NVMe y recovery ligado al dispositivo.
- Evidencia faltante para cierre: Identidad serial/model/firmware, SMART, journal correlacionado, transición mount, backup/export+restore, recuperación/rollback y ruta OEM.
- Siguiente acción: Solicitar capturas readonly de identidad/SMART/journal/mount y backup a filesystem externo ante incidente; reservar prueba de recovery/rollback para NVMe de laboratorio sano, sin escribir medio sospechoso.
- Responsable del siguiente paso: BB; operador Luis para hardware/peer.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FEATURE-FORUM-NVME-READONLY-01.md`, `tasks/evidence/FEATURE-FORUM-NVME-READONLY-01/export-copy-lab/run.json`, `tasks/evidence/FEATURE-FORUM-NVME-READONLY-01/host-observation.txt`, `tools/nvme_readonly.py`, `tools/forum_hardware_subjects.py`, `tests/test_nvme_readonly.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
