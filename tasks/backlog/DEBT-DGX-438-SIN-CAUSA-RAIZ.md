---
id: DEBT-DGX-438-SIN-CAUSA-RAIZ
kind: debt
title: Algo mata procesos de fondo con SIGTERM y no se sabe que
status: open
severity: P1
origin: detected
detector: {"rule": "systemd/unit-killed-by-TERM", "confidence": 1.0}
satd_family: UNKNOWN_FAILURE
created: 2026-09-08
close_check: {"cmd": "grep -q 'DGX-438 causa raiz' tasks/done/DEBT-DGX-438-SIN-CAUSA-RAIZ.md", "expect": "exit_zero"}
---

## Que pasa

Atlas registro en DGX-438 muertes de procesos python de fondo con `rc=143`
(SIGTERM) a intervalos irregulares (10-15 min), con o sin `setsid`, con o sin
`disown`. Sin causa raiz.

El 2026-09-08 se sumo un caso con dos victimas casi simultaneas:
`atom-gpu-telemetry.service` murio `(code=killed, signal=TERM)` a las 07:41:02 y
el vLLM del gateway cayo a las 07:41:27, 25 segundos despues.

## Descartado con evidencia

- `systemd-oomd`: `is-enabled` devuelve `not-found`, ni instalado.
- La mitigacion de `atom_gpu_telemetry.py`: usa SIGSTOP/SIGCONT, no mata.
- `liberation_watchdog.py`: no envia kill a nadie; el SIGTERM que documenta es el
  que RECIBE por `TimeoutStartSec=245min`, y 245 min no encaja con 10-15.

## Vivos

`earlyoom` y un cgroup ajeno con `TimeoutStopSec`. Tampoco se ha descartado que
el caso del 07:41 lo causara esta misma sesion con alguna operacion de esa
franja: no se identifico quien envio la senal.

## Que la cierra

Identificar al emisor del SIGTERM.

## Instrumento, puesto el 2026-09-23

Hasta hoy la ficha apuntaba a `bb sample`/`bb scan`, y eso no podia cerrarla:
la muestra se toma del lado de la VICTIMA, asi que ve que un proceso
desaparecio y nunca quien lo mato. El emisor solo existe durante el syscall.

El unico sitio de esta caja que guarda esa pareja es el registro de auditoria.
Peldano 4 de la escalera -- la plataforma ya lo hace: `auditd` corre
(`active`/`enabled`), persiste, rota, y `/var/log/audit` es `root:adm`, o sea
que este usuario lo LEE sin root, la misma dependencia de grupo que `bb` ya
tiene para `journalctl -k`. No hacia falta un demonio nuevo con bpftrace.

Lo que faltaba era la regla, no el demonio. Medido el 2026-09-23:
`grep -c "syscall=62\|syscall=200\|syscall=234"` sobre `audit.log` y
`audit.log.1` da **0**, y `grep -c "sig=15\|SIGTERM"` da **0** -- cero eventos
de kill en las 4 h 08 min que cubria el anillo. No es que nadie matara: es que
nadie miraba.

- `sudo ./enable-privileged.sh` seccion 7 instala la regla (`kill`/`tkill` con
  la senal en `a1`, `tgkill` con la senal en `a2` -- una sola regla con `-F a1`
  habria dejado pasar todo `tgkill` sin que nada lo dijera).
- `bb sigterm ["hace X"]` lee el registro y empareja el `SYSCALL` (emisor:
  pid/comm/exe/auid) con el `OBJ_PID` (victima: opid/ocomm) por el id de
  evento, que es lo unico que los relaciona.

Los dos sospechosos vivos caen ahi: `earlyoom` manda la senal por syscall, y un
cgroup ajeno con `TimeoutStopSec` la manda via systemd, tambien por syscall.
El `auid` del emisor separa ademas demonio de humano, que descarta de entrada
la hipotesis abierta de que el caso del 07:41 lo causara una sesion a mano.

**Controles corridos** (2026-09-23), porque un lector que solo sabe imprimir
cero no es un lector:

| control | salida |
|---|---|
| positivo: log con 2 eventos, ventana de 10 min | 2 filas, emisor -> victima, `could_not_run: 0` |
| negativo: los mismos eventos con 2 h, ventana de 10 min | `0 senales registradas` |
| y de nuevo con ventana de 3 h | vuelven las 2 filas |
| sobre el registro REAL, hoy | `0 senales` + **`NO ARMADO`** + `could_not_run: 1` |

Esa ultima fila es la mitad del valor del subcomando: hoy el instrumento aun no
esta armado, y `bb sigterm` lo DICE en vez de devolver un cero limpio. El
discriminador no es "cero eventos con mi clave" -- eso es justo lo ambiguo --
sino el efecto de la otra regla que instala la misma seccion: si el sondeo de
rustdesk sigue cayendo en el anillo, la seccion 7 no esta cargada.

## Lo que hubo que resolver antes, y es su propia ficha

El anillo de auditoria estaba ahogado: **99.8 % de sus eventos eran
`/usr/bin/loginctl` ejecutado por `rustdesk.service` a 14.6 por segundo**, lo
que encoge la retencion de 248 min a 37 min mientras vive su hijo `--server`.
A esa retencion, una captura de kill envejece antes de que nadie la lea. La
seccion 7 excluye ese ruido con `auid=unset` sin cegar la regla `reboot_cmd`
que lo produce; la causa queda en `DEBT-AUDIT-AHOGADO-POR-RUSTDESK`.

## Lo que sigue sin saberse

El instrumento esta escrito y probado; **no esta armado**, porque la regla
necesita root y el `sudo` lo corre el usuario. Hasta que corra
`sudo ./enable-privileged.sh` y el control negativo de ahi
(`sleep 300 & kill -TERM $!` -> `bb sigterm '5 minutes ago'`) devuelva una fila,
esta ficha sigue sin instrumento en la practica, y este bloque no dice otra
cosa.
