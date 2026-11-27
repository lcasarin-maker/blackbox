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

## Trabajo en la ATOM

Preflight de runtime en la ATOM (arquitectura, digest OCI, driver contra `NVIDIA_REQUIRE_CUDA`, GPU sm_121) mas un canario de `finish_reason`/usage/logits finitos sobre `nemotron-local` (extender `tools/canario_motor.py`) y rollback al digest de v0.27.1. Los casos multinodo, Ray/NCCL y de otros modelos no son de esta maquina.

## Referencia pública

Hilos de los que salió esta ficha (URL pública):

- https://forums.developer.nvidia.com/t/353639
- https://forums.developer.nvidia.com/t/348537
- https://forums.developer.nvidia.com/t/349199
- https://forums.developer.nvidia.com/t/379168
- https://forums.developer.nvidia.com/t/375361
- https://forums.developer.nvidia.com/t/351413
- https://forums.developer.nvidia.com/t/356417
- https://forums.developer.nvidia.com/t/358610
- https://forums.developer.nvidia.com/t/native-sm121-fp8-kernels-any-progress/363514
- https://forums.developer.nvidia.com/t/repeated-xid-31-mmu-faults-during-amp-enabled-yolov8s-training-on-dgx-spark-gb10/378529
- https://forums.developer.nvidia.com/t/trouble-to-find-cuda-at-dgx/
- https://forums.developer.nvidia.com/t/incompatibility-of-torchaudio-in-ngc-pytorch-container-25-12-on-dgx-spark-blackwell-gb10/
- https://forums.developer.nvidia.com/t/help-finding-issue-in-eugr-spark-vllm-docker-vs-vllm-vllm-openai-gemma4-cu130-running-gemma-4-26b-a4b-it/370805
- https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-specialized.html
- https://docs.nvidia.com/cuda/blackwell-compatibility-guide/index.html
- https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/compute-capabilities.html
- https://forums.developer.nvidia.com/t/dgx-spark-int8-awq-w8a16-completely-broken-on-dgx-spark-gb10-blackwell-anyone-got-this-working/
- https://forums.developer.nvidia.com/t/tensorrt-llm-1-3-0rc5/
- https://forums.developer.nvidia.com/t/oudated-playbook-https-build-nvidia-com-spark-comfyui-video-gen-workflow/
- https://forums.developer.nvidia.com/t/driver-590-is-not-support-dgx-spark-yet/
- https://forums.developer.nvidia.com/t/full-glm-4-7-355b-nvfp4-at-64k-context-on-2x-dgx-spark-gb10-working-recipe-vllm-tp-2/375690
- https://forums.developer.nvidia.com/t/flashinfer-sparse-mla-mbarrier-livelock-on-gb10-root-cause-evidence-and-validated-workaround/377334
- https://github.com/marksunner/glm52-dgx-spark-deadlock-evidence
- https://github.com/marksunner/glm52-dgx-spark-deadlock-evidence/blob/main/rfc-48720-update-20260717.md
- https://forums.developer.nvidia.com/t/384621
- https://forums.developer.nvidia.com/t/356426
- https://forums.developer.nvidia.com/t/358755
- https://forums.developer.nvidia.com/t/382725/138
- https://forums.developer.nvidia.com/t/381228/311
- https://forums.developer.nvidia.com/t/qwen3-5-tool-calling-finally-fixed-possibly/366451
- https://forums.developer.nvidia.com/t/laguna-s-2-1-config-benchmarks/377663
- https://forums.developer.nvidia.com/t/connect-two-sparks-question/365379/5
- https://forums.developer.nvidia.com/t/366127
- https://forums.developer.nvidia.com/t/359550
- https://forums.developer.nvidia.com/t/383406/94
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-1-048-576-context-on-2x-dgx-spark-custom-sparkrun-recipe/
- https://forums.developer.nvidia.com/t/serving-qwen3-5-397b-at-1m-tokens-on-2-dgx-spark-minimax-m3-is-next/375421
- https://forums.developer.nvidia.com/t/360299
- https://forums.developer.nvidia.com/t/6-node-dgx-spark-ring-topology-nccl-fails-on-non-adjacent-node-pairs-routed-rdma/377435/1
- https://forums.developer.nvidia.com/t/355126/36
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-0731-dspark-1m-nvfp4-kv-2x-dgx-spark/378824/1
- https://forums.developer.nvidia.com/t/qwen-3-8-27b-dflash2/380617/10
- https://forums.developer.nvidia.com/t/380244
- https://forums.developer.nvidia.com/t/362824
- https://forums.developer.nvidia.com/t/assertion-violation-while-serving-intel-qwen3-5-122b-a10b-int4-autoround-solo-via-community-build/362754
- https://forums.developer.nvidia.com/t/glm-5-3-flash-on-2-gb10-speculative-decoding-makes-long-prefill-ttft-alternate-2x-after-a-mixed-workload-plus-3-knobs-that-measurably-helped/382099
- https://forums.developer.nvidia.com/t/fitting-qwen3-8-flash-next-180b-onto-one-dgx-spark-44-tok-s-at-four-bits/382117
- https://forums.developer.nvidia.com/t/kat-coder-v2-5-dev-versus-ornith-1-0-35b-spark-autoround/379611
- https://forums.developer.nvidia.com/t/running-mistral-small-4-119b-moe-on-dgx-spark-with-sglang-full-setup-benchmarks/364763
- https://forums.developer.nvidia.com/t/why-is-my-nccl-broken/359593
- https://forums.developer.nvidia.com/t/qwen3-8-27b-nvfp4-on-single-dual-dgx-spark-sglang-dflash2-fully-openai-compatible/380732
- https://forums.developer.nvidia.com/t/359598/18
- https://forums.developer.nvidia.com/t/359598/40
- https://forums.developer.nvidia.com/t/354771
- https://forums.developer.nvidia.com/t/dgx-spark-sm121-software-support-is-severely-lacking-official-roadmap-needed/357663
- https://forums.developer.nvidia.com/t/nemotron-3-nano-30b-a3b-nvfp4-ultra-efficient-nvfp4-precision-version-of-nemotron-3-nano/359074
- https://forums.developer.nvidia.com/t/psa-state-of-fp4-nvfp4-support-for-dgx-spark-in-vllm/353069
- https://forums.developer.nvidia.com/t/setting-up-vllm-sglang-or-tensorrt-on-two-dgx-sparks/353338
- https://forums.developer.nvidia.com/t/minimax-m3-w4a16-gptq-2xgb10-deployment-36-t-s-fp8-nvfp4-kvarn-eagle-3/375595
- https://forums.developer.nvidia.com/t/tensorrt-edge-llm/368290
- https://forums.developer.nvidia.com/t/help-running-nvfp4-model-on-2x-dgx-spark-with-vllm-ray-multi-node/353723
- https://forums.developer.nvidia.com/t/glm-5-3-flash-320b-total-parameters-18b-active/
- https://forums.developer.nvidia.com/t/dgx-spark-qwen3-next-80b-proven-performance-but-missing-clear-path-to-nim-tensorrt-llm-web-uis/357820
- https://forums.developer.nvidia.com/t/376831/10
- https://forums.developer.nvidia.com/t/375690/1
- https://forums.developer.nvidia.com/t/377334/1
- https://forums.developer.nvidia.com/t/353010/1
- https://forums.developer.nvidia.com/t/359518/1
- https://forums.developer.nvidia.com/t/353527/1
- https://forums.developer.nvidia.com/t/384789/10
- https://forums.developer.nvidia.com/t/364098/1
- https://forums.developer.nvidia.com/t/375308/5
- https://forums.developer.nvidia.com/t/slow-performance-for-redhatai-qwen3-coder-next-nvfp4/363129/6
- https://forums.developer.nvidia.com/t/382754/1
- https://forums.developer.nvidia.com/t/373274/1
- https://forums.developer.nvidia.com/t/365513/4
- https://forums.developer.nvidia.com/t/373314/1
- https://forums.developer.nvidia.com/t/358421/1
- https://forums.developer.nvidia.com/t/363493/1
- https://forums.developer.nvidia.com/t/cant-inference-gpt-oss-120b-eagle3-on-gb10/354783/1
- https://forums.developer.nvidia.com/t/bug-tensorrt-llm-1-2-0rc8-trtllmgenfusedmoe-does-not-support-sm120-error-on-dgx-spark-with-gpt-oss-120b-eagle3/357849/1
- https://forums.developer.nvidia.com/t/setting-up-vllm-sglang-or-tensorrt-on-two-dgx-sparks/353338/6
- https://forums.developer.nvidia.com/t/tensorrt-edge-llm/368290/1
- https://forums.developer.nvidia.com/t/help-running-nvfp4-model-on-2x-dgx-spark-with-vllm-ray-multi-node/353723/1
- https://forums.developer.nvidia.com/t/dgx-spark-qwen3-next-80b-proven-performance-but-missing-clear-path-to-nim-tensorrt-llm-web-uis/357820/4
- https://forums.developer.nvidia.com/t/nsys-profile-not-showing-any-gpu-data/352250/1
- https://forums.developer.nvidia.com/t/qwen3-next-awq-4bit-vs-fp8-vs-nvfp4-on-single-spark/361300/1
- https://forums.developer.nvidia.com/t/353639/1
- https://forums.developer.nvidia.com/t/379624/1
- https://forums.developer.nvidia.com/t/365002/1
- https://forums.developer.nvidia.com/t/introducing-prismascout-prismaquant-v2/368933/31
- https://forums.developer.nvidia.com/t/364731/1
- https://forums.developer.nvidia.com/t/381428/1
- https://forums.developer.nvidia.com/t/373401/1
- https://forums.developer.nvidia.com/t/359555/30
- https://forums.developer.nvidia.com/t/mimo-v2-5-dflash-speculative-decoding-on-a-2x-dgx-spark-pair-22-67-tok-s-depending-on-workload/375607/64
- https://forums.developer.nvidia.com/t/366266
- https://forums.developer.nvidia.com/t/collective-operations-timeout-on-dual-spark-during-distributed-training/366147
- https://forums.developer.nvidia.com/t/nccl-test-bandwidth-is-only-3gb-s-between-2-dgx-spark-using-qsfp-cable/366373
- https://forums.developer.nvidia.com/t/new-ngc-vllm-container-image-vllm-26-01-py3/359213
- https://forums.developer.nvidia.com/t/vllm-100-cpu-usage-when-idle-again/362964
- https://forums.developer.nvidia.com/t/effective-pytorch-and-cuda/348230
- https://forums.developer.nvidia.com/t/running-parakeet-speech-to-text-on-spark/356353
- https://forums.developer.nvidia.com/t/gb10-qsfp56-ports-speed-connecting-multiple-gb10-with-mikrotik-crs804-ddq/364093
- https://forums.developer.nvidia.com/t/365296/15
- https://forums.developer.nvidia.com/t/dflash-llm-for-dgx-spark-too-good-to-be-true/366445
- https://forums.developer.nvidia.com/t/356118/17
- https://forums.developer.nvidia.com/t/378784
- https://forums.developer.nvidia.com/t/368726
- https://forums.developer.nvidia.com/t/368097
- https://forums.developer.nvidia.com/t/375416
- https://forums.developer.nvidia.com/t/379722
- https://forums.developer.nvidia.com/t/377598/12
- https://forums.developer.nvidia.com/t/358382/18
- https://forums.developer.nvidia.com/t/380248/27
- https://forums.developer.nvidia.com/t/382939/178
- https://forums.developer.nvidia.com/t/382939/181
- https://forums.developer.nvidia.com/t/370834/15
- https://forums.developer.nvidia.com/t/introducing-prismaquant/367085/21
- https://forums.developer.nvidia.com/t/362721/24
- https://forums.developer.nvidia.com/t/375945/9
- https://forums.developer.nvidia.com/t/concern-about-the-usefulness-of-a-single-dgx-spark/377281/93
- https://forums.developer.nvidia.com/t/366828/80
- https://forums.developer.nvidia.com/t/377396
- https://forums.developer.nvidia.com/t/373669
- https://forums.developer.nvidia.com/t/step-3-7-flash-is-supported-in-community-docker-on-dgx-spark/371652/49
- https://forums.developer.nvidia.com/t/359571/38
- https://forums.developer.nvidia.com/t/360319/50
- https://forums.developer.nvidia.com/t/run-vllm-in-spark/348862
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-dspark-on-2x-dgx-spark-gb10-big-single-stream-speed-boost-60-67-tok-s-1m-context-now-with-concurrency/374846/97
- https://forums.developer.nvidia.com/t/361967/162
- https://forums.developer.nvidia.com/t/361639/173
- https://forums.developer.nvidia.com/t/deepseek-v4-released/367696/55
- https://forums.developer.nvidia.com/t/we-unlocked-nvfp4-on-the-dgx-spark-20-faster-than-awq/361163
- https://forums.developer.nvidia.com/t/introducing-prismaquant/367085/71
- https://forums.developer.nvidia.com/t/why-turboquant-saves-dgx-twice/364736
- https://forums.developer.nvidia.com/t/minimax-m2-7-nfvp4-recipe-benchmarks/366324
- https://forums.developer.nvidia.com/t/qwen3-8-flash-fp8-dual-sparks/381440/40
- https://forums.developer.nvidia.com/t/qwen3-8-flash-fp8-dual-sparks/381440/69
- https://forums.developer.nvidia.com/t/qwen3-6-27b-is-out/367503/292-295
- https://forums.developer.nvidia.com/t/glm-5-2-on-a-4-gb10-cluster-22-tok-s-decode-256k-ctx-recipe/374125/157
- https://forums.developer.nvidia.com/t/glm-5-2-on-a-4-gb10-cluster-22-tok-s-decode-256k-ctx-recipe/374125/202
- https://forums.developer.nvidia.com/t/gemma-4-models-which-vllm-version-any-prs-spotted/365490/114
- https://forums.developer.nvidia.com/t/dgx-spark-performance/356651/52
- https://forums.developer.nvidia.com/t/whats-the-best-speed-we-can-get-with-qwen-3-6-27b-without-quantizing/367561
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-official-fp8-running-across-2x-dgx-spark-tp-2-mtp-200k-ctx-recipe-numbers/370309/195
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-aiden-recipe-from-reddit-1m-token-session-operational-cuda-12-1-tailored-for-dgx-spark-gb10/372268/73
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-vision-exp-is-released-as-open-weights/381911/302
- https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822/213
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-aiden-recipe-from-reddit-1m-token-session-operational-cuda-12-1-tailored-for-dgx-spark-gb10/372268/573
- https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822/221
- https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822/236
- https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822/252
- https://forums.developer.nvidia.com/t/qwen-qwen3-6-35b-a3b-and-fp8-has-landed/366822/305
- https://forums.developer.nvidia.com/t/qwen3-5-122b-a10b-on-single-spark-up-to-51-tok-s-v2-1-patches-quick-start-benchmark/365639/315
- https://forums.developer.nvidia.com/t/fp4-on-dgx-spark-why-it-doesnt-scale-like-youd-expect/360142
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-aiden-recipe-from-reddit-1m-token-session-operational-cuda-12-1-tailored-for-dgx-spark-gb10/372268/607
- https://github.com/tonyd2wild/DeepSeek-v4-Flash-Vision-Exp-DSpark-1M-NVFP4-KV-2x-DGX-Spark
- https://forums.developer.nvidia.com/t/deepseek-v4-flash-aiden-recipe-from-reddit-1m-token-session-operational-cuda-12-1-tailored-for-dgx-spark-gb10/372268/639
- https://forums.developer.nvidia.com/t/350367

El texto de lo que dicen esos hilos se reubicó el 2026-11-01 a la base de conocimiento del dueño, por decisión del dueño: el conocimiento vive en el consumidor de conocimiento. Esta ficha conserva sólo el trabajo sobre la máquina y su registro de verificación; su `close_check` no cambió.

## Prevención y fix propuesto

Reutilizar metadatos de imagen, manifiesto OCI/ARM64, CUDA/PTXAS, GPU real y arquitecturas del backend; documentar una matriz OEM/OS/driver/contenedor soportada y un smoke test antes de cargar modelos. Probar la imagen oficial compatible primero; construir un verificador propio exige demostrar un hueco. Si existe fallback Triton soportado, comparar estabilidad y exactitud antes de recomendarlo. Conectar admisión y restart containment, separando error del proceso de freeze del host.

## Riesgos, validación y cierre

Imagen ARM64 correcta/amd64 incompatible, CPU-only wheel, cubin equivocado, hash inválido, imagen CUDA que exige driver diferente y stack sano. Preservar hash/versions/outputs y control de host/SSH durante reproducción. No saltar checksums ni requisitos CUDA; no instalar toolkit global o driver fuera de soporte como receta general. Cada cambio de backend necesita controles de resultados, medición local de rendimiento, soak predeclarado y retorno a imagen anterior. El verificador propuesto todavía debe implementarse y los logs adjuntos siguen pendientes; registrar compatibilidad desconocida como could_not_run.

## Progreso de preflight (2026-10-02)

La ficha sigue abierta: falta validar las rutas de kernel del backend y la combinación OEM/imagen para el workload elegido, exactitud/rendimiento, soak y rollback de imagen. El contenedor actual está corriendo con un proceso GPU; esto no acredita todas sus rutas de ejecución. No se cambió imagen ni driver.

### DELTA-ROOT-TOKENIZER-PATCH-SEMANTIC-GATE-01

Propuesta: registrar revision/hash efectivos de tokenizer, checkpoint, imagen y patch; probar recepción completa de un prompt largo con centinelas verificables, imágenes por encima y debajo del antiguo límite, herramientas/Harmony y generación sostenida. Ante pérdida semántica, rechazar la promoción del candidato y conservar el runtime conocido. Riesgo: cambiar tokenizer completo altera otras reglas; preferir artefacto corregido del proveedor y comparar el delta exacto. Rollback: retirar overlay identificado y restaurar el snapshot/digest previo; verificar el mismo canary. `close_check`: fixture afectado reproduce truncamiento; fixture corregido conserva todos los centinelas y el conteo esperado; patch MXFP4 candidato pasa casos funcionales y soak con resultados/errores explícitos. Parches externos y ensayos en host siguen pendientes; esta ficha registra investigación.

## Clasificación del impedimento — 2026-10-04

- Categoría principal: `workload_or_lab`.
- Impedimento: La identidad de arquitectura/driver/CUDA/imagen se reutiliza parcialmente, pero no hay logs locales ni canario de carga, primera inferencia, salida semántica y soak con rollback.
- Evidencia faltante para cierre: La identidad de arquitectura/driver/CUDA/imagen se reutiliza parcialmente, pero no hay logs locales ni canario de carga, primera inferencia, salida semántica y soak con rollback.
- Siguiente acción: Coordinación BB: cerrar contrato de admisión y controles negativos; operador Luis: correr canario en runtime/OEM compatible con digest fijado. Ref explícita: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md y tests/test_debt_registration_controls.py. Ref explícita: tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md y tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01-direct-close-current.log.
- Responsable del siguiente paso: Coordinación BB prepara/implementa; cuando la acción requiere root/lab/hardware, operador Luis aporta y ejecuta el sujeto indicado..
- Cierre completo accionable hoy: no. Preparación coordinable: sí.
- Evidencias de clasificación: `tasks/backlog/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01.md`, `tests/test_debt_registration_controls.py`, `tasks/evidence/OPEN-96-CLASSIFICATION-2026-10-04/batches/batch_03.json`, `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01-direct-close-current.log`.
- Impedimentos de inspección: 0. El criterio original permanece intacto; esta clasificación conserva la ficha abierta.

## Adaptacion a este equipo (clasificacion 2026-10-13)
Aplicabilidad: adaptable · utilidad: alta · lectura: completa.

Ficha acumulada de ~40 hilos; el nucleo (imagen ARM64, driver 580 frente a NVIDIA_REQUIRE_CUDA, cubin sm_121, NaN/salida corrupta en backends FP8/NVFP4) aplica a este nodo, que corre vllm/vllm-openai:v0.27.1 con nemotron-local. La parte de preflight ya existe (tools/preflight.py check_runtime, evidencia en tasks/evidence/FEATURE-FORUM-GB10-RUNTIME-COMPAT-01/) con resultado unknown en kernels efectivos, y tools/canario_motor.py cubre nombre servido, JSON y tool-call; la ficha sigue abierta por soak, rollback y manifiesto de kernels. Los casos multinodo/CX7/Ray/NCCL/GLM/Qwen/MiniMax/DeepSeek (alrededor de la mitad del texto) no tienen sujeto aqui (/sys/class/infiniband no existe).

Version para un solo nodo Gigabyte AI TOP ATOM: Reducir el alcance a un nodo: cerrar con preflight runtime (arquitectura, digest OCI, driver vs NVIDIA_REQUIRE_CUDA, GPU sm_121) mas un canario de finish_reason/usage/logits finitos sobre nemotron-local (extender tools/canario_motor.py) y rollback al digest de v0.27.1; mover todos los casos multinodo, Ray/NCCL y otros modelos a una ficha aparte marcada otro_hardware.

Perfil contra el que se clasifico: un nodo GB10 Gigabyte, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04, un contenedor vLLM (`nemotron-local`), sin InfiniBand/CX7 en pareja, sin Ray ni llama.cpp RPC. Clasificacion por lectura, sin control negativo: es una propuesta, no una verificacion.

## Avance 2026-10-14: manifiesto cubin/PTX medido

`python3 -m tools.backend_arch_manifest capture` (contenedor desechable `--rm --network none --memory 4g`, sin GPU, sin montajes) + `build-evidence`. Núcleo (vllm `_C`/`_moe_C`, torch `libtorch_cuda`) cubre 12.1 de forma nativa (sm_120 / sm_121a); marcados NOT_COVERED: flashmla, qutlass, vllm_fa3, flashinfer_cubin (sólo sm_90a/sm_100). El ptxas de triton es CUDA 12.8 sin sm_121. El preflight `runtime` pasa a `pass`; el verificador sigue en `unknown` (faltan negativo de incidente, modelo-kernel probado, OEM, rollback): la ficha NO se cierra.

## Criterios ejecutables de `tools.verify_forum_finding` (2026-10-14)
Los criterios ejecutables de `tools.verify_forum_finding` se miden en esta ficha: su `close_check` corre ese verificador contra la captura real del sujeto. La meta-ficha `DEBT-CLOSE-CHECK-VERIFY-FORUM-FINDING-01`, que pedia implementarlos, se cerro el 2026-10-14 como `duplicate` (voto de Luis: consolidar en la ficha sujeto): el verificador existe y hoy, sin esa captura, sale con could_not_run (rc=2); conseguir la captura es trabajo de esta ficha.
