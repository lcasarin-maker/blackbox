---
id: DEBT-REBOOTS-JSONL-DOS-FILAS-ERRONEAS-SIN-CORRECCION-01
kind: task
domain: VERDICT
title: "reboots.jsonl conserva dos filas falsas (fc60e471 juzgado vivo, 7cd0848b con sucesor equivocado) y no hay forma de corregirlas"
status: done
severity: P1
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-02
closed_at: 2026-11-21
close_check: {"cmd": "python3 -c 'from pathlib import Path\nfrom tools.reboot_ledger import leer_filas\nimport os, sys\n\nruta = Path(os.environ.get(\"BLACKBOX_LEDGER_PATH\", Path.home() / \".local/share/blackbox/reboots.jsonl\"))\navisos = []\nvigentes = leer_filas([ruta], avisos)\nif avisos:\n    print(\"COULD_NOT_RUN: \" + \"; \".join(avisos), file=sys.stderr)\n    sys.exit(2)\nesperados = {\n    \"7cd0848b8fc742e982970cc9697c34e9\": \"2f73178e2f3c4e4084ba38a6012c56ab\",\n    \"fc60e471d9c149648b0d1ea922fc9e57\": \"e0666a39e3194129be9bcb663dc0891e\",\n}\nmatches = sum(vigentes.get(boot, {}).get(\"boot_id_siguiente\") == siguiente for boot, siguiente in esperados.items())\nprint(f\"sucesores correctos={matches}/{len(esperados)}\")\nsys.exit(0 if matches == len(esperados) else 1)'", "expect": "exit_zero", "porque": "El lector común debe devolver exactamente ambos sucesores vigentes. Un historial ilegible devuelve 2."}
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

## Decisión de Luis del 2026-11-21

Las rectificaciones se añaden al mismo historial de reinicios. Los registros
originales se conservan y los lectores aplican la última rectificación válida
de cada arranque. Se elige un solo historial para evitar que dos fuentes
puedan divergir. Se descarta guardar rectificaciones en un archivo separado.

## Cierre del 2026-11-21

El lector común de Blackbox y el consumidor externo de Orcaestrator
aplican la referencia a la última línea vigente del mismo arranque.
El consumidor se integró en `0f9ed7d` con una prueba de referencia cruzada y controles de historial ilegible.

El historial operativo ya contenía las anulaciones y reposiciones. El instrumento anterior tenía un identificador de sucesor mal transcrito. El cierre nuevo consulta el lector común y obtuvo `sucesores correctos=2/2`, código 0. El historial se inspeccionó en modo de solo lectura.

El [registro de sesión](../../audit/sessions/2026-11-21-DEBT-REBOOTS-JSONL-DOS-FILAS-ERRONEAS-SIN-CORRECCION-01.md) conserva el primer subalcance, cuando todavía faltaba el lector externo. El resultado de cierre incorpora esa integración posterior.
