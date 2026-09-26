---
id: DEBT-GATE-EFFECTIVENESS-SIN-ESTADO-LEGAL
kind: debt
title: "`gate_effectiveness` bloquea a `telemetry_prune` esté declarado o no: sus dos mitades leen columnas distintas"
status: open
severity: P1
origin: detected
detector: {"rule": "gate_effectiveness --gate", "confidence": 1.0}
satd_family: CONTRADICTORY_GATE
created: 2026-09-26
close_check: {"cmd": "python3 .simplecode/run.py simplecode.verification.gate_effectiveness --root . --gate", "expect": "exit_zero", "porque": "el sujeto ES el gate, y hoy sale 1 en las DOS configuraciones posibles. Cuando exista una legal, este comando sale 0 -- no hace falta que nadie escriba que aterrizo, porque el propio gate lo dira. Control negativo corrido y registrado abajo: sale 1 con la declaracion y sale 1 sin ella."}
---

## Que pasa

Al sincronizar el kit a 8.6.3 el 2026-09-26, `gate_effectiveness --gate` empezó
a bloquear el push por `telemetry_prune`, y **bloquea en los dos estados
posibles**. Medido, no deducido:

```
declaración PRESENTE  -> DECLARACIONES REFUTADAS POR EL SUJETO: 1      rc=1
                         "declared inapplicable, but this repo's telemetry
                          records bloqueos_reales=0 hallazgos=4 controles=0.
                          The declaration is refuted by the subject; delete it."

declaración BORRADA   -> INSTRUMENTOS SIN CAPTURAS TRAS 10+ CORRIDAS: 1  rc=1
                         "NOT CLEAN: 1 organ(s) with 10+ runs and zero catches."
```

No hay tercera configuración. El gate pide borrar la declaración y condena al
órgano por no tenerla.

## La causa, leída en la fuente del propio kit

Las dos mitades deciden con columnas distintas.

`_clasificar` **quitó `hallazgos` a propósito** del test de mudez, y su comentario
dice por qué:

> `hallazgos` used to be a third clause here and has been dropped, because
> `gate_runner` fabricated it as `int(rc != 0)`: measured 2026-09-05 over the
> whole file, 0 of 9011 rows had it differ from the block bit, so it was a
> verbatim copy of `bloqueos` and added nothing.

`_refutadas`, en el mismo fichero, **sí** lo usa:

```python
if c and (c["bloqueos_reales"] or c["hallazgos"] or c["controles"]):
    ... "The declaration is refuted by the subject; delete it."
```

Así que para un órgano **advisory** cuyo canal de hallazgos SÍ funciona
-- `bloqueos_reales=0`, `hallazgos=4` -- una mitad lo declara mudo y la otra lo
declara probado. Las dos condenan.

Y la premisa que justificó quitar la cláusula es **falsa en este repo**: aquí
`hallazgos` NO es una copia del bit de bloqueo. `telemetry_prune` tiene 0
bloqueos y 4 hallazgos. La medición de 2026-09-05 describía el estado del
emisor de entonces, no una propiedad del campo.

## Por qué `telemetry_prune` cae justo ahí

Es advisory por construcción, y eso está medido:

- su entry en el config canónico es `bash -c '... --gate || true'`;
- su propio `name` dice `"(advisory)"`;
- corrido a mano el 2026-09-26: `rc=0`, con
  `[telemetry] would archive 843 row(s) older than 7d from telemetry.jsonl;
  keeping 3016` y `OK: under the declared threshold`.

O sea: informa y no bloquea, que es su diseño. Su columna `bloqueos` es 0 para
siempre, y su columna `hallazgos` se llena de verdad. Es exactamente la
combinación que las dos mitades leen al revés.

## Lo que este repo hizo antes de abrir esto, para no confundir el sujeto

1. La declaración anterior decía que el órgano era **inaplicable** ("no está
   cableado como compuerta con nombre aquí"). El gate la refutó con la medida
   delante y mandó borrarla. Se borró: era falsa.
2. Se escribió otra que dice lo que sí es cierto -- **consultivo, no ciego** --
   y el gate la refutó igual, porque `_refutadas` no distingue "no aplica" de
   "no bloquea por diseño". Las dos van al mismo fichero y reciben el mismo
   trato.
3. Y se comprobó que borrarla otra vez tampoco pasa.

El paso 2 importa: el problema no es que la declaración esté mal escrita. Es que
`organ_inapplicable.json` sólo tiene una forma de decir "este órgano calla por
una razón buena", y hay dos razones distintas.

## Como se cierra

Aguas arriba, en `simplecode/verification/gate_effectiveness.py`, con las dos
mitades de acuerdo. Cualquiera de estas lo hace:

- que `_refutadas` no cuente `hallazgos` para un órgano cuya entry va envuelta
  en `|| true` -- un advisory no puede refutarse por informar, que es su trabajo;
- o que `organ_inapplicable.json` admita declarar CONSULTIVO como clase distinta
  de INAPLICABLE, y que `_clasificar` la saque del conjunto mudo;
- o que `_clasificar` vuelva a mirar `hallazgos` ahora que el emisor ya no lo
  fabrica -- pero eso hay que medirlo antes, porque su comentario documenta un
  caso que la cláusula estaba arreglando al quitarse (un órgano cuyos bloqueos
  fueron todos `false_positive`).

**No se cierra escribiendo nada en blackbox.** Lo único que este repo puede hacer
es no fingir que hay una configuración válida.

## Limite declarado

Esta ficha no dice que `gate_effectiveness` esté mal diseñado: dice que sus dos
mitades discrepan **para esta combinación**, y que la combinación existe aquí.
Cabe que la respuesta correcta aguas arriba sea que `telemetry_prune` deje de ir
envuelto en `|| true` y pase a bloquear, con lo que su columna `bloqueos` se
llenaría y el conflicto desaparecería sin tocar este gate. Eso también cierra
esto, y es la salida que no se puede decidir desde un satélite.
