# Revisión 2 (última) de otra familia — close-check, Claude Opus 5.5 high

Fecha: 2026-11-13. Tarea task_63c7a0777fda. Reporte del autor (Sol): `~/scratch/blackbox/2026-11-13-close-check-r2/reporte.md`.
Sujeto fijo: blackbox `6194cf8fb0bd1ac657935c98c5779e952079fa93`, construido sobre 35fdb0e5. El acumulado se mide desde dd5b7098.
Parche propuesto, sin escribir en simplecode: `close-check-measurement-r2.patch`, sha256 `146ce275…b767`, aplicado sobre simplecode `cc482aa2`.
No modifiqué blackbox ni simplecode. Corrí todo sobre copias propias en este directorio. Sin servicios, GPU, Dell, lista privada, publicación ni integración.

## Veredictos por alcance

| alcance | veredicto |
|---|---|
| **Compatibilidad local**: blackbox 6194cf8f, contrato report-only | **APRUEBA** |
| **Parche propuesto** para simplecode (medición más aceptaciones rojas) | **APRUEBA como propuesta**, con los requisitos R1–R3 antes de integrarlo con un voto |

Ninguno de los dos veredictos aprueba un cierre ni una barrera. La deuda del falso verde sigue abierta. Una fila normal `pass` con `no_ejecuta=1` solo prueba que el reporte está disponible: no ejecuta los cierres y no bloquea nada.

## Sujeto y hashes

- Los hashes de `git show 6194cf8f:<f>` coinciden con `candidate-r2.json` en los 5 archivos (`sujeto-hashes.txt`). El árbol rastreado es igual a 6194cf8f.
- `simple.json` de 6194cf8f es idéntico byte a byte al publicado: `git diff --quiet dd5b7098 6194cf8f -- simple.json` da rc=0.
  En el acumulado dd5b7098..6194cf8f solo cambia `tasks/`, así que el resto del contrato queda preservado.
- La política viva de simplecode tiene sha256 `bee585a2…cbd5` y la ficha canónica `19df72cc…700e`, igual que `source-r2.json`. El parche aplica limpio en la copia.
- La propuesta de enforce retirada se conservó por rename, como manda el contrato de suspensión: sha256 `acfba2b1…d49` y modo `664`, igual que su MANIFEST, que vence el 2026-11-27 y tiene vigilante declarado.

## Aceptación roja y medición (copia `sc/`, sin PYTHONPATH ni POLICY_SOURCE)

```
$ python3 -m pytest -q tests/policy/test_close_check_lint_block.py      # close_check literal de la ficha
FAILED ...test_aceptacion_bloqueo_pendiente_en_cierre_sin_codigo   assert 0 == 1  ('criterio pendiente: bloqueo votado...')
FAILED ...test_aceptacion_clasificador_no_rechaza_ejecucion_real    assert 'no_ejecuta' == 'ejecuta'
FAILED ...test_aceptacion_no_confunde_echo_con_ejecucion            assert 'ejecuta' == 'no_ejecuta'
3 failed in 0.12s          (desde otro cwd: 3 failed in 0.11s)
$ python3 -m pytest -q tests/policy/test_close_check_lint.py tests/policy/test_close_check_report_measurement.py
64 passed in 0.70s
```
Las tres pruebas fallan por aserciones sobre el producto. No hay ImportError ni errores de colección. Con `--import-mode=importlib` el import entre hermanos sí daría `ModuleNotFoundError`, pero simplecode no usa ese modo (grep vacío) y ya importa entre hermanos en `tests/fleet/*`.

## Negativos reales sobre copias mutadas (`negativos-r2.txt`)

| copia | medición (4) | aceptación (3) | qué demuestra |
|---|---|---|---|
| `sc` (propuesta) | 4 passed | 3 failed | línea base |
| `n1` clasificador neutralizado (todo es `ejecuta`) | **1 failed** | 2 failed, 1 passed | la medición detecta que se quitó el detector; neutralizarlo no pone verde la aceptación |
| `n2` prueba de git ausente sin retirar git del PATH | **1 failed** | 3 failed | la prueba CNR depende de retirar git en un repo válido; no hay falso verde por un directorio sin Git |
| `n3` clasificador que pierde los scripts `.py` | **1 failed** | 3 failed | el positivo real discrimina |
| `p1` arreglo completo hipotético (bloqueo por defecto + shellcheck/heredoc + echo) | 2 failed | **3 passed** | la aceptación puede ponerse verde, así que es alcanzable |
| `p2` solo bloqueo por defecto (arreglo parcial) | 2 failed | **2 failed**, 1 passed | un arreglo parcial no cierra la ficha |

## Compatibilidad con el corredor instalado (clon en `runner/sujeto`, fila policy nativa, `simplecode verify --hook pre-push --no-observe --fresh`)

```
normal (base dc1b5442, rango real del falso verde)  rc=0 {could_not_run:0, fail:0, pass:1, pending:0}  stdout: fichas_cerradas=1 ejecuta=0 no_ejecuta=1
base_invalida (control)                             rc=2 {could_not_run:1, fail:0, pass:0, pending:0}  reason: base refinexistente ... does not resolve to a commit
```
El push ya no se congela como CNR (esto resuelve F3). El `pass` es la disponibilidad del reporte: `no_ejecuta=1` sigue siendo deuda, no un cierre.

## Alineación con el generador y el perfil (`alineacion.txt`)

`generate.text_of('blackbox')` == `profiles/fleet/blackbox.simple.json` == local en la fila close-check, todos con `args: []`.
El contrato local es igual al publicado (`local==publicado(dd5b7098) True`). La única fila que difiere del generador es
`datos-privados-publicacion`, que es local y ya difería antes del cambio. Control negativo: con `--enforce` en memoria, la igualdad da `False`.

## Privacidad y fichas

- `tests/test_sin_datos_privados.py tests/test_guarda_snapshot.py` en 6194cf8f: `8 passed in 3.39s`.
- Busqué rutas personales, usuario, correo, IPv4 y temas de ntfy/Tailscale en los archivos que cambiaron entre 35fdb0e5 y 6194cf8f: 0 coincidencias.
  Control: el mismo patrón sobre una línea sintética da 1. `measurement-r2.json` declara el enmascarado de las rutas de diagnóstico.
- Las tres fichas de privacidad y `tasks/checks/test_revision_privacidad.py` no cambian entre dd8ec17c y 6194cf8f (diff_rc=0).
  Siguen con `status: open`, y su aceptación sigue roja (`4 failed in 2.14s`). No se arregló nada.

## Muestra del clasificador: es una muestra, no una tasa de la flota

Reproduje en vivo las 6 clasificaciones de `measurement-r2.json` con la política intacta (`clasificador-vivo.txt`):
- 2 falsas alarmas para un bloqueo futuro: `shellcheck bin/bb` y `python3 - <<'PY'`.
- 1 omisión: `echo pytest` cuenta como `ejecuta`. El docstring ya lo declaraba como límite.
- 2 correctas.
- 1 sin adjudicar: `systemctl is-active`, que no se ejecutó (CNR=1 de la muestra).
El resumen dice «controlled sample, not a fleet rate; no blocking threshold voted». No extrapolo ninguna tasa. El conteo `--all` de la ronda 1 (blackbox 65/273) es un inventario, no una tasa adjudicada.

## F1–F5

- F1 resuelto. El close_check canónico está rojo por el producto. No se pone verde neutralizando el detector ni con un arreglo parcial, y sí se puede poner verde con el arreglo completo. Queda R2.
- F2 resuelto. Rige report-only con `args: []`. La propuesta de enforce quedó retirada por rename con MANIFEST verificado.
- F3 resuelto. El corredor instalado da pass (rc=0) y la base inválida da CNR (rc=2).
- F4 resuelto. Generador, perfil y contrato local coinciden, y el negativo en memoria da `False`.
- F5 resuelto. Las pruebas cubren el rango explícito y las variables del hook, git ausente en un repo válido (con su restauración) y un positivo real que el reporte no re-ejecuta. Los negativos n1, n2 y n3 rompen cada uno su prueba.

## Requisitos antes de integrar con un voto (no bloquean el estado de «propuesta»)

- **R1.** La aceptación 1 llama a la política sin flag, así que prescribe el bloqueo **por defecto**, y `p1` muestra que eso rompe 2 de las 4 pruebas de medición, que fijan report-only.
  Si el voto elige bloqueo opt-in (flag), hay que ajustar la aceptación 1 en ese mismo commit. Si elige bloqueo por defecto, hay que reescribir la medición en ese mismo commit. Las dos suites no pueden quedar verdes a la vez, y es intencional.
- **R2.** La aceptación todavía no cubre dos cláusulas del criterio de la ficha: que un commit que toca código no bloquee, y el negativo «contra el árbol anterior».
  `p1`, que bloquea sin mirar el código, la pone verde. Por eso el verde de la aceptación no equivale a cumplir el criterio. Hay que añadir esos casos si el voto conserva la cláusula.
- **R3.** El caso `systemctl` sigue sin adjudicar, y el MANIFEST vence el 2026-11-27: alguien del dueño (simplecode) o de la coordinación tiene que decidir su destino antes.

## Lo que no corrió

- No corrí el corredor completo del candidato ni la suite completa de simplecode o de blackbox. Es otro alcance y lo despachará la coordinación.
- No adjudiqué `systemctl` (CNR=1 de la muestra).
- Tuve un error de instrumento propio: faltaba el directorio `bt/` de `--basetemp`, lo que produjo un FileNotFoundError en la primera corrida. Lo creé, repetí la corrida, y las cifras de arriba son de la repetición.
