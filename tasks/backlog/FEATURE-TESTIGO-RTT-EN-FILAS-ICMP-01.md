---
id: FEATURE-TESTIGO-RTT-EN-FILAS-ICMP-01
kind: task
domain: HARDWARE
title: "Las filas de ping ICMP del testigo registran la latencia, no sólo si respondió"
status: open
severity: P3
origin: measured
satd_family: BLIND_INSTRUMENT
created: 2026-11-25
close_check: {"cmd": "python3 -m pytest -q tests/test_testigo_rtt_icmp.py", "expect": "exit_zero", "porque": "Mide que las filas ICMP del testigo incluyan `rtt_ms` y que la prueba lo verifique. Hoy sale distinto de 0: el archivo de prueba no existe (medido 2026-11-25) y las filas `fuente: icmp` de `ping.jsonl` traen `ok` sin `rtt_ms`. Un pytest ausente cuenta como fallo, nunca como éxito. No mide el control negativo por mutación: lo revisa quien cierre."}
---

## Medido (2026-11-25)

En una ventana de 1,499 s, `ping.jsonl` del testigo tiene 1,500 filas `fuente: tcp` y 1,500 `fuente: icmp`, todas con `ok: true`. Las filas TCP traen `rtt_ms` (p50 15 ms, p95 16 ms). Las filas ICMP no traen `rtt_ms`: sólo `ok`. Hoy no hay serie de latencia ICMP, y comparar ICMP con TCP, que daría información sobre el camino y el servicio, no es posible.

## Qué hacer

1. En `tools/testigo/bb_testigo.py`, registrar `rtt_ms` en cada fila ICMP cuando el comando `ping` lo reporte. Si el sistema no lo da, `rtt_ms: null` con `ok` y el motivo, nunca 0.
2. Mantener el formato de las filas existentes: sólo se añade el campo, sin romper a `tools/observador_ping.py` ni a `reboot_verdict.py`.
3. Prueba con un `ping` simulado en sus tres casos: responde con RTT, responde sin RTT parseable, no responde.

## Límites

Cambiar `bb_testigo.py` exige redesplegarlo en el equipo testigo, igual que el 2026-11-18. Eso modifica otro equipo y requiere orden expresa de Luis, con motivo y comando. Se despliega junto con la ficha del archivo único (`FEATURE-ESTADO-EXTERNO-UN-SOLO-CANAL-01`) para hacer un solo redespliegue.

## Control negativo exigido

Pruebas que fallan al mutar: un RTT no parseable se registra como 0, la fila ICMP vuelve a salir sin el campo, un `ok: false` lleva un RTT inventado.
