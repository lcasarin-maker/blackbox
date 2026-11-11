---
id: IDEA-REENCOLAR-TRABAJO-PERDIDO-TRAS-CAIDA-DE-LA-MAQUINA
kind: task
title: "Reencolar automáticamente los trabajos que una caída o un OOM dejó sin terminar, con el diagnóstico de la falla en el mismo registro"
status: open
severity: P3
origin: asserted
satd_family: MISSING_CAPABILITY
close_check: {"cmd": "python3 -m pytest tests/test_reencolar_tras_caida.py -q", "expect": "exit_zero"}
created: 2026-11-10
---

## Contexto

Se pidió un registro completo de cada falla de la máquina (crash, OOM) con diagnóstico automático y que lo que se perdió por la falla se reencole. El repo ya registra y diagnostica caídas, pero no existe un mecanismo que enliste los trabajos interrumpidos por una caída ni los devuelva a una cola.

## Criterio de cierre

Tras una caída simulada, un registro enlaza la falla con su causa y con la lista de trabajos interrumpidos, y un comando los reencola una sola vez (idempotente); una prueba corre el reencolado dos veces y comprueba que no duplica.

## Origen

Idea de Luis en sus conversaciones con agentes, cosecha de ideas de own_chats del 2026-11-10. Ideas agrupadas: I-Chat-0443.
