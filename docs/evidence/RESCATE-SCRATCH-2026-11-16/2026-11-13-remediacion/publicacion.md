# Publicacion de limpieza hacia adelante

Fecha local: 2026-11-13T18:03:38.152226-06:00

Publicada exclusivamente la serie aprobada `dc1b5442..dd5b7098` (10 commits).
Aprobacion independiente: Claude ctx_60ef95378e30, informe y adenda en
`~/scratch/blackbox/2026-11-13-revision-final-claude/INFORME.md`.
Autorizacion de coordinacion recibida tras esa aprobacion.
La ficha DEBT-GUARDA-PUBLICA-28-RUTAS-SOBRE-LINEA-BASE-01 sigue abierta.

## Conciliacion del sujeto

`git diff --quiet dd5b7098 HEAD`: rc=0, stdout="", stderr="".
Control negativo: `git diff --quiet dc1b5442 dd5b7098 -- SPEC.md`:
rc=1, stdout="", stderr="".
`git status --porcelain`: rc=0, stdout="".
Control negativo en la copia de pruebas: mismo comando muestra
` D docs/control_privacidad.txt` y `?? .simple/`.
El remoto antes del push estaba en dc1b544284c19cbea5f31db8b5c5b2a4863a07f9.
No se incorporaron cambios posteriores al rango aprobado.

## Push normal y gate real

Comando: `PYTHONDONTWRITEBYTECODE=1 TMPDIR="$HOME/scratch/blackbox/r13" git push origin master`.
rc=0; salida final literal: `dc1b5442..dd5b7098  master -> master`.
Sin force, reescritura ni omision de hooks.
Resumen del hook (un tip publicado): `{"could_not_run": 0, "fail": 0, "none_selected": 0, "not_applicable": 0, "pass": 1, "pending": 0}`.
Reporte de filas: `{"could_not_run": 0, "fail": 0, "pass": 5, "pending": 0}`, ready=true.

- datos-privados-publicacion: pass; rc=0.
Salida literal:

```text
.....                                                                    [100%]
5 passed in 3.21s
```

- pytest: pass; rc=0.
Salida literal:

```text
test_impact: import graph: 313 modules parsed, 0 unparseable (skipped), 1 changed code file(s) reached by no test
test_impact: running 7 impacted test file(s) for 11 code change(s):
  • tests/test_bb_wol.py
  • tests/test_boton_rojo.py
  • tests/test_config_privacidad.py
  • tests/test_guarda_snapshot.py
  • tests/test_inventario.py
  • tests/test_panic.py
  • tests/test_sin_datos_privados.py
...................................
[tiempo] sin contenedores: 0.13 s
.
[tiempo] con contenedores, docker stop 5 s: 5.13 s
.................................... [ 60%]
...................................
[tiempo] sudo panic con punto, configuracion cambiada y regeneracion de grub.cfg: 0.24 s
............                          [100%]
119 passed in 25.08s
```

- bb-cobertura-piso: pass; rc=0.

- ceremony: pass; rc=0.

- close-check: pass; rc=0.
Salida literal:

```text
no_ejecuta tasks/done/FEATURE-VENTANA-GPU-NOCTURNA-SECUENCIA-01.md: ningún ejecutor de la lista: test -s ~/.local/share/blackbox/ventana-gpu/resumen.txt && grep -q 'quien_mata=' ~/.local/share/blackbox/ventana-gpu/res
fichas_cerradas=1 ejecuta=0 no_ejecuta=1
```

La fila de privacidad uso snapshot `shared read-only`.
Control negativo previo sobre el codigo aprobado: el mismo pre-push en copia
con dato en HEAD y disco limpio dio pass=4, fail=1, could_not_run=0; la fila
que fallo fue datos-privados-publicacion. Pytest directo con disco limpio y
archivo borrado tambien fallo (1 failed, 4 passed). Detalles por punto y
commits en revision-respuestas.md; logs integros locales en push-normal.txt.

## Remoto observado despues

`git ls-remote origin refs/heads/master`:

```text
dd5b7098b3714219a3a5fc6a2c17964c0baa4d7f	refs/heads/master
```

`git rev-parse master origin/master`:

```text
dd5b7098b3714219a3a5fc6a2c17964c0baa4d7f
dd5b7098b3714219a3a5fc6a2c17964c0baa4d7f
```

Arbol limpio al comprobar la publicacion. La comparacion con el remoto se
hizo contra la respuesta de red, ademas de la referencia local origin/master.

## Verificaciones anteriores que conservan su alcance

Guarda antes: `1 failed, 4 passed in 3.31s`; despues: `5 passed in 3.32s`;
tras correcciones: `5 passed in 3.51s`.
Suite completa corregida: `17 failed, 4579 passed, 8 skipped, 3 deselected, 2 warnings in 522.43s (0:08:42)`.
Los 17 fallos ya estaban entre los 18 originales; cero nuevos, solo la guarda
deja de fallar. No se repitio la suite completa: HEAD y controles relevantes
seguian iguales al rango aprobado. Los ocho omitidos y tres deseleccionados
se conservan como tales. El pre-push real si se ejecuto para esta publicacion.

Lista privada sin publicar: 78 valores, modo 600, 682 commits afectados;
MAC=33, IP_LAN=25, USUARIO=1, HOST=1, KB=2, PROYECTO=16.
Marcas: A-confirmado=13, A-historico=10, candidato-sintetico=55.
La reescritura y la adjudicacion conservadora siguen pendientes.
Los despliegues desalineados siguen enumerados en la ficha y en revision-respuestas.md:
unit de muestreo, copia root del boton y dependencia de timers de restauracion,
WoL en la Dell y ejemplos/copias documentales. Instalaciones y servicios intactos.

## Tres observaciones menores conservadas

Pendientes especificos con evidencia en pendientes-revision.json, fuera del
rango Git aprobado; pendientes de materializar por coordinacion:

1. DEBT-GUARDA-PUBLICA-ERROR-LECTOR-COMO-FAIL-01: G4/C7 del revisor,
   instrumento roto produce fail rc=1 y could_not_run=0, en vez de diferenciar
   el fallo del lector. El push se bloquea; la clasificacion requiere corregirse.
2. DEBT-GUARDA-PUBLICA-ARCHIVOS-EXENTOS-01: C6 del revisor, el archivo de la
   guarda y su base estan exentos; dato sintetico en el primero dio 5 passed.
   Es previo al cambio. Definir cobertura de esas exenciones con controles.
3. DEBT-SPEC-GATEWAY-DOS-NOTACIONES-01: SPEC.md:380 y :404 usan dos formas
   genericas distintas para el mismo gateway; unificar en cambio posterior.

## No se pudo correr y limites

Publicacion: could_not_run=0, fail=0, pending=0; cinco filas pass.
Revision independiente: counts G0-G4 tambien imprimen could_not_run=0, pero
su adenda conserva estas limitaciones: suite completa y pre-push completo
no ejecutados por el revisor; montaje de solo lectura no disponible por
bwrap/namespace, por lo que sus filas corrieron en copia privada degradada;
despliegues, red y Dell fuera de su comprobacion. Sus controles directos de
pytest aportan la via independiente. El fallo inicial de envio EPERM fue
resuelto por excepcion selectiva de orquestacion, segun su adenda.
No se presenta esa revision como un pre-push completo ni se oculta su degradacion.
El pre-push de publicacion arriba completo esa comprobacion para el rango.
Close-check conserva su no_ejecuta=1 sobre la ficha historica de ventana GPU;
los contadores del hook no convierten esa omision en una captura runtime.
Ningun manifiesto ni evidencia historica se declaro restaurado o recapturado.
La ficha queda abierta; no se cerro la deuda de historia, despliegue ni residuos.
Memoria de continuidad: entrega de publicacion y pendientes a coordinacion,
por restriccion de escrituras fuera del repo y su scratch en este encargo.
