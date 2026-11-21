# Relevo

2026-11-21: el lector común `tools/reboot_ledger.py` valida anulaciones por
línea y `boot_id`, conserva las filas originales y aplica la última reposición
válida. `_ya_escritos`, `leer_veredictos`, `arranque_anterior` y `bb status`
lo reutilizan. El contrato operativo pasa en solo lectura; la ficha
`DEBT-REBOOTS-JSONL-DOS-FILAS-ERRONEAS-SIN-CORRECCION-01` permanece abierta en
`tasks/backlog/` hasta aterrizar el lector externo. No se hizo push ni merge.

Actualización del 2026-11-21. Después de ese relevo, la integración del lector externo en Orcaestrator quedó registrada en la [ficha cerrada](tasks/done/DEBT-REBOOTS-JSONL-DOS-FILAS-ERRONEAS-SIN-CORRECCION-01.md).
