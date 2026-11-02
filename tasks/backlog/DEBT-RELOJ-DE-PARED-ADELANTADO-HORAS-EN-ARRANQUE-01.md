---
id: DEBT-RELOJ-DE-PARED-ADELANTADO-HORAS-EN-ARRANQUE-01
kind: task
domain: SYSTEM
title: "Dos arranques del 2026-11-02 y 11-01 tienen el reloj de pared horas adelantado; el temporizador de reloj de arranque estaba suspendido y ningun monitor lo vio"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-11-02
close_check: {"cmd": "python3 - <<'E'\nimport json,subprocess,sys\nbl=json.loads(subprocess.run(['journalctl','--list-boots','--no-pager','-o','json'],capture_output=True,text=True,errors='replace').stdout)\nmal=[b['boot_id'] for b in bl if b['last_entry']<b['first_entry']]\nsys.exit(1 if mal else 0)\nE", "expect": "exit_zero", "porque": "Falla hoy (medido 2026-11-02): el arranque c092e563 tiene last_entry anterior a first_entry. Pasa solo cuando ningun arranque del journal tiene el reloj hacia atras."}
---

## Medido el 2026-11-02

- `journalctl --list-boots`: el arranque c092e563 empieza `2026-11-02 16:31:26` y termina `2026-11-01 22:33:03` (duracion -64 703 s); el arranque cd2e65ee empieza `2026-11-02 16:29:10` y duro 10 s, pero fisicamente ocurrio entre las 11:44 y las 13:02. Ambos son arranques en 7.0.0-1024 de 10 a 861 s de vida.
- El tiempo adelantado es ~3 h 25 min (16:29 contra ~13:00) en el segundo y ~18 h en el primero.
- `bb-reloj-arranque.timer`, el detector de reloj, estaba entre las 22 unidades suspendidas el 2026-10-30 16:42; no corrio en ninguno de esos arranques.
- Consecuencia medida: `reboot_verdict` ordena por reloj y juzgo el arranque en marcha como cortado (ver DEBT-REBOOT-VERDICT-CIEGO-A-ARRANQUES-CORTOS-Y-RELOJ-01).
- Causa del reloj adelantado: no determinada. Hipotesis sin probar: RTC leido mal en arranques que mueren antes de que `systemd-timesyncd` corrija, o el EC entrega una hora errada tras un corte de energia.

## Alcance

1. Reponer `bb-reloj-arranque.timer` primero en la reposicion de las 22 unidades (es solo lectura).
2. Registrar en cada arranque, antes de que NTP corrija, `CLOCK_REALTIME` contra `CLOCK_BOOTTIME` y contra la ultima hora escrita en el arranque anterior.
3. Leer el RTC por hardware (`hwclock --show` con root) y compararlo.

## Control negativo

El `close_check` falla hoy (arranque c092e563). Para el detector: debe marcar c092e563 y no marcar el arranque en 6.17 en marcha.

## Limite

No hay datos del RTC fisico de esos arranques; solo se midio el desfase que dejo el journal.
