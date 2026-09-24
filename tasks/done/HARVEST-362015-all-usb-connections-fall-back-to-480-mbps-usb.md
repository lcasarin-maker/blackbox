---
id: HARVEST-362015-all-usb-connections-fall-back-to-480-mbps-usb
kind: task
title: "Evaluar adopción: mecanismo cosechado por Atlas (362015-all-usb-connections-fall-back-to-480-mbps-usb-2-0)"
status: done
closure_type: adopted_prior_implementation
closed_at: 2026-09-23
evidence: {"verificado_el_destino": "$ # el close_check de la ficha que lleva el trabajo, corrido el 2026-09-23\n$ grep -q 'USB/xHCI' tasks/done/FEATURE-USB-XHCI-FORENSICS.md\nrc=0  (0 = pasa)", "evidencia_del_destino": "Los 3 ficheros de tasks/done/FEATURE-USB-XHCI-FORENSICS.md, comprobados presentes el 2026-09-23: tasks/evidence/FEATURE-USB-XHCI-FORENSICS/e2e.txt, tasks/evidence/FEATURE-USB-XHCI-FORENSICS/fail.txt, tasks/evidence/FEATURE-USB-XHCI-FORENSICS/pass.txt", "limite_declarado": "El close_check de FEATURE-USB-XHCI-FORENSICS.md es un grep sobre su propio texto: comprueba que la ficha diga lo que dice, no que la funcion sirva. Lo que sostiene el cierre son sus ficheros de evidencia, que traen comando, salida y control negativo.", "e2e": "tasks/evidence/FEATURE-USB-XHCI-FORENSICS/e2e.txt", "fail": "tasks/evidence/FEATURE-USB-XHCI-FORENSICS/fail.txt", "pass": "tasks/evidence/FEATURE-USB-XHCI-FORENSICS/pass.txt"}
severity: P3
origin: asserted
satd_family: HARVEST_SUGGESTION
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/HARVEST-362015-all-usb-connections-fall-back-to-480-mbps-usb.md", "expect": "exit_zero", "porque": "Sugerencia de adopcion, no un defecto -- verifica que accepted.by/date/trigger este lleno y no sea el placeholder, patron de own_chats/tools/check_harvest_accepted.py (DGX-505)."}
created: 2026-09-09
reason: "CERRADA 2026-09-23 como adopted_prior_implementation. La adopcion de esta sugerencia se implemento con codigo real en un commit ANTERIOR y ese trabajo vive en tasks/done/FEATURE-USB-XHCI-FORENSICS.md, cerrada con su propia evidencia (3 ficheros, los 3 presentes). Esta ficha era la EVALUACION, no el trabajo: su trigger era un puntero a trabajo ya terminado, no una vigilancia, asi que cerrarla no apaga nada. Verificado antes de cerrar: el close_check de FEATURE-USB-XHCI-FORENSICS.md corre y pasa."
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

## Root Cause

Atlas cosecho un mecanismo de una fuente externa y lo sugirio para blackbox por
dominio. **Nadie de blackbox pidio esta evaluacion** -- es cosecha pasiva, y la
ficha existe para dejar constancia de la DECISION, no para hacer el trabajo.

La decision fue ADOPTAR. El trabajo real se escribio como codigo y vive en
`tasks/done/FEATURE-USB-XHCI-FORENSICS.md`, cerrada por su cuenta y con su propia evidencia. Esta
ficha no tenia codigo que escribir: su entregable era decidir, y decidio.

Por eso el `closure_type` es `adopted_prior_implementation` y no
`void_wontfix` (seria falso: SI se hizo trabajo) ni `duplicate` (no lo es: la
evaluacion y la implementacion son cosas distintas) ni
`relocated_prior_verification` (presupone que esta ficha ya estaba `done` en un
commit anterior, y seguia abierta).

## Regression Test

El de la ficha que lleva el trabajo, que es donde vive el sujeto:

```
grep -q 'USB/xHCI' tasks/done/FEATURE-USB-XHCI-FORENSICS.md
```

Corrido el 2026-09-23 antes de cerrar esta: **pasa**. Si esa verificacion
dejara de pasar, la que se reabre es `FEATURE-USB-XHCI-FORENSICS.md` -- ahi esta el codigo --, no esta
evaluacion, que no tiene nada que arreglar.

## Verification Evidence

La de `tasks/done/FEATURE-USB-XHCI-FORENSICS.md`, comprobada presente el 2026-09-23 (3 de 3 ficheros):

- `tasks/evidence/FEATURE-USB-XHCI-FORENSICS/e2e.txt`
- `tasks/evidence/FEATURE-USB-XHCI-FORENSICS/fail.txt`
- `tasks/evidence/FEATURE-USB-XHCI-FORENSICS/pass.txt`

LIMITE DECLARADO: el `close_check` de `FEATURE-USB-XHCI-FORENSICS.md` es un `grep` sobre su propio
texto en la mayoria de estas fichas, o sea que comprueba que la ficha diga lo
que dice, no que la funcion sirva. Lo que sostiene el cierre de verdad son sus
ficheros de evidencia, que traen comando, salida y control negativo. Se dice
en vez de presentar el `grep` como si fuera una prueba funcional.
