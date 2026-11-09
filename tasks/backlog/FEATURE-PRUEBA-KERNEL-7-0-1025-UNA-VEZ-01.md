---
id: FEATURE-PRUEBA-KERNEL-7-0-1025-UNA-VEZ-01
kind: task
domain: GPU
title: "Probar una sola vez el kernel 7.0.0-1025 con vuelta automatica al 6.17.0-1032, con captura de arranque y alguien presente"
status: open
severity: P2
origin: asserted
satd_family: UNCLASSIFIED_DEBT
created: 2026-11-09
close_check: {"cmd": "test -s ~/data/blackbox/prueba-kernel-1025/resumen.txt && grep -q 'resultado=' ~/data/blackbox/prueba-kernel-1025/resumen.txt", "expect": "exit_zero", "porque": "Falla hoy (no existe el resumen). Cierra cuando una prueba supervisada deja resumen.txt con resultado=ARRANCO_ESTABLE|COLGO|BUCLE y la ATOM de vuelta en 6.17.0-1032."}
---

## Decision de Luis, 2026-11-09 (boleta «Kernel 7.0»)
Probar el 7.0.0-1025 **una sola vez**. Alternativas descartadas: no actualizar y preguntar primero a zneill (recomendada por bb) y quedarse en 7.0 de forma permanente.

## Lo medido antes de decidir
- 1025 = 1024 mas un solo cambio publico: `ipv4: free inet_opt and ireq_opt after an RCU grace period` (LP: #2172774). Sin cambios de GSP, Xid 154, USB-PD ni EC (changelog de `linux-nvidia-7.0_7.0.0-1025.26~24.04.1`).
- `nvidia.ko` de 7.0.0-1024 y de 7.0.0-1025: mismo `srcversion` B9F87D2C66AEAE721A6DFF6 (580.178.04), el mismo que corre hoy en 6.17.0-1032. Lo que colgo al 1024 sigue en el 1025 salvo un cambio que el changelog no muestre.
- El 1024 anadio un parche SAUCE de USB (`xhci-plat`, NVDA8000, LP: #2171975); el 1025 no lo toca. Hipotesis sin comprobar: no se sabe si tiene relacion con el cuelgue.

## Secuencia (un comando a la vez, los de sudo los corre Luis en su terminal)
1. **Antes:** Luis presente en la casa; nemotron `health 200`; alarma de la Dell viva; `bb_intentos=0`; netconsole `bb` activo y comprobado con una linea de prueba que llegue a la Dell; punto de restauracion sano (`sudo panic` no hace falta).
2. **Una sola vez:** `sudo grub-reboot "<ruta de la entrada del 1025>"` (solo el proximo arranque; `saved_entry` sigue en 6.17.0-1032).
3. `sudo reboot`. Cualquier arranque posterior, sea reinicio por bucle o por corte de luz, vuelve a 6.17.0-1032 porque la entrada de una sola vez ya se consumio; ademas el autoarm de GRUB cubre tres arranques sin confirmar.
4. **Si cuelga sin reiniciarse:** apagado a mano (boton 10 s) y encender; arranca 6.17. Es el unico modo que GRUB no cubre.
5. **Si arranca:** observar 30 min con `journalctl -k -b | grep -E 'rpcRecvPoll|Xid|Oops|BUG'`; luego `sudo reboot` de vuelta a 6.17.0-1032 y escribir el resumen.

## Limites
- Un cuelgue sin reinicio automatico exige a Luis fisicamente (no es remoto).
- `netconsole-arranque` (captura desde el arranque temprano) sigue sin instalar; la captura sera la de `bb-netconsole` en marcha, que no cubre los primeros segundos.
