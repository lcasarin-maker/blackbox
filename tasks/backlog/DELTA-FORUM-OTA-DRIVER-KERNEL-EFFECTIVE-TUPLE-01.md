---
id: DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01
kind: task
domain: VERDICT
title: "Validar forum ota driver kernel effective tuple 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_ota_driver_kernel_effective_tuple_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01.** Durante el rollout DGX OS 7.4, los usuarios observaron OTA 7.4 con kernel 6.14; después el kernel 6.17.0-1008 llegó por la ruta de paquetes mientras la versión/fecha del OTA, kernel y driver avanzaban desincronizados ([359550](https://forums.developer.nvidia.com/t/359550)). El hilo recoge aviso de que Driver 590.48.01 no estaba listo para GB10 y un propietario reporta después una unidad casi inutilizable con ~5.5 GiB libres de 121 GiB, que recuperó al volver a 580.126.09; otra respuesta aclara que GB10 usa memoria unificada y que `nvidia-smi` devuelve `[N/A]` para memoria. Son relatos de usuarios; no se inspeccionaron logs adjuntos ni se demostró causalidad independiente. NVIDIA dijo que el carveout UEFI baja 4→2 GiB con OTA2 en equipos partner una vez que OEM lo adopta, mientras un post previo confundía el cambio con firmware EC; diferenciar EC/build, release OTA, kernel activo, driver activo y carveout observado. Prevención: admitir únicamente el tuple kernel/driver/CUDA/DGX OS soportado por release notes y la variante OEM; leer metadatos efectivos tras actualización y medir `MemAvailable`/PSI desde Linux, no usar memoria GPU de nvidia-smi. No instalar drivers/kernel manualmente desde `proposed` como default. Validar en OEM canary el rollout parcial, boot/recovery, memory baseline y workloads bajo soak; rollback por canal OEM conocido.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Avance de inventario — 2026-10-03

`tools/apt_sources.py` reutiliza `tools.memory_profile.capture` para registrar el tuple local DGX SW build `7.2.3` / OTA `7.6.0` / kernel `6.17.0-1032-nvidia` / driver cargado y en disco `580.178.04`, con igualdad de versiones observada. Captura: `tasks/evidence/BB-INSTRUMENTS-2026-10-03/apt-sources-capture.json`; la salida marca procedencia no verificada y `support_verdict: not evaluated`. No compara contra release notes/OEM ni ejecuta canary, workload, recovery o rollback; el reporte de tuple no demuestra el hallazgo ni cierra la ficha.
