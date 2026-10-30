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

## Avance 2026-10-26 (serie por arranque desde el journal) y refutacion parcial

Duracion de `systemd-tmpfiles-setup.service` (lineas Starting/Finished del journal de cada arranque guardado) y userspace total:

| inicio del arranque | tmpfiles-setup | userspace |
|---|---|---|
| 10-12 18:33 | 2.9 s | 23 s |
| 10-12 18:45 | 0.4 s | 23 s |
| 10-12 21:57 | 0.7 s | 10 s |
| 10-13 14:07 | 5.5 s | 15 s |
| 10-16 10:56 | 22.0 s | 29 s |
| 10-17 17:07 | 40.4 s | 48 s |
| 10-19 08:12 | 30.4 s | 55 s |
| 10-24 23:53 | 95.4 s | 120 s |
| 10-26 19:58 | 108.2 s | 133 s |

La unidad `systemd-tmpfiles-setup` explica casi todo el crecimiento del userspace. No hay relacion con el `Cable removal` del CX7 (aparece
13 a 19 s tras el inicio de la unidad en 8 de 9 arranques, con tmpfiles de 0.4 a 108 s). Journal de este boot: 78.5 s de silencio total
entre `systemd-fsckd.service: Deactivated` y `Finished systemd-tmpfiles-setup.service`.

Banco de borrado en frio (`bench_frio.sh`, cache vaciada con `drop_caches=3`): 30000 archivos de 23 KiB en 0.52 s, 57193 archivos/s;
356222 archivos tardarian 6 s. El conteo de `/tmp` que use (356222) lo hizo `find` como usuario normal y NO ve los directorios de root
con modo 0700, entre ellos `/tmp/systemd-private-*` (que el arranque borra con la regla `R! /tmp/systemd-private-*`) y los
`systemd-private-*` de `/var/tmp`. Es el candidato siguiente y no esta medido: puede contener caches de servicios con millones de archivos.
Comando de medicion (root, solo lectura) en el reporte del 2026-10-26.

## Avance 2026-10-26: directorios privados de root descartados; captura del proximo arranque (voto de Luis)

`sudo find`/`du` sobre `/tmp/systemd-private-*` y `/var/tmp/systemd-private-*` (arranque actual, 1.5 h de uptime): cada directorio tiene 2
archivos y 8 KiB; ninguno se acerca al volumen que haria falta. Es el estado de este boot, no el que existia al apagar.
Voto de Luis: capturar lo que hace tmpfiles en el proximo arranque con un drop-in que ejecuta el mismo comando bajo `strace -f -c -w`.
Unidad base verificada: `ExecStart=systemd-tmpfiles --create --remove --boot --exclude-prefix=/dev`, sin `SystemCallFilter` y con
`CAP_SYS_PTRACE` en el conjunto de capacidades, `ProtectKernelTunables=no`. Prueba del envoltorio con `/bin/ls`: el resumen sale en 1.4 KB;
prueba del respaldo con un `strace` inexistente: el comando se ejecuta igual (rc=0). Resumen por arranque en
`/var/lib/blackbox/tmpfiles-boot-<epoch>.strace-c` (tiempo de pared por llamada al sistema). Reversion: renombrar el drop-in a `.off`
(systemd ignora ese sufijo) y `daemon-reload`.

## Causa medida 2026-10-27 (primer arranque con la captura strace)

Arranque 2026-10-27 18:17: `systemd-tmpfiles-setup` 48.8 s (`systemd-analyze blame`), userspace 1 min 13.7 s. Resumen
`/var/lib/blackbox/tmpfiles-boot-1793146659.strace-c`: **910211 llamadas `unlinkat`** (16.66 s de tiempo de llamada, 51.6 %),
205736 `getdents64` (9.03 s), 103259 `statx`; 1854060 llamadas en total. Antes de apagar, `find /tmp /var/tmp -xdev | wc -l` como usuario
dio **905474** entradas. Los 910211 borrados coinciden con ese conteo: la unidad pasa 48.8 s vaciando `/tmp` (ext4 raiz, no tmpfs) y
el tiempo sigue al numero de archivos que habia al apagar (356222 -> 108 s en el arranque anterior no encaja linealmente; el
arranque anterior arrastraba mas volumen que el que medi a los 34 min).

Quien llena `/tmp`: tras este mismo arranque, `/tmp` tenia 877 entradas; 45 s despues tenia 275741. De ellas, **274858 estan en
`/tmp/opencode`**: tres worktrees git de `<proyecto-A>` (`wt-pdf-f1`, `wt-pdf-f2`, `wt-pdf-f3`, ramas `swarm/pdf-f1..f3`, ~91.6k archivos
cada uno, checkout completo) creados por un enjambre de opencode (`opencode_desktop` con 133 s de vida al medir). Los tres sin cambios
sin commitear. Cada enjambre agrega otro juego y nadie lo limpia hasta el siguiente arranque.

Consecuencias:
1. Cada arranque borra esos worktrees; el registro en `<proyecto-A>/.git/worktrees/` queda `prunable`. Todo trabajo sin commitear
   en ellos se pierde en el reinicio.
2. El arranque lento viene del volumen de `/tmp`, no de una regla de tmpfiles ni del disco.

Correccion pendiente (vive en el lanzador del enjambre de opencode, otro proyecto): crear los worktrees fuera de `/tmp`
(p. ej. `~/.cache/opencode/` o `~/worktrees/`) y retirarlos con `git worktree remove` al terminar. Alternativa local en esta maquina:
`x /tmp/opencode` en un `tmpfiles.d` evita el borrado, y deja los ~275k archivos en disco entre arranques. La primera quita la causa; la
segunda solo oculta el sintoma en el arranque.

Control negativo: el `close_check` sigue fallando (userspace 73.7 s, no baja de 30 s). Se mide de nuevo en el arranque siguiente:
`/tmp` con pocas entradas al apagar debe dar `unlinkat` de miles y tmpfiles-setup de segundos.

## Procedimiento acordado 2026-10-27 (pendiente: el enjambre de opencode sigue trabajando; Luis no quiere tocarlo en vivo)

Lanzador localizado: no es un script, es el agente de opencode que obedece `<proyecto-A>/docs/architecture/RETOMAR_INGESTA_UNIFICADA_20261027.md`
(linea 48: `git worktree add /tmp/opencode/wt-pdf-fN swarm/pdf-fN`; lineas 52-53: salidas en `/tmp/opencode/cohort`) y los `run.py`/`run_v5.py` de
`tasks/evidence/ola1-{pdf,docx}-cohort-20261027/` (`/tmp/opencode/{cohort,docx-cohort,ingest-cache,docx-cache}`).
Cuando el enjambre pare: `mkdir -p ~/worktrees/<proyecto-A>` (hecho), `git worktree move /tmp/opencode/wt-pdf-fN ~/worktrees/<proyecto-A>/wt-pdf-fN`
para N=1..3, `git worktree list` sin `prunable`, cambiar las rutas del documento y de los scripts, y al terminar `git worktree remove`.
Hasta entonces, un reinicio borra los worktrees de /tmp: el trabajo commiteado en `swarm/pdf-f*` sobrevive, el no commiteado se pierde.

## Actualizacion 2026-10-28 13:32

El enjambre de opencode termino (ultimo registro 23:21 del 2026-10-27: `Your credit balance is too low`). Los worktrees `/tmp/opencode/wt-pdf-f*` y las ramas `swarm/*` ya no existen (`git worktree list` de `<proyecto-A>`: solo `main` y un worktree de codex); `/tmp` baja de 298779 a 105979 entradas. El procedimiento de mudanza queda para la proxima vez que un enjambre cree worktrees en `/tmp`; la causa del arranque lento (volumen de `/tmp` al apagar) sigue vigente.
