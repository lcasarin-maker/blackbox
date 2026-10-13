---
id: FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01
kind: task
domain: HARDWARE
title: "Observador externo de ping 1 s y netconsole para saber si la maquina murio entera"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "grep -q . /home/lcasarin/.local/share/blackbox/externo/ping.jsonl", "expect": "exit_zero", "porque": "Un corte de energia mata al propio instrumento: la evidencia tiene que venir de afuera. Sin registro externo de ping Y de voltaje/consumo, CORTE_ABRUPTO no se separa en CORTE_DE_RED o APAGADO_INTERNO."}
---

## Por que

`tools/reboot_verdict.py` (2026-10-11) clasifica cada reinicio. Los 4 cortes abruptos bajo carga (06, 07, 08 y 11-oct) quedan `CORTE_ABRUPTO` con la causa INDETERMINADA entre energia y hardware interno, y asi seguiran: la herramienta lo declara en `could_not_run: observador_externo`.

Config medida: `kernel.panic=10`, panics por hung/softlockup/hardlockup/oops activados y watchdog SBSA de 60 s. Un cuelgue se habria reiniciado solo; la maquina estuvo 70 min abajo hasta el boton. Apunta a perdida de alimentacion o apagado de proteccion, sin demostrarlo.

## Alcance

1. Enchufe inteligente con medicion de voltaje y watts, con exportacion o API local (lo compra Luis; decision votada 2026-10-11).
2. Otro equipo siempre encendido hace ping de 1 s a la ATOM con marca de hora y lo escribe en `~/.local/share/blackbox/externo/ping.jsonl`.
3. `netconsole` hacia ese mismo equipo (ver FEATURE-FORUM-NETCONSOLE-01).
4. `reboot_verdict.py` lee esos ficheros y rellena `ev["externo"] = {"voltaje_perdido": bool}` en la ventana del corte.

## Cierre

El close_check pasa solo con `ping.jsonl` con datos; el medidor de energia tiene su propia ficha (FEATURE-MEDIDOR-DE-ENERGIA-EXTERNO-01). Ademas, un corte real o provocado debe salir clasificado por `reboot_verdict` como CORTE_DE_RED o APAGADO_INTERNO, no CORTE_ABRUPTO.

## Avance 2026-10-13: colector de ping construido, falta el equipo observador
`tools/observador_ping.py` (un ping por ejecucion a la ATOM hacia `externo/ping.jsonl`; `ultima_respuesta(ruta, hasta)` devuelve la hora de la ultima respuesta anterior al corte, y None si no hay cobertura), con `tests/test_observador_ping.py` (4 tests) y las unidades `systemd/bb-observador-ping.{service,timer}` (1 s, sin instalar). Falta, y no se puede producir aqui: un equipo siempre encendido que lo corra (un ping desde la propia ATOM muere con ella) y `$BLACKBOX_DATA/externo/observador.json` con `{"destino": "<ip de la ATOM>"}`. Tampoco esta enlazado a `reboot_verdict`: sin datos reales de ese equipo no hay forma de probar el enlace con el sujeto.
