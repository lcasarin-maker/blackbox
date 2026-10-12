---
id: FEATURE-ATLAS-RECOLECTOR-HALLAZGOS-BB-01
kind: task
domain: INCIDENT_CAPTURE
title: "Que Atlas recoja los hallazgos bb-hallazgo/1 de la bandeja de blackbox y los integre con su flujo"
status: open
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
