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

Identificar al emisor del SIGTERM. `bb sample` ya registra los PID de python de
fondo y `bb scan` compara muestras consecutivas para cazar la desaparicion.
