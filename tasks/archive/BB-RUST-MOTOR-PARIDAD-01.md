---
id: BB-RUST-MOTOR-PARIDAD-01
kind: task
title: "Evaluar una migración parcial del control del motor sin dos actuadores"
status: done
closure_type: void_wontfix
closed_at: 2026-11-21
reason: "Se evaluó el rebase del cribado sintético. La medición y la auditoría no encontraron una causa atribuible al lenguaje bajo carga representativa."
severity: P3
origin: asserted
created: 2026-11-21
close_check: {"cmd":"cargo test --locked --test contrato_control_motor","expect":"exit_zero"}
---

Trabajo condicionado a una necesidad medida. Comparar [el vigilante](../../bin/bb-vigilante-motor), [solicitudes](../../tools/motor_solicitudes.py) y [política de reinicios](../../tools/workload_restart_policy.py) antes de abrir una implementación. Si la evidencia no justifica el cambio, registrar descarte con la medición bajo el flujo del backlog.

- Mantener el formato `bb-motor-solicitud/1` y el mismo resultado para solicitudes válidas, repetidas y caducadas. Contrastar ventana vigente, compensación y tope alcanzado con actuador simulado.
- Control adverso: petición fuera de alcance, intento duplicado y actuador real inaccesible. El vigilante autorizado conserva la exclusividad durante toda comparación.

## Resolución de la condición

Migración descartada por ahora. Se ejercitaron el control y sus contratos con sujetos actuales, testigos sintéticos y auditoría de solo lectura. El `close_check` de portada se conserva para una futura implementación condicionada. El [dictamen de descarte](../evidence/BB-RUST-MOTOR-PARIDAD-01/coordinacion/resolucion.md) contiene mediciones, controles, causa y disparadores de reapertura. La redacción original queda en el historial de Git.
