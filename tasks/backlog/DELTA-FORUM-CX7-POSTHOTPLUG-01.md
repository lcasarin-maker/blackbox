---
id: DELTA-FORUM-CX7-POSTHOTPLUG-01
kind: task
domain: VERDICT
title: "Validar forum cx7 posthotplug 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_cx7_posthotplug_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-CX7-POSTHOTPLUG-01.** En un clúster GB10 con CX7 firmware 28.45.4028, kernel 6.17.0-1018-nvidia, driver 580.159.03 y mlx5 26.01-1.0.0, el dueño reporta que tras desconectar/reconectar una NIC el all-gather NCCL cae de ~192 a ~25 Gbit/s; `mlxlink` conserva Active/200G y el dueño muestra AER y reenumeración PCIe, mientras reiniciar restaura throughput ([371031](https://forums.developer.nvidia.com/t/371031)). En [363193](https://forums.developer.nvidia.com/t/363193) hay relatos separados de root-port retraining/endpoint ausente y enlace/cable caído; FieldDiag PASS coexistió con NIC no disponible. El adjunto nvidia-bug-report.log.gz no fue leído y las causas siguen abiertas. Añadir un canary post-hotplug que compruebe tráfico NCCL/RDMA extremo a extremo, endpoint PCIe, AER y resultado/frescura de FieldDiag; el estado Active/200G o 27W aislados no cierran salud. Riesgo: reinicio o cambio de marcador altera el estado; registrar versión/cable/firmware y probar en nodo canary con rollback por OEM.

Fuentes: tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Avance de instrumentación 2026-10-03

`tools.host_diagnostics` captura MTU, carrier, operstate, binding PCI/driver y, si hay sysfs RDMA, GID/netdev/firmware por puerto. No provoca hotplug ni valida throughput, recovery o NCCL; la captura actual no expuso dispositivos RDMA y `ip -j link` quedó inaccesible. Evidencia: [BB-INSTRUMENTS-network](../../docs/evidence/BB-INSTRUMENTS-network.md). La ficha permanece abierta; `close_check` y `status` no cambiaron.
