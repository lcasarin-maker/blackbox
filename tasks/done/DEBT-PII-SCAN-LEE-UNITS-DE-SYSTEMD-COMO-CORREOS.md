---
id: DEBT-PII-SCAN-LEE-UNITS-DE-SYSTEMD-COMO-CORREOS
kind: debt
title: "`pii-scan` lee un nombre de unit de systemd como una direccion de correo de un tercero"
status: done
closure_type: relocated_prior_verification
closed_at: 2026-09-26
severity: P2
origin: detected
detector: {"rule": "simplecode/pii-scan", "confidence": 1.0}
satd_family: FALSE_POSITIVE
created: 2026-09-25
close_check: {"cmd": "grep -q 'unit de systemd deja de casar' tasks/done/DEBT-PII-SCAN-LEE-UNITS-DE-SYSTEMD-COMO-CORREOS.md", "expect": "exit_zero", "porque": "el arreglo vive aguas arriba, en simplecode, y esta ficha no lo puede provocar. Mismo patron que DGX-438: cierra cuando alguien ESCRIBE que aterrizo. La senal automatica la da tests/test_pii_scan_systemd.py, que lleva xfail(strict=True) y pondra la suite ROJA el dia que el kit se sincronice arreglado."}
evidence: {"pass": "tasks/evidence/DEBT-PII-SCAN-LEE-UNITS-DE-SYSTEMD-COMO-CORREOS/aterrizaje-8.6.3.txt"}
reason: "relocated_prior_verification: el arreglo aterrizo aguas arriba, en el kit 8.6.3, y llego a este repo con el sync del commit 7639ce6 -- un commit ANTERIOR. Este cierre solo mueve la ficha y anade la evidencia de que se verifico sobre el runtime: `es_unidad_systemd` da True para las tres units y False para las dos direcciones reales, y el gate ENTERO da hallazgos=0 sobre un fichero con una unit y una ruta de cgroup. La unit de systemd deja de casar como direccion, y el detector NO se apago -- las dos mitades que la ficha exigia."
---

## Que pasa

`pii-scan` bloqueo el push de este repo **dos veces** el 2026-09-25, sobre
cadenas que no son datos de nadie:

| cadena | donde | como la enmascaro el gate |
| --- | --- | --- |
| `org.gnome.Shell@x11.service` | una tabla de consumo de CPU en una ficha | `org.*********************ce` |
| `user@1000.service` | dentro de una ruta de `/sys/fs/cgroup` en un `close_check` | `user***********ce` |

Su patron es

```
CORREO = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
```

y una unit de systemd **con instancia** lo casa igual que una direccion: parte
local, arroba, "dominio", punto, "tld". Medido contra el modulo real del kit:

```
user@1000.service               -> CAZADO
org.gnome.Shell@x11.service     -> CAZADO
getty@tty1.service              -> CAZADO
user@.service                   -> limpio   (plantilla, sin instancia)
<una direccion de verdad>       -> CAZADO   (y debe serlo)
```

Mirando solo la cadena no hay forma de distinguirlas.

## Esta misma ficha lo disparo, y eso es parte del hallazgo

Al escribirla, `pii-scan` bloqueo el push con TRES hallazgos: `getty@tty1.service`
en la tabla de arriba, y dos direcciones de EJEMPLO que yo habia escrito en
prosa para explicar el patron.

Las tres se resolvieron distinto, y la diferencia importa:

- la unit entra en el allowlist, porque no hay forma de escribirla que no case;
- las direcciones de ejemplo se BORRARON y se describieron por su forma. Una
  direccion inventada casa el patron igual que una real, y la doctrina del
  propio gate es que un hallazgo se describe por su forma y su tamano, no por
  su contenido identificable. Meterlas en el allowlist habria sido usar la
  valvula para no seguir la regla.

Los literales que el test SI necesita viven en `tests/`, que este gate no
barre -- barre `tasks/` y `docs/`.

## Lo que YA esta pagado, y con que

`tasks/pii_allow.txt`, que es el mecanismo sancionado del propio gate:
versionado, explicito, y una afirmacion firmada por linea. **No es un bypass**
-- el gate lo lee por diseno, y vive en `tasks/` y no en `.simplecode/`
precisamente para que viaje al clone.

Control negativo corrido, no argumentado:

```
CON tasks/pii_allow.txt   -> revisados=156  hallazgos=0
SIN tasks/pii_allow.txt   -> revisados=155  hallazgos=8
```

Los ocho estan en dos ficheros: siete en ESTA ficha -- que para describir el
defecto tiene que escribir las cadenas que lo disparan-- y el octavo en el
`close_check` de `DEBT-ESCRITORIO-Y-ARNESES-COMPARTEN-CGROUP`, que es el que
importa. El `revisados` baja de 156 a 155 porque sin el fichero de allowlist
hay un fichero versionado menos que barrer.

Y con eso se **recupero** algo que se habia perdido: el `close_check` de
`DEBT-ESCRITORIO-Y-ARNESES-COMPARTEN-CGROUP` habia tenido que cambiarse a un
eslabon mas debil de la cadena, porque la ruta del bueno contiene
`user@1000.service` y no se puede reescribir -- es una ruta de `/sys/fs/cgroup`
y escribirla de otra forma seria escribir una ruta que no existe. Ese es el
coste concreto que este falso positivo llego a cobrar: **un criterio de cierre
peor**.

## Lo que queda ABIERTO, y por que es de flota y no de este repo

El allowlist resuelve **instancias**, no la **clase**. Cada unit con instancia
que cualquier satelite documente habra que declararla a mano, una a una, y el
que se la encuentre leera "dato personal de terceros" sobre el nombre de un
servicio del sistema. En una flota que documenta cgroups y units, eso se repite.

El arreglo vive en `simplecode/verification/pii_scan.py`, y el modulo ya tiene
la forma donde encaja: `es_identificador_compuesto()` existe exactamente para
descartar cadenas que casan un patron por casualidad, y hoy solo mira prefijos
tipo `X-Y-`.

## Como se cierra

Aguas arriba, con las dos mitades:

1. que el patron (o su guardia de identificadores compuestos) deje de casar
   `<algo>@<instancia>.<sufijo-de-unit>`;
2. **sin apagar el detector**: el incidente que creo este gate fue una tabla
   con veinte RFC de clientes reales pegada en una ficha, y un arreglo que
   ensanche el escape seria peor que el falso positivo.

`tests/test_pii_scan_systemd.py` mide las dos, sobre el artefacto REAL del
`runtime.zip` y no sobre una copia del patron escrita aqui -- una copia
probaria que se escribir el mismo regex, no que el gate se comporte de una
forma.

## Por que el criterio no es "que ese test pase"

Porque los tres casos llevan `xfail(strict=True)`. Hoy salen `xfailed` y la
suite queda verde; el dia que el kit se sincronice con el patron arreglado
pasan a `XPASS` y **la suite se pone roja**, que es la senal para venir a
cerrar esto. Un `xfail` no estricto se quedaria verde para siempre y la ficha
envejeceria sin que nadie lo notara.

Un criterio de "pytest sale 0" cerraria la ficha hoy mismo, con el defecto
intacto.

## Limite declarado

Esta ficha no arregla nada por si sola: pide un cambio en otro repo. Lo unico
que blackbox puede garantizar es que el falso positivo no le vuelva a costar un
criterio de cierre (allowlist) y que la regresion se vea cuando el arreglo
llegue (el xfail estricto). Si el plazo de la linea base vence sin que aterrice,
se vuelve a discutir en vez de renovarse sola.

## CERRADO el 2026-09-26: la unit de systemd deja de casar

El arreglo aterrizo en el kit **8.6.3**, y llego con el sync del commit
`7639ce6`. Verificado sobre el runtime, no sobre una copia:

```
es_unidad_systemd("user@1000.service")            -> True
es_unidad_systemd("org.gnome.Shell@x11.service")  -> True
es_unidad_systemd("getty@tty1.service")           -> True
es_unidad_systemd("alguien@ejemplo.com")          -> False
es_unidad_systemd("nombre.apellido@empresa...")   -> False
```

Y de punta a punta, porque la funcion podria estar bien y no llamarse: el gate
sobre un fichero con `org.gnome.Shell@x11.service` y una ruta de
`/sys/fs/cgroup/.../user@1000.service/app.slice` da `hallazgos=0`.

El patron NO cambio -- byte a byte el mismo que en 8.5.1, y sigue cazando las
tres cadenas. Lo que cambio es el veredicto, via una funcion nueva. Eso importa
porque es lo que dejo muda la senal de esta ficha, abajo.

### El allowlist se BORRA, medido por retirada

```
hoy, con el arreglo:   CON tasks/pii_allow.txt -> 163/0   SIN -> 162/0
el 2026-09-25, sin el: CON                     -> 156/0   SIN -> 155/8
```

Sus tres firmas ya no cargan nada. Un allowlist que no exime nada es una
afirmacion firmada sobre un riesgo que ya no existe.

### Y el defecto del instrumento PROPIO que este cierre paga

Esta ficha prometia: "el dia que el kit se sincronice arreglado, los tres
`xfail(strict=True)` pasan a XPASS y la suite se pone ROJA. Eso es la senal".

**No disparo.** `3 passed, 3 xfailed` el mismo dia en que el bloqueador dejo de
existir, porque el test asertaba sobre `CORREO.search()` -- el patron, que nunca
iba a cambiar-- en vez de sobre el veredicto del gate.

La suite se reescribio: asierta `es_unidad_systemd` y el gate de punta a punta,
8 casos, sin xfail. Con su control de que la alarma suena: apagada
`es_unidad_systemd`, el test levanta `AssertionError`; encendida, pasa.

La leccion queda en `DECISIONS.md`, porque es durable y no de esta ficha: un
xfail usado como senal de aterrizaje tiene que asertar el VEREDICTO del gate, no
un interno al que el gate llegue de paso.

## Root Cause

El patron de `pii-scan` es
`\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b`, y una unit de systemd
**con instancia** tiene la misma forma que una direccion: parte local, arroba,
"dominio", punto, "tld". `user@1000.service` y `alguien@ejemplo.com` son
indistinguibles mirando solo la cadena.

Y el guardia que existia para esto -- `es_identificador_compuesto` -- solo miraba
prefijos tipo `X-Y-`, asi que no alcanzaba a las units.

## Regression Test

`tests/test_pii_scan_systemd.py`, 8 casos, sin xfail. Asierta el **veredicto** del
gate en dos niveles, no un interno:

1. `es_unidad_systemd` sobre las tres units y las dos direcciones;
2. el gate ENTERO por subproceso -- `hallazgos=0` sobre un fichero con una unit y
   una ruta de cgroup, `hallazgos>=1` sobre uno con una direccion-- porque la
   funcion podria estar bien y no llamarse desde el barrido.

Y el control de que la alarma suena, que es lo que la version anterior no tenia:

```
apagada `es_unidad_systemd` (la regresion de 8.5.1) -> AssertionError   rojo
encendida                                           -> pasa            verde
```

## Verification Evidence

`tasks/evidence/DEBT-PII-SCAN-LEE-UNITS-DE-SYSTEMD-COMO-CORREOS/aterrizaje-8.6.3.txt`,
con: el patron antes y despues (identico), la funcion nueva y su tabla de
veredictos, el gate de punta a punta, la retirada del allowlist (163/0 con el,
162/0 sin el, contra 155/8 el 2026-09-25) y el registro de que la senal de esta
ficha no disparo.

LIMITE DECLARADO: el arreglo vive aguas arriba y este repo no lo controla. Si un
sync futuro lo revierte, el que avisa es el test -- ahora que asierta el
veredicto, se pone rojo. Antes no: se quedaba verde, y eso es lo que costo que el
aterrizaje pasara desapercibido el mismo dia que ocurrio.
