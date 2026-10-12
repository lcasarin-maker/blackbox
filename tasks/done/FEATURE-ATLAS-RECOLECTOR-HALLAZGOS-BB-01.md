---
id: FEATURE-ATLAS-RECOLECTOR-HALLAZGOS-BB-01
kind: task
domain: INCIDENT_CAPTURE
title: "Que Atlas recoja los hallazgos bb-hallazgo/1 de la bandeja de blackbox y los integre con su flujo"
status: done
closed_at: 2026-10-11
evidence:
  pass: tasks/evidence/FEATURE-ATLAS-RECOLECTOR-HALLAZGOS-BB-01/pass.txt
  fail: tasks/evidence/FEATURE-ATLAS-RECOLECTOR-HALLAZGOS-BB-01/fail.txt
  e2e: tasks/evidence/FEATURE-ATLAS-RECOLECTOR-HALLAZGOS-BB-01/e2e.txt
closure_type: relocated_prior_verification
reason: "el codigo vive en el repo de Atlas (commit 21dbc9308: tools/recoge_hallazgos_bb.py, clase bb_hallazgo en tools/index_cosecha_dictamenes.py, tests/test_recoge_hallazgos_bb.py) y blackbox no cambia de codigo en el commit que mueve esta ficha. Verificado con el close_check en las dos direcciones (rc=1 antes, rc=0 despues) y e2e sobre la bandeja real."
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "grep -rq blackbox/hallazgos /home/lcasarin/projects/Atlas/tools", "expect": "exit_zero", "porque": "Elegido por Luis el 2026-10-11: blackbox publica hallazgos en ~/.local/share/blackbox/hallazgos/ y Atlas los recoge. Pasa cuando algun archivo de Atlas/tools lee esa bandeja; hoy ninguno lo hace y los hallazgos esperan alli."}
---

## Esquema

`bb-hallazgo/1`, definido y validado en `tools/hallazgo.py` de blackbox: frontmatter con comillas (`esquema`, `id`, `prov:generatedAtTime`, `prov:wasAttributedTo`, `prov:wasGeneratedBy`, `tipo`, `confianza`, `nodo`, `datos`, `atlas_refs`) y las dos secciones literales del contrato de hallazgos de Atlas. El test `test_hallazgo_cumple_el_contrato_de_atlas` valida un hallazgo con el `_contract_violations` y el `split_frontmatter` reales de Atlas.

## Lo que debe hacer el recolector (lado Atlas, su flujo, sus tests)

1. Leer, solo lectura, `~/.local/share/blackbox/hallazgos/*.md`; validar con `_contract_violations`.
2. Escribir el dictamen en `docs/agent_findings/AAAA-MM-DD_<slug>.md` con el prefijo de fecha que Atlas usa para su procedencia, y **indexarlo** (`tools/index_cosecha_dictamenes.py`): `tests/test_findings_indexed.py` exige que cada dictamen este indexado y se puso en rojo dos veces por no hacerlo.
3. Idempotente por `id`: estado propio de Atlas (no se escribe nada en la bandeja de blackbox).
4. Marcar el dictamen como derivado (ya lo hace `is_derived_source` para `docs/agent_findings/`).

## Estado

Hoy hay 11 hallazgos esperando en la bandeja: los 10 reinicios medidos y la medicion del efecto del cap de 2100 MHz. blackbox ya publica uno por cada boot terminado (`bb reboots --escribe`, timer `bb-reboot-verdict`).

## CERRADA 2026-10-11 -- el recolector aterrizo en Atlas (commit 21dbc9308, sin push)

### Root Cause

Atlas no tenia ningun lector de la bandeja de blackbox: los hallazgos `bb-hallazgo/1` se acumulaban (12 al cerrar, no 11: llego el del boot 54b71618) sin que ningun flujo de Atlas los recogiera, y `tests/test_findings_indexed.py` habria exigido indexar cada uno al entrar a `docs/agent_findings/`.

### Regression Test

`tests/test_recoge_hallazgos_bb.py` en Atlas (13 casos). Controles negativos corridos: sin `_contract_violations` fallan 3 casos de rechazo; con `ruta.exists()` anulado falla la idempotencia; sin la clase en `CLASES` fallan 2; sin `docs/INDEX_BB_HALLAZGO.md` `test_ningun_dictamen_nuevo_queda_sin_indexar` nombra los 12 dictamenes. Cada regla de rechazo (esquema, valor sin comillas, fecha sin comillas, falta de cada seccion, sin cita, id mal formado, sin frontmatter, nombre distinto del id) tiene su caso.

### Verification Evidence

`tasks/evidence/FEATURE-ATLAS-RECOLECTOR-HALLAZGOS-BB-01/{fail,pass,e2e}.txt`. Dos limites declarados: (1) el `close_check` es un grep de la cadena `blackbox/hallazgos` y se satisface con cualquier mencion; la prueba de que el recolector funciona es el e2e y el test, no ese grep. (2) El recolector es una herramienta que se invoca (`.venv/bin/python3 -m tools.recoge_hallazgos_bb`); no se cableo al `liberation_watchdog` ni a un timer, asi que los hallazgos futuros esperan hasta que alguien (o un job de la cola) la corra. Eso es una decision de Atlas sobre su propia cola y no se tomo aqui.
