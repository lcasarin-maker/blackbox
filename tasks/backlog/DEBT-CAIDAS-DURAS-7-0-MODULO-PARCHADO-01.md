---
id: DEBT-CAIDAS-DURAS-7-0-MODULO-PARCHADO-01
kind: task
domain: GPU
title: "Cuatro caidas en 25 min con el modulo nvidia parchado en el kernel 7.0.0-1024; el modulo de fabrica aguanto 1 h 50 con la misma carga"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-30
close_check: {"cmd": "f=tasks/evidence/DEBT-CAIDAS-DURAS-7-0-MODULO-PARCHADO-01/estable-con-motor.txt; test -s $f && grep -qE '^uptime_min=([6-9][0-9]|[0-9]{3,})$' $f && grep -q '^motor_activo=1$' $f && grep -q '^modulo=.*/updates/nvidia.ko$' $f", "expect": "exit_zero", "porque": "Falla hoy: el archivo no existe. Pasa solo con una foto tomada tras >=60 min de uptime continuo, con el motor activo y el modulo parchado (updates/) cargado."}
---

## Medido el 2026-10-30 (kernel 7.0.0-1024-nvidia, driver 580.178.04)

- Modulo de fabrica: arranque 15:30, estable hasta el reinicio voluntario de las 16:20 (1 h 50 min, motor vLLM de 40 GB cargado).
- Modulo parchado (instalado en updates/ a las 16:17, cargado desde el arranque de las 16:22; dmem.capacity con region vidmem 53.8 GB):
  - 16:22:07 a 16:30:10 (8 min): corte DURO, el journal acaba en una linea rutinaria de earlyoom (66 GB libres), sin panic ni volcado. BERT nuevo (corrected, MTKID).
    La telemetria muestra la GPU pasando de 8 % a 96 % de uso y 52 W a las 22:30:06Z, y 44 GB de memoria liberados 5 s despues; a las 16:30:00 `liberation-watchdog` habia parado `atlas-api`.
  - 16:32:16 a 16:34:29 (2 min 13 s): corte DURO con la GPU en reposo (11 %, 9 W, 76 GB libres) y sin que nada la usara; el watchdog NO dispara a esa hora.
  - 16:36:51 a 16:38:34 (1 min 43 s): corte duro. Su journal acaba en una linea de `python3` de otro servicio, sin secuencia de apagado.
  - 16:41:02 a 16:42:57 (1 min 55 s): corte duro, PERO a las 16:42:26 yo (Claude) ejecute `systemctl --user disable --now` sobre 22 unidades, incluido `ai-nemotron.service`;
    Docker lo mato a los 30 s ("Container failed to exit within 30s of signal 15", 16:42:56) y el journal acaba a las 16:42:57. Este cuarto corte NO es evidencia independiente:
    coincide con la parada forzada de un contenedor de 40 GB que hice yo. Puede ser causa o casualidad; no se midio.
- Comprobacion de que son cortes y no apagados: buscar `systemd-shutdown|Reached target.*(Shutdown|Reboot|Power)|Stopped target` en el journal de cada arranque. Control negativo: el reinicio voluntario de las
  16:20 da 67 coincidencias y acaba en "Journal stopped"; los cuatro cortes dan 1 (una linea de GNOME al iniciar sesion, no de apagado) y ninguno acaba en "Journal stopped".
- Bloqueo (16:42, `disable --now` de 22 unidades de usuario, manifiesto en `~/.local/share/blackbox/suspensiones/2026-10-30-crashloop.json`, vence 2026-11-06):
  el arranque de las 16:45 sin motor ni temporizadores supero los 2:28 de uptime.
- Descartado: `bb-dmem-guardia` (journal: "la GPU responde; el modulo parcheado se queda"; solo hace `retrocede`, no reinicia).

## No se sabe

La causa. Cuatro cortes con el modulo parchado y ninguno con el de fabrica es correlacion, no prueba: el modulo de fabrica solo se midio en UN arranque largo.
El 7.0 con el modulo parchado nunca se probo antes (solo compilado). Candidatos: el modulo parchado (fallo de contabilidad dmem al liberar o asignar memoria unificada), el arranque del motor
de 40 GB, o la combinacion.

## Corte de la causa: lo que el retroceso NO determina (2026-10-30, tras retroceder el modulo)

El retroceso devuelve el modulo de fabrica. Si despues la maquina aguanta, eso es una correlacion mas, no el aislamiento de la causa: cambiaron a la vez el modulo, el kernel en uso
(7.0.0-1024 desde el arranque de las 15:30), el estado de las unidades y yo mismo (comandos en vivo). Otros candidatos que NO se descartaron:
- Firmware: `nvidia-spark-ota-check` del 2026-10-30 marca `SOCFW`, `EC` y `USBPD` por detras de OTA2610 (apt no los actualiza). Los cortes duros sin mensaje de kernel son la firma de un reset
  de SoC, EC o PD, no de un panic de kernel (no hay panic, no hay volcado de kdump, el BERT solo trae el encabezado).
- Cortes duros previos al parche en el 7.0: el repo documenta el colapso del 2026-10-16 y hay BERT del 14 y 16 de octubre (kernel 6.17).

## Procedimiento que SI determina la causa (una variable por vez, con instrumento que sobreviva al corte)

1. Instrumento primero: hoy el corte duro no deja nada. Antes de repetir la prueba, armar una captura que lo vea (consola serie `ttyS0` ya esta en la linea de comandos; netconsole hacia otra maquina;
   telemetria de EC/PD con `fwupdmgr`), y registrar el resultado con su control negativo.
2. Linea base de fabrica CON motor: reponer las 22 unidades de una en una, el motor primero, y medir el tiempo hasta el corte. Si el modulo de fabrica tambien corta, el parche queda exonerado.
3. Solo si la base aguanta >= 60 min con motor: reinstalar el modulo parchado SIN tocar nada mas y repetir exactamente la misma carga. Un corte aqui y ninguno en el paso 2 si aisla el parche.
4. Si cortan los dos: la causa es kernel o firmware; no se vuelve a tocar el modulo y se abre la ficha de firmware.

## Por hacer

1. Estabilizar sin motor, luego reintroducir UNA unidad a la vez (primero el motor) y registrar el tiempo hasta el corte.
2. Si el motor reproduce el corte con el modulo parchado y no con el de fabrica, retroceder el modulo (`sudo bash tools/dmem_modulo.sh retrocede`) y devolver el parche a revision.
3. Restaurar las 22 unidades con el manifiesto antes del 2026-11-06.
