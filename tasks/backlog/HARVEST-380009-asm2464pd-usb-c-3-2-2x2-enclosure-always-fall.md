---
id: HARVEST-380009-asm2464pd-usb-c-3-2-2x2-enclosure-always-fall
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (380009-asm2464pd-usb-c-3-2-2x2-enclosure-always-fall-back-to-usb2-0-48)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-380009-asm2464pd-usb-c-3-2-2x2-enclosure-always-fall.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-USB-XHCI-FORENSICS.md, no en esta ficha de evaluacion"}
reason: "Fallback de velocidad de enlace USB (generaliza el mismo mecanismo que HARVEST-362015, no depende del chip especifico del enclosure). El reset del controlador via registro es mitigacion activa, fuera de alcance. Se consolida en FEATURE-USB-XHCI-FORENSICS."
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

- El Mecanismo 2 ataca la categoría de falla de degradación silenciosa de ancho de banda o estado no saludable de enlace, asociándose al patrón de verificación de salud de nodo antes de operar — `knowledge/references/forum_nvidia_380009_asm2464pd-usb-c-3-2-2x2-enclosure-always-fall-back-to-usb2-0-480-mbps-soft-replu.md:"El patrón de polling de estado y la verificación de salud del enlace RAG/pertenece a la lógica de enrutamiento y estado del sistema Atlas, que a menudo necesita confirmar la salud del nodo antes de proceder con tareas de inferencia o transferencia de datos."`
- Mecanismo 3 (Ruteo por VID/PID y configuración de montajes): Abstrae la selección del periférico objetivo configurando variables de Vendor ID/Product ID y gestiona puntos de montaje (tales como unmount ZFS o compuertas en Docker) para evitar actuar sobre dispositivos erróneos en sistemas con múltiples carcasas — `knowledge/references/forum_nvidia_380009_asm2464pd-usb-c-3-2-2x2-enclosure-always-fall-back-to-usb2-0-480-mbps-soft-replu.md:"El script abstrae la identificación del dispositivo mediante Variables VID/PID configurables y rutas de montaje (ej. puntos de montaje ZFS o Docker). Esto permite al script aplicar la lógica de reset específicamente al dispositivo objetivo sin afectar otros hubs USB del sistema"`
- El disparador de reevaluación declarado es la necesidad de integrar el mecanismo de reset del controlador dentro del pipeline de resiliencia de Liberation Watchdog — `knowledge/references/forum_nvidia_380009_asm2464pd-usb-c-3-2-2x2-enclosure-always-fall-back-to-usb2-0-480-mbps-soft-replu.md:"El disparador de reevaluación es la necesidad de integrar este mecanismo de reset de controlador en el pipeline de resiliencia de **Liberation Watchdog**, añadiendo una nueva capacidad de recuperación de periféricos al portafolio de la flota."`

## Por qué se sugiere para blackbox en concreto

Los mecanismos (reset de controlador USB por escritura de registros, polling de salud de enlace vía lsusb, ruteo por VID/PID para evitar actuar sobre el dispositivo erróneo) son recuperación y monitoreo de periféricos de hardware físico -- dominio de blackbox -- pero el disparador de reevaluación se fijó sólo en el nombre falso Liberation Watchdog.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/asm2464pd-usb-c-3-2-2x2-enclosure-always-fall-back-to-usb2-0-480-mbps-soft-replug/380009
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_380009_asm2464pd-usb-c-3-2-2x2-enclosure-always-fall-back-to-usb2-0-480-mbps-soft-replu.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
