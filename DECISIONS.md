# DECISIONS

Durable decisions only — not a log. One entry per decision, with the reason it was
taken and what it rules out.

Lo que NO va aquí: una decisión sobre una ficha concreta, que vive en esa ficha.
Meter cada voto aquí lo convierte en el log que la línea de arriba prohíbe.

---

## 2026-09-25 · Un `xfail` usado como señal de aterrizaje asierta el VEREDICTO del gate, nunca un interno

**La decisión.** Cuando un test existe para avisar de que un arreglo aguas arriba
aterrizó — `xfail(strict=True)` que debe pasar a `XPASS` y poner la suite roja —
tiene que asertar sobre lo que el gate **decide**, no sobre una pieza interna a la
que el gate llegue de paso.

**Por qué, medido.** `tests/test_pii_scan_systemd.py` prometía en su docstring:
«el día que el kit se sincronice arreglado, los tres casos pasan a XPASS y la
suite se pone ROJA, que es la señal». El arreglo aterrizó en el kit 8.6.3 y la
suite dio `3 passed, 3 xfailed`. Verde, en silencio, el mismo día en que el
bloqueador dejó de existir.

La causa: asertaba `CORREO.search(unit)`, el patrón. El patrón no cambió — en
8.6.3 es byte a byte el de 8.5.1 y sigue cazando las tres cadenas. Lo que cambió
fue el veredicto, vía una función nueva, `es_unidad_systemd`. Un interno puede
quedarse quieto mientras el comportamiento cambia entero.

**Qué descarta.** Descarta dar por buena una señal de aterrizaje sin un control de
que suena. Un `xfail` estricto sobre el sujeto equivocado es peor que no tener
señal: promete un aviso que no llega, y quien lo escribió deja de mirar. Desde
ahora un test de esta clase lleva su propio control — se simula la regresión y se
comprueba que el test se pone rojo.

---

## 2026-09-25 · Un criterio que no puede salir positivo sin matar al sujeto no es un criterio

**La decisión.** La regla de la casa dice que una verificación que no puede salir
negativa no verifica. Su gemela vale igual: una que no puede salir **positiva**
tampoco. Un `close_check` así se reescribe, y el hecho que lo hacía imposible se
separa en lo que es.

**Por qué, medido.** El `close_check` de `DEBT-TECHOS-SIN-CALIBRAR` exigía que los
techos compusieran restando una reserva de GPU de 86 GiB. Sobre 121.1 GiB de
máquina eso deja 35.1 para todos los cgroups, y `app.slice` **sola** picó 39.8
(`memory.peak` = 42731823104). No había reparto que lo satisfaciera sin poner el
techo del escritorio por debajo de lo que el escritorio ya usó.

Y los 86 GiB eran un transitorio de **cuatro minutos** — ocho workers de
`pytest-xdist` — presentado como si fuera un compromiso permanente.

**Qué descarta.** Descarta sumar en la misma cuenta un compromiso que el kernel
aplica y una observación que no aplica nadie. Se separan: la aritmética compone
contra el suelo comprometido (derivado, el p95 de la serie), y la excursión — que
ningún cgroup acota — se **firma** con dueño y caducidad o el gate queda rojo.
Descarta también aflojar un criterio para que pase: partirlo no lo puso en verde,
y ese es el control de que no fue una amnistía.

---

## 2026-09-25 · Un techo de cgroup sale de una serie, y el instrumento se niega si no la hay

**La decisión.** Ningún techo de memoria se elige a ojo. Lo propone
`tools/calibra_techo_slice.py` desde la serie que `bb sample` guarda, o no se
pone. El módulo se niega mientras la serie no lo sostenga, y dice qué le falta.

**Por qué, medido.** Cuando quedó un solo eslabón para cerrar
`DEBT-TECHOS-SIN-CALIBRAR` — `system.slice` sin techo, 5.3 GiB de holgura para
ponérselo — lo único disponible para elegir el número era su `memory.peak` de UN
arranque: 2.8 GiB en 8 h 19 min. El techo de `docker.slice` salió de 18 944
muestras, y ese es el listón. Lo único que impedía elegir 4G porque parece
razonable era la buena voluntad de quien lo hiciera.

**Qué descarta.** Descarta el número plausible. Y descarta también que «hay
muchas muestras» baste: el freno que de verdad protege es que el **máximo haya
dejado de crecer**, porque una serie que aún sube no ha visto el peor caso y un
techo puesto ahí se queda corto por construcción. Ese freno puede decir «todavía
no» con 100 000 muestras.

---

## 2026-09-26 · Una declaración que el sujeto refuta se borra; no se renueva con mejor redacción

**La decisión.** Cuando la telemetría del propio repo contradice una declaración
de inaplicabilidad, la declaración se borra. Si además resulta que lo que se
quería declarar era otra cosa, se escribe lo que sí es cierto — y si el
instrumento tampoco admite eso, se abre ficha en vez de insistir con la redacción.

**Por qué, medido.** `telemetry_prune` estaba declarado inaplicable con el motivo
«no está cableado como compuerta con nombre aquí». `gate_effectiveness` lo refutó:
`declared inapplicable, but this repo's telemetry records hallazgos=1`. Se borró.
Se reescribió diciendo lo cierto — **consultivo**, con su `|| true` y su
`"(advisory)"` medidos — y la refutó igual, porque `organ_inapplicable.json` sólo
tiene una forma de decir «calla por buena razón» y hay dos razones distintas.

**Qué descarta.** Descarta el reflejo de renovar una declaración caducada con las
mismas palabras. Y descarta tratar «no aplica aquí» y «no bloquea por diseño» como
la misma cosa: la primera era falsa y la segunda es cierta, y confundirlas es lo
que hizo que la corrección no funcionara.

---

## 2026-09-26 · Un allowlist que no exime nada se borra, con su control de retirada

**La decisión.** Una válvula — allowlist, exención, supresión — se comprueba
**por retirada**: se quita y se mide si cambia el veredicto. Si no cambia, se
borra, y la medida va en el commit.

**Por qué, medido.** `tasks/pii_allow.txt` llevaba tres afirmaciones firmadas sobre
nombres de unit de systemd. Con el arreglo del kit 8.6.3 en su sitio:

```
CON el fichero -> revisados=163  hallazgos=0
SIN el fichero -> revisados=162  hallazgos=0
el 2026-09-25, antes del arreglo:  SIN el fichero -> 8 hallazgos
```

**Qué descarta.** Descarta dejar una válvula muerta «por si acaso». Un allowlist
que no exime nada es una afirmación firmada sobre un riesgo que ya no existe, y el
siguiente que lo lea creerá que hace falta. El riesgo de borrarlo — que un sync
revierta el arreglo — se cubre con el test, no con el fichero.

---

## 2026-09-26 · Una ficha HARVEST decidida se ARCHIVA; `open` + `accepted` no es un estado terminal

**La decisión.** Una sugerencia de cosecha cuya decisión ya está registrada pasa a
`tasks/done/`. Un descarte cierra con `void_wontfix`; una adopción, con
`adopted_prior_implementation` apuntando a la ficha que lleva el código.

**Por qué, medido.** 34 fichas HARVEST cumplían su `close_check` desde el
2026-09-09 con `status: open`. El repo ya tenía 26 precedentes de cerrarlas, así
que la convención existía; lo que faltaba era aplicarla. Dejarlas abiertas hacía
que cada `/debt` reportara 34 decisiones ya tomadas y que el ranking las tuviera
dominado — el mismo defecto que `/debt` existe para cerrar, por el otro extremo.

**Qué descarta.** Descarta leer la forma «abierta + aceptada» que
`harvest_decision` admite como si fuera un destino. Es una forma válida de
tránsito, no de reposo. Y descarta cerrar sin las secciones que el contrato exige:
en un descarte, Root Cause / Regression Test / Verification Evidence dicen que no
hay código que pueda regresar, que lo que vigila es el disparador de reapertura, y
que el chequeo mira el REGISTRO y no una función.

---

## 2026-09-26 · Un defecto del kit se reporta aguas arriba; blackbox no lo arregla ni lo rodea

**La decisión.** Cuando un gate de la flota deja a este repo sin configuración
válida, se mide en las dos direcciones, se abre ficha, y se reporta a la sesión
dueña del kit. No se arregla desde aquí, y no se usa `SKIP` ni `--no-verify`
mientras tanto — el trabajo se queda local.

**Por qué, medido.** El kit 8.6.3 dejó a `telemetry_prune` sin estado legal:
declarado se refuta por `hallazgos=4`, borrado se condena por `bloqueos=0`. Ambas
salidas rc=1. La causa, leída en la fuente: `_refutadas` usa `hallazgos` y
`_clasificar` lo quitó a propósito, con una premisa —«es copia del bit de
bloqueo»— que la flota midió después como falsa: 226 de 33 865 filas (0.67 %)
difieren, en los órganos consultivos.

**Qué descarta.** Descarta arreglar el kit desde un satélite, que multiplica la
versión del arreglo por el número de satélites. Y descarta la salida cómoda:
`SKIP` silencia el gate entero, así que si en la misma corrida tiene razón sobre
otro órgano no se ve. El precio aceptado es que el push queda bloqueado —
`DEBT-GATE-EFFECTIVENESS-SIN-ESTADO-LEGAL` lo registra con su medida.
