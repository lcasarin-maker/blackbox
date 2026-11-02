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

## Medido el 2026-11-02: pila con simbolos y segunda firma

`coredumpctl debug` sobre el core de 2026-11-02 16:53:04 (PID 4729) con `DEBUGINFOD_URLS=https://debuginfod.ubuntu.com` (sin instalar paquetes ni usar sudo), hilo 1:

```
#5  meta_input_device_x11_reset_scroll_info (device=0x0) at ../src/backends/x11/meta-input-device-x11.c:683
#6  meta_seat_x11_translate_event (xevent=..., seat=...) at ../src/backends/x11/meta-seat-x11.c:2664
#7  meta_backend_x11_handle_event ... meta-event-x11.c:71
```

- Es una desreferencia nula (`device=0x0`) en el backend X11 de mutter 46.2 al traducir un evento de XInput. Los cores del 2026-10-25 y del 2026-11-02 comparten `libmutter-14.so.0+0xf77a0`; el del 2026-10-27 cae en `+0xf604c` dentro de `free` (otra firma, la que describe la seccion anterior).
- Disparador probable: 34 s antes del crash de hoy todo el arbol USB (hub, teclado, receptor) se reenumero (`usb 1-1: new high-speed USB device number 24`, 16:52:29) y X anadio y quito los dispositivos de entrada; el 2026-10-25 hubo la misma reenumeracion 31 s antes (22:58:40 contra 22:59:11). Contraejemplo: el 2026-11-02 14:53:36-38 el mismo hub se desconecto y reconecto dos veces sin caida, asi que el hotplug no basta. El 2026-10-27 no hubo reenumeracion previa.
- Consecuencia medida el 2026-11-02: la sesion X cayo a las 16:53:37 y `chrome` y `antigravity` murieron con SIGTRAP a las 16:53:23 al perder X. La maquina no se reinicio (`uptime -s` 13:02:39).
- Serie por semana (`coredumpctl list gnome-shell`): 2026-10-25, 10-26 (SIGQUIT, reinicio manual), 10-27 y 11-02: tres SIGSEGV en 8 dias.

Pendiente del alcance 2 de arriba: decidir entre sesion Wayland (el X11 con el controlador NVIDIA es la combinacion en uso), actualizar mutter o evitar el hotplug; con evidencia de cada una.
