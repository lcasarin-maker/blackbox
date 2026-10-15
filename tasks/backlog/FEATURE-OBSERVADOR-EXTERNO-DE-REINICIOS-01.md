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

## Avance 2026-10-14: observador = NAS QNAP (voto de Luis); script, sync y unidades construidos, nada instalado
Decision votada: el QNAP de la LAN (siempre encendido) hace el ping a la ATOM. Construido, todo sin instalar:
- `adopted/nas/bb-ping-atom.sh` (POSIX sh, busybox): una linea `<epoch> ok|fail` por segundo en un log del NAS, rotacion por lineas (`BB_MAX_LINEAS`, 172800 = 2 dias), un solo proceso (directorio de bloqueo). Instrucciones de instalacion en su cabecera.
- `tools/observador_ping.py --sync`: trae el log por `smbclient -A <archivo>` y lo mezcla en `externo/ping.jsonl` (fuente `nas`, clave epoch, idempotente); estados OK / OBSOLETO (log sin avanzar 900 s) / NOT_COLLECTED (rc != 0, `ping.jsonl` intacto); lineas rotas se descartan y se cuentan; rehusa credenciales con modo distinto de 600; estado en `externo/sync.json`. Respeta el interruptor `observador_ping` (off = no trae).
- `systemd/bb-observador-ping-sync.{service,timer}` (5 min, `ExecStopPost` de bb-parada-diagnostico).
- Pruebas en `tests/test_observador_ping.py` (12 en total), con controles negativos corridos como mutantes: sin dedupe falla `test_sync_mezcla_y_es_idempotente`; sin comprobar el rc de smbclient falla `test_sync_nas_caido_es_not_collected_y_no_toca_ping`.

Pasos de Luis (nada de esto se ejecuto aqui):
1. En el NAS: copiar `adopted/nas/bb-ping-atom.sh` a una carpeta compartida, editar `BB_ATOM_IP` (IP de la ATOM) y `BB_LOG`, `chmod 755`, y arrancarlo por Task Scheduler o autorun.sh (pasos 1 a 5 en la cabecera del script). Verificar: `tail -n 5 <log>` muestra `epoch ok`.
2. En la ATOM: crear `$BLACKBOX_DATA/externo/nas.json` = `{"host": "<nas>", "share": "<recurso>", "ruta": "<ruta dentro del recurso>", "credenciales": "/ruta/al/archivo"}`; el archivo de credenciales tiene `username=...` y `password=...` (formato de `smbclient -A`), `chmod 600`.
3. Probar a mano: `cd ~/projects/blackbox && python3 -m tools.observador_ping --sync` (el interruptor `observador_ping` debe estar en `observar`; con `off` no hace nada) y ver `estado: OK` y filas `fuente: nas` en `externo/ping.jsonl`.
4. Instalar: copiar `systemd/bb-observador-ping-sync.{service,timer}` a `~/.config/systemd/user/`, `systemctl --user daemon-reload && systemctl --user enable --now bb-observador-ping-sync.timer`. No instalar `bb-observador-ping.{service,timer}` (ese corre en la ATOM y muere con ella).

Sigue sin verificar: el NAS real nunca se toco (ni SMB, ni busybox del QNAP, ni el nombre real de share/ruta, ni que su `ping -W 1` acepte esos flags); el reloj del NAS (un desvio mueve `ultima_respuesta` entera; verificar NTP en QTS y comparar `date +%s` del NAS con el de la ATOM); `smbclient` real contra el NAS (las pruebas usan un stub); y el enlace con `reboot_verdict`: `reboot_verdict` aun no llama a `ultima_respuesta`, solo se probo `ultima_respuesta` sobre el archivo mezclado.
