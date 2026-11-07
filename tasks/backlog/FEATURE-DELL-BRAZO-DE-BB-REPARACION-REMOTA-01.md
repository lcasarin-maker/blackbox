---
id: FEATURE-DELL-BRAZO-DE-BB-REPARACION-REMOTA-01
kind: task
domain: RECOVERY
title: "La Dell ejecuta por orden de bb la reparacion de la red de la ATOM (tailscaled, NetworkManager, RustDesk) cuando la alarma la ve caida"
status: open
severity: P1
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-06
close_check: {"cmd": "grep -qx reparacion_remota_probada tasks/evidence/FEATURE-DELL-BRAZO-DE-BB-REPARACION-REMOTA-01/medicion.txt", "expect": "exit_zero", "porque": "Falla hoy: la alarma de la Dell (tools/testigo/bb_alarma.py) solo avisa; no repara. Cierra con una medicion en la que se detiene a proposito tailscaled en la ATOM (o un camino equivalente), la Dell lo ve caido, ordena la reparacion por el canal de bb, el camino vuelve y queda el registro, con el interruptor en actuar y el mismo caso con el interruptor en observar sin reparar (control negativo)."}
---

## Por que

El 2026-11-05 `tailscaled` y `NetworkManager` murieron a las 19:59 (earlyoom los mato; systemd se rindio por `Start request repeated too quickly`) y quedaron caidos 17,6 h. Hoy el reinicio ilimitado de systemd y el `--avoid` de earlyoom cubren ese camino exacto, y la alarma de la Dell avisa. Falta lo que cubre el siguiente camino distinto: algo que repare sin esperar a Luis.

## Decision que la habilita

`DECISIONS.md` 2026-11-06: bb manda y la Dell es su brazo; la Dell ejecuta, bb decide, con interruptor `off`/`observar`/`actuar`, registro y tope.

## Alcance

1. Un comando de bb en la ATOM, `bb reparar-red`, con interruptor `reparar_red`: mira `tailscaled` y `NetworkManager`, y en `actuar` reinicia SOLO los que no estan activos (`reset-failed` y `restart`). Lo que pide root pasa por un script sellado de `bb-root-run` (`adopted/root-scripts/red-reparar.sh`, sin argumentos), que Luis despliega con sudo.
2. La alarma de la Dell (`bb_alarma.py`) gana una accion opcional por camino: tras `umbral` fallos de `ssh-tailscale` o `rustdesk` con `ssh-casa` vivo, ejecuta por `ssh atom` el comando de bb, con tope (una orden cada 10 min) y deja la orden y su resultado en `alarma.jsonl` y en el aviso de ntfy.
3. Pruebas: la decision (cuando ordenar y cuando no) es pura y lleva control negativo; la orden se prueba en `observar` antes de `actuar`.

## Limite

Si `ssh-casa` tambien esta caido, la Dell no puede entrar: el camino sigue siendo el aviso por ntfy y el reinicio por `sudo panic` o fisico. Esta ficha no cubre un cuelgue del kernel.

## Decision de Luis, 2026-11-06 (boleta «Reparacion»): no se construye ahora

- **Decidido:** se deja abierta y se pasa al limite de memoria de GPU. Motivo del voto: ninguno adicional (eligio la opcion recomendada).
- **Evidencia que la sustenta:** `systemctl show tailscaled NetworkManager` da `Restart=always RestartUSec=2s StartLimitIntervalUSec=0` (el drop-in `bb-reinicio-ilimitado.conf` del 2026-11-06); el `--avoid` de earlyoom incluye `tailscaled|NetworkManager|rustdesk`; la alarma de la Dell avisa tras 3 fallos. Eso cubre el camino exacto del 2026-11-05.
- **Costo medido que la frena:** `python3 -m tools.bb_root_manifest --check` da `aprobados iguales: 10, cambios: 2` (`earlyoom-proteger` cambiado y `nvidia-bug-report` sin aprobar); la re-aprobacion con sudo aprobaria ambos a la vez. `tests/test_bb_root_manifest.py` afirma 12 scripts en tres sitios (`len(SCRIPTS) == 12`, «los doce scripts», `aprobados iguales: 12`).
- **Descartado por ahora:** construirla completa (script sellado `red-reparar`, llave de solo-ese-comando para la Dell, accion en la alarma) y la version sin root que solo reinicia RustDesk (no cubre `tailscaled` ni `NetworkManager`).
- **Reabrir si:** `tailscaled` o `NetworkManager` vuelven a quedar caidos por una causa que el reinicio ilimitado no resuelve, o si la alarma avisa de una caida de red que requirio la mano de Luis.
