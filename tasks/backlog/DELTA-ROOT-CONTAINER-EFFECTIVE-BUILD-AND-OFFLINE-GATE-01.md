---
id: DELTA-ROOT-CONTAINER-EFFECTIVE-BUILD-AND-OFFLINE-GATE-01
kind: task
domain: VERDICT
title: "Validar root container effective build and offline gate 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_root_container_effective_build_and_offline_gate_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

### DELTA-ROOT-CONTAINER-EFFECTIVE-BUILD-AND-OFFLINE-GATE-01

Fuentes: https://forums.developer.nvidia.com/t/362721/24 y /26–46; https://forums.developer.nvidia.com/t/375945/9 y /19–43.

362721: repo y wheel actualizados coexistieron con imagen efectiva experimental vieja, falta de kernels NVFP4/no-act-and-mul y MXFP4 roto; nombre por defecto reutilizó contenedor al intentar segundo modelo. Rebuild y cambio de cuota ayudaron a un propietario; otro seguía fallando, luego carga FP4/8 tras limpieza completa sin causa aislada. HEAD a HF bloquea inicio por timeouts. 375945: 1M real requiere TTFT 2524584ms; bucle de thinking es fallo de contenido y ocurre también fuera de la receta, mientras DCP aceleración inicial fue explícitamente desmentida.

Acción: Preflight y canario comprueban digest y build efectivos dentro de cada contenedor, modelo/checkpoint/patches, nombre y puerto reales y reserva conjunta de memoria. Probar carga e inferencia real de la arquitectura, no inferir compatibilidad de presencia de torch.ops antes de importar extensiones. Precachear artefactos completos por revisión y verificar arranque sin red antes de activar modo offline. Conservar imagen anterior y aislar cache mediante rename+manifest con sha/mode/expiry/vigía, sin copiar purgas globales de volúmenes.

Cierre: Fixture wheel nuevo/imagen vieja detectada; dos instancias nombres/puertos distintos y presupuesto agregado. Canary por modelo carga y genera; rollback a digest previo. Arranque sin red completo y fallo explícito por archivo faltante. Permitir prefill largo con progreso; detener bucle de contenido con presupuesto y error específico.

Riesgos: Tests nightly declarados por mantenedor no auditan cada carga del usuario; PR/código externo sin revisar; Offline con caché incompleta impide arrancar; bucles semánticos y prefill largo requieren clasificación distinta.

**FORUM-00-DS4F-APPEND-PREFILL-KV-CHECKPOINT-GATE.** [377281, posts 51 and 93](https://forums.developer.nvidia.com/t/concern-about-the-usefulness-of-a-single-dgx-spark/377281/93) contrasts an owner’s single-GB10 DS4 workflow that reportedly took about an hour to inspect 60 small files because each turn re-prefilled the unchanged history, with a separate CUDA-fork author’s report of append-prefill and canonical KV checkpoint reuse. That author reports ~836 tok/s average prefill while appending from 128K to 181K and 24–25 tok/s decode at 55K–70K, but gives no exact stack versions in the post; attached benchmark screenshots were not reviewed and neither implementation nor figures were independently validated. Review and pin the source, then A/B baseline vs reuse with cold/warm prefill, per-turn latency, cache hits/bytes, changed-prefix invalidation, answer equivalence and UMA/cgroup state on a single GB10. Preserve prior image/config for rollback; do not treat the reported speed as a BB baseline or promote unreviewed KV checkpoints.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
