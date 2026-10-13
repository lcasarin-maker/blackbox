---
id: FEATURE-COSECHA-FORO-ETAPA2-LECTURA-POR-MECANISMO-01
kind: task
domain: GPU
title: "Etapa 2 de la cosecha del foro: lectura completa por mecanismo de los candidatos si/quizas de la ola 2"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-13
close_check: {"cmd": "grep -q '^etapa2_cobertura_completa: True' tasks/evidence/FEATURE-COSECHA-FORO-ETAPA2-LECTURA-POR-MECANISMO-01/cobertura-etapa2.txt", "expect": "exit_zero", "porque": "Escindida de FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01 al cerrarla (2026-10-13): la ola 1 (450 temas de las categorias 722/723) tiene cobertura completa verificada; falta la etapa 2 de la ola 2 (categoria 721 y Docker: 3043 temas descargados, 2593 triados, 416 si y 340 quizas). Cierra cuando exista cobertura-etapa2.txt con una linea `etapa2_cobertura_completa: True` producida por tools.verifica_cosecha_foro sobre los candidatos leidos completos."}
---

## Alcance (heredado de la etapa 2 de la ficha madre)
Leer completos, con el prompt de analisis de la ola 1 (`tasks/evidence/FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01/PROMPT-analisis-tema.txt`): (a) los candidatos `si` con respuesta de personal de NVIDIA, (b) un representante por mecanismo distinto, (c) los hilos de mas de 40 mensajes marcados si/quizas. Los candidatos salen de `ola2-triaje/` (416 si, 340 quizas). Cada mecanismo que valga la pena se implementa con interruptor off/observar/actuar y medicion antes de adoptarse.

## Costo declarado
Unos 756 candidatos; a ~5 temas por agente Sonnet son ~150 agentes. Conviene empezar por (a) y (b) y medir cuantos mecanismos nuevos aparecen antes de leer el resto (rendimiento decreciente esperado: la ola 1 dio un mecanismo accionado de 450 temas, el reloj atascado).

## Verificacion
El verificador `python3 -m tools.verifica_cosecha_foro` (sin `--triaje`) comprueba descarga completa, esquema, y que `posts_leidos` coincida con los mensajes reales del texto; un resultado con `lectura: parcial` o con lectura declarada de mas no es cobertura completa.
