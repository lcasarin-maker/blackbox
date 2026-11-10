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

## Plan escalonado, 2026-11-09 (orden de Luis: avanzar a 7.0 dejando siempre el camino de regreso)
Regla: una sola variable por etapa. El refugio de cada etapa es 6.17.0-1032 con el modulo de fabrica (`saved_entry`, autoarm tras 3 arranques sin confirmar, `sudo panic`).

| Etapa | Cambio | Criterio de salida | Camino de regreso |
|---|---|---|---|
| 0 (hoy) | 1025 una vez, con carga (`~/scratch/blackbox/2026-11-09-prueba-1025/observa.sh`, 100 min) | 0 firmas (`rpcRecvPoll`, `Xid`, `Oops`, `hung task`, `NVRM` timed/fail/OOM) y sin reinicios | reiniciar: `next_entry` ya se consumio |
| 1 (sin reiniciar) | guardia de GPU por nombre protegido (nemotron-server), no por etiqueta; `core22` y `dgx-spark-fieldiag` de uno en uno | pruebas verdes; actualizaciones sin errores | `git revert` / paquete anterior |
| 2 | instalar `netconsole-arranque` y fijar el punto de restauracion en 6.17 (verificar en `tools/panic.py` que no migre al 1025 tras 6 h sanas) | captura de arranque comprobada con linea de prueba en la Dell | `opt_in_captura.sh retrocede` |
| 3 | 1025 como defecto 24 h (modulo de fabrica) | 24 h sin firmas, `bb_intentos` vuelve a 0 | autoarm / `sudo panic` |
| 4 | 7 dias en 1025 | 7 dias sin cortes duros ni Xid 154 | idem |
| 5 | parche memacct recompilado para el kernel que se quede (no para 6.17: se tiraria), firmado con MOK, tope en `observar` una semana | el modulo carga, dmem.capacity != 0, 0 cortes | quitar `updates/nvidia.ko`, `depmod`, reiniciar al modulo de fabrica |
| 6 | firmware OTA de uno en uno; Ubuntu 26.04 al final con respaldo | cada uno con su ventana | respaldo previo |

## Lo medido que sostiene el orden
- 6.17 no es refugio libre de cortes: 7 cortes duros sin rastro desde el 6 de oct (DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01), con y sin modulo parchado; tasa antes/despues del parche 6,3 y 6,2 por 100 h (n=3, sin inferencia posible).
- 7.0.0-1024: bucle del 2 nov con `gsp_timeout` en varias filas de `reboots.jsonl`; `modulo_nvidia_ruta` = NOT_COLLECTED en esos arranques, asi que no se puede atribuir al modulo parchado o al de fabrica.
- El parche cobro y hizo cumplir `dmem.max` en 6.17 (DECISIONS 2026-10-16), pero hay que recompilarlo por kernel: parchearlo para 6.17 y luego rehacerlo para 7.0 duplica el trabajo.

## Hallazgo 2026-11-09 21:50: la vuelta 7.0 -> 6.17 con `reboot` fallo (voto de Luis: se mantiene el plan y se mejora la recuperacion)
- 19:21:03 el 1025 cerro de forma ordenada (3 h 23 min, 141 min con carga, 0 firmas estrictas). 19:21:53 arranco 6.17.0-1032 con el modulo de fabrica, como debia.
- **19:22:07, 10 s despues de cargar el modulo, en 6.17:** `Xid 119` / GSP Timeout (`rpcRecvPoll timedout`, funcion 76 GSP_RM_CONTROL, proceso Xorg). Ese arranque dejo 16 961 lineas `NVRM` y, a las 21:20:00, `Assertion failed ... NV_ERR_GPU_IN_FULLCHIP_RESET`. Es la firma que se atribuia al 7.0, ahora en 6.17.
- 21:20:17 `systemd-logind: Power key pressed short` (Luis apago con el boton). 21:22:05 a 21:22:59 otro arranque que acabo en apagado. Los reinicios manuales siguientes no dejaron diario. 21:47:09 arranco 6.17 y quedo sano (0 firmas, `bb_intentos=0`).
- **Correccion:** la nota de esta ficha «cualquier reinicio vuelve al 6.17» era cierta para GRUB y insuficiente: el arranque en 6.17 fallo igual.
- **Hipotesis sin probar:** un reinicio en caliente tras una sesion larga en 7.0 deja la GPU o el GSP en un estado que el arranque siguiente no recupera (el reinicio en caliente no corta la alimentacion de la GPU). Apoyan: dos reinicios en caliente 6.17 -> 6.17 (6 y 9 nov) y uno 6.17 -> 7.0 salieron bien; la unica vuelta 7.0 -> 6.17 fallo. No lo prueba: n=1.
- **Regla desde ahora:** la vuelta de 7.0 a 6.17 se hace con apagado completo (`poweroff`, esperar 30 s, encender), nunca con `reboot`.

### Recuperacion antes de la etapa 2 (nuevo requisito)
Escalera, de mas a menos automatica; cada peldano lleva su prueba:
1. Alarma de la Dell con una comprobacion de solo lectura por `ssh atom`: `GSP Timeout`/`Xid 119|154` en el diario del arranque actual, aviso por ntfy con la orden recomendada.
2. Apagado en frio remoto: script sellado de `bb-root-run` que hace `systemctl poweroff`, y la Dell envia Wake-on-LAN (MAC enP7s7 48:21:0b:95:41:f1) a los 45 s. Sin probar: que la NIC y el BIOS enciendan desde apagado (`sudo ethtool enP7s7 | grep Wake-on`; `/sys/class/net/enP7s7/device/power/wakeup` dice `enabled`).
3. Si `ssh-casa` esta caido: nada de la Dell llega. Solo el boton fisico, o un enchufe inteligente (corte real de energia) comandado desde la Dell. Decision de Luis y de hardware.
