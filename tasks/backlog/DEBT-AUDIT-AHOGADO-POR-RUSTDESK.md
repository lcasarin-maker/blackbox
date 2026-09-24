---
id: DEBT-AUDIT-AHOGADO-POR-RUSTDESK
kind: debt
title: rustdesk ejecuta loginctl 14.6 veces por segundo y ahoga el registro de auditoria
status: open
severity: P2
origin: detected
detector: {"rule": "audit/execve-flood", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-09-23
close_check: {"cmd": "grep -q 'CERRADO' tasks/done/DEBT-AUDIT-AHOGADO-POR-RUSTDESK.md", "expect": "exit_zero", "porque": "cierre solo con evidencia real (comando + salida + control negativo) en el done, patron DEBT-DGX-438."}
---

## Que pasa

`rustdesk.service` sondea sesiones ejecutando `loginctl` en bucle. Medido el
2026-09-23 sobre `/var/log/audit`:

| fichero | bytes | ventana | tasa | execve de loginctl |
|---|---|---|---|---|
| audit.log.4 | 8388707 | 3701 s | 2.2 KiB/s | 6879 |
| audit.log.3 | 8388993 | 3694 s | 2.2 KiB/s | 6869 |
| audit.log.2 | 8388612 | 3676 s | 2.2 KiB/s | 6838 |
| audit.log.1 | 8388625 | 3453 s | 2.4 KiB/s | 6826 |
| audit.log   | 6843346 |  372 s | **18.0 KiB/s** | 5420 |

Dos emisores, los dos de `rustdesk.service` (`0::/system.slice/rustdesk.service`):

- `pid=3011`, `/usr/bin/rustdesk --service`, uid 0, 12 h 13 min de vida -- 1.9/s.
- `pid=1011421`, `/usr/share/rustdesk/rustdesk --server`, uid 1000, lanzado por
  `sudo` desde el anterior, 42 min de vida -- **14.6/s**.

Las lineas de comando exactas, sacadas del `PROCTITLE` del propio registro:
`/bin/loginctl show-session 2`, `show-session -p State 2`, `show-session -p Type 2`.

## Por que importa, con su medida

**99.8 % del registro de auditoria es este sondeo.** En `audit.log` habia 4731
eventos de syscall y 4724 eran `loginctl`. El resto del dia entero: 12632
`loginctl` frente a 59 `systemctl`, 8 `cron`, 1 `snap-confine`, 1
`systemd-detect-virt`, 1 `python3.12`, 1 `firmware-notifier`.

**El anillo se encoge.** Los 5 x 8 MiB cubrian 248 min al medir. Mientras el
hijo `--server` vive, a 18 KiB/s, el mismo anillo cubre **37 min**. Eso es lo
que convierte esto de molestia en defecto: DEBT-DGX-438 necesita cazar un
SIGTERM que llega cada 10-15 min, y con 37 min de retencion la captura
envejece antes de que nadie la lea.

**1.48 GiB/dia de escritura** a esa tasa.

**La regla que lo produce es `key="reboot_cmd"`** -- la regla estandar que
audita `loginctl`/`systemctl` para saber quien reinicio la maquina. O sea que
una regla de seguridad para cazar a una persona apagando la caja la esta
disparando un demonio quince veces por segundo.

## Como se mitiga hoy (no es el arreglo)

`enable-privileged.sh` seccion 7 instala
`/etc/audit/rules.d/10-blackbox-signals.rules`, que excluye SOLO la invocacion
de demonio:

```
-a never,exit -F arch=b64 -S execve -F exe=/usr/bin/loginctl -F auid=unset
```

El discriminador es `auid`, y esta medido con su control negativo el
2026-09-23: los 12934 eventos de rustdesk llevan `auid=4294967295` (unset), y
antes del control habia **0** eventos de `loginctl` con auid humano en tres
ficheros del anillo. Corrido `loginctl` desde una terminal, su evento quedo
con `ppid=1073636 auid=1000`. Para contraste, `systemctl` da 106 con
`auid=1000` frente a 10 unset: el campo discrimina de verdad. Lo que
`reboot_cmd` existe para ver -- una persona apagando la maquina -- se sigue
auditando.

**Eso tapa el sintoma en el registro. No toca la causa**, que es un demonio
ejecutando un binario 15 veces por segundo, con su coste de fork/exec y de
planificador aunque auditd deje de anotarlo.

## Que la cierra

Una de estas dos, con medida delante:

1. Que rustdesk deje de sondear a esa tasa (configuracion del propio rustdesk,
   o bajarle la frecuencia, o apagar el servicio si el escritorio remoto no se
   esta usando).
2. Una decision explicita de que el sondeo se queda, con el coste aceptado por
   escrito -- y entonces esta ficha se cierra como `void_wontfix`, no se deja
   abierta envejeciendo.

## Lo que NO se midio, y por eso no se afirma

No se midio el coste en CPU del sondeo, solo el coste en registro. 14.6
fork/exec por segundo no es gratis, pero cuanto cuesta en esta caja no se ha
puesto en un numero, asi que esta ficha no lo reclama. Tampoco se comprobo si
rustdesk tiene una opcion de configuracion que baje la frecuencia: se
diagnostico el emisor, no su manual.
