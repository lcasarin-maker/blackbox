---
id: HARVEST-347951-dgx-spark-boot-failure-after-installing-llm-m
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (347951-dgx-spark-boot-failure-after-installing-llm-model)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-347951-dgx-spark-boot-failure-after-installing-llm-m.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-GDM-BOOT-COLGADO.md, no en esta ficha de evaluacion"}
reason: "El mecanismo 1 (ruta de script en macOS) no aplica -- SO distinto. El mecanismo 3 (GDM colgado tras instalar un LLM grande) es una firma real que el check de Electron no cubre (exige un zygote ya vivo, GDM opera antes). Se consolida en FEATURE-GDM-BOOT-COLGADO."
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

- Mecanismo 1 (Ruta de script incorrecta en macOS): el script `CreateUSBKeyMacOS.sh` en la DGX Spark Recovery Image v1.91.51 referencia una ruta heredada (`/usbimg.customer/../usb`) en vez de (`/usbimg.customer/usb`), provocando el error "Install folder not found" que rompe la creación del medio en macOS — `knowledge/references/forum_nvidia_347951_dgx-spark-boot-failure-after-installing-llm-model.md:"CreateUSBKeyMacOS.sh script was moved out of the usbimg.customer/scripts folder, but the path inside the script wasn't updated. The script still references /usbimg.customer/../usb instead of /usbimg.customer/usb, which causes it to fail on macOS with the error:"`
- Mecanismo 3 (Bloqueo en el servicio GDM tras instalar LLM): el sistema pasa los servicios de arranque con "[OK]" pero se cuelga indefinidamente al arrancar el display manager GDM tras instalar un modelo LLM de 65GB, impidiendo el acceso a la consola o interfaz gráfica — `knowledge/references/forum_nvidia_347951_dgx-spark-boot-failure-after-installing-llm-model.md:"I installed a 65GB LLM, but after rebooting, the system never fully started up again. It gets all the way to the GDM login service, shows everything as "[OK]" in the boot messages, but then just hangs there indefinitely."`
- Interrogatorio - Paso 2 (Versión a nuestra escala y nombres existentes): La validación de rutas y particiones se mapea al pipeline de despliegue en Atlas para evitar fallos por rutas heredadas, la incoherencia de nodos de montaje mapea a validación de storage en pipelines de datos, y el bloqueo en GDM mapea a detección de cuellos de botella de infraestructura en Liberation Watchdog — `knowledge/references/forum_nvidia_347951_dgx-spark-boot-failure-after-installing-llm-model.md:"El mecanismo de extracción de rutas de scripts y validación de estructura de particiones FAT32/bootable es transferible a Atlas para pipelines de despliegue de modelos, asegurando que los medios de instalación no fallen por rutas heredadas."`
- Veredicto y disparador de reevaluación (Paso 3): Clasificado como COS porque los problemas evidencian fallos operacionales concretos con soluciones viables y rescatables (corrección de paths, ajustes de udev, purga de paquetes), con disparador de reevaluación fijado en la aplicación de parches a los scripts de creación de USB y la validación de device nodes antes de instalar modelos LLM grandes — `knowledge/references/forum_nvidia_347951_dgx-spark-boot-failure-after-installing-llm-model.md:"El disparador de reevaluación es la aplicación de parches a los scripts de creación de USB y la validación de device nodes antes de la instalación de grandes modelos LLM."`

## Por qué se sugiere para blackbox en concreto

El hallazgo VERIFICADO mapea 'el bloqueo en GDM mapea a detección de cuellos de botella de infraestructura en Liberation Watchdog' (satélite falso); ese mecanismo de detección de cuelgue de servicio systemd (GDM) por presión de disco/memoria tras instalar un LLM grande es el dominio literal de blackbox (monitoreo de hardware, logs, systemd units de la misma máquina GB10).

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/dgx-spark-boot-failure-after-installing-llm-model/347951
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_347951_dgx-spark-boot-failure-after-installing-llm-model.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
