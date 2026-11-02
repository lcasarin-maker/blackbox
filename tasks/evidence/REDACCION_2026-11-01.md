# Redacción de evidencia 2026-11-01

Decisión de Luis (2026-11-01): este repositorio es público y debe quedar limpio de temas ajenos. En evidencia NO se
reescribe prosa: cada token ajeno (nombres de siete proyectos o servicios que no son de este repositorio, sin
distinguir mayúsculas; la lista vive en el script) se sustituye por el marcador `[externo]`. Script
`mudanza_neutraliza.py` (modo evidencia), versionado fuera de este repositorio.

- Archivos de evidencia redactados: 97. Tokens sustituidos: 272.
- Los 29 JSON redactados se comprobaron con `python3 -m json.tool` y sin claves duplicadas nuevas.
- Incluye `docs/evidence/INCIDENTES/bb-2026-10-11-54b71618.json` y `.md` (informe generado, tratado como evidencia): una clave que nombraba al proyecto ajeno pasa a `"[externo]"`.
- Las columnas `sha256 antes/después` son los 12 primeros hex del archivo; el hash antes es el del commit `1448660`.

## Lo que NO se tocó, y por qué

- **Hash citado por otros archivos** (procedencia; la guarda `tests/test_sin_datos_privados.py` ya declara que esas evidencias no se reescriben): 13 archivos de la lista de entrada tienen su sha256 escrito en otro archivo versionado. 12 no traían ningún token fuera de lo exento y quedan igual. UNO traía 2 menciones y queda SIN redactar para no romper esa cadena: `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/simplecode-producer-validation/reviewed-producer.redacted.patch` (su hash lo citan 14 archivos). Si Luis prefiere redactarlo igual, hay que re-sellar esos 14 hashes.
- **URL y títulos de terceros que contienen una de las palabras**: el hilo 380553 del foro de NVIDIA (`tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/{items,batch_00,verdict_00}.json`) y varios hilos de `tasks/evidence/FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01/` (362210, 369263, 383477) llevan en el título el nombre de un producto de terceros que coincide con una de las palabras. No son un proyecto ajeno de este repositorio y se dejan literales.

## Archivos redactados

| Archivo | Tokens | sha256 antes | sha256 después |
|---|---|---|---|
| `docs/evidence/INCIDENTES/bb-2026-10-11-54b71618.json` | 23 | `3588cf518185` | `d636c6350b71` |
| `docs/evidence/INCIDENTES/bb-2026-10-11-54b71618.md` | 23 | `a3801b31b6c9` | `30d5c9e5bf67` |
| `tasks/evidence/BB-INSTRUMENTS-2026-10-03/h1-movement-proof.json` | 3 | `bf21ab712d95` | `c6c1d2be5731` |
| `tasks/evidence/CLASIFICACION-FICHAS-APLICABILIDAD-20261013/PROMPT-clasificador.txt` | 1 | `58c897fd53d5` | `a68e69cbfd35` |
| `tasks/evidence/CLASIFICACION-FICHAS-APLICABILIDAD-20261013/clasificacion.json` | 15 | `b579fed06bb7` | `801ae0f8b775` |
| `tasks/evidence/CLEAN-2026-10-03/h1-renew-normalized.json` | 3 | `8217c6308daf` | `ba16f433c118` |
| `tasks/evidence/CLEAN-2026-10-03/h1-renew-original.json` | 3 | `9e9bb0f8740c` | `24c36875dd3a` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-readonly-root-integrated/batch-05.json` | 3 | `2eee1b7c20f3` | `406c73d32500` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/simplecode-producer-validation/reviewed-producer.patch` | 2 | `396d13bd922c` | `90fc53c66afe` |
| `tasks/evidence/DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01/audit-2026-10-10.md` | 4 | `1dd4aefe5287` | `e5d2b52031ec` |
| `tasks/evidence/DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01/calibracion-escalon.txt` | 1 | `8fe629e639a3` | `6e99290097d7` |
| `tasks/evidence/DEBT-DOCKER-FUERA-DEL-TECHO/antes.txt` | 2 | `bae3c2ea42ae` | `367a05e17b79` |
| `tasks/evidence/DEBT-DOCKER-FUERA-DEL-TECHO/despues.txt` | 1 | `a9f861a5aa91` | `c4c8a51d638c` |
| `tasks/evidence/DEBT-DOCKER-SLICE-TOPE-VS-TOPES-DE-CONTENEDORES-01/medicion.txt` | 6 | `b4adf6f4b2b4` | `b92688b42616` |
| `tasks/evidence/DEBT-EARLYOOM-DESARMADO-POR-EL-AND-DEL-SWAP/fail.txt` | 1 | `abe5244ff45e` | `0beb10dc797d` |
| `tasks/evidence/DEBT-H1-RELEASE-CLAIMS-01/final-results.json` | 12 | `59b94b529050` | `cd1b14b1c14a` |
| `tasks/evidence/DEBT-H1-RELEASE-CLAIMS-01/final-source.json` | 6 | `ec341b02cde0` | `0510f2e6d9e5` |
| `tasks/evidence/DEBT-H1-RELEASE-CLAIMS-01/host-evidence/sample-2026-09-25-line-451.json` | 2 | `407041d18acf` | `23c8cc074b21` |
| `tasks/evidence/DEBT-H1-RELEASE-CLAIMS-01/host-evidence/snapshot-2026-09-25-050801.txt` | 2 | `dd0ac8063d87` | `75fb1b9234e7` |
| `tasks/evidence/DEBT-H1-RELEASE-CLAIMS-01/source.json` | 6 | `2cc067fc3be2` | `9f52fd8fc064` |
| `tasks/evidence/DEBT-NO-COVER-ATOM-GPU-TELEMETRY-1676/e2e.txt` | 1 | `7d7c8cb1354c` | `78a3fc7931f1` |
| `tasks/evidence/DEBT-NO-COVER-MUTACION-ALCANZA-66/e2e.txt` | 1 | `c814e1d051ba` | `88b6834c8571` |
| `tasks/evidence/DEBT-NO-COVER-PRESUPUESTO-MEMORIA-497/e2e.txt` | 1 | `543d64513bfc` | `d7d3c2175150` |
| `tasks/evidence/DEBT-PUSHES-ACUMULADOS-BLOQUEADOS-POR-DEUDA-ABIERTA-01/e2e.txt` | 1 | `72f88cdfd24b` | `dc172dd56c88` |
| `tasks/evidence/DEBT-PUSHES-ACUMULADOS-BLOQUEADOS-POR-DEUDA-ABIERTA-01/pass.txt` | 2 | `c6bd7bcac54b` | `4206d907c696` |
| `tasks/evidence/DEBT-PUSHES-ACUMULADOS-BLOQUEADOS-POR-DEUDA-ABIERTA-01/publicacion.txt` | 1 | `ec840c868a14` | `41438b1c59ac` |
| `tasks/evidence/DEBT-RELOJ-ARRANQUE-GPU-OCUPADA-POR-EL-MOTOR-01/e2e.txt` | 1 | `056e7a09b0df` | `dd82b8d745d9` |
| `tasks/evidence/DEBT-REVISION-DE-LO-INSTALADO-Y-LO-USADO-01/informe.txt` | 2 | `8a3a82729f93` | `ca3b50fb9ac8` |
| `tasks/evidence/DEBT-SIN-ARNES-DE-MUTACION/fail.txt` | 1 | `12ab5230fbcb` | `bc3574eb9cf1` |
| `tasks/evidence/DEBT-VERIFICAR-DGX-30-OOM-LLAMADORES-CONCURRENTES-01/e2e.txt` | 1 | `94976c6a1e5e` | `8a0469b0a2f0` |
| `tasks/evidence/DEBT-VERIFICAR-DGX-30-OOM-LLAMADORES-CONCURRENTES-01/verificacion.txt` | 9 | `d8e76bff000f` | `fb76264c7cad` |
| `tasks/evidence/DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-CX7-POSTHOTPLUG-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01/pass.txt` | 1 | `9d8a1e046378` | `cc054e344902` |
| `tasks/evidence/DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-MEMORY-RECOVERY-SOAK-01/pass.txt` | 1 | `797929c1e71e` | `a1ca6e08e6a4` |
| `tasks/evidence/DELTA-FORUM-MUSE-GLIMMER-DFLASH-MAX-SEQS-GATE-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01/pass.txt` | 1 | `d1ea1474ba80` | `a3dc2a91f978` |
| `tasks/evidence/DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01/pass.txt` | 1 | `ac7cb8308a57` | `c026fa09fa82` |
| `tasks/evidence/DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01/pass.txt` | 1 | `a48bbc2f2de5` | `198d4599dc7d` |
| `tasks/evidence/DELTA-FORUM-QWEN38-LONG-RUN-JSON-CORRECTNESS-CANARY-01/pass.txt` | 1 | `70389e90df71` | `dc0a74ffad1e` |
| `tasks/evidence/DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-ROOT-CONTAINER-EFFECTIVE-BUILD-AND-OFFLINE-GATE-01/pass.txt` | 9 | `0c91957ac3b3` | `c147d98f05ba` |
| `tasks/evidence/DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01/pass.txt` | 1 | `238988375db5` | `67563d24f29e` |
| `tasks/evidence/DELTA-ROOT-GX10-SOC-EC-CABLE-RECOVERY-CANDIDATE-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-ROOT-MIMO-OVERLAY-AND-PREFILL-FAIRNESS-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01/pass.txt` | 1 | `6a6d3f4d319c` | `878087fac9a8` |
| `tasks/evidence/DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01/pass.txt` | 1 | `4ce8fd04aa78` | `08544a6fc913` |
| `tasks/evidence/DEUDA-ABIERTA-CLASIFICACION-20261013/bloqueo-por-ficha.tsv` | 8 | `6a3c08ba7f8d` | `bdc4bff114d6` |
| `tasks/evidence/DEUDA-ABIERTA-CLASIFICACION-20261013/close_checks.tsv` | 3 | `473321f596eb` | `f016928ca07c` |
| `tasks/evidence/DEUDA-ABIERTA-CLASIFICACION-20261013/construible.tsv` | 2 | `e12f339d73dc` | `f3368b3c13bc` |
| `tasks/evidence/DEUDA-ABIERTA-CLASIFICACION-20261013/construible/revision-019.json` | 1 | `a6627d656109` | `c485f75c7514` |
| `tasks/evidence/DEUDA-ABIERTA-CLASIFICACION-20261013/construible/revision-020.json` | 2 | `7b2b6f1b29bb` | `5a965e7f98f1` |
| `tasks/evidence/DEUDA-ABIERTA-CLASIFICACION-20261013/construible/revision-074.json` | 1 | `58c1acbdce3c` | `dd0b3f02a644` |
| `tasks/evidence/DEUDA-ABIERTA-CLASIFICACION-20261013/ola-final-close-checks.tsv` | 2 | `3b0a647ca097` | `5de51e0c6ce8` |
| `tasks/evidence/FEATURE-ARBITRO-MEMORIA-UNIFICADA-POR-PRIORIDAD-01/e2e.txt` | 1 | `66906c52b842` | `dc85f9a3e720` |
| `tasks/evidence/FEATURE-CONTENEDORES-TOPE-PROPIO-Y-RUNTIME-OCI-01/nivel1-y-dorado.txt` | 1 | `cc60bca02516` | `40e947ec5ea1` |
| `tasks/evidence/FEATURE-COSECHA-FORO-ENERGIA-Y-DGXTOP-01/cosecha.txt` | 1 | `2eb2da23db95` | `d13e44f9de3a` |
| `tasks/evidence/FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01/medicion-v3-cargado-20261016.txt` | 1 | `093b8ad8abd1` | `5938118b8fd8` |
| `tasks/evidence/FEATURE-DMEM-PREENROLAMIENTO-LISTA-01/reinicio-afectados.txt` | 4 | `4f473ce812a6` | `f99340189781` |
| `tasks/evidence/FEATURE-INCIDENTE-CAMPOS-NO-COLECTADOS-01.e2e.txt` | 3 | `1f638bf8b2b1` | `fbcc4bb14970` |
| `tasks/evidence/FEATURE-NVIDIA-CONTAINER-RUNTIME-HOOK/fail.txt` | 1 | `43872cd7042a` | `1c4dd7e9f17f` |
| `tasks/evidence/FEATURE-OWNEAR-EN-BB-LO-QUE-ACTUA-SOBRE-LA-MAQUINA-01/inventario.txt` | 10 | `e9293e0afc9b` | `d69cdcbf00da` |
| `tasks/evidence/FEATURE-PORTERO-UNIVERSAL-DE-LA-MAQUINA-01/validaciones.txt` | 1 | `0de67ff5d2e8` | `da746a82fde6` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-h1/all-final.json` | 3 | `2256eaaf30dc` | `575c1831be2d` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-h1/batch_00.json` | 2 | `88ed680662d7` | `237632293307` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-h1/batch_01.json` | 2 | `398246b31dd4` | `adc924f3b1e7` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-h1/final/verdict_00.json` | 3 | `a14a5dcf03ce` | `116e2203d8a7` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-h1/source.json` | 4 | `c71aa54d3cd4` | `82b97827c5d9` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-h1/stale-after-renewals.json` | 4 | `0e78024357b6` | `2e449f99cb89` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-h1/stale.json` | 4 | `0e78024357b6` | `2e449f99cb89` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-h1/verdict_00.json` | 3 | `253762999f12` | `d53d381e9f66` |
| `tasks/evidence/RELEASE-2.1.0/h1-batches/batch_00.json` | 3 | `58faa578c06d` | `1fc60ed4def6` |
| `tasks/evidence/RELEASE-2.1.0/h1-batches/batch_01.json` | 1 | `a893f476d3a1` | `81985826df6b` |
| `tasks/evidence/RELEASE-2.1.0/h1-batches/batch_02.json` | 2 | `254fb65f32b3` | `9ebdf2f7f334` |
| `tasks/evidence/RELEASE-2.1.0/h1-batches/verdict_00.json` | 2 | `63e7ecd4bb4e` | `a23266d00cdf` |
| `tasks/evidence/RELEASE-2.1.0/h1-batches/verdict_01.json` | 3 | `e167111c84f4` | `0f245dd41560` |
| `tasks/evidence/RELEASE-2.1.0/h1-items.json` | 6 | `f83de679f314` | `b7ef96abeda4` |
| `tasks/evidence/RELEASE-2.1.0/h1-results.json` | 5 | `800b698d094b` | `d1bbaa40d863` |
| `tasks/evidence/SWARM-OPEN-2026-10-02/capture-commands.json` | 1 | `809b61232c3a` | `a23bd5b56fac` |
| `tasks/evidence/VENTANA-VLLM-20261015/ventana-20261015T063058.txt` | 1 | `ccb2ac2fa9c5` | `b69f0eb3c1b0` |

## Actualización 2026-11-01 (boleta #26 A): parche redactado y re-sellado

Luis decidió redactar igualmente `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/simplecode-producer-validation/reviewed-producer.redacted.patch` y volver a sellar los archivos que citan su hash. Mismo marcador `[externo]`, misma convención que arriba. Esta sección sustituye lo dicho antes sobre ese archivo: ya no queda sin redactar.

- **Alcance de la redacción.** El parche es del proyecto cuyo nombre lleva su propia ruta, así que sus rutas, importaciones y constantes son la estructura del parche y no se tocan. Se sustituyó sólo el comentario de la línea 263 (3 tokens: 2 de un proyecto privado y 1 del nombre del proyecto del parche, en prosa). Quedan 20 menciones del nombre del propio proyecto en 16 líneas de estructura (cabeceras `diff`, rutas, una importación y una constante), pendientes de decisión de Luis si quiere neutralizarlas también (rompería la aplicabilidad del parche).
- **sha256 del parche.** Antes `f72e4b3faf1d`, después `7307b80d5609` (los 12 primeros hex; el hash completo vive en el repositorio privado).
- **Hash citado por otros archivos.** Los 14 archivos que citaban el hash viejo del parche se re-sellaron sustituyendo SOLO ese valor (278 líneas cambiadas, todas de hash; ninguna otra). Además, uno de ellos (`publication-privacy-current.json`) tiene su propio sha256 citado por otros dos archivos, y al cambiar su contenido cambió el suyo. Cadena completa: parche → 14 archivos → `publication-privacy-current.json` → `publication-privacy-binary-review.json` y `publication-privacy-provenance-followup-current.json` (este último ya estaba entre los 14). Ningún otro archivo cita los hashes de esos dos y la cadena termina ahí.
- Los 15 JSON re-sellados se comprobaron con `python3 -m json.tool`.
- Tras el cambio, el hash viejo del parche no aparece en ningún archivo del repositorio y el nuevo aparece en los 14.

| Archivo re-sellado | sha256 antes | sha256 después |
|---|---|---|
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/simplecode-producer-validation/reviewed-producer.redacted.patch` | `f72e4b3faf1d` | `7307b80d5609` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/publication-producer-redaction-candidate.json` | `e1bf5bc408a5` | `b150a55c556b` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-binary-review.json` | `412db91a5e4c` | `3d863e056116` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-current.json` | `67d330789be4` | `e132362b141d` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-followup-batches/batch_00.json` | `0c96a673fdb8` | `a5e5415672c4` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-followup-batches/batch_01.json` | `45f8ce342670` | `34777829b080` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-followup-batches/batch_02.json` | `0b61d280914e` | `d824e973e2c6` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-followup-batches/batch_03.json` | `7ec25a82a17a` | `ec1b2183805f` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-followup-batches/batch_04.json` | `1c0fd45e09dc` | `88fde58e7cba` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-followup-batches/verdict_00.json` | `f605961f9a04` | `ce2214621c26` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-followup-batches/verdict_01.json` | `6992c97399dd` | `c6483e5137ae` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-followup-batches/verdict_02.json` | `6c9db6e2c5c9` | `aec1e6f89772` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-followup-batches/verdict_03.json` | `c1439401a2b8` | `18c1f64ffd8f` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-followup-batches/verdict_04.json` | `744dd1cef570` | `2aff61c2acef` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-followup-items.json` | `352bba56a368` | `9dd80f0763e6` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-provenance-followup-current.json` | `7ee89c9c7f58` | `1ce0cd63d6a2` |


## Actualización 2026-11-01 (boletas #27 A y #28 B): ids de tickets ajenos, rutas de la base de conocimiento y alias de proyecto

Luis decidió neutralizar en este repositorio los identificadores de tickets del consumidor de conocimiento (`DGX-nnn`), las rutas `knowledge/(references|investigations|identity)/` y el alias de otro proyecto. Mismo marcador `[externo]` y misma convención que arriba: en evidencia no se reescribe prosa, se sustituye el token. Sustitución textual con expresiones regulares (`knowledge/(references|investigations|identity)/` pasa a `[externo]/`; `DGX-[0-9]+` y el alias, a `[externo]`), sin tocar nada más del archivo.

- Archivos de evidencia redactados en esta pasada: 23. Tokens sustituidos: 84 (46 rutas de la base de conocimiento, 38 ids de tickets, 0 alias).
- Los 14 JSON redactados se comprobaron con `python3 -m json.tool` y sin claves duplicadas (antes y después).
- Hash citado por otros archivos: se hizo `grep` del sha256 (completo y de 12 hex, y de cualquier prefijo de 12 o más hex) de cada candidato contra todo el repositorio. Ningún archivo editado tenía su hash citado por otro archivo de procedencia. 10 de los 23 ya figuraban en la tabla de arriba y su hash "después" sólo lo citaba esa tabla: para ellos, "antes" aquí es el "después" de la fila anterior, y esa fila queda superada por ésta.
- **No se editó** `tasks/evidence/ZERO-2026-10-02/prepush-before-final.txt`: su sha256 lo cita `tasks/evidence/RELEASE-SUNSET-2-2-01/source.json`. Sus únicas menciones son el identificador de la ficha `DEBT-DGX-438-SIN-CAUSA-RAIZ` dentro de una salida literal, que de todos modos se conserva (ver abajo).
- **Se conserva a propósito** el número de ticket cuando forma parte del identificador de una ficha de este repositorio (`DEBT-DGX-438-SIN-CAUSA-RAIZ`, `DEBT-VERIFICAR-DGX-30-OOM-LLAMADORES-CONCURRENTES-01`, la forma corta `DEBT-DGX-438` de la ficha) y de sus rutas: son el nombre real de un archivo y de un directorio de evidencia, y aparecen en salidas literales de herramientas (`AVISO <ficha>.md: ...`, el `--help` de `bb`). Renombrar esas dos fichas toca `bin/`, `tools/` y `tests/` y queda como decisión aparte. Tampoco se tocó ningún `close_check`.
- Los `.json` que citan una línea de código (el comentario `-- <id de ticket>  # sunset-reviewed...`) ya no coinciden en ese token con el archivo fuente actual: es la misma limitación de la redacción anterior.

| Archivo | rutas | ids | alias | sha256 antes | sha256 después |
|---|---|---|---|---|---|
| `docs/evidence/INCIDENTES/bb-2026-10-11-54b71618.json` | 23 | 0 | 0 | `d636c6350b71` | `46112c3af7bf` |
| `docs/evidence/INCIDENTES/bb-2026-10-11-54b71618.md` | 23 | 0 | 0 | `30d5c9e5bf67` | `4cd561a8ecf9` |
| `tasks/evidence/CLASIFICACION-FICHAS-APLICABILIDAD-20261013/clasificacion.json` | 0 | 1 | 0 | `801ae0f8b775` | `ed64adeb330e` |
| `tasks/evidence/CLEAN-2026-10-03/renew-source.json` | 0 | 1 | 0 | `276092e2e9d2` | `020d904fd4ed` |
| `tasks/evidence/DEBT-DGX-438-SIN-CAUSA-RAIZ/instrumento-2026-09-27.txt` | 0 | 3 | 0 | `33ee19ec3f49` | `936b90352893` |
| `tasks/evidence/DEBT-DGX-438-SIN-CAUSA-RAIZ/pass.txt` | 0 | 1 | 0 | `bdf9b2625d87` | `5b4f0ca04b60` |
| `tasks/evidence/DEBT-NO-COVER-ATOM-GPU-TELEMETRY-1676/e2e.txt` | 0 | 4 | 0 | `78a3fc7931f1` | `ea50c7cf1fdf` |
| `tasks/evidence/DEBT-NO-COVER-NOMBRA-VICTIMAS-271/e2e.txt` | 0 | 1 | 0 | `96bdeecd3073` | `fa9151a6fd6c` |
| `tasks/evidence/DEBT-REGISTRATION-2026-10-02/manifest.json` | 0 | 1 | 0 | `e16e671bd379` | `a06d371a9b61` |
| `tasks/evidence/DEBT-TRES-CHEQUEOS-POR-IS-ACTIVE/fail.txt` | 0 | 2 | 0 | `29b209b7b33d` | `bc0e37240654` |
| `tasks/evidence/DEBT-VERIFICAR-DGX-30-OOM-LLAMADORES-CONCURRENTES-01/e2e.txt` | 0 | 1 | 0 | `8a0469b0a2f0` | `48d85a09824f` |
| `tasks/evidence/DEBT-VERIFICAR-DGX-30-OOM-LLAMADORES-CONCURRENTES-01/verificacion.txt` | 0 | 8 | 0 | `fb76264c7cad` | `034efa413afc` |
| `tasks/evidence/DEUDA-ABIERTA-CLASIFICACION-20261013/construible.tsv` | 0 | 2 | 0 | `f3368b3c13bc` | `ff1080d2d609` |
| `tasks/evidence/DEUDA-ABIERTA-CLASIFICACION-20261013/construible/revision-020.json` | 0 | 2 | 0 | `5a965e7f98f1` | `b2dd8d8d752e` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-sunset/batch_00.json` | 0 | 1 | 0 | `5bea48bd585f` | `efd74bf70d4a` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-sunset/current-target-2.4.json` | 0 | 2 | 0 | `f0d478e11817` | `3713e81c1d43` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-sunset/renewed-17-root.json` | 0 | 2 | 0 | `6af11cbf0fa5` | `98283e1f236c` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-sunset/source.json` | 0 | 1 | 0 | `9c1b7745dfbf` | `d8cafe821987` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-sunset/target-2.4-final-root.json` | 0 | 1 | 0 | `c1838b46f404` | `9e800b6b3613` |
| `tasks/evidence/RELEASE-2.1.0/h1-batches/verdict_01.json` | 0 | 1 | 0 | `0f245dd41560` | `4f8b16e0ac74` |
| `tasks/evidence/RELEASE-2.1.0/h1-results.json` | 0 | 1 | 0 | `d1bbaa40d863` | `c1901693b7e7` |
| `tasks/evidence/RELEASE-2.1.0/sunset-review.json` | 0 | 1 | 0 | `3f5d145caf55` | `d0bec5fed745` |
| `tasks/evidence/RELEASE-SUNSET-2-2-01/source.json` | 0 | 1 | 0 | `6bdabd9b641a` | `abffdd6198eb` |

## Actualización 2026-11-01 (boleta #27 A): las dos fichas con id ajeno en el nombre, renombradas

Lo que la actualización anterior dejó como «decisión aparte». Las dos fichas se movieron con `git mv` (ficha y directorio de
evidencia), y su `id:` cambió con el nombre:

| Antes | Después |
|---|---|
| `DEBT-DGX-438-SIN-CAUSA-RAIZ` (y la forma corta `DEBT-DGX-438` / `DGX-438`) | `DEBT-SIGTERM-SIN-CAUSA-RAIZ` |
| `DEBT-VERIFICAR-DGX-30-OOM-LLAMADORES-CONCURRENTES-01` | `DEBT-VERIFICAR-REFERENCIA-OOM-LLAMADORES-CONCURRENTES-01` |

- Fuera de `tasks/evidence/` se actualizaron TODAS las referencias: `bin/bb` (comentarios, la cabecera de `bb sigterm` en el
  `--help` y el título de la sección 10 de `bb scan`), `enable-privileged.sh`, `tools/nombra_victimas.py` (incluida su línea
  `SUJETO DE ...`), `tests/test_nombra_victimas.py`, `tests/test_bb_bash.py` y 18 fichas de `tasks/done/`: las dos renombradas,
  13 por el `porque` de su `close_check` (11 dicen «patron DEBT-DGX-438»; una de ellas,
  `FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR`, también por un encabezado) y 3 por su prosa (`DEBT-PSI-UMBRALES-SIN-CALIBRAR`,
  `DEBT-SLUGGISH-SIN-CAUSA-PROBADA`, `FEATURE-ARBITRO-MEMORIA-UNIFICADA-POR-PRIORIDAD-01`).
- `close_check`: en los dos que citaban su propia ruta solo cambió la ruta; ninguna lógica cambió. El marcador
  `dgx30_verificado` de `verificacion.txt` se conserva: es el contenido de la evidencia que el `close_check` busca. Los 18
  `close_check` de las fichas tocadas dan el mismo rc antes y después (17 rc=0; `FEATURE-ARBITRO-MEMORIA-UNIFICADA-POR-PRIORIDAD-01`
  da rc=1 en las dos corridas, porque su test hace `git show` de un commit que no está en este clon).
- En la evidencia, las salidas literales con el nombre viejo (los `AVISO <ficha>.md`, los `.tsv` y `.json` de clasificación, las
  tablas de arriba) **quedan como están**: son registro. A cada `e2e.txt` de las dos fichas se le AÑADIÓ al final una sección
  fechada con el `close_check` corrido con la ruta nueva y su salida (rc=0), para que la evidencia nombre a su ficha por el nombre
  vigente; lo anterior del archivo no cambió. Su sha256 pasa de `6837e6d358fd` a `0134ad80ae61` (`DEBT-SIGTERM-SIN-CAUSA-RAIZ/e2e.txt`) y de
  `48d85a09824f` a `de5ffa5d021e` (`DEBT-VERIFICAR-REFERENCIA-OOM-LLAMADORES-CONCURRENTES-01/e2e.txt`); el único archivo que citaba esos
  hashes es esta misma tabla (fila de arriba), que queda superada por ésta.

## Actualización 2026-11-01 (boleta #35 A): usuario, hostname e IP de la LAN neutralizados en el árbol, y re-sellado en cadena

Luis decidió (boleta #35 A) neutralizar con commits normales todo dato personal que quedaba en el árbol, ANTES de reescribir el historial (#36 B), para que la reescritura purgue también las versiones viejas. Sustitución textual, sin tocar nada más del archivo: `/home/<usuario de la máquina>/` pasa a `/home/<usuario>/`, el usuario suelto (también dentro de `-home-…-projects-…` y `pytest-of-…`) a `<usuario>`, el hostname a `<host>` y las IP de las dos subredes de la LAN de la máquina a `<ip-lan>`. La cuenta pública de GitHub (el usuario seguido de `-maker`) no se toca. Script `redacta.py`, versionado fuera de este repositorio. El hash «antes» es el del commit `fded6f5`; las columnas de sha256 son los 12 primeros hex.

- **Alcance.** 486 archivos editados (tabla de abajo). En texto: 3720 apariciones del usuario, 17 del hostname y 2 de la IP de la LAN, más 13 del usuario cambiadas a mano en comandos ejecutables. En las 5 bases SQLite de cobertura (`*.coverage`), 253 rutas de la tabla `file` reescritas con `UPDATE … replace()` y `VACUUM` (cada ruta aparecía dos veces en bytes, tabla e índice: 506); tras el `VACUUM` ningún byte del archivo conserva el dato, las tablas tienen las mismas filas, `line_bits` es idéntica y `pragma integrity_check` da `ok`.
- **JSON.** Los 111 JSON y JSONL redactados y los 34 re-sellados se comprobaron antes y después con `json.loads` y un detector de claves duplicadas: todos válidos, ninguna clave duplicada.
- **Comandos ejecutables en fichas (`close_check` y la línea que se pega).** La ruta pasa a `$HOME/` en los tres `close_check` que leen un archivo del usuario (`DEBT-ATOM-CRASH-DETECTOR-TIMER-SIN-DESPLEGAR-01`, `FEATURE-MEDIDOR-DE-ENERGIA-EXTERNO-01`, `FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01`). En `DEBT-TEST-PORTERO-DROPIN-REAL-FALLA-EN-EL-PRE-PUSH-01` el comando fija `HOME=$(mktemp -d)` a propósito, así que `$HOME` ya no es el home real: la ruta pasa a `$(getent passwd $(id -un) | cut -d: -f6)/.local`, puesta ANTES de `HOME=…` (el shell expande las asignaciones de izquierda a derecha). En las dos líneas `sudo sh -c '…'` (`DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01`, `FEATURE-RELOJ-CAPTURA-PD-FIRMWARE-Y-TRANSICION-01`) la ruta va dentro de comillas simples y `$HOME` lo expandiría el `sh` de root: pasa a `'"$HOME"'/`, que expande el shell del usuario; con `sudo` sustituido por un `printf`, los argumentos que recibe son byte a byte los de antes. Los cuatro `close_check` dan el mismo rc antes y después en este contenedor (2, 2, 2 y 0; el último porque la prueba se salta sin systemd de usuario), y los tres primeros dan 0 con un HOME temporal que contiene los archivos que piden. Los dos guiones de root guardados como evidencia (`CLOSURE-CONTROLS-2026-10-03/deploy-drift-reviewed.sh`, `VENTANA-VLLM-20261015/ventana.sh`) toman el home de `getent passwd "$SUDO_USER"` en vez del literal; `bash -n` los acepta.
- **Re-sellado en cadena.** Antes de editar se construyó el grafo «archivo → archivos que citan su sha256 completo o un prefijo de 12 o más hex» sobre los 3571 archivos versionados (728 citados, 2350 aristas, sin ciclos). Después se re-selló en orden topológico, el citado antes que quien lo cita y hasta el final de cada cadena, sustituyendo SOLO el valor citado por el prefijo de la misma longitud del hash nuevo: 37 archivos re-sellados, 178 citas. Tras el cambio, `grep -rlF` de cada uno de los 111 hashes viejos re-sellados no encuentra nada en el árbol.
- **Hashes que NO se re-sellaron, y por qué.** (1) Los de `adopted/system-config/etc_default_earlyoom` y `tests/fixtures/etc_default_earlyoom.viejo`: lo que citan `adopted/pendiente-de-despliegue/LEEME.txt`, la ficha `DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01` y las evidencias `DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01/e2e.txt`, `DEBT-EARLYOOM-MATA-AL-MOTOR-VLLM-01/pass.txt` y `DEBT-EARLYOOM-MOTOR-SIGUE-ELEGIBLE-01/e2e.txt` es el sha256 del fichero DESPLEGADO en la máquina y el nombre de su copia en `/var/lib/blackbox/`; re-sellarlo falsearía una medición. El script sellado `adopted/root-scripts/earlyoom-proteger.sh` sí se re-selló (`sha_viejo`, `sha_nuevo` y el heredoc), y el manifiesto `adopted/pendiente-de-despliegue/bb-root-run.manifest.json` lo regeneró su herramienta (`python3 -m tools.bb_root_manifest --propose`). (2) Las filas de las tablas de arriba de este mismo archivo: son registro, y esta tabla las supera.
- **Nombres de archivo.** Ningún archivo versionado lleva el usuario, el hostname ni la IP en su nombre. Los de `ZERO-2026-10-02/receipts-retro/<hex>.txt` son ids de commit (SHA-1), no hashes de archivos editados. El manifiesto de la entrega del 2026-10-12 (`FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01/entrega_…_manifiesto.sha256`) lleva en su nombre el de un proyecto ajeno y no se renombra; `tools/entrega_cosecha_foro.py` escribe desde ahora `entrega_manifiesto.sha256` al lado.
- **Lo que NO se tocó (boleta #32 A).** `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/simplecode-producer-validation/`: 9 archivos con el usuario (6 de texto y 3 bases de cobertura) quedan como están.
- **Archivos adoptados que cambian** (`bb drift` los verá DIVERGE hasta reinstalarlos; los tres cambios son solo de comentario y no piden reiniciar nada): `adopted/system-config/etc_default_earlyoom`, `adopted/system-config/etc_sysctl.d_99-blackbox-panic.conf` y `adopted/systemd-user/atom-gpu-telemetry.service`. El script sellado `earlyoom-proteger.sh` necesita re-aprobar el manifiesto antes de volver a correr.

| Archivo | usuario | host | ip | citas re-selladas | a mano | sha256 antes | sha256 después |
|---|---|---|---|---|---|---|---|
| `DECISIONS.md` | 0 | 0 | 0 | 0 | sí | `b76e334a28f8` | `80243a6f10c9` |
| `adopted/pendiente-de-despliegue/bb-root-run.manifest.json` | 0 | 0 | 0 | 0 | sí | `7511a3580aaf` | `cbcff2e5f81f` |
| `adopted/root-scripts/earlyoom-proteger.sh` | 0 | 0 | 0 | 0 | sí | `d069e765a0e8` | `3fe7c2981459` |
| `adopted/system-config/etc_default_earlyoom` | 0 | 0 | 0 | 0 | sí | `0e8bc5de5b68` | `f15bb4fce9da` |
| `adopted/system-config/etc_sysctl.d_99-blackbox-panic.conf` | 0 | 0 | 0 | 0 | sí | `2cf69bb2044c` | `9590e4684643` |
| `adopted/systemd-user/atom-gpu-telemetry.service` | 0 | 0 | 0 | 0 | sí | `2238af1b0204` | `d05e23d67653` |
| `docs/evidence/BB-INSTRUMENTS-2026-10-03-report.md` | 1 | 0 | 0 | 0 |  | `75638eae6c1a` | `927e60b38b43` |
| `docs/evidence/CLOSURE-CONTROLS-2026-10-03.md` | 1 | 0 | 0 | 0 |  | `222c9a4203ff` | `1ba9d36e698b` |
| `docs/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch-02-controls.md` | 1 | 0 | 0 | 0 |  | `5a6fe598bd7f` | `76ce2a49277b` |
| `docs/evidence/LUNA-FIVES-2026-10-03-report.md` | 3 | 0 | 0 | 0 |  | `34a7a3d5e843` | `7656eda8ef64` |
| `docs/evidence/OPEN-96-CLASSIFICATION-2026-10-04.md` | 96 | 0 | 0 | 0 |  | `a35a8c00a68e` | `5330368b5d3b` |
| `docs/evidence/SIMPLECODE-9.3.1-2026-10-03.md` | 4 | 0 | 0 | 0 |  | `780add60bc52` | `ea5cb6292298` |
| `docs/evidence/SWARM-LUNA-FORUM-2026-10-02/BACKLOG-INDEX.md` | 26 | 0 | 0 | 0 |  | `f36319724cb3` | `6b3f16e5a90f` |
| `docs/evidence/ZERO-RESUME-2026-10-03-report.md` | 1 | 0 | 0 | 0 |  | `921de38a0f1f` | `09ac6106beba` |
| `suspended/MANIFIESTO.md` | 0 | 0 | 0 | 0 | sí | `769c0c3537e9` | `6a897e7c5b13` |
| `tasks/backlog/FEATURE-MEDIDOR-DE-ENERGIA-EXTERNO-01.md` | 0 | 0 | 0 | 0 | sí | `cf936fc36bd5` | `f04be5d1557e` |
| `tasks/backlog/FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01.md` | 0 | 0 | 0 | 0 | sí | `206e1c4be798` | `5e2e9a96a0e6` |
| `tasks/done/DEBT-ATOM-CRASH-DETECTOR-TIMER-SIN-DESPLEGAR-01.md` | 0 | 0 | 0 | 0 | sí | `71783ac6d8e5` | `aa7cad8f721c` |
| `tasks/done/DEBT-CONFIG-ADOPTADA-QUE-NINGUN-SCRIPT-INSTALA.md` | 2 | 0 | 0 | 0 |  | `fc21935e3746` | `6372b9ca7227` |
| `tasks/done/DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01.md` | 1 | 0 | 0 | 0 |  | `f1e0ed05e264` | `b2e016d2c200` |
| `tasks/done/DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01.md` | 0 | 0 | 0 | 0 | sí | `b2f50b1cccaf` | `580865784fb1` |
| `tasks/done/DEBT-EARLYOOM-DESARMADO-POR-EL-AND-DEL-SWAP.md` | 0 | 2 | 0 | 0 |  | `0add50697af7` | `c60b4eba7e54` |
| `tasks/done/DEBT-ESCRITORIO-Y-ARNESES-COMPARTEN-CGROUP.md` | 1 | 0 | 0 | 0 |  | `31a7473100bd` | `6bebd2878563` |
| `tasks/done/DEBT-RESEARCH-COLLECTOR-BB-FORUM-FETCH-01.md` | 1 | 0 | 0 | 0 |  | `8c8e0f6ca799` | `846cb35fa9c9` |
| `tasks/done/DEBT-RESEARCH-COLLECTOR-BB-FORUM-INVENTORY-01.md` | 1 | 0 | 0 | 0 |  | `02158ec1b586` | `33143af5621d` |
| `tasks/done/DEBT-TEST-PORTERO-DROPIN-REAL-FALLA-EN-EL-PRE-PUSH-01.md` | 0 | 0 | 0 | 0 | sí | `38c130c49ce5` | `f06e4beb913a` |
| `tasks/done/DELTA-FORUM-QWEN-LONG-AGENT-STOP-01.md` | 1 | 0 | 0 | 0 |  | `27da7c1f71c3` | `afe3ae7a56b1` |
| `tasks/done/FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01.md` | 1 | 0 | 0 | 0 |  | `e5826985c8cd` | `48fbb8e75a5d` |
| `tasks/done/FEATURE-RELOJ-CAPTURA-PD-FIRMWARE-Y-TRANSICION-01.md` | 0 | 0 | 0 | 0 | sí | `b1ecb6a0bd58` | `896e6b0c6202` |
| `tasks/evidence/BB-INSTRUMENTS-2026-10-03/coverage-final.txt` | 9 | 0 | 0 | 0 |  | `40925aeaa4b8` | `f39dfaa4041f` |
| `tasks/evidence/BB-INSTRUMENTS-2026-10-03/coverage-first.txt` | 9 | 0 | 0 | 0 |  | `96468e3e0828` | `03bf1eb37895` |
| `tasks/evidence/CLASIFICACION-FICHAS-APLICABILIDAD-20261013/PROMPT-clasificador.txt` | 1 | 0 | 0 | 0 |  | `a68e69cbfd35` | `ea6fe44b92b4` |
| `tasks/evidence/CLEAN-2026-10-03/coverage.txt` | 9 | 0 | 0 | 0 |  | `57c98d2f8462` | `7c78a66e0a0c` |
| `tasks/evidence/CLEAN-2026-10-03/forum-retro.txt` | 1 | 0 | 0 | 0 |  | `f1021215e083` | `608e2340abbb` |
| `tasks/evidence/CLEAN-2026-10-03/forum-review.json` | 0 | 0 | 0 | 1 |  | `051c856f020d` | `1070208974b6` |
| `tasks/evidence/CLEAN-2026-10-03/h1-renew-normalized.json` | 1 | 0 | 0 | 0 |  | `ba16f433c118` | `477bf95e67cd` |
| `tasks/evidence/CLEAN-2026-10-03/h1-renew-original.json` | 1 | 0 | 0 | 0 |  | `24c36875dd3a` | `4e4cc0df99cf` |
| `tasks/evidence/CLEAN-2026-10-03/judge-scope-review.json` | 1 | 0 | 0 | 0 |  | `5430d2ff3e77` | `c698662bedd0` |
| `tasks/evidence/CLEAN-2026-10-03/pyright-after.txt` | 2 | 0 | 0 | 0 |  | `ada2d0f02a77` | `8a87ea0fc0ac` |
| `tasks/evidence/CLEAN-2026-10-03/pyright-before.txt` | 5 | 0 | 0 | 0 |  | `dccfaeac6855` | `620853a648c3` |
| `tasks/evidence/CLEAN-2026-10-03/worktree-archives.json` | 54 | 0 | 0 | 0 |  | `96a095529072` | `e59e6fb81c1d` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DEBT-CLOSE-CHECK-VERIFY-GPU-CLOCK-CAP-AB-01-current-selector.log` | 2 | 0 | 0 | 0 |  | `38cb650f2a7a` | `6167b377a91f` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DEBT-CLOSE-CHECK-VERIFY-USB-HID-POSTUPDATE-01-current-selector.log` | 2 | 0 | 0 | 0 |  | `4c5d5bc0a9f4` | `307218d1252b` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DEBT-CLOSE-CHECK-VERIFY-WIFI-ISOLATION-01-current-selector.log` | 2 | 0 | 0 | 0 |  | `6eb6137ea3d6` | `fe9844311bf2` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `c216fd499893` | `683db47a7f29` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `224862c62116` | `93b825e223fd` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `9e3d0a8b9867` | `65685438f4ae` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `e0f9999b9468` | `24943ee2e366` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01-original-selector.log` | 2 | 0 | 0 | 0 |  | `342ea7853580` | `41451273e3f9` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `82d62ddd4179` | `3129df7ab7e3` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01-original-selector.log` | 2 | 0 | 0 | 0 |  | `e42d717ec22a` | `2fc9a3bcfe54` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `d85317d29ace` | `269a2089c1bc` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01-original-selector.log` | 2 | 0 | 0 | 0 |  | `6593d962bf33` | `e45ae8965018` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CX7-POSTHOTPLUG-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `34ed7c7d7287` | `82f738bbd217` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CX7-POSTHOTPLUG-01-original-selector.log` | 2 | 0 | 0 | 0 |  | `cf2a7cec56d1` | `41f3038d55d0` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `cbb23b16898e` | `da15a994bd5c` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01-original-selector.log` | 2 | 0 | 0 | 0 |  | `6fb786d373eb` | `75ca39c3e274` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `6c0699afb260` | `49cc25cd9c01` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `ed112266c69a` | `8ec36853930d` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `f41bc8299637` | `6eb6352fd152` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `f0110bdc07e7` | `cd0510342a1c` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `aafa22a71d39` | `69fdfc356c11` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `3669e5af7c08` | `543f4a605a04` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01-original-selector.log` | 2 | 0 | 0 | 0 |  | `d51e06abd57d` | `0a2dca56c431` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `191949edb8c5` | `b64d7ce4befe` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `a6df06df25df` | `e18ccd49e5cd` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `e74c571d2875` | `48d6c73c7dae` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01-original-selector.log` | 2 | 0 | 0 | 0 |  | `b3f084cfcbd9` | `8b99c4a4fd84` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `8a57b03100f1` | `ba1f6def9196` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `6e7b6ab9ebef` | `7f7ec5fec7bc` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-MEMORY-RECOVERY-SOAK-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `0c3759f7b66b` | `c7a739056f7a` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-MEMORY-RECOVERY-SOAK-01-original-selector.log` | 2 | 0 | 0 | 0 |  | `92bc0692d360` | `03fa8c18bf06` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `a10b7e0e17e8` | `89a353bb294c` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `c689a8997d5f` | `9402d9e357ec` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-MUSE-GLIMMER-DFLASH-MAX-SEQS-GATE-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `f545d49ce7b7` | `805f6f4efe25` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `a4984e072c02` | `5da20fdab758` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-NEMOTRON-SM121-PREBUILT-KERNEL-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `2140a9467b37` | `01c8df4147a6` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `32514dedf65a` | `9aa8dd51bd01` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `4d3e94ad8f2b` | `0dc7a31304ce` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01-original-selector.log` | 2 | 0 | 0 | 0 |  | `6d5acce11242` | `22d76d3da2f5` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `ce6e39e6fc41` | `2a129c891863` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-QWEN-LONG-AGENT-STOP-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `03bb131b3dda` | `535f7e0081ca` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `be2916b786f3` | `85e308dc350a` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `501a72477c33` | `f31fe15606a4` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `6ff69a713b8f` | `7372c87102e6` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `b20274a53cea` | `663e1d2efae2` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-QWEN38-LONG-RUN-JSON-CORRECTNESS-CANARY-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `45567a8181bc` | `f5f8ca316f63` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `8d33efc1b709` | `1baf20a1f864` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-RECOVERY-APT-UPDATE-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `2e38949f930e` | `6efc6d59a4b9` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-RECOVERY-APT-UPDATE-01-original-selector.log` | 2 | 0 | 0 | 0 |  | `cd382d8fa42d` | `ab092bd56632` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-VLLM-GB10-ARCH-AND-BUILD-MATRIX-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `621933706edf` | `215642f43a2e` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `6b03a32233d5` | `6f012bf92b15` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-ROOT-CONTAINER-EFFECTIVE-BUILD-AND-OFFLINE-GATE-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `2c83bd08b7d0` | `c866e239cfef` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-ROOT-DSML-PARSER-RECOVERY-BOUNDARY-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `b9e5ba1ce260` | `1c34dafe79ad` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `634b89fa497d` | `11ab5b503b2e` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-ROOT-MIMO-OVERLAY-AND-PREFILL-FAIRNESS-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `b039c09e4552` | `ccef484a4b2a` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `240964337022` | `59b507d3db9d` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `ceafe05cd1fb` | `63d8ddff7385` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `c57b69e03eb6` | `ed7b46a9de8d` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `16bd61bf1db2` | `20370b495594` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01-original-selector-current.log` | 2 | 0 | 0 | 0 |  | `3db74f13c2e5` | `571747f2b8c3` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/apt-integral-primary-integration.json` | 0 | 0 | 0 | 1 |  | `b2a14ff3c305` | `f4422cb0ef38` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-all-controls-global-20261004-a.coverage` | 57 | 0 | 0 | 0 |  | `62d59856a586` | `193619c41ec9` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-all-controls-global-20261004-a.log` | 181 | 0 | 0 | 0 |  | `d242a1c678c0` | `a10a9ea48a68` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-all-controls-global-20261004-b.coverage` | 57 | 0 | 0 | 0 |  | `cfb6dbd0732c` | `6a24e74ea75e` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-all-controls-global-20261004-b.log` | 181 | 0 | 0 | 0 |  | `f0301cf2014d` | `b3d64724e4c1` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-all-controls-global-20261004-c.coverage` | 57 | 0 | 0 | 0 |  | `938724955d81` | `45701e6e2c21` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-all-controls-global-20261004-c.log` | 193 | 0 | 0 | 0 |  | `a021cbd5764c` | `7a415336fff8` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-apt-integral-pyright-20261004.log` | 69 | 0 | 0 | 0 |  | `efee5275f439` | `acff40c10029` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-deployed-drift-current-20261004.log` | 17 | 0 | 0 | 0 |  | `0415e4191874` | `a0d5103bf919` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-forum-original-selector-20261004.log` | 39 | 0 | 0 | 0 |  | `823ace3873ab` | `53c5457a0e10` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-global-two-regressions-fixed.log` | 1 | 0 | 0 | 0 |  | `68c888b08438` | `ea586065f6d7` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-hardware-command-reader-primary-tests.log` | 2 | 0 | 0 | 0 |  | `730d06797cb9` | `e7a1dac3f165` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-hardware-router-primary-integration.log` | 3 | 0 | 0 | 0 |  | `7e847f2f48e0` | `6cd974192386` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-hardware-router-provider-fixed.log` | 1 | 0 | 0 | 0 |  | `641457865ab0` | `72a52afd29ac` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-registration-assert-helper-regressions.log` | 2 | 0 | 0 | 0 |  | `26c25180a3c4` | `e0ae8868917a` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-smi-original-negative-control.log` | 2 | 0 | 0 | 0 |  | `e2b9603c4373` | `ed3cfbf5ae85` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-tradeoff-original-selector-20261004.log` | 2 | 0 | 0 | 0 |  | `bfd207ec44cd` | `2a0838cec43a` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/bb-zero-debt-after-nvme-real-selector.log` | 1 | 0 | 0 | 0 |  | `4acd112fb4de` | `44d3c6aa2e04` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/deploy-drift-reviewed.sh` | 0 | 0 | 0 | 0 | sí | `e144ad680d55` | `19feac5d8174` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/drm-watchdog-sudo-current-blocker.json` | 1 | 0 | 0 | 0 |  | `cb9b7700a6cf` | `a93ca9937195` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/forum-original-selector-primary-run.json` | 38 | 0 | 0 | 1 |  | `a75fe869b3ab` | `40a74dbe0f5a` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-17-agent-raw-receipt.json` | 1 | 0 | 0 | 0 |  | `a7707ced7fa4` | `1988fc971604` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-apt-signature-dependency-handoff.json` | 1 | 0 | 0 | 0 |  | `4091eaba46e2` | `a00b405801f4` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch02-original-selectors-current.json` | 10 | 0 | 0 | 10 |  | `3bdcd5357ff8` | `f74368271723` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch02-original-selectors-run.json` | 10 | 0 | 0 | 10 |  | `b56048ef1a47` | `e26633c75572` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch03-integration/copy-receipt.json` | 0 | 0 | 0 | 1 |  | `7b1767a51d4a` | `6cee27cf9789` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch03-integration/integration-manifest.json` | 6 | 0 | 0 | 0 |  | `d1f4873f5936` | `1d8393bd68d2` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch03-integration/original-command-wiring-audit.json` | 7 | 0 | 0 | 0 |  | `db7bad431af3` | `ddda1198e0ee` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch03-integration/original-selectors-primary.stdout` | 14 | 0 | 0 | 0 |  | `ecdede3cd892` | `c55c36534e68` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch03/integration-manifest.json` | 6 | 0 | 0 | 0 |  | `d1f4873f5936` | `1d8393bd68d2` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch03/real-evaluation.txt` | 6 | 0 | 0 | 0 |  | `40bd88f63cae` | `8ee57d26aa9e` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch03/verdict.json` | 6 | 0 | 0 | 0 |  | `c4afbb2bc0ef` | `3b563f3d3a23` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-readonly-root-actions/readonly-action-batch.json` | 0 | 0 | 0 | 1 |  | `9b73a6221439` | `5fc098d300cd` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-readonly-root-actions/readonly-action-results.json` | 0 | 0 | 0 | 1 |  | `cdbc82051166` | `d008ae348bf7` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-readonly-root-integrated/batch-01.json` | 26 | 0 | 0 | 11 |  | `6b2709de3b94` | `5d16ada29d03` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-readonly-root-integrated/batch-02.json` | 1 | 0 | 0 | 0 |  | `82387faf997b` | `60506ca77349` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-readonly-root-integrated/batch-03.json` | 1 | 0 | 0 | 0 |  | `a02306f8ccbc` | `ba6bd3d43921` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-readonly-root-integrated/batch-04.json` | 1 | 0 | 0 | 0 |  | `0bdc8f0f2593` | `63db0e816ae8` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-readonly-root-integrated/batch-05.json` | 1 | 0 | 0 | 0 |  | `406c73d32500` | `eae273f44ff7` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-readonly-root-integrated/evidence-reference-root-recheck.json` | 0 | 0 | 0 | 11 |  | `db75291e1ccb` | `96d60c8965bc` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-readonly-root-integrated/hardware-readonly-evidence-map.json` | 1 | 0 | 0 | 12 |  | `96420fde632f` | `b2ea388dfc1f` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-readonly-root-integrated/verdict_01.json` | 0 | 0 | 0 | 11 |  | `8b20f50bf2ff` | `d2e97097bfaf` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/host-native-readonly.json` | 1 | 0 | 1 | 0 |  | `bf677a4434c4` | `31cc073a55e0` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/kernel-integration/integrated-global-native-validation.json` | 14 | 0 | 0 | 0 |  | `e3a30a7102ab` | `ab08e628385c` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/kernel-integration/primary-all-original-commands.json` | 2 | 0 | 0 | 0 |  | `f9ba320898fe` | `f555c2bc28ea` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/kernel-integration/primary-return-audit/merge-result.json` | 1 | 0 | 0 | 0 |  | `9c4c7ff71749` | `3bdfbec0886b` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/kernel-integration/primary-validation.json` | 2 | 0 | 0 | 0 |  | `992ec2b37c96` | `c8faacefe943` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/kernel-readonly-actions/readonly-action-map.json` | 10 | 0 | 0 | 0 |  | `4b40542bf1b0` | `f82f8b45fce0` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/kernel-readonly-actions/verifier-results-primary-20261004.json` | 10 | 0 | 0 | 0 |  | `f3aa16b72c60` | `308b054e3a18` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/kernel-readonly-actions/verifier-results.json` | 18 | 0 | 0 | 0 |  | `451decd6c9ed` | `187f5a2ec4ec` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/kernel-readonly-root-integrated/readonly-action-map.json` | 10 | 0 | 0 | 0 |  | `4b40542bf1b0` | `f82f8b45fce0` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/kernel-readonly-root-integrated/root-import-receipt.json` | 0 | 0 | 0 | 3 |  | `305c254553ec` | `62f0de3c5cd4` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/kernel-readonly-root-integrated/verifier-results-primary-20261004.json` | 10 | 0 | 0 | 0 |  | `f3aa16b72c60` | `308b054e3a18` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/kernel-readonly-root-integrated/verifier-results.json` | 18 | 0 | 0 | 0 |  | `451decd6c9ed` | `187f5a2ec4ec` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/md-migration-integrate-codex-closure.json` | 0 | 0 | 0 | 1 |  | `e604f5ca5024` | `12c0afaece91` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/native-coverage-after-fixture-fix/stderr.txt` | 7 | 0 | 0 | 0 |  | `949903719504` | `3047b3597ddf` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/native-coverage-after-fixture-fix/stdout.txt` | 2 | 0 | 0 | 0 |  | `10ebbfb0ca40` | `22b64e091c89` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/native-coverage-after-nvme/stderr.txt` | 7 | 0 | 0 | 0 |  | `949903719504` | `3047b3597ddf` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/native-coverage-after-nvme/stdout.txt` | 1 | 0 | 0 | 0 |  | `3023158aa070` | `4c057c7a50e3` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/nvme-in-progress-pyright-context-check.json` | 2 | 0 | 0 | 0 |  | `618b6f5c1e6c` | `46f6de80ad7c` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/post-kit-9.3.3-validation/bb-post-kit-9.3.3-pytest.log` | 2 | 0 | 0 | 0 |  | `565ccc691e87` | `3d3792f96f6d` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/post-kit-9.3.3-validation/bb-post-kit-9.3.3.coverage` | 40 | 0 | 0 | 0 |  | `3462aacb40b8` | `db61f5058293` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/post-kit-9.3.3-validation/run.json` | 0 | 0 | 0 | 2 |  | `83dc814d203d` | `7992a8e73d56` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/primary-code-gates-after-hardware-followup.json` | 1 | 0 | 0 | 0 |  | `5a4b416241c6` | `f42581c1fac3` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/primary-shared-reader-full-suite/bb-primary-shared-reader-20261004-pytest.log` | 2 | 0 | 0 | 0 |  | `e5bfa5b031a9` | `f8a4379b7897` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/primary-shared-reader-full-suite/bb-primary-shared-reader-20261004.coverage` | 42 | 0 | 0 | 0 |  | `9d8b936670f2` | `fab442d22b52` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/primary-shared-reader-full-suite/run.json` | 2 | 0 | 0 | 2 |  | `6d9d64d8484a` | `ad7b190329d0` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/provider-reader-primary-integration.json` | 0 | 0 | 0 | 2 |  | `baf19c9befc2` | `4adeb1691b08` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/publication-artifact-pii-after-9.3.4.json` | 0 | 0 | 0 | 20 |  | `8c07f4062ca5` | `a2da675b31ec` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/publication-artifact-pii-followup-current.json` | 0 | 0 | 0 | 1 |  | `958b94934a79` | `c1bfc1230ad9` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/publication-artifact-pii-provenance-review-20261004.json` | 0 | 0 | 0 | 2 |  | `e8a9e6e39a54` | `8bba4efc13a1` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/publication-coverage-sqlite-readonly-review.json` | 0 | 0 | 0 | 4 |  | `9e37c27a9697` | `59036b5fc8f5` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/publication-indeterminate-canonical-source-root-review.json` | 1 | 0 | 0 | 0 |  | `1b4d2cc5d657` | `2f1ca9b8e778` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/registration-collection-current.json` | 1 | 0 | 0 | 0 |  | `0134deae97f7` | `d45e43a6cf11` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/root-native-suite.txt` | 5 | 0 | 0 | 0 |  | `fd71112360d9` | `7c3340ce9a16` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/root-suite.txt` | 12 | 0 | 0 | 0 |  | `b359b8a4af6f` | `110d70f08932` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime-b02-bool-root-recheck.json` | 1 | 0 | 0 | 0 |  | `9bdb3614856f` | `a5e85844090f` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime-b02-root-final-suite.json` | 10 | 0 | 0 | 0 |  | `f03f65ebef4a` | `5c70219408d6` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime-original-selectors-primary-run.json` | 37 | 0 | 0 | 37 |  | `21046a265dd5` | `bfdb867ae90c` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime-primary-exact-once/verdict_batch01.json` | 9 | 0 | 0 | 0 |  | `acbcdf6bc378` | `ace64982129b` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime-primary-exact-once/verdict_batch02.json` | 10 | 0 | 0 | 0 |  | `001940be26a0` | `efc3cb723917` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime-primary-exact-once/verdict_batch03.json` | 10 | 0 | 0 | 0 |  | `ec465a2b8504` | `8a1af75a22d3` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime-primary-exact-once/verdict_batch04.json` | 8 | 0 | 0 | 0 |  | `ca526db847ec` | `dcf140139f76` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime-readonly-all37-review/manifest.json` | 7 | 0 | 0 | 0 |  | `794a46f00462` | `6ef26e548cad` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime-readonly-batch01-context.json` | 2 | 0 | 0 | 0 |  | `d5286d286210` | `3f87abd30527` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime-return-audit/audit.json` | 1 | 0 | 0 | 0 |  | `3b3ed0818ca1` | `dfdf29e7f471` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime-return-audit/current-merge-recheck.json` | 1 | 0 | 0 | 0 |  | `0fb6ebec573c` | `353c54b69fc9` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime37-external-root-integrated/batch02.json` | 1 | 0 | 0 | 0 |  | `7313e4f1a802` | `a4e5015cd146` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime37-external-root-integrated/batch03.json` | 4 | 0 | 0 | 0 |  | `15d2e634aa86` | `c0bd61995a59` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime37-external-root-integrated/batch04.json` | 1 | 0 | 0 | 0 |  | `abc1cf140956` | `7bd44f5f4d19` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime37-external-root-integrated/manifest.json` | 10 | 0 | 0 | 1 |  | `7e967f386b99` | `09b84361168f` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime37-external-root-integrated/verdict_02.json` | 1 | 0 | 0 | 0 |  | `1b9b92dc478e` | `f951dda024e5` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime37-external-root-integrated/verdict_03.json` | 4 | 0 | 0 | 0 |  | `55bfd20b57c2` | `7fce72c4b8f3` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime37-external-root-integrated/verdict_04.json` | 1 | 0 | 0 | 0 |  | `1c14e265466a` | `3a1dfaf3951c` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/scope-repair/backlog-before-record-fix.txt` | 1 | 0 | 0 | 0 |  | `18f084a39e1a` | `a61cf9fbada6` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/scope-repair/native-suite-after.txt` | 5 | 0 | 0 | 0 |  | `5bc71c799ed5` | `e454797feb62` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/simplecode-inner-query-owner-root-recheck.json` | 2 | 0 | 0 | 0 |  | `193ba73dbf14` | `68aa8d5ccebd` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/simplecode-json-row-binding-root-recheck.json` | 1 | 0 | 0 | 0 |  | `c0591d2a1ae0` | `0e58a7f79e95` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/three-hardware-original-selectors-primary-run.json` | 3 | 0 | 0 | 3 |  | `bdfcff89d5c9` | `2ca46c0cd935` |
| `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/tradeoff-original-selector-primary-run.json` | 1 | 0 | 0 | 1 |  | `91e18a24320f` | `3337e0c34ac2` |
| `tasks/evidence/DEBT-APT-ARM64-EVIDENCE-PASS-INALCANZABLE-01/fail.txt` | 1 | 0 | 0 | 0 |  | `fc4c842812aa` | `518a38fbe4ba` |
| `tasks/evidence/DEBT-ATOM-CRASH-DETECTOR-TIMER-SIN-DESPLEGAR-01/e2e.txt` | 2 | 0 | 0 | 0 |  | `5ea7e28f5541` | `9b59bc294b8b` |
| `tasks/evidence/DEBT-ATOM-CRASH-DETECTOR-TIMER-SIN-DESPLEGAR-01/pass.txt` | 2 | 0 | 0 | 0 |  | `ed73b46cdeb8` | `1fb5d20c3eb3` |
| `tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-CGROUP-PLAN-01/pass.txt` | 2 | 0 | 0 | 0 |  | `d6a9a44c42a9` | `ec952395a023` |
| `tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01/pass.txt` | 2 | 0 | 0 | 0 |  | `2d6b5f0254d6` | `d4d089001eb6` |
| `tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-GPU-CLOCK-CAP-AB-01/pass.txt` | 2 | 0 | 0 | 0 |  | `0dbd44359b74` | `465d1b7edd91` |
| `tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-MEMORY-SAVER-01/pass.txt` | 2 | 0 | 0 | 0 |  | `a8abf5035185` | `1d74e863138b` |
| `tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-NETCONSOLE-01/pass.txt` | 2 | 0 | 0 | 0 |  | `8e08219eae3b` | `2254bd6d7fa1` |
| `tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-RCU-PANIC-PSTORE-01/pass.txt` | 2 | 0 | 0 | 0 |  | `43623eb6780a` | `eaab622bdd4e` |
| `tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-USB-HID-POSTUPDATE-01/pass.txt` | 2 | 0 | 0 | 0 |  | `d9ca534350f6` | `8cdfd658be0b` |
| `tasks/evidence/DEBT-CLOSE-CHECK-VERIFY-WIFI-ISOLATION-01/pass.txt` | 2 | 0 | 0 | 0 |  | `4888c341b52d` | `696ddef4cb4b` |
| `tasks/evidence/DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01/audit-2026-10-10.md` | 3 | 1 | 0 | 0 |  | `e5d2b52031ec` | `99a65bacbe90` |
| `tasks/evidence/DEBT-COLAPSO-CONFINADO-A-APP-SLICE-REINICIA-LA-MAQUINA-ENTERA-01/evidencia.txt` | 2 | 0 | 0 | 0 |  | `f7785daa9aad` | `337f71f73807` |
| `tasks/evidence/DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01/calibracion-escalon.txt` | 2 | 0 | 0 | 0 |  | `6e99290097d7` | `adaa3caf5253` |
| `tasks/evidence/DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01/despliegue.txt` | 4 | 0 | 0 | 0 |  | `f1a2244d2b51` | `5b2587c80918` |
| `tasks/evidence/DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01/medicion.txt` | 3 | 0 | 0 | 0 |  | `bcc64082c3ec` | `877282922dea` |
| `tasks/evidence/DEBT-CONFIG-ADOPTADA-QUE-NINGUN-SCRIPT-INSTALA/cierre.txt` | 1 | 0 | 0 | 0 |  | `6fef1080cefb` | `6131c97e28ff` |
| `tasks/evidence/DEBT-CONFIG-ADOPTADA-QUE-NINGUN-SCRIPT-INSTALA/fail.txt` | 3 | 0 | 0 | 0 |  | `866c06cc3fbd` | `fee1cbc72a37` |
| `tasks/evidence/DEBT-CONFIG-ADOPTADA-QUE-NINGUN-SCRIPT-INSTALA/pass.txt` | 1 | 0 | 0 | 0 |  | `41d6193c4806` | `00b14b73b579` |
| `tasks/evidence/DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01/fail.txt` | 1 | 0 | 0 | 0 |  | `f8a79ffcde47` | `fabc7a374854` |
| `tasks/evidence/DEBT-DOCKER-CGROUP-SYSTEMD-RECARGA-QUITA-GPU-01/prueba.txt` | 1 | 0 | 0 | 0 |  | `c65d9a40f753` | `7b9bdabca414` |
| `tasks/evidence/DEBT-GUARDIA-PROCESO-MUERE-EN-SILENCIO-01/pass.txt` | 1 | 0 | 0 | 0 |  | `d28c6984ec29` | `9e05bf198e8a` |
| `tasks/evidence/DEBT-GUARDIA-PROCESO-NO-FRENA-SIN-UID-01.e2e.txt` | 1 | 0 | 0 | 0 |  | `8bbde77b97f8` | `5f14f7b195ec` |
| `tasks/evidence/DEBT-GUARDIA-PROCESO-NO-FRENA-SIN-UID-01.fail.txt` | 6 | 0 | 0 | 0 |  | `28f8a233d191` | `a4a18dbd4607` |
| `tasks/evidence/DEBT-H1-RELEASE-CLAIMS-01/drift-current.txt` | 17 | 0 | 0 | 0 |  | `356dfd3a3f4b` | `f9811212a116` |
| `tasks/evidence/DEBT-H1-RELEASE-CLAIMS-01/final-results.json` | 3 | 0 | 0 | 0 |  | `cd1b14b1c14a` | `0cf5c1147c14` |
| `tasks/evidence/DEBT-H1-RELEASE-CLAIMS-01/host-evidence/drift-current-2026-10-03.txt` | 17 | 0 | 0 | 0 |  | `616381c97a77` | `52031b40e9df` |
| `tasks/evidence/DEBT-H1-RELEASE-CLAIMS-01/host-evidence/linger-and-owned-timers.txt` | 1 | 0 | 0 | 0 |  | `1ccc634b3f1c` | `ca15fcf36592` |
| `tasks/evidence/DEBT-H1-RELEASE-CLAIMS-01/host-evidence/recalculate-boot-pressure-command.txt` | 2 | 0 | 0 | 0 |  | `7906ec3e478b` | `304da03d9dc9` |
| `tasks/evidence/DEBT-H1-RELEASE-CLAIMS-01/host-evidence/snapshot-2026-09-25-050801.txt` | 2 | 0 | 0 | 0 |  | `75fb1b9234e7` | `af58dac7f497` |
| `tasks/evidence/DEBT-HOST-DEPLOYED-DRIFT-01/e2e.txt` | 15 | 0 | 0 | 0 |  | `f58f6a764bb5` | `db12a5770159` |
| `tasks/evidence/DEBT-HOST-DEPLOYED-DRIFT-01/fail.txt` | 17 | 0 | 0 | 0 |  | `0415e4191874` | `a0d5103bf919` |
| `tasks/evidence/DEBT-HOST-DEPLOYED-DRIFT-01/pass.txt` | 15 | 0 | 0 | 0 |  | `f58f6a764bb5` | `db12a5770159` |
| `tasks/evidence/DEBT-KIT-HOOK-POSTCOMMIT-LLAMA-MODULO-AUSENTE-DEL-ZIP-01.e2e.txt` | 2 | 0 | 0 | 0 |  | `a845429df409` | `2e9b33984a1c` |
| `tasks/evidence/DEBT-KIT-HOOK-POSTCOMMIT-LLAMA-MODULO-AUSENTE-DEL-ZIP-01.fail.txt` | 1 | 0 | 0 | 0 |  | `4165cb440cef` | `30e6af7d6c03` |
| `tasks/evidence/DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01/audit-2026-10-10.md` | 0 | 14 | 0 | 0 |  | `3c2b127b6944` | `9c65ab89f038` |
| `tasks/evidence/DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01/control-negativo-no-volcado.txt` | 2 | 0 | 0 | 0 |  | `93d48925824e` | `1fb74e14434b` |
| `tasks/evidence/DEBT-PII-HOST-DIAGNOSTICS-CONTACT-01/pyright.txt` | 15 | 0 | 0 | 0 |  | `191e671fc859` | `0efd02a97fef` |
| `tasks/evidence/DEBT-PORTERO-IGNORA-SU-INTERRUPTOR-01/e2e.txt` | 1 | 0 | 0 | 0 |  | `b4c7222b1b21` | `15cfcb533ce2` |
| `tasks/evidence/DEBT-PORTERO-LOG-SIN-ROTACION-CON-OBSERVAR-DE-LIBREOFFICE-01.fail.txt` | 1 | 0 | 0 | 0 |  | `ea5d7b4707ce` | `1fe973956922` |
| `tasks/evidence/DEBT-PRUEBAS-SIN-FICHA-CRUDA-01.e2e.txt` | 1 | 0 | 0 | 0 |  | `51b040735b3a` | `4fd93b0c8f29` |
| `tasks/evidence/DEBT-PRUEBAS-SIN-FICHA-CRUDA-01.fail.txt` | 3 | 0 | 0 | 0 |  | `803589271e26` | `dea7d4f35370` |
| `tasks/evidence/DEBT-PRUEBAS-SIN-FICHA-CRUDA-01/signature-canary/run.json` | 2 | 0 | 0 | 0 |  | `6aed2cac31ba` | `8e2df21c222a` |
| `tasks/evidence/DEBT-REGISTRATION-2026-10-02/manifest.json` | 21 | 0 | 0 | 0 |  | `a06d371a9b61` | `ebdeda527c90` |
| `tasks/evidence/DEBT-RUFF-TEST-BB-BASH-01/e2e.txt` | 1 | 0 | 0 | 0 |  | `00dbc09a111b` | `6a724f7c34b0` |
| `tasks/evidence/DEBT-SCHEMA-EVIDENCE-INDEX-SCOPE-01/migration.json` | 0 | 0 | 0 | 1 |  | `ea6ddaf80749` | `a42c827e8d32` |
| `tasks/evidence/DEBT-SHELLCHECK-BB-2.fail.txt` | 9 | 0 | 0 | 0 |  | `3b41ca480b08` | `ec92df3c08a7` |
| `tasks/evidence/DEBT-SHELLCHECK-BB-2286.fail.txt` | 1 | 0 | 0 | 0 |  | `e108b6c29393` | `3534691c7478` |
| `tasks/evidence/DEBT-TELEMETRIA-GPU-SIN-COTA-EN-CALIENTE/e2e.txt` | 1 | 0 | 0 | 0 |  | `ad2495fd5407` | `e012674b0b39` |
| `tasks/evidence/DEBT-TELEMETRY-HISTORICAL-UNDISPOSED-20260908-01/recovered-event-metadata.json` | 2 | 0 | 0 | 0 |  | `ef9026fd56e3` | `a19c9b33023e` |
| `tasks/evidence/DEBT-TRES-CHEQUEOS-POR-IS-ACTIVE/e2e.txt` | 5 | 0 | 0 | 0 |  | `a12185b5531c` | `70e697bb5c62` |
| `tasks/evidence/DEBT-VIGILANTE-MOTOR-SIN-PRESUPUESTO-DE-REINICIOS-01/e2e.txt` | 2 | 0 | 0 | 0 |  | `7d35a88d42f9` | `deaba83eae94` |
| `tasks/evidence/DEBT-VIGILANTE-MOTOR-SIN-PRESUPUESTO-DE-REINICIOS-01/fail.txt` | 1 | 0 | 0 | 0 |  | `6116051b590d` | `174c9b894a67` |
| `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/all-cached-release-signatures/embedded-key-recheck.json` | 4 | 0 | 0 | 0 |  | `efee41839fa5` | `a8a24f9dab02` |
| `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/all-cached-release-signatures/run.json` | 900 | 0 | 0 | 0 |  | `085b2944c2ee` | `5a353a36651c` |
| `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/all-cached-release-signatures/source-specific-signatures.json` | 50 | 0 | 0 | 0 |  | `fc9b3ad2ac3e` | `a0ecd5c4b49f` |
| `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/healthy-source-canary/collector-source.txt` | 1 | 0 | 0 | 0 |  | `b56c9d583ca1` | `704989d41306` |
| `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/healthy-source-canary/run.json` | 2 | 0 | 0 | 1 |  | `d0f23da60fc3` | `9b9a9df2b76a` |
| `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/isolated-update-control-replay.json` | 0 | 0 | 0 | 2 |  | `a7cdf53c7f0b` | `03cb577e59f7` |
| `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/native-suite-parser-validation.json` | 9 | 0 | 0 | 0 |  | `eb009a82cdc0` | `e98b9619c858` |
| `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/signed-integrity-canary/collector-source.txt` | 1 | 0 | 0 | 0 |  | `e1a25692f77d` | `d70157aec361` |
| `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/signed-integrity-canary/run.json` | 0 | 0 | 0 | 1 |  | `365131997c0e` | `8943e56d801e` |
| `tasks/evidence/DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01/commands.json` | 22 | 0 | 0 | 0 |  | `a51c6b79cc4d` | `1fd4b896c842` |
| `tasks/evidence/DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01/verifier-after.txt` | 1 | 0 | 0 | 0 |  | `1eac7f4bae0b` | `a2e73e5885ad` |
| `tasks/evidence/DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01/fail.txt` | 2 | 0 | 0 | 0 |  | `8329435593f7` | `b745dfa988de` |
| `tasks/evidence/DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01/pass.txt` | 1 | 0 | 0 | 0 |  | `a3dc2a91f978` | `a0ec8d7244e8` |
| `tasks/evidence/DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01/fail.txt` | 2 | 0 | 0 | 0 |  | `61da3b35ede6` | `dc826048562a` |
| `tasks/evidence/DEUDA-ABIERTA-CLASIFICACION-20261013/bloqueo-por-ficha.tsv` | 1 | 0 | 0 | 0 |  | `bdc4bff114d6` | `541bb0def6b5` |
| `tasks/evidence/DEUDA-ABIERTA-CLASIFICACION-20261013/close_checks.tsv` | 3 | 0 | 0 | 0 |  | `f016928ca07c` | `493478e8a8f7` |
| `tasks/evidence/DEUDA-ABIERTA-CLASIFICACION-20261013/construible.tsv` | 2 | 0 | 0 | 0 |  | `ff1080d2d609` | `015ad4eb6aa3` |
| `tasks/evidence/DEUDA-ABIERTA-CLASIFICACION-20261013/construible/revision-020.json` | 1 | 0 | 0 | 0 |  | `b2dd8d8d752e` | `edf75b5051b3` |
| `tasks/evidence/DEUDA-ABIERTA-CLASIFICACION-20261013/construible/revision-077.json` | 1 | 0 | 0 | 0 |  | `51c09e6fa53a` | `ef9a87201981` |
| `tasks/evidence/DEUDA-ABIERTA-CLASIFICACION-20261013/razones.tsv` | 2 | 0 | 0 | 0 |  | `008041586774` | `cffda4ffebb9` |
| `tasks/evidence/FEATURE-1358-CGROUP-01-REPRO/run-profile-integration.json` | 6 | 0 | 0 | 0 |  | `b394ec76da83` | `7250354911e7` |
| `tasks/evidence/FEATURE-1358-CGROUP-01-REPRO/run.json` | 6 | 0 | 0 | 0 |  | `baec49aa0417` | `15ee82486831` |
| `tasks/evidence/FEATURE-ADMISION-TODO-O-NADA-CON-HOLGURA-REAL-01/mide_admision.py.txt` | 1 | 0 | 0 | 0 |  | `d80b6c0cf241` | `b33f13421aae` |
| `tasks/evidence/FEATURE-ADMISION-TODO-O-NADA-CON-HOLGURA-REAL-01/mide_admisiones_reales.py.txt` | 1 | 0 | 0 | 0 |  | `a930503849c4` | `87d1e0e41b2e` |
| `tasks/evidence/FEATURE-ADOPT-ATOM-SECUNDARIAS-SLICE/fail.txt` | 2 | 0 | 0 | 0 |  | `f21f1770c346` | `085b7d782b6a` |
| `tasks/evidence/FEATURE-CONTENEDORES-TOPE-PROPIO-Y-RUNTIME-OCI-01/nivel1-salida.txt` | 8 | 0 | 0 | 0 |  | `ce3bfb035882` | `343289901c49` |
| `tasks/evidence/FEATURE-COSECHA-DISTROS-ALTERNAS-GB10-01/cosecha.txt` | 1 | 0 | 0 | 0 |  | `af5ac32e2da7` | `f60b578016ba` |
| `tasks/evidence/FEATURE-COSECHA-FORO-CATEGORIAS-722-723-01/e2e.txt` | 1 | 0 | 0 | 0 |  | `23e049c07450` | `b7dd8cce9276` |
| `tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01/raw-control-negativo.json` | 12 | 0 | 0 | 0 |  | `08931de37728` | `83c7c52123b4` |
| `tasks/evidence/FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01/raw.json` | 12 | 0 | 0 | 0 |  | `f4af871112f1` | `7d5dda546962` |
| `tasks/evidence/FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01/compilacion.txt` | 8 | 0 | 0 | 0 |  | `b0947fb4a973` | `9cf665f52fe6` |
| `tasks/evidence/FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01/control-negativo-zerofb.txt` | 10 | 0 | 0 | 0 |  | `d1ba68c7185a` | `c50a287faae9` |
| `tasks/evidence/FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01/firma-dmem.txt` | 2 | 0 | 0 | 0 |  | `4345fb6dfae5` | `cde21a9903ab` |
| `tasks/evidence/FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01/medicion.txt` | 1 | 0 | 0 | 0 |  | `8097702d8636` | `3395511c29cb` |
| `tasks/evidence/FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01/modulo-ko.txt` | 4 | 0 | 0 | 0 |  | `056e64a41419` | `a7547ab45703` |
| `tasks/evidence/FEATURE-FAN-RPM-LEER-ACPI-FAN-DONDE-EXISTA-01/fail.txt` | 1 | 0 | 0 | 0 |  | `19f62f0499d8` | `459d30840802` |
| `tasks/evidence/FEATURE-INCIDENTE-CAMPOS-NO-COLECTADOS-01.e2e.txt` | 3 | 0 | 0 | 0 |  | `fbcc4bb14970` | `71f37f8834b5` |
| `tasks/evidence/FEATURE-MEMORYSAVER-03-INTEGRIDAD/runtime.json` | 1 | 0 | 0 | 0 |  | `316450291565` | `14bea3992eb9` |
| `tasks/evidence/FEATURE-OWNEAR-EN-BB-LO-QUE-ACTUA-SOBRE-LA-MAQUINA-01/inventario.txt` | 30 | 0 | 0 | 0 |  | `d69cdcbf00da` | `fa38d39b9909` |
| `tasks/evidence/FEATURE-VIGILANTE-MEMAVAILABLE-UMA-01/medicion-cruda-2026-10-13.txt` | 13 | 0 | 0 | 0 |  | `cc6232cbdb92` | `199753990e57` |
| `tasks/evidence/FEATURE-VIGILANTE-MEMAVAILABLE-UMA-01/medicion.txt` | 1 | 0 | 0 | 0 |  | `14a536d0e05f` | `3d61f12e8140` |
| `tasks/evidence/FORUM-02-GX10-READ-INTEGRITY/pass.txt` | 1 | 0 | 0 | 0 |  | `3916a5a3230f` | `c55e63777aad` |
| `tasks/evidence/LUNA-98-2026-10-03/after.txt` | 1 | 0 | 0 | 0 |  | `70a8545442d9` | `98987d5cd828` |
| `tasks/evidence/LUNA-98-2026-10-03/before.txt` | 1 | 0 | 0 | 0 |  | `70a8545442d9` | `98987d5cd828` |
| `tasks/evidence/LUNA-98-2026-10-03/cleanup.txt` | 1 | 0 | 0 | 0 |  | `d42f68b44deb` | `241622e163dc` |
| `tasks/evidence/LUNA-98-2026-10-03/coverage-before-doc-fix.txt` | 9 | 0 | 0 | 0 |  | `b1ba9507e81d` | `792552720b23` |
| `tasks/evidence/LUNA-98-2026-10-03/coverage-before-observability-fix.txt` | 9 | 0 | 0 | 0 |  | `21c96973a3a2` | `0a3f826d726b` |
| `tasks/evidence/LUNA-98-2026-10-03/coverage.txt` | 9 | 0 | 0 | 0 |  | `1951c486f565` | `d5be6859b47e` |
| `tasks/evidence/LUNA-98-2026-10-03/h1-first-review.json` | 9 | 0 | 0 | 0 |  | `d5ef8949bef1` | `1ba633f6a8e8` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DEBT-HOST-DEPLOYED-DRIFT-01.txt` | 17 | 0 | 0 | 0 |  | `92ad08a2b75c` | `c0367d7400ef` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01.txt` | 1 | 0 | 0 | 0 |  | `3d8cc2ca85be` | `e5974c0f41f1` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-8NODE-NCCL-INTERFACE-MTU-01.txt` | 1 | 0 | 0 | 0 |  | `c368952152ec` | `09913606c051` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01.txt` | 1 | 0 | 0 | 0 |  | `efe123353e3d` | `3b49e1cb15ed` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01.txt` | 1 | 0 | 0 | 0 |  | `dbf1cb29f191` | `8963ea1c9417` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01.txt` | 1 | 0 | 0 | 0 |  | `f9666ea75e89` | `bb0bbc694f8b` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-CX7-FW-UPDATE-GUARD-01.txt` | 1 | 0 | 0 | 0 |  | `0b1fd6b1e6f5` | `0d599516b0c8` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01.txt` | 1 | 0 | 0 | 0 |  | `e6adba58c1dc` | `2fa9113476c4` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-CX7-POSTHOTPLUG-01.txt` | 1 | 0 | 0 | 0 |  | `8635b797079a` | `f40d7c37e522` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-CX7-RDMA-ASYMMETRY-RETEST-01.txt` | 1 | 0 | 0 | 0 |  | `dbd26e1875a1` | `57da530408b5` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01.txt` | 1 | 0 | 0 | 0 |  | `8fc91adb88a5` | `50278f62a289` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01.txt` | 1 | 0 | 0 | 0 |  | `8902200a66dc` | `1d926b65f5ed` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01.txt` | 1 | 0 | 0 | 0 |  | `f45510ed19b6` | `c15c5e08428a` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01.txt` | 1 | 0 | 0 | 0 |  | `abfdfa471e72` | `6a21f5aa1523` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01.txt` | 1 | 0 | 0 | 0 |  | `2de04b2edec4` | `482af5b7e767` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01.txt` | 1 | 0 | 0 | 0 |  | `806d811b2d20` | `12bab8a774b5` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01.txt` | 1 | 0 | 0 | 0 |  | `48318defe3e6` | `99e651f3a408` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01.txt` | 1 | 0 | 0 | 0 |  | `efe5c16fccba` | `ae8a26e00bf9` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01.txt` | 1 | 0 | 0 | 0 |  | `df7929bb8fc8` | `354af7e9fa85` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-LLAMACPP-RPC-UMA-AND-ORDERLY-TEARDOWN-01.txt` | 1 | 0 | 0 | 0 |  | `0285f32b8c14` | `e043545a3eb7` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01.txt` | 1 | 0 | 0 | 0 |  | `46dabf2e8854` | `8a2cb3203c9b` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-MEMORY-RECOVERY-SOAK-01.txt` | 1 | 0 | 0 | 0 |  | `0438bae648f1` | `4ce303ac38aa` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01.txt` | 1 | 0 | 0 | 0 |  | `020f67cf2fc4` | `5c8c1f7abc7a` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01.txt` | 1 | 0 | 0 | 0 |  | `4063b5c53f43` | `02c4a5ecb25a` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-MUSE-GLIMMER-DFLASH-MAX-SEQS-GATE-01.txt` | 1 | 0 | 0 | 0 |  | `7ed8bc62bd00` | `9f43e460de81` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01.txt` | 1 | 0 | 0 | 0 |  | `4c558b9fedb5` | `16ecc8d87097` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-NEMOTRON-SM121-PREBUILT-KERNEL-01.txt` | 1 | 0 | 0 | 0 |  | `82a4617f36cc` | `c0dff0b3d757` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01.txt` | 1 | 0 | 0 | 0 |  | `02e11e9dd511` | `bc7882a32bb0` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-QWEN-COLD-COMPILE-OOM-01.txt` | 1 | 0 | 0 | 0 |  | `0583592b8c96` | `0948ac9445ce` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-QWEN-LONG-AGENT-STOP-01.txt` | 1 | 0 | 0 | 0 |  | `7a341a666c27` | `b873288eb5f8` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01.txt` | 1 | 0 | 0 | 0 |  | `8010d951a852` | `2d3cfc93eedc` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-QWEN-SERVICE-OOMD-CACHE-FAIL-01.txt` | 1 | 0 | 0 | 0 |  | `a34c147b380f` | `bda8c3d08f49` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-QWEN-TOOLCALL-WEDGE-01.txt` | 1 | 0 | 0 | 0 |  | `af681979a120` | `998ad0557e7a` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01.txt` | 1 | 0 | 0 | 0 |  | `db00ee7a3521` | `0ec3ea067cc6` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-QWEN38-LONG-RUN-JSON-CORRECTNESS-CANARY-01.txt` | 1 | 0 | 0 | 0 |  | `2179748e92a2` | `01c22f0a193c` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01.txt` | 1 | 0 | 0 | 0 |  | `f81a67d2d8a8` | `6e4dfcef1452` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-RECOVERY-APT-UPDATE-01.txt` | 1 | 0 | 0 | 0 |  | `16c723b3c6c0` | `85378391776e` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01.txt` | 1 | 0 | 0 | 0 |  | `a87670ffc83c` | `147151f5cb03` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-USB-RAID-LINK-ADMISSION-01.txt` | 1 | 0 | 0 | 0 |  | `292e78ec9924` | `98ebcf37da59` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-VLLM-GB10-ARCH-AND-BUILD-MATRIX-01.txt` | 1 | 0 | 0 | 0 |  | `83eeb6ab02e6` | `2e6b8c7764d7` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01.txt` | 1 | 0 | 0 | 0 |  | `60dc6a9b29d1` | `be8bd5be9742` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01.txt` | 1 | 0 | 0 | 0 |  | `6f6b89d12a0f` | `0966b8206000` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-ROOT-CONTAINER-EFFECTIVE-BUILD-AND-OFFLINE-GATE-01.txt` | 1 | 0 | 0 | 0 |  | `a40c9668c6ff` | `21eb0475bd20` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01.txt` | 1 | 0 | 0 | 0 |  | `a0ef70dc7c8e` | `4de8a6f649a8` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-ROOT-DSML-PARSER-RECOVERY-BOUNDARY-01.txt` | 1 | 0 | 0 | 0 |  | `651361845b37` | `b782b79b0ecd` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01.txt` | 1 | 0 | 0 | 0 |  | `6314e1245c16` | `07021e13485b` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-ROOT-GX10-SOC-EC-CABLE-RECOVERY-CANDIDATE-01.txt` | 1 | 0 | 0 | 0 |  | `0c5ff4fcc562` | `f88abb37b405` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-ROOT-MIMO-OVERLAY-AND-PREFILL-FAIRNESS-01.txt` | 1 | 0 | 0 | 0 |  | `40576239cb60` | `d7033580b6a7` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01.txt` | 1 | 0 | 0 | 0 |  | `5a08f9084ecb` | `c6d43bd4cd9e` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01.txt` | 1 | 0 | 0 | 0 |  | `ecc264b089d4` | `7c057a4771f3` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-ROOT-SUBAMBIENT-COOLING-AND-UMA-CANARY-01.txt` | 1 | 0 | 0 | 0 |  | `b48ac19f8ff1` | `d9515d5bb2e3` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01.txt` | 1 | 0 | 0 | 0 |  | `b2bb03e26229` | `af314cfd85bb` |
| `tasks/evidence/LUNA-98-2026-10-03/remaining-before/DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01.txt` | 1 | 0 | 0 | 0 |  | `73b423d0f291` | `c9ddf13cc773` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_04.json` | 5 | 0 | 0 | 0 |  | `05739ba24591` | `932540aa016d` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_05.json` | 5 | 0 | 0 | 0 |  | `46884a5e0af4` | `3ba3b7e206ed` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_06.json` | 5 | 0 | 0 | 0 |  | `9474b9203652` | `60722c9dd240` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_07.json` | 5 | 0 | 0 | 0 |  | `bf50aaa51eba` | `5dc65618ee81` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_08.json` | 5 | 0 | 0 | 0 |  | `3737227b476e` | `4c836ad35f0d` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_09.json` | 5 | 0 | 0 | 0 |  | `17f79672650a` | `466c35a41f6e` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_10.json` | 5 | 0 | 0 | 0 |  | `e93a14358b91` | `4edeb4248472` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_11.json` | 5 | 0 | 0 | 0 |  | `6a7f8b9807c3` | `d26ec8b3ff9d` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_12.json` | 5 | 0 | 0 | 0 |  | `0f4d39f02f9d` | `02095c9f4fea` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_13.json` | 5 | 0 | 0 | 0 |  | `cb3a5961b1e2` | `a23391095d36` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_14.json` | 5 | 0 | 0 | 0 |  | `63b289c93c08` | `99d8883794cf` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_15.json` | 5 | 0 | 0 | 0 |  | `fd3124ffdb56` | `b33e8c23f06d` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_16.json` | 5 | 0 | 0 | 0 |  | `367687f394b7` | `ac8ff1230a63` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_17.json` | 5 | 0 | 0 | 0 |  | `d1ba26f51408` | `ac3a33d61b47` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_18.json` | 5 | 0 | 0 | 0 |  | `701fb87bb59f` | `22f7d1b7ca78` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_19.json` | 5 | 0 | 0 | 0 |  | `09671b4d24b9` | `8b96e3396ccd` |
| `tasks/evidence/LUNA-98-2026-10-03/triage/verdict_20.json` | 3 | 0 | 0 | 0 |  | `ab4cf1307101` | `f7f2f234eb9a` |
| `tasks/evidence/LUNA-98-2026-10-03/verdict-20-original.json` | 3 | 0 | 0 | 0 |  | `abc66334ce3d` | `4f5852337608` |
| `tasks/evidence/LUNA-FIVES-2026-10-03/backlog-after.txt` | 1 | 0 | 0 | 0 |  | `907340e74520` | `cbfaa5ff45d4` |
| `tasks/evidence/LUNA-FIVES-2026-10-03/coverage-before-error-controls.txt` | 9 | 0 | 0 | 0 |  | `6b123d469544` | `42842fdcdaca` |
| `tasks/evidence/LUNA-FIVES-2026-10-03/coverage-final.txt` | 9 | 0 | 0 | 0 |  | `59f152af3133` | `dd08b64700c1` |
| `tasks/evidence/LUNA-FIVES-2026-10-03/coverage-incomplete-before-metadata.txt` | 12 | 0 | 0 | 0 |  | `5197871fefdb` | `835a3136761c` |
| `tasks/evidence/LUNA-FIVES-2026-10-03/pyright.txt` | 5 | 0 | 0 | 0 |  | `dccfaeac6855` | `620853a648c3` |
| `tasks/evidence/LUNA-FIVES-2026-10-03/receipt-37ea.txt` | 1 | 0 | 0 | 0 |  | `342f0d154a85` | `79ef4803c482` |
| `tasks/evidence/LUNA-FIVES-2026-10-03/receipt-51.txt` | 1 | 0 | 0 | 0 |  | `3d40a58b9bd0` | `84d8b1cd9334` |
| `tasks/evidence/LUNA-FIVES-2026-10-03/receipt-951.txt` | 1 | 0 | 0 | 0 |  | `c06d5f93b9ff` | `4e839f4e403d` |
| `tasks/evidence/LUNA-FIVES-2026-10-03/receipt-e381.txt` | 1 | 0 | 0 | 0 |  | `e5305e31bb37` | `62ef9b8308ef` |
| `tasks/evidence/LUNA-FIVES-2026-10-03/receipt-e460.txt` | 1 | 0 | 0 | 0 |  | `3fe0d6475e5c` | `1b785515ec81` |
| `tasks/evidence/LUNA-FIVES-2026-10-03/receipt-efa.txt` | 1 | 0 | 0 | 0 |  | `2de4c57dc58e` | `4708e0da06e3` |
| `tasks/evidence/LUNA-FIVES-2026-10-03/scan-after.txt` | 1 | 0 | 0 | 0 |  | `70a8545442d9` | `98987d5cd828` |
| `tasks/evidence/LUNA-FIVES-2026-10-03/scan-before.txt` | 1 | 0 | 0 | 0 |  | `ccad2047873a` | `203daf74266a` |
| `tasks/evidence/LUNA-FIVES-2026-10-03/version-final.txt` | 20 | 0 | 0 | 0 |  | `2bf65e48fc58` | `71dfc3a43e8e` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/bb-open96-publication-coverage-native-20261004.log` | 189 | 0 | 0 | 0 |  | `548f718687d4` | `aba462d480bf` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/merge-terminal.json` | 1 | 0 | 0 | 0 |  | `19bf8bec9f4a` | `6a417afbfe94` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-coverage-native-terminal.json` | 0 | 0 | 0 | 1 |  | `58bde304034c` | `b55d59577187` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-binary-review.json` | 1 | 0 | 0 | 6 |  | `3d863e056116` | `b2ddaaadb29f` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-current.json` | 0 | 0 | 0 | 6 |  | `e132362b141d` | `1879d016ed29` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-privacy-provenance-followup-current.json` | 2 | 0 | 0 | 6 |  | `1ce0cd63d6a2` | `814496e64f08` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-sunset/current-target-2.4.json` | 46 | 0 | 0 | 0 |  | `3713e81c1d43` | `268f34cfe4e9` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-sunset/root-integrity.json` | 1 | 0 | 0 | 0 |  | `8d351c183557` | `5131eafdc1a6` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-sunset/runtime-ignore-root.json` | 1 | 0 | 0 | 0 |  | `3f80860e1973` | `d89f990d87dd` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-sunset/simplecode-ownership-proof.json` | 8 | 0 | 0 | 0 |  | `c0bbb066718b` | `be3e633fc465` |
| `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/publication-sunset/target-2.4-final-root.json` | 23 | 0 | 0 | 0 |  | `9e800b6b3613` | `26128a876995` |
| `tasks/evidence/RELEASE-2.1.0/coverage.txt` | 11 | 0 | 0 | 0 |  | `c6d838d6b65a` | `647058913aa3` |
| `tasks/evidence/RELEASE-2.1.0/h1-agent-limits.txt` | 2 | 0 | 0 | 0 |  | `99891c2da3ed` | `f527886d4901` |
| `tasks/evidence/RELEASE-2.1.0/h1-batches/verdict_01.json` | 2 | 0 | 0 | 0 |  | `4f8b16e0ac74` | `c143be14b51a` |
| `tasks/evidence/RELEASE-2.1.0/h1-batches/verdict_02.json` | 2 | 0 | 0 | 0 |  | `e57402a978e8` | `55056927916f` |
| `tasks/evidence/RELEASE-2.1.0/h1-results.json` | 4 | 0 | 0 | 0 |  | `c1901693b7e7` | `4edc36eb190e` |
| `tasks/evidence/RELEASE-SUNSET-2-2-01/e2e.txt` | 21 | 0 | 0 | 0 |  | `0c61eae5d812` | `dd263bafbc18` |
| `tasks/evidence/RELEASE-SUNSET-2-2-01/fail.txt` | 20 | 0 | 0 | 0 |  | `9bc129628ed2` | `1c3919ad7355` |
| `tasks/evidence/RELEASE-SUNSET-2-2-01/pass.txt` | 21 | 0 | 0 | 0 |  | `aaf9b9fae35d` | `ae8a29db9a4c` |
| `tasks/evidence/RELEASE-SUNSET-2-2-01/source.json` | 0 | 0 | 0 | 1 |  | `abffdd6198eb` | `f57dce4c65d1` |
| `tasks/evidence/SIMPLECODE-9.3.1-2026-10-03/coverage-final.txt` | 9 | 0 | 0 | 0 |  | `c4ee3726bf65` | `c472c757696a` |
| `tasks/evidence/SIMPLECODE-9.3.1-2026-10-03/prepush-initial.txt` | 30 | 0 | 0 | 0 |  | `35c90ed9e4cb` | `8492fe0816d9` |
| `tasks/evidence/SWARM-CGROUP-2026-10-02/triage-negative.txt` | 1 | 0 | 0 | 0 |  | `7d7e24202294` | `ce9150b56b89` |
| `tasks/evidence/SWARM-CGROUP-2026-10-02/triage-pass.txt` | 1 | 0 | 0 | 0 |  | `43207eba37ab` | `00077ad998ba` |
| `tasks/evidence/SWARM-DEV-2026-10-02/triage-checks.json` | 2 | 0 | 0 | 0 |  | `c44345e80c0b` | `03c4234fdf05` |
| `tasks/evidence/SWARM-LUNA-1358-2026-10-02/journal-watchdog.jsonl` | 21 | 0 | 0 | 0 |  | `3690748e9932` | `d77cf1cddf3e` |
| `tasks/evidence/SWARM-LUNA-1358-2026-10-02/verification.txt` | 1 | 0 | 0 | 0 |  | `82b07e3fc0b9` | `1c1b7d205971` |
| `tasks/evidence/SWARM-LUNA-2026-09-29/README.md` | 4 | 0 | 0 | 0 |  | `26d3705cdf24` | `cb5de65b5447` |
| `tasks/evidence/SWARM-LUNA-2026-09-29/baseline-tests.txt` | 4 | 0 | 0 | 0 |  | `939cc5f8374e` | `e1ef79b68478` |
| `tasks/evidence/SWARM-LUNA-2026-09-29/debt-after.txt` | 2 | 0 | 0 | 0 |  | `24cfc6e44014` | `3ccb434555d1` |
| `tasks/evidence/SWARM-LUNA-2026-09-29/debt-before.txt` | 1 | 0 | 0 | 0 |  | `ffb0cc606985` | `11fc39a50aef` |
| `tasks/evidence/SWARM-LUNA-2026-09-29/triage-merge.txt` | 1 | 0 | 0 | 0 |  | `91d266406b3a` | `054fb734c482` |
| `tasks/evidence/SWARM-OPEN-2026-10-02/host-diagnostics.json` | 1 | 0 | 1 | 0 |  | `b1316f24d906` | `d5e0fb84c65f` |
| `tasks/evidence/SWARM-OPEN-2026-10-02/status-host.json` | 1 | 0 | 0 | 0 |  | `162606c2fb49` | `f1b1ce05e8cc` |
| `tasks/evidence/SWARM-OPEN-2026-10-02/triage-negative.txt` | 1 | 0 | 0 | 0 |  | `86be5795df85` | `6b0bd275c563` |
| `tasks/evidence/SWARM-OPEN-2026-10-02/triage-pass.txt` | 1 | 0 | 0 | 0 |  | `6c99b48d39d2` | `ea736237852d` |
| `tasks/evidence/SWARM-TENS-2026-10-03/after.txt` | 1 | 0 | 0 | 0 |  | `70a8545442d9` | `98987d5cd828` |
| `tasks/evidence/SWARM-TENS-2026-10-03/before.txt` | 1 | 0 | 0 | 0 |  | `70a8545442d9` | `98987d5cd828` |
| `tasks/evidence/SWARM-TENS-2026-10-03/coverage-before-extra-controls.txt` | 9 | 0 | 0 | 0 |  | `b1ba97ec3f3a` | `eb213be52233` |
| `tasks/evidence/SWARM-TENS-2026-10-03/coverage-final.txt` | 9 | 0 | 0 | 0 |  | `a1b2466e833b` | `51660691068f` |
| `tasks/evidence/SWARM-TENS-2026-10-03/coverage-first-failure.txt` | 9 | 0 | 0 | 0 |  | `cc84f9e94979` | `3154ef678a81` |
| `tasks/evidence/VENTANA-VLLM-20261015/ventana-20261015T063058.txt` | 1 | 0 | 0 | 0 |  | `b69f0eb3c1b0` | `7a508723841c` |
| `tasks/evidence/VENTANA-VLLM-20261015/ventana.sh` | 0 | 0 | 0 | 0 | sí | `68a33c391450` | `eed209b1d814` |
| `tasks/evidence/ZERO-2026-10-02/after-wave1.txt` | 1 | 0 | 0 | 0 |  | `1e67f629c193` | `4f4a83e9f061` |
| `tasks/evidence/ZERO-2026-10-02/before.txt` | 1 | 0 | 0 | 0 |  | `7f34e832363c` | `59db36ddbbbe` |
| `tasks/evidence/ZERO-2026-10-02/final-debt-scan.txt` | 2 | 0 | 0 | 0 |  | `be5e73eca7ac` | `2ff2d1c07153` |
| `tasks/evidence/ZERO-2026-10-02/final-pyright-before.txt` | 37 | 0 | 0 | 0 |  | `5d1b14bdec8f` | `66fb893d06f3` |
| `tasks/evidence/ZERO-2026-10-02/final-zero-debt.txt` | 2 | 0 | 0 | 0 |  | `5e83f2884260` | `5c7178d9f062` |
| `tasks/evidence/ZERO-2026-10-02/materialize-before.txt` | 1 | 0 | 0 | 0 |  | `534407034996` | `82e77fcfc9eb` |
| `tasks/evidence/ZERO-2026-10-02/prepush-after-final.txt` | 7 | 0 | 0 | 0 |  | `d39ebc633eef` | `eabd2f48b6bc` |
| `tasks/evidence/ZERO-2026-10-02/prepush-before-final.txt` | 41 | 0 | 0 | 1 |  | `26f283f06fd7` | `d573605f9588` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/3db81484e08436a289cbd23ca1a12192ac8b58b0.txt` | 1 | 0 | 0 | 0 |  | `bc0931be867a` | `256dc91c905e` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/50a174b937fe0ab64c267788cf3996b65aabb8f9.txt` | 1 | 0 | 0 | 0 |  | `c3f15d662617` | `4b4ce6cced66` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/550f78bb180ac055c3db643177bc12cded8d6072.txt` | 1 | 0 | 0 | 0 |  | `b8809de24b62` | `f612042d5d4e` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/5e6eb0cad0abd20cd5704cdd9077d3a096e33b03.txt` | 1 | 0 | 0 | 0 |  | `6de4f158342d` | `da7d2f7bed0c` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/725285a7efd1a985012e4fb95fb3601502918b7c.txt` | 1 | 0 | 0 | 0 |  | `e9e50a97892e` | `20422080e3f0` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/7ae22716eeb5476bc0772150cfec952feea024cd.txt` | 1 | 0 | 0 | 0 |  | `a7af948931a3` | `eb495a6636a9` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/84f76d3b887ac21c7cc3bc39ecddc475b4446409.txt` | 1 | 0 | 0 | 0 |  | `48bfa0b7123e` | `402ea281b186` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/9aa3310dc6eae5b8b5130cc8b57dc3ceee8217be.txt` | 1 | 0 | 0 | 0 |  | `56a54c136629` | `5cbcfdefdbe5` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/a456d8e85b55dc91e819d07b64973f4e0ed2246d.txt` | 1 | 0 | 0 | 0 |  | `5b9f216b9a99` | `e2b9864a1632` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/a456d8e8f9f279e31a2e46ca05172082.txt` | 1 | 0 | 0 | 0 |  | `5591673c49a3` | `709b330a8b87` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/a852ff2f24fe8ddbf7e1ec0cbdbf1376b7966eb9.txt` | 1 | 0 | 0 | 0 |  | `3b129e57dad5` | `64bfd8e7f31c` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/backlog-verifier-after-admin-fiches.txt` | 6 | 0 | 0 | 0 |  | `fe68e86d6cac` | `6fa2b4e3bb8a` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/continuation-053-six-history/053cfd0181ddc6607b4c34c9c2760d4f1bcd4887.txt` | 1 | 0 | 0 | 0 |  | `217a30117b30` | `08484cba3c3c` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/continuation-053-six-history/77840c738d30b98e2f21b033e03aff8e119e0df0.txt` | 1 | 0 | 0 | 0 |  | `ca530b61fffc` | `2dbbdd1562e2` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/continuation-053-six-history/7be0ed939a73ccbfe46f99c81b1c5281facb3f08.txt` | 1 | 0 | 0 | 0 |  | `d7f778675f7f` | `2061393791f0` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/continuation-053-six-history/89b0905706ddc7fc0726d103c60cc4c83c857e1c.txt` | 1 | 0 | 0 | 0 |  | `66acdf3bec0a` | `afc328077e0c` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/continuation-053-six-history/b75cef580612a7be6b2f9f688768e29831e9e98e.txt` | 1 | 0 | 0 | 0 |  | `505a4b9837fd` | `391f019227de` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/continuation-053-six-history/dabbde50a71dc783e39a9abadcdd817559b61487.txt` | 1 | 0 | 0 | 0 |  | `498daa4bf371` | `ee05f23f1bb1` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/continuation-053-six-history/edcb39a688616c0ad4743c93743c4410bf133f40.txt` | 1 | 0 | 0 | 0 |  | `fc0a500bb597` | `6a7818cc5c33` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/continuation-053-six-history/summary.txt` | 7 | 0 | 0 | 0 |  | `929df9319227` | `557012d0c450` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/e24586b72af332eaed463585a088fea065ab6344.txt` | 1 | 0 | 0 | 0 |  | `48999123cc44` | `49e59e99214c` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/f6b1f447e6cf6738a6ee91d32077da77aa1fdfca.txt` | 1 | 0 | 0 | 0 |  | `5148f2cf13a3` | `8ed53a7f0f99` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/f7ee5eb122ab37e718b349bac1a7196e0086e71c.txt` | 1 | 0 | 0 | 0 |  | `db290fc166b0` | `cbdfc5e79d83` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/telemetry-29ac-rawcollector.txt` | 0 | 0 | 0 | 1 |  | `d4fadde7a01f` | `d5b2b038238c` |
| `tasks/evidence/ZERO-2026-10-02/receipts-retro/verify-summary.txt` | 12 | 0 | 0 | 0 |  | `d4d7623fe786` | `db6ca03233fe` |
| `tasks/evidence/ZERO-2026-10-02/research-collectors-before.txt` | 2 | 0 | 0 | 0 |  | `ce6a62d0b222` | `255d60168d5c` |
| `tasks/evidence/ZERO-2026-10-02/research-collectors-source.json` | 2 | 0 | 0 | 0 |  | `501a69c60f09` | `834ceb42c9cb` |
| `tasks/evidence/ZERO-2026-10-02/telemetry-29ac-rawcollector.txt` | 0 | 0 | 0 | 1 |  | `d4fadde7a01f` | `d5b2b038238c` |
| `tasks/evidence/ZERO-2026-10-02/telemetry-final-b6ca/prepush-output.txt` | 7 | 0 | 0 | 0 |  | `d39ebc633eef` | `eabd2f48b6bc` |
| `tasks/evidence/ZERO-2026-10-02/workload-final-source.json` | 2 | 0 | 0 | 0 |  | `541e9bb2d6bb` | `5899d84fcb6f` |
| `tasks/evidence/ZERO-RESUME-2026-10-03/backlog-before-contract-fix.txt` | 1 | 0 | 0 | 0 |  | `51097fe70ad4` | `459b73499094` |
| `tasks/evidence/ZERO-RESUME-2026-10-03/coverage-after.txt` | 9 | 0 | 0 | 0 |  | `1bad29367155` | `ae7112ac5200` |
| `tasks/evidence/ZERO-RESUME-2026-10-03/coverage-before-contract-fix.txt` | 9 | 0 | 0 | 0 |  | `522118d6f0f6` | `6f7cc097d9cf` |
| `tasks/evidence/ZERO-RESUME-2026-10-03/pyright-after.txt` | 5 | 0 | 0 | 0 |  | `dccfaeac6855` | `620853a648c3` |
| `tasks/evidence/ZERO-RESUME-2026-10-03/scan-after.txt` | 1 | 0 | 0 | 0 |  | `ccad2047873a` | `203daf74266a` |
| `tasks/evidence/ZERO-RESUME-2026-10-03/scan-before.txt` | 1 | 0 | 0 | 0 |  | `420fd344f3b9` | `009c65d8b4a6` |
| `tasks/evidence/ZERO-RESUME-2026-10-03/scanner-path-resolution.txt` | 2 | 0 | 0 | 0 |  | `4b0d286f9139` | `791dfe5a5c5e` |
| `tasks/evidence/ZERO-RESUME-2026-10-03/version-after.txt` | 20 | 0 | 0 | 0 |  | `30803c573fca` | `19b9aac768b5` |
| `tests/fixtures/datos_privados_baseline.json` | 0 | 0 | 0 | 0 | sí | `1866ecf9636c` | `b24f43f5453b` |
| `tests/fixtures/etc_default_earlyoom.viejo` | 0 | 0 | 0 | 0 | sí | `89fe78dade9a` | `b4fb4f09ab4e` |
| `tests/test_bb_root_manifest.py` | 0 | 0 | 0 | 0 | sí | `a46e2187fc4a` | `6c0760e7c751` |
| `tests/test_cobertura_g3_bordes.py` | 0 | 0 | 0 | 0 | sí | `1b2a4ec0c386` | `71a02cb369a4` |
| `tests/test_entrega_cosecha_foro.py` | 0 | 0 | 0 | 0 | sí | `89a04120e218` | `f2e03a13bfe1` |
| `tests/test_procesos_protegidos.py` | 0 | 0 | 0 | 0 | sí | `820c400c1473` | `f238035869cf` |
| `tests/test_sin_datos_privados.py` | 0 | 0 | 0 | 0 | sí | `c0f3fb1d7137` | `5bbadda3d609` |
| `tools/entrega_cosecha_foro.py` | 0 | 0 | 0 | 0 | sí | `838531459609` | `45a3d2d1ac57` |
| `tools/verifica_cosecha_foro.py` | 0 | 0 | 0 | 0 | sí | `96634696594f` | `2cf5c5e0acee` |
