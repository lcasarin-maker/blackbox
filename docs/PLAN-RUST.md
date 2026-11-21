# Plan de trabajo de Blackbox

Plan de implementación iniciado sobre `8138339c`. El [inventario de funciones](../SPEC.md#inventario-de-funciones) define los instrumentos y sus contratos. El objetivo es conservar evidencia y reducir dependencias en los caminos que se usan cuando la ATOM ya está bajo presión.

| Fase | Entrega | Criterio de avance |
| --- | --- | --- |
| 1. Captura en observación | [BB-RUST-CAPTURA-OBSERVACION-01](../tasks/done/BB-RUST-CAPTURA-OBSERVACION-01.md) | Comparación con el muestreador actual sobre las mismas entradas. Capacidad de guardar evidencia y de declarar fuentes ilegibles, atrasadas o incompletas. |
| 2. Usabilidad y watchdog en observación | [BB-RUST-USABLE-PARIDAD-01](../tasks/done/BB-RUST-USABLE-PARIDAD-01.md) | Después de la fase 1, reproducir las decisiones de `bb-usable` con reloj y watchdog simulados. Todo cambio del actuador requiere autorización y reversión ensayada. |
| 3. Control del motor | [BB-RUST-MOTOR-PARIDAD-01](../tasks/done/BB-RUST-MOTOR-PARIDAD-01.md) | Sólo tras medir un motivo para migrar. Reproducir el contrato de solicitudes, ventanas y topes con el actuador simulado. |

Rust se propone para captura y protección crítica. systemd y Linux conservan los límites, la supervisión y los mecanismos de captura del kernel. Python conserva informes, calibración, veredictos, publicación de hallazgos y el [testigo externo](../tools/testigo/LEEME.md). Se mantiene [el contrato de reinicios](../tools/reboot_ledger.py) para los consumidores.

El estado operativo del watchdog y su prueba en máquina se siguen en las fichas existentes [inactividad](../tasks/backlog/DEBT-BB-USABLE-INACTIVO-DEJA-CIEGO-EL-WATCHDOG-01.md) y [prueba de hardware](../tasks/backlog/DEBT-WATCHDOG-SIN-CONTROL-NEGATIVO-01.md). Una comparación con datos grabados no acredita ese ensayo. Captura y paridad quedaron cerradas en observación offline. La evaluación del motor descartó su migración por ahora. Los cambios de servicio se deciden con mediciones y revisión independiente.
