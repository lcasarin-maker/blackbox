---
id: FEATURE-1358-B2-CAPTURA-TRANSICION
kind: task
domain: GPU
title: "PSI en telemetría rápida existente"
status: done
reason: "La captura PSI local se implementó y verificó; su utilidad durante cuelgues nuevos queda por medir."
closed_at: 2026-10-02
evidence: {"pass": "tasks/evidence/FEATURE-1358-B2-CAPTURA-TRANSICION/pass.txt", "fail": "tasks/evidence/FEATURE-1358-B2-CAPTURA-TRANSICION/fail.txt", "e2e": "tasks/evidence/FEATURE-1358-B2-CAPTURA-TRANSICION/e2e.txt"}
satd_family: BLIND_INSTRUMENT
closure_type: fixed
severity: P2
origin: asserted
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_1358_telemetria.py -k \"psi_memory or muestra\"", "expect": "exit_zero", "porque": "Comportamiento y controles negativos del alcance implementado, sin afirmar despliegue."}
---

## Contexto

Derivada de NVIDIA/open-gpu-kernel-modules#1358 y la comparación del 2026-10-02.

## Alcance

Se añadió PSI de memoria `some` y `full` (avg10/avg60/avg300/total) al productor GPU existente, leyendo `/proc/pressure/memory` sin procesos adicionales. Grupos ausentes y valores inválidos quedan visibles. Se conserva la cadencia configurada de 5 s del productor. Ya existe una muestra ligera de `bin/bb` cada 2 s durante 50 s ante PSI>=10 o caída de RAM>=8 GB; esta ficha no duplica esa captura.

No hay evidencia comparativa que muestre que capturar a 1 Hz aporte información suficiente para justificar más I/O y tamaño de registro. Se mantiene el muestreo existente. Reabrir la decisión si una reproducción rápida documenta que los hitos relevantes caben dentro del intervalo efectivo de 2 s y que la ráfaga actual los pierde.

## Verificación y límite

Cierre local: PSI se incorpora en cada muestra de 5 s y los errores de lectura quedan explícitos. Las pruebas no validan la captura en un cuelgue real ni miden la cobertura temporal de la ráfaga de 2 s. El valor diagnóstico añadido en incidentes nuevos sigue sin calibrar.

## Root Cause

El productor rápido existente registraba uso GPU sin incluir el PSI de memoria del kernel. Añadir esa lectura amplía la observación para comparar presión con la actividad GPU; no demuestra que PSI cause los incidentes.

## Regression Test

`tests/test_1358_telemetria.py` comprueba los campos PSI `some`/`full`, valores inválidos y ausentes, y su integración en la muestra existente.

## Verification Evidence

Salidas reales de pytest: `tasks/evidence/FEATURE-1358-B2-CAPTURA-TRANSICION/{pass,fail,e2e}.txt`. El uso durante un cuelgue real sigue pendiente.
