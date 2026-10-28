---
id: FEATURE-RELOJ-CAPTURA-DE-INCIDENTE-ANTES-DE-QUITAR-AC-01
kind: task
domain: GPU
title: "bb reloj captura el paquete de incidente que NVIDIA pide (bug-report, nvidia-smi -q, dmidecode 45, telemetria de 5 s) antes de quitar AC"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-28
close_check: {"cmd": "python3 -m pytest -q tests/test_reloj_atascado.py -k \"captura_incidente\"", "expect": "exit_zero", "porque": "Especificacion pendiente, no prueba existente: hoy pytest no recolecta ninguna prueba con ese nombre y sale con codigo 5. Pasa cuando exista la captura y su prueba cubra el veredicto ATASCADO y el SANO."}
---

## Origen

zneill (NVIDIA), post [386060/6](https://forums.developer.nvidia.com/t/386060/6), 2026-10-28: si el reloj atascado reaparece en una unidad
actualizada, capturar ANTES de quitar la corriente alterna `sudo nvidia-bug-report.sh`, `sudo dmidecode -t 45` y
`nvidia-smi -q -d CLOCK,POWER,TEMPERATURE,PERFORMANCE`, y adjuntar `nvidia-bug-report.log.gz`, la salida de `nvidia-smi -q` y la
telemetria de 5 s que cubra la transicion sana-atascada. "A recurrence on a fully updated unit is the most useful data point."

## Hueco (medido 2026-10-28)

`tools/reloj_atascado.py` consulta `nvidia-smi --query-gpu` (linea 230) y emite el veredicto, y no guarda nada de lo que NVIDIA pide.
La captura hoy es manual: quien ve el veredicto ATASCADO debe recordar tres comandos, uno con root y de varios minutos, antes de
apagar el equipo. La telemetria de 5 s existe (`~/.local/share/blackbox/atom_gpu_telemetry.jsonl`, 103540 filas del 2026-10-22 al
2026-10-28, 140 MB) y no se recorta al incidente.

## Alcance

1. Con veredicto ATASCADO (arranque o manual), crear una carpeta de incidente con: `nvidia-smi -q -d CLOCK,POWER,TEMPERATURE,PERFORMANCE`,
   el recorte de la telemetria de 5 s de las 2 h previas, el `dmidecode -t 45` (script sellado de `bb-root-run`, que ya existe), y el
   `nvidia-bug-report.sh` lanzado en segundo plano por `bb-root-run` (necesita root y tarda minutos).
2. Imprimir al final la ruta de la carpeta y cuales piezas faltan, con `could_not_run` visible: un bug-report sin terminar no se
   presenta como captura completa.
3. Exigir confirmacion explicita antes de cualquier paso que lo corra como root fuera de `bb-root-run`.

## Control negativo exigido

Prueba con veredicto SANO: no crea carpeta. Prueba con ATASCADO y `nvidia-bug-report.sh` ausente: la carpeta existe y lista la pieza
faltante como `could_not_run`.

## Limite

Hardware unico (AI TOP ATOM). El bug-report agrega carga y tarda; sobre una GPU atascada no se midio cuanto.
