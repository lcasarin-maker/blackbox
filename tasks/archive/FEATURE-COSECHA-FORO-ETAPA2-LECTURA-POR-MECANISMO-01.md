---
id: FEATURE-COSECHA-FORO-ETAPA2-LECTURA-POR-MECANISMO-01
kind: task
domain: GPU
title: "Etapa 2 de la cosecha del foro: lectura completa por mecanismo de los candidatos si/quizas de la ola 2"
status: done
closed_at: 2026-10-13
closure_type: relocated_prior_verification
reason: "Los 756 candidatos si+quizas de la ola 2 (416+340) tienen lectura completa mensaje por mensaje y cobertura verificada sobre el sujeto (cobertura-etapa2.txt: 756 descargados, 0 sin resultado, 0 parciales, 0 declarados de mas; tres controles negativos dan rc=1). Los mecanismos nuevos se fichan aparte."
evidence: {"pass": "tasks/evidence/FEATURE-COSECHA-FORO-ETAPA2-LECTURA-POR-MECANISMO-01/pass.txt", "fail": "tasks/evidence/FEATURE-COSECHA-FORO-ETAPA2-LECTURA-POR-MECANISMO-01/fail.txt", "e2e": "tasks/evidence/FEATURE-COSECHA-FORO-ETAPA2-LECTURA-POR-MECANISMO-01/e2e.txt"}
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

## Avance 2026-10-13: tramo 1 (60 de los 416 candidatos `si`)
Seleccionados por relevancia para esta ATOM (senales de un solo nodo: OOM, drop_caches, memoria unificada, reloj, apagado en seco, fieldiag, watchdog, firmware; sin multinodo ni CX7 en pareja; 223 cumplian, se leyeron los 60 con mas senales) y leidos completos por 12 agentes Sonnet, mensaje por mensaje. Verificado sobre el sujeto con `python3 -m tools.verifica_cosecha_foro`: 60 descargados, 0 sin resultado, 0 parciales, 0 declarados de mas; controles negativos corridos (sin un resultado -> rc=1; `posts_leidos` inflado -> rc=1). Resultado: 31 de utilidad alta, 25 media, 4 baja; 37 mecanismo, 22 diagnostico, 1 anuncio oficial. Evidencia: `tasks/evidence/FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01/ola2-etapa2-tramo1/` (60 resultados, `cobertura-tramo1.txt`, `catalogo-mecanismos-alta.txt`). Los mecanismos son afirmaciones de usuarios y de personal del foro, NO verificadas aqui.
Quedan 356 candidatos `si` y 340 `quizas`; el rendimiento esta confirmado como decreciente (la mayoria de los mecanismos de alta utilidad del tramo ya estaban fichados: tope de reloj, tope de CPU, desconexion AC tras firmware, journal del arranque previo, earlyoom), asi que la etapa 2 solo cierra con `etapa2_cobertura_completa: True` sobre todos los candidatos o con una decision explicita de acotarla.

## Avance 2026-10-13: cierre (tramo 2 y resto)
Tramo 2: 60 candidatos `si` mas. Resto: los 636 candidatos que faltaban (356-60 `si` y 340 `quizas`), leidos completos por 106 agentes Sonnet de 6 temas cada uno, mensaje por mensaje. Respuesta del usuario a la pregunta de acotar: "Leer todo lo que falta". Resultado del resto: 32 de utilidad alta, 234 media, 329 baja, 41 ninguna; 280 mecanismo, 221 diagnostico, 68 anuncio oficial, 51 pregunta sin respuesta, 16 ruido. Catalogo: `tasks/evidence/FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01/ola2-etapa2-resto/catalogo-mecanismos-alta.txt` (generado de los resultados, una IP privada de usuario sustituida por `<ip>`). Los mecanismos son afirmaciones del foro, NO verificadas aqui.

## Root Cause
La etapa 2 estaba abierta porque solo 120 de 756 candidatos tenian lectura completa; el rendimiento decreciente justificaba acotar, pero la decision del usuario fue leer todo.

## Regression Test
`tools/verifica_cosecha_foro.py` con `tests/test_verifica_cosecha_foro.py` (conteo exacto de mensajes `POST n |`, lectura parcial y declarada de mas); el cierre repite el verificador sobre la union de los tres conjuntos.

## Verification Evidence
fail.txt: el close_check sobre una copia con la linea en False sale 1; pass.txt: sobre cobertura-etapa2.txt sale 0; e2e.txt: el verificador sobre los 756 da `cobertura_completa: true`. Controles negativos corridos en cobertura-etapa2.txt: sin un resultado rc=1, `posts_leidos` inflado rc=1, directorio de hilos equivocado rc=1.
