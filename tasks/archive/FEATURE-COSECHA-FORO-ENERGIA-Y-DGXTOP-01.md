---
id: FEATURE-COSECHA-FORO-ENERGIA-Y-DGXTOP-01
kind: task
domain: GPU
title: "Evaluar las ideas de los hilos de energia (384499) y dgxtop v2 (385664) para frenar los cortes termicos"
status: done
closed_at: 2026-10-13
closure_type: relocated_prior_verification
reason: "Las 15 ideas de la cosecha tienen veredicto con su prueba y control negativo en evaluacion.txt; el guardia predictivo (paso 1) ya esta en observar y la medicion nueva (148480 muestras: la zona mas caliente supera a gpu_temp_c en mediana 8.1 C y hasta 40.1 C) decide que el tope se pone sobre la zona. Lo que queda por medir (rampa de reloj, tope de CPU, num-gpu-blocks-override, acantilado de swap) vive en sus fichas propias."
evidence: {"pass": "tasks/evidence/FEATURE-COSECHA-FORO-ENERGIA-Y-DGXTOP-01/pass.txt", "fail": "tasks/evidence/FEATURE-COSECHA-FORO-ENERGIA-Y-DGXTOP-01/fail.txt", "e2e": "tasks/evidence/FEATURE-COSECHA-FORO-ENERGIA-Y-DGXTOP-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q cosecha_evaluada tasks/evidence/FEATURE-COSECHA-FORO-ENERGIA-Y-DGXTOP-01/evaluacion.txt", "expect": "exit_zero", "porque": "Cada idea de cosecha.txt lleva veredicto (adoptar, descartar, medir primero) con su prueba y control negativo; hoy no existe evaluacion.txt."}
---

## Por que
El corte en seco del 2026-10-12 18:32 llego con la zona ACPI mas caliente a 96.3 C, vLLM al 96 % y bb en `sostenida` 40 s antes; en los 3 cortes con telemetria la zona marcaba 95.7-98.0 C en la ultima muestra. bb mide y avisa; no actua sobre el reloj ni sobre vLLM. Dos hilos del foro de NVIDIA publican ideas para eso y bb no las habia cosechado.
## Que hay
`tasks/evidence/FEATURE-COSECHA-FORO-ENERGIA-Y-DGXTOP-01/cosecha.txt`: ideas de djmad/Spark_Energy_Management (CC BY-NC: solo ideas, no codigo) y de DennySORA/dgxtop (Apache-2.0: codigo reutilizable con atribucion), hilos relacionados sin leer y el hueco del colector (el hilo 384499 tenia un id menor que los cosechados y no estaba).
## Plan (cada paso con interruptor off/observar/actuar y medicion antes de decidir)
1. Guardia termico predictivo en `observar`: tendencia de zonas a 2 s y velocidad de subida contra el tope de 96 C; registra cuando habria actuado, sin actuar. Se compara contra los 3 cortes con telemetria (debe haber disparado antes).
2. Historial por proceso con motivo de fin y pico de memoria GPU (idea de dgxtop; la memoria GPU por cgroup ya se mide exacta con dmem: 0.005 % contra nvidia-smi).
3. Rampa de carga y tope de reloj: sigue en `FEATURE-FORUM-GPU-CLOCK-CAP-AB-01`; esta ficha aporta el diseno de rampa (100 MHz/s con GPU >=75 %).
4. Leer los hilos relacionados (NVML con memoria unificada, nvtop con memoria unificada, nvidia-smi roto).
5. Arreglar la cobertura del colector de foros por id (DEBT-RESEARCH-COLLECTOR-BB-FORUM-INVENTORY-01).
6. HECHO 2026-10-12: `tools/guardia_termico_predictivo.py` en `observar` (unidad `systemd/bb-vigilante-termico.service`, sin instalar: decision de Luis). La repasada mide que la regla corta no sirve (0-76 s de aviso) y que la de acumulacion de calor avisa 11.8 min antes del ultimo corte pero dispara tambien en arranques sin corte; falta etiquetar como termino cada arranque.
7. Riesgo medido: Docker usa cgroup `systemd` (hilo 352743). Ficha propia: DEBT-DOCKER-CGROUP-SYSTEMD-RECARGA-QUITA-GPU-01.
8. Tras cada corte correr `sudo ras-mc-ctl --errors` y guardar la salida (hilo 372486; rasdaemon ya esta instalado).
9. Anadir `--num-gpu-blocks-override` a la propuesta vLLM y vigilar el acantilado de swap (hilo 358869: 0 GiB de swap 37 tok/s, 13 GiB 1.8 tok/s).
## No se hace
Ventiladores: NVIDIA no documenta metodo soportado y el controlador embebido no esta probado en esta placa. Instalar el controlador de djmad: sin revision de su codigo, con licencia no comercial y probado en otro equipo.

## Avance 2026-10-13: cierre
`tasks/evidence/FEATURE-COSECHA-FORO-ENERGIA-Y-DGXTOP-01/evaluacion.txt`: 15 ideas, cada una con veredicto (adoptar, descartar o medir primero), prueba y control negativo. Medicion nueva sobre `atom_gpu_telemetry.jsonl`: zona_max menos gpu_temp_c, mediana +8.1 C, rango -4.9 a +40.1 C en 148480 muestras.

## Root Cause
La ficha estaba abierta porque la cosecha no tenia evaluacion por idea; se escribio una y se midio la divergencia de sensores que faltaba.

## Regression Test
`tests/test_guardia_termico_predictivo.py` y `tests/test_gpumem_historial.py` (36 passed el 2026-10-13); el `close_check` exige el marcador `cosecha_evaluada` en `evaluacion.txt`.

## Verification Evidence
fail.txt: el close_check sobre un archivo ausente sale 2; pass.txt: sobre evaluacion.txt sale 0; e2e.txt: 15 ideas numeradas con veredicto.
