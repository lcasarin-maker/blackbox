---
id: DEBT-GATE-EFFECTIVENESS-SIN-ESTADO-LEGAL
kind: debt
title: "gate_effectiveness bloqueaba telemetry_prune por leer columnas distintas"
status: done
closed_at: 2026-09-27
evidence:
  pass: tasks/evidence/DEBT-GATE-EFFECTIVENESS-SIN-ESTADO-LEGAL/pass.txt
  fail: tasks/evidence/DEBT-GATE-EFFECTIVENESS-SIN-ESTADO-LEGAL/fail.txt
  e2e: tasks/evidence/DEBT-GATE-EFFECTIVENESS-SIN-ESTADO-LEGAL/e2e.txt
closure_type: relocated_prior_verification
reason: "el arreglo lo hizo el kit aguas arriba (8.6.3 -> 8.6.5) y lo unico que este repo tenia que hacer -- borrar la declaracion de telemetry_prune de .simplecode/organ_inapplicable.json-- es DATOS, no codigo. Aterrizo en el commit anterior con su evidencia y las dos direcciones medidas; este commit solo mueve la ficha, que es lo que genuine-task-closure prescribe para este caso. No se anadio un test sintetico: el regression test de esto es el propio gate, cableado en el pre-push."
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

## CERRADA 2026-09-27 -- el arreglo aterrizo en el kit 8.6.5

### Root Cause

Las dos mitades de `gate_effectiveness` decidian con columnas distintas.
`_clasificar` habia quitado `hallazgos` del test de mudez con la premisa de que
era copia del bit de bloqueo; `_refutadas` si lo usaba. Un organo consultivo con
`bloqueos_reales=0` y `hallazgos=4` caia justo en medio: una mitad lo declaraba
mudo, la otra lo declaraba probado, y las dos condenaban.

La premisa era falsa, y la flota lo midio despues de que esta ficha se abriera:
226 de 33 865 filas (0.67 %) tienen `hallazgos` distinto del bit de bloqueo, y
estan en los organos consultivos -- exactamente esta clase.

### Regression Test

El propio gate, que corre en cada `pre-push`. No hace falta un test nuevo: el
`close_check` de esta ficha ES el gate, y si el kit vuelve a la forma anterior el
push se bloquea igual que bloqueaba. Un test escrito aqui seria una copia peor
del instrumento que ya esta cableado.

Lo que SI quedo: la entrada `telemetry_prune` borrada de
`.simplecode/organ_inapplicable.json`. Si el organo volviera a necesitar
declaracion, el gate lo dira.

### Verification Evidence

`tasks/evidence/DEBT-GATE-EFFECTIVENESS-SIN-ESTADO-LEGAL/aterrizaje-8.6.5.txt`,
con las dos direcciones corridas en 8.6.5:

```
declaracion PRESENTE -> DECLARACIONES REFUTADAS POR EL SUJETO: 1   rc=1
declaracion BORRADA  -> INSTRUMENTOS SIN CAPTURAS TRAS 10+: 0      rc=0
en 8.6.3 las dos direcciones daban rc=1, y eso es lo que abrio la ficha
```

El control negativo es ese par, no el rc=0 suelto: el mismo comando en el mismo
kit sale 1 con la declaracion puesta y 0 sin ella, asi que el gate sigue mirando.

### Lo que este cierre NO afirma

No afirma que blackbox arreglara nada: el trabajo lo hizo el kit, y esta ficha
solo registro la contradiccion con su medida en las dos direcciones y la reporto
aguas arriba. La decision durable que gobierna eso -- un defecto del kit se
reporta, no se rodea ni se arregla desde un satelite-- esta en `DECISIONS.md` y
sigue en pie. El precio que se pago fue tener el push bloqueado un dia.
