---
id: DEBT-RUST-USABLE-PARIDAD-MAPA-MEMORIA-01
kind: task
domain: MEMORY
title: "Actualizar el prototipo Rust usable_paridad tras añadir el mapa de memoria al declarar colapso en bb-usable"
status: open
severity: P2
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-26
close_check: {"cmd": "cargo test --locked --test usable_paridad", "expect": "exit_zero", "porque": "Tras el commit 95e31d82 (FEATURE-MAPA-DE-MEMORIA-AL-DECLARAR-COLAPSO-01), bin/bb-usable y tests/test_bb_usable_caracterizacion.py añadieron el mapa de memoria al declarar colapso, pero tests/usable_paridad.rs sigue comparando contra la caracterización previa y falla en 5 casos (confinado_habria_acariciado, ilegible_con_colapso_declarado, racha_hasta_colapso, recuperacion_tras_bajas, una_baja_no_absuelve_colapso)."}
---

## Medido (2026-11-26)

Al auditar `BB-RUST-USABLE-PARIDAD-01` durante `/debt`, `cargo test --locked --test usable_paridad` falló en `close_check_runs_subject_and_negative_in_private_bwrap` con `rc=101` (`1 passed; 1 failed; 1 ignored`): 5 de los casos de `tests/usable_paridad.rs` divergen de la caracterización actual de `bin/bb-usable` tras `95e31d82`.

## Qué hacer

1. Decidir si el prototipo Rust `usable_paridad` incorpora el contrato de mapa de memoria o si se archiva/retira conforme a la política de paridad.
2. Si se mantiene, actualizar `usable_paridad` y verificar `cargo test --locked --test usable_paridad` con control negativo intacto.
