---
id: IDEA-RESPETAR-MARCA-DE-DIAGNOSTICO-EN-PRUEBAS-DEL-PRODUCTO
kind: task
title: "Definir la marca de diagnóstico de la máquina que las pruebas de los proyectos consumidores respetan para no llamar al servidor de modelos"
status: open
severity: P3
origin: asserted
satd_family: MISSING_CAPABILITY
close_check: {"cmd": "python3 -m pytest tests/test_marca_diagnostico.py -q", "expect": "exit_zero"}
created: 2026-11-10
---

## Contexto

Mientras se diagnostica la máquina, las pruebas del producto que consumen el servidor de modelos local siguen llamándolo y ensucian la medición o lo reinician. Se pidió que exista una marca de modo diagnóstico, escrita por blackbox, que esas pruebas consulten para suspenderse o no llamar al servidor.

## Criterio de cierre

bb activa y desactiva una marca de diagnóstico con caducidad, documentada en SPEC.md con el contrato de lectura para los consumidores; una prueba demuestra que con la marca activa un consumidor de ejemplo no llama y sin ella sí.

## Origen

Idea de Luis en sus conversaciones con agentes, cosecha de ideas de own_chats del 2026-11-10. Ideas agrupadas: I-Chat-0865.
