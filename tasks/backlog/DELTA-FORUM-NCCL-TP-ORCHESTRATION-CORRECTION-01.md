---
id: DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01
kind: task
domain: VERDICT
title: "Validar forum nccl tp orchestration correction 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_nccl_tp_orchestration_correction_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01.** Un reporte inicial atribuía un cuelgue TP=2 entre dos Spark a NCCL, después de ver canales conectados y hangs en TRT-LLM/vLLM ([366127](https://forums.developer.nvidia.com/t/366127)). El mismo autor reimaginó Ubuntu 25.10 a DGX OS 24.04.4 soportado: la prueba independiente `nccl-tests all_reduce_perf` pasó a 17.3 GB/s sin errores; el hang restante de TRT-LLM quedó localizado en captura CUDA Graph. Más tarde corrigió la conclusión TP: en el stack dual DGX OS 24.04.4, kernel 6.17.0-1014, driver 580.126.09, contenedor nightly `ghcr.io/spark-arena/dgx-vllm-eugr-nightly`/vLLM 0.19.1rc1/NCCL 2.29.7/Qwen3-235B NVFP4, el launcher de receta `launch-cluster.sh` sirvió TP=2 con CUDA graphs a 22.6 tok/s; `--no-ray` en el mismo launcher también pasó a 23.1 tok/s. Los lanzamientos manuales sin ese setup colgaban. Esto corrige la atribución de que Ray arregló NCCL: el autor dice que la variable común fue el launcher y el entorno por nodo. Reproducir primero el NCCL microtest, validar interfaz/subred y variables efectivas en cada worker, comparar launcher oficial/receta frente a comandos manuales, y conservar por rango los logs antes de reiniciar. No recomendar una config NCCL global basada en este hilo. Las imágenes community y scripts enlazados no fueron auditados; el `pip install instanttensor` y `docker commit` posterior es una modificación mutable distinta, que requiere fijar digest y probar rollback antes de producción.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.
## Evaluación de instrumentos 2026-10-03

Reusa `tools/provider_trace.py` solo para worker/proveedor; no observa el launcher por nodo, variables/interfaz efectiva, NCCL microtest ni CUDA Graph. No hay captura local de launcher/logs por rango; el registro existente `root-qwen-image-review.json` corresponde a otras imágenes y declara casos sin A/B, por lo que no cubre esta ficha. Estado `deferred_lab`: stack dual fijado, microtest y comparación receta/manual con logs por nodo y control de salida, antes de atribuir causalidad a NCCL/Ray.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: La corrección de orquestación requiere jobs NCCL/TP reales y control de fallo del coordinador; no se halló resultado local en la evidencia específica.
- Evidencia faltante para cierre: stack/digests; logs rank/node/collective; positivo multi-GPU y negativo de orquestación; rollback
- Siguiente acción: Preparar job NCCL/TP en canario multi-GPU con topología y digests fijados; probar coordinación sana y negativa y archivar trazas completas.
- Responsable del siguiente paso: coordinación BB prepara; operador Luis ejecuta root/lab.
- Cierre completo accionable hoy: no. Preparación coordinable: sin acción adicional demostrada en esta revisión.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01.md`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_05.json`, `tasks/evidence/DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01/ (directorio ausente al inspeccionar)`.
- Impedimentos de inspección: 1. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
