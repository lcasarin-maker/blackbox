---
id: DEBT-AUDIT-ANILLO-DESBORDADO-SIN-LIMITE-01
kind: task
domain: AUDIT
title: "Subir audit_backlog_limit: el anillo de audit pierde eventos y deja ciega la atribucion"
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

## Avance 2026-10-13
`enable-privileged.sh` fija ahora `-b 32768` antes de las reglas de captura (`tests/test_enable_privileged_audit_backlog.py`: la linea esta y precede a la primera regla; control negativo sin la linea o despues de la captura da False). El `close_check` (`grep -q -- "-b 32768" enable-privileged.sh`) pasa. Sigue abierta porque falta lo que pide el Hueco: aplicar el instalador (`sudo`, de Luis) y medir que `audit_lost` deja de subir; /etc/audit es root:root 0750.

## Avance 2026-10-13 18:18: instalador aplicado por Luis
`sudo ./enable-privileged.sh` corrio completo, incluida la regla de auditoria con `-b 32768`. `bb scan "2 hours ago"` muestra la linea de eventos de audit perdidos sin valor, y leer `auditctl -s` exige root, asi que NO se midio que `audit_lost` deje de subir: queda pendiente leer `audit_backlog_limit` (esperado 32768) y el contador `lost` con sudo, y compararlo con el del boot del 07 al 08-oct (2662).

## Avance 2026-10-13 18:50: el `-b 32768` no quedo activo; causa medida y corregida en el instalador
Tras correr el instalador, `sudo auditctl -s` dio `backlog_limit 8192` y `lost 0`. `sudo grep -rnE "^-(b|D|e) " /etc/audit/rules.d/ /etc/audit/audit.rules` mostro `10-blackbox-signals.rules:10:-b 32768`, `rules.d/audit.rules:6:-b 8192` y `/etc/audit/audit.rules:3:-b 8192`: el audit.rules de serie ordena DESPUES del archivo 10- y lo pisa, y el archivo combinado no se regenero con la regla. Corregido: el `-b 32768` vive ahora en `zz-blackbox-backlog.rules` (ordena despues de `audit.rules`), el instalador lo aplica con `augenrules --load` y `auditctl -b 32768`, y `--revert` lo retira en su propio bloque. `tests/test_enable_privileged_audit_backlog.py` (4 tests, con controles negativos). Pendiente de Luis: aplicar el archivo con sudo y medir `sudo auditctl -s | grep -E "backlog_limit|lost"` (esperado 32768).
