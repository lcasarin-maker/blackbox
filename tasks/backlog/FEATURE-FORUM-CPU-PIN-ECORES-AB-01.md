---
id: FEATURE-FORUM-CPU-PIN-ECORES-AB-01
kind: task
domain: GPU
title: "Validate pinning inference host threads to the A725 cores as an opt-in thermal mitigation"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-21
close_check: {"cmd": "python3 -m tools.verify_cpu_pin_ab --evidence tasks/evidence/FEATURE-FORUM-CPU-PIN-ECORES-AB-01", "expect": "exit_zero", "porque": "Debe comparar, con la misma carga y el mismo cap de reloj, el proceso de inferencia sin pin contra el pin a cpu 0-4,10-14 (A725), registrando las 7 thermal zones acpitz, clocks efectivos y throughput, con repeticion, control negativo (pin a los X925 no debe enfriar) y rollback verificado. Si falta hardware o carga, imprimir could_not_run y conservar open."}
---

## Origen

Hilo [386102](https://forums.developer.nvidia.com/t/386102) (GB10 a 95 C en zonas termicas y apagones bajo inferencia 122B) y su enlace [386117](https://forums.developer.nvidia.com/t/386117). Los reportes de foro siguen sin validacion local.

- 386117 (un usuario, dos ASUS GX10, motor tensorfold, un dia de datos): las zonas `acpitz` llegaban a 95-97 C con la GPU fria; el host de inferencia ocupaba los X925 (cpu 5-9,15-19) mientras los diez A725 (cpu 0-4,10-14) estaban libres. `taskset -a -p -c 0-4,10-14 <pid>` bajo el pico de 94 a 72 C con el mismo throughput (107 vs 108 tok/s decode) y con el cap en 1400 MHz; con el pin, el cap volvio a 2000 MHz y el prefill subio ~20%. Reglas que reporta: el proceso entero va al conjunto de A725; repartir hilos entre los dos clusters A725 dio 2-3 C mas.
- 386102 posts 3, 5, 10 (otros tres usuarios) reportan lo mismo con cap 1400-1700 MHz. Post 11 del autor: A/B en corridas cortas sin diferencia, corridas largas a 93-95 C; sin explicar.
- 379389: el cap de reloj baja potencia en pared pero NO la zona caliente del SoC (90-96 C a todo reloj), porque no afecta a los nucleos Grace. El cap ayuda con transitorios de potencia, no con calor de CPU.
- 386102 post 12: el 90 C de ACPI reflejaria la interfaz C2C y no la CPU. Sin verificar.

## Lo medido en este equipo (2026-10-21)

- `midr_el1`: cpu 0-4 y 10-14 = `0x410fd871` (A725, cpuinfo_max 2808000); cpu 5-9 y 15-19 = `0x410fd851` (X925, cpuinfo_max 3900000). Coincide con la tabla del foro.
- `ps -eo pid,psr,pcpu,comm --sort=-pcpu`: `VLLM::EngineCor` (pid 1245358) al 103 % en cpu16, un X925. Es el escenario del reporte.
- 7 thermal zones `acpitz` entre 45.1 y 51.4 C, GPU 43 C, `clocks_event_reasons.active` = 0x0: sin calor actual, asi que este equipo no reproduce el sintoma ahora. Falta una corrida larga con carga.
- `atom-clock-lock.service` aplica hoy `nvidia-smi -lgc 300,2100`. La ficha FEATURE-FORUM-GPU-CLOCK-CAP-AB-01 dice 300,2800: ese texto esta desactualizado y debe conciliarse al tocarla.

## Alcance

1. Con el mismo workload acotado (vLLM de nemotron-local, decode + prefill) y el mismo cap, comparar sin pin contra `taskset -a -p -c 0-4,10-14` sobre el proceso de inferencia entero (alternativa persistente: `AllowedCPUs=0-4 10-14` en el unit, no un cron). Corrida larga hasta saturar el calor (>= 30 min por brazo) y repeticion; las corridas de 5 min del reporte no distinguen.
2. Registrar las 7 zonas por separado (no solo la maxima), clocks efectivos, throughput de decode y prefill, potencia, `clocks_event_reasons`.
3. Control negativo corrido, no argumentado: pin a cpu 5-9,15-19 (X925). Si tambien "enfria", el instrumento no discrimina.
4. Rollback: `taskset -a -p -c 0-19 <pid>` y lectura de vuelta de `taskset -p`.

No cambiar la afinidad de vLLM en produccion ni el unit del reloj hasta que el A/B exista. Cualquier intervencion es opt-in y requiere la aprobacion de Luis.

## Limites

Un usuario, una carga, un motor (tensorfold, no vLLM); el propio autor no midio vLLM. El mapeo zona-a-nucleo es desconocido (las zonas `acpitz` no tienen etiqueta; ver DEBT-RELOJ-VERIFICADOR-ETIQUETAS-DE-SENSORES-INCOMPLETAS-01). Un resultado nulo es valido y cierra la ficha como evidencia negativa.

## Avance 2026-10-30

El verificador del `close_check` existe: `tools/verify_cpu_pin_ab.py` (tests: `tests/test_verify_cpu_pin_ab.py`, fila nueva en `SPEC.md`). Antes el comando salia rc=1 con `No module named tools.verify_cpu_pin_ab` (instrumento caido); ahora sale rc=2 con `could_not_run: 1` mientras falte evidencia.

Contrato: `verify(evidence_dir) -> dict` con `status` (`pass` / `fail` / `unknown`), `fail`, `could_not_run`, `reason`; `main()` sale 0 en pass, 1 en fail (evidencia contradictoria), 2 en unknown (falta o incompleta). Lee `<dir>/ab.json`; el esquema esta en el docstring del modulo. Exige los tres brazos (`unpinned`, `pin_a725` a 0-4,10-14, `pin_x925` a 5-9,15-19 como control negativo), >= 2 repeticiones por brazo de >= 1800 s con la GPU bajo carga, las 7 zonas `acpitz`, clocks efectivos, decode/prefill, potencia, `clocks_event_reasons`, mismo cap y misma tupla de workload en todas las corridas, readback de `taskset -p`, `midr_el1` de los dos conjuntos y rollback a 0-19 leido de vuelta. Si el control X925 tambien enfria, `fail`: el instrumento no discrimina. Un resultado nulo del pin A725 es valido y pasa con `effect: "null"`.

El A/B real sigue pendiente y la ficha sigue `open` en `backlog/`: exige corridas de >= 30 min por brazo con carga en la GPU y repeticion, es decir hardware y tiempo que ningun agente produjo. No se capturo ninguna evidencia real; el verificador solo juzga lo que alguien le entregue (el origen de la captura no se autentica).
