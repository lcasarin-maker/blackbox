---
id: HARVEST-374016-dgx-spark-gb10-gpu-fails-to-initialize-gsp-fi
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (374016-dgx-spark-gb10-gpu-fails-to-initialize-gsp-firmware-sec2-secure)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-374016-dgx-spark-gb10-gpu-fails-to-initialize-gsp-fi.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-GPU-XID-DETECTION.md, no en esta ficha de evaluacion"}
reason: "Codigos Xid/RmInitAdapter de fallo de inicializacion de firmware GSP son una categoria de fallo distinta de la OOM del driver que bb scan ya cruza. El bloqueo de MODS por Secure Boot es limitacion operativa, no una señal capturable. Se consolida en FEATURE-GPU-XID-DETECTION."
---

## Qué es esto

Sugerencia de cosecha, no un defecto. Atlas (la KB compartida de la flota) leyó una fuente
externa y encontró mecanismos que podrían servirle a **este proyecto** específicamente, por
dominio. Nadie de blackbox pidió esta evaluación -- es cosecha pasiva. **La decisión
de adoptar, adaptar o descartar es 100% de este proyecto.**

Cruzada antes de escribirse contra `.simplecode/fork_own.json` de este repo (si existe) para
evitar sugerir algo que ya está vendorizado -- ver DGX-505 en Atlas, donde `own_chats` cazó 3
falsos positivos de este tipo en el primer lote.

## Mecanismos encontrados, con su cita (tal como Atlas los verificó)

- Mecanismo 1 (ksec2PrepareBootCommands): El kernel NVRM intenta cargar el firmware GSP a través de la partición SEC2, produciéndose un timeout durante el arranque seguro que impide inicializar el adaptador — `knowledge/references/forum_nvidia_374016_dgx-spark-gb10-gpu-fails-to-initialize-gsp-firmware-sec2-secure-boot-timeout-rmi.md:"1.  **Fallo de arranque SEC2 GSP (ksec2PrepareBootCommands):** El kernel NVRM intenta cargar el firmware GSP a través de la partición SEC2, la cual se queda esperando (timed out) durante el arranque seguro. Este es el mecanismo de bajo nivel que impide la inicialización del adaptador."`
- Paso 2 (Mecanismo 1 - Dolor / Falla de flota): El fallo de arranque SEC2 GSP ataca la categoría de falla de bootstrap de hardware out-of-the-box o post-sobrecalentamiento donde el dispositivo no pasa la autenticación de firmware — `knowledge/references/forum_nvidia_374016_dgx-spark-gb10-gpu-fails-to-initialize-gsp-firmware-sec2-secure-boot-timeout-rmi.md:"| **Fallo de arranque SEC2 GSP** | **DGX Spark** | Fallo de bootstrap de hardware 'out-of-the-box' o post-sobrecalentamiento; el dispositivo no pasa la autenticación de firmware, convirtiéndose en un pisapapeles. |"`
- Paso 2 (Mecanismo 2 - Dolor / Falla de flota): RmInitAdapter con error 0x62:0x65:2028 ataca la categoría de corrupción de estado de firmware por agotamiento de memoria unificada o thrashing de swap — `knowledge/references/forum_nvidia_374016_dgx-spark-gb10-gpu-fails-to-initialize-gsp-firmware-sec2-secure-boot-timeout-rmi.md:"| **RmInitAdapter / Error 0x62:0x65:2028** | **DGX Spark** | Corrupción del estado de firmware tras un evento de "thrashing" de memoria/unified swap; el error impide que el kernel NVRM reclame el hardware. |"`
- Paso 2 (Mecanismo 3 - Dolor / Falla de flota): El bloqueo de MODS por Secure Boot ataca el impedimento de diagnóstico en campo cuando las políticas UEFI bloquean drivers diagnósticos tras fallar la consola de video — `knowledge/references/forum_nvidia_374016_dgx-spark-gb10-gpu-fails-to-initialize-gsp-firmware-sec2-secure-boot-timeout-rmi.md:"| **Bloqueo MODS por Secure Boot** | **Liberation Watchdog** | Impedimento de diagnóstico en campo; el flujo de trabajo de verificación de hardware está atascado por políticas de seguridad UEFI cuando la consola de video falla. |"`

## Por qué se sugiere para blackbox en concreto

La tabla de interrogatorio mapea los tres mecanismos (timeout de firmware GSP/SEC2, corrupción de estado por RmInitAdapter, bloqueo de diagnóstico MODS por Secure Boot) a 'DGX Spark' y 'Liberation Watchdog' (ambos falsos); son fallas de firmware/diagnóstico de hardware, dominio exacto de blackbox, nunca interrogado.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-gb10-gpu-fails-to-initialize-gsp-firmware-sec2-secure-boot-timeout-rminitadapter-0x622028-rma/374016
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_374016_dgx-spark-gb10-gpu-fails-to-initialize-gsp-firmware-sec2-secure-boot-timeout-rmi.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
