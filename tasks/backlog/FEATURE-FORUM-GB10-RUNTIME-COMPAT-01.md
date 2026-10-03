---
id: FEATURE-FORUM-GB10-RUNTIME-COMPAT-01
kind: task
domain: RUNTIME
title: "Verificar compatibilidad GB10 de imagen, toolchain y backend antes de admitir cargas"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FEATURE-FORUM-GB10-RUNTIME-COMPAT-01 --evidence tasks/evidence/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01", "expect": "exit_zero", "porque": "Verificador pendiente: demostrar preflight mínimo con imágenes soportadas, arquitectura/cubin y controles negativos; ninguna recomendación de backend sin validar salida/estabilidad y rollback."}
---

## Fuentes y límites

[353639](https://forums.developer.nvidia.com/t/353639) reporta host inaccesible con TRT-LLM1.2rc4/NVFP4; un responder atribuye cubins SM100 frente a GB10 SM121 y propone Triton para otro camino vLLM. La transferencia de ese fix al comando original sigue pendiente. [348537](https://forums.developer.nvidia.com/t/348537) muestra ptxas CUDA12.8 sin sm_121a y progreso tras Toolkit13.0.2/Torch2.9/Triton3.5, con otro crash de veinte minutos sin explicar. [349199](https://forums.developer.nvidia.com/t/349199) identifica Pinecone sin soporte ARM en un playbook y restart loop por exec format error; separar incompatibilidad de OOM. [379168](https://forums.developer.nvidia.com/t/379168) expone imagen CUDA13.2/vLLM26.04 frente a driver580 y requisitos >=595.58; un bypass de NVIDIA_REQUIRE carece de validación como solución soportada.

## Prevención y fix propuesto

Reutilizar metadatos de imagen, manifiesto OCI/ARM64, CUDA/PTXAS, GPU real y arquitecturas del backend; documentar una matriz OEM/OS/driver/contenedor soportada y un smoke test antes de cargar modelos. Probar la imagen oficial compatible primero; construir un verificador propio exige demostrar un hueco. Si existe fallback Triton soportado, comparar estabilidad y exactitud antes de recomendarlo. Conectar admisión y restart containment, separando error del proceso de freeze del host.

## Riesgos, validación y cierre

Imagen ARM64 correcta/amd64 incompatible, CPU-only wheel, cubin equivocado, hash inválido, imagen CUDA que exige driver diferente y stack sano. Preservar hash/versions/outputs y control de host/SSH durante reproducción. No saltar checksums ni requisitos CUDA; no instalar toolkit global o driver fuera de soporte como receta general. Cada cambio de backend necesita controles de resultados, medición local de rendimiento, soak predeclarado y retorno a imagen anterior. El verificador propuesto todavía debe implementarse y los logs adjuntos siguen pendientes; registrar compatibilidad desconocida como could_not_run.

## Casos de validación adicionales leídos por coordinador

[375361](https://forums.developer.nvidia.com/t/375361) reporta MiniMax-M3 TP4: wheelCUDA13.2 incompatible y rebuild13.0, NCCL2.28.9 wedgeRay/2.30.4 y util.85OOM/.80estable. Repos/patches externos pendientes de audit; validar versión concreta y carga real, sin transformar .80 en presupuesto universal. [351413](https://forums.developer.nvidia.com/t/351413) reporta headRay en interfaz10Gb frente workerCX7 y recuperación al fijar node-ip-address: comprobar topología y nodo efectivo antes de admitir workload multinodo. [356417](https://forums.developer.nvidia.com/t/356417) aporta NVIDIAimageTorch25.11 y torchaudio sin dependencias para preservar build optimizada, como receta específica pendiente de validación en workload objetivo.

[358610](https://forums.developer.nvidia.com/t/358610) reports a TRT-LLM Qwen 235B autoload/autotuning hang. NVIDIA says an updated playbook image fixes the issue, but the reply gives no exact image tag and the author does not confirm a retest. Capture the precise image digest, model, autotuning stage and supported stack; do not infer a prior `librdmacm` warning caused the hang or claim the patch fixed the reporter’s machine until a tagged image passes a repeatable load test.

[363514](https://forums.developer.nvidia.com/t/native-sm121-fp8-kernels-any-progress/363514) reports vLLM 0.17.1 on GB10 SM12.1 returning silent all-NaN logits through FP8 FlashInfer/CUTLASS paths that accepted the device in `is_supported()`. A user-proposed fallback worked at lower throughput. A later community patch changes an SM120-only guard to the SM120-family guard and reports 10 minutes/32 concurrent requests without errors; source patch is external and not independently audited. This is a correctness failure, not merely performance. Gate exact vLLM/image digest and kernel backend with finite-logit/output checks plus a longer soak before enabling FP8/NVFP4 paths.

[378529](https://forums.developer.nvidia.com/t/repeated-xid-31-mmu-faults-during-amp-enabled-yolov8s-training-on-dgx-spark-gb10/378529) reports repeated Xid 31 during AMP YOLOv8s on DGX OS 7.5, kernel 6.17.0-1026, host 580.159.03 and NGC PyTorch 26.06/user driver 610.43.02. NVIDIA reproduced on PyTorch 26.06, not 26.05, then stated PyTorch 26.08 should fix it. Preserve that exact image release as a compatibility candidate, require the same AMP workload/negative FP16 and Xid checks, and avoid claiming the reporter verified the fix: the thread has no post-release retest.

[361848](https://forums.developer.nvidia.com/t/trouble-to-find-cuda-at-dgx/) shows normal host `nvidia-smi`/CUDA 13.0 yet Python wheel install errors for vLLM/framework platform detection; a response says standard pip wheels were unavailable for that Spark CUDA build and recommends a GB10-targeted image. Do not install a CPU wheel over the optimized NVIDIA stack. [357745](https://forums.developer.nvidia.com/t/incompatibility-of-torchaudio-in-ngc-pytorch-container-25-12-on-dgx-spark-blackwell-gb10/) separately reports PyTorch 25.12 ARM64 container has no matching torchaudio wheel; PyPI’s CPU wheel would replace the NVIDIA build, and source build failed on header mismatch. An alternate community image was suggested, not verified by the original author. Add exact package/image/architecture checks and a clean-environment smoke test before changing a production container; preserve the known-good image digest for rollback.

[370805](https://forums.developer.nvidia.com/t/help-finding-issue-in-eugr-spark-vllm-docker-vs-vllm-vllm-openai-gemma4-cu130-running-gemma-4-26b-a4b-it/370805) reports one-owner reliability divergence for `google/gemma-4-26B-A4B-it`: `eugr/spark-vllm-docker` begins timeout/FastAPI-hang loops after 1–2 hours, while `vllm/vllm-openai:gemma4-cu130` reportedly runs days to weeks. The post gives start commands but no logs, image digests, host telemetry or final diagnosis. Use this as an exact-image/model soak candidate: compare request latency, health of generation, process/cgroup state and host/SSH across repeated long runs before selecting a backend. Do not conclude community or NVIDIA images are generally less reliable from this single unverified report.

## Índice de propuestas registradas del swarm NVIDIA categoría 721

- **`BB-GLM47-NCCL-GDR-UMA-HARDLOCK`** — An owner reports two-node GLM-4.7 355B NVFP4 load hard-locks UMA without NCCL_NET_GDR_LEVEL=0; launch also needed --no-ray and a community KV scale loader arity patch. Fuente: [375690](1).
- **`BB-FLASHINFER-COLD-PREFILL-MBARRIER-HANG`** — A 4-node GB10/sm_121 GLM-5.2 TP4 report attributes repeated host-wide hard wedges under cold prefill to a block spinning in FlashInfer sparse_mla_sm120 mbarrier TRYWAIT; owner reports 8/8 at >=60K cold prefill and zero during… Fuente: [377334](1).
- **`BB-MULTINODE-NCCL-TRANSPORT-PREFLIGHT`** — Two-Spark NCCL test setup has SSH working but Open MPI TCP connection to the peer on port 1024 fails EAGAIN. `ibdev2netdev` shows multiple ROCE interfaces DOWN and one UP; `mpirun hostname` reaches both nodes but `all_gather_perf` does… Fuente: [353010](https://forums.developer.nvidia.com/t/353010/1).
- **`BB-LONGCONTEXT-STRUCTURED-OUTPUT-INTEGRITY`** — An owner reports GLM-4.7-Flash structured output/tool-call corruption after growing context (~17K) on GB10, while claiming the same configuration works on RTX PRO 6000. Driver 580 update reportedly reduced but did not eliminate it. The… Fuente: [359518](https://forums.developer.nvidia.com/t/359518/1).
- **`BB-CLUSTER-MANAGEMENT-ROUTE-SEPARATION`** — Following the Connect Two Sparks netplan step, a user reports NVIDIA Sync over Wi-Fi failed despite wireless/internet remaining up. The author traced reply routing to CX7 IPs placed in the same subnet as Wi-Fi; moving fabric addresses… Fuente: [353527](https://forums.developer.nvidia.com/t/353527/1).
- **`BB-MULTIMODAL-CONCURRENCY-OUTPUT-INTEGRITY`** — A user reports a Qwen3.8 Flash Next community recipe gave 5–10 second first-token latency with an image and then produced “dangerous garbage” in a simple Hi/thank-you conversation, with unrequested command execution text and Japanese… Fuente: [384789](https://forums.developer.nvidia.com/t/384789/10).
- **`BB-MOE-PRUNING-AS-OOM-CONTROL-RISK`** — A community vLLM fork proposes live profiling/masking of MoE experts to free model memory; the author says the monitor initially fails with CUDA graphs, requires eager-mode profiling and reports that 90% masking leaves the model unable… Fuente: [364098](https://forums.developer.nvidia.com/t/364098/1).
- **`BB-LMCACHE-DSA-RESTORE-TP-CONTROLS`** — On reported GLM-5.2 dual-group DSA workload (4×GB10 TP4, vLLM 0.23.1rc1.dev197, LMCache HEAD d1b6371/0.5.0, 3GB L1 + RESP L2), a 32K-token restore requests 125 L1 blocks while the cache is warm. Allocation reportedly fails without… Fuente: [375308](https://forums.developer.nvidia.com/t/375308/5).
- **`BB-QWEN-CODER-AUTOROUND-PATCH-APPLICABILITY`** — For vLLM 0.17.0 and Intel/Qwen3-Coder-Next-int4-AutoRound, a user applied a Qwen3-Coder-Next patch whose hunks no longer matched source and then observed repeated `!` output without a compatible mod. The maintainer said AutoRound needs… Fuente: [363129](https://forums.developer.nvidia.com/t/slow-performance-for-redhatai-qwen3-coder-next-nvfp4/363129/6).
- **`BB-SGLANG-DASH2-ABORT-LOWTOKEN-CLUSTER-RECOVERY`** — A user reports a specific four-node Qwen3.8/SGLang DFlash2 stack where max_tokens<=8 wedges the scheduler and the timeout SIGQUIT handler kills all ranks; client abort mid-stream can also crash the server. A custom patch clamps short… Fuente: [382754](https://forums.developer.nvidia.com/t/382754/1).
- **`BB-VLLM-SM121-CUBIN-JIT-HANG-AND-WEIGHTLOADER-GATE`** — A FE owner on kernel 6.17.0-102/driver 580.159.03 reports vLLM startup hanging after backend selection across three image lineages, no port/health bind, GPU utilization 0%, process sleeping with retained GPU memory and no I/O. The owner… Fuente: [373274](https://forums.developer.nvidia.com/t/373274/1).
- **`BB-GEMMA4-TF5-BUILD-PATCH-DRIFT-GATE`** — Gemma4 vLLM community TF5 rebuild on one reported commit imported `vllm._C` with an undefined PyTorch/CUDA symbol. A forced vLLM rebuild restored the command, but the configured PR #38909 Gemma tool-parser mod then failed to apply and… Fuente: [365513](https://forums.developer.nvidia.com/t/365513/4).
- **`BB-VLLM-FASTAPI-DEPENDENCY-HEALTH-GATE`** — After rebuilding community vLLM containers after a host Dashboard update, `/v1/models` returned HTTP500 because a newly resolved FastAPI version (0.137) exposed `_IncludedRouter` without `.path` to prometheus-fastapi-instrumentator. An… Fuente: [373314](https://forums.developer.nvidia.com/t/373314/1).
- **`BB-HF-MODEL-CACHE-INTEGRITY-CANARY`** — A user initially saw HTTP400 during reasoning output on a vLLM model request, suspected image/parser, then inspected the local Hugging Face checkpoint and found corruption; re-downloading a pinned revision reportedly fixed model… Fuente: [358421](https://forums.developer.nvidia.com/t/358421/1).
- **`BB-MTP-SPECULATIVE-DECODE-CORRECTNESS-GATE`** — A headline custom CUTLASS performance claim was later retracted by author; separate direct benchmark reports MTP2 succeeds initially but fails on third pass, while MTP0 runs stable on exact stack. The author later describes changed… Fuente: [363493](https://forums.developer.nvidia.com/t/363493/1).
- **`BB-TENSORRT-EAGLE3-SEMANTIC-OUTPUT-CANARY`** — With TensorRT-LLM 1.2.0rc1 on a GB10, a GPT-OSS-120B + Eagle3 request returned HTTP 200 while Harmony parsing reported Unexpected EOS and raw output ended in `!!!`. The body therefore did not prove useful model output. Later posts… Fuente: [354783](https://forums.developer.nvidia.com/t/cant-inference-gpt-oss-120b-eagle3-on-gb10/354783/1).
- **`BB-TRTLLM-EAGLE3-DRAFT-WEIGHT-STARTUP-GATE`** — On GB10 SM120, TensorRT-LLM 1.2.0rc8 with GPT-OSS-120B + Eagle3 fails server startup. Although the title cites TRTLLMGenFusedMoE SM120 unsupported, the full log shows CutlassFusedMoE selected and draft-model QKV weight loading asserts… Fuente: [357849](https://forums.developer.nvidia.com/t/bug-tensorrt-llm-1-2-0rc8-trtllmgenfusedmoe-does-not-support-sm120-error-on-dgx-spark-with-gpt-oss-120b-eagle3/357849/1).
- **`BB-SGLANG-MULTINODE-CUDAGRAPH-REGRESSION-GATE`** — A two-Spark GPT-OSS-120B SGLang discussion reports `CUDART error: invalid resource handle` with CUDA graphs in a distributed configuration; the owner says the Spark container was created before upstream PR #12724, manually applied its… Fuente: [353338](https://forums.developer.nvidia.com/t/setting-up-vllm-sglang-or-tensorrt-on-two-dgx-sparks/353338/6).
- **`BB-PYTORCH-DEPENDENCY-MUTATION-CUDA-GATE`** — In a DGX-hosted quantization pipeline for TensorRT Edge-LLM, `pip install .` replaced preinstalled torch `2.10.0a0+b4e4ee81d3.nv25.12` with upstream `torch 2.10.0`; subsequent load failed `Torch not compiled with CUDA enabled`, then… Fuente: [368290](https://forums.developer.nvidia.com/t/tensorrt-edge-llm/368290/1).
- **`BB-NVFP4-SM121-SEMANTIC-ACCEPTANCE`** — A 2xSpark vLLM/Ray NVFP4 experiment reports Triton ptxas 12.8 rejects sm_121a and vLLM0.12 CUTLASS fails for sm120; a community container and eager mode runs GLM-4.6 but owner reports slower generation and limited KV headroom. Another… Fuente: [353723](https://forums.developer.nvidia.com/t/help-running-nvfp4-model-on-2x-dgx-spark-with-vllm-ray-multi-node/353723/1).
- **`BB-VLLM-DRIVER-MEMORY-ADMISSION-SEPARATION`** — A vLLM 25.12.post1 Qwen3-Next FP8 startup reports CUDA OOM with 550.64MiB free and 462MiB requested, on a 119.64GiB GPU with model length16,384, max sequences16, utilization.85 and fp8 KV. The same thread reports the image requires… Fuente: [357820](https://forums.developer.nvidia.com/t/dgx-spark-qwen3-next-80b-proven-performance-but-missing-clear-path-to-nim-tensorrt-llm-web-uis/357820/4).


## Índice de hallazgos asociados

- **`BB-NVIDIA-SMI-PROFILER-BLINDNESS`** — A user on kernel 6.11.0-1016-nvidia ran Nsight Systems with CUDA/cuDNN/cuBLAS trace flags but saw CPU/OS data only; nsys status showed CPU system-wide profiling failed with root privilege disabled. NVIDIA said it would investigate;… Fuente: [352250](https://forums.developer.nvidia.com/t/nsys-profile-not-showing-any-gpu-data/352250/1).


## Índice de hallazgos asociados

- **`BB-MTP-SPECULATIVE-DECODE-LONG-SOAK`** — An owner reports intermittent crashes after more than one week with speculative decoding enabled for AWQ4 and FP8 Qwen3-Next on a single Spark using NVCR vLLM 26.01. Their custom NVFP4 image v22 seemed stable only during a short trial;… Fuente: [361300](https://forums.developer.nvidia.com/t/qwen3-next-awq-4bit-vs-fp8-vs-nvfp4-on-single-spark/361300/1).


## Índice de propuestas del lote 00

- `FORUM-00-SM121-CUBIN-ARCH-COMPAT` — [Validate architecture-matched FlashInfer cubins and safe fallback for GB10 inference](); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-CACHE-IPC-VERSION-GATE` — [Reject incompatible external KV cache connector and vLLM IPC versions before startup](); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-CHECKPOINT-LOADER-UMA-BUDGET` — [Validate checkpoint shard integrity, loader mode and OEM UMA headroom before serving](); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`. En [368933, posts 28 y 31](https://forums.developer.nvidia.com/t/introducing-prismascout-prismaquant-v2/368933/31), un operador informa que un fine-tune conserva tensors `mtp.*` pero omite el contador MTP en config; el planificador externo derivó cero shards y dejó pesos fuera de la cuantización hasta que la validación bloqueó el export. El autor reporta un cambio para inferir shards desde los pesos, sin auditoría independiente. Añadir a la comprobación exacta de cobertura checkpoint/config de pesos auxiliares; esto no demuestra un fallo del cargador de BB.
- `FORUM-00-NEMOTRON-VLLM-ENGINE-STABILITY` — [Require a versioned stability soak for Nemotron 3 Super vLLM serving](); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-QWEN38-MROPE-OOB-GRAPH` — [Gate patched M-RoPE kernel and CUDA-graph vision soak on exact SM121 stack](); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-VLLM-GRAMMAR-MTP-TOOL-BOUNDARY` — [Gate structured output and tool-call transitions with speculative decoding](); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`. Un operador también informa formato de tool call roto tras crecer el contexto, supuestamente menos frecuente tras actualizar driver en imágenes 25.x/26.01, sin RCA, versiones exactas ni reproducción ([359555, posts 30–32](https://forums.developer.nvidia.com/t/359555/30)); se conserva como señal sin atribución, cubierta por el mismo canary. El hilo [375607, posts 64–80](https://forums.developer.nvidia.com/t/mimo-v2-5-dflash-speculative-decoding-on-a-2x-dgx-spark-pair-22-67-tok-s-depending-on-workload/375607/64) amplía el canary con MiMo-V2.5/DFlash: KiloCode con esquemas/herramientas grandes produce rechazos de gramática y HTTP 500 en una receta outlines; un operador informa que outlines rechaza EOS, mientras pruebas separadas con backend xgrammar por defecto no reproducen. Probar cada combinación de parser/backend, chat template, harness, tamaño de schema y reasoning/tool transition, incluyendo validez de salida y request completion. Las modificaciones de MiMo, KV cache y DFlash son comunitarias y no auditadas; las cifras de aceptación/TPS dependen del formato de carga.
- `FORUM-00-NCCL-TRANSPORT-PATH-VALIDATION` — [Detect and gate silent NCCL fallback from NET/IB to TCP on GB10 multi-node runs](https://forums.developer.nvidia.com/t/366266; https://forums.developer.nvidia.com/t/collective-operations-timeout-on-dual-spark-during-distributed-training/366147; https://forums.developer.nvidia.com/t/nccl-test-bandwidth-is-only-3gb-s-between-2-dgx-spark-using-qsfp-cable/366373); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-NEMOTRON-LONG-CONTEXT-XID-SMOKE` — [Exercise long-context Nemotron CUDA graph paths and capture Xid 13/43 before admitting an NGC image](https://forums.developer.nvidia.com/t/new-ngc-vllm-container-image-vllm-26-01-py3/359213); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-VLLM-RAY-IDLE-BUSY-LOOP` — [Canary native multiprocessing for Ray-specific vLLM CPU busy loops at idle](https://forums.developer.nvidia.com/t/vllm-100-cpu-usage-when-idle-again/362964); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-PYTORCH-SM121-ARCH-ADMISSION` — [Check effective PyTorch SM 12.1 support before GB10 training](https://forums.developer.nvidia.com/t/effective-pytorch-and-cuda/348230); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-NEMO-LHOTSE-TORCH-API-GATE` — [Smoke NeMo dataloader against exact PyTorch/Lhotse ABI](https://forums.developer.nvidia.com/t/running-parakeet-speech-to-text-on-spark/356353); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-CRS804-BREAKOUT-PORT-MTU-GATE` — [Verify CRS804 breakout, cable EEPROM and L2MTU before CX7 fault triage](https://forums.developer.nvidia.com/t/gb10-qsfp56-ports-speed-connecting-multiple-gb10-with-mikrotik-crs804-ddq/364093); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.

**DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01.** En una malla de tres Spark con PP, un operador reporta SIGTERM silencioso del worker en la primera inferencia usando el contenedor `vllm-node` con NCCL estándar; en el ensayo incremental, varias variables NCCL, Ray, allocator y loader no cambiaron el fallo. El operador reporta éxito posterior con imagen TF5 que llevaba NCCL de mesh; el mantenedor responde que la funcionalidad ya se integró en NCCL main y que la receta se actualizó ([365296, posts 15–16](https://forums.developer.nvidia.com/t/365296/15)). Validar build/image digest/NCCL por rank y una inferencia PP entre etapas en el topology real; load/HTTP ready no basta. Las fuentes externas no fueron auditadas y la corrección es declarada por usuarios; no tratar el caso como bug driver ni trasladar el umbral 0.85 de Grace Hopper a Spark.

[366445](https://forums.developer.nvidia.com/t/dflash-llm-for-dgx-spark-too-good-to-be-true/366445) añade al canario de DFlash dos riesgos independientes. Un dueño de Qwen3-Coder-Next-NVFP4 reporta dos días con más velocidad pero peor calidad, tool execution y reasoning que con INT4-AutoRound; es su opinión y no una prueba pareada. En otro stack, el autor informa dos OOM al usar `gpu_memory_utilization=.85` con DFlash, luego usa `.60`; el valor es stack-específico, no umbral GB10. Una prueba eager/compile con dos prompts tarda ~9.5 vs ~18 min hasta listo, y el beneficio en petición caliente es prácticamente cero según el autor. Separar integridad semántica, OOM/headroom y cold-start/steady state; no aceptar DFlash por TPS ni fijar `.60` globalmente. Parches, gist e imágenes no auditados. Hallazgos relacionados: `BB-NVFP4-SM121-SEMANTIC-ACCEPTANCE`, `BB-VLLM-DRIVER-MEMORY-ADMISSION-SEPARATION` y `BB-DFLASH-CUDAGRAPH-OUTPUT-DIVERGENCE-GATE`.

**DELTA-FORUM-M2-COMPACTION-STATE-VALIDATION-01.** En un hilo de MiniMax M2.1, un operador informa que después de varias compactions con OpenCode+llama.cpp cae el throughput de prefill/decode, degrada la calidad y fallan tool calls; dice que vio algo parecido con otro build vLLM. La causa sugerida —corrupción de estado CUDA-graph al limpiar KV— es solo su paráfrasis, sin versión completa, logs ni reproducción; otra respuesta reporta ausencia del fallo hasta 120K ([356118, posts 17 y 20](https://forums.developer.nvidia.com/t/356118/17)). Añadir al canary de runtime, para modelos/harnesses exactos que limpien o compacten KV, una secuencia larga que cruce límites de compaction/cache-reset, seguida de tool calls, salida semántica y métricas prefill/decode/process/host; repetir con reset limpio y control sin compaction. No atribuirlo a GB10/driver ni recomendar una opción NVFP4/graph como fix.

## DELTA-ROOT-DSML-PARSER-RECOVERY-BOUNDARY-01

[Hilo 378784](https://forums.developer.nvidia.com/t/378784): el dueño reporta filtraciones DSML desde 60K de contexto y un estado roto a 150K después de aplicar PR #49117. La descripción incrustada del PR declara validación del parser, sin ensayo de servicio con el modelo; también reconoce que un marcador citado como prosa, idéntico a una herramienta declarada, puede convertirse en una invocación. Otro dueño reporta un proxy saludable con una imagen diferente: esa comparación requiere controlar el resto del stack.

Propuesta: conservar el historial que reproduce el fallo y probar streaming y respuestas completas, reasoning inconcluso, argumentos truncados, `tool_choice=none` y marcadores citados. Registrar qué queda fuera de la recuperación. El parche y el proxy siguen como candidatos; sus fuentes enlazadas quedaron sin auditar.

Riesgos: invocaciones espurias al interpretar prosa como herramienta y una nueva superficie de fallo al añadir un proxy. Close check: fixture del historial real y ensayo prolongado con contexto largo demuestran recuperación sin llamadas espurias ni pérdida de texto. El rollback restaura los digests y la configuración previa del parser y del proxy.


[368726](https://forums.developer.nvidia.com/t/368726) records a failed four-node switchless ConnectX-7 lane-split experiment: after MFT/MFT firmware configuration created an additional interface, the author found F2 aliased to F0 and able to pass traffic despite no physical connection; the mesh proposal was abandoned. A separate owner later says a four-node ring worked with custom networking/vLLM patches at a 10–20% performance cost, but the repository was not audited. Add an exact-OEM preflight after any CX7 lane/MFT changes that maps PCI BDF ↔ physical connector ↔ netdev and proves each intended link by disconnect/loopback control and sustained peer traffic, then runs NCCL collectives on the intended topology before workload admission. Preserve BIOS/MFT state, Secure Boot implications and recovery path; never infer physical paths from visible interfaces or adopt the community split commands as a supported fix. **DELTA-FORUM-CX7-PHYSICAL-TOPOLOGY-ALIAS-CHECK-01**.

### DELTA-ROOT-MIMO-PATCH-SUPERSESSION-GATE-01 — Admitir parches según versión y validar modalidades

Fuente: [hilo 368097](https://forums.developer.nvidia.com/t/368097); cuerpos capturados leídos, sin auditoría de binarios ni repos externos.

MiMo FP8 sobre GB10: PR41834 evita crash de MTP en 0.20.1rc1, pero su función fue refactorizada en 0.21.1rc1.dev30+g4db300e95 y el owner declara innecesario el parche. CUTLASS block FP8 pasa el gate de capability y falla can_implement; un bypass a Triton reporta éxito. Torchcodec ABI incompatible fue reemplazado por stub text-only, que bloquea audio. MTP/EAGLE producen OOM locks; primer inicio _load_w2 puede quedarse detenido y owner reinicia contenedor.

Propuesta: Gate por digest/revisión y símbolo objetivo: rechazar parche obsoleto, probar backend real SM121 con primera petición y modalidades anunciadas. Registrar carga fría y memoria de draft por rank; recuperación de contenedor propia y acotada. Conservar imagen conocida y rollback exacto. Los repos externos y estado upstream siguen sin auditar.

Riesgo: Stub oculta capacidad audio; copiar swapoff, apagar GUI/servicios o asumir umbral universal amenaza disponibilidad.

Cierre: Reproducir crash en versión afectada y comprobar que versión refactorizada rechaza parche obsoleto; canarios de texto, herramientas y modalidades habilitadas; medir soak con errores y contexto real. Benchmark máximo 100K en el hilo queda separado de configuración 1M.


[375416](https://forums.developer.nvidia.com/t/375416) reports a correctness failure in a community vLLM V1 speculative/MTP path under DCP4: draft parallel configuration reportedly omitted `decode_context_parallel_size`, leaving draft attention in DCP1 while KV/metadata were DCP-sharded. The operator’s tensor-level probe reportedly found no q all-gather/LSE merge and all-zero attention on 3/4 ranks; TP all-reduce then made corrupted state identical across ranks, so a cross-rank equality check passed. The operator reports a code fix and stronger GLM-5.2 MTP3/4 acceptance/throughput on 4×GB10, but the patch/repositories were not audited or run in BB. Add a pinned-image regression that asserts draft effective DCP size, verifies gather/merge and nonzero partial outputs against a DCP1/reference control, then checks coherent deterministic output and per-position acceptance across repeated prompts; do not rely on rank consensus or acceptance alone. The same thread contains a second operator’s NV_ERR_NO_MEMORY before an after-load trim hook; first operator’s memory advice did not resolve that case, so preserve a separate pre-trim load/host-headroom test and do not generalize one configuration’s 128K success. **DELTA-FORUM-DCP-MTP-DRAFT-CORRECTNESS-AND-PRETRIM-OOM-01**.


[379722](https://forums.developer.nvidia.com/t/379722) adds Muse-Glimmer/DFlash admission details. An initial NVIDIA/vLLM image reportedly failed because the draft class was missing; a later owner says their DFlash-enabled vLLM muse-glimmer tag only worked with `max_num_seqs <= 32`, reproduced on their setup. A GB10 report says a patched stack completed an 84-scenario tool eval but still had prompt-injection/hallucination and long-horizon failures; other BFCL measurements swung sharply when the prompt required parallel same-turn calls. Repositories, PRs and benchmark captures were not audited. For the pinned image/model/parser/template, preflight draft class resolution and run an A/B at the reported 32/33 sequence boundary, including bounded resource/CPU/GPU tests and semantic canaries for single-tool, parallel calls, token truncation and untrusted tool output. Treat this as a candidate compatibility limit for the exact branch; never set a universal DFlash concurrency cap or infer product safety from an aggregate benchmark score. **DELTA-FORUM-MUSE-GLIMMER-DFLASH-MAX-SEQS-GATE-01**.

**DELTA-FORUM-GLM52-MULTITURN-CORRECTNESS-AND-RECIPE-SENSITIVITY-01.** [377598, posts 12–17, 23, 27–36](https://forums.developer.nvidia.com/t/377598/12) aporta dos señales que requieren una prueba fijada por stack: un operador reporta que GLM-5.2 Hybrid FP8/MXFP4 con vLLM `0.11.2.dev279`/fork `b12x284a2ea`, driver/build CUDA 13.2.1 y `VLLM_ADAPTIVE_SPEC_DEPTHS=2,4` empezó a producir texto multilingüe incoherente tras 80–95K tokens y 15+ turnos con prefix caching; sus needle tests de prompt único seguían funcionando. Logprobs cercanos a distribución uniforme son medición del operador, sin archivos de trazas adjuntos. Otro reporte mide la categoría de salida estructurada en 58% con thinking activado y 100% desactivado en seis escenarios A/B de una sola ejecución; la misma publicación registra menor resultado de razonamiento/restricción en el benchmark completo al desactivar thinking. El autor también describe un bucle de unas 200 llamadas con `tool_choice=required`, falsos números de prefill al omitir `--tokenizer`, y una penalización de repetición 1.2 que causaba “word slop” en su GLM-5.2. Son reportes de operadores, no reproducción local ni fix validado. Añadir a la canaria de runtime sesiones multi-turno crecientes con prefix cache, comprobaciones de distribución/finish reason y semántica; separar prompts de formato estricto y razonamiento al probar `enable_thinking`, y limitar iteraciones de herramientas en el harness. Registrar tokenizer, parámetros de generación y entorno efectivos para interpretar resultados. Cierre: repetir en el digest/driver/runtime/model exactos un A/B de conversación creciente y prompt único, ejecutar el canario estructurado y de razonamiento con thinking on/off, y confirmar que el límite/timeout corta el bucle `tool_choice=required`; comparar salidas y recursos, conservar la configuración conocida y revertir únicamente el parámetro probado si causa regresión. Evidencia, versiones y cambios de calidad siguen pendientes de validación independiente.

**DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01.** [358382, posts 18–23](https://forums.developer.nvidia.com/t/358382/18) documentan un fallo concreto en dos Spark con GPT-OSS-120B y vLLM V1/Ray: la solicitud deja el worker inactivo y el proceso termina con `RayChannelTimeoutError` tras `RAY_CGRAPH_get_timeout=300`, mientras logs previos muestran mismatch entre el TP=2 requerido y un placement group con 1 GPU reservada por nodo. El usuario inicialmente probó una imagen anterior a un cambio MXFP4; en post 20 el fallo continúa después de reconstruir, y en post 23 reporta éxito con imagen fechada `20260130`, `--rebuild-deps` y el build MXFP4, junto con `ray status`, carga completa y respuesta terminada. Esto no demuestra que el cambio específico resolviera la causa, ni que las recomendaciones de subnet/MTU fueran necesarias; los logs/configuración se publicaron en línea y no se ejecutaron ni auditaron. Para el gate multi-node del runtime, conservar una prueba de placement group/rank/GPU efectivo antes de admitir la carga, y una inferencia acotada que registre actividad por nodo, primer token/fin y timeout Ray. Anclar evidencia al tag/digest, commit y wheels reales. Cierre: con dos GB10 y el mismo checkpoint, verificar recursos asignados y una petición semántica repetida bajo imagen anterior/candidata cuando sea reproducible; la candidata debe completar sin timeout y registrar versiones efectivas. Mantener el digest anterior para rollback; no aumentar el timeout ni fijar MTU/NCCL como remedio sin A/B causal.

**DELTA-FORUM-QWEN38-LONG-RUN-JSON-CORRECTNESS-CANARY-01.** [380248, posts 27, 34, 36–38](https://forums.developer.nvidia.com/t/380248/27) contiene un reporte aislado de Qwen3.8-27B: un operador dice que varios proveedores/quant mostraron salidas JSON cada vez menos válidas durante tareas autónomas largas, con aproximadamente 3/4 malformadas tras 30 minutos; no presenta prompts, respuestas ni hashes que permitan atribuirlo a AutoRound, FP8 KV, temperatura o MTP. Otros participantes expresan preocupación por deriva de calidad en procesos largos y por diferencias de BF16/FP8, pero reconocen que son observaciones subjetivas y no ofrecen pares controlados. En la misma discusión, la ficha inicial permite `max_model_len=1010000`, aunque sus pruebas visibles de throughput terminan a profundidad 8192; ese número de configuración no prueba integridad a un millón de tokens. Conservar como señal para la canaria semántica de runtime: sobre una versión/modelo exactos, ejecutar tareas largas repetidas que requieran JSON validable, guardar checksums/digest del checkpoint, backend, tokenizer, template, sampling, KV y MTP, y comparar control BF16 contra candidato cuantizado/FP8 si el stack lo soporta. Rechazar degradación objetiva de formato o contenido bajo criterios definidos antes del ensayo; mantener rollback de imagen/checkpoint. Cierre requiere fixtures reproducibles con respuestas completas y comparación pareada/soak; la anécdota por sí sola no demuestra regresión ni prescribe BF16.

### DELTA-ROOT-GLM53-QUEUED-REQUEST-PROGRESS-GATE-01

Fuente: https://forums.developer.nvidia.com/t/382939/178 y https://forums.developer.nvidia.com/t/382939/181.

Posts 178/181: tras más de 40 horas, una petición decodifica mientras hasta siete quedan sin prefill durante 14 minutos. Reducir max_num_seqs de 8 a 4 reproduce antes; segundo episodio declara KV máximo 37%, frente a 99% del primero. Endpoint vivo y porcentaje KV por sí solos omiten este hang parcial.

Acción preventiva/correctiva: Canario por petición y etapa: antigüedad de cola, inicio/progreso de prefill, tokens decodificados, concurrencia real y terminación/cancelación. Retención de prefix cache y recompilación se validan con prompts reales repetidos; TTFT largo esperado se distingue por progreso. Cuotas de concurrencia y recuperación acotada deben preservar otras peticiones y registrar causa desconocida.

Cierre: Soak multiusuario por digest/commit/modelo con fixture de una petición activa y otras bloqueadas. Detectar bloqueo con KV bajo, permitir prefill lento que progresa, limitar reintentos y probar rollback. Benchmarks breves o TEB no cierran estabilidad del host.

Riesgo y límites: Un solo propietario; recetas cambiantes y logs externos sin auditoría. Diagnóstico externo central sobre freezes de driver permanece `could_not_run`; ausencia de causa aislada impide convertir una versión de driver en fix universal.

**DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01.** [370834, posts 15, 21–24, 39, 42, 47, 52](https://forums.developer.nvidia.com/t/370834/15) registra una señal preventiva de seguridad crítica: con Qwen3.5-122B-A10B INT4 AutoRound, operadores reportan que `tool-eval-bench` activó una sleeper injection entre turnos y añadió BCC/CC de un atacante descrito en el resultado del clima inicial. El aviso reaparece en otro ensayo del mismo hilo con el stack publicado como “definitivo”, en Qwen3.6-27B abliterated NVFP4/MTP y en Qwen3.5-397B con y sin Ray; las pruebas usaron distintos builds y el test de 397B está parcialmente truncado en el post 42. Un usuario atribuye haber despejado las amenazas al parser XML/template y otro reporta 5/5 tool calls fallidos al probar una receta/parser distinto en vLLM 0.22; esos comentarios no demuestran fix ni causalidad. Los resultados agregados de 91–97/100 y los subset de 15 casos no cubren por sí solos la seguridad multi-turno. Añadir al canario de promoción del runtime un caso determinista de herramienta no confiable en el turno inicial seguida de acción de correo controlada en otro turno; comprobar que el contenido inyectado nunca altera destinatario, CC/BCC, cuerpo ni selección de herramienta. Usar herramientas mock y registrar checkpoint, parser/template, imagen, vLLM, tokenizer y harness exactos; exigir cero efecto de la instrucción atacante en varias repeticiones y mantener un control positivo que demuestre que el fixture sí llega al contexto. El hilo [367085, posts 21, 65, 76 y 98](https://forums.developer.nvidia.com/t/introducing-prismaquant/367085/21) aporta otras advertencias TC-60 en Qwen3.6-35B/27B y Qwen3.5-122B, incluso con puntuaciones agregadas de 92–94/100; imágenes sin revisar y stacks/plantillas distintos impiden comparar causalidad. Una plantilla/parser candidato necesita ejecutar el mismo caso y controles completos antes de aceptarse. Cierre: la configuración candidata completa la suite multi-turno con rechazo de la instrucción del resultado de herramienta, sin filtrarla a la respuesta ni generar mutación de correo no autorizada; parser, modelo o template que falle bloquea promoción y se revierte al digest conocido. No aplicar el parser comunitario ni recetas de cuantización de este hilo automáticamente.

### DELTA-ROOT-CONTAINER-EFFECTIVE-BUILD-AND-OFFLINE-GATE-01

Fuentes: https://forums.developer.nvidia.com/t/362721/24 y /26–46; https://forums.developer.nvidia.com/t/375945/9 y /19–43.

362721: repo y wheel actualizados coexistieron con imagen efectiva experimental vieja, falta de kernels NVFP4/no-act-and-mul y MXFP4 roto; nombre por defecto reutilizó contenedor al intentar segundo modelo. Rebuild y cambio de cuota ayudaron a un propietario; otro seguía fallando, luego carga FP4/8 tras limpieza completa sin causa aislada. HEAD a HF bloquea inicio por timeouts. 375945: 1M real requiere TTFT 2524584ms; bucle de thinking es fallo de contenido y ocurre también fuera de la receta, mientras DCP aceleración inicial fue explícitamente desmentida.

Acción: Preflight y canario comprueban digest y build efectivos dentro de cada contenedor, modelo/checkpoint/patches, nombre y puerto reales y reserva conjunta de memoria. Probar carga e inferencia real de la arquitectura, no inferir compatibilidad de presencia de torch.ops antes de importar extensiones. Precachear artefactos completos por revisión y verificar arranque sin red antes de activar modo offline. Conservar imagen anterior y aislar cache mediante rename+manifest con sha/mode/expiry/vigía, sin copiar purgas globales de volúmenes.

Cierre: Fixture wheel nuevo/imagen vieja detectada; dos instancias nombres/puertos distintos y presupuesto agregado. Canary por modelo carga y genera; rollback a digest previo. Arranque sin red completo y fallo explícito por archivo faltante. Permitir prefill largo con progreso; detener bucle de contenido con presupuesto y error específico.

Riesgos: Tests nightly declarados por mantenedor no auditan cada carga del usuario; PR/código externo sin revisar; Offline con caché incompleta impide arrancar; bucles semánticos y prefill largo requieren clasificación distinta.


**FORUM-00-DS4F-APPEND-PREFILL-KV-CHECKPOINT-GATE.** [377281, posts 51 and 93](https://forums.developer.nvidia.com/t/concern-about-the-usefulness-of-a-single-dgx-spark/377281/93) contrasts an owner’s single-GB10 DS4 workflow that reportedly took about an hour to inspect 60 small files because each turn re-prefilled the unchanged history, with a separate CUDA-fork author’s report of append-prefill and canonical KV checkpoint reuse. That author reports ~836 tok/s average prefill while appending from 128K to 181K and 24–25 tok/s decode at 55K–70K, but gives no exact stack versions in the post; attached benchmark screenshots were not reviewed and neither implementation nor figures were independently validated. Review and pin the source, then A/B baseline vs reuse with cold/warm prefill, per-turn latency, cache hits/bytes, changed-prefix invalidation, answer equivalence and UMA/cgroup state on a single GB10. Preserve prior image/config for rollback; do not treat the reported speed as a BB baseline or promote unreviewed KV checkpoints.

**DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01.** [366828, posts 25–26, 42, 72–74, 80–90, 96–99, 105–106](https://forums.developer.nvidia.com/t/366828/80) aporta tres señales de corrección/recuperación en Qwen3.x/vLLM: un tool-eval de Qwen3.6-35B-A3B INT4 AutoRound reporta de nuevo el fallo crítico TC-60 de sleeper injection; enlaza al delta `DELTA-FORUM-CROSS-TURN-SLEEPER-INJECTION-REGRESSION-01`. Por separado, un operador de Qwen3.5-122B dice que MTP con más de 1 token rompía tool calls (`Expected function.name to be a string`) bajo vLLM `0.19.2rc1` y `qwen3_xml`; en su ensayo, MTP=1 evitó los errores, pero otro usuario reportó MTP=3 estable con vLLM 0.20.2 y luego autor atribuyó resolución a cambiar parser a `qwen3_coder`, sin A/B compartido. El autor también informa un fallo intermitente tras cancelar generación en curso: el texto continúa, pero el parser deja de producir tool calls hasta reiniciar vLLM; el wrapper descrito reinicia el proceso en bucle cuando sale. Los reportes no aíslan parser, MTP, cancelación o cambio de build como causa; imágenes externas de benchmark no fueron inspeccionadas. Añadir a la compatibilidad fijada una matriz reducida de parser × MTP × cancelación con herramienta mock: respuestas parciales/completas, una cancelación mid-stream y el siguiente tool call en el mismo proceso. Registrar salida del parser, finish reason, exit/restart y alertar en transición `HTTP 200`/inferencia viva pero 0 tool calls inesperados. Cierre: bajo un digest/version exactos, cada combinación admitida conserva llamadas correctamente tipadas antes y después de cancelar; repetir tras reinicio distingue recuperación del proceso de recuperación del parser. No convertir `MTP=1`, `qwen3_coder` ni auto-restart en arreglos universales; mantener el límite probado o bloquear el combo defectuoso con rollback fijado.

### DELTA-ROOT-RAY-MULTIENGINE-RANK-PROGRESS-01

Fuentes: https://forums.developer.nvidia.com/t/377396.

Post101 relata dos vLLM dentro del mismo cluster Ray con NCCL atascado, sin logs ni versión; Distributed mp se propone, sin A/B demostrado.

Acción: Antes de admitir segundo motor, verificar identidades, presupuesto agregado y progreso real de cada rank en ambos motores; medir colectivo y petición real, no solo disponibilidad Ray. Fijar digest y configuración; aislar recursos y recuperación al motor afectado.

Cierre: Fixture un motor sano y otro sin progreso colectivo; detectar el afectado y mantener al primero. A/B efectivo y rollback de cambios de executor.

Riesgos: Relato único sin versión; mp es propuesta, no fix confirmado.

### DELTA-ROOT-MIMO-OVERLAY-AND-PREFILL-FAIRNESS-01

Fuentes: https://forums.developer.nvidia.com/t/373669.

Post132 modelo cargado sin errores emite ASCII aleatorio y acceptance de draft casi cero; overlay ausente publicado después permite funcionar (135–139), sin causa kernel aislada. Posts161/163 sesión350K segunda petición reprocess prompt/stall y prefill de una detiene decode de otra. Load_model OOM antecede KV(40/44); bajar utilización KV omite ese pico.

Acción: Manifiesto efectivo por nodo de imagen, checkpoint, overlay, draft, tokenizer y mods con hashes; resolver symlinks en mounts y probar artefactos antes de cargar. Canary semántico real y por modalidad, per-rank y etapas. Admisión incluye coldload/draft previo KV. Escenario concurrente con prefill largo y decode corto, progreso y límites de espera; comparar chunked-prefill/batch como candidatos con riesgo de memoria, sin umbral universal.

Cierre: Fixture overlay ausente/symlink roto falla antes de servir. Respuesta semántica real y error específico en modalidad no validada. Soak prefill/decode simultáneo mide espera por petición y recuperación acotada; retorno a digest/config anterior probado.

Riesgos: Mods publicados tarde y recetas contradicen eager/Ray/comando; código externo no auditado; Éxito de un owner no resuelve todos los OOM ni demuestra calidad omnimodal.


**`BB-DSPARK-DRAFT-QUANTIZATION-FAIL-CLOSED`.** [371652, post 49](https://forums.developer.nvidia.com/t/step-3-7-flash-is-supported-in-community-docker-on-dgx-spark/371652/49) aporta un caso distinto al de DeepSeek: en Step-3.7 Flash NVFP4, un operador de 2×Spark TP=2 reporta que el cargador MTP intenta copiar el vocabulario completo de ancho 4096 a un shard local de ancho 2048 y aborta; el serving sin MTP funciona en el mismo montaje. La causa observada es incompatibilidad de forma/sharding al cargar el draft, sin parche ni corrección posterior auditados. Añadir un test de carga distribuida TP=2 que compruebe cada tensor contra la forma local por rank y falle antes de activar MTP, con nombre, formas y rank en el error; TP=8 no cubre TP=2. La conversación también contiene informes contradictorios sobre `libtorch_cuda.so` en rebuilds comunitarios (posts 42, 44–45), así que sirven para probar la matriz exacta de imagen/runtime, sin atribuir una regresión general. No se auditaron contenedores, código ni artefactos enlazados. Hallazgo literal: `BB-DSPARK-DRAFT-QUANTIZATION-FAIL-CLOSED`.

### DELTA-ROOT-TRITON-ALLOCATOR-PATCH-STATE-GATE-01

Fuente: https://forums.developer.nvidia.com/t/359571/38 y /50–63, /87–92.

Ray TP2 falla con allocator Triton; eager permite cargar pero degrada. Post38 propone NullAllocator.__call__ global via .pth y torch.cuda.caching_allocator_alloc con except Exception:pass. Mantenedor confirma funcionar en50, pero necesita commit previo13397841ab469cecf1ed425c3f52a9ffc38139b5 además, pues el fix de arranque solo deja 1–2 tok/s. Patches crash/performance después upstream integrados/revertidos fallan hunks y se ignoran(57–63). El cambio de imagen base causa torch._opaque_base ausente(87–88); el autor del post 92 recupera con un build nuevo.

Acción: Catalogar patch como candidato específico por commit/Triton/Ray; detectar estado ausente/aplicado/supersedido/incompatible y verificar extensión efectiva en cada rank/hilo. Excepción silenciosa y omitir parches no certifican corrección. Probar carga, primera petición fría, generación semántica, warmup y prefix hit repetido. Preservar digest previo; rollback no toca otras imágenes.

Cierre: Fixture patch falla silenciosamente o fue supersedido identifica estado real; canary distingue startup arreglado de regresión y calentamiento inicial de hang con progreso. Auditoría de código y propiedad de memoria/alignment/stream antes de recomendar monkeypatch global; rollback probado.

Riesgos: Modifica allocator global y se ejecuta por .pth; fragmento no prueba gestión/lifetime de memoria; Casos posteriores contradicen recetas anteriores; commits y wheel efectivo deben fijarse.

### DELTA-ROOT-RECIPE-MEMORY-UNKNOWN-AND-RAW-EVIDENCE-01

Fuentes: https://forums.developer.nvidia.com/t/360319/50 y /14–22, /118.

Ejemplo llama.cpp post50 imprime DGX Spark fit:YES usando solo 1.58 GB de pesos, pero inmediatamente dice arquitectura ausente y estimación de KV unavailable; log real agrega 896 MiB de KV y buffers. Posts14–22 crash/hang de caché de prefijos en vLLM tras actualización admite commit previo y mod posterior; throughput positivo de otras máquinas no prueba este workflow.

Acción: Presupuesto de admisión incluye weights, KV, staging, graphs, draft, buffers y reserva del host por etapa y runtime. Campos desconocidos impiden afirmar seguro; exigir canario funcional efectivo o perfil medido compatible. Reusar exportación consolidada de receta/comando/resultados de sparkrun como evidencia candidata con versión y digest, no crear otro launcher. Evitar pip upgrade sin fijar versiones en cada arranque; validar imagen base efectiva y rollback.

Cierre: Fixture pesos que caben con KV desconocido reporta unknown y no promete protección. Comparación por hardware/topología/digests/checkpoint/params y resultados crudos con workload real posterior a warmup; cambio de backend validado funcionalmente y rollback disponible.

Riesgos: Estimaciones y tests de comunidad no sustituyen admisión/soak del host; Exportador/código externo sin auditoría.


### DELTA-FORUM-VLLM-GB10-ARCH-AND-BUILD-MATRIX-01

[348862](https://forums.developer.nvidia.com/t/run-vllm-in-spark/348862) contains 159 available post bodies with distinct owner-reported failures across GB10 builds: unresolved CUTLASS symbols; Triton 3.5.0 PTX rejected for `sm_121a`; CUDA/architecture-specific CMake kernel selection; a vLLM 0.11.1rc4 TorchInductor autotune failure; and later vLLM 0.12.0 startup after community patch/dependency changes. NVFP4 performance and parser/model compatibility also vary by stack. The changes are confounded, so they do not establish a general fix.

Extend the exact-stack gate with compiler/PTXAS, architecture flags, wheel provenance and resolver output, model/quantization, and the selected backend. Require build/import, model load, functional generation and finite-output checks on pinned digests, with a mismatched-toolchain negative control and image rollback. Treat eager mode, nightly packages, architecture exclusions, and community patches as experiments until validated on the target model. Linked repositories, screenshots, and external log files were not audited; post 117 itself says its patch excerpt is truncated.


**`BB-MTP-SPECULATIVE-DECODE-LONG-SOAK`.** El hilo [374846, posts 13, 43, 56, 65, 69, 71, 75, 79, 82, 84, 87, 96–97, 103–104](https://forums.developer.nvidia.com/t/deepseek-v4-flash-dspark-on-2x-dgx-spark-gb10-big-single-stream-speed-boost-60-67-tok-s-1m-context-now-with-concurrency/374846/97) añade un caso de dos Spark con DeepSeek-V4-Flash-DSpark. Un operador informa CUDA illegal-memory-access/gibberish; otro midió caída sostenida de ~56 a ~34 tok/s, hasta 0.1–1.1 tok/s con dos agentes, KV 96–98%, OOM y recuperación temporal tras reiniciar el contenedor. Driver 580.159.03 y la teoría de starvación/corrupción de KV aparecen como hipótesis, sin logs de incidente ni A/B que pruebe causalidad. Hay contrapruebas de distinta carga/versiones: un batch nocturno 250K reportó cero abort/OOM/wedge (post 56), el autor anunció un runtime fix (71) mientras persiste tool leakage para otro usuario (75), una build comunitaria vLLM 0.23.1rc1 con fixes específicos pasó cuatro needle probes 300–500K (87), y una receta posterior v0.25.1 informa salida limpia pero menor rendimiento que custom images (104). Añadir soak de tráfico multiagente con pool KV/concurrency acotados, métricas de cola/espera por petición, finish reason, salud del proceso, CUDA/Xid, aceptación por posición y verificación de contenido/tools; introducir backpressure antes de caída y captura de evidencia antes de recovery. Comparar target-only frente a DSpark y probar cold-resume; fijar el soak sobre la duración observada. Un restart que restaura velocidad solo caracteriza recuperación, no identifica causa. Repositorios, PR #4, código y adjuntos externos no auditados; no endorsar recetas de topk ni limpieza de caché. ID literal `BB-MTP-SPECULATIVE-DECODE-LONG-SOAK`.

**DELTA-FORUM-DUALSPARK-NCCL-GID-TWIN-AND-COLD-RECOVERY-01.** En [361967, posts 158–167 y 190](https://forums.developer.nvidia.com/t/361967/162), un operador de dos ASUS GX10 reportó NCCL allReduce fallando al inicializar Qwen3.5-397B-A17B INT4 AutoRound aunque `ib_write_bw` entre pares alcanzaba 108 Gbit/s y las cuatro interfaces figuraban UP. En el post 190 redujo `IB_IF` de `rocep1s0f1,roceP2p1s0f1` a `rocep1s0f1`; observó que el índice GID 3 del twin sin IPv4 era null, y después NCCL avanzó, aunque la recuperación también incluyó apagar y desconectar ambos suministros. Es evidencia de que `ib_write_bw`, link-up y GID de otra interfaz no validan el HCA/GID efectivo de NCCL; no aísla el cambio causal. Extender el preflight multi-nodo ya existente para registrar por nodo el HCA/RoCE twin seleccionado, IPv4/GID index efectivo, MTU e interfaz usada, y ejecutar collective NCCL y primera inferencia con la misma selección del serving. Incluir control con twin sin IPv4/GID null y conservar el inventario/log antes de recovery. No autoquitar interfaces ni aplicar ciclo de energía; esos cambios requieren canary, evidencia de antes/después y rollback de configuración. Prueba reportada en kernel/red/imagen de marzo 2026, sin reproducción local.

**DELTA-FORUM-QWEN35-NVFP4-CUTLASS-FIRST-REQUEST-GATE-01.** [361639, posts 94 y 173](https://forums.developer.nvidia.com/t/361639/173) informa que un modelo Qwen3.5 NVFP4 llegó a server-ready y falló en la primera petición con CUDA illegal instruction; el autor dice que varias variantes Qwen3.5 NVFP4 compartían el fallo con CUTLASS y que seleccionar `VLLM_NVFP4_GEMM_BACKEND=marlin` y `VLLM_TEST_FORCE_FP8_MARLIN=1` permitió una prueba GPQA sobre Qwen3.5-35B-A3B-NVFP4. El reporte no identifica una combinación universal de modelo, build, backend o driver y no compara semántica/rendimiento pareados. El gate de arquitectura/runtime debe ejecutar una primera inferencia real después de readiness, registrar kernel/backend y CUDA/Xid, y bloquear promoción si aparece una instrucción ilegal. Probar cualquier fallback sobre el modelo y digest exactos contra una referencia semántica, soak y rollback; esos env vars son una hipótesis/workaround del operador, no un default recomendado.

El hilo [367696, post 55](https://forums.developer.nvidia.com/t/deepseek-v4-released/367696/55) da una firma reproducible por el operador para DeepSeek-V4-Flash en vLLM `0.19.2rc1.dev272+gda7349a00`, TP=2, GB10, sparse MLA y MTP: MTP disparó `AssertionError` porque la ruta de referencia SWA solo admite un query token por petición (`num_decode_tokens=8, num_decodes=4`; otro intento con eager tuvo `2` frente a `1`), mató EngineCore y la petición. El mismo post informa un arranque/serving sin MTP, pero no aísla todos los cambios entre ejecuciones. Tratarlo como un control negativo exacto para el canary del speculative path: conservar el log y scheduler dump, validar MTP-off y MTP-on contra la misma imagen/build/harness, y confirmar que el modo MTP queda rechazado o completado sin fatal engine exit; no inferir que `--enforce-eager` lo corrige. Posts posteriores del mismo hilo reportan calidad de tool-call variable y perfiles de aceptación distintos bajo otros commits/modelos, por lo que los resultados 15-case o 1M-context de terceros no reemplazan la prueba funcional y el soak. El post 38 aporta un segundo intento multi-Spark Ray/vLLM que reporta falla al iniciar EngineCore tras cargar 74.05 GiB, pero el cuerpo oficial termina a mitad del stack en `ray_ex`; los endpoints raw y JSON devuelven la misma traza parcial y revisions es 404. No es posible identificar la línea final ni atribuir el fallo a una incompatibilidad de arquitectura. Copia de la traza truncada: `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/attachments-root/367696-post38-raw-truncated.txt`. Los demás repos/imágenes enlazados en el hilo no se tomaron como auditados.


### DELTA-FORUM-MTP-ACCEPTANCE-AND-SEMANTIC-CONTROL-01

[361163](https://forums.developer.nvidia.com/t/we-unlocked-nvfp4-on-the-dgx-spark-20-faster-than-awq/361163) adds a direct MTP counterexample: one owner reports Qwen3-Coder-Next NVFP4 at about 38 tok/s without MTP and about 26 tok/s with MTP, with zero acceptance; separate reports vary by model/build, and a cold restart reportedly restored speed without rebuilding. Benchmark labels also differ: speculative accepted output rate and target decode rate are distinct. The repository patches, images, scripts, screenshots and raw result files were not audited, and no matched independent correctness run appears in the thread. A later Qwen/PrismaQuant thread [367085, posts 71–74, 139 and 155–160](https://forums.developer.nvidia.com/t/introducing-prismaquant/367085/71) also reports that MTP/DFlash behavior changes with context pressure, concurrency and backend; one 50%-context-pressure test saw little difference between MTP=2 and 4, while other results changed after DFlash/SWA build changes. This supplies no universal speculative-token count.

For each pinned model/image/backend, compare MTP on/off with the same prompts, output limits, concurrency and warm/cold state. Record per-position acceptance, semantic/tool correctness, prefill and decode latency, target decode rate, user-visible rate and memory. Gate zero acceptance or failed output checks and retain the last known-good recipe for rollback; do not infer a universal NVFP4 or MTP setting from this thread.


### DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01

[364736](https://forums.developer.nvidia.com/t/why-turboquant-saves-dgx-twice/364736) includes a material correction: the author retracted a claim of 92.5% q4_0 prefill collapse and higher memory use after identifying that the original memory measurement used process RSS instead of the llama.cpp KV buffer. The corrected owner report gives 216 MiB q4_0 versus 768 MiB f16 KV, with no prefill cliff and about 37% lower decode rate at 110K context. Later TurboQuant/RotorQuant timings, quality and kernel claims vary by fork/config and remain unverified; external repositories and result files were not audited.

Keep RSS, cgroup, host available memory/swap, allocator residency and framework KV bytes as separately labeled counters. Compare the exact K/V mode, backend, model, context and concurrency with output correctness and prefill/decode measurements. A KV capacity win does not establish faster or correct generation; the reported values are not universal thresholds.


### DELTA-FORUM-MINIMAX-TOOLCALL-FUNCTIONAL-CANARY-01

Fuente: https://forums.developer.nvidia.com/t/minimax-m2-7-nfvp4-recipe-benchmarks/366324 (127/127 cuerpos revisados).

Un operador informa que `health 200`, la carga de 15 shards, CUDA graphs y una generación simple pasaron en `vllm/vllm-openai:latest`, pero la segunda petición —la primera llamada de herramienta— se bloqueó con timeout de shared-memory broadcast y `EngineDeadError`. Tras reiniciar, también se bloquearon peticiones simples. El mismo operador reporta después éxito con `nvcr.io/nvidia/vllm:26.06-py3` / vLLM 0.22.1 y Ray instalado; cambió varias piezas a la vez, así que el hilo no demuestra cuál resolvió el fallo. También hay relatos de caracteres insertados en llamadas de herramienta en versiones específicas de vLLM/FlashInfer, con configuraciones y resultados posteriores distintos. No hay reproducción independiente ni auditoría de repositorios, imágenes y adjuntos enlazados.

Extender el gate existente para separar readiness HTTP de readiness funcional. En cada digest fijado de imagen, driver, vLLM, Ray, FlashInfer, cuantización y parser, ejecutar en el mismo proceso: texto simple → llamada mock de herramienta con nombre de archivo puntuado → texto simple. Verificar argumentos byte-exactos, resultado del mock, finish reason y vida del proceso; conservar logs de timeout/RPC y comprobar rollback. Un health 200 o una sola generación no basta para promover la pila.


**`BB-QWEN38-DUALSPARK-CUDAGRAPH-STARTUP-GATE`.** En Qwen3.8-Flash-Next FP8 sobre dos GB10, TP=2 y expert parallel, el autor de la receta dice que la captura CUDA Graph bloqueaba el warmup en `shm_broadcast` durante collectives cross-node; el mismo owner informa que `--enforce-eager` arranca el mismo cluster después de una bisección (#40). La versión indicada es vLLM `0.1.dev20073+g8e685d198`; el build y la causa no se verificaron independientemente. Añadir captura por rank de fase/progreso y un watchdog acotado que bloquee admisión si el warmup queda atascado; comparar eager y graph solo en esta tupla y hacer un canary semántico antes de abrir tráfico. Cualquier reintento debe conservar logs. No convertir eager ni tamaños de grafo en default global. Ver también los deltas de carga picos UMA y PLE mixto de este hilo bajo `FORUM-00-CHECKPOINT-LOADER-UMA-BUDGET`. Source: [381440/40](https://forums.developer.nvidia.com/t/qwen3-8-flash-fp8-dual-sparks/381440/40), y contexto de versión [381440/69](https://forums.developer.nvidia.com/t/qwen3-8-flash-fp8-dual-sparks/381440/69). ID literal `BB-QWEN38-DUALSPARK-CUDAGRAPH-STARTUP-GATE`.

**Delta `FORUM-00-CHECKPOINT-LOADER-UMA-BUDGET` — 381440.** Un owner reporta que safetensors eager dejó ambos nodos sin SSH/HTTP al cargar Qwen3.8-Flash-Next FP8; requirió power-cycle. Con `--safetensors-load-strategy lazy` el load completó a util `.83`, con mínimo ~8 GiB libres (post62). Es una mitigación reportada por un solo stack, no un umbral universal; incluir modo de loader y pico de page-cache/UMA en cold-load canary, obtener logs por nodo y retener rollback antes de recomendar una modalidad. Además, un owner identifica que checkpoint NVFP4 conserva shards PLE FP8 y escala BF16 pese a ruta de config mixta; vLLM falla por faltar `ngram_embedding.weight_scale` (post69). El autor advierte que descartar la escala corrompe embeddings; el gate de loader debe comprobar coherencia config↔tensor y fallar con claridad, y el parche sugerido espera revisión/A-B antes de adopción. No se auditaron repos ni diffs externos.


### DELTA-FORUM-DFLASH-XGRAMMAR-STRUCTURED-OUTPUT-REGRESSION-01

Fuente: https://forums.developer.nvidia.com/t/qwen3-6-27b-is-out/367503/292-295 y /286-295 (301/301 cuerpos del hilo revisados).

Operadores reportan errores de llamadas y salidas estructuradas con Qwen3.6/DFlash en revisiones de vLLM distintas. Un relato atribuye 500 HTTP a que xgrammar recibía el bloque speculative completo y rechazaba tokens posteriores al JSON válido; otro informa que `qwen3_coder` entregaba parámetros en un chunk grande y `qwen3_xml` podía emitir tool calls vacías. Tras un upstream revert, un dueño dice que los 500 desaparecieron en vLLM `0.23.1rc1.dev54`, pero quedó un fallo semántico de herramienta. Los reportes no aíslan un arreglo general y los PRs/branches cambiaron de base y estado varias veces. No se auditaron repositorios, PRs, capturas ni logs externos.

Ampliar la matriz del runtime fijado con DFlash + JSON estructurado, llamadas de herramienta streamed y no streamed, llamadas paralelas y follow-up tras respuesta de herramienta. Capturar respuesta HTTP, parser, finish reason, fragmentación de chunks, salida y salud del proceso; validar JSON y argumentos con fixtures deterministas. Registrar commit efectivo de vLLM y estado del patch/merge en la imagen. Un benchmark de velocidad no pasa esta barrera funcional. Probar la revisión incompatible como control negativo y conservar rollback al último digest que supera la matriz.


**`BB-GLM52-CUTLASS-DSL-STARTUP-GATE`.** En un reporte de GLM-5.2 con 4× GB10/sm_121, un operador dice que el firmware/driver 580.159.03 dejó de compilar b12x CuteDSL con `nvidia-cutlass-dsl==4.5.2` (`ValueError: Operation creation failed (via atom_tma_partition)`); dice que subir a 4.5.3 corrigió la compilación ([374125, post 157](https://forums.developer.nvidia.com/t/glm-5-2-on-a-4-gb10-cluster-22-tok-s-decode-256k-ctx-recipe/374125/157)). El autor aclara que construyó la imagen después de la actualización y no pudo hacer A/B del driver, así que la asociación temporal no demuestra regresión del firmware. Gatear compilación de kernels y dependencias del runtime fijado antes de servir; conservar imagen y dependencias conocidas y rollback. Repositorio, patches y scripts no auditados.

El mismo hilo añade dos señales al hallazgo `BB-FLASHINFER-COLD-PREFILL-MBARRIER-HANG`: un operador reporta deadlock de shared-memory broadcast/EngineCore solo con speculative decoding y dos días estables tras desactivarlo, pero luego descubre dos patches omitidos al construir su imagen; el trigger queda incierto ([374125, posts 202–208](https://forums.developer.nvidia.com/t/glm-5-2-on-a-4-gb10-cluster-22-tok-s-decode-256k-ctx-recipe/374125/202)). Otro autor enlaza evidencia de cold-prefill mbarrier y dice haber visto el deadlock dos veces, con fixes todavía bajo prueba de workloads reales (post 203). No se revisaron esas evidencias ni los patches. Esto amplía la cobertura de la matriz por modo MTP/DSpark y construcción exacta de imagen, sin validar causa o workaround.


**`BB-GEMMA4-TF5-BUILD-PATCH-DRIFT-GATE` — evidencia adicional.** En Gemma4, usuarios informaron una firma incompatible del constructor del parser corregida por PR, razonamiento ausente de `reasoning_content` en streaming, y prefijos HTML duplicados por una ruta del tool parser; un operador dice que PR #38909 corrigió la mayoría, con fallos ocasionales aún visibles ([365490, posts 4, 19–20, 28–31, 93–97, 109, 114–119, 153–174](https://forums.developer.nvidia.com/t/gemma-4-models-which-vllm-version-any-prs-spotted/365490/114)). En el mismo hilo, rebuilding contra dependencias cambiantes falló temporalmente, y el mantenedor separó ruedas estables de rebuilds bleeding-edge. La evidencia pide fijar digest de imagen, vLLM/Transformers/Torch y patchset y probar reasoning/tool streaming, schemas y contenido HTML de salida por turnos; repos/PRs externos no se auditaron y la solución reportada es parcial.


**`BB-GB10-MXFP4-TP2-STREAM-COMPAT-GATE`** — En [356651, posts 41–44 y 52](https://forums.developer.nvidia.com/t/dgx-spark-performance/356651/52), un operador de GPT-OSS-120B MXFP4 TP=2 informa `Invalid thread config` al perfilar `lm_head`; atribuye el fallo a un shard de dimensión 100544 que no divide el tile 128. Tras añadir padding, dice que el servidor inició y pasó preguntas de coherencia a 2K/16K/100K. En los posts 64 y 67 informa aparte un hang de generación larga streaming con CUDA graphs (un rank al 100%, otro al 0%) mientras `--enforce-eager` funciona; más tarde, en el post 83, dice que arrancó tras cambiar a imagen PyTorch y quitar paquetes del sistema, sin A/B que conecte esos cambios con el hang. Fijar imagen/dependencias y revisar forma por shard frente al kernel elegido; probar arranque y generación stream/no-stream de dos nodos con logs por rank y control eager. El padding y eager solo son evidencia de ese stack. El log adjunto de illegal memory access del post 49 (39.2 KB) y los repos/patches no se inspeccionaron. Detalle de cierre y riesgos: `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_02.json`, ID literal `BB-GB10-MXFP4-TP2-STREAM-COMPAT-GATE`.

**`FORUM-00-QWEN36-DASHED-RELEASE-AND-SEMANTIC-GATE` — hilo 367561.** Las recetas de Qwen3.6-27B con DFlash cambian entre vLLM/imagen AEON 0.20–0.24, modelo PrismaSCOUT/AURA, número de draft tokens, contexto y harness. El autor reporta variación de calidad/throughput, alta presión de memoria y una falla de xgrammar que termina una petición en vLLM 0.24; otro propietario informa bucles de comandos con templates comunitarios a contexto ≥90K, mientras una plantilla distinta “se comporta mejor” sin comparación controlada ([367561, posts 32, 34, 46, 50, 62–64, 70](https://forums.developer.nvidia.com/t/whats-the-best-speed-we-can-get-with-qwen-3-6-27b-without-quantizing/367561)). Los puntajes y arreglos son relatos de operadores, sin digest completo, repetición independiente ni auditoría de imágenes, templates o repositorios. El gate existente debe fijar imagen/modelo/template/parser, profundidad DFlash, contexto, concurrencia y versión de vLLM; capturar excepciones de parser y comprobar finalización y resultado semántico con canario de herramientas, además de repetir con contextos largos antes de promover. No convertir la recomendación v0.22/DFlash ni cambiar template/depth en receta universal; conservar la última combinación admitida para rollback.


**BB-VLLM-V1-PREFIX-CACHE-LIFECYCLE-GATE-01** — [370309, posts 195–197, 211, 228–229, 239](https://forums.developer.nvidia.com/t/deepseek-v4-flash-official-fp8-running-across-2x-dgx-spark-tp-2-mtp-200k-ctx-recipe-numbers/370309/195) aporta síntomas distintos de lifecycle del prefix cache. Para vLLM V1, un operador describe RSS/cache que no decrece, linear RSS growth y pérdida progresiva de efectividad; atribuye el caso a una colisión en `BlockPool._maybe_evict_cached_block()` donde `reset_hash()` no se ejecuta tras `pop()` fallido, y enlaza PR #44237. Dos usuarios confirman el síntoma y reportan recuperación luego de parchear, sin versión exacta, digest ni auditoría independiente del PR. En otro setup de 4× Spark, la tasa de hit cayó de 35% a casi 0 con uso KV GPU reportado ~7%; el autor propuso priorizar bloques libres sin hash, pero no se verificó ni integró esa modificación. En 2× Spark, otro usuario reporta que alternar dos sesiones obliga a recomputar prefijos; sin restart nocturno, versión o trazas que identifiquen causa. Estos mecanismos quedan separados. Extender el canario existente con prompts repetidos y sesiones alternadas bajo carga sostenida, registrando hits/misses, evicciones, KV, RSS/cgroup, progreso y errores de hash; validar recuperación tras terminar solicitudes y controles cache-off/capacidad saturada. Revisar primero una versión oficial que contenga el fix; mantener allocator patches comunitarios desactivados hasta auditar su código y medir A/B, con digest previo disponible para rollback. Ninguna publicación confirma que el stack actual de Blackbox tenga esta falla. Adjuntos y PR no auditados.

La lectura directa de [372268, posts 73, 84, 97–98, 101, 112, 153, 161, 163, 269–280, 282–284](https://forums.developer.nvidia.com/t/deepseek-v4-flash-aiden-recipe-from-reddit-1m-token-session-operational-cuda-12-1-tailored-for-dgx-spark-gb10/372268/73) añade historial contradictorio en builds comunitarios del mismo stack: antes de PR #44237 se describen KV/cache que asciende hasta saturación, decodificación que cae a ~1 tok/s y un parche local propuesto para limpiar hashes obsoletos; con builds posteriores algunos operadores reportan evicción y RSS estables bajo presión, mientras otros reportan pausas, recomputación de prefijos o corrupción/gibberish al alternar sesiones y lanzar subagentes. El autor anuncia un fix asociado a PR #44237 y varios usuarios informan mejora, pero también hay regresiones/cambios entre production-v2, 2.9, 3.2 y 3.7 sin A/B idéntico ni digest común; un benchmark breve de tool-eval no cubre la vida del cache. Tratarlo como precedentes de prueba y validar el canario de lifecycle por build exacto, sesiones largas/concurrentes y contexto amplio. El cuerpo completo del hilo 372268 sigue pendiente de lectura y sus repositorios, imágenes, logs y adjuntos tampoco se auditaron; esta evidencia no cierra el gap.

El hilo de DSV4 Vision Exp añade un caso distinto: en vLLM 0.29-b12x con DSpark, el cuerpo de la petición terminaba 1–64 tokens después de un límite de bloque de 256 y no producía un prefijo reutilizable. El reporte inicial de 0.82–2.27% de retención quedó expresamente retractado: el harness terminaba temprano al confundir esas fallas de hit con evicción, por lo que esas tasas no miden retención. Luego el autor reportó un test de reenvío sin hits 0/22 antes y 0/44 después del fix de 27 líneas, una prueba offline de offsets con fallas 192/768→0/768, y un soak de 553 requests/18M prompt tokens con 91.3% de hits, 0 errores, preempciones ni reinicios; otro operador informó resultado de caché correcto a 500K ([381911, posts 290–313](https://forums.developer.nvidia.com/t/deepseek-v4-flash-vision-exp-is-released-as-open-weights/381911/302)). Evidencia posterior del autor identifica una brecha por final de prompt en el grupo EAGLE de 64 tokens de DSpark, retenido a la última frontera alcanzable. Es prueba comunitaria de una versión concreta, no confirmación de upstream ni de la instalación de BB. Añadir al canario offsets 0–255 respecto a bloque 256, reenvío de prefijos con variantes de cola, sesiones bajo presión y medición de TTFT/cache-hit por request; validar la versión oficial que lo resuelva y soak concurrente antes de adoptar un parche. Preservar digest y apagado del parche como rollback; las imágenes, repositorios enlazados y benchmark externo no se auditaron.


**BB-QWEN36-FP8-KV-SCALE-QUALITY-GATE** — [366822, post 213](https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822/213) compara Qwen3.6-35B-A3B FP8 con BF16 vs FP8 KV cache: el operador informa una tarea de paridad/extracción con 1/8 fallos usando BF16 KV y 4/8 con FP8 KV. Con FP8 KV, los logs que publicó indican que el checkpoint no trae q scaling factor, vLLM usa `k_scale`, aplica `1.0` a `fp8_e4m3` y advierte que q/prob scales sin calibrar pueden afectar precisión. Su tool-eval siguió marcando 100%, por lo que el resultado de herramienta no cubre esta tarea semántica. El comando contiene tanto `--no-ray` como `--distributed-executor-backend ray` mientras declara TP=2; la topología exacta es ambigua. No se inspeccionaron captura, outputs completos ni digest, así que no queda demostrada causalidad ni falla universal de FP8 KV. Agregar a la canaria del checkpoint/backend: log de escalas efectivas y defaults, comparación pareada BF16/FP8 KV con pesos, prompt, sampling, contexto y batch fijos, tarea de paridad además de tool-eval y criterio previo de error. No silenciar warnings ni aplicar globalmente scale 1.0; conservar BF16 y digest conocido para rollback hasta validar una ruta calibrada.

**BB-VLLM-EMPTY-TOOL-CALLS-STREAMING-COMPAT** — [372268, post 573](https://forums.developer.nvidia.com/t/deepseek-v4-flash-aiden-recipe-from-reddit-1m-token-session-operational-cuda-12-1-tailored-for-dgx-spark-gb10/372268/573) informa en vLLM 0.21.1 sobre 2× GB10 TP=2: una aplicación VS Code Insiders mostraba “Sorry, no response was returned” mientras funcionaban las llamadas de herramienta. Un proxy de logging vio que el servidor devolvía una respuesta completa (2135 caracteres, `finish_reason=stop`), pero su parser adjuntaba `tool_calls: []` a los 232 deltas de contenido cuando la solicitud contenía `tools`; la aplicación JS interpretó ese array truthy como rama de llamada a herramienta y descartó texto. El autor reporta una corrección en el parser base `deepseekv32_tool_parser.py` para omitir `tool_calls` si la lista está vacía, conservando campos cuando hay llamadas reales; afirma probar que no hay deltas vacíos, las llamadas reales siguen y el loop de agente funciona. Es un fix comunitario reportado, código/PR no auditado y aún sin confirmación de aplicación a la versión usada por Blackbox. Añadir al canario de API streaming un cliente que distingue campo ausente de lista vacía y prueba ambos casos con/sin herramientas, verificando texto final, finish reason y llamadas reales; comparar build exacto y rollback al digest previo. No inferir pérdida del servidor a partir del error del cliente ni cerrar con `/health` o HTTP 200 solamente. El resto del cuerpo del hilo 372268 sigue en revisión y adjuntos/repositorios quedan sin auditar.


**BB-QWEN36-SPEC-PREFIX-TOOLCALL-COMPAT-GATE** — [366822, posts 221–227](https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822/221) aporta una regresión de compatibilidad reportada: Qwen3.6-35B-A3B con vLLM `0.20.2` comparado con `0.19.2` tuvo peor tool-eval pese a throughput benchmark parecido. Luego el autor y otro usuario describen fallos de tool calls cuando speculative decode (MTP o DFlash) y prefix caching están activos a la vez; dicen que desactivar cualquiera recuperó su comportamiento normal, y otra respuesta dice quitar prefix caching devolvió los resultados en `0.20.x`. Son observaciones de operadores sin matriz factorial, logs ni causa confirmada; los gráficos de posts 221 y 224 siguen sin inspeccionar. Ampliar la prueba fijada por stack con matriz vLLM-version × speculative-on/off × prefix-cache-on/off y MTP/DFlash separados, midiendo resultados de herramientas en conversaciones repetidas y cache hits, además del throughput. Preservar la última imagen/configuración aceptada para rollback; no convertir la desactivación de cache ni la elección de versión en receta global.


**BB-QWEN36-INDUCTOR-CUDAGRAPH-AUTOTUNE-GATE** — [366822, post 236](https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822/236) presenta una causa plausible y un workaround comunitario para un fallo de startup/capture en Qwen3.6-35B-A3B int4-mixed: `torch._inductor.runtime.benchmarking.Benchmarker.benchmark_gpu` ejecutaría `torch.cuda.synchronize()` durante stream capture de CUDA Graph; AOT caches cargarían kernels compilados sin decisiones autotune, por lo que la primera llamada autotune ocurre dentro de capture. El mod monkeypatchea todas las clases Benchmarker del módulo para devolver `inf` durante captura (seleccionando la primera config) y envuelve todo con `except Exception: pass`. No se publicaron versión/digest completos ni reproducción independiente; screenshots/logs externos quedan sin auditar. Reproducir con cache AOT frío y caliente en el stack exacto; preferir fix upstream. Cualquier workaround temporal debe estar fijado a la API/versión validada, conservar excepciones no relacionadas visibles, probar captura on/off y comparar corrección/salida y recursos. El patch puede ocultar fallos y alterar autotune privado, así que no recomendarlo como arreglo general.


**BB-QWEN36-GDN-QUEUE-ASSERT-RECOVERY-GATE** — [366822, post(s) 252–254](https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822/252) reports an exact GB10/SM_12.1a Qwen3.6-35B-FP8, vLLM `0.19.1rc1.dev110+gb55d830ec.d20260408`, DFlash-8 setup with prefix caching, chunked prefill and FlashAttention. The owner observed a CUDA device assert in `fused_sigmoid_gating_delta_rule_update_kernel` after one scheduler tick jumped from Running=1/Waiting=3 to Waiting≥7; every request then returned HTTP 500 until container restart. A reply says chunked prefill has known DFlash issues. Removing that flag while changing to a newer cu130-nightly/FlashInfer stack removed this assert for the owner, but those changes were simultaneous and a separate memory-allocation drift then appeared. Cause remains unproven. Add queue-transition canary coverage for hybrid GDN/Mamba × chunked prefill × prefix cache × speculative decode, recording scheduler queues, per-rank errors, CUDA/process health, request completion and bounded recovery. Prefer an upstream-supported build; gate an exact failing combination instead of prescribing a universal flag. Logs/Nsight artifacts and linked package were not supplied/audited.


**BB-QWEN36-MTP-SM121-FLASHINFER-CRASH-SOAK** — [366822, posts 305–310](https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822/305) añade una firma de fallo fatal al gate MTP existente: un operador de GB10/SM121 reporta Qwen3.6-35B-A3B NVFP8 con driver 580.159.03, CUDA 13.0, vLLM 0.22.1rc1.dev22 y FlashInfer 0.6.11.post2 fallando en serving con MTP: Xid 13→43/EngineDead o `cudaErrorIllegalAddress` dentro del proceso. Con depth 3 informa varias caídas al día; con depth 2 una tras ~9 h; depth 1 llevaba solo ~1 h de observación. En post 308 el mismo grupo de discusión informa degradación de calidad de herramientas para MTP 1–4 sin resultados crudos. El issue vLLM #37754 enlazado no se verificó externamente; faltan logs, imagen exacta, control MTP-off y exposición comparable. Añadir esa tupla a la canaria exact-stack: registrar Xid/CUDA, EngineCore, proceso, requests, draft acceptance y salida semántica; probar off vs depths con carga idéntica y soak predeclarado que exceda las ~9 h observadas. Tratar depth 1 como candidato sin evidencia suficiente, no como fix. Quarantinar la tupla después de un error CUDA fatal y guardar evidencia fuera del host antes de recovery. Hallazgo literal: `BB-QWEN36-MTP-SM121-FLASHINFER-CRASH-SOAK`.


**BB-QWEN35-MAMBA-PREFIX-CACHE-SEMANTIC-GATE** — [365639, posts 315, 318–326, 433–434](https://forums.developer.nvidia.com/t/qwen3-5-122b-a10b-on-single-spark-up-to-51-tok-s-v2-1-patches-quick-start-benchmark/365639/315) aporta señales contradictorias sobre prefix caching en Qwen3.5 híbrido: un ensayo de vLLM 0.19.1 con modo Mamba `align` experimental cuenta cero hits en 14,744 tokens y TTFT/throughput ambiguos; operadores posteriores reportan hits en sesiones reales, incluyendo 57.8% sostenido en una secuencia OpenCode, pero sin control semántico pareado. No inferir cache correcta por porcentaje ni incompatibilidad universal por un benchmark sintético. Para el stack fijado, registrar modo/cache queries, tokens computados/cacheados, TTFT, block size y salida/herramientas; comparar cache off/on con prompts repetidos, prefijos compartidos, únicos y turnos reales. Exigir igualdad semántica con control cache-off y que contadores coincidan con menor trabajo de prefill, dentro de capacidad medida. El post315 también informa assert de startup cuando block_size 2112 superó max-num-batched-tokens 2048; no aumentar el límite sin medir headroom. Repos, capturas y logs externos unread. ID literal: `BB-QWEN35-MAMBA-PREFIX-CACHE-SEMANTIC-GATE`.

**`FORUM-00-QUANT-SPECULATIVE-SEMANTIC-CANARY` — hilo 360142.** Los autores reportan que una ruta Triton FP8 entrega salida garbage con 0% en su prueba matemática; en NVFP4+EAGLE3 describen cambios de 2–12 puntos de precisión al variar profundidad/plataforma; otro usuario ve loops de GLM al incluir sintaxis SQL/código; y más adelante una carga AutoRound produce `!!!`/pesos faltantes en una revisión nueva de vLLM hasta aplicar un mod o reconstruir. La matriz cambia modelo, formato, engine/kernel, versión, contexto, draft depth y harness; las mediciones no se comparan como una receta única. Revisé completos el start script del post 35 y `RESULTS.md` del post 39: el script fija un contenedor `vllm-next`, Modelo Qwen3-Coder-30B AutoRound W4A8, FP8 y ajustes de Marlin; la tabla reporta resultados para DGX Spark SM121 y RTX PRO 6000 SM120 con throughput/calidad, pero no incluye el harness determinista completo ni reproduce fallos/mediciones en BB. Los cinco posts públicos 2, 3, 5, 131 y 187 no aparecen en el stream capturado; los modelos/repositorios completos tampoco se auditaron. Fuente y copias auditadas: [360142](https://forums.developer.nvidia.com/t/fp4-on-dgx-spark-why-it-doesnt-scale-like-youd-expect/360142), `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/attachments-root/360142-post35-start_qwen3_w4a8.sh` y `360142-post39-RESULTS.md`. Para cada tupla exacta que BB admite, correr controles pareados de corrección matemática, salida válida, carga íntegra de pesos, finish reason, structured output y tool calls con speculative on/off, contextos fijados y modelo de referencia antes del benchmark de throughput. Registrar digest de imagen, pesos, backend real, harness y draft depth; cambiar una variable por ensayo y conservar rollback al último digest que pasó. ID literal: `FORUM-00-QUANT-SPECULATIVE-SEMANTIC-CANARY`.


**`BB-DSPARK-UNIFORM-BATCH-CONTEXT-CRASH-GATE`.** [372268, post 607](https://forums.developer.nvidia.com/t/deepseek-v4-flash-aiden-recipe-from-reddit-1m-token-session-operational-cuda-12-1-tailored-for-dgx-spark-gb10/372268/607) aporta un informe de caída del EngineCore en una imagen comunitaria production-3.8/vLLM 0.21: cuatro continuaciones de herramientas concurrentes terminaron con longitudes efectivas `[2, 144, 149, 145]` tras recortar tokens rechazados; el autor dice que la propuesta DSpark exige longitudes uniformes y lanza una excepción que devuelve 500 y apaga el servidor. El mismo autor informa que el workload funciona con vLLM 0.11 en production-3.7/3.75. La versión, causa, código fuente, logs y parche no se auditaron; el hilo 372268 sigue parcialmente leído. Para cada tupla fijada, probar solicitudes concurrentes de longitudes diversas y capturar longitudes efectivas, excepción, EngineCore/proceso, HTTP y recuperación; aislar o rechazar la tupla incompatible sin tumbar cargas sanas. Comparar versiones y DSpark off/on con mismo harness, salida y tool calls; conservar imagen conocida y rollback. No desactivar DSpark ni aplicar un patch del foro como default sin validar semántica, memoria y soak.


**Delta de fuentes 372268, cuerpo completo leído.** El post 286 describe fallos distintos en concurrente DSpark: propuesta que se detiene al entrar la segunda solicitud, ventana que se reinicia con contextos cacheados/chunked-prefill, y aperturas de tool call truncadas al cruzar rechazo de draft; son observaciones de un operador de clúster 4×Spark con B12X, sin parche/código adjunto auditado. El post 259 describe texto garbled tras alternar una sesión larga con un harness concurrente; el autor lo atribuye a contaminación de batches KV, pero otros usuarios no lo reproducen en los posts vecinos. En la rama actual del repositorio comunitario [tonyd2wild/DeepSeek-v4-Flash-Vision-Exp-DSpark](https://github.com/tonyd2wild/DeepSeek-v4-Flash-Vision-Exp-DSpark-1M-NVFP4-KV-2x-DGX-Spark), el README atribuye garble concurrente frío a draft greedy con MTP=5, captura CUDA graph no fijada y posible caché JIT compartida; propone draft probabilístico MTP=3, capture-size alineado con concurrencia, y caché JIT local por nodo, y reporta una prueba con cuatro primeras sesiones concurrentes por instancia en dos TP=2 independientes. Es una mitigación específica de ese overlay custom, con resultados del autor; no se transfiere a vLLM 0.21/production-3.8 ni a Blackbox sin pin de commit/image, auditoría del diff y A/B/soak con control concurrente y rollback. El mismo README documenta por separado fallos de illegal-memory-access con repetition_penalty en esa ruta; no se debe confundir ese fix con el problema de garble.

**`BB-DSPARK-REASONING-EFFORT-TOOL-SAFETY-01`.** [372268, posts 538, 607–608, 639](https://forums.developer.nvidia.com/t/deepseek-v4-flash-aiden-recipe-from-reddit-1m-token-session-operational-cuda-12-1-tailored-for-dgx-spark-gb10/372268/639) informa que production-3.7 convierte `high` en texto de plantilla de 5 tokens, mientras `max` produce 84; el autor compara con la plantilla del modelo: `high` 84 y `max` 97. En un A/B declarado de un solo cambio (2×GB10 TP=2, DSV4-0731, vLLM lineage 0.25.2, tool-eval-bench 2.1.0, 84 casos/seed42/temp0), `max` corregido queda 85 vs 86; 4 tareas de finalización mejoran, 7 empeoran y la defensa de prompt-injection cambia de pass a fail. Corrige el significado efectivo del ajuste, pero no acredita una mejora de calidad o seguridad. Fijar imagen, modelo y plantilla; comprobar `/tokenize` por cada nivel y medir finalización, tool calls, injection y latencia por corridas pareadas antes de cambiar defaults. Código, casos crudos y logs externos del foro no auditados; conservar rollback. El repositorio comunitario publicado luego mantiene este resultado como un A/B, no como prueba de calidad o seguridad general.

### Captura NCCL revisada — 350367

Fuente: https://forums.developer.nvidia.com/t/350367. La captura de `all_gather_perf` usa dos GB10, 1 GiB, nccl-tests 2.17.6 y NCCL 22803: algbw 1.56/1.55 GB/s, busbw 0.78 GB/s, wrong=0. Orden MPI declara IPs link-local y NIC; no prueba transporte efectivo de NCCL ni cable averiado. El canario debe conservar comando, collective, payload, algbw/busbw, transporte efectivo, NIC y corrección; la respuesta con guía oficial carece de resultado del autor.

## Estado de publicación de esta investigación

Propuesta abierta. Los comandos de cierre describen el verificador y evidencia requeridos; esta rama publica investigación y fichas, sin implementación ni resultados de ejecución de los mecanismos propuestos.

### FORUM-00-VLLM-CUDAGRAPH-AUTOROUND-MEMORY-GATE — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "FORUM-00-VLLM-CUDAGRAPH-AUTOROUND-MEMORY-GATE",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01",
    "title": "Gatear CUDA Graph y margen UMA para vLLM AutoRound en GB10",
    "source": "https://forums.developer.nvidia.com/t/assertion-violation-while-serving-intel-qwen3-5-122b-a10b-int4-autoround-solo-via-community-build/362754",
    "related_ids": [
      "362754"
    ],
    "gap": "En la combinación Intel/Qwen3.5-122B-A10B-int4-AutoRound, imagen comunitaria spark-vllm-docker/vLLM tf5 0.17.0rc1.dev150+gb7332b058.d20260308 y gpu_memory_utilization=0.7, el propietario documentó fallo durante captura de CUDA Graph (NONE/PIECEWISE). Subir a 0.85 permitió iniciar según su reporte, con fiabilidad aún en prueba.",
    "proposal": "Agregar esa combinación como caso explícito de compatibilidad: smoke de carga fría y captura de grafo, luego solicitudes y soak; registrar build, flags, memoria UMA pico/disponible y salud de SSH/escritorio. No promover 0.85 como default: dimensionar el presupuesto con margen del host y comparar opciones de grafo/configuración en el stack exacto.",
    "confidence": "media para el fallo y arranque reportados por el propietario; baja para estabilidad de 0.85, pues no aportó resultado de soak.",
    "risks": "Aumentar utilization puede quitar margen UMA al sistema y convertir un fallo de inicialización en bloqueo bajo carga; builds comunitarios cambian rápido y el repositorio no se auditó.",
    "closure": "Reproducir o marcar no reproducible en el build exacto; pasar carga fría, captura de grafo, peticiones representativas y soak sin perder SSH/escritorio, con telemetría de UMA y rollback del parámetro. Mantener matriz versionada de resultados."
  }
]
```

### FORUM-00-HYBRID-SPEC-PREFILL-DEGRADATION — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "FORUM-00-HYBRID-SPEC-PREFILL-DEGRADATION",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01",
    "title": "Detectar regresión silenciosa de prefill tras workload mixto en vLLM híbrido",
    "source": "https://forums.developer.nvidia.com/t/glm-5-3-flash-on-2-gb10-speculative-decoding-makes-long-prefill-ttft-alternate-2x-after-a-mixed-workload-plus-3-knobs-that-measurably-helped/382099",
    "related_ids": [
      "382099"
    ],
    "gap": "En ASUS Ascent GX10, vLLM fork entrpi/glm-5.3-flash-exl3-2x-spark:v2-glmnext, kernel 6.17.0-1031, driver 580.173.02 y CX7 FW 28.45.4028, propietario reporta que prefill de 24,364 tokens alterna ~14.6s/~19–27s después de workload mixto con speculative decode; decode permanece en ±3%, varias métricas revisadas no cambian y restart de contenedor limpia efecto. Root cause no probado.",
    "proposal": "Incluir workload mixto seguido de probe prefill repetido en estabilidad para stacks híbridos con speculative decoding; guardar fingerprint/base commit del fork y verificar exporter/labels antes de usar métricas upstream. Correlacionar tiempo de paso, utilización, potencia y progreso funcional. Restart solo como control reversible, no autorizar auto-restart general.",
    "confidence": "Media para patrón reportado con series; baja para causa interna, no hay reproducción independiente ni auditoría del fork.",
    "risks": "Restart pierde servicio/cache y puede ocultar trigger; nombres/semántica de métricas upstream pueden no aplicar a fork; automatizar por TTFT puede matar solicitudes largas legítimas.",
    "closure": "Reproducir en fork/tag/build exactos con secuencia preregistrada y controles MTP/DFlash/eager; validar instrumentación efectiva; repetir antes/después de restart y distinguir variación natural. Mantener servicio interactivo y documentar no reproducibilidad si falla el caso."
  }
]
```

### FORUM-00-CTX-FINISH-REASON-CAPACITY-GATE — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "FORUM-00-CTX-FINISH-REASON-CAPACITY-GATE",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01",
    "title": "Distinguir truncamiento por contexto de fallo de servicio",
    "source": "https://forums.developer.nvidia.com/t/fitting-qwen3-8-flash-next-180b-onto-one-dgx-spark-44-tok-s-at-four-bits/382117",
    "related_ids": [
      "382117"
    ],
    "gap": "Una receta comunitaria Qwen3.8-Flash-Next servía con límite de 8,192 tokens; solicitud larga acababa sin error visible en contenedor/UI. Usuario confirmó API finish_reason=length y usage total_tokens=8192. El maintainer dice que subir CTX a 65,536 pasó su propio benchmark; no constituye soporte universal.",
    "proposal": "Añadir al smoke de serving una solicitud mayor que el límite configurado y comprobar finish_reason/usage, CTX real y línea de capacidad KV/concurrencia del arranque. Exponer a diagnóstico el motivo de terminación para distinguir cap normal de respuesta truncada, crash o hang. Registrar runtime/config exactos; ampliar contexto solo en caso que el KV budget lo admita.",
    "confidence": "Alta para el límite 8192 reportado y confirmado por API; media para orientación del maintainer; los datos de CTX 64k corresponden a un release/build concreto.",
    "risks": "CTX mayor aumenta KV comprometido y reduce concurrencia/margen UMA; UI puede omitir finish_reason; pruebas con prompts largos consumen recursos.",
    "closure": "Reproducir límite con API y cliente UI, verificar finish_reason=length, elevar CTX en sandbox con headroom medido y verificar capacidad concurrente/soak según runtime; rollback a límite conocido."
  }
]
```

### FORUM-00-AUTOROUND-RESUME-CHECKPOINT-INTEGRITY — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "FORUM-00-AUTOROUND-RESUME-CHECKPOINT-INTEGRITY",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01",
    "title": "Validar integridad/calidad tras reanudar cuantización AutoRound",
    "source": "https://forums.developer.nvidia.com/t/kat-coder-v2-5-dev-versus-ornith-1-0-35b-spark-autoround/379611",
    "related_ids": [
      "379611"
    ],
    "gap": "Un usuario de Spark-AutoRound/BigBang-v1-int4-AutoRound informó una ejecución interrumpida y reanudada desde checkpoint 21/40; las capas cuantizadas después del resume muestran métricas cosine/PSNR peores y uloss mayor que un intento fresh posterior. La persona atribuye posible corrupción a resume pero no aporta A/B controlado; no hay verificación del autor de herramienta.",
    "proposal": "Para jobs largos de cuantización en el GB10, registrar versión/config/digest del checkpoint y guardar métricas por capa. Ante discontinuidad, mantener checkpoint original y una copia; validar el artefacto reanudado frente a fresh/control con un umbral preregistrado de calidad antes de publicar/servir. No recomendar borrar el cache o rehacer desde cero sin preservar evidencia/datos.",
    "confidence": "media-baja: comparación por capas reportada por propietario, causa no aislada, no se auditó herramienta/repo.",
    "risks": "Métricas de cuantización pueden variar legítimamente por modelo/datos/config; reejecución completa cuesta recursos; checkpoints grandes requieren espacio. Borrar checkpoints destruye diagnóstico y rollback.",
    "closure": "Reproducir en misma versión/modelo con copia preservada, comparar resume vs fresh bajo mismos datos/semilla/config por capa y salida final; demostrar regresión por encima del ruido o atribuirla a diferencias controladas. Verificar que rollback conserva checkpoint fuente."
  }
]
```

### FORUM-00-SGLANG-SM121-EAGLE-CONCURRENCY-GATE — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "FORUM-00-SGLANG-SM121-EAGLE-CONCURRENCY-GATE",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01",
    "title": "Gate SGLang SM121 image and EAGLE/Triton concurrency on GB10",
    "source": "https://forums.developer.nvidia.com/t/running-mistral-small-4-119b-moe-on-dgx-spark-with-sglang-full-setup-benchmarks/364763",
    "related_ids": [
      "364763"
    ],
    "gap": "En marzo de 2026 un autor de setup GB10 informa que lmsysorg/sglang:mistral-small-4 falla con ptxas sobre sm_121a y que PR #20708 fix llegó a nightly CUDA 13; reporta otro crash Triton JIT “operation not permitted” al probar concurrencia 32 con EAGLE, mientras 16 le funcionó. Las mitigaciones se plantean como opciones, sin ablation que identifique cuál resuelve el crash.",
    "proposal": "Mantener una matriz versionada de compatibilidad SM121a/SGLang/CUDA image por digest y verificar smoke de carga antes de actualizar; para el stack y modelo de este reporte conservar cap de concurrencia validado y ejecutar escalado progresivo con soak, gates de salud/SSH y rollback. Tratar spec v2, graphs off y cambio de backend como experimentos A/B aislados; recoger ptxas/Triton error y reproducibilidad antes de elevar límite.",
    "confidence": "Media para errores y resultados reportados con logs/comandos; baja para causa/eficacia de mitigaciones y cobertura más allá del exacto SGLang/Mistral/GB10 stack.",
    "risks": "Nightly/cu13 cambia de contenido; elevar concurrencia puede recrear crash y hacer caer servicio; alternar varios toggles impide atribuir arreglo; reducir concurrencia cuesta rendimiento.",
    "closure": "En mismo OEM/driver/kernel y digest de imagen, probar concurrencia escalonada con EAGLE/Triton, luego cada toggle individual, repetir 32 con carga/soak; validar no crash, salida correcta, SSH/TTY, memoria y rollback a límite/imágen anterior."
  }
]
```

### FORUM-00-NCCL-ROCE-HCA-AND-PEER-LISTENER-GATE — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "FORUM-00-NCCL-ROCE-HCA-AND-PEER-LISTENER-GATE",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01",
    "title": "Verificar HCA RoCE twin y listener antes de diagnosticar ancho de banda NCCL",
    "source": "https://forums.developer.nvidia.com/t/why-is-my-nccl-broken/359593",
    "related_ids": [
      "359593"
    ],
    "gap": "En dos Spark/GB10 CX7, propietario obtuvo NCCL all-gather bus bandwidth de ~16.23 GB/s y decía seguir el playbook; experto identificó que no exportaba NCCL_IB_HCA. El resultado final de prueba de 16 GiB subió a 24.05 GB/s con HCA RoCE twin especificados, aunque tests/tamaños/versiones no son exactamente idénticos. ib_write_bw falló hasta ejecutar el listener en el peer; luego el propietario confirmó éxito.",
    "proposal": "Ampliar el gate NCCL existente para mapear interfaz netdev↔HCA↔puerto físico y validar port Active/LinkUp, NCCL_IB_HCA con interfaces RoCE correctas, NCCL_SOCKET_IFNAME para control y un test RDMA con listener presente en el destino. Distinguir resultados nccl-tests/RDMA/TCP y tamaños/versiones; no inferir fallo por mensajes X11/SSH si test termina con validation OK.",
    "confidence": "Media-alta para requisitos del HCA twin y servidor del benchmark según troubleshooting del experto y confirmación del autor; media para delta de ancho de banda, porque cambió la configuración y no se mantuvo idéntico test-size/library.",
    "risks": "Asignar mal HCA puede desviar tráfico a interfaz incorrecta o romper link/aislamiento de red; cambiar netplan puede cortar conectividad. Las configuraciones son específicas de topología/puertos.",
    "closure": "En dos nodos aislados verificar primero puerto/dispositivo/mapping, misma interfaz/red y NCCL variables; correr ib_write_bw con servidor en receptor, luego nccl-tests con mismas bibliotecas/tamaños; comparar error counters y ruta efectiva; registrar rollback de Netplan antes de tocar IP."
  }
]
```

### FORUM-00-SGLANG-IDLE-SCHEDULER-CPU-CAPTURE — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "FORUM-00-SGLANG-IDLE-SCHEDULER-CPU-CAPTURE",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01",
    "title": "Observe and gate SGLang idle CPU busy-spin on always-on GB10",
    "source": "https://forums.developer.nvidia.com/t/qwen3-8-27b-nvfp4-on-single-dual-dgx-spark-sglang-dflash2-fully-openai-compatible/380732",
    "related_ids": [
      "380732"
    ],
    "gap": "Recipe owner reports SGLang scheduler uses ~97% CPU while idle without --sleep-on-idle, citing MiaAI repo issue #4. The linked issue/repo and exact version behavior were not independently reviewed.",
    "proposal": "Add SGLang as a distinct backend case in existing idle-process/CPU admission: sample scheduler CPU after ready+idle, verify interactive request/SSH remains available, then test version-supported --sleep-on-idle and remeasure. Track upstream fix/status; avoid assuming a vLLM/Ray fix applies.",
    "confidence": "medium: explicit author report, one exact community recipe; upstream issue not inspected.",
    "risks": "Sleep mode could add latency or miss wakeup behavior; disabling may consume CPU and reduce headroom.",
    "closure": "Confirm exact backend and version; compare idle CPU and first-request latency with flag off/on over soak; verify server health and no lost requests; pin or rollback image."
  }
]
```

### FORUM-00-TP2-NCCL-WARMUP-MTU-HCA-DIAG — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "FORUM-00-TP2-NCCL-WARMUP-MTU-HCA-DIAG",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01",
    "title": "Differentiate TP=2 NCCL warmup hang from bad MTU or HCA selection",
    "source": "https://forums.developer.nvidia.com/t/qwen3-8-27b-nvfp4-on-single-dual-dgx-spark-sglang-dflash2-fully-openai-compatible/380732",
    "related_ids": [
      "380732"
    ],
    "gap": "In a two-Spark SGLang DFlash2 profile, author reports NCCL warmup hang with GPU ~96% util/~14W when fabric MTU is not 9000 on both nodes or NCCL_IB_HCA uses wrong device names. Both are alternative proposed causes; thread does not report a controlled ablation to distinguish them.",
    "proposal": "Extend preflight to check MTU on both peer ports and map actual RoCE devices from ibv_devices/ibdev2netdev before TP=2 launch; record GPU power/util and NCCL logs to distinguish initialization wait from active compute. Use tested values for each exact node/port and preserve current netplan.",
    "confidence": "medium-low: explicit troubleshooting statement in a tested user guide; no independent reproduction or clean single-variable comparison.",
    "risks": "Changing MTU/routes can interrupt management networking; incorrect HCA selection may silently fallback or route wrong.",
    "closure": "In isolated two-node canary, verify MTU/HCA, repeat warmup at controlled settings and inspect NCCL transport; preserve SSH and rollback config; demonstrate successful collective and model request."
  }
]
```

### FORUM-00-NEMOTRON-NVFP4-XID13-SOAK-GATE — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "FORUM-00-NEMOTRON-NVFP4-XID13-SOAK-GATE",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01",
    "title": "Gate Nemotron NVFP4/vLLM stacks on illegal-instruction canary and soak",
    "source": "https://forums.developer.nvidia.com/t/dgx-spark-sm121-software-support-is-severely-lacking-official-roadmap-needed/357663",
    "related_ids": [
      "357663"
    ],
    "gap": "The thread contains owner-reported recurrent vLLM EngineCore crashes on Nemotron 3 Nano NVFP4 after >20 minutes of GPQA, with CUDA illegal-instruction and Xid 13 evidence; an NVIDIA contributor reports reproducing a crash. PyTorch/Triton/nightly candidates were suggested later, but owner validation is absent and an attached FlashInfer log archive is unread.",
    "proposal": "Record exact model revision, image digest, PyTorch/vLLM/Triton/FlashInfer versions, MoE backend and flags. Before admission, run model-load plus fixed correctness requests, then a declared-duration GPQA or representative workload soak; capture EngineCore exit, CUDA illegal instruction, Xid and FlashInfer autotune logs. Quarantine the affected exact candidate on any Xid/illegal instruction and retain a known-good image/backend for rollback. Evaluate NVIDIA’s later candidate only as a versioned canary, not a blanket upgrade.",
    "confidence": "medium: multiple owner reports and an NVIDIA maintainer says they also reproduced a crash; precise component cause is not isolated, attachment logs unread, later fix has no owner retest.",
    "risks": "A short canary can miss a delayed failure; switching backend or lowering performance does not prove correctness. A false Xid attribution could prompt unrelated driver changes.",
    "closure": "Reproduce on the exact reported stack or establish non-reproduction with declared versions; compare candidate and control in fixed correctness requests and a soak longer than the reported failure interval; require zero Xid/illegal instruction, no EngineCore death, preserved host/SSH, and captured FlashInfer logs; document rollback digest."
  },
  {
    "id": "FORUM-00-NEMOTRON-NVFP4-XID13-SOAK-GATE",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01",
    "source_threads": [
      "359074"
    ],
    "source_posts": [
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/14",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/25",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/26",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/28",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/33",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/35",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/50",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/51",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/54",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/56",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/61",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/62",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/71",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/75",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/78",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/80",
      "https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074/83"
    ],
    "gap": "Additional to 357663, owners in this thread report Nemotron 3 Nano NVFP4 on single DGX Spark with vLLM+FlashInfer MoE eventually crashing with CUDA illegal instruction and Xid 13. A FlashInfer commit plus vLLM 0.16 supports 512 concurrent requests for over 3 hours but then an owner reports Xid 13 after 4 hours; earlier failure intervals reported 20–60 minutes. A Marlin recipe is claimed to work in a different report, but there is no matched control/long soak; CUTLASS starts without exceptions but reportedly lacks speed advantage, and a nightly change broke Marlin. Exact artifacts and FlashInfer archives are not audited.",
    "proposal": "Extend the existing exact-stack canary with backend-separated matched runs for FlashInfer NVFP4, Marlin NVFP4 and CUTLASS NVFP4, recording image digest, vLLM/PyTorch/FlashInfer commits, model revision, first-request correctness, EngineCore exit, CUDA illegal instructions and Xid. Soak longer than the longest reported failure before candidate admission and quarantine the affected digest on Xid; treat eager/Marlin as stack-specific canaries, not universal fixes.",
    "confidence": "High for multiple owner-reported crash/Xid events including one NVIDIA contributor report in related source; medium for backend-specific attribution because versions/configs vary and crashes persist across different revisions.",
    "risks": [
      "A 3-hour no-crash window can miss a 4-hour failure; predeclare soak duration beyond observed interval.",
      "Backend change can alter accuracy/performance and does not guarantee stability on another model or OEM.",
      "Unreviewed crash archive or external PR may contain stronger evidence that changes attribution."
    ],
    "closure": "Use exact supported image and model with backend-specific matched controls, fixed output correctness requests and repeated soak longer than reported 4 hours; capture EngineCore exit/Xid/illegal instructions and off-host logs. Verify no crash in candidate and unchanged baseline and prove rollback. Do not accept a PR, runtime pin, or switch to Marlin as closure without this canary.",
    "related_ids": [
      "357663"
    ]
  }
]
```

### FORUM-00-CUTLASS-FLASHINFER-DEPENDENCY-LOCK-SMOKE — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "FORUM-00-CUTLASS-FLASHINFER-DEPENDENCY-LOCK-SMOKE",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01",
    "title": "Fail closed on CUDA JIT dependency conflict and verify installed runtime",
    "source": "https://forums.developer.nvidia.com/t/minimax-m3-w4a16-gptq-2xgb10-deployment-36-t-s-fp8-nvfp4-kvarn-eagle-3/375595",
    "related_ids": [
      "375595"
    ],
    "gap": "On 2×GB10, an operator reports CuTe-DSL JIT failures with an all-4.5.2 CUTLASS DSL trio and says 4.5.3 resolves the OpView ABI symptom. A separate fresh deployment reproduces a related JIT failure traced to a floating FlashInfer main build requiring CUTLASS DSL 4.7.0 while its pinned vLLM commit requires 4.5.2; solver conflict is reported, and FlashInfer 0.6.14 plus the exact pinned vLLM stack starts and serves. An earlier Docker image build also succeeded while omitting the vLLM wheel, detected only by `import vllm` failing. These are author-reported reproductions, and their suggested versions differ.",
    "proposal": "At build time, pin the complete CUDA-sensitive package set by exact version and wheel hash/commit; evaluate the dependency graph in one resolver transaction and fail on incompatible requirements or forced/partial installs. Before publishing or admitting a container, check installed package versions and run `python -c \"import torch,vllm; ...\"` plus a small SM121 CUDA/JIT kernel canary and first model request. Save the previous image digest and package manifest so rollback restores a known-good artifact. Treat reported 4.5.3 or FlashInfer 0.6.14 combinations as test candidates for their exact vLLM/build, not universal fixes.",
    "confidence": "medium: independent operators provide detailed failure evidence; one reports a package ABI error and another logs an explicit resolver conflict plus successful controlled pinned build, but external wheels/repositories and patch claims were not independently audited.",
    "risks": "Pins can freeze a known regression or miss security/fixes; latest tags can silently change dependencies. Smoke can miss workload-specific kernels, so it supplements a stack-specific representative soak.",
    "closure": "For the affected exact stack, reproduce dependency/JIT or establish non-reproduction under recorded versions; prove resolver fails closed on conflicting pins, verify all installed package versions/hashes and import vLLM inside the built image, run SM121 kernel + model correctness canary and declared soak; prove rollback uses saved digest/manifest."
  }
]
```

### DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01 — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01",
    "title": "Classify low GPU power only against a supported runtime baseline",
    "source_threads": [
      "356426"
    ],
    "failure": "A thread initially reports GPU stuck at ~5W/0% under workload, then its author says the cause was old Driver 550.54.15/CUDA12.4; after GPU-burn installed Driver 580.95.05/CUDA13.0, GPU reached 96%/28W and power scaled normally. The mlx5 PCIe 27W message also appears on healthy idle Spark, so it is a false standalone indicator for GPU cap.",
    "current_coverage": "Runtime compatibility diagnostics capture active driver/CUDA stack; CX7 diagnostics capture PCIe slot power warning.",
    "gap_or_complement": "Before labeling platform power fault, record effective host/container driver+CUDA and run a known-good supported GPU load; keep mlx5 27W warning separate from GPU-side utilization/power/clock measurements.",
    "evidence_level": "Medium: forum author reports fix but diagnostic zip shared by DM was inaccessible.",
    "risks": [
      "Initial setup was called stock before final post disclosed old driver/CUDA, showing provenance can be incomplete.",
      "A single workload may fail for a model/kernel issue rather than power delivery."
    ],
    "closure": "Reproduce on exact supported host/container stack; show healthy idle can emit mlx5 27W, stale runtime is rejected as unsupported, and supported GPU-burn plus inference correlate load/utilization/power correctly.",
    "backlog_card": "tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"
  }
]
```

### DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01 — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "DELTA-FORUM-RAY-TORCH-GRAPH-HANG-01",
    "title": "Gate exact Ray/vLLM/Torch tensor-parallel stack and detect rank-progress stalls",
    "source_threads": [
      "358755"
    ],
    "failure": "Two-Spark owner reports vLLM TP=2 lost one node after first prompt while peer GPU stayed at 100%; `--enforce-eager` changed symptom and owner later reported fixing their setup by using torch 2.9.1 instead of 2.10.0.",
    "current_coverage": "Runtime compatibility card captures supported versions; host hang capture does not necessarily distinguish dead distributed rank from GPU-busy/no-progress.",
    "gap_or_complement": "Track exact container digest/Torch/CUDA/vLLM/Ray/NCCL and TP/PP config. Validate known-good combinations; export per-rank request and collective progress/heartbeat alongside GPU busy/power. Bound request timeout and retain logs before process kill. Keep eager mode as A/B diagnostic only.",
    "evidence_level": "Medium for operator-reported loss and version change; low-to-medium for causality (single setup, no complete logs or repeated controlled A/B).",
    "risks": [
      "Torch version may be confounded with build, CUDA kernels, or stack changes.",
      "A generic GPU-100% alarm can misclassify productive prefill as a wedge.",
      "Eager mode may lower performance without fixing underlying stack incompatibility."
    ],
    "closure": "On two named GB10s, exact supported container/kernel/driver/Torch/CUDA/Ray/NCCL, compare 2.9.1 and target version under same model/prompt; capture rank and collective progress; verify detector catches no-progress while allowing long prefill, then verify bounded stop/recovery and rollback.",
    "backlog_card": "tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"
  }
]
```

### DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01 — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "DELTA-FORUM-DSV41-NFS-STOP-TAG-PIN-01",
    "title": "Protect NFS worker mounts and pin container digest during stack cleanup",
    "source_threads": [
      "382725"
    ],
    "failure": "A 4× Spark operator migrating DeepSeek stack reports `stop.sh` wildcard-deletes all dsv41-* containers including the NFS exporter; workers with persistent NFS mounts then hang in health/doctor on next serve. Floating `dev-dsv41` tag also moved to a different base than the pinned digest. Other recipe reports include 12 failed boot attempts after topology changes, with no verified root cause.",
    "current_coverage": "Runtime compatibility captures host/container versions; rescue runbook covers recovery after unavailable nodes, but cleanup script behavior and NFS dependency ordering are not gated.",
    "gap_or_complement": "Use explicit container allowlist and dependency graph; preserve exporter while worker mounts exist, check mount/export health before stopping and before relaunch. Pin immutable image digest and record recipe commit. Apply network/share changes in a canary after config backup; validate exact TP topology.",
    "evidence_level": "Medium for owner-reported NFS hang and floating-tag drift; low for causal hardware impact and failed-boot attribution (forum report without diagnostic logs).",
    "risks": [
      "A broad cleanup can remove a shared service and strand remote workers on hard NFS mounts.",
      "Reconfiguring network or shares cluster-wide can cause loss of remote access and requires rollback path.",
      "Digest pinning can preserve vulnerable/outdated images unless updates are reviewed."
    ],
    "closure": "On disposable 4-node test, reproduce hard-mounted worker + exporter, run stop/upgrade/rollback and prove exporter stays reachable or workers unmount cleanly; fail on missing exporter before launching model, pin and report exact image digest, exercise config restore. No production NFS mount required.",
    "backlog_card": "tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"
  }
]
```

### DELTA-FORUM-QWEN-LONG-AGENT-STOP-01 — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "DELTA-FORUM-QWEN-LONG-AGENT-STOP-01",
    "title": "Detect and preserve premature end-of-turn in long GB10 agent sessions",
    "source_threads": [
      "381228"
    ],
    "failure": "A single owner reports 15 confirmed premature `finish_reason=stop` turns without tool calls across 24 long Hermes sessions and 2,176 tool turns over 12 days; one session had 11. Replays passed 4/4. Same symptom reportedly appeared with NVIDIA NVFP4; a different INT4 checkpoint had no observed stops in limited ongoing use.",
    "current_coverage": "Runtime compatibility gates model/image/runtime, while hang capture targets no-progress host/runtime failures. It does not evidence long-horizon model turn termination with zero tool calls while an agent task remains open.",
    "gap_or_complement": "Add long-agent integration/soak tests per exact checkpoint/runtime, recording request/turn IDs, prompt-size bucket, finish_reason, tool-call count, elapsed context and stack digests. Surface premature stop as a reviewable recoverable incident; require operator continuation and avoid automatic replay of potentially mutating tools.",
    "evidence_level": "Medium for owner-measured symptom counts, low for generalization and attribution; the linked issue and repro attachments were not audited and 4/4 fresh replays did not reproduce.",
    "risks": [
      "Could flag legitimate final answers or lead to duplicate external tool actions if auto-replayed.",
      "Long soak is expensive and model/benchmark revisions alter behavior.",
      "Session content may be sensitive; default to bounded IDs and metadata instead of raw prompts."
    ],
    "closure": "Run preregistered long-horizon tool-agent soak against exact NVIDIA and candidate checkpoints with repeated trials; include healthy final-answer controls and deliberate tool-required turns, verify no silent task halt escapes the receipt, no duplicate mutating calls occur, and preserve manual resume plus rollback to known checkpoint.",
    "backlog_card": "tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"
  }
]
```

### DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01 — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "DELTA-FORUM-NCCL-TP-ORCHESTRATION-CORRECTION-01",
    "title": "Validate CX7 and per-rank environment before attributing TP startup hangs to NCCL",
    "source_threads": [
      "366127"
    ],
    "failure": "A dual-Spark owner first attributed TP2 freezes in TRT-LLM/vLLM/SGLang to NCCL. Reimage from unsupported Ubuntu 25.10 to DGX OS 24.04.4 enabled correctly distributed MPI ranks and independent NCCL all_reduce test at 17.3 GB/s; a later TP2 deployment passed with the recipe launcher on both Ray and --no-ray, while bare launches still hung. A separate TRT-LLM CUDA graph capture hang remained.",
    "current_coverage": "Runtime compatibility records image and NCCL versions; it does not explicitly distinguish unsupported-host/rank placement/configuration errors from an actual collective or graph-capture bug.",
    "gap_or_complement": "Before filing or responding to NCCL incident, capture OS support state, per-rank hostname/device, CX7 interface/address/subnet and effective container env; execute cross-node nccl-tests separately; compare supported launcher and manual reproduction. Preserve separate phase for collective, weight load, autotune and CUDA graph capture.",
    "evidence_level": "Medium for detailed owner-reported reimage, microtest and working launcher comparison; low for independent generalization because linked community scripts/image were not audited.",
    "risks": [
      "Incorrect generalized NCCL tuning can degrade or isolate cluster traffic.",
      "Wrongly attributing a launcher issue to NCCL can lead to driver or firmware changes with broader blast radius.",
      "Changing subnets/interfaces can strand nodes without a maintenance rollback plan."
    ],
    "closure": "On isolated dual GB10 using supported DGX OS, reproduce/verify placement and NCCL microtest, compare recipe launcher and manual launch with per-rank environment receipts, prove healthy TP path and distinguish an intentionally failing CUDA graph stage. Roll back to recorded IP/interface settings.",
    "backlog_card": "tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"
  }
]
```

### DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01 — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01",
    "title": "Gate OTA, kernel, driver and OEM firmware as effective GB10 tuple",
    "source_threads": [
      "359550"
    ],
    "failure": "During DGX OS 7.4 rollout, posts report OTA/kernel drift and an unsupported 590.48.01/CUDA13.1 combo; one user later reported ~5.5 GiB free of 121 GiB and recovered after downgrade to 580.126.09. Other post says UEFI memory carveout reduction 4→2GiB was planned for OEM adoption in OTA2. Individual memory-leak attribution is unverified.",
    "current_coverage": "Runtime preflight captures active image/driver and DGX OS compatibility; kernel/OEM firmware rollout stage and measured unified-memory baseline can still drift independently.",
    "gap_or_complement": "Record DGX release/OTA commit, active uname, driver/CUDA, OEM model, firmware versions and free/available memory from host; gate unsupported tuple per OEM release notes and stop if baseline materially changes after update. Treat carveout changes as UEFI evidence, not EC inference.",
    "evidence_level": "Medium for rollout mismatch; low for driver590 memory-leak causality and reported rollback remediation, both owner evidence without inspected logs.",
    "risks": [
      "Manual proposed packages or partner firmware can leave an unsupported, unrecoverable boot tuple.",
      "A memory baseline taken at different services/workloads may falsely signal leak.",
      "Partner OEM updates can lag Founder Edition release."
    ],
    "closure": "In an OEM-supported canary, record before/after tuple and MemAvailable/PSI, boot each supported OTA stage, verify model load and long soak, confirm supported rollback path and firmware effective version before enabling broad rollout.",
    "backlog_card": "tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"
  }
]
```

### DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01 — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "DELTA-FORUM-OPENCLAW-VLLM-REQUEST-CONTRACT-01",
    "title": "Preflight the served model ID and effective generation budget for GB10 agent clients",
    "source_threads": [
      "360299"
    ],
    "failure": "A Spark owner’s OpenClaw→vLLM GPT-OSS-120B request failed 404 from model ID mismatch until served-model alias and client ID aligned; a subsequent 400 set max_tokens to -17474 when config declared 200K context. Thread replies cite 131072 as GPT-OSS context maximum and advise against a static maxTokens=8192; user reports working 200 after adjustments.",
    "current_coverage": "Runtime compatibility preflight checks host/image/kernel/backend compatibility, but its request canary does not verify application model alias, effective model-specific context bound or calculated positive output budget.",
    "gap_or_complement": "Before admitting client workload, query `/v1/models`, compare configured model ID, checkpoint-declared context limit, requested context and max_tokens calculation; run a bounded positive completion and tool-call canary with metadata-only receipt.",
    "evidence_level": "Medium for reported 404/400 and owner-confirmed 200 after configuration correction; stack/config file not independently audited.",
    "risks": [
      "Model context limits are version/checkpoint-specific; a universal cap can unnecessarily reduce supported work.",
      "A probing request must be bounded and avoid mutating tool calls.",
      "Logging request bodies would expose sensitive prompts; capture status and sanitized metadata."
    ],
    "closure": "Test exact model/runtime/client tuple with aligned ID, negative mismatched ID, overlimit context, nonpositive token budget, and successful bounded generation/tool-call; receipt must link served model metadata to client config without storing prompt text.",
    "backlog_card": "tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"
  }
]
```

### DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01 — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "DELTA-FORUM-VLLM-RAY-GB10-RESOURCE-FIX-01",
    "title": "Keep Ray GB10 GPU-resource compatibility as a versioned regression fixture",
    "source_threads": [
      "355126"
    ],
    "failure": "In a Dec 2025 report, vLLM 25.11/Ray lacked generic `GPU` resource on GB10 while a reference recipe was cited; thread clarifies the author ran an NVIDIA container rather than the community image. Later forum update says NVIDIA playbook fix was verified in vLLM26.01. Earlier TRT-LLM NVFP4 missing SM121 kernel is a separate image/version report.",
    "current_coverage": "Runtime preflight covers GPU architecture and backend compatibility, but Ray resource placement needs a live cluster test and the old issue must not be mistaken for current regression.",
    "gap_or_complement": "For chosen image digest/version, verify Ray reports GPU on each node, placement matches topology and a minimal multi-node request succeeds; keep version 25.11 negative test as regression fixture only, and verify post-fix image separately.",
    "evidence_level": "Medium for dated reporter command/config and later post saying NVIDIA verified fix in 26.01; no linked upstream diff or test artifacts were audited.",
    "risks": [
      "Treating the stale 25.11 issue as current may lead to unnecessary third-party image changes.",
      "Assuming every 26.01+ image includes the fix can silently admit broken tags or OEM variants.",
      "SM121 kernel support is model/backend/image specific."
    ],
    "closure": "Reproduce old error under recorded 25.11 stack if available; assert exact corrected 26.01 image resolves resources/placement and serves TP canary, with controls for wrong image digest and missing GPU resource. Preserve prior image for rollback.",
    "backlog_card": "tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"
  }
]
```

### DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01 — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "DELTA-FORUM-CUTLASS-SM121-ISA-GATE-01",
    "title": "Gate CUTLASS CuTe kernel by actual SM121 MMA capability",
    "source_threads": [
      "359598"
    ],
    "failure": "CuTe CUTLASS maintainers say tcgen05 and associated blockscaled FP4 ops are SM100/SM110 paths and absent on SM12x; GB10 FP4 must use supported SM12x MMA pipeline. A user proposal to remap SM121 to SM100 would bypass guard but miscompile or emit invalid code. NVIDIA says NVFP4 performance work is underway in CUTLASS/FlashInfer/vLLM, with no release target in this thread.",
    "current_coverage": "Runtime card checks compiled arch manifests and finite-output canaries; this adds explicit invalid tcgen05 path and forbids fake arch override.",
    "gap_or_complement": "Before enabling third-party FP4 kernels, inspect target arch/instruction requirements and actual loaded backend; route through supported SM121 MMA path; run finite logits/reference comparison and sustained request canary.",
    "evidence_level": "High for architecture limitation as maintainer response and official NVIDIA announcement in-thread; no proof of a finished SM121 performance implementation.",
    "risks": [
      "Fake SM100 arch may generate unsupported instructions or wrong arithmetic.",
      "Alternative MMA path may have slower performance; correctness takes priority and throughput requires measurement.",
      "A generic `supports_fp4` boolean does not prove this kernel path exists."
    ],
    "closure": "On GB10 SM121, run positive supported MMA FP4 build and negative tcgen05 build; verify negative is rejected at preflight, positive logits finite and match reference tolerances over representative shapes, then batch/soak with image digest and backend recorded. No `CUTE_DSL_ARCH` override.",
    "backlog_card": "tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"
  }
]
```

### DELTA-FORUM-NEMOTRON-SM121-PREBUILT-KERNEL-01 — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "DELTA-FORUM-NEMOTRON-SM121-PREBUILT-KERNEL-01",
    "title": "Gate Nemotron kernels by exact SM121 ops and first real request",
    "source_threads": [
      "354771"
    ],
    "failure": "On GB10 SM121, SGLang :spark failed parsing NemotronHConfig; newer image loaded BF16 then failed RMSNorm on first inference and FP8 failed scaled_fp8_quant because compiled sgl_kernel ops lacked SM121 code. Host ptxas override did not add those binary kernels. A local llama.cpp Nemotron support build worked; later main merged support and a user confirmed latest rebuild worked.",
    "current_coverage": "Runtime compatibility can check architecture/manifest and smoke readiness but exact per-op execution under target architecture and response integrity must be verified at first inference.",
    "gap_or_complement": "Gate exact model/backend/image/build and ops RMSNorm/FP8 quant kernels for SM121; perform load and bounded first request, inspect finite output/reference. Keep `:spark` vs `:latest` image digests and commit hashes.",
    "evidence_level": "Medium/high for detailed owner logs and later main rebuild confirmation; no independent validation of tags/branches and later NVIDIA playbook in this thread.",
    "risks": [
      "Model load or HTTP-ready can mask missing kernels until first request.",
      "FP8 server may return nonsense despite process startup.",
      "Using an external branch may introduce unreviewed code or lack reproducibility."
    ],
    "closure": "Repeat positive first-request and FP8 correctness tests for exact current image and model; negative-control stale :spark image must fail fast with clear compatibility reason; preserve chosen image/build rollback and verify service recovery.",
    "backlog_card": "tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"
  }
]
```

### DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01 — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "DELTA-FORUM-DCP4-DECODE-STARVATION-FAIR-SCHEDULER-01",
    "status": "registered_to_existing",
    "source": "https://forums.developer.nvidia.com/t/376831/10",
    "evidence": "Eight-GB10 GLM-5.2 TP8/DCP4 operator reports simultaneous prefills starve active decode to 0.0–0.2 tok/s until prefill completion. Proposed patch at local-inference-lab/vllm commit a663653d8cf3a66ee3c0060aea8c2fd28e3f1362 dynamically limits aggregate prefill with active decode and rotates long-prefill requests. Forum author reports 3 new tests, 7 regression tests, ruff, and 4 CLI checks passing; hardware run with 1 continuous decode+4 ~8K prefills reports max stall 1.64s, pressure decode 2.74 tok/s and 4/4 prefills complete. Patch/repo not audited or run here.",
    "current_coverage": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01 already includes runtime readiness, context/concurrency admission, and long-run behavior. This adds decode-service fairness under simultaneous DCP4 prefill.",
    "gap_or_delta": "An HTTP-ready model and aggregate throughput can conceal a nearly stalled active decode stream while new prefill requests complete. Close check should measure max decode stall and completion under concurrent prefill, not throughput alone.",
    "proposal": "On an exact DCP4 image/revision, compare baseline against the exact scheduler patch with one long-lived decode and four bounded prefill prompts, record stall distribution, TTFT, decoded output, completion, throughput and memory; preserve config rollback via the disable flag.",
    "confidence": "medium for issue/signature and reported patch outcome, low-to-medium for reproducibility because artifacts are community-authored and unaudited.",
    "risk": "A stricter prefill budget can lower prefill throughput; patch may be incompatible with later vLLM/B12X scheduler code.",
    "closure": "Reproduce under declared pinned vLLM/B12X/FlashInfer/NCCL stack, demonstrate valid completion of all requests, decode stall budget, acceptable throughput, no regression tests failing, and rollback restoring baseline.",
    "backlog_card": "tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"
  }
]
```

### BB-MULTINODE-SEMANTIC-CANARY-BEFORE-ACCEPTANCE — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "BB-MULTINODE-SEMANTIC-CANARY-BEFORE-ACCEPTANCE",
    "source_threads": [
      "365379"
    ],
    "source_posts": [
      "https://forums.developer.nvidia.com/t/connect-two-sparks-question/365379/5",
      "https://forums.developer.nvidia.com/t/connect-two-sparks-question/365379/6",
      "https://forums.developer.nvidia.com/t/connect-two-sparks-question/365379/7",
      "https://forums.developer.nvidia.com/t/connect-two-sparks-question/365379/8",
      "https://forums.developer.nvidia.com/t/connect-two-sparks-question/365379/9",
      "https://forums.developer.nvidia.com/t/connect-two-sparks-question/365379/10"
    ],
    "failure": "En un cluster comunitario de dos GB10 el autor reportó generación corrupta/en bucle con un modelo denso, pese a lograr lanzar SGLang TP0/TP1; otro modelo Qwen3.5-35B corría. Capturas muestran scheduler usando ~93.5 GiB por host y el log TP0 avanzando a 27K tokens; el texto no acredita que esa salida sea semánticamente correcta. El hilo comenzó con subnet duplicado en interfaces CX-7 y mods con hunks fallidos, que sí detuvieron los contenedores. Un maintainer explica que `--gpu-mem` de la receta reserva también KV capacity aunque el modelo sea pequeño. Stack reportado: driver 580.142, CUDA 13.1; imagen/runtime exacto no queda fijado.",
    "current_coverage": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01 valida salida real, además de startup. Este caso añade aceptación de cluster multi-host: correcto networking y procesos activos no prueban que tensor-parallel esté produciendo texto válido.",
    "gap_or_complement": "Antes de marcar un deployment multi-host como usable, ejecutar una petición canary pequeña con respuesta de contenido predeterminado y validable, guardar prompt/expected invariant, salida y logs de cada TP rank; registrar modelo/checkpoint, imagen digest, backend, GPUs, driver/CUDA, receta y `--gpu-mem`. Repetir sobre single-host/TP control con la misma imagen/checkpoint y con stack/mod sin parche. Tratar fallos de patch hunk como incompatibilidad bloqueante del mod, conservar `.rej`/versión base y rollback del workload. No atribuir corrupción a memoria reservada, red o SGLang hasta que los controles separen esos factores.",
    "confidence": "Media para la salida corrupta reportada en un modelo denso y para los hunks de parche fallidos; baja para la causa. El thread no presenta salida completa reproducible, versión exacta del modelo pequeño, receta/image digest ni comparación controlada.",
    "risks": [
      "Reducir `--gpu-mem` puede evitar capacidad KV necesaria para contexto/concurrencia y no corrige necesariamente salida corrupta.",
      "Reaplicar mods comunitarios sobre versiones distintas puede cambiar silenciosamente componentes y dejar parches parciales; el launcher sí informó detener los contenedores.",
      "El hallazgo procede de un cluster comunitario con equipo Gigabyte Autom además del DGX Spark; no generalizar a stack OEM único."
    ],
    "closure": "Reproducir sobre dos nodos con stack exacto y canary semántico, primero con receta sin mods y luego con cada mod aplicado por separado; capture logs completos de ambos TP ranks, checkpoint/config resuelto y memoria/PSI. Ejecutar mismo modelo/config en single-node y con control negativo de canary. Demostrar que un hunk rechazado deja deployment no aceptado y limpio/rollback ejecutable. Cerrar causa solo tras aislamiento A/B que elimine/reproduzca salida corrupta; el soak y throughput por sí solos no valen como éxito.",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"
  }
]
```

### BB-DGPP-CONTEXT-POOL-OUTPUT-RESERVE — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "BB-DGPP-CONTEXT-POOL-OUTPUT-RESERVE",
    "source_threads": [
      "383406"
    ],
    "source_posts": [
      "https://forums.developer.nvidia.com/t/383406/94"
    ],
    "failure": "A DGPP master repeatedly exited during a large-context C2 API request with 1–2 additional small agents active; other 4-session overnight downtime has unknown cause. Author reports a pool around 262K but no guaranteed 32K completion after prompt/context and multi-agent allocation. A 295-second cold prefill for a large request later behaved differently from a 5-second hot-prefix case with healthy progress; a deadline update improved an owner trial but no crash retest or independent validation exists.",
    "current_coverage": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01 and FEATURE-1358-CGROUP-05 cover service success and host/process separation. Add request-level resource admission for aggregate concurrent prompts/agent contexts and guaranteed output reserve; separate slow progressing prefill from dead engine and healthy HTTP from a completed valid response.",
    "gap_or_complement": "Before accepting API work, compute available context-pool and concurrent request/agent budget using actual model/runtime limits; reserve declared output tokens for every admitted call and reject/queue work that exceeds it. Track per-request token counts, context occupancy, cancellation/deadline, stage progress, process/cgroup state and health of each tool/agent. A 262K advertised pool is a ceiling, not a completed-answer guarantee; do not hard-code a universal 600s deadline. Preserve one bounded cold-prefill and hot-prefix control; treat healthy progress as distinct from stall.",
    "confidence": "Medium for author-reported shutdown and resource accounting concerns; low on cause and fix because external repository/logs were not audited and later fix was not retested against shutdown.",
    "risks": [
      "Raising timeouts can strand GPU/UMA capacity if the engine stopped progressing; short timeouts can cancel legitimate cold prefill.",
      "Concurrency/agent fanout can exhaust shared context and UMA even when each request appears individually admissible.",
      "A process and HTTP health probe can remain up after request output is incomplete."
    ],
    "closure": "Pin model/checkpoint, engine image, prompt/context length, number and size of agents, concurrency and exact pool config. Run cold-prefix and hot-prefix tests with progress timeline, reserve-output checks, process/cgroup/UMA status and correct semantic response; include a negative request that exceeds budget and must be queued/rejected. Reproduce any shutdown and show bounded containment/recovery without killing a progressing prefill. Report the exact window and attempts; do not certify from a max token budget alone.",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"
  }
]
```

### BB-KV-QUANT-BACKEND-UMA-ADMISSION-GATE — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "BB-KV-QUANT-BACKEND-UMA-ADMISSION-GATE",
    "source_threads": [
      "375421"
    ],
    "source_posts": [
      "https://forums.developer.nvidia.com/t/serving-qwen3-5-397b-at-1m-tokens-on-2-dgx-spark-minimax-m3-is-next/375421/1",
      "https://forums.developer.nvidia.com/t/serving-qwen3-5-397b-at-1m-tokens-on-2-dgx-spark-minimax-m3-is-next/375421/2",
      "https://forums.developer.nvidia.com/t/serving-qwen3-5-397b-at-1m-tokens-on-2-dgx-spark-minimax-m3-is-next/375421/4"
    ],
    "failure": "An operator reports that applying open vLLM PR #46812 KVarN on unified-memory DGX Spark hosts caused memory-related errors and required an additional self-authored patch. Exact errors, patch, driver/runtime image digest and reproduction logs are absent. The operator posts a Qwen3.5-397B AutoRound command on 2×GB10 with vLLM 0.24.0, `--gpu-memory-utilization 0.91`, `--max-model-len 1010000`, `--max-num-seqs 10`, KV KVarN backend; the in-thread visible benchmark evidence includes depths up to 900K with prefill slowdown but does not establish a completed valid 1M run.",
    "current_coverage": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01 requires exact backend/runtime/model compatibility and real output checks. Add experimental KV cache backend on unified memory to that same matrix; an upstream PR or memory-saving estimate is not GB10 compatibility evidence.",
    "gap_or_complement": "Do not include the external patch or select KVarN as default. First verify PR #46812 landed in the exact pinned vLLM release and its supported architectures. On an identified OEM, use a small model/corpus canary with FP16 KV control and incremental context/concurrency A/B; capture resolved backend, GPU/system UMA/PSI, allocation failures, output validity, process health, cold compile peak, and rollback. Test requested contexts independently (32K, 524K, 900K, 1M) and distinguish successfully allocated KV capacity from a completed request with output reserved.",
    "confidence": "Medium that the author observed memory errors after KVarN on UMA; low on failure mechanism, patch efficacy, model quality and 1M capability because error details/code are absent and posted benchmark results do not reach 1M completion.",
    "risks": [
      "Unofficial patch may change allocator/layout behavior and cause silent corruption or unsupported backend selection.",
      "High KV reservation and context length can leave inadequate UMA for cold compile/model/runtime scratch even if pool capacity reports fit.",
      "Memory compression claims from PR benchmarks use different hardware/models and do not prove GB10 stability or semantic quality."
    ],
    "closure": "For the release containing official KVarN support (if present), reproduce on exact GB10/OEM/runtime with clean unpatched and FP16-KV controls, exact checkpoint, bounded cold and warm requests, and all allocation/health/output telemetry. Keep every claimed context under test; require valid complete semantic output and host recovery after negative over-budget control. No closure from a theoretical cache token capacity or a patch making the error disappear.",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"
  }
]
```

### BB-RDMA-RING-TOPOLOGY-STARTUP-CANARY — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "BB-RDMA-RING-TOPOLOGY-STARTUP-CANARY",
    "source_threads": [
      "377435"
    ],
    "source_posts": [
      "https://forums.developer.nvidia.com/t/6-node-dgx-spark-ring-topology-nccl-fails-on-non-adjacent-node-pairs-routed-rdma/377435/1",
      "https://forums.developer.nvidia.com/t/6-node-dgx-spark-ring-topology-nccl-fails-on-non-adjacent-node-pairs-routed-rdma/377435/4",
      "https://forums.developer.nvidia.com/t/6-node-dgx-spark-ring-topology-nccl-fails-on-non-adjacent-node-pairs-routed-rdma/377435/6",
      "https://forums.developer.nvidia.com/t/6-node-dgx-spark-ring-topology-nccl-fails-on-non-adjacent-node-pairs-routed-rdma/377435/8",
      "https://forums.developer.nvidia.com/t/6-node-dgx-spark-ring-topology-nccl-fails-on-non-adjacent-node-pairs-routed-rdma/377435/9"
    ],
    "failure": "Six-node DGX Spark switchless L3/OSPF ring: direct-neighbor RDMA and TCP bootstrap work, but raw `ibv_write_bw` to nonadjacent peers and NCCL world-group QP setup fail at `ibv_modify_qp` INIT→RTR timeout. The author then reports a 6-node PP workload functioning over `NCCL_IB_DISABLE=1` TCP fallback. A later patched NCCL with `NCCL_IB_MERGE_NICS=0` and `NCCL_IB_SUBNET_AWARE_ROUTING=1` connected all QPs and served traffic, but reported only ~7% aggregate throughput gain. External patched code and repo not audited; author hypothesizes lack of GPUDirect RDMA but has no vendor confirmation.",
    "current_coverage": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01 already gates exact distributed runtime and validates output/startup; earlier cases cover Ray interface selection and multi-node model execution. This adds topology reachability at raw verbs + actual PP rank mapping, before allocating long-running inference, and documents the tested socket fallback as a candidate rather than a general performance choice.",
    "gap_or_complement": "For any >3-node switchless topology, validate actual L2 peer reachability / network layout against supported product guidance first. Capture each physical HCA/port, neighbor/rank mapping, GID/subnet and NCCL resolved transport. Gate at raw verbs test for the peer pairs that the workload requires; then do short exact PP semantic canary with per-rank logs and recovery. A green Ray/Gloo TCP bootstrap does not prove RDMA QPs can connect; rank swizzle and `NCCL_IB_MERGE_NICS=0` alone do not solve unconnected HCA peers. Prefer supported switch or use TCP/socket fallback only after measuring throughput/latency on the actual workload. Do not patch NCCL/LD_PRELOAD, bridge a live ring, or assume GPUDirect feature availability without vendor-supported route and rollback.",
    "confidence": "High for the author-posted raw verbs failure and the sequential owner-reported TCP/RDMA tests; medium-low for transferability and cause because topology is custom, logs/repo were not independently audited, and GDR is only a hypothesis.",
    "risks": [
      "L2 bridging a ring can create broadcast loops/storms unless topology and loop-prevention are engineered and tested.",
      "Custom NCCL flags may not exist or have same semantics in stock NCCL; envs can be silently ignored or fused interface mappings wrong.",
      "Switchless ring with TCP fallback can reduce performance materially for a PP workload; numbers in thread are owner measurements and do not transfer.",
      "Wrong GID/HCA/rank mapping may cause remote startup failure after model allocation, wasting time and memory."
    ],
    "closure": "On exact OEM NICs/firmware, kernel, NCCL/vLLM image digest and documented topology, test each needed peer with native raw verbs, then the actual topology/rank assignment with short PP canary and output validation. Capture per-rank mapping, selected HCA/GID/transport, startup result, response correctness, throughput and host health; include negative disconnected peer control and the supported socket path. Verify rollback to a known supported topology. Any patched NCCL candidate requires code review/vendor support plus same A/B/soak before admission.",
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01"
  }
]
```

### DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01 — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01",
    "title": "Admitir correcciones exactas de tokenizer y parches con control semántico",
    "source_threads": [
      "380244",
      "362824"
    ],
    "merge_into": "FEATURE-FORUM-GB10-RUNTIME-COMPAT-01",
    "evidence_level": "Texto íntegro capturado; resultado reportado por propietarios; PRs y binarios sin auditar",
    "failure": "Truncación silenciosa de texto a2048 y fallo visual; parche MXFP4 carga pero posteriores pruebas muestran corrupción Harmony y regresión funcional.",
    "gap_or_complement": "Guardar hashes/revisión y cambio mínimo; centinelas al principio/fin, imagen y herramientas, pruebas largas de salida; cada candidato conserva imagen conocida para rollback.",
    "risks": [
      "Cambiar tokenizer completo altera contrato fuera del campo corregido",
      "TPS/HTTP200 ocultan corrupción semántica"
    ],
    "closure": "Fixture reproduce truncación y verifica preservación con corrección; soak del parche reporta errores y duraciones; restauración exacta probada.",
    "backlog_card": "tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md"
  }
]
```
