---
id: FEATURE-COSECHA-DISTROS-ALTERNAS-GB10-01
kind: task
domain: GPU
title: "Cosechar distros alternas para GB10 y ver si alguien ya construyo lo que nos falta"
status: done
closed_at: 2026-10-12
evidence: {"pass": "tasks/evidence/FEATURE-COSECHA-DISTROS-ALTERNAS-GB10-01/pass.txt", "fail": "tasks/evidence/FEATURE-COSECHA-DISTROS-ALTERNAS-GB10-01/fail.txt", "e2e": "tasks/evidence/FEATURE-COSECHA-DISTROS-ALTERNAS-GB10-01/e2e.txt", "cosecha": "tasks/evidence/FEATURE-COSECHA-DISTROS-ALTERNAS-GB10-01/cosecha.txt"}
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q cosecha_distros_leida tasks/evidence/FEATURE-COSECHA-DISTROS-ALTERNAS-GB10-01/cosecha.txt", "expect": "exit_zero", "porque": "Peticion de Luis 2026-10-12: explorar otras distros (NixOS, Arch, Fedora/RHEL/Rocky, Kairos, Omarchy, otras) y sus adaptaciones a GB10 para ver si alguien ya desarrollo, para ellas, lo que nos falta: limite de memoria GPU por contenedor o cgroup, dmem/memacct, guardia contra OOM de memoria unificada, kernel con CONFIG_CGROUP_DMEM, driver 610/615 empaquetado, monitores de UMA. Cierra con un informe por proyecto: que hace, licencia, evidencia leida (archivo:linea o URL) separada de inferencia, y que NO se leyo."}
---

## Por que
La publicacion 6 de https://forums.developer.nvidia.com/t/can-dgx-spark-work-with-non-dgx-os/379085 solo pide soporte no Debian. El material esta en https://forums.developer.nvidia.com/t/has-anyone-tried-an-alternative-linux-distro/349124 (69 respuestas) y en repos: graham33/nixos-dgx-spark, straylight-software/nixos-dgx-spark, RageLtd/linux-dgx-spark, Kairos, Omarchy (Jim Martin, Matt Gilg), guias RHEL/Rocky.
## Que se busca (lo que nos falta)
Limite de memoria GPU por contenedor o cgroup; dmem/memacct; guardia de MemAvailable para memoria unificada; kernel con CONFIG_CGROUP_DMEM; driver 610/615; monitores UMA; politicas de OOM.

## Root Cause
No habia lista de fuentes ni lectura de lo que otras distros ya hicieron para GB10.

## Regression Test
`tests/test_distros_alternas_fuentes.py` (esquema, ids unicos, URLs https, la cosecha citada existe); control negativo: un id duplicado la hace fallar (fail.txt).

## Verification Evidence
`cosecha.txt` (agente Sonnet, solo lectura; verificado por mi lo comprobable): kernel con CGROUP_DMEM existe en straylight, omarchy-spark, spark-rocky y en este host; RageLtd lo desactiva (y PSI); no existe en ninguna fuente leida un limite de memoria GPU por contenedor/cgroup, ni politica de slice para Docker con GPU; guardia mas cercana: `tom-doerr/gpuoom` (MIT, PSI + MemAvailable + NVML); driver 610/615 en spark-rocky, omarchy-spark y graham33, ninguno resuelve Secure Boot (piden desactivarlo), solo Start9 lo hace con MOK. Lista versionada en `data/distros_alternas.json`. Huecos declarados: Red Hat 404, openSUSE 403, repos de Omarchy sin clonar, hilos 371180/353752 sin abrir.
