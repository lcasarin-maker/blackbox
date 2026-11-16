# Materializacion y correccion preparada del falso verde

Commits locales, sin publicar: dd8ec17c (materializacion), 35fdb0e5 (gate y propuesta).
Rango remoto publicado anterior dd5b7098 se conserva; no se revirtio ni reescribio.
Owner de las tres fichas: blackbox. Owner del detector: simplecode.

## Completitud sobre el sujeto

Fuente: tasks/evidence/REVISION-PRIVACIDAD-2026-11-13/pendientes-revision.json,
copiada byte a byte de la lista fuente local; SHA256 consignado en cada ficha.
Generacion: `PYTHONDONTWRITEBYTECODE=1 python3 "$HOME/scratch/blackbox/2026-11-13-close-check/materializar.py"`.
Salida: `items_fuente=3 fichas_generadas=3`.
Verificador: `PYTHONDONTWRITEBYTECODE=1 python3 "$HOME/scratch/blackbox/2026-11-13-close-check/verificar_materializacion.py"`.
Salida literal: `{"cards": 3, "duplicate_ids": 0, "invalid": [], "missing": [], "source_items": 3}`.
La fuente determina los IDs y textos; los archivos no se transcribieron a mano.

Fichas existentes en tasks/backlog, todas open, con owner, aceptacion y close_check:

- DEBT-GUARDA-PUBLICA-ERROR-LECTOR-COMO-FAIL-01
- DEBT-GUARDA-PUBLICA-ARCHIVOS-EXENTOS-01
- DEBT-SPEC-GATEWAY-DOS-NOTACIONES-01

Cada close_check invoca su selector en tasks/checks/test_revision_privacidad.py.
Se invocan explicitamente desde las fichas; no se anadieron xfails ni skips.
Comando: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tasks/checks/test_revision_privacidad.py` (basetemp en scratch).
Salida final literal: `4 failed in 2.03s`: base ilegible, Git ausente, exencion
que blanquea dato nuevo y notacion de SPEC; son aceptaciones rojas de producto.
El primer selector parametriza los dos fallos del lector y tambien exige
HEAD limpio=0 y un dato ordinario=1 despues de corregir la clasificacion CNR.
No se cerro ninguna de las tres observaciones.

Negativos de completitud: copia con una ficha retirada da rc=1,
`cards=2, source_items=3, missing=[DEBT-GUARDA-PUBLICA-ERROR-LECTOR-COMO-FAIL-01]`;
fuente con un ID duplicado da rc=1, `duplicate_ids=1`.
Los casos se ejecutaron contra archivos y fuente reales de control en scratch.

## Hallazgo adicional: ID existente, ninguna ficha duplicada

Se encontro en simplecode la ficha abierta
IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS.
Se reutiliza ese ID y se registra evidencia nueva en
tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/medicion.json.
Se entrega por tanto 3 items JSON=3 fichas, mas 1 ID existente enlazado.

Comando original de publicacion: `PYTHONDONTWRITEBYTECODE=1 TMPDIR="$HOME/scratch/blackbox/r13" git push origin master`.
Fila close-check: state=pass, exit_code=0, con salida literal:

```text
no_ejecuta tasks/done/FEATURE-VENTANA-GPU-NOCTURNA-SECUENCIA-01.md: ningún ejecutor de la lista: test -s ~/.local/share/blackbox/ventana-gpu/resumen.txt && grep -q 'quien_mata=' ~/.local/share/blackbox/ventana-gpu/res
fichas_cerradas=1 ejecuta=0 no_ejecuta=1
```

Ese cierre sigue sin prueba de producto: el PASS anterior era un falso verde.
No se modifico su close_check ni se afirmo nueva captura de la ventana GPU.

## Correccion minima preparada para revision independiente

Reutiliza el detector canonico: opcion --enforce devuelve 1 si no_ejecuta>0;
error de instrumento conserva 2. simple.json solicita ese modo para la fila
close-check. El modo informativo de los otros contratos sigue disponible.
No se creo un adaptador duplicado ni se reemplazaron close_checks por existencia.

Parche preparado (codigo, cuatro pruebas y enlace/owner en ficha existente):
tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/close-check-enforce.patch.
SHA256 del fuente original y propuesto en source.json; el repo simplecode
se leyo y no se modifico. `git -C "$HOME/projects/simplecode" apply --check
"$HOME/projects/blackbox/tasks/evidence/IDEA-ENDURECER-EL-CIERRE-DE-FICHAS-CONTRA-CIERRES-SINTETICOS/close-check-enforce.patch"`
salio rc=0 sin stdout. Control contra copia ya parcheada salio rc=1.

La correccion se probo en copia de la dependencia bajo scratch, sin instalarla.
Comando: `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider
"$HOME/scratch/blackbox/2026-11-13-close-check/simplecode-propuesta/tests/policy"`.
Salida literal: `64 passed in 0.33s`: 60 existentes y 4 nuevos.

Casos medidos con el dispatcher real de la politica:
`PYTHONDONTWRITEBYTECODE=1 python3 "$HOME/scratch/blackbox/2026-11-13-close-check/medir_detector.py"`.
Salida:

```text
antes_no_ejecutor rc=0: fichas_cerradas=1 ejecuta=0 no_ejecuta=1
despues_no_ejecutor rc=1: fichas_cerradas=1 ejecuta=0 no_ejecuta=1
sin_git rc=2: COULD_NOT_RUN: close-check: git rev-parse: [Errno 2] No such file or directory: 'git'
detector_retirado rc=0: fichas_cerradas=1 ejecuta=1 no_ejecuta=0
producto_real_ejecutado rc=0: fichas_cerradas=1 ejecuta=1 no_ejecuta=0
```

stdout/stderr completos en controles.json. La prueba positiva ejecuto
product.py y comprobo su efecto antes de medir el comando correspondiente.
La politica clasifica ejecutabilidad; no es un ejecutor de todos los cierres,
ni demuestra el criterio mas amplio de diff y evidencia previa de la ficha existente.
Esa ficha canonica sigue abierta en la propuesta.

Control adversarial: copia con classify neutralizado, misma prueba de bloqueo:
`python3 -m pytest -q -p no:cacheprovider .../test_close_check_lint_block.py::test_closed_card_without_executor_blocks`.
Salida literal: `1 failed in 0.05s`, rc=1. Retirar el detector rompe el negativo.

## Corredor pendiente: reporte con CNR abierto

El binario instalado aun no incorpora --enforce. Sobre una copia con una sola
fila del contrato propuesto, `simplecode verify --hook pre-push` dio rc=2:
`{"could_not_run": 1, "fail": 0, "pass": 0, "pending": 0}`.
Fila close-check: could_not_run, exit_code=2; no fue un PASS.
La consulta exploratoria `simplecode policy close-check` tambien devolvio
could_not_run=1 porque ese KIND no esta expuesto por su CLI directa; se
conservo esa salida en antes.json y no se uso como medicion del sujeto.
No se pudo correr con el corredor actual: 1 fila (y 1 consulta CLI exploratoria
no disponible). No se presenta el reporte como limpio.

Antes de publicar: revision de otra familia de ambos commits y del parche,
integracion de la dependencia y preparacion del corredor por su owner;
medir con ese binario el pre-push completo y sus positivos/negativos.
No se instalo ni se recompilo el corredor. No se publico otra vez.

## Comprobaciones acotadas y limites

`ruff check tasks/checks/test_revision_privacidad.py`: `All checks passed!`.
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_sin_datos_privados.py tests/test_guarda_snapshot.py`:
........                                                                 [100%]
8 passed in 3.39s

No se repitio suite completa; las cuatro aceptaciones rojas y el CNR del
corredor quedan visibles junto a los 64 controles verdes de la propuesta.
Sin GPU, historia, Dell, despliegues ni listas privadas. La lista de 78 valores
no se leyo, copio ni versiono en este encargo. Memoria/seguimiento del corredor
pendiente a coordinacion por el ambito de escrituras de este worker.

`git rev-parse HEAD origin/master`:

```text
35fdb0e5edb75ce55827af99d3c90301e9c30ff2
dd5b7098b3714219a3a5fc6a2c17964c0baa4d7f
```
