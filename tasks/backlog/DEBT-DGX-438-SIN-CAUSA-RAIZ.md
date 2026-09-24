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

## ARMADO el 2026-09-23 22:01, y el control lo confirmo

`sudo ./enable-privileged.sh` cargo la seccion 7 y su propia verificacion
respondio `reglas CARGADAS en el kernel (auditctl -l las ve)`.

El control negativo devolvio filas, que es lo que hacia falta:

```
  CUANDO              SENAL    EMISOR                          -> VICTIMA
  2026-09-23 22:01:46 SIGTERM  bash[1695154] humano auid=1000  -> bash[1695156]
  2026-09-23 22:01:48 SIGKILL  python[1657416] humano auid=1000 -> sleep[1698528]
  2026-09-23 22:02:47 SIGKILL  claude-desktop[130715] humano auid=1000 -> bash[1698596]
```

Emisor, victima, `exe` y `auid`, que es exactamente lo que faltaba desde el
2026-09-08.

**Estas tres capturas NO son el sujeto de esta ficha**, y se dice para que
nadie las lea como un cierre: las tres son gestion de procesos de la propia
herramienta (el SIGTERM es el del control, y los dos SIGKILL matan shells y
`sleep` de comandos que acababan de terminar), todas con `auid=1000` de una
sesion interactiva. El sujeto son procesos python de FONDO muriendo a
intervalos de 10-15 min sin que nadie lo pida. Eso no ha vuelto a pasar desde
que la regla esta puesta, y cuando pase quedara registrado con su emisor.

Efecto lateral medido: el sondeo de rustdesk **paro en seco** al cargar la
regla -- 408 eventos en los 60 s previos, **0 en los 30 s siguientes**. La
retencion del anillo deja de ser de 37 min, que era la condicion para que una
captura sobreviviera hasta que alguien la leyera.

### Un defecto que el control encontro en el propio instrumento

La primera lectura tras armar imprimio las dos capturas y debajo dijo
**NO ARMADO**. El estado se calculaba contando ruido de rustdesk en la ventana
que pide el usuario, y en esos 5 minutos cabian 417 eventos ANTERIORES a la
instalacion: el instrumento estaba capturando y su propia linea de estado lo
desmentia. Corregido a una ventana FIJA de 30 s (a 1.9/s el sondeo mas lento,
30 s de silencio son >=57 eventos que no llegaron), con su control en las dos
direcciones: ruido llegando ahora -> NO ARMADO con could_not_run 1; el mismo
ruido de hace 5 min -> armado con could_not_run 0.

Se anadio ademas un tercer veredicto, **NO SE PUDO DETERMINAR**: si rustdesk
no corre, nadie genera el ruido que la regla calla y un cero no distingue
"regla puesta" de "nada que callar". Antes eso se habria leido como armado.

## Lo que sigue sin saberse

Quien manda el SIGTERM del sujeto.

## Que espera esta ficha, reescrito el 2026-09-23

Hasta hoy esperaba un arreglo. **Ya no: espera una REAPARICION con el
instrumento puesto**, y el cambio se hace porque el sujeto dejo de aparecer.
Medido el 2026-09-23:

| medida | resultado |
|---|---|
| senales capturadas desde que se armo (~1 h) | 4 |
| de ellas con emisor DEMONIO, que es la forma del sujeto | **0** |
| muertes `code=killed, signal=TERM` en el journal, ultimos 10 dias | **2** (sep 16, sep 20) |
| `Atlas/uvicorn` en pie | 16 h 24 min |
| `simplecode.daemon` en pie | 16 h 24 min |
| `bb-usable` en pie | 11 h 45 min |

La ficha describe muertes "a intervalos irregulares (10-15 min)". Eso no esta
ocurriendo: los candidatos llevan dieciseis horas vivos y el journal registra
DOS muertes en diez dias, no cientos. Lo medido el 2026-09-08 se midio y no se
retira; lo que cambia es que el fenomeno no se reproduce hoy.

**Por que NO se cierra pese a eso.** Un cierre por no-reproducible tiraria el
contexto que mas cuesta reconstruir: tres sospechosos ya descartados con
evidencia (`systemd-oomd` ni instalado, la mitigacion de
`atom_gpu_telemetry.py` que usa SIGSTOP/SIGCONT, `liberation_watchdog.py` que
no manda kill) y dos todavia vivos (`earlyoom`, un cgroup ajeno con
`TimeoutStopSec`). Si reaparece sin ficha, ese trabajo se repite entero.

**Que la cierra ahora**, cualquiera de las dos:

1. **Reaparece y se identifica al emisor.** `bb sigterm` lo dara con nombre,
   `exe` y `auid`. Los dos sospechosos vivos mandan la senal por syscall, asi
   que los dos caen en la regla. Un emisor con `auid` sin poner es un demonio y
   se distingue de un vistazo de una sesion interactiva.
2. **Pasa el plazo sin una sola captura de demonio.** Entonces se cierra como
   no reproducible, con el instrumento puesto y el trigger de reapertura
   automatica: si `bb sigterm` caza un emisor demonio matando un python de
   fondo, vuelve a abrirse.

La diferencia con antes es que ahora las dos salidas son medibles. Hasta el
2026-09-23 esta ficha no podia cerrarse por ninguna via, porque no habia
instrumento que distinguiera "no ha pasado" de "no estabamos mirando".
