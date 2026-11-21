---
id: IDEA-TABULAR-BLOQUEADORES-Y-BOLETA-DE-DESBLOQUEO
kind: task
title: "Tabular el bloqueador de cada ficha abierta y preparar las boletas que desbloquean la mayoría sin reiniciar la máquina"
status: done
severity: P3
origin: asserted
satd_family: PROCESS_DEBT
close_check: {"cmd": "test -s docs/BLOQUEADORES-DEL-BACKLOG.md", "expect": "exit_zero"}
created: 2026-11-10
closed_at: 2026-11-21
---

## Contexto

Una parte del backlog espera una autorización o un despliegue que solo el dueño puede dar. Se pidió un bucle autónomo que ataque toda la deuda solventable, cierre con la comprobación antes y después, termine cuando una ola cierre cero fichas y nombre el bloqueador de cada ficha que quede abierta, y que diseñe cómo desbloquear la mayoría mediante boletas de voto o autorizaciones, sin reinicio.

## Criterio de cierre

Un documento lista cada ficha abierta con su bloqueador exacto (voto, despliegue con sudo, ventana del motor, hardware) y agrupa los bloqueadores en boletas de voto; cada boleta indica si exige reinicio; el conteo de fichas del documento coincide con tasks/backlog.

## Origen

Idea de Luis en sus conversaciones con agentes, cosecha de ideas de proyecto-local del 2026-11-10. Ideas agrupadas: I-Chat-0685, I-Chat-0686.

## Cierre

El [inventario](../../docs/BLOQUEADORES-DEL-BACKLOG.md) registra las 84 fichas que siguen abiertas, con evidencia por ID, decisiones, autorizaciones y requisito de reinicio. Las boletas quedan como propuestas. La [evidencia](../evidence/IDEA-TABULAR-BLOQUEADORES-Y-BOLETA-DE-DESBLOQUEO/README.md) registra el close_check y el control de cobertura con una fila eliminada.
