---
id: DEBT-MUESTREO-1S-FUERA-DEL-REPO-01
kind: task
domain: SYSTEM
title: "El muestreador de 1 s con fsync, el unico instrumento que demostro cubrir el ultimo segundo antes de un corte, es un script suelto fuera del repo y sin pruebas"
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-11-02
close_check: {"cmd": "git ls-files | grep -q 'muestreo_1s'", "expect": "exit_zero", "porque": "Falla hoy (medido 2026-11-02): ningun archivo versionado se llama muestreo_1s. El script vive en ~/.local/share/blackbox/incidentes/caidas-2026-10-30/muestreo_1s.py."}
closed_at: 2026-11-07
closure_type: verified_closed
closure_reason: "El close_check de la ficha sale 0 hoy (corrido por /debt el 2026-11-07); la ficha seguia abierta aunque su condicion ya se cumplia. Salida en la evidencia."
evidence:
  pass: tasks/evidence/DEBT-MUESTREO-1S-FUERA-DEL-REPO-01/pass.txt
---

## Medido el 2026-11-02

- `bb-muestreo-corte.service` (habilitado, activo) ejecuta `python3 -I ~/.local/share/blackbox/incidentes/caidas-2026-10-30/muestreo_1s.py`; el script no esta en git y no tiene pruebas.
- Cubrio 22 arranques entre 2026-10-30 y hoy (`muestreo-<boot>.jsonl`, 13 974 lineas en el arranque actual). Prueba de que el fsync sobrevive a un corte: en 7cd0848b la ultima muestra (`ts=1793638458`) esta a ~0,4 s del ultimo registro del journal; en los 14 arranques cortos del bucle la ultima muestra (CPU 0,5 a 44 %, temperatura maxima 52,2 C, GPU 5 a 9,7 W) no muestra saturacion ni calentamiento.
- Sus datos son lo que descarta CPU, temperatura y potencia de GPU como causa en esos arranques; el repo no los puede reproducir.
- No muestrea: potencia de entrada de la maquina, estado del GSP, ni el hilo `pr/ttyS0`.

## Alcance

Mover el script a `tools/` con pruebas (formato de linea, fsync por segundo, rotacion), mantener el nombre de la unidad, sumar `nvidia-smi -q` solo si es barato y anotar la deuda `ponytail:` con techo y disparador.

## Control negativo

El `close_check` falla hoy. Una prueba debe fallar si se quita el `fsync`.

## Limite

Mover el archivo no cambia lo que mide.
