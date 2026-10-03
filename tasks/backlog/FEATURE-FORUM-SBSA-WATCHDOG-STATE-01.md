---
id: FEATURE-FORUM-SBSA-WATCHDOG-STATE-01
kind: task
domain: RECOVERY
title: "Verificar disponibilidad y propietario del watchdog en lugar de inferirlos"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FEATURE-FORUM-SBSA-WATCHDOG-STATE-01 --evidence tasks/evidence/FEATURE-FORUM-SBSA-WATCHDOG-STATE-01", "expect": "exit_zero", "porque": "Verificador propuesto pendiente: requiere evidencia del caso positivo, controles negativos, compatibilidad OEM y recuperación/rollback; la ficha registra trabajo abierto."}
---

## Fuente y evidencia

[360564](https://forums.developer.nvidia.com/t/360564). El hilo relata resets incluso durante FieldDiag y una respuesta muestra SBSA timeout 10s. El autor afirma lsmod vacío y estabilidad posterior sin explicar acción ni duración. La causalidad sigue pendiente; un driver built-in puede faltar de lsmod.

## Delta y prevención/resolución

bb status lee RuntimeWatchdogUSec; ese valor configurado requiere corroboración del dispositivo y propietario efectivos.

Reutilizar sysfs/watchdog, logs systemd, configuración kernel y wdctl cuando sea seguro para el propietario actual. Registrar identidad, timeout y ownership sin abrir un dispositivo que altere su estado. Mantener la recuperación vigente; deshabilitar watchdog requiere diagnóstico OEM y canary específico.

## Validación, riesgo y cierre

driver built-in, módulo, dispositivo ausente, permiso denegado y propietario activo. Correlacionar boot/pstore antes de cambiar política; cualquier experimento conserva timeout previo, vigilancia, caducidad y recuperación.

El verificador de close_check todavía debe implementarse; ejecutar esta ficha exige evidencia adicional y deja registradas las consultas que no pueden correr. Ningún cambio del host se aplica al registrar la propuesta. Detalle fuente preservado en tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_*.json y threads/.


## Estado de publicación de esta investigación

Propuesta abierta. Los comandos de cierre describen el verificador y evidencia requeridos; esta rama publica investigación y fichas, sin implementación ni resultados de ejecución de los mecanismos propuestos.
