---
id: FEATURE-ATLAS-REINDEX-PAQUETE-GB10-01
kind: task
domain: INCIDENT_CAPTURE
title: "Que Atlas indexe el paquete GB10 entregado el 2026-10-11 y re-mida su eval con la ATOM fria"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-11
close_check: {"cmd": "grep -q hilo_378315_hard-power-off /home/lcasarin/projects/Atlas/rag/graphs/entity_graph.json", "expect": "exit_zero", "porque": "El grafo de entidades de Atlas contiene cada documento por nombre (36 de 36 investigaciones planas y 200 de 200 referencias de foro probadas el 2026-10-11). Mientras el archivo del hilo 378315 no aparezca en el grafo, Atlas no ha construido su indice con el paquete."}
---

## Que se entrego (2026-10-11, a peticion de Luis)

430 archivos en `Atlas/knowledge/investigations/gb10_cortes_2026-10-11/` (6.9 MB, 8 % de los 86 MB de su KB): 423 hilos del foro de NVIDIA con sus hallazgos y su texto integro, el catalogo destilado, cuatro dossiers y un reporte de incidente. SHA-256 de cada archivo en `docs/evidence/INVESTIGACION-GB10-2026-10-11/entrega_atlas_manifiesto.json` (0 diferencias medidas contra lo copiado). No se ejecuto el build de Atlas ni se hizo commit en su repo.

Comprobado: el indexador real de Atlas (`KnowledgeIndexer.index_markdown_files`) lee una muestra de 42 archivos y da 349 chunks, ninguno con metadatos no serializables a JSON; los 98 tests de Atlas que tocan `investigations/`, procedencia y penalizacion de derivados pasan. Los 3821 valores de frontmatter son cadenas (el primer envio tenia 1276 fechas sin citar y se corrigio).

## Consulta mientras tanto

Aunque el indice no incluya la carpeta, la consulta de texto de Atlas ya la ve: `tools.bulk_ops.find_in_kb` (la herramienta `grep_kb` del investigador) lee `knowledge/**/*.md` directamente. Medido el 2026-10-11: `MODS-020000600139` da 77 coincidencias, 52 en el paquete entregado y 25 en contenido que Atlas ya tenia. Lo que falta es la recuperacion semantica (RAG) y el grafo.

Se entrego una segunda carpeta, `gb10_mediciones_propias_blackbox_2026-10-11/` (5 archivos con las mediciones propias de la ATOM). El build debe cubrir las dos.

## Vias para correr el build

Atlas encola trabajos como JSON en `tools/liberation_queue/pending/` (esquema estricto, ver `FORMATO_JOBS.md`); su `liberation-watchdog` corre uno cuando la maquina se libera. Es la via que respeta su politica. Riesgo medido en su propio codigo: la guarda del build incremental puede caer a build COMPLETO si un archivo nuevo participa en su deduplicacion global.

## Por que no se indexo

El build de Atlas embebe con `bge-m3` en CUDA (`logs/index_build.jsonl`: `embedder_loaded device=cuda`) y la ATOM corta bajo carga de GPU sostenida. Hacerlo con la zona termica en 96-98 C era anadir el tipo de carga que esta ficha investiga.

## Pendiente

1. Con la maquina fria y sin vLLM sirviendo, correr `python tools/build_incremental.py` en Atlas.
2. El tamano del paquete completo en chunks NO esta medido (solo la muestra de 42 archivos). Medirlo antes de dar por buena la indexacion.
3. AGENTS.md de Atlas advierte que el umbral del router caduca con cada crecimiento grande del corpus: re-medir la eval congelada despues del build y comparar con la linea base. Los archivos van bajo `investigations/`, que Atlas ya marca como derivado y penaliza en el reranker (`derived_penalty=3.0`), para que no desplacen a los manuales.

## Estado 2026-10-11 -- ENCOLADO, NO CERRADO (espera a la cola de Atlas)

El `close_check` mide el grafo de entidades de Atlas, que solo cambia cuando el job corre; correrlo a mano esta prohibido (GPU, posible FULL build). Hecho en Atlas (commit `fee0a2b89`, sin push):

- `tools/liberation_queue/pending/79_00_reindex_paquete_gb10_20261011.json` (efecto `modifica`): `build_incremental.py --stats-json ...` y despues `build_entity_graph` + `save_graph`. El segundo paso es necesario y no estaba en la ficha: `build_incremental --graph-path` escribe el `KnowledgeGraph` (`knowledge_graph.json`), no `entity_graph.json`, que es el que mide el `close_check`.
- `tools/liberation_queue/pending/80_00_verifica_reindex_paquete_gb10_20261011.json` (efecto `verifica`, `verifica_a` el anterior): corre el `close_check` y MIDE los chunks de las dos carpetas en `rag/embeddings/index.json` (pendiente 2 de esta ficha). Sale 1 si falta el hilo o alguna carpeta tiene 0 chunks.
- Gate termico (`atom_gpu_telemetry.py --gate-termico`): `bloquea:false` justo antes de escribir los jobs; `bloquea:true` ("sostenida") minutos despues. El watchdog es quien decide cuando corre; encolar no genera carga.

Siguen abiertos: (a) que la cola corra los dos jobs y se lea `logs/reindex_paquete_gb10_20261011.txt` (modo `incremental` o `full`) y `logs/verifica_reindex_paquete_gb10_20261011.txt`; (b) el pendiente 3, re-medir la eval congelada contra la linea base despues del build, que NO se encolo porque `rebenchmark_v2_post_expansion.py` escribe un dictamen nuevo en `docs/agent_findings/` que exige su propia indexacion y una pareja de medicion; (c) el paquete sigue SIN versionar en el git de Atlas (esta ficha no lo pide). Se cierra cuando `80_00` pase y el `close_check` de arriba de rc=0.
