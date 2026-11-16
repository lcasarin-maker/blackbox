# Paquete documental para decision director/Luis — sin publicacion

Recomendacion: someter a boleta la publicacion por push normal de los tres
commits existentes como registro de deuda, evidencia y propuesta. Condicionar
la autorizacion al sujeto fijo y al resultado del hook real, con cero fallos,
CNR y pendientes en las filas exigidas. Mantener report-only, deudas abiertas
y propuesta simplecode separada de cualquier integracion o cierre.

Este paquete no emite el voto ni autoriza publicar. No se modificaron producto,
contrato, commits ni fuentes canonicas durante su preparacion.

## 1. Sujeto exacto y efecto publicable

Remoto de red `git ls-remote origin refs/heads/master`:
`dd5b7098b3714219a3a5fc6a2c17964c0baa4d7f refs/heads/master`.
HEAD/master candidato: `6194cf8fb0bd1ac657935c98c5779e952079fa93`.
Rango exacto: `dd5b7098b3714219a3a5fc6a2c17964c0baa4d7f..6194cf8fb0bd1ac657935c98c5779e952079fa93`.
Arbol e indice limpios; origin/master local coincide con el remoto observado.

Tres commits alcanzables del candidato fuera del remoto, con neto de 17 archivos
nuevos bajo tasks/ (809 lineas). Incluye 55 lineas de Python de aceptaciones
en tasks/checks/test_revision_privacidad.py: no es solo Markdown. No cambia
bin/, tools/, tests/ ni simple.json respecto del remoto. Las aceptaciones son
explicitas de las fichas, permanecen rojas y no se presentan como producto listo.

Comparacion actual y su negativo, comandos literales:
- `git diff --quiet dd5b7098 6194cf8f -- simple.json bin tools tests`: rc=0.
- `git diff --quiet dd5b7098 35fdb0e5 -- simple.json`: rc=1.
- `git merge-base --is-ancestor dd5b7098 6194cf8f`: rc=0.
- `git merge-base --is-ancestor 6194cf8f dd5b7098`: rc=1.
Las salidas stdout/stderr son vacias en los cuatro; su distinto rc demuestra
que los instrumentos pueden detectar diferencias y direccion de ascendencia.
Inventario generado desde Git en sujeto.json; no se reconstruyo de informes.

Efecto de cada commit:

### dd8ec17c — docs(debt): generar tres fichas y vincular medicion del falso verde

Genera tres fichas open con owner, aceptacion y close_check desde el JSON fuente, agrega la aceptacion ejecutable y enlaza el falso verde al ID canonico existente. No implementa ni cierra las tres deudas.

Archivos de ese commit (fuente: git diff-tree):

- `A` `tasks/backlog/DEBT-GUARDA-PUBLICA-ARCHIVOS-EXENTOS-01.md`
- `A` `tasks/backlog/DEBT-GUARDA-PUBLICA-ERROR-LECTOR-COMO-FAIL-01.md`
- `A` `tasks/backlog/DEBT-SPEC-GATEWAY-DOS-NOTACIONES-01.md`
- `A` `tasks/checks/test_revision_privacidad.py`
- `A` `tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/medicion.json`
- `A` `tasks/evidence/REVISION-PRIVACIDAD-2026-11-13/pendientes-revision.json`

### 35fdb0e5 — fix(gate): preparar bloqueo de no_ejecuta para revision y corredor

Propone --enforce en simple.json y agrega parche/evidencia. Era incompatible con el corredor instalado y fue rechazado para aterrizar aislado. Se conserva como historia; su activacion se corrige en el commit siguiente.

Archivos de ese commit (fuente: git diff-tree):

- `M` `simple.json`
- `A` `tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/README.md`
- `A` `tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/close-check-enforce.patch`
- `A` `tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/controles.json`
- `A` `tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/source.json`

### 6194cf8f — fix(close-check): conservar report-only y separar medicion de aceptacion

Repara hacia adelante args=[] y preserva el voto report-only; archiva la propuesta anterior por rename con MANIFEST; agrega medicion discriminada y nueva propuesta con aceptacion roja separada. No escribe ni integra simplecode.

Archivos de ese commit (fuente: git diff-tree):

- `M` `simple.json`
- `M` `tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/README.md`
- `A` `tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/alineacion-r2.json`
- `A` `tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/candidate-r2.json`
- `A` `tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/close-check-measurement-r2.patch`
- `A` `tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/measurement-r2.json`
- `A` `tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/propuestas-no-vigentes/MANIFEST.json`
- `R100` `tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/close-check-enforce.patch` → `tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/propuestas-no-vigentes/close-check-enforce.patch`
- `A` `tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/runner-r2.json`
- `A` `tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/source-r2.json`

Publicar el rango junto preserva la historia y publica una punta compatible;
publicar solo 35fdb0e5 tendria otro sujeto y no esta recomendado ni aprobado.

## 2. Que revision cubre cada alcance

Opus ronda 1, sobre dd5b7098..35fdb0e5: no aterrizable por F1–F5. Se conserva
como antecedente, no como veto vigente del candidato distinto.
Opus ronda 2, sujeto exacto 6194cf8f: texto literal:

> Compatibilidad local: blackbox 6194cf8f, contrato report-only | APRUEBA
> Parche propuesto para simplecode (medición más aceptaciones rojas) | APRUEBA como propuesta

Y sobre R1–R3, su titulo literal delimita:

> Requisitos antes de integrar con un voto (no bloquean el estado de «propuesta»)

Ninguno de esos veredictos aprueba un cierre o una barrera. Fuente:
~/scratch/blackbox/2026-11-13-revision-close-check-opus-r2/informe.md.
El corredor Luna y la conciliacion posterior cubren el mismo HEAD y el mismo
binario/politica. Sus limites no se fusionan ni se borran por la conciliacion.

La conciliacion titula «publicación **BLOQUEADA en este dictamen**» y despues
remite la publicacion a coordinacion. Eso conserva la reserva de decision;
no aporta una clausula contractual que convierta todo backlog abierto en veto.
La decision sigue pendiente del director/Luis, no de este worker.

## 3. Contrato real de publicacion: deudas no son un veto general

Autoridad operativa local: .git/hooks/pre-push invoca literalmente
`exec "$simple" hook run pre-push "$@"`. core.hooksPath no tiene valor propio.
El contrato simple.json selecciona cinco filas pre-push: datos-privados-publicacion,
pytest (test-impact), bb-cobertura-piso, ceremony y close-check. No selecciona
un gate zero-debt ni exige ejecutar los close_checks de todas las fichas abiertas.
No se infiere esa conclusion solo de la ausencia de un nombre: la semantica
positiva y la autoridad de las filas se citan a continuacion.

simplecode/docs/HOOKS.md:11, texto exacto de la regla de bloqueo:

> Sí: 2 si alguna línea es `could_not_run`, si no 1 si alguna falla, si no 0.

Sobre el sujeto que se evalua, :13 dice literalmente:

> El commit intermedio de un push con varios commits **no** se verifica por separado: el sujeto es cada punta. La salida lo declara en `scope`.

simplecode/DECISIONS.md:184, Boleta 6, 2A:

> los detectores `ceremony` y `close-check` corren en modo reporte por defecto en toda la flota; los umbrales de bloqueo se votan tras medir

simplecode/policy/simple_policy/close_check_lint.py:21 dice exactamente:

> Exit codes: 0 reported (never blocks in this phase), 2 COULD_NOT_RUN.

Ese mismo archivo :137 filtra status done/closed; las tres fichas nuevas son
open. No inspecciona deudas abiertas como condicion universal de publicacion.
El PASS significa reporte disponible, no ejecucion, integridad de evidencia ni
cierre. Si el instrumento no puede medir, su rc=2 bloquea la fila.
Como antecedente local, DECISIONS.md:435 rechaza «conservar el proceso de fichas
como compuerta»; la conclusion actual se basa en el contrato y voto vigentes,
no en extender una decision historica a reglas que cambiaron despues.

Conclusiones limitadas al alcance:

| Pendiente | Publicar estos tres commits como registro/propuesta | Integrar parche o cerrar deuda |
|---|---|---|
| Tres fichas privacidad open y 4 aceptaciones rojas | No es veto contractual por su sola existencia; guarda de privacidad obligatoria si debe pasar | Impide declarar sus defectos resueltos o cerrarlas |
| R1: opcion bloqueo por defecto/opt-in y suites incompatibles | No bloquea almacenar la propuesta, segun alcance expreso de Opus | Resolver junto al voto e integracion |
| R2: falta caso con codigo y negativo sobre arbol anterior | No bloquea documentacion/propuesta; no afirmar cumplimiento del criterio canonico | Bloquea dar por cumplido ese criterio si el voto lo conserva |
| R3: systemctl sin adjudicar y MANIFEST con vencimiento | No es veto automatico del gate; hay que conservar pendiente y vigilancia | Adjudicar y decidir destino antes de 2026-11-27 |
| CNR/fail real en fila exigida por pre-push | Si bloquea, aunque el backlog estuviera vacio | No saltar ni reetiquetar |
| Falta decision de publicacion del director/Luis | Mantiene esta entrega sin publicar | Este paquete es el insumo para esa decision |

No se inspeccionaron reglas de proteccion remotas ni se afirma permiso del
servidor. Un rechazo del remoto o un cambio de sujeto obliga a conciliar;
este analisis no sustituye al hook ni a la autorizacion.

## 4. Evidencia positiva y negativa existente, sin repetir ejecuciones

Corredor completo Luna sobre 6194cf8f, comando literal:

```sh
simplecode verify --repo . --hook pre-push --fresh --no-observe --impact-base dd5b7098b3714219a3a5fc6a2c17964c0baa4d7f
```

Reporte: ready=true, pass=4, fail=0, could_not_run=0, pending=0.
Privacidad: 5 pruebas PASS; pytest impacto: 314 modulos parseados y 0 pruebas
impactadas (no es una suite global aprobada); ceremony y close-check reportan;
close-check: fichas_cerradas=0 ejecuta=0 no_ejecuta=0 en ese rango.
Cobertura: no aplicable; el neto no toca bin/bb ni tests/test_bb_bash.py.
La carpeta de Luna disponible contiene su INFORME, no el JSON crudo completo:
es evidencia historica citada, distinguida de los recibos crudos posteriores.

Luna tambien corrio base de seleccion inexistente: pass=5, fail=0, CNR=0,
ready=true y evaluated=false; cobertura corrio y su reporte cita 119560 ms.
La conciliacion distingue esa entrada de una base contractual invalida.

En la copia minima independiente de conciliacion (dos filas reales y un probe),
recibos JSON completos leidos sin volver a ejecutarlos:

| Caso | pass | fail | CNR | pending | ready | Alcance |
| positive | 2 | 0 | 0 | 0 | true | copia minima sintetica |
| invalid-selection-base | 3 | 0 | 0 | 0 | true | copia minima sintetica |
| invalid-policy-base | 1 | 0 | 1 | 0 | false | copia minima sintetica |
| both-bases-invalid | 2 | 0 | 1 | 0 | false | copia minima sintetica |
| invalid-contract-base | 2 | 0 | 1 | 0 | false | copia minima sintetica |
| invalid-selection-fallback-fails | 2 | 1 | 0 | 0 | false | copia minima sintetica |
| privacy-negative | 1 | 1 | 0 | 0 | false | copia minima sintetica |
| privacy-instrument-cnr | 2 | 0 | 1 | 0 | false | copia minima sintetica |

Cada caso conserva su SHA sintetico y recibo en evidencias.json: **no** es el
SHA del candidato real ni prueba del gate de cobertura. El probe inocuo solo
observa seleccion/fallo bajo fallback. privacy-negative usa la guarda real
firmada y un blob ficticio: 1 failed, 4 passed; privacy-instrument-cnr no ejecuta
la guarda, porque el interprete es inexistente. Es averia del instrumento,
distinta del hallazgo de privacidad.

Positivo de privacidad en el sujeto real de conciliacion: 5 passed in 3.30s.
Opus en el candidato: 8 passed in 3.39s (guarda y snapshots), 64 passed in 0.70s
(medicion canonica), 3 failed in 0.12s (aceptacion canonica), 4 failed in 2.14s
(aceptacion de las tres deudas). Los negativos de Opus detectan detector
neutralizado, Git no retirado y perdida de scripts; la aceptacion solo se pone
verde con una mutacion hipotetica de arreglo completo, no con arreglo parcial.

## 5. Las dos bases: texto que evita un bloqueo inventado

simplecode/SPEC.md:49, sobre applies_to:

> Ante cualquier duda corren todas las filas seleccionadas y `impact.evaluated` es `false` con la causa

Entre las causas incluye base de seleccion que no resuelve. Eso es fallback
seguro, no CNR global. El negativo invalid-selection-fallback-fails demuestra
que un fallo de fila sigue dejando ready=false en ese mismo fallback.
SPEC.md:44, sobre base de la fila, dice literalmente:

> Una base que no resuelve da `could_not_run` en esa fila.

--impact-base decide seleccion. SIMPLE_PUSH_BASE/base contractual liga el rango
de la politica. Solo la segunda entrada irresoluble genera ese CNR de fila.
La conciliacion resuelve la diferencia de entradas sin cambiar contrato ni voto.

## 6. CNR historicos, controles deliberados y pendientes

- El contrato intermedio 35fdb0e5 produjo CNR=1 con --enforce no soportado.
  Compatibilidad corregida hacia adelante en 6194cf8f; no es el estado actual.
- El negativo de privacidad que Luna no corrio queda CNR historico. Conciliacion
  aporta otro negativo propio con fail=1, CNR=0; no reescribe la corrida anterior.
- CNR deliberados de conciliacion: base politica invalida, ambas bases invalidas,
  base contractual invalida e interprete ausente, uno por fila en cada recibo.
- Dos consultas CLI exploratorias simplecode policy close-check no pudieron
  correr (KIND no expuesto). La medicion posterior por verify es otro camino;
  los intentos se conservan, no se cuentan como pruebas PASS.
- Primer intento confundido de base contractual: pass=1, fail=1, CNR=1; se
  conserva y se excluye de la matriz porque mezclaba fixture de privacidad.
  Repeticion no confundida: pass=2, fail=0, CNR=1.
- Opus tuvo error propio de basetemp faltante, luego repitio; sus cifras citadas
  son de la repeticion. No se borra el intento fallido.
- Pendiente de adjudicar: systemctl de la muestra, CNR=1; no hubo consulta a servicios.
- Conciliacion no corrio cobertura real ni corredor completo otra vez: CNR/no
  corridos de su alcance. El positivo completo de Luna es historico, mismo sujeto.
- No se han ejecutado en este encargo suites, gates, hardware o publicacion:
  solo lectura acotada y preparacion documental. Tampoco listas privadas.

No se presenta un total artificial de cero sumando reportes de sujetos y alcances
distintos. Los ceros y CNR de cada caso quedan junto a sus PASS.

## 7. Cambios de sujeto y requisitos verificables

Ahora: mismo candidato 6194cf8f, mismo remoto dd5b7098, arbol limpio, binario
SHA256 10dd470d321eecc1f8ffda31193d49c855bccf449fcee62a107d9af2311be4b3 y
politica SHA256 bee585a24f25cf94e59cf98b75b9bb5d8c9f7f034019d5339d96b4612020cbd5,
identicos a la conciliacion. No hay cambio de sujeto desde esa evidencia.
La copia minima contiene otras puntas sinteticas; el parche simplecode se probo
en una copia con archivos nuevos; ninguna de esas puntas sustituye a 6194cf8f.
La diferencia frente a dd5b7098 es de alcance documental/aceptacion/propuesta;
la suite global de producto anterior no se transforma en una nueva suite verde.

Antes de autorizar la accion de publicar:

1. Director/Luis decide la boleta de alcance limitado; este worker no la emite.
2. Reconciliar de nuevo HEAD/master=6194cf8f y remoto=dd5b7098, indice/arbol
   limpios y huellas del corredor/politica; si cambian, detener y devolver a coordinacion.
3. Preservar tres fichas open, propuesta sin integrar, report-only y vigilancia
   del MANIFEST. No cambiar aceptaciones para fabricar un cierre.
4. Ejecutar el hook real de publicacion sin force ni no-verify; fail=0,
   could_not_run=0 y pending=0 en lo exigido. Un job previo contradictorio de
   una fila no aplicable tambien puede bloquear segun HOOKS.md:20.
5. Conciliar recibo de envio y `git ls-remote origin refs/heads/master` con el
   candidato; una salida interrumpida no autoriza a asumir entrega ni a repetir a ciegas.

No falta un nuevo positivo offline para el mismo sujeto: ya existe el corredor
Luna y el negativo complementario de conciliacion. Falta, por definicion, el
veredicto del hook nativo en la accion final que aun no esta autorizada.
Comando concreto futuro de publicacion, despues de decidir:
`git push origin 6194cf8fb0bd1ac657935c98c5779e952079fa93:refs/heads/master`.
No se ejecuta en este encargo. Segun HOOKS.md, juzga la punta y la base remota
real; no integra la propuesta simplecode ni ejecuta todas las deudas.

Si director requiere preflight fresco sin publicar, comando acotado propuesto:

```sh
timeout --signal=TERM --kill-after=5s 180s env PYTHONDONTWRITEBYTECODE=1 TMPDIR="$HOME/scratch/blackbox/2026-11-13-paquete-aterrizaje" simplecode verify --repo . --rev 6194cf8fb0bd1ac657935c98c5779e952079fa93 --hook pre-push --fresh --no-observe --impact-base dd5b7098b3714219a3a5fc6a2c17964c0baa4d7f
```

No corrido. Limite externo elegido: 180 s y 5 s de terminacion; rc 124/137 sin
reporte completo es CNR/no se pudo correr, no PASS ni fallo del producto.
Las cuatro filas aplicables tienen timeouts declarados 300/900/300/300 s;
suma 1800 s de ejecuciones declaradas, no estimacion de tiempo total.
Si fallback seleccionara cobertura, se agrega su timeout de 900 s; la suma de
cinco es 2700 s. No es permiso para hardware ni suite global: cambiar sujeto,
base o seleccion obliga a explicar su alcance antes de ampliar trabajo.
La comprobacion propuesta usa el mismo rango valido del positivo Luna y no
manda comandos de GPU, servicios o Dell.

## 8. Boleta borrador y decision recomendada

boleta-borrador.json contiene dos acciones mutuamente excluyentes y un solo
Recommended: publicar el rango documental, condicionado a los requisitos de
arriba; o mantener los tres commits locales. Incluye costo/riesgo por opcion.
La primera publica tambien la propuesta retirada como historia y exige que
nadie la aplique; la segunda demora compartir fichas y evidencia sin que el
contrato exija por ello completar el producto pendiente.

Recomendacion no es aprobacion ni cierre. Mantener R1–R3 para integracion con
voto, completar el criterio si se desea cerrar la ficha canonica y adjudicar
la muestra antes de proponer un umbral de bloqueo. No aplicar parches ni
publicar desde este paquete.
