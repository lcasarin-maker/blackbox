---
id: IDEA-DECLARAR-DUENIO-UNICO-DEL-MONITOREO-Y-AREAS
kind: task
title: "Declarar en el repo el dueño único del monitoreo de la máquina y el dueño de cada área (scripts, mejora, consolidación, reinicio)"
status: open
severity: P3
origin: asserted
satd_family: PROCESS_DEBT
close_check: {"cmd": "test -s docs/OWNERSHIP.md", "expect": "exit_zero"}
created: 2026-11-10
---

## Contexto

El monitoreo de la máquina (diagnóstico, caídas, recursos) se había repartido entre varios repos. Se pidió que viva como proyecto propio con un solo dueño, y que un agente de desarrollo pueda asumir un área con propiedad explícita para no pisar a otros. El repo no tiene un documento de propiedad por área.

## Criterio de cierre

Existe docs/OWNERSHIP.md con la lista de áreas y su dueño único, y la regla de que quien toca un área sin ser su dueño pide traspaso; cada pieza que mide o actúa sobre la máquina aparece en una sola fila.

## Origen

Idea de Luis en sus conversaciones con agentes, cosecha de ideas de own_chats del 2026-11-10. Ideas agrupadas: I-Chat-0863, I-Chat-0866.
