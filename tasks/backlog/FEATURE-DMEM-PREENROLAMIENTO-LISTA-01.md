---
id: FEATURE-DMEM-PREENROLAMIENTO-LISTA-01
kind: task
domain: GPU
title: "Todo implementado y probado antes de enrolar la llave MOK y reiniciar con el modulo parcheado"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q pre_enrolamiento_completo tasks/evidence/FEATURE-DMEM-PREENROLAMIENTO-LISTA-01/lista.txt", "expect": "exit_zero", "porque": "Instruccion de Luis 2026-10-12: antes de enrolar la llave y reiniciar quiere que todo este implementado. Cierra cuando cada fila de la lista tiene estado HECHO con su evidencia y la fila de la ventana de reinicio la fija Luis."}
---

## Lista (estado al 2026-10-12)
| # | Pieza | Estado | Evidencia / lo que falta |
|---|---|---|---|
| 1 | Modulo 580.178.04 con memacct y parche zero-FB, compilado | HECHO | `FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01`: sha256 `bf817b6b…`, vermagic 6.17.0-1032-nvidia |
| 2 | Los 5 modulos (nvidia, modeset, uvm, drm, peermem) compilados | HECHO | `kernel-open/*.ko` en el scratchpad; falta guardar su sha256 junto al parche |
| 3 | Instalar/retroceder con retroceso verificable | HECHO | `tools/dmem_modulo.sh` probado en directorio temporal con llave desechable (incl. archivo alterado: rc 1) |
| 4 | Guardia de arranque (retrocede si la GPU no responde en 120 s) | HECHO en logica; sin probar en arranque real | `bb-dmem-guardia.service`; su primera prueba real es el primer arranque |
| 5 | Prueba posterior al arranque | HECHO en logica | `tools/dmem_prueba.sh`: rc 0/4/5 con arbol falso, rc 3 contra el sistema real hoy |
| 6 | initramfs no pisa el modulo | HECHO | `lsinitramfs`: solo firmware NVIDIA, ningun `.ko`; `depmod` busca `updates` primero (`/usr/lib/depmod.d`) |
| 7 | Llave MOK existente, sin enrolar | HECHO (inventario) | `/var/lib/shim-signed/mok/MOK.der`, creada por dkms 2026-09-12; `mokutil --test-key`: not enrolled |
| 8 | Limitador CUDA que falla cerrado | HECHO | `bb limita` (9 pruebas) |
| 9 | Interruptores en observar (memavail, gpuoom) | memavail instalado; gpuoom en repo SIN instalar | decidir instalar `bb-vigilante-gpuoom.service` |
| 10 | Prueba del limitador con vLLM real en el laboratorio | PENDIENTE | el laboratorio solo tiene postgres y 1 GiB de tope: hace falta cargar la imagen vLLM y un modelo pequeno, o declarar que no cabe |
| 11 | Ajustes de vLLM (gpu-memory-utilization, expandable_segments, max-num-seqs) | PENDIENTE de Luis | `FEATURE-VLLM-ENDURECIMIENTO-DE-MEMORIA-GB10-01` |
| 12 | Adaptar el patron de los boosters dmem (dmem.low/dmem.max) | PENDIENTE | depende de que la prueba 5 dé region; `FEATURE-DMEM-BOOSTERS-ADAPTAR-A-GB10-01` |
| 13 | Runbook de recuperacion desde la consola fisica | PENDIENTE | escribirlo con comandos exactos y probarlos en seco |
| 14 | Quien sufre el reinicio: vLLM, Atlas, atlas-pgvector, otras sesiones Claude, jobs | PENDIENTE | lista y orden de parada/arranque |
| 15 | Bloqueo de actualizaciones del kernel y del driver mientras el modulo este parcheado | PENDIENTE | un kernel nuevo hace que `updates/` no coincida (vermagic); `apt-mark hold` o aviso en `bb` |
| 16 | Ventana de reinicio | DE LUIS | fecha y hora, con consola fisica |

## Orden de enrolamiento (solo cuando 1-15 esten HECHO)
1. `sudo bash tools/dmem_modulo.sh enrolar`; reiniciar; pantalla azul MOK Manager: Enroll MOK, Continue, Yes, contrasena de un uso, Reboot.
2. `sudo bash tools/dmem_modulo.sh estado` (la llave debe salir enrolada).
3. `sudo bash tools/dmem_modulo.sh firma <dir con los .ko>` y `sudo bash tools/dmem_modulo.sh instala`.
4. Reiniciar con la consola a mano. Tras el arranque: `sudo bash tools/dmem_modulo.sh verifica` y `sudo bash tools/dmem_prueba.sh`.
5. Si algo falla: `sudo bash tools/dmem_modulo.sh retrocede && sudo reboot`.
