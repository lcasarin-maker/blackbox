---
id: DEBT-REBOOT-VERDICT-CIEGO-A-ARRANQUES-CORTOS-Y-RELOJ-01
kind: task
domain: SYSTEM
title: "reboot_verdict juzga solo el arranque anterior y solo tras 3 min de uptime, ordena por reloj de pared y marco CORTE_ABRUPTO al arranque en marcha"
status: done
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-11-02
close_check: {"cmd": "python3 - <<'E'\nimport json,subprocess,os,datetime as dt,sys\nids={json.loads(l).get('boot_id') for l in open(os.path.expanduser('~/.local/share/blackbox/reboots.jsonl'))}\nbl=json.loads(subprocess.run(['journalctl','--list-boots','--no-pager','-o','json'],capture_output=True,text=True,errors='replace').stdout)\ncur=open('/proc/sys/kernel/random/boot_id').read().strip().replace('-','')\ncorte=dt.datetime(2026,10,24).timestamp()*1e6\nfalta=[b for b in bl if b['boot_id']!=cur and b['first_entry']>=corte and b['boot_id'] not in ids]\nsys.exit(1 if falta else 0)\nE", "expect": "exit_zero", "porque": "Falla hoy (medido 2026-11-02): 23 de los arranques desde 2026-10-24, sin contar el actual, no tienen fila en reboots.jsonl. Pasa solo cuando cada arranque anterior tiene su veredicto."}
closed_at: 2026-11-07
closure_type: verified_closed
closure_reason: "El close_check de la ficha sale 0 hoy (corrido por /debt el 2026-11-07); la ficha seguia abierta aunque su condicion ya se cumplia. Salida en la evidencia."
evidence:
  pass: tasks/evidence/DEBT-REBOOT-VERDICT-CIEGO-A-ARRANQUES-CORTOS-Y-RELOJ-01/pass.txt
---

## Medido el 2026-11-02

1. **Cobertura**: de 32 arranques desde 2026-10-24 solo 8 tienen fila en `~/.local/share/blackbox/reboots.jsonl`. La causa es el diseno de la unidad: `bb-reboot-verdict.timer` (`OnBootSec=3min`) corre `reboot_verdict --ultimos 1 --escribe`, asi que juzga unicamente el arranque anterior y solo si el actual dura 3 min. Los 20 arranques de 3 a 242 s del bucle (2026-10-30 19:05 a 2026-11-02 11:44) quedaron sin veredicto.
2. **Orden por reloj de pared**: dos arranques tienen el reloj adelantado horas (primer registro 2026-11-02 16:29 y 16:31 cuando la hora real era ~11:44 y ~22:30 del dia anterior; uno tiene `last_entry < first_entry`, duracion -64 702 s). El veredicto de las 13:06 escribio una fila con `boot_id` del arranque EN MARCHA (vivo 4 h despues, `uptime -s` 13:02:39), `etiqueta=CORTE_ABRUPTO`, `hueco_s=12186`: tomo como sucesor al arranque de reloj adelantado.
3. **`--ultimos N>1` desalineado**: `python3 -m tools.reboot_verdict --ultimos 32` (sin `--escribe`) cita, en la fila del arranque que empezo 16:22:07, un apagado ordenado de las 16:20:29, anterior a ese arranque. Las razones de cierre ordenado salen corridas un arranque respecto de la fila escrita por el temporizador.
4. **Falta senal**: los arranques en kernel 7.0.0-1024 desde 10-30 19:05 registran un timeout RPC del GSP y Xid 154 (ver DEBT-NVRM-GSP-TIMEOUT-XID154-KERNEL-7-0-SIN-ALARMA-01); el campo `xids` de la fila no lo refleja (el arranque de 2 h 44 min con 7 000+ aserciones NVRM tiene 0 xids).

## Alcance

Orden por indice del journal y nunca por reloj, nunca juzgar el arranque en marcha, bandera `reloj_desfasado` con los segundos; modo idempotente que juzga todo arranque sin fila (`--pendientes`); unidad que corre a ~20 s y a 3 min; campos `gsp_timeout`, `xid154`, `gpu_fullchip_reset_asserts`. Filas solo anexadas, sin reescribir las viejas.

## Control negativo

El `close_check` falla hoy con 23 arranques sin fila. Cada defecto (2 y 3) exige una prueba que falle contra el codigo actual y pase despues; la hace el trabajo de cierre.

## Limite

Esta ficha no dice cual fue la causa de ningun corte; dice que el instrumento no habia mirado 24 de 32 arranques ni sabia en que arranque estaba.
