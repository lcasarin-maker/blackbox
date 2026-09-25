---
id: DEBT-SIN-ARNES-DE-MUTACION
kind: debt
title: El runner de mutacion del kit no alcanza a ningun satelite: 0 de 374 tests resuelven su sujeto
status: done
severity: P2
origin: asserted
satd_family: LOST_VERIFICATION
created: 2026-09-25
closed_at: 2026-09-25
close_check: {"cmd": "python3 -m tools.mutacion_alcanza --root .", "expect": "exit_zero", "porque": "mide el sujeto de ESTA ficha -- que el runner del kit encuentre que mutar aqui -- y no la calidad de un test. `mutation_verify --gate` sale 1 igual con WEAK que con COULD_NOT_RUN, y WEAK es el veredicto normal porque muta el modulo entero y corre UN test: usarlo seria un criterio que no puede pasar nunca."}
evidence: {"pass": "tasks/evidence/DEBT-SIN-ARNES-DE-MUTACION/pass.txt", "fail": "tasks/evidence/DEBT-SIN-ARNES-DE-MUTACION/fail.txt", "e2e": "tasks/evidence/DEBT-SIN-ARNES-DE-MUTACION/e2e.txt"}
reason: "El arreglo aterrizo aguas arriba, en simplecode 8.3.1 y 8.3.2, y este repo pasa de 0 a 8 de 10 ficheros de test resolviendo su sujeto. tools/mutacion_alcanza.py guarda esa condicion para que no vuelva a perderse en la proxima sincronizacion del kit."
---

## Que pasa

Con `tools/atom_gpu_telemetry.py` vinieron de Atlas sus dos arneses de
mutacion -- `run_mitigacion_carga_mutation.py` (89 lineas) y
`run_alarm_mark_mutation.py` (181) -- que rompen el modulo a proposito, una
mutacion por vez, y exigen que la suite MUERA. Un test que pasa igual con el
codigo roto no prueba nada, y esos arneses eran lo unico que lo comprobaba
sobre la compuerta de carga y sobre el marcado de alarmas termicas.

**El reparto correcto, por funcion y no por nombre:**

| pieza | que es | de quien |
| --- | --- | --- |
| los dos arneses | tienen SUJETO: mutan `atom_gpu_telemetry.py` | **de este repo**, que es donde vive el sujeto |
| `run_injection_mutation.py` (617 lineas, 49 usuarios en Atlas) | no tiene sujeto: es el METODO -- mutar, `compile()` antes de gastar maquina, correr pytest, exigir `failed` y no `error`, restaurar verificando sha256 | **de ninguno de los dos repos: del kit** |

Y el kit **ya trae uno**: `simplecode/verification/mutation_verify.py`, 390
lineas, vendorizado en los dos satelites.

## El hallazgo: ese runner del kit no alcanza a ningun satelite

Medido el 2026-09-25 con su propia funcion `resolve_source_for_test`:

```
blackbox:  0 de   9 ficheros de test resuelven su sujeto
Atlas:     0 de 365
```

La causa esta en el codigo del kit: el resolutor exige `root/src/` y deriva de
ahi los nombres de paquete locales. **blackbox no tiene `src/`** -- su codigo
vive en `tools/` y `bin/` -- y el `src/` de **Atlas solo contiene `images/`**,
sin un paquete Python dentro. Asi que devuelve `None` siempre, y el llamador lo
reporta como `COULD_NOT_RUN`.

Control negativo corrido, que es lo que convierte esto en hallazgo y no en
sospecha: el mismo runner sobre el repo del kit, que SI tiene `src/simplecode/`,
resuelve sus tests sin problema. O sea funciona donde nacio y no donde se
vendoriza.

Eso reencuadra los 617 lineas de Atlas: **no eran duplicacion caprichosa**, eran
suplir un instrumento del kit que no llega. Y reencuadra al propio
`mutation_verify`: un gate vendorizado en dos repos donde no puede capturar nada
es un defecto del instrumento, nunca evidencia de que el sujeto este limpio.

## Lo que se pierde mientras tanto, dicho sin adornos

La verificacion por mutacion de dos caminos del gate termico. No eran gates de
CI -- se corren a mano -- pero eran lo unico que respondia "¿estos tests
cazarian el bug?" sobre la mitigacion. Lo que queda son 137 tests y el 100 % de
cobertura de lineas, que contesta otra pregunta: que se EJECUTO, no que un
fallo se cazaria.

Los tres ficheros viven en la historia de Atlas, recuperables:

```
git -C ~/projects/Atlas show 82b27781^:tools/run_mitigacion_carga_mutation.py
git -C ~/projects/Atlas show 82b27781^:tools/run_alarm_mark_mutation.py
git -C ~/projects/Atlas show HEAD:tools/run_injection_mutation.py
```

## Root Cause

El kit envia `simplecode/verification/mutation_verify.py` a cada satelite, y
su resolutor exigia una disposicion `root/src/` que este repo no tiene -- su
codigo vive en `tools/` y `bin/`. Devolvia `None` siempre, el llamador lo
reportaba como COULD_NOT_RUN, y nadie podia correr mutacion aqui.

Medido el 2026-09-25 con la propia funcion del modulo: blackbox **0 de 9**,
Atlas **0 de 365**, simplecode **158 de 164** -- funcionaba donde nacio y no
donde se vendoriza. Eso reencuadra las 617 lineas de
`run_injection_mutation.py` de Atlas: no eran duplicacion caprichosa, eran
suplir un instrumento del kit que no llegaba.

## Regression Test

```
python3 -m tools.mutacion_alcanza --root .
python3 -m pytest tests/test_mutacion_alcanza.py -q
```

El primero es el criterio de esta ficha. El segundo prueba el guardian en sus
dos sentidos, incluido un repo montado a proposito para que NO alcance.

## Verification Evidence

- `pass`: `8 de 10 ficheros de test resuelven su sujeto`, rc=0.
- `fail`: el control negativo CORRIDO -- un repo cuyos tests no importan modulo
  local da rc=1 y lo dice -- mas la medicion del sujeto antes del arreglo.
- `e2e`: 23 sentencias al 100 %, 4 tests, y el runner dando veredicto de
  verdad sobre un test de aqui en vez de COULD_NOT_RUN.

## Como se cerro

Aguas arriba, que es donde estaba el defecto: `simplecode` 8.3.1 hizo
`source_roots()` agnostico de disposicion y corrigio la especificidad, y 8.3.2
el ValueError con rutas relativas que el primero tapaba. Este repo paso de
**0 de 9** a **8 de 10** ficheros de test resolviendo su sujeto.

`tools/mutacion_alcanza.py` guarda esa condicion. Su criterio NO es
`mutation_verify --gate`: ese sale 1 igual con WEAK que con COULD_NOT_RUN, y
WEAK es el veredicto normal aqui -- medido sobre cuatro tests de tres modulos
distintos, los cuatro WEAK, porque el runner muta el modulo entero y corre UN
test. Un criterio que no puede pasar nunca es tan inservible como uno que no
puede fallar.

## Lo que sigue sin existir, dicho sin adornos

Los dos arneses de mutacion de `atom_gpu_telemetry.py` no volvieron. Con el
runner ya funcionando se pueden reconstruir sobre el del kit, y eso es trabajo
ordinario; lo que esta ficha cierra es que ya hay con que hacerlo.

## Como se cierra (version original de la ficha)

**Aguas arriba, en `simplecode`, no aqui.** `resolve_source_for_test` tiene que
dejar de suponer `src/` y derivar los paquetes locales de lo que el proyecto ya
declara -- `coverage_targets` en `corpus_exempt.yaml`, o los paquetes de
`pyproject.toml` -- que es como el resto del kit se adapta a cada satelite.
Copiar el runner a este repo seria duplicar el metodo en vez de arreglarlo, y
dejaria a Atlas con el mismo agujero.

Con eso hecho, los dos arneses vuelven aqui expresados sobre el runner del kit,
y el `close_check` de arriba deja de dar `COULD_NOT_RUN`.

Control negativo obligatorio del arreglo: un mutante que la suite NO caza tiene
que reportarse como SUPERVIVIENTE. Un arnes donde todos los mutantes mueren
siempre no discrimina un test bueno de uno decorativo -- y un resolutor que
devuelve `None` los mata a todos por ausencia, que es el fallo de hoy.
