---
id: DEBT-TRES-CHEQUEOS-POR-IS-ACTIVE
kind: debt
title: "Tres filas de `bb status` leen si la unit esta activa, no si el instrumento trabaja"
status: open
severity: P2
origin: asserted
satd_family: WEAK_VERIFICATION
created: 2026-09-25
close_check: {"cmd": "python3 -m pytest tests/test_bb_bash.py -k status_comprueba_el_dato_no_la_unit -q", "expect": "exit_zero"}
---

## Que pasa

`bb status` tiene una regla propia, escrita en SPEC: **por sus datos, no por
la unit**, porque una unit `active` cuyo proceso dejo de escribir es justo el
fallo silencioso que bb existe para cazar. La cumple en cuatro filas -- sar,
monitor de memoria, telemetria termica, y desde hoy la proteccion de memoria
del escritorio, que lee los cgroups.

No la cumple en tres:

| fila | lo que hace | lo que no ve |
| --- | --- | --- |
| muestreo de apps/zombis | `systemctl is-active` del timer | un timer activo cuyo `bb sample` falla en cada disparo |
| clock lock de GPU | `systemctl is-active` de la unit | una unit que arranco y no aplico el limite |
| earlyoom | `systemctl is-active` del servicio | un earlyoom vivo con la punteria mal puesta |

## Por que importa, y no es hipotetico

El 2026-09-25 la cuarta fila -- la termica -- se midio **mintiendo al reves**:
declaraba FALTA sobre un instrumento activo que escribia 711 muestras por
hora, porque leia una ruta borrada. Se arreglo porque miraba el dato y el dato
se podia comprobar. Las tres de arriba no tienen ni eso: dicen ARMADO mientras
`systemctl` diga `active`, y no hay forma de que salgan mal por la razon
correcta.

Un gate que no puede salir negativo por el motivo que vigila no es un gate.

## Como se cierra

Cada una contra su propio artefacto, que en las tres existe:

1. **muestreo**: la fila mas nueva de `$SAMPLES/<hoy>.jsonl` de hace menos de
   dos intervalos. bb ya sabe leer ese fichero.
2. **clock lock**: `nvidia-smi --query-gpu=clocks.applications.graphics` o los
   limites vigentes, contra los 300-2800 MHz que la unit declara aplicar.
3. **earlyoom**: su linea de arranque en el journal ya imprime umbrales y el
   regex de procesos a evitar; comprobar que lo que imprimio coincide con lo
   que `adopted/system-config/etc_systemd_system_earlyoom.service.d_override.conf`
   declara.

Cada una con su control negativo, que aqui es barato: un fichero de muestras
viejo, unos relojes fuera de rango, un override cambiado.

## Limite declarado

Esto NO cierra el riesgo que SPEC ya declara sobre esta fila: quedaria por
comprobar que el instrumento mide lo que dice, no solo que escribio algo
reciente. Un `bb sample` que escriba basura fresca seguiria pasando.
