---
id: DELTA-FORUM-DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01
kind: task
domain: VERDICT
title: "Validar forum dualspark nccl gid twin and cold recovery 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_dualspark_nccl_gid_twin_and_cold_recovery_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01.** En [361967, posts 158–167 y 190](https://forums.developer.nvidia.com/t/361967/162), un operador de dos ASUS GX10 reportó NCCL allReduce fallando al inicializar Qwen3.5-397B-A17B INT4 AutoRound aunque `ib_write_bw` entre pares alcanzaba 108 Gbit/s y las cuatro interfaces figuraban UP. En el post 190 redujo `IB_IF` de `rocep1s0f1,roceP2p1s0f1` a `rocep1s0f1`; observó que el índice GID 3 del twin sin IPv4 era null, y después NCCL avanzó, aunque la recuperación también incluyó apagar y desconectar ambos suministros. Es evidencia de que `ib_write_bw`, link-up y GID de otra interfaz no validan el HCA/GID efectivo de NCCL; no aísla el cambio causal. Extender el preflight multi-nodo ya existente para registrar por nodo el HCA/RoCE twin seleccionado, IPv4/GID index efectivo, MTU e interfaz usada, y ejecutar collective NCCL y primera inferencia con la misma selección del serving. Incluir control con twin sin IPv4/GID null y conservar el inventario/log antes de recovery. No autoquitar interfaces ni aplicar ciclo de energía; esos cambios requieren canary, evidencia de antes/después y rollback de configuración. Prueba reportada en kernel/red/imagen de marzo 2026, sin reproducción local.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Evaluación de instrumentos 2026-10-03

Reusa host diagnostics/network inventory solo para enumeración HCA/GID; captura local reportada sin HCA, consulta de link inaccesible, transporte sin validar y adjunto físico desconocido. No hay evidencia de nodos gemelos o GID seleccionada. Siguiente paso `deferred_lab`: capturas de ambos nodos e identidad HCA/GID/IP, prueba del mismo collective e inferencia inicial, control nulo de GID/twin y preservación de logs antes de recovery. No hubo tráfico, reinicio ni recuperación.
