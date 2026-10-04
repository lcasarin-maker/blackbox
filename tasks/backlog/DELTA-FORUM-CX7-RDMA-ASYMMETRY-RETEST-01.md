---
id: DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01
kind: task
domain: VERDICT
title: "Validar forum cx7 rdma asymmetry retest 01"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_debt_registration_controls.py::test_delta_forum_cx7_rdma_asymmetry_retest_01", "expect": "exit_zero", "porque": "Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

**DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01.** Un hilo atribuyó una caída direccional RDMA Write (Spark→ASUS GX10 ~13.2 Gbit/s frente a ~111.6 Gbit/s inversa) al kernel ASUS 6.17.0-1029 y reportó vuelta a 6.17.0-1026 ([379303](https://forums.developer.nvidia.com/t/379303)). La atribución pierde fuerza en el propio hilo: tras actualizar/reiniciar el mismo ASUS siguió en 1029 y `ib_write_bw` volvió a ~111.7 Gbit/s; un segundo dueño no reprodujo en Founder Edition. El problema reapareció una vez tras reiniciar y luego se restauró con reinicios de ambos GX10, mientras el propietario sospechó una condición de conectar el DAC con nodos encendidos; esa hipótesis no se controló y otro participante reporta diferencia con cable Amphenol frente a FS.com. No fijar kernel 1026 como workaround. En canary de CX7 compare direcciones en frío, tras reboot individual/secuencial y hotplug, guardando comando/perftest, cable/PN, fw CX7, kernel por OEM, interfaz/IP y estado PCIe/firmware. El resultado de ~13G es reporte temporal de operador; no se leyó issue/bundle externo.

Fuentes: tasks/backlog/FORUM-00-CX7-HOTPLUG-FAN-PROTECTION.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

### Evidencia de instrumento (2026-10-03)

Estado: `deferred_lab`. El inventario de red existente informa cero HCA RDMA, `ip link` inaccesible, conexión física `UNKNOWN` y transporte no probado. Falta retest bidireccional `ib_write_bw` entre ambos hosts fijados antes/después de reboot individual/secuencial y hotplug, con cable PN, CX7 fw y comandos/resultados. No se alteró host ni se generó tráfico. La ficha sigue abierta y `close_check` intacto. Informe: `docs/evidence/BB-INSTRUMENTS-feasibility-runtime.md`.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: Inventario informa cero HCA RDMA, ip link inaccesible y enlace físico UNKNOWN; falta retest bidireccional ib_write_bw en ambos hosts con reboot individual/secuencial.
- Evidencia faltante para cierre: Inventario informa cero HCA RDMA, ip link inaccesible y enlace físico UNKNOWN; falta retest bidireccional ib_write_bw en ambos hosts con reboot individual/secuencial.
- Siguiente acción: Coordinación BB: preparar captura/criterio de simetría; operador Luis: aportar ambos hosts CX7 y correr prueba bidireccional/reboots seguros con resultados literales. Ref explícita: tasks/backlog/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01.md y tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_09.json.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01.md`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01-original-selector-current.log`, `docs/evidence/BB-INSTRUMENTS-network.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_09.json`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.
