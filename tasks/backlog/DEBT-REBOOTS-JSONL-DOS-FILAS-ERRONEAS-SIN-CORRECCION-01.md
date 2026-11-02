---
id: DEBT-REBOOTS-JSONL-DOS-FILAS-ERRONEAS-SIN-CORRECCION-01
kind: task
domain: VERDICT
title: "reboots.jsonl conserva dos filas falsas (fc60e471 juzgado vivo, 7cd0848b con sucesor equivocado) y no hay forma de corregirlas"
status: open
severity: P1
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-02
close_check: {"cmd": "python3 -c \"import json,os,sys; p=os.path.expanduser('~/.local/share/blackbox/reboots.jsonl'); u={}; [u.__setitem__(f['boot_id'], f) for f in map(json.loads, open(p)) ]; sys.exit(0 if u['7cd0848b8fc742e982970cc9697c34e9']['boot_id_siguiente'] == '2f73178e3f4c4e4084ba38a6012c56ab' and u['fc60e471d9c149648b0d1ea922fc9e57']['boot_id_siguiente'] != 'cd2e65eee13846249fc0d5a7145aa565' else 1)\"", "expect": "exit_zero", "porque": "Cierra cuando la ULTIMA fila de cada uno de los dos boots (la que gana si las correcciones se anaden al final) dice el sucesor real. Hoy sale 1: las dos filas falsas son las unicas."}
---

## Medido el 2026-11-02 (rama del arreglo de `tools/reboot_verdict.py`)

La corrida del timer de las 13:06 escribio en `~/.local/share/blackbox/reboots.jsonl`:

- linea 24: `boot_id=fc60e471d9c1...` (el arranque VIVO, que siguio vivo 4 h despues) `CORTE_ABRUPTO`,
  `boot_id_siguiente=cd2e65ee...`, `hueco_s=12186`. Causa: systemd 255 ordena `--list-boots` por hora de pared, y
  cd2e65ee tenia el reloj 12385 s adelantado, asi que el vivo no quedo al final de la lista.
- linea 23: `7cd0848b...` con `boot_id_siguiente=cd2e65ee...` y `hueco_s=29784`; su sucesor real es `2f73178e...`.

Con el arreglo (`-b <boot_id>`, vivo al final, `reloj_desfasado`) la corrida de solo lectura da para 7cd0848b
`sig=2f73178e`; el script de comparacion contra el ledger reporto exactamente estas dos lineas y ninguna otra de las
filas que el ledger y la corrida nueva comparten.

## Por que no se arreglo en la misma rama
El ledger es append-only y `--pendientes` / `--escribe` saltan todo `boot_id` que ya tiene fila: la fila falsa de
fc60e471 impide que su fila verdadera se escriba cuando ese boot termine, y la de 7cd0848b queda para siempre.
Corregir exige decidir un contrato que hoy no existe: (a) una fila de correccion anadida al final con un campo
`corrige_linea` y la regla "la ultima fila de un boot_id gana" en todos los lectores (`_ya_escritos`, `hallazgo`,
`bb status`, el consumidor externo), o (b) un archivo aparte de correcciones. Cualquiera cambia como leen el ledger
otros consumidores; eso es una decision de Luis.
