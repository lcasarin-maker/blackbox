---
id: FEATURE-1358-B1-CLOCK-EFECTIVO
kind: feature
title: "Verificar confirmación de aplicación del límite GPU"
status: done
reason: "Alcance local implementado y verificado; despliegue y calibración contra incidentes se declaran aparte. Evidencia integrada en verification.txt."
closed_at: 2026-10-02
evidence: {"pass": "tasks/evidence/SWARM-LUNA-1358-2026-10-02/verification.txt"}
closure_type: fixed
severity: P2
origin: asserted
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_1358_servicio_clock.py -k \"clock_lock\"", "expect": "exit_zero", "porque": "Comportamiento y controles negativos del alcance implementado, sin afirmar despliegue."}
---

## Contexto

Derivada de NVIDIA/open-gpu-kernel-modules#1358 y la comparación del 2026-10-02.

## Alcance

`bb status clock lock` compara rango declarado en ExecStart con la confirmación del driver en el journal del arranque actual, y exige que la confirmación sea posterior al inicio actual de la unit. Informa confirmación ausente, discrepante o vieja. ARMADO significa confirmación de aplicación tras inicio; el driver no expone el clock actual por esta vía. No despliega ni cambia frecuencias.

## Verificación y límite

`python3 -m pytest -q tests/test_1358_servicio_clock.py`: 13 passed. Hay controles para ausencia, rango discrepante, confirmación anterior al reinicio de la unit y confirmación actual.

Límite: el resultado demuestra evidencia registrada de aplicación del rango; no verifica la frecuencia efectiva en vivo ni la respuesta térmica de la GPU. El mock de systemd/journal valida la lógica, no el formato de todas las versiones instaladas.
