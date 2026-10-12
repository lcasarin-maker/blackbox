# Investigación GB10 del 2026-10-11: el conocimiento vive en Atlas

Decisión de Luis (2026-10-11): el conocimiento de esta investigación **no se guarda en blackbox**; vive en Atlas, que es la KB, para que se consulte allí y no exista una copia paralela e incompleta.

Dónde está: `~/projects/Atlas/knowledge/investigations/gb10_cortes_2026-10-11/` (438 archivos: 423 hilos del foro de NVIDIA con hallazgos y texto íntegro, la issue NVIDIA #1358, el catálogo destilado, los dossiers y el reporte de un incidente; `_procedencia/` trae scripts y resultados para auditar). `00_INDICE.md` de esa carpeta explica el contenido y sus límites.

Además, las mediciones propias de esta máquina (comentarios en la issue #1358, tabla de cortes con registro BERT, secciones medidas del README) se entregaron a `~/projects/Atlas/knowledge/investigations/gb10_mediciones_propias_blackbox_2026-10-11/` (5 archivos; SHA-256 en `entrega_atlas_mediciones_propias_manifiesto.json`).

Qué queda aquí:

- `entrega_atlas_manifiesto.json`: SHA-256 de los 430 archivos del primer envío (recibo de la entrega).
- `../INCIDENTES/`: un reporte real de `bb incident`, que es salida de blackbox.
- `../../../rules/firmas_gb10.json`: las firmas que `bb incident` busca en el journal. Es instrumento, y cada firma apunta al documento de Atlas que la respalda.

Cómo consultar: `python3 -c "from tools.bulk_ops import find_in_kb; ..."` desde Atlas, o `atlas "<pregunta>"` cuando su índice incluya la carpeta (ver `tasks/backlog/FEATURE-ATLAS-REINDEX-PAQUETE-GB10-01.md`).
