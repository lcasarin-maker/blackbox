---
id: FEATURE-MEMORYSAVER-03-INTEGRIDAD
kind: task
domain: GPU
title: "Trasladar matriz acotada de integridad y reutilización CUDA"
status: done
reason: "La matriz CUDA pequeña pasó lectura completa, liberación alterna y reutilización de huecos en cuatro workers con 16 MiB agregados. Los controles negativos detectan corrupción y verifican liberación segura ante fallos."
closed_at: 2026-10-02
evidence: {"pass": "tasks/evidence/FEATURE-MEMORYSAVER-03-INTEGRIDAD/pass.txt", "fail": "tasks/evidence/FEATURE-MEMORYSAVER-03-INTEGRIDAD/fail.txt", "e2e": "tasks/evidence/FEATURE-MEMORYSAVER-03-INTEGRIDAD/e2e.txt"}
closure_type: fixed
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.cuda_integrity && python3 -m pytest -q tests/test_memory_capture_and_cuda_integrity.py tests/test_cuda_integrity_cli.py", "expect": "exit_zero", "porque": "Ejecuta el e2e CUDA acotado y todos los controles de corrupción, huecos, liberación, preservación de errores, alcance systemd y detalles de cleanup."}
---

## Fuente y dependencias

[Memory Saver](https://github.com/christopherowen/dgx-spark-memory-saver), commit `55816f0b5c88bbab3c0641f9d6f1d9fd36e5854d`. Revisión local: `tasks/evidence/MEMORY-SAVER-REVIEW-2026-10-02/review.txt` y `code-review.txt`. Dependencias: FEATURE-1358-CGROUP-01-REPRO. Dueño: coordinación de Blackbox; ejecución por asignar en la siguiente ola.

## Alcance

Reutilizar el arnés de Blackbox y los patrones de validación publicados: asignación concurrente, liberación de huecos y reutilización, llenado y readback de todo el buffer, transferencia host/device y sincronización antes de reutilizar. Mantener memoria agregada y duración acotadas; conservar los límites del ensayo pequeño actual. Distinguir reserva, residencia y caché del allocator PyTorch; comprobar liberación por fase. Referenciar los programas originales y su licencia antes de copiar código. Las pruebas grandes de 4.5 GiB, CUDA graphs y BF16 son referencias de una matriz ampliada para otra ventana, no ejecuciones implicadas por esta ficha. Sirve a los criterios de seguridad de FEATURE-1358-CGROUP-04-PARCHE y de comparación de 05.

## Criterio de cierre

Control sano con bytes conocidos y readback completo correcto, control negativo con bytes deliberadamente alterados que el verificador detecte, repetición/reutilización en al menos dos workers con techo agregado y timeout efectivo. Registrar errores CUDA y cleanup en rutas de fallo. Comparar stock/candidato solo cuando exista candidato validado; separar tests unitarios de pruebas GPU y declarar todos los casos no ejecutados.

## Cierre — 2026-10-02

E2E en `tasks/evidence/FEATURE-MEMORYSAVER-03-INTEGRIDAD/runtime.txt`: cuatro
workers, máximo agregado 16 MiB, cuatro rondas; el sujeto llenó, leyó por
completo, liberó slots alternos, reutilizó huecos con vecinos vivos y volvió a
leer todo. Las 22 pruebas cubren byte alterado/truncado, fallo de asignación,
fallo de free sin reintento incierto y limpieza del resto mientras se preserva
el error inicial. Ruff y Pyright pasan según `verification.txt`. Cubre el
ensayo pequeño en esta pila, no la matriz grande ni el parche candidato.

## Root Cause

La referencia del parche incluía lectura completa, concurrencia y reutilización
de slots, pero el ensayo disponible en Blackbox solo comparaba cargos de
asignación. Sin readback y huecos concurrentes, corrupción por alias o una
liberación incierta quedaban sin observación.

## Regression Test

`tests/test_memory_capture_and_cuda_integrity.py` comprueba patrones completos,
mutación, truncado, reutilización con slots vecinos vivos y errores inyectados de
asignación/liberación. Los fallos de free no se repiten; el cleanup continúa con
los demás buffers y conserva la excepción primaria y sus notas.

## Verification Evidence

E2E acotado y salidas literales en
`tasks/evidence/FEATURE-MEMORYSAVER-03-INTEGRIDAD/{pass,fail,e2e}.txt`.
Memory Saver y su parche no se instalaron.
