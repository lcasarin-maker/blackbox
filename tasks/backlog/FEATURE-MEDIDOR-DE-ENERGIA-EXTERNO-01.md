---
id: FEATURE-MEDIDOR-DE-ENERGIA-EXTERNO-01
kind: task
domain: HARDWARE
title: "Enchufe medidor en la entrada de la ATOM para separar corte de red de apagado interno"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "grep -q . /home/lcasarin/.local/share/blackbox/externo/energia.jsonl", "expect": "exit_zero", "porque": "Un corte de energia mata al propio instrumento: solo un medidor de voltaje y watts en la entrada distingue CORTE_DE_RED de APAGADO_INTERNO en los 4 cortes abruptos bajo carga del 06, 07, 08 y 11-oct."}
---

## Por que

Decision de Luis (2026-10-11): comprar un enchufe inteligente con medicion de voltaje y watts y exportacion o API local. Con la configuracion medida (`kernel.panic=10`, panics por lockup, watchdog SBSA de 60 s) un cuelgue se habria reiniciado solo; el equipo estuvo 70 min abajo el 11-oct hasta pulsar el boton y la pantalla no tenia imagen. Apunta a perdida de alimentacion o apagado de proteccion, sin probarlo.

## Alcance

Enchufe entre la pared y el adaptador de la ATOM (el adaptador original de 240 W: la documentacion de NVIDIA advierte que otros pueden causar apagados inesperados). Un registro local de voltaje y potencia, con marca de hora, en `~/.local/share/blackbox/externo/energia.jsonl`, escrito desde otro equipo o desde el propio enchufe. `reboot_verdict.py` lo lee y rellena `ev["externo"] = {"voltaje_perdido": bool}` en la ventana del corte.

## Cierre

El fichero tiene datos y un corte real o provocado sale como `CORTE_DE_RED` o `APAGADO_INTERNO`, no `CORTE_ABRUPTO`.

## Avance 2026-10-13: colector y clasificador construidos, falta el enchufe
Construido sin el dispositivo: `tools/medidor_energia.py` (lee Shelly Gen2/3 `Switch.GetStatus` o Tasmota `Status 8` por API local, una fila por ejecucion en `externo/energia.jsonl`; un campo ausente es `NOT_COLLECTED`, un enchufe mudo es `ok: false` y no cuenta como voltaje perdido), `ventana_de_corte` (tres estados: solo concluye con voltaje medido) y el enlace en `reboot_verdict._anade_evidencia_externa`, que rellena `ev["externo"]` o declara `medidor_externo (no concluyente)` en `could_not_run`. Tests: `tests/test_medidor_energia.py` (9) y 2 en `tests/test_reboot_verdict.py`, con control negativo en cada rama. Las unidades `systemd/bb-medidor-energia.{service,timer}` (1 s) quedan sin instalar.
Falta, y es de Luis: comprar y conectar el enchufe, crear `$BLACKBOX_DATA/externo/medidor.json` con `{"tipo": "shelly"|"tasmota", "url": "http://<ip>"}` y correr el colector desde otro equipo. Los nombres de campos son los de la documentacion de cada fabricante y NO se verificaron contra un dispositivo: la primera lectura real lo confirma o lo corrige (`python3 -m tools.medidor_energia --paso`).
