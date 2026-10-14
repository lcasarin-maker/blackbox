---
id: FEATURE-DMEM-PREENROLAMIENTO-LISTA-01
kind: task
domain: GPU
title: "Todo implementado y probado antes de enrolar la llave MOK y reiniciar con el modulo parcheado"
status: done
closed_at: 2026-10-14
closure_type: void_wontfix
reason: "Superada por el reinicio del 12-oct (Luis 2026-10-14): la llave MOK esta enrolada y el modulo NVIDIA 580.178.04 parcheado esta cargado desde el arranque del 2026-10-12 21:57, con la region dmem de vidmem en cgroup v2; la lista era el requisito PREVIO a ese reinicio. La fila 11 (ajustes de vLLM) sigue sin hacer y vive en FEATURE-VLLM-ENDURECIMIENTO-DE-MEMORIA-GB10-01; la fila 12 en FEATURE-DMEM-BOOSTERS-ADAPTAR-A-GB10-01; la fila 16 (ventana de reinicio) ya ocurrio."
evidence: {"pass": "tasks/evidence/FEATURE-DMEM-PREENROLAMIENTO-LISTA-01/pass.txt", "fail": "tasks/evidence/FEATURE-DMEM-PREENROLAMIENTO-LISTA-01/fail.txt", "e2e": "tasks/evidence/FEATURE-DMEM-PREENROLAMIENTO-LISTA-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "python -m tools.check_harvest_accepted tasks/done/FEATURE-DMEM-PREENROLAMIENTO-LISTA-01.md", "expect": "exit_zero", "porque": "Cerrada sin sujeto en este equipo (void_wontfix, decision de Luis 2026-10-14): no hay fix que probar, lo verificable por maquina es que la decision quedo registrada (closure_type y reason). El close_check anterior apuntaba a `grep -q pre_enrolamiento_completo tasks/evidence/FEATURE-DMEM-PREENROLAMIENTO-LISTA-01/lista.txt`, que ya no puede cumplirse porque el enrolamiento ocurrio antes de completar la lista."}
---

## Lista (estado al 2026-10-12)
| # | Pieza | Estado | Evidencia / lo que falta |
|---|---|---|---|
| 1 | Modulo 580.178.04 con memacct y parche zero-FB, compilado | HECHO | `FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01`: sha256 `bf817b6b…`, vermagic 6.17.0-1032-nvidia |
| 2 | Los 5 modulos (nvidia, modeset, uvm, drm, peermem) compilados | HECHO | sha256 de los 5 y de los de Canonical en `modulos-sha256.txt` |
| 3 | Instalar/retroceder con retroceso verificable | HECHO | `tools/dmem_modulo.sh` probado en directorio temporal con llave desechable (incl. archivo alterado: rc 1) |
| 4 | Guardia de arranque (retrocede si la GPU no responde en 120 s) | HECHO en logica; sin probar en arranque real | `bb-dmem-guardia.service`; su primera prueba real es el primer arranque |
| 5 | Prueba posterior al arranque | HECHO en logica | `tools/dmem_prueba.sh`: rc 0/4/5 con arbol falso, rc 3 contra el sistema real hoy |
| 6 | initramfs no pisa el modulo | HECHO | `lsinitramfs`: solo firmware NVIDIA, ningun `.ko`; `depmod` busca `updates` primero (`/usr/lib/depmod.d`) |
| 7 | Llave MOK existente, sin enrolar | HECHO (inventario) | `/var/lib/shim-signed/mok/MOK.der`, creada por dkms 2026-09-12; `mokutil --test-key`: not enrolled |
| 8 | Limitador CUDA que falla cerrado | HECHO | `bb limita` (9 pruebas) |
| 9 | Interruptores en observar (memavail, gpuoom) | HECHO | ambos instalados 2026-10-12 (voto de Luis); revisar `resumen()` el 2026-10-19 |
| 10 | Prueba del limitador con vLLM real en el laboratorio | PENDIENTE | el laboratorio solo tiene postgres y 1 GiB de tope: hace falta cargar la imagen vLLM y un modelo pequeno, o declarar que no cabe |
| 11 | Ajustes de vLLM (gpu-memory-utilization, expandable_segments, max-num-seqs) | PENDIENTE de Luis | `FEATURE-VLLM-ENDURECIMIENTO-DE-MEMORIA-GB10-01` |
| 12 | Adaptar el patron de los boosters dmem (dmem.low/dmem.max) | PENDIENTE | depende de que la prueba 5 dé region; `FEATURE-DMEM-BOOSTERS-ADAPTAR-A-GB10-01` |
| 13 | Runbook de recuperacion | HECHO (escrito, sin probar en un fallo real) | `runbook-recuperacion.txt`: SSH por socket, GRUB con kernel 7.0 de Canonical, comandos exactos |
| 14 | Quien sufre el reinicio | HECHO (lista medida; orden por confirmar) | `reinicio-afectados.txt`: 3 contenedores, 8 servicios de usuario, 19 procesos de sesiones |
| 15 | Actualizaciones del kernel y del driver con el modulo parcheado | HECHO (voto de Luis: NO bloquear; monitor + reparador) | `tools/dmem_monitor.py` + timer diario y `tools/dmem_reconstruye.sh`; el parche aplica a 580.178.04 y 580.173.02 y no a 615 |
| 16 | Ventana de reinicio | DE LUIS | fecha y hora, con consola fisica |

## Orden de enrolamiento (solo cuando 1-15 esten HECHO)
1. `sudo bash tools/dmem_modulo.sh enrolar`; reiniciar; pantalla azul MOK Manager: Enroll MOK, Continue, Yes, contrasena de un uso, Reboot.
2. `sudo bash tools/dmem_modulo.sh estado` (la llave debe salir enrolada).
3. `sudo bash tools/dmem_modulo.sh firma <dir con los .ko>` y `sudo bash tools/dmem_modulo.sh instala`.
4. Reiniciar con la consola a mano. Tras el arranque: `sudo bash tools/dmem_modulo.sh verifica` y `sudo bash tools/dmem_prueba.sh`.
5. Si algo falla: `sudo bash tools/dmem_modulo.sh retrocede && sudo reboot`.

## Avance 2026-10-13
Fila 10 (prueba del limitador con vLLM real): por voto de Luis se declara NO EJECUTABLE mientras el motor de produccion corra. Medido: el motor usa hasta 75 GiB de memoria unificada de 121 GiB (pico 76 968 MiB en la telemetria) y un segundo vLLM compartiria esa memoria; la imagen cabe en disco (2,0 TB libres) pero la prueba arriesgaria el unico motor. Quedan abiertas la fila 11 (ajustes de vLLM, de Luis) y la fila 16 (ventana de reinicio, de Luis).

## Root Cause
La lista se escribio para no enrolar la llave sin tener todo listo. El enrolamiento y el reinicio ocurrieron el 2026-10-12 21:57 con la guardia de arranque confirmando que la GPU responde; el estado que la lista preparaba ya no existe, asi que su close_check (`pre_enrolamiento_completo` en `lista.txt`) quedo sin objeto.

## Regression Test
Ninguno: la ficha no tenia test por ficha; su close_check era un grep sobre `lista.txt`, que nunca se escribio. Lo pendiente de la lista no se entierra: fila 11 en `FEATURE-VLLM-ENDURECIMIENTO-DE-MEMORIA-GB10-01` y fila 12 en `FEATURE-DMEM-BOOSTERS-ADAPTAR-A-GB10-01`, ambas abiertas; la fila 10 quedo declarada no ejecutable por voto de Luis el 2026-10-13.

## Verification Evidence
Tres rutas del frontmatter: `fail` (control negativo: las ordenes que buscan el sujeto salen con rc distinto de 0), `pass` (estado medido: Secure Boot, `dmem.capacity`/`dmem.current` con vidmem, `last -x reboot`, modulo en updates/ firmado con la llave del equipo, guardia de arranque en los dos arranques, con control positivo) y `e2e` (la decision registrada). Para reabrirla si el sujeto aparece: `git mv tasks/done/FEATURE-DMEM-PREENROLAMIENTO-LISTA-01.md tasks/backlog/` y `status: open`.
