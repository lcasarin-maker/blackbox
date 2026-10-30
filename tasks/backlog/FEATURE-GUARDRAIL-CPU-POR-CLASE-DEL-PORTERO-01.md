---
id: FEATURE-GUARDRAIL-CPU-POR-CLASE-DEL-PORTERO-01
kind: task
domain: CPU
title: "Ningun guardrail limita la CPU de un proceso o de una clase de trabajo: el portero topa memoria e io, pero no tiene ni una linea de CPU"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-30
close_check: {"cmd": "test -f tests/test_portero_cpu.py && python3 -m pytest -q -p no:cacheprovider tests/test_portero_cpu.py", "expect": "exit_zero", "porque": "Falla hoy: el archivo no existe. Pasa cuando el portero aplique y pruebe un tope de CPU por clase, con control negativo (sin tope un proceso de prueba satura el nucleo; con tope no)."}
---

## Que se midio (2026-10-30)

- `grep -nE 'cpu' tools/portero.py`: 0 coincidencias. Las clases del portero topan memoria e io (`memory_max_kb`, `io.max`), nada de CPU.
- `bin/bb-guardia-proceso` vigila el crecimiento de RSS de UN proceso, no su CPU. `tools/guardia_termico_predictivo.py` mira calor, no limita CPU.
- `systemctl show app.slice -p CPUQuotaPerSecUSec` = `infinity`; `/sys/fs/cgroup/app.slice/cpu.max` no existe.
- Ninguna muestra de CPU en `atom_gpu_telemetry.jsonl` (solo PSI de memoria). Si algo saturo la CPU antes de un corte duro, hoy no hay dato que lo diga ni lo niegue.
- Indicio debil en contra de saturacion sostenida antes de las caidas 2 a 4 del 2026-10-30: la temperatura de GPU, que comparte paquete con la CPU, quedo plana en 45 C hasta la ultima muestra de 5 s. No descarta una rafaga corta.

## Diseno (escalera ponytail)

1. Reuso: el portero ya crea un drop-in por prefijo de scope para topar memoria; el tope de CPU entra por el mismo mecanismo con `CPUQuota=` (nativo de systemd, ya soportado por el cgroup).
2. Primero medir: un muestreador de 1 s con CPU agregada y los 3 procesos que mas consumen, para fijar el umbral con datos y no a ojo (hoy no hay ninguno).
3. Interruptor `portero_cpu` con los tres modos de bb (`off` por defecto, `observar` registra `habria_limitado`, `actuar` aplica el tope). Sin pasar por `observar` no se activa.
4. Reservar nucleos para el sistema y el motor: el tope va por clase de trabajo de `app.slice`, no sobre `docker.slice` ni sobre el motor.

## No hacer

Poner `CPUQuota` global en `app.slice` sin datos: ahi corren OpenCode, el escritorio y las compilaciones, y se estrangularian sin evidencia de que la CPU sea la causa de nada.
