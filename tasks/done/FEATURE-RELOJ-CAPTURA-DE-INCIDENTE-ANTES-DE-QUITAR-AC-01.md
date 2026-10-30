---
id: FEATURE-RELOJ-CAPTURA-DE-INCIDENTE-ANTES-DE-QUITAR-AC-01
kind: task
domain: GPU
title: "bb reloj captura el paquete de incidente que NVIDIA pide (bug-report, nvidia-smi -q, dmidecode 45, telemetria de 5 s) antes de quitar AC"
status: done
closed_at: 2026-10-30
closure_type: fixed
reason: "Con veredicto ATASCADO (arranque, --prueba o pasivo) bb reloj arma incidentes/reloj-<boot_id>/ con nvidia-smi -q, la telemetria de 5 s de las 2 h previas y del paso sano->atascado, el dmidecode -t 45 de este arranque (script sellado arranque-forense) y pide el nvidia-bug-report al script sellado nuevo nvidia-bug-report en segundo plano (systemd-run --user); imprime la ruta y cada pieza faltante con could_not_run, y un bug-report EN_CURSO o NO_INSTALADO deja la captura INCOMPLETA. Probado con falsos de subprocess, mutaciones y una e2e real sin root. Limite declarado: el script sellado nuevo espera el paso de root de Luis; hasta entonces la pieza sale NO_INSTALADO."
evidence: {"pass": "tasks/evidence/FEATURE-RELOJ-CAPTURA-DE-INCIDENTE-ANTES-DE-QUITAR-AC-01/pass.txt", "fail": "tasks/evidence/FEATURE-RELOJ-CAPTURA-DE-INCIDENTE-ANTES-DE-QUITAR-AC-01/fail.txt", "e2e": "tasks/evidence/FEATURE-RELOJ-CAPTURA-DE-INCIDENTE-ANTES-DE-QUITAR-AC-01/e2e.txt"}
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

## Cierre (2026-10-30)

Hecho en `tools/reloj_atascado.py` (`captura_incidente`, `completar_bug_report`, `linea_captura`; `main` la llama con todo
ATASCADO y `evento_arranque` lleva ruta y faltantes a `reloj_arranque.jsonl`):

- Carpeta `~/.local/share/blackbox/incidentes/reloj-<boot_id>/`, una por arranque (el estado atascado dura el arranque y el
  bug-report pesa). Una segunda corrida no repite lo `ok` ni un bug-report EN_CURSO de menos de 15 min; reintenta lo demas.
- Piezas en `captura.json`, cada una `ok` (con su archivo) o `could_not_run` (con su motivo): `nvidia_smi_q` (sin root),
  `telemetria_2h` y `telemetria_transicion` (copia literal de las filas; la transicion es +/-10 min alrededor de
  `ultima_sana`/`primera_atascada` de `inicio()`, aunque sea anterior a las 2 h), `dmidecode_t45` (la copia de
  `bb-root-run arranque-forense` solo si es de ESTE arranque; si no, se pide el script sellado una vez) y `nvidia_bug_report`.
  `completa` solo es true con las cinco en ok.
- El bug-report: `systemd-run --user` lanza `python3 -m tools.reloj_atascado --completar-bug-report <carpeta>`, que pide
  `sudo -n bb-root-run nvidia-bug-report`, guarda la salida y copia el `.log.gz` solo si rc=0 y es de esa corrida. Mientras
  corre la pieza es `could_not_run` `EN_CURSO`: la captura no se presenta como completa. La unidad transitoria sobrevive al
  fin de la unit oneshot `bb-reloj-arranque`.
- Root: ningun camino corre nada como root fuera de bb-root-run (`sudo -n`, que nunca pregunta). El punto 3 del alcance
  (confirmacion antes de root fuera de bb-root-run) queda cubierto porque ese camino no existe.
- La ultima linea (stderr) dice ruta, COMPLETA/INCOMPLETA, `could_not_run=N de 5` y el motivo de cada faltante.
- `BB_RELOJ_CAPTURA=off` existe solo para las pruebas que corren el modulo como script; la salida lo declara como
  `could_not_run`.

Limitacion declarada (paso de root que solo Luis puede dar): el script sellado nuevo `adopted/root-scripts/nvidia-bug-report.sh`
esta escrito, probado sin root con un `nvidia-bug-report.sh` sustituido y anadido a la propuesta del manifiesto, pero NO
instalado. Hasta que Luis corra `python3 -m tools.bb_root_manifest --propose` desde el checkout principal y el
`sudo sh -c '...'` de su ultima linea (pasos en `adopted/pendiente-de-despliegue/LEEME.txt`), toda captura real sale con
`nvidia_bug_report: could_not_run NO_INSTALADO` e INCOMPLETA. No medido: la duracion y la carga del bug-report sobre una GPU
atascada, y un `systemd-run --user` real lanzando el completador (solo con falsos).

Evidencia: `tasks/evidence/FEATURE-RELOJ-CAPTURA-DE-INCIDENTE-ANTES-DE-QUITAR-AC-01/{fail,pass,e2e}.txt`.
