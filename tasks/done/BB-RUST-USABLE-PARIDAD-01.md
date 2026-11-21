---
id: BB-RUST-USABLE-PARIDAD-01
kind: task
title: "Reproducir las decisiones de bb-usable con Rust en modo observación"
status: done
closure_type: fixed
closed_at: 2026-11-21
severity: P2
origin: asserted
created: 2026-11-21
close_check: {"cmd": "bash -c 'base=\"$HOME/scratch/blackbox/$(date +%F)-usable-close-check\"; mkdir -p \"$base\"; lab=$(mktemp -d \"$base/run-XXXXXX\") && mkdir \"$lab/tmp\" \"$lab/evidence\" && CARGO_NET_OFFLINE=true CARGO_TARGET_DIR=\"$base/target\" TMPDIR=\"$lab/tmp\" BB_USABLE_TMP=\"$lab/tmp\" BB_USABLE_EVIDENCE=\"$lab/evidence\" systemd-run --user --scope -p MemoryMax=3G cargo test --locked --test usable_paridad'", "expect": "exit_zero"}
---

Depende de BB-RUST-CAPTURA-OBSERVACION-01. Reusar la [caracterización existente](../../tests/test_bb_usable_caracterizacion.py) y la [implementación](../../bin/bb-usable). Comparar decisiones con reloj, PSI y watchdog simulados.

- Probar racha sostenida, recuperación, atasco confinado y PSI ilegible antes y después del umbral. Registrar divergencias y revisar cada una.
- Control adverso: cualquier intento de señalar un proceso, cambiar unidades o tocar el watchdog real hace fallar la prueba.
- La prueba de hardware, instalación y cambio de autoridad quedan en la fase operativa del [plan](../../docs/PLAN-RUST.md).

## Resolución

Cerrada para observación offline. [Evidencia y revisión independiente](../evidence/BB-RUST-USABLE-PARIDAD-01/coordinacion/resolucion.md).
