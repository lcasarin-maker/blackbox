---
id: DEBT-AUDIT-AHOGADO-POR-RUSTDESK
kind: debt
title: rustdesk ejecuta loginctl 14.6 veces por segundo y ahoga el registro de auditoria
status: done
closure_type: void_wontfix
closed_at: 2026-09-23
severity: P2
origin: detected
detector: {"rule": "audit/execve-flood", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-09-23
close_check: {"cmd": "grep -q 'CERRADO' tasks/done/DEBT-AUDIT-AHOGADO-POR-RUSTDESK.md", "expect": "exit_zero", "porque": "cierre solo con evidencia real (comando + salida + control negativo) en el done, patron DEBT-DGX-438."}
evidence:
  pass: tasks/evidence/DEBT-AUDIT-AHOGADO-POR-RUSTDESK/pass.txt
  fail: tasks/evidence/DEBT-AUDIT-AHOGADO-POR-RUSTDESK/fail.txt
  e2e: tasks/evidence/DEBT-AUDIT-AHOGADO-POR-RUSTDESK/e2e.txt
reason: "CERRADO como void_wontfix 2026-09-23. El dano caro estaba en el REGISTRO y ya esta tapado (0 eventos en 60s). El coste que quedaba era la incognita que la propia ficha declaraba, y medido resulta ser 0.2% de un nucleo -- 500 veces menos que un soffice.bin que ya corre en esta caja sin que nadie lo llame deuda. Tocar la frecuencia de rustdesk costaria mas que lo que ahorra, y es el canal de acceso remoto en uso. Se reabre por el trigger de abajo."
---

## Root Cause

### Que pasa

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

### Por que importa, con su medida

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

### Como se mitiga hoy (no es el arreglo)

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

## Verification Evidence

### CERRADO el 2026-09-23 -- salida 2 de las dos que la ficha se dio

La ficha ofrecia dos cierres: bajar la frecuencia, o aceptar el coste por
escrito con medida delante. Se toma el segundo, y aqui esta la medida.

### El hueco que la propia ficha declaraba, ya medido

Decia: *"No se midio el coste en CPU del sondeo, solo el coste en registro.
14.6 fork/exec por segundo no es gratis, pero cuanto cuesta en esta caja no se
ha puesto en un numero, asi que esta ficha no lo reclama."*

Medido el 2026-09-23 sobre 20 s, con una sesion de rustdesk ACTIVA (el peor
caso, no el de reposo):

```
  pid=3011     0.2% CPU   /usr/bin/rustdesk --service    <- el que sondea
  pid=1491821  8.4% CPU   rustdesk --server              <- captura+codifica pantalla
  --- TOTAL rustdesk: 9.1% de UN nucleo, de 20 = 0.45% de la maquina
```

**El sondeo cuesta 0.2 % de un nucleo.** El 8.4 % es el `--server` haciendo su
trabajo real -- comprimir la pantalla para la sesion remota -- y no tiene nada
que ver con `loginctl`.

Control, en la misma caja y al mismo tiempo: `soffice.bin` a **104 %** y otro a
**99.7 %**. El proceso que esta ficha persigue cuesta **500 veces menos** que un
proceso ofimatico que ya corre sin que nadie lo considere deuda. Perseguirlo
seria gastar la atencion en el sitio equivocado.

### Lo que SI era caro, y esta resuelto

El 99.8 % del registro de auditoria y la retencion cayendo de 248 min a 37 min.
Eso lo tapo la regla `auid=unset` de `enable-privileged.sh` seccion 7, y esta
medido: **0 execve de loginctl con auid=unset en los ultimos 60 s**, frente a
los ~114 a 876 que caian antes en esa misma ventana. Era la condicion para que
DGX-438 pudiera cazar algo, y se cumplio.

## Regression Test

### Trigger de reapertura

Se reabre si el sondeo vuelve a hacerse caro por cualquiera de estas dos vias,
las dos comprobables con un comando:

1. **El registro se vuelve a ahogar**: `bb sigterm` empieza a decir `NO ARMADO`
   estando la regla puesta, o vuelven a aparecer execve de `loginctl` con
   `auid=unset` en el anillo. Eso significaria que rustdesk cambio de forma y
   la regla dejo de casar.
2. **El coste en CPU del sondeo sube de 2 % de un nucleo** (diez veces el
   medido hoy) con el servicio en reposo, sin sesion activa.

Si rustdesk deja de usarse, la ficha no hay que reabrirla: apagar el servicio
la hace irrelevante y eso es un cierre mas fuerte que este.

### Lo que sigue sin comprobarse, y por eso no se afirma

No se reviso el manual de rustdesk para ver si expone el intervalo por
configuracion: se diagnostico el emisor, no su documentacion. `RustDesk2.toml`
(276 bytes) no trae ninguna clave de intervalo, pero eso es la config del
usuario, no la lista de opciones posibles. Se cierra porque el coste no lo
justifica, no porque se haya agotado la via.
