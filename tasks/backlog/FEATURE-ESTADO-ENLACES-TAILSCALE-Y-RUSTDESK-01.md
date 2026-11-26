---
id: FEATURE-ESTADO-ENLACES-TAILSCALE-Y-RUSTDESK-01
kind: task
domain: HARDWARE
title: "bb publica el estado de Tailscale y de RustDesk en la ATOM y en la Dell"
status: open
severity: P2
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-25
close_check: {"cmd": "python3 -m pytest -q tests/test_estado_enlaces.py", "expect": "exit_zero", "porque": "Mide que el lector de Tailscale y de RustDesk exista y pase su prueba. Hoy sale distinto de 0: el archivo de prueba no existe (medido 2026-11-25). La alarma de la Dell prueba hoy tres caminos como booleanos y nada publica el estado de la malla ni del servicio. Un pytest ausente cuenta como fallo, nunca como éxito. No mide el control negativo por mutación: lo revisa quien cierre."}
---

## Por qué

El acceso remoto a la ATOM depende de tres caminos: SSH en la red de casa, SSH por Tailscale y el escritorio remoto. `bb_alarma` los prueba cada 30 s y publica tres booleanos (`ssh-casa`, `ssh-tailscale`, `rustdesk`). Esos booleanos dicen que un camino responde y no por qué falla ni cómo se degrada. Tailscale puede estar arriba y caer a un relevo lento. RustDesk puede estar activo y sin puerto.

## Medido (2026-11-25)

- `tailscale status` en la ATOM lista cuatro dispositivos. La Dell figura `active; direct`. Un portátil lleva 13 días fuera de línea.
- El servicio de RustDesk está activo en la ATOM y el puerto de control escucha.
- `bb_alarma` reportó los tres caminos en `true` en su última muestra.

## Qué hacer

1. **Tailscale, desde `tailscale status --json`** en la ATOM y en la Dell: por dispositivo, nombre lógico, si está en línea, si el camino es directo o por relevo, última vez visto y bytes enviados y recibidos. Una malla con un dispositivo caído más de un umbral declarado se publica como degradada.
2. **RustDesk:** servicio activo, puerto escuchando, y si responde la comprobación de la alarma. Sin publicar identificadores ni claves de RustDesk.
3. **Publicar** ambos en el archivo único de `FEATURE-ESTADO-EXTERNO-UN-SOLO-CANAL-01`, con sello de tiempo y reglas de frescura.
4. **Aviso** cuando un camino pasa de directo a relevo sostenido o cuando RustDesk queda sin puerto, con la misma disciplina de ráfaga única que los demás avisos.
5. Una lectura que falla se publica como `COULD_NOT_RUN` con su causa. Nunca se asume que la malla está sana.

## Límites

Sólo lectura. No reinicia servicios: la reparación remota tiene su propia ficha, `FEATURE-DELL-BRAZO-DE-BB-REPARACION-REMOTA-01`. Ver también `DEBT-AUDIT-AHOGADO-POR-RUSTDESK`. El repo es público: ni direcciones ni nombres de equipos reales en el archivo publicado ni en las pruebas.

## Control negativo exigido

Pruebas que fallan al mutar: un dispositivo fuera de línea figura en línea, un relevo se publica como directo, un comando que falla publica «sana», un identificador de RustDesk llega al archivo.
