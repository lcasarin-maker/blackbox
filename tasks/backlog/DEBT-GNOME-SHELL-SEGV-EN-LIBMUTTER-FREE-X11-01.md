---
id: DEBT-GNOME-SHELL-SEGV-EN-LIBMUTTER-FREE-X11-01
kind: task
domain: SYSTEM
title: "gnome-shell (X11, mutter 46.2) muere con SIGSEGV dentro de libmutter/free y tira la sesion grafica con la app Claude"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-27
close_check: {"cmd": "python3 -c \"import subprocess,sys;o=subprocess.run(['coredumpctl','list','--no-pager','--since','-7d'],capture_output=True,text=True).stdout;sys.exit(1 if 'gnome-shell' in o else 0)\"", "expect": "exit_zero", "porque": "Especificacion pendiente: pasa solo si en los ultimos 7 dias no hay un coredump de gnome-shell. Hoy hay uno (2026-10-27 18:47), asi que falla; sobre un host con ese coredump el comando da rc=1."}
---

## Medido el 2026-10-27

- `coredumpctl list --since 18:30`: `gnome-shell` PID 4423, SIGSEGV, 2026-10-27 18:47:15 CST, 31.3 MB en
  `/var/lib/systemd/coredump/core.gnome-shell.1000.1ac9b61aee1349e0b299f56412e60d27.4423.1793148435000000.zst`.
- Pila del hilo 4423: `raise` -> gnome-shell+0x3828 (manejador de la senal) -> `libmutter-14.so.0+0xf604c` -> `__GI___libc_free`.
  La caida ocurre al liberar memoria dentro de mutter (corrupcion o doble liberacion).
- Journal: `gnome-shell[4423]: Error in size change accounting.` a las 18:46:32, 43 s antes, y `GNOME Shell crashed with signal 11` a las 18:47:15.
- Consecuencia: la sesion X11 se reinicia (`beforeQuit: handler fired` de la app Claude a las 18:47:19, `NVRM ... ZBC_REFERENCED` por el
  cierre de contextos GPU a las 18:47:19) y la sesion de Claude muere. La app Claude vuelve a las 18:47:34.
- No es OOM: el `Memory cgroup out of memory` de 18:40 a 18:48 cae en scopes `bb-cap-python3-*` (pruebas deliberadas de tope con `mmap`
  de 2 y 3 GiB), no en gnome-shell ni en la app Claude.
- Kernel 6.17.0-1032-nvidia, mutter 46.2, sesion X11 con driver NVIDIA, host marcado `Tainted: O`.

## Alcance

1. Obtener la pila con simbolos (`gdb` sobre el coredump con `libmutter-14-dbgsym`) y ubicar la funcion de mutter que libera.
2. Decidir entre actualizar mutter/gnome-shell, probar sesion Wayland o desactivar la extension implicada, con evidencia de cada una.
3. Registrar cuantas veces cae por semana (`coredumpctl list gnome-shell`) como serie, no como incidente aislado.

## Control negativo exigido

El `close_check` falla hoy (hay coredump del 2026-10-27). Debe pasar solo tras 7 dias sin coredump de gnome-shell.

## Limite

Un coredump, un host. No prueba que la causa sea el driver NVIDIA; la pila solo ubica la caida en mutter.
