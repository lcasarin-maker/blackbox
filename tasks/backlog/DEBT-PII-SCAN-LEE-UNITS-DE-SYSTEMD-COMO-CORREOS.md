---
id: DEBT-PII-SCAN-LEE-UNITS-DE-SYSTEMD-COMO-CORREOS
kind: debt
title: "`pii-scan` lee un nombre de unit de systemd como una direccion de correo de un tercero"
status: open
severity: P2
origin: detected
detector: {"rule": "simplecode/pii-scan", "confidence": 1.0}
satd_family: FALSE_POSITIVE
created: 2026-09-25
close_check: {"cmd": "grep -q 'unit de systemd deja de casar' tasks/done/DEBT-PII-SCAN-LEE-UNITS-DE-SYSTEMD-COMO-CORREOS.md", "expect": "exit_zero", "porque": "el arreglo vive aguas arriba, en simplecode, y esta ficha no lo puede provocar. Mismo patron que DGX-438: cierra cuando alguien ESCRIBE que aterrizo. La senal automatica la da tests/test_pii_scan_systemd.py, que lleva xfail(strict=True) y pondra la suite ROJA el dia que el kit se sincronice arreglado."}
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
