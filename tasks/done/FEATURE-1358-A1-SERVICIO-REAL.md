---
id: FEATURE-1358-A1-SERVICIO-REAL
kind: feature
title: "Respuesta útil del servicio frente a TCP abierto"
status: done
reason: "Alcance local implementado y verificado; despliegue y calibración contra incidentes se declaran aparte. Evidencia integrada en verification.txt."
closed_at: 2026-10-02
evidence: {"pass": "tasks/evidence/SWARM-LUNA-1358-2026-10-02/verification.txt"}
closure_type: fixed
severity: P2
origin: asserted
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_1358_servicio_clock.py -k \"not clock_lock\"", "expect": "exit_zero", "porque": "Comportamiento y controles negativos del alcance implementado, sin afirmar despliegue."}
---

## Contexto

Derivada de NVIDIA/open-gpu-kernel-modules#1358 y la comparación del 2026-10-02.

## Alcance

Añadir comprobación opcional y acotada de banner SSH o reutilizar endpoint con respuesta útil. Solo observación; sin activar reinicios por señal sin calibrar. Integrar en bb sample y declarar ausencias/error/timeout.

## Verificación y límite

`python3 -m pytest -q tests/test_1358_servicio_clock.py`: 13 passed. `bin/bb sample` registra `servicio_ssh` como DESACTIVADO si falta puerto; al configurarlo, solo admite loopback, valida un banner SSH completo y limita conexión más lectura a 0.05–10 s. Los controles cubren TCP conectado sin banner, flujo lento dentro de un plazo total, respuesta válida, prefijo incompleto, identificación demasiado larga, destino externo rechazado y JSON de muestra.

Límite: no se hizo conexión real porque el sandbox bloquea sockets. La sonda permanece desactivada por defecto y no participa en decisiones ni reinicios. La calibración del endpoint del operador queda pendiente.

## Verificación adicional del coordinador

El 2026-10-02 la sonda real en loopback devolvió `OK`, 44 ms. Comando y salida en `tasks/evidence/SWARM-LUNA-1358-2026-10-02/host-checks.txt`. Esto comprueba respuesta sana actual; calibrar contra un incidente continúa pendiente.
