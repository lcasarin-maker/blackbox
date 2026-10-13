---
id: DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01
kind: task
domain: VERDICT
title: "Validar forum cx7 physical topology alias check 01"
status: done
closed_at: 2026-10-13
closure_type: void_wontfix
reason: "Requiere malla switchless de cuatro nodos con ConnectX-7 y cambios MFT; este equipo es un nodo unico sin CX7 en pareja (/sys/class/infiniband ausente) y tools/huella_host.py ya registra driver por interfaz. Decision de Luis 2026-10-13: deprecar por aplicabilidad, con independencia de la nota del 2026-10-11 (que dejaba abiertas las fichas con xfail porque un xfail no verifica nada)."
evidence: {"pass": "tasks/evidence/DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01/pass.txt", "fail": "tasks/evidence/DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01/fail.txt", "e2e": "tasks/evidence/DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01.md", "expect": "exit_zero", "porque": "Cerrada por aplicabilidad (void_wontfix, decision de Luis 2026-10-13): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a un test por ficha que se retiro con la deprecacion."}
---

## Registro y responsable

Registro solicitado por Luis el 2026-10-02. Responsable: coordinación de Blackbox. Trabajo o revisión pendiente; la presencia del marcador no demuestra por sí sola un defecto.

## Evidencia y alcance

Trabajo separado del ámbito de su ficha madre, conservando la fuente original. Los reportes de foro siguen sin validación local y no se convierten en recomendaciones automáticas.

[368726](https://forums.developer.nvidia.com/t/368726) records a failed four-node switchless ConnectX-7 lane-split experiment: after MFT/MFT firmware configuration created an additional interface, the author found F2 aliased to F0 and able to pass traffic despite no physical connection; the mesh proposal was abandoned. A separate owner later says a four-node ring worked with custom networking/vLLM patches at a 10–20% performance cost, but the repository was not audited. Add an exact-OEM preflight after any CX7 lane/MFT changes that maps PCI BDF ↔ physical connector ↔ netdev and proves each intended link by disconnect/loopback control and sustained peer traffic, then runs NCCL collectives on the intended topology before workload admission. Preserve BIOS/MFT state, Secure Boot implications and recovery path; never infer physical paths from visible interfaces or adopt the community split commands as a supported fix. **DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01**.

Fuentes: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md.

## Criterio de cierre y control negativo

Aplicar el alcance y los controles concretos de la evidencia copiada arriba: stack/OEM y versiones fijadas, sujeto real, caso sano y negativo, resultados literales y rollback cuando haya intervención. Si faltan hardware, adjuntos, compatibilidad o permisos, imprimir could_not_run y conservar open. Un score agregado o mero estado de un dispositivo no acredita el resultado funcional. No instalar parches ni provocar fallo del host para registrar la ficha.

## Estado del verificador

La ficha permanece abierta. El test selector del close_check es una especificación pendiente, no una prueba existente ni un resultado ejecutado. Implementarlo exige comprobar el sujeto y su control negativo; la existencia de archivos o esta ficha no basta para cerrar.

Conservar comandos, salida literal y could_not_run incluso cero; una ejecución skipped o inaccesible deja el cierre pendiente. Reutilizar instrumentos nativos y pruebas existentes antes de crear código.

## Avance de instrumentación 2026-10-03

El inventario correlaciona netdev con BDF/vendor/device/driver disponibles en sysfs. La conexión física permanece `UNKNOWN`: una ruta PCI no demuestra cable, conector ni alias bajo control de enlace. La consulta `ip -j link` no pudo abrir netlink en esta captura. Evidencia: [BB-INSTRUMENTS-network](../../docs/evidence/BB-INSTRUMENTS-network.md). La ficha permanece abierta; `close_check` y `status` no cambiaron.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `hardware_or_peer`.
- Impedimento: Sysfs correlaciona netdev/BDF pero la conexión física sigue UNKNOWN; netlink no se pudo consultar y PCI no prueba cable/alias.
- Evidencia faltante para cierre: OEM/NIC/topología y firmware; identificación física de lanes/puertos; tráfico por cada ruta y control desconectado; rollback.
- Siguiente acción: Solicitar al dueño del CX7 mapa de lanes/puertos, captura de tráfico por puerto y control físico desconectado/reconectado sobre topología de cuatro nodos.
- Responsable del siguiente paso: BB; operador Luis para hardware/peer.
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01.md`, `docs/evidence/BB-INSTRUMENTS-network.md`, `tools/hardware_batch02_controls.py`, `tools/host_diagnostics.py`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Estado (2026-10-11, /0 + /vote)

Bloqueada por criterio sin implementar: el `close_check` de esta ficha termina en `xfailed` y por eso sale con codigo 0 sin que el criterio real exista. Un `xfail` no es una verificacion y cerrar con el no es cierre. Cerrarla exige implementar la prueba real contra el sujeto (vLLM, NCCL, CX7 u otro hardware) con su control negativo. Decision del dueno el 2026-10-11: dejarla abierta y declarada, no cerrarla como `void_wontfix`.

## Root Cause
No aplica a este equipo: Malla de cuatro nodos con CX7 y MFT; este equipo no tiene CX7 en pareja ni cables que mapear. huella_host ya registra firmware CX7 y driver por interfaz. (aplicabilidad otro_hardware, utilidad baja).

## Regression Test
Ninguno: la ficha se depreca por no tener sujeto aqui. Los tests que la vigilaban (`test_delta_forum_cx7_physical_topology_alias_check_01`) se retiran o dejan de parametrizarla, junto con sus entradas de `tests/known_failures.json`.

## Verification Evidence
Tres rutas del frontmatter: `fail` (el close_check era un xfail), `pass` (perfil medido del equipo: sin dispositivos InfiniBand, un solo contenedor vLLM, sin Ray ni llama.cpp RPC) y `e2e` (la clasificacion). Para reabrirla si el equipo cambia (otro nodo, CX7 en pareja, otro modelo): `git mv tasks/done/DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01.md tasks/backlog/` y `status: open`.
