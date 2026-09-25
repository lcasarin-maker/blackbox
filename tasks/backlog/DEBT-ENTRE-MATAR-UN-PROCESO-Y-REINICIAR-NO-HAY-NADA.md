---
id: DEBT-ENTRE-MATAR-UN-PROCESO-Y-REINICIAR-NO-HAY-NADA
kind: debt
title: "El unico remedio armado contra el caso medido es reiniciar la maquina entera"
status: open
severity: P2
origin: detected
detector: {"rule": "bb status", "confidence": 1.0}
satd_family: MISSING_COVERAGE
created: 2026-09-25
close_check: {"cmd": "grep -q 'remedio intermedio CALIBRADO' tasks/done/DEBT-ENTRE-MATAR-UN-PROCESO-Y-REINICIAR-NO-HAY-NADA.md", "expect": "exit_zero", "porque": "cierra sobre una CALIBRACION que todavia no existe, no sobre codigo que se pueda escribir hoy. Un guardia nuevo con un umbral inventado hoy mata un proceso Y ADEMAS afirma haber tenido razon -- peor que no tenerlo. Mismo patron que DGX-438: cierra cuando alguien ESCRIBE que aterrizo, con las dos mitades medidas."}
---

## Que dice el informe hoy

`bb status` imprime, y lleva imprimiendolo desde que se anadio la fila:

```
  CIEGO     earlyoom ante agotamiento de memoria unificada
            su umbral lee MemAvailable, que marco 56% durante los congelamientos del 2026-09-22/23
```

`armado: 15    falta: 0    ciego: 1`

## Por que earlyoom no puede ver esto

Lee dos senales, `MemAvailable` y `SwapFree`, y ninguna de las dos se movio.
Medido en los congelamientos del 22 y el 23: `MemAvailable` marco **56 %**
durante 17 horas mientras `PSI memory full` estaba en **98-99 %**. earlyoom
disparo **una vez** (05:51:40) y nunca mas.

No es un defecto de configuracion: es que la memoria unificada de la GPU no la
contabiliza ningun cgroup y apenas la toca `MemAvailable`. Contra un OOM
clasico earlyoom sigue sirviendo, y por eso sigue armado.

## Lo que SI esta cubierto, y con que

`bin/bb-usable` lee `/proc/pressure/memory` directamente, actua sobre
`full avg10` sostenida, y su corte (10 % durante 300 s) esta **validado por
`tools/calibra_psi.py` contra los TRES congelamientos reales de esta maquina**
-- no es un numero elegido. Esta armado, y `bb status` lo imprime como tal.

O sea: la maquina no esta desprotegida. Esta ficha no es un agujero de
cobertura.

## Lo que falta, que es otra cosa

El remedio de `bb-usable` es `FailureAction=reboot-immediate`. El de earlyoom
es matar un proceso. **Entre "muere un proceso" y "se reinicia la maquina
entera" no hay nada armado**, y el caso que se midio TRES veces cae del lado
caro: el unico remedio que lo alcanza es el mas destructivo que existe.

Un guardia que matara al proceso que se come la memoria unificada antes de que
haga falta reiniciar es lo que falta. No existe.

## Por que esto no tenia ficha hasta hoy

La fila CIEGO se venia reportando en cada corrida de `bb status`, y el control
compensatorio (`bb-usable`) estaba nombrado **solo en un comentario de
`bin/bb`**. Una brecha que se declara en un informe y no se escribe como deuda
es exactamente lo que la regla prohibe: declararla no la paga. Contarla como
`ciego: 1` corrida tras corrida la vuelve paisaje.

## Como se cierra, con las dos mitades

1. **Dispara sobre el sujeto real**: sobre los tres congelamientos que
   `tools/calibra_psi.py` ya usa como sujeto, el guardia tiene que haber
   elegido un proceso antes del punto en que `bb-usable` habria reiniciado.
2. **Control negativo, corrido y no argumentado**: sobre las 19 045 muestras de
   operacion normal ya acumuladas, cero disparos. Sin esta mitad el arreglo es
   peor que la brecha -- un guardia que mata por un umbral inventado hoy mata
   un proceso y ademas afirma haber tenido razon.

El corte no se inventa aqui: se calibra igual que se calibro el de
`bb-usable`, contra medidas propias.

## Limite declarado

Esta ficha **no prueba que el remedio intermedio sea lo que hacia falta**. Cabe
que para esta maquina el reinicio SEA proporcionado y que un asesino
intermedio solo anada una forma nueva de equivocarse. Decidir eso tambien
necesita la medicion: cuanto tiempo pasa entre el punto en que un proceso ya
es identificable como el culpable y el punto en que `bb-usable` reinicia. Si
esa ventana es de segundos, no hay remedio intermedio que quepa, y esta ficha
se cierra escribiendo ESO.
