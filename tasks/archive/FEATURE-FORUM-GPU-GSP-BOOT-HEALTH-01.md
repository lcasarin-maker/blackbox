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

## Trabajo en la ATOM

Separar en la ATOM PCI presente / GSP inaccesible / ninguna GPU enumerada con la sonda `gpu_gsp` de `tools/huella_host.py`; falta un incidente real (o inyeccion soportada) con versiones y boot preservados y la ruta de recuperacion/rollback.

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/373171
- https://forums.developer.nvidia.com/t/364499/1
- https://forums.developer.nvidia.com/t/373394/1
- https://forums.developer.nvidia.com/t/dgx-spark-mini-connectx-7-qsfp-ports-not-powering-diagnostic-tool-unavailable/363311

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Delta y prevención/resolución

FEATURE-GPU-XID-DETECTION ya comprueba nvidia-smi con timeout y captura Xid. Primero probar esa ruta: crear otra sonda exige demostrar un hueco concreto.

Añadir el caso real como fixture de la instrumentación existente, conservando boot, firmas GSP sin Xid y diferencia entre command error y ninguna GPU enumerada. Si la detección actual cubre el caso, cerrar como validación cubierta; ante delta demostrado extender la ruta existente.

## Validación, riesgo y cierre

GPU sana, PCI presente/GSP fallido, PCI ausente, rechazo de firma y permisos. Capturar evidencia antes de reset/reload; validar en incidente natural o fault injection soportada, sin atribuir causa desde un self-test previo.

El verificador de close_check todavía debe implementarse; ejecutar esta ficha exige evidencia adicional y deja registradas las consultas que no pueden correr. Ningún cambio del host se aplica al registrar la propuesta. Detalle fuente preservado en tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_*.json y threads/.

## Progreso de preflight (2026-10-02)

Se implementó `python3 -m tools.preflight gsp <snapshot.json>` para separar presencia PCI, CUDA operativo y observación de timeout GSP. El control sano actual muestra GB10 en PCI, CUDA disponible con capacidad 12.1, GSP firmware 580.178.04, recuperación NVSMI `None` y ninguna entrada actual del kernel que coincida con GSP/SEC2/timeout. El resultado del control sano es `pass`; los controles negativos de PCI ausente, CUDA error y timeout se ejecutan en `tests/test_preflight.py`. Comandos y salidas literales: `tasks/evidence/FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01/commands.json`; evaluación: `preflight.json` y `validator-run.json`.

La ficha sigue abierta: falta un incidente fallido con versiones/boot preservados, una inyección de fallo soportada y compatibilidad OEM. El estado sano actual no prueba la cobertura del caso de campo.

## Nota de instrumentación readonly (2026-10-03)

Se reutilizó `gpu_runtime_capture` y se preservó resultado `could_not_run` de `nvidia-smi`; la telemetría existente no prueba un incidente GSP/SEC2 ni recuperación. Evidencia: `tasks/evidence/BB-INSTRUMENTS-2026-10-03/boot.capture.json` y `docs/evidence/BB-INSTRUMENTS-boot.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: Preflight y estado de host no demuestran salud GSP durante boot ni recuperación OEM; selector reporta evidencia incompleta.
- Evidencia faltante para cierre: log crudo de boot/GSP con versión firmware/driver; control de fallo; boot/recovery y rollback OEM
- Siguiente acción: Capturar arranque sano y control negativo en GX10 canary con telemetría persistente y rollback probado.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_05.json`, `tasks/evidence/FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01/commands.json`, `tasks/evidence/FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01/preflight.json`, `tasks/evidence/FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01/validator-run.json`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Avance 2026-10-13

- close_check antes: rc=2, `could_not_run: 1` (faltan control negativo de incidente y recuperacion/rollback). Sigue igual: este avance no lo cierra.
- Construido: sonda `gpu_gsp` en `tools/huella_host.py` (PCI display NVIDIA + nvidia-smi con timeout 10 s + `journalctl -k -b` filtrado en Python por GSP/NVRM; veredicto `disponible` / `PCI_SIN_GSP` / `INDETERMINADO`; nunca `disponible` sin respuesta de nvidia-smi ni sin journal legible; la ultima linea se guarda sin el prefijo con el hostname). Tests en `tests/test_huella_host.py` (57 pasan; cobertura de `tools/huella_host.py` 99%, la unica linea sin cubrir es el `sys.exit` de `__main__`).
- Medido en esta maquina (boot actual): `disponible`, nvidia-smi `NVIDIA GB10, 580.178.04`, 0 lineas GSP en el journal del kernel.
- Controles negativos corridos en tests: PCI presente + nvidia-smi falla/timeout -> PCI_SIN_GSP; PCI presente + smi ok + linea de error GSP/NVRM -> PCI_SIN_GSP; PCI ausente -> INDETERMINADO; journal ilegible -> INDETERMINADO.
- Falta: un incidente real (o inyeccion de fallo soportada) con versiones y boot preservados, recuperacion/rollback OEM y verificador `verify_forum_finding` con esa evidencia. La sonda se probo con fixtures, no con un GSP fallido real (could_not_run).

## Criterios ejecutables de `tools.verify_forum_finding` (2026-10-14)
Los criterios ejecutables de `tools.verify_forum_finding` se miden en esta ficha: su `close_check` corre ese verificador contra la captura real del sujeto. La meta-ficha `DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01`, que pedia implementarlos, se cerro el 2026-10-14 como `duplicate` (voto de Luis: consolidar en la ficha sujeto): el verificador existe y hoy, sin esa captura, sale con could_not_run (rc=2); conseguir la captura es trabajo de esta ficha.
