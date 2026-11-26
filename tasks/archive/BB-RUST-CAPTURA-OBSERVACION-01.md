---
id: BB-RUST-CAPTURA-OBSERVACION-01
kind: task
title: "Comparar un capturador Rust con el muestreo crítico existente"
status: done
closure_type: fixed
closed_at: 2026-11-21
severity: P2
origin: asserted
created: 2026-11-21
close_check: {"cmd":"cargo test --locked --test captura_observacion","expect":"exit_zero"}
---

En [muestreo](../../tools/muestreo_1s.py) y [último aliento](../../tools/ultimo_aliento.py), elegir la captura mínima que resulte útil durante presión de memoria. Reusar las interfaces de Linux y las fuentes de evidencia ya existentes. Emitir a un destino de prueba separado.

- Sobre entradas iguales, contrastar campos crudos, boot, timestamps y resultado. Registrar memoria máxima, latencia y pérdida de registros con los comandos y salidas.
- Control adverso: lecturas ilegibles, fuente atrasada y escritura fallida. El capturador declara el hueco y conserva cuanto se pudo recoger. Los límites de consumo y criterios de aceptación se fijan con la línea base antes de comparar.

## Resolución

Cerrada para observación offline. [Evidencia y revisión independiente](../evidence/BB-RUST-CAPTURA-OBSERVACION-01/coordinacion/resolucion.md).
