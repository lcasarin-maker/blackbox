---
id: DEBT-ARRANQUE-USERSPACE-CRECE-TMPFILES-1M48-01
kind: task
domain: SYSTEM
title: "El tiempo de userspace del arranque crece en cada boot (9.6 s a 132 s) y systemd-tmpfiles-setup tarda 1 min 48 s"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-26
close_check: {"cmd": "python3 -c \"import re,subprocess,sys;o=subprocess.run(['systemd-analyze'],capture_output=True,text=True).stdout;m=re.search(r'\\+ (?:(\\d+)min )?([\\d.]+)s \\(userspace\\)',o);s=(int(m.group(1) or 0)*60+float(m.group(2))) if m else 1e9;sys.exit(0 if s<30 else 1)\"", "expect": "exit_zero", "porque": "Especificacion pendiente: pasa solo si el userspace del boot actual dura menos de 30 s. Hoy dura 132.6 s, asi que falla. Sin linea de userspace en la salida cuenta como fallo."}
---

## Medido el 2026-10-26 (`systemd-analyze` y journal por arranque)

Userspace por arranque, de los 8 guardados (firmware ~71 s y kernel ~4.5 s constantes en todos):
boot -6: 9.6 s, -5: 15.3 s, -4: 29.2 s, -3: 47.9 s, -2: 54.7 s, -1: 119.6 s, 0: 132.6 s.
Este boot: total 3 min 33 s. `systemd-analyze blame`: `systemd-tmpfiles-setup.service` 1 min 48.2 s (journal: iniciado 19:58:51,
terminado 20:00:39), `plymouth-quit-wait.service` 20.6 s, el resto 2.7 s o menos. Apagado previo: de las 19:56:10 (docker stop, el
motor vLLM mato su EngineCore a la fuerza) a las 19:57:09 en que cierra el journal: 59 s.

## Lo que se descarto (medido, sin root)

Archivos en las rutas que limpia tmpfiles: `/tmp` 52, `/var/tmp` 817, `/var/lib/systemd` 2120, `/var/lib/snapd` 798, `/var/cache` 423,
`/var/log` 349. Montajes: solo `portal` (FUSE de usuario) y el ext4 raiz. Errores de NVMe o de disco en el kernel de este boot: ninguno.
Reglas locales de tmpfiles.d: solo `screen-cleanup.conf`. Journal persistente 2.7 GiB.
Sin medir (exigen root): `/var/lib/docker` y `/var/lib/containerd` (`find` sin permiso, cuenta 1), y el dry-run de `systemd-tmpfiles`
(sin root sale con rc=1 tras una linea). La causa del crecimiento sigue desconocida.

## Alcance

1. Con root: `sudo systemd-tmpfiles --create --dry-run --verbose` con marca de tiempo por linea; ubicar la regla que consume los
   108 s (comando en el reporte del 2026-10-26).
2. Explicar por que el tiempo crece monotonicamente entre arranques (acumulacion en algun directorio, no un valor fijo).
3. Corregir la causa sin borrar datos ajenos: renombrar y registrar (ley de suspension), nunca eliminar.

## Control negativo exigido

El `close_check` falla hoy (132.6 s). Debe pasar solo con un boot real bajo 30 s, y el comando debe dar rc=1 sobre un boot lento.

## Avance 2026-10-26 (medido con strace y un banco de borrado)

- `systemd-tmpfiles --create --exclude-prefix=/dev` ejecutado ahora con `strace -f -ttt`: 2536 llamadas, **0.14 s** en total. La parte de
  creacion no explica los 108 s del arranque. (`--dry-run` y `--verbose` no existen en systemd 255: dos comandos mios fallaron por eso.)
- El arranque tambien ejecuta `--remove --boot`: las reglas `D /tmp 30d` y `D! /tmp/...` vacian `/tmp` al arrancar. `/tmp` vive en el
  ext4 raiz (`/dev/nvme0n1p2`), no en tmpfs.
- `/tmp` a los 34 min de este boot: **356222 archivos, 8.0 GB** (a los 3 min tenia 52): `cacheprof` 193892, `claude-1000` 70096, cuatro
  directorios `.tmpXXXXXX` de ~19.6k cada uno (78k), `simple-next-cargo` 7644, `profiles-work` 2293. Se llena con la actividad de la sesion
  y el siguiente arranque lo borra.
- Banco con cache caliente (30000 archivos de 23 KiB, `rm -rf` + `sync`): 43145 archivos/s, **8 s** extrapolado a 356222 archivos. Eso
  no alcanza los 108 s medidos; con cache fria (metadatos leidos del disco) el borrado puede ser mucho mas lento, y no esta medido.
- Pendiente: medicion en frio (`/tmp/claude-1000/.../scratchpad/bench_frio.sh`, necesita `sudo` para vaciar la cache) y comparar el
  tiempo de `tmpfiles-setup` del proximo arranque contra el conteo de `/tmp` antes de apagar.
