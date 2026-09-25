---
id: DEBT-TRES-CHEQUEOS-POR-IS-ACTIVE
kind: debt
title: "Tres filas de `bb status` leen si la unit esta activa, no si el instrumento trabaja"
status: done
severity: P2
origin: asserted
satd_family: WEAK_VERIFICATION
created: 2026-09-25
closed_at: 2026-09-25
close_check: {"cmd": "python3 -m pytest tests/test_bb_bash.py -k 'muestreo_por_su_dato or clock_lock or punteria' -q", "expect": "exit_zero"}
evidence: {"pass": "tasks/evidence/DEBT-TRES-CHEQUEOS-POR-IS-ACTIVE/pass.txt", "fail": "tasks/evidence/DEBT-TRES-CHEQUEOS-POR-IS-ACTIVE/fail.txt", "e2e": "tasks/evidence/DEBT-TRES-CHEQUEOS-POR-IS-ACTIVE/e2e.txt"}
reason: "Las tres filas leen ahora el artefacto del sujeto y no el estado de la unit: la muestra mas fresca del dia, la confirmacion que imprimio el driver contrastada con los argumentos que la unit declara, y las dos regex de punteria que earlyoom imprimio al arrancar. Siete tests, cuatro controles negativos corridos."
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


## Root Cause

`bb status` tenia una regla propia -- **por sus datos, no por la unit** -- y la
cumplia en cuatro filas de siete. Las tres restantes se quedaron con
`systemctl is-active` porque en su momento no se busco que artefacto dejaba
cada instrumento; se asumio que no habia ninguno.

Lo habia en las tres. El muestreo deja su fichero del dia, el clock lock deja
la linea que nvidia-smi imprime al aplicarlo, y earlyoom imprime sus dos regex
de punteria al arrancar. Ninguno hacia falta inventarlo.

## Regression Test

Siete tests en `tests/test_bb_bash.py`. Los negativos montan el estado que
antes era indistinguible de sano:

- muestreo: directorio de muestras vacio -- un timer activo que no escribe;
- clock lock: el driver confirmando **otro** rango (2600) que el declarado
  (2800) -- un limite aplicado que no es el que se pidio;
- clock lock: journal mudo -- una unit `active` que fallo al aplicar;
- earlyoom: arrancado de serie, sin las dos regex -- activo y matando lo que
  le parezca;
- earlyoom: con UNA sola regex -- preferir a quien matar sin proteger a quien
  no tocar deja el escritorio expuesto, y son dos propiedades.

Y los positivos, para que no sean chequeos que no puedan salir en verde.

## Verification Evidence

Antes: `armado: 14  falta: 1`, con tres filas que no podian salir mal por el
motivo que vigilaban.
Despues: `armado: 15  falta: 0`, y las tres pueden.

```
ARMADO  blackbox: muestreo de apps/zombis (dato de hace <2 min)
ARMADO  clock lock de GPU (declarado 300,2800 MHz, confirmado por el driver)
ARMADO  earlyoom con la punteria puesta (prefiere y evita)
```

Un rotulo se corrigio de camino: decia "el driver confirmo 300,2800 MHz" tambien
cuando el driver habia confirmado 2600, o sea afirmaba en el titulo justo lo que
el chequeo estaba negando.

## Limites declarados

- El driver **no expone** el rango bloqueado. Medido sobre el 580.178.04:
  `nvidia-smi -q -d CLOCK` da "Max Clocks: 3003 MHz", el maximo del hardware, y
  ningun campo dice 2800. Lo que se lee es la confirmacion del journal de ESTE
  arranque: si alguien cambia el lock a mano despues, no se ve hasta el
  siguiente arranque.
- El chequeo del muestreo mira que el fichero se escribio hace menos de dos
  minutos, no que su contenido sea correcto. Un `bb sample` que escriba basura
  fresca sigue pasando. Es la misma frontera que SPEC ya declara para sar y el
  monitor de memoria.
- earlyoom: se comprueba que las dos regex LLEGARON, no que su contenido sea el
  que enable-privileged.sh declara. Comparar el texto exacto ataria bb a la
  redaccion del regex y lo rompería cada vez que se afine.
