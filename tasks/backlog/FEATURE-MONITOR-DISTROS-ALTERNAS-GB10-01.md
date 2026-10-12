---
id: FEATURE-MONITOR-DISTROS-ALTERNAS-GB10-01
kind: task
domain: GPU
title: "Monitor de distros alternas para GB10 que avise de mecanismos cosechables para la ATOM"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "test -s tasks/evidence/FEATURE-MONITOR-DISTROS-ALTERNAS-GB10-01/primera-pasada.txt && grep -q monitor_distros_probado tasks/evidence/FEATURE-MONITOR-DISTROS-ALTERNAS-GB10-01/primera-pasada.txt", "expect": "exit_zero", "porque": "Decision de Luis 2026-10-12 (DECISIONS.md): la ATOM se queda en DGX OS oficial y se MONITOREAN las distros alternas. Cierra con una primera pasada real del monitor sobre la lista de fuentes, que escriba un hallazgo por fuente con cambio (o 'sin cambio') y su control negativo: una fuente sin actividad no genera hallazgo, una con commit nuevo si."}
---

## Que monitorea
Lista versionada de fuentes en este repo (`data/distros_alternas.json`, esquema `bb-fuentes/1`): `graham33/nixos-dgx-spark`, `straylight-software/nixos-dgx-spark`, `RageLtd/linux-dgx-spark`, Kairos (guia DGX Spark), Omarchy (repos y paquetes aarch64 de Jim Martin y Matt Gilg), guias RHEL 10 / Rocky 10 para Spark, el hilo https://forums.developer.nvidia.com/t/has-anyone-tried-an-alternative-linux-distro/349124 y los que descubra FEATURE-COSECHA-DISTROS-ALTERNAS-GB10-01.
## Que busca (palabras y archivos, no opiniones)
`CGROUP_DMEM`, `memacct`, `dmem.capacity`, `HAMi`, `MemoryMax` con GPU, guardias de `MemAvailable`, empaquetado de driver 610/615 y firma Secure Boot, cambios en la configuracion de kernel.
## Contrato de informacion (sin imports cruzados)
El monitor escribe `$BLACKBOX_DATA/hallazgos/distros_alternas.jsonl` (`bb-hallazgo/1`, como los demas hallazgos de bb); Atlas los recoge con `tools/recoge_hallazgos_bb.py`. bb no sabe de Atlas.
## Plan
1. HECHO 2026-10-12: lista de fuentes `data/distros_alternas.json` (15 fuentes, `bb-fuentes/1`) con `tests/test_distros_alternas_fuentes.py`, de la cosecha FEATURE-COSECHA-DISTROS-ALTERNAS-GB10-01.
2. Comparador por fuente con `git ls-remote` (HEAD) y la API de commits recientes; el hilo del foro por numero de respuestas. Sin descargar codigo.
3. Interruptor `monitor_distros` (off/observar/actuar) en `tools/interruptores.py`; `actuar` solo escribe el hallazgo.
4. Frecuencia semanal; la unidad de usuario con tope de memoria.
## Limite declarado
Detecta actividad y palabras clave, no juzga si el mecanismo sirve: eso lo mide una ficha propia con control negativo.
