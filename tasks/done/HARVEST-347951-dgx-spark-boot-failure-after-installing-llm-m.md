---
id: HARVEST-347951-dgx-spark-boot-failure-after-installing-llm-m
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (347951-dgx-spark-boot-failure-after-installing-llm-model)"
status: done
closure_type: adopted_prior_implementation
closed_at: 2026-09-23
evidence: {"verificado_el_destino": "$ # el close_check de la ficha que lleva el trabajo, corrido el 2026-09-23\n$ grep -q 'journalctl -b -1\\\\|boot anterior' tasks/done/FEATURE-GDM-BOOT-COLGADO.md\nrc=0  (0 = pasa)", "evidencia_del_destino": "Los 3 ficheros de tasks/done/FEATURE-GDM-BOOT-COLGADO.md, comprobados presentes el 2026-09-23: tasks/evidence/FEATURE-GDM-BOOT-COLGADO/e2e.txt, tasks/evidence/FEATURE-GDM-BOOT-COLGADO/fail.txt, tasks/evidence/FEATURE-GDM-BOOT-COLGADO/pass.txt", "limite_declarado": "El close_check de FEATURE-GDM-BOOT-COLGADO.md es un grep sobre su propio texto: comprueba que la ficha diga lo que dice, no que la funcion sirva. Lo que sostiene el cierre son sus ficheros de evidencia, que traen comando, salida y control negativo.", "e2e": "tasks/evidence/FEATURE-GDM-BOOT-COLGADO/e2e.txt", "fail": "tasks/evidence/FEATURE-GDM-BOOT-COLGADO/fail.txt", "pass": "tasks/evidence/FEATURE-GDM-BOOT-COLGADO/pass.txt"}
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-347951-dgx-spark-boot-failure-after-installing-llm-m.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
reason: "CERRADA 2026-09-23 como adopted_prior_implementation. La adopcion de esta sugerencia se implemento con codigo real en un commit ANTERIOR y ese trabajo vive en tasks/done/FEATURE-GDM-BOOT-COLGADO.md, cerrada con su propia evidencia (3 ficheros, los 3 presentes). Esta ficha era la EVALUACION, no el trabajo: su trigger era un puntero a trabajo ya terminado, no una vigilancia, asi que cerrarla no apaga nada. Verificado antes de cerrar: el close_check de FEATURE-GDM-BOOT-COLGADO.md corre y pasa."
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

## Root Cause

Atlas cosecho un mecanismo de una fuente externa y lo sugirio para blackbox por
dominio. **Nadie de blackbox pidio esta evaluacion** -- es cosecha pasiva, y la
ficha existe para dejar constancia de la DECISION, no para hacer el trabajo.

La decision fue ADOPTAR. El trabajo real se escribio como codigo y vive en
`tasks/done/FEATURE-GDM-BOOT-COLGADO.md`, cerrada por su cuenta y con su propia evidencia. Esta
ficha no tenia codigo que escribir: su entregable era decidir, y decidio.

Por eso el `closure_type` es `adopted_prior_implementation` y no
`void_wontfix` (seria falso: SI se hizo trabajo) ni `duplicate` (no lo es: la
evaluacion y la implementacion son cosas distintas) ni
`relocated_prior_verification` (presupone que esta ficha ya estaba `done` en un
commit anterior, y seguia abierta).

## Regression Test

El de la ficha que lleva el trabajo, que es donde vive el sujeto:

```
grep -q 'journalctl -b -1\\|boot anterior' tasks/done/FEATURE-GDM-BOOT-COLGADO.md
```

Corrido el 2026-09-23 antes de cerrar esta: **pasa**. Si esa verificacion
dejara de pasar, la que se reabre es `FEATURE-GDM-BOOT-COLGADO.md` -- ahi esta el codigo --, no esta
evaluacion, que no tiene nada que arreglar.

## Verification Evidence

La de `tasks/done/FEATURE-GDM-BOOT-COLGADO.md`, comprobada presente el 2026-09-23 (3 de 3 ficheros):

- `tasks/evidence/FEATURE-GDM-BOOT-COLGADO/e2e.txt`
- `tasks/evidence/FEATURE-GDM-BOOT-COLGADO/fail.txt`
- `tasks/evidence/FEATURE-GDM-BOOT-COLGADO/pass.txt`

LIMITE DECLARADO: el `close_check` de `FEATURE-GDM-BOOT-COLGADO.md` es un `grep` sobre su propio
texto en la mayoria de estas fichas, o sea que comprueba que la ficha diga lo
que dice, no que la funcion sirva. Lo que sostiene el cierre de verdad son sus
ficheros de evidencia, que traen comando, salida y control negativo. Se dice
en vez de presentar el `grep` como si fuera una prueba funcional.
