# Sesión 2026-11-21 — rectificaciones de `reboots.jsonl`

- Objetivo: aplicar el contrato de rectificaciones append-only en Blackbox y
  dejar abierta la ficha hasta el aterrizaje del lector externo.
- OWNS: `tools/reboot_ledger.py`, consumidores de `reboots.jsonl` en Blackbox,
  `bin/bb`, pruebas y evidencia de esta ficha. Sin cambios en `aequitax` ni
  `[dato-local]_os`.
- Control rojo: la anulación con referencia a otro boot falló antes con
  `{'x2'} == {'x1', 'x2'}`.
- Verificación final: `274 passed in 135.83s (0:02:15)` bajo
  `systemd-run --user --scope --quiet -p MemoryMax=4G`.
- Ledger operativo: solo lectura; hash antes/después
  `c898f917b32bc40469bc1e65a09f9f36f9b5a54cce7048e7004d393b4737e686`.
- Publicación: sin push ni merge.
- Estado de ficha: `tasks/backlog/DEBT-REBOOTS-JSONL-DOS-FILAS-ERRONEAS-SIN-CORRECCION-01.md`,
  `status: open`; el contrato operativo pasa, falta el consumidor externo.
