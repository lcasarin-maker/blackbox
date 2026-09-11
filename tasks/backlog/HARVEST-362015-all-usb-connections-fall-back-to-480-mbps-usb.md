---
id: HARVEST-362015-all-usb-connections-fall-back-to-480-mbps-usb
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (362015-all-usb-connections-fall-back-to-480-mbps-usb-2-0)"
status: open
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/backlog/HARVEST-362015-all-usb-connections-fall-back-to-480-mbps-usb.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
accepted: {"by": "the maintainer + Claude, revision de deuda 2026-09-09", "date": "2026-09-09", "trigger": "adoptado -- el trabajo real vive en tasks/backlog/FEATURE-USB-XHCI-FORENSICS.md, no en esta ficha de evaluacion"}
reason: "Detectar puertos SuperSpeed atascados en fallback a USB2.0/480Mbps (fallo de PHY) es una senal ausente en todo el inventario actual. Se consolida en FEATURE-USB-XHCI-FORENSICS."
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

- El controlador xHCI de plataforma intenta manejar el host Mediatek, pero falla al recuperar el proveedor PHY — `knowledge/references/forum_nvidia_362015_all-usb-connections-fall-back-to-480-mbps-usb-2-0.md:7`
- Función del kernel devm_usb_get_phy_by_phandle busca un proveedor PHY usando phandle y devuelve nulo por falta de binding ACPI para phy-mtk-tphy — `knowledge/references/forum_nvidia_362015_all-usb-connections-fall-back-to-480-mbps-usb-2-0.md:8`
- Los puertos SuperSpeed port01 en los controladores NVDA8000:00 a :04 quedan atrapados en el estado Powered Not-connected Disabled Link:RxDetect PortSpeed:0 — `knowledge/references/forum_nvidia_362015_all-usb-connections-fall-back-to-480-mbps-usb-2-0.md:9`
- Para el Paso 2 sobre DGX Spark, el mecanismo raíz ataca la categoría de falla de inicialización/enlace de capa física de hardware (falta de registro de PHY T-PHY MediaTek e invocación sin binding ACPI) — `knowledge/references/forum_nvidia_362015_all-usb-connections-fall-back-to-480-mbps-usb-2-0.md:13`
- Para Atlas, el patrón devm_usb_get_phy_by_phandle ataca la categoría de problemas de enrutamiento y enlace de hardware de bajo nivel — `knowledge/references/forum_nvidia_362015_all-usb-connections-fall-back-to-480-mbps-usb-2-0.md:14`
- Para Liberation Watchdog y Nomad Offline, el patrón de estado RxDetect atascado ataca la categoría de falla en monitoreo/depuración de inicialización de hardware fuera de línea — `knowledge/references/forum_nvidia_362015_all-usb-connections-fall-back-to-480-mbps-usb-2-0.md:15`
- El veredicto técnico es COS, requiriendo parche o configuración de binding ACPI para phy-mtk-tphy o manejo en driver para evitar caída a USB 2.0 — `knowledge/references/forum_nvidia_362015_all-usb-connections-fall-back-to-480-mbps-usb-2-0.md:21`
- El disparador de reevaluación es la validación en un DGX Spark físico con kernel 6.17.0-1008-nvidia y el registro de xhci-plat exitoso — `knowledge/references/forum_nvidia_362015_all-usb-connections-fall-back-to-480-mbps-usb-2-0.md:21`

## Por qué se sugiere para blackbox en concreto

En '## Hallazgos verificados' el mecanismo de estado RxDetect atascado (falla de detección/enlace de capa física de hardware) se atribuye a 'Liberation Watchdog y Nomad Offline' (nombres falsos) bajo la categoría de 'monitoreo/depuración de inicialización de hardware fuera de línea', que es exactamente el dominio declarado de blackbox: telemetría del AI TOP ATOM (mismo chip GB10), monitoreo de hardware, logs, systemd units.

## Procedencia

- Fuente original: https://forums.developer.nvidia.com/t/all-usb-connections-fall-back-to-480-mbps-usb-2-0/362015
- Dictamen de cosecha, ruta absoluta: `~/projects/Atlas/docs/agent_findings/2026-09-05_cosecha_forum_nvidia_362015_all-usb-connections-fall-back-to-480-mbps-usb-2-0.md`
- Corregido el 2026-09-09 (DGX-503): el dictamen original interrogó estos mecanismos sólo contra
  Atlas/aequitas_os porque la lista de flota de Atlas estaba rota (DGX-502) y no consideraba
  a blackbox en absoluto.

## Lo que esta ficha NO decide

No dice que blackbox deba adoptar nada. No mide si el código fuente es
production-ready, tiene licencia compatible, o pasa los propios gates de este repo -- eso lo
evalúa quien trabaje aquí, si decide que vale la pena mirarlo.
