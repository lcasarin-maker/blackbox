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

## Por hacer

1. Estabilizar sin motor, luego reintroducir UNA unidad a la vez (primero el motor) y registrar el tiempo hasta el corte.
2. Si el motor reproduce el corte con el modulo parchado y no con el de fabrica, retroceder el modulo (`sudo bash tools/dmem_modulo.sh retrocede`) y devolver el parche a revision.
3. Restaurar las 22 unidades con el manifiesto antes del 2026-11-06.
