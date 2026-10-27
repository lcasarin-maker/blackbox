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
