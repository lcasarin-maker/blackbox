---
id: DEBT-AUDIT-ANILLO-DESBORDADO-SIN-LIMITE-01
kind: task
domain: AUDIT
title: "Subir audit_backlog_limit: el anillo de audit pierde eventos y la atribucion de quien mato queda ciega"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-10
close_check: {"cmd": "grep -q -- \"-b 32768\" enable-privileged.sh", "expect": "exit_zero", "porque": "El instalador privilegiado debe fijar un backlog de audit mayor que 8192; hoy no lo fija."}
---

## Hueco

El kernel reporta `audit_backlog=8193 > audit_backlog_limit=8192` y `audit_lost` llego a 2662 en el boot del 07 al 08-oct. Mientras el anillo desborda, los instrumentos que atribuyen senales por audit (`bb sigterm`, `bin/bb-parada-diagnostico`) pierden eventos sin avisar. `bb scan` ya imprime el contador desde 2026-10-10; falta que el instalador fije el limite (`-b 32768` en la regla de audit) y se mida que deja de perder.
/etc/audit es root:root 0750: este usuario no puede leer el limite vigente.
