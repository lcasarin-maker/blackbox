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
