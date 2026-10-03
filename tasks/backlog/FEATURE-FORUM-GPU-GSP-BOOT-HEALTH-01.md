---
id: FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01
kind: task
domain: GPU
title: "Validar disponibilidad GPU ante PCI presente y GSP inaccesible"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01 --evidence tasks/evidence/FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01", "expect": "exit_zero", "porque": "Verificador propuesto pendiente: requiere evidencia del caso positivo, controles negativos, compatibilidad OEM y recuperación/rollback; la ficha registra trabajo abierto."}
---

## Fuente y evidencia

[373171](https://forums.developer.nvidia.com/t/373171). Un autor conserva PCI, módulos y nodos pero CUDA devuelve 999 y GSP/SEC2 timeout; FieldDiag había pasado el día anterior. Faltan versiones y diagnóstico del estado fallido; GPU presente en PCI deja pendiente su disponibilidad efectiva.

## Delta y prevención/resolución

FEATURE-GPU-XID-DETECTION ya comprueba nvidia-smi con timeout y captura Xid. Primero probar esa ruta: crear otra sonda exige demostrar un hueco concreto.

Añadir el caso real como fixture de la instrumentación existente, conservando boot, firmas GSP sin Xid y diferencia entre command error y ninguna GPU enumerada. Si la detección actual cubre el caso, cerrar como validación cubierta; ante delta demostrado extender la ruta existente.

## Validación, riesgo y cierre

GPU sana, PCI presente/GSP fallido, PCI ausente, rechazo de firma y permisos. Capturar evidencia antes de reset/reload; validar en incidente natural o fault injection soportada, sin atribuir causa desde un self-test previo.

El verificador de close_check todavía debe implementarse; ejecutar esta ficha exige evidencia adicional y deja registradas las consultas que no pueden correr. Ningún cambio del host se aplica al registrar la propuesta. Detalle fuente preservado en tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_*.json y threads/.

## Progreso de preflight (2026-10-02)

Se implementó `python3 -m tools.preflight gsp <snapshot.json>` para separar presencia PCI, CUDA operativo y observación de timeout GSP. El control sano actual muestra GB10 en PCI, CUDA disponible con capacidad 12.1, GSP firmware 580.178.04, recuperación NVSMI `None` y ninguna entrada actual del kernel que coincida con GSP/SEC2/timeout. El resultado del control sano es `pass`; los controles negativos de PCI ausente, CUDA error y timeout se ejecutan en `tests/test_preflight.py`. Comandos y salidas literales: `tasks/evidence/FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01/commands.json`; evaluación: `preflight.json` y `validator-run.json`.

La ficha sigue abierta: falta un incidente fallido con versiones/boot preservados, una inyección de fallo soportada y compatibilidad OEM. El estado sano actual no prueba la cobertura del caso de campo.


## Índice de hallazgos asociados

- **`BB-GPU-SYS-PRI-POISON-REGISTER-DEGRADED-STATE`** — On a Spark and a separate HP ZGX Nano, authors report recurring NVRM `gpuHandleSanityCheckRegReadError_GH100` with register value `0xbadf5600` and `Unknown SYS_PRI_ERROR_CODE`, followed by NVML `GPU requires reset`; no Xid is reported.… Fuente: [364499](https://forums.developer.nvidia.com/t/364499/1).


## Índice de propuestas del lote 00

- `FORUM-00-GSP-BOOT-FAILURE-RECOVERY-BLOCKED` — [Preserve a GSP-failure escalation path when display, UEFI and FieldDiag are unavailable](https://forums.developer.nvidia.com/t/373394/1); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-FIELDDIAG-DRM-UNLOAD-BLOCK` — [Diagnose FieldDiag refusal when nvidia_drm remains busy](https://forums.developer.nvidia.com/t/dgx-spark-mini-connectx-7-qsfp-ports-not-powering-diagnostic-tool-unavailable/363311); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.

## Nota de instrumentación readonly (2026-10-03)

Se reutilizó `gpu_runtime_capture` y se preservó resultado `could_not_run` de `nvidia-smi`; la telemetría existente no prueba un incidente GSP/SEC2 ni recuperación. Evidencia: `tasks/evidence/BB-INSTRUMENTS-2026-10-03/boot.capture.json` y `docs/evidence/BB-INSTRUMENTS-boot.md`.
