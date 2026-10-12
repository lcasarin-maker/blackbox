---
id: DEBT-CONTRATO-ATLAS-SONDAS-DE-MEMORIA-01
kind: task
domain: HARDWARE
title: "Las sondas de memoria de Atlas deben leer la muestra de blackbox en vez de re-medir"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "grep -lE '\\[\"free\", \"-b\"\\]|Path\\(\"/proc/meminfo\"\\)' /home/lcasarin/projects/Atlas/tools/liberation_watchdog.py /home/lcasarin/projects/Atlas/tools/dgx401_medicion_pareada_dos_motores.py", "expect": "empty_stdout", "porque": "Hoy liberation_watchdog.available_gb() corre `free -b` y dgx401 lee /proc/meminfo directo (medido 2026-10-11, lineas 1027 y 84). Pasa cuando ninguno de los dos mide memoria por su cuenta y ambos leen la muestra de blackbox."}
---

## Origen

Escindida de `DEBT-CONTRATO-ATLAS-INSTRUMENTOS-EN-BLACKBOX-01` al cerrarla
(2026-10-11). Esa ficha tenia dos alcances; su `close_check` solo medía el
primero (`detect_atom_crash.py` lee `reboots.jsonl`), que quedo cerrado. El
segundo alcance, las sondas de memoria de Atlas, sigue abierto y es esta ficha:
cerrarla sin partirla lo habria enterrado.

## Medido (2026-10-11, Atlas `55f8b533a`)

- `tools/liberation_watchdog.py:1021-1027` `available_gb()`: `subprocess.run(["free", "-b"], ...)`.
  Lo usa la admision de trabajos (`:1412` dice "no se pudo leer la memoria disponible de `free -b`").
- `tools/medir_consumo_de_job.py:65`: reusa esa misma sonda.
- `tools/dgx401_medicion_pareada_dos_motores.py:84`: `available_memory_bytes(path=Path("/proc/meminfo"))`.

## Alcance

La politica de admision se queda en Atlas (enmienda del 2026-10-11, punto 2).
Lo que cambia es la FUENTE del numero: la muestra que blackbox ya publica
(`atom_gpu_telemetry.jsonl` o `bb sample`), con su latido, por archivo y sin
`import` cruzado. Una muestra vieja o ausente debe fallar cerrado en la
admision, igual que hoy falla cerrado `free -b` ilegible. Esta ficha es de dos
repos: la parte de Atlas la ejecuta su propio flujo (tests, gates), con control
negativo de la muestra vieja.
