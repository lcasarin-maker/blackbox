---
id: FEATURE-COSECHA-FORO-ENERGIA-Y-DGXTOP-01
kind: task
domain: GPU
title: "Evaluar las ideas de los hilos de energia (384499) y dgxtop v2 (385664) para frenar los cortes termicos"
status: open
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
## No se hace
Ventiladores: NVIDIA no documenta metodo soportado y el controlador embebido no esta probado en esta placa. Instalar el controlador de djmad: sin revision de su codigo, con licencia no comercial y probado en otro equipo.
