---
id: FEATURE-ATLAS-REMEDIR-EVAL-TRAS-REINDEXADO-01
kind: task
domain: HARDWARE
title: "Re-medir el eval de Atlas con la ATOM fria tras indexar el paquete GB10 y nombrar los 11 archivos sin entidad"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-13
close_check: {"cmd": "grep -q eval_atom_fria_remedido tasks/evidence/FEATURE-ATLAS-REMEDIR-EVAL-TRAS-REINDEXADO-01/medicion.txt", "expect": "exit_zero", "porque": "Al cerrar FEATURE-ATLAS-REINDEX-PAQUETE-GB10-01 el grafo de Atlas nombra 425 de 436 archivos entregados. Quedan 11 sin entidad propia y nadie ha re-medido el eval de Atlas con el indice nuevo y la ATOM fria. Cierra con una medicion en tasks/evidence/<id>/medicion.txt que liste los 11 archivos con su causa y el eval antes/despues, con la frase eval_atom_fria_remedido."}
---

## Origen
Resto declarado al cerrar `FEATURE-ATLAS-REINDEX-PAQUETE-GB10-01` (2026-10-13). El job de Atlas `reindex_paquete_gb10_20261013_retry` (commit 9a1ea7ce2 de Atlas) construyo el grafo; la medicion esta en `tasks/evidence/FEATURE-ATLAS-REINDEX-PAQUETE-GB10-01/e2e.txt`.

## Bloqueo
El eval vive en Atlas y exige la ATOM fria (sin motor vLLM cargado), es decir una ventana de Luis; los 11 archivos se listan leyendo el grafo de Atlas (solo lectura).
