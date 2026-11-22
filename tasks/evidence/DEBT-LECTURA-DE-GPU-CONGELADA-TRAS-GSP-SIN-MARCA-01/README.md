# Evidencia offline — calidad de lectura GPU

Estado: candidato funcional parcial, ficha abierta. El alcance fue sintético; no consultó GPU, `nvidia-smi`, `/proc`, `/sys`, journal ni servicios durante la selección final.

## Contrato observable

- `gpu` y `ts` conservan su contenido. `gpu_calidad` se añade al final del registro de 1 s y junto a la lectura GPU del sampler de consulta.
- `edad_entrega_s` mide desde la última salida completa transportada con identidad válida. Una repetición idéntica en un tick nuevo da `edad_entrega_s=0` y mantiene creciente `edad_contenido_s`. Un error conserva la edad anterior. Un campo requerido ausente produce `no_comparable` y puede renovar solo la edad de entrega.
- Las edades son monotónicas, dentro de una instancia del proceso. Retroceso o valor no finito invalida las dos anclas. No cruza reinicio ni boot.
- El stream lleva índice de dispositivo en el transporte y lo excluye de `gpu`. Acumula filas con un solo índice usando la última; índices mezclados son `ambiguo`. Conserva un fragmento de línea para el tick siguiente. Cuatro métricas finitas requeridas permiten comparación; el quinto campo `memory.used` acepta `[N/A]`. En un lote A→B→A, cada fila completa se observa en orden, así que `gpu` preserva la última A mientras calidad declara `cambio`, edad de contenido cero y racha reiniciada. El índice distingue el mismo dispositivo entre filas; el CSV no da UUID, por eso filas del mismo índice se toman como un flujo y varios índices en un tick se rechazan.
- La consulta 5 s incluye índice, timeout y comprobación de `returncode`; stdout vacío declara ausencia y varias filas se rechazan como ambiguas. Los datos internos de índice y transporte no se serializan.
- La corroboración GSP usa `reboot_verdict.gpu_del_boot()` como autoridad: firma de timeout y tiempo monotónico salen de la misma línea parseada; requiere journal legible, boot idéntico, intervalo de sospecha explícito, tiempo no futuro e incertidumbre finita. Para avisar también exige al menos dos observaciones de calidad del mismo boot, dentro del intervalo, frescas, iguales y con edad de contenido creciente. Solo registra dedup tras ACK; fallo permite reintento y caída entre ACK y registro puede duplicar. `main()` del aviso no activa la ruta.

## Verificaciones ejecutadas

Comando focal, bajo `flock -x` y con `HOME`, `BLACKBOX_DATA` y `TMPDIR` sintéticos; salida literal guardada en scratch como `focales.log`:

```text
19 passed in 0.12s
```

Incluye la entrada real `main()` del stream con `os.pipe()` real para fragmento/sufijo y lote A→B→A, más filas iguales por tick, filas mezcladas, identidad que cambia, N/A opcional/requerido y ausencia. Para la entrada de consulta cubre `leer_gpu()` con `rc=7` más stdout aparentemente válido, NaN/inf y `muestrear()` con dos lecturas iguales, error y N/A; los límites `/proc`, `/sys`, journal, memoria y alertas quedan sustituidos. Aviso usa `hechos(CON)` y un receptor sintético.

Arranque aislado desde cwd ajeno: carga ambos módulos por ruta absoluta con `env -i` y `/usr/bin/python3 -I`, sin llamar `main()`:

```text
IMPORTS_OK 2
```

Comando reproducible desde la raíz del repo (el hijo ejecuta desde el `TMPDIR` sintético):

```bash
set -e
REPO="$(git rev-parse --show-toplevel)"
SCRATCH_BASE="${BLACKBOX_GPU_CHECK_DIR:-$HOME/scratch/blackbox/2026-11-21-deuda-retoma-director/calidad-gpu/revision}"
mkdir -p "$SCRATCH_BASE/import-home" "$SCRATCH_BASE/import-data" "$SCRATCH_BASE/import-tmp"
cd "$SCRATCH_BASE/import-tmp"
env -i PATH=/usr/bin:/bin HOME="$SCRATCH_BASE/import-home" \
  BLACKBOX_DATA="$SCRATCH_BASE/import-data" TMPDIR="$SCRATCH_BASE/import-tmp" \
  /usr/bin/python3 -I - "$REPO" <<'PY'
import importlib.util
import sys
from pathlib import Path

repo = Path(sys.argv[1])
mods = []
for name, path in (("muestreo_entry", repo / "tools/muestreo_1s.py"),
                   ("atom_entry", repo / "tools/atom_gpu_telemetry.py")):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    mods.append(module)
print("IMPORTS_OK", len(mods))
PY
```

`git diff --check` no produjo salida. `gpu_calidad_tracker` se pasa aparte del diccionario de estado persistido. El `close_check` de grep en frontmatter se conserva como límite pendiente; el cuerpo propone una prueba funcional con recibo y clasificación separada `PASS` / `FAIL` / `COULD_NOT_RUN`.

## Negativos semánticos incluidos

- `rc=7` invalida stdout con forma válida.
- Dos índices en un tick impiden renovar entrega y conservar una mezcla como muestra fresca.
- `[N/A]` en métrica requerida es no comparable; `[N/A]` en memoria opcional permite comparar entregas idénticas.
- Boot distinto, timestamp futuro, journal ilegible o falta de receptor impiden corroborar/enviar.
- Receptor fallido no consume la clave; ACK exitoso deduplica en el proceso.

## Close check funcional copiable

El frontmatter conserva su `grep` canónico hasta que se acepte formalmente un sustituto. Este comando enumera nodos seguros explícitos, clasifica `PASS`, `FAIL` y `COULD_NOT_RUN`, y conserva el rc original de pytest en `pytest.rc`. `COULD_NOT_RUN` cubre ejecución/colección sin recibo o sin casos, además de skips y errores de colección/setup. Una aserción fallida es `FAIL`; el recibo muestra todos los conteos y el rc de pytest.

```bash
set -e
SCRATCH_BASE="${BLACKBOX_GPU_CHECK_DIR:-$HOME/scratch/blackbox/2026-11-21-deuda-retoma-director/calidad-gpu/revision}"
LOCK="${BLACKBOX_GPU_TEST_LOCK:-$HOME/scratch/blackbox/2026-11-21-deuda-retoma-director/pruebas.lock}"
if ! mkdir -p "$SCRATCH_BASE"; then echo 'COULD_NOT_RUN scratch_base'; exit 2; fi
if ! RUN="$(mktemp -d "$SCRATCH_BASE/run.XXXXXX")"; then echo 'COULD_NOT_RUN mktemp'; exit 2; fi
if ! mkdir -p "$RUN/home" "$RUN/data" "$RUN/tmp"; then echo 'COULD_NOT_RUN scratch_dirs'; exit 2; fi
set +e
flock -x "$LOCK" \
  env HOME="$RUN/home" BLACKBOX_DATA="$RUN/data" TMPDIR="$RUN/tmp" \
  PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  python3 -B -m pytest -p no:cacheprovider -q --junitxml="$RUN/results.xml" \
  tests/test_muestreo_1s.py::test_calidad_distingue_entrega_de_contenido \
  tests/test_muestreo_1s.py::test_reloj_invalido_no_reancla_aunque_haya_entrega \
  tests/test_muestreo_1s.py::test_fsync_por_linea \
  tests/test_muestreo_1s.py::test_main_dos_filas_acumuladas_mismo_indice_actualiza_ultima_legacy \
  tests/test_muestreo_1s.py::test_main_no_mezcla_dos_identidades_y_conserva_fragmento \
  tests/test_muestreo_1s.py::test_main_recompone_fila_fragmentada_entre_ticks \
  tests/test_muestreo_1s.py::test_main_n_a_en_memoria_opcional_conserva_comparacion \
  tests/test_muestreo_1s.py::test_main_n_a_en_metrica_requerida_es_no_comparable \
  tests/test_muestreo_1s.py::test_main_entrega_igual_refresca_solo_edad_de_entrega \
  tests/test_muestreo_1s.py::test_main_cambio_de_identidad_cuenta_como_cambio_de_contenido \
  tests/test_muestreo_1s.py::test_main_recompone_con_pipe_os_real \
  tests/test_muestreo_1s.py::test_main_pipe_cambio_intermedio_aba_marca_cambio_y_preserva_ultima \
  tests/test_atom_gpu_telemetry.py::test_rc_no_cero_invalida_stdout_aparentemente_valido \
  tests/test_atom_gpu_telemetry.py::test_metricas_gpu_no_finitas_no_califican_lectura \
  tests/test_atom_gpu_telemetry.py::test_leer_gpu_rechaza_multiples_identidades \
  tests/test_atom_gpu_telemetry.py::test_nvidia_smi_falla_y_devuelve_vacio_declara_la_ausencia \
  tests/test_atom_gpu_telemetry.py::test_muestrear_conserva_orden_zonas_ts_boot_antes_de_consulta \
  tests/test_atom_gpu_telemetry.py::test_muestrear_emite_edad_de_entrega_sin_serializar_tracker \
  tests/test_aviso_gpu_reset.py \
  tests/test_gpu_calidad.py::test_entrega_identica_renueva_entrega_y_no_contenido \
  tests/test_gpu_calidad.py::test_reloj_regresivo_invalida_anclas \
  > "$RUN/pytest.log" 2>&1
pytest_rc=$?
set -e
printf '%s\n' "$pytest_rc" > "$RUN/pytest.rc"
python3 - "$RUN/results.xml" "$pytest_rc" <<'PY'
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

xml_path, pytest_rc = Path(sys.argv[1]), int(sys.argv[2])
expected_tests = 32
if pytest_rc == 127 or not xml_path.is_file():
    print(f"COULD_NOT_RUN tests=0 assertion_failures=0 errors=0 skipped=0 pytest_rc={pytest_rc}")
    raise SystemExit(2)
try:
    root = ET.parse(xml_path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    tests = sum(int(s.get("tests", 0)) for s in suites)
    failures = sum(int(s.get("failures", 0)) for s in suites)
    errors = sum(int(s.get("errors", 0)) for s in suites)
    skipped = sum(int(s.get("skipped", 0)) for s in suites)
except (ET.ParseError, OSError, ValueError):
    print(f"COULD_NOT_RUN tests=unknown assertion_failures=unknown errors=unknown skipped=unknown pytest_rc={pytest_rc}")
    raise SystemExit(2)
counts = f"tests={tests} expected={expected_tests} assertion_failures={failures} errors={errors} skipped={skipped} pytest_rc={pytest_rc}"
if tests == 0:
    print(f"COULD_NOT_RUN {counts}")
    raise SystemExit(2)
if failures:
    print(f"FAIL {counts}")
    raise SystemExit(1)
if tests != expected_tests or errors or skipped or pytest_rc:
    print(f"COULD_NOT_RUN {counts}")
    raise SystemExit(2)
print(f"PASS {counts}")
PY
```

Nodos excluidos: `tests/test_muestreo_1s.py::test_linea_con_datos_vivos` lee `/proc`; el resto de `test_atom_gpu_telemetry.py` incluye cobertura histórica más amplia fuera de esta frontera. En aviso, las pruebas que llaman `main()` sustituyen boot-id, journal, ruta y receptor; no invocan `lee_journal` ni el envío real. El control negativo del runner muta el loop para procesar solo la última fila y debe devolver `FAIL`; una selección inexistente produce rc 4, cero casos y `COULD_NOT_RUN`.

### Contraste de mutación y clasificación (2026-11-21)

- PASS anterior excluido: `32 passed in 0.19s`, `revision/run.G1tKQG/pytest.log`. La revisión Terra encontró que `test_fsync_por_linea` llamaba `muestra()` sin aislar lecturas de `/proc` y `/sys`; el resultado no acredita el selector seguro.
- El nodo legacy de stdout vacío quedó aislado: `leer_gpu` usa stdout sintético, boot sintético y suplanta memoria, PSI, vLLM, procesos GPU, journal y alertas; el expected distingue cero filas de formato parcial.
- Mutante no discriminante inicial: `1 passed in 0.02s`; alteró únicamente el ajuste final de comparación, y queda conservado como `revision/mutant-no-discriminante.log`.
- Mutante discriminante: cambió `for ... in filas` a `for ... in filas[-1:]`; la aserción vio `igual` frente a `cambio`, `1 failed`, rc 1 y clasificador `FAIL tests=1 expected=32 assertion_failures=1 errors=0 skipped=0 pytest_rc=1`, en `revision/mutant-discriminante.log` y `revision/mutant-discriminante.xml`.
- COULD_NOT_RUN por colección: selección de nodo inexistente, rc 4, `tests=0 assertion_failures=0 errors=0 skipped=0`; evidencia `revision/cnr-collection/pytest.log` y `revision/cnr-collection/no-tests.xml`.
- COULD_NOT_RUN de un borrador del runner: `flock: cannot open lock file : No such file or directory`, rc 66, sin XML en `revision/run.a0jDhW/pytest.log`; la variable `LOCK` faltaba. Se corrigió el comando y la repetición final creó recibo y pasó los 32 casos.
- COULD_NOT_RUN con fallo de scratch sintético: `mkdir: cannot create directory ‘…/revision/not-a-directory’: File exists`, luego `COULD_NOT_RUN scratch_base`, runner rc 2 en `revision/cnr-scratch-synthetic.log`. Un control anterior intentó `mkdir` en `/proc/bb-gpu-check-forbidden`, recibió `No such file or directory` y rc 2 (`revision/cnr-scratch.log`); se conserva el intento/error sin inferir acceso cero.

### Revalidación de aislamiento de `fsync`

`test_fsync_por_linea` conserva tres aserciones de `os.fsync` por archivo, pero `muestra()` ahora usa un stub de `rd` y otro de `glob`; el test registra las cuatro rutas consultadas por registro y bloquea con `AssertionError` cualquier `open()` a `/proc` o `/sys`. El negativo del guard llama a la ruta `/proc/close-check-guard` a través de ese wrapper y verifica el rechazo antes de delegar en `open`.

El RED inicial de la guarda estaba incompleto: faltaban `/proc/pressure/cpu` y `/proc/pressure/memory` en la lista esperada; prueba aislada rc 1, salida `revision/fsync/fsync-guard-expected-red.log`. Tras completar las cuatro rutas sintéticas: `1 passed in 0.03s`, rc 0, `revision/fsync/fsync-green.log`. Mutante que reemplaza `os.fsync(f.fileno())` por `pass`: `1 failed`, rc 1 porque se observaron `[]` en vez de tres llamadas, `revision/fsync/fsync-mutante.log`.

La corrida excluida `run.G1tKQG` atravesó el stub ausente: `registro()` intentó `/proc/loadavg`, `/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq`, `/proc/pressure/cpu`, `/proc/pressure/memory` y enumeró `/sys/class/thermal/thermal_zone*/temp`. No se copiaron valores. Sobre el intento previo de `mkdir /proc/bb-gpu-check-forbidden`: `mkdir` respondió `No such file or directory`; Orca confirmó luego que no se creó directorio. Este efecto se conserva separado del control sintético.

Tras aislar el nodo y auditar los restantes nodos del selector, el comando exacto de arriba dio `PASS tests=32 expected=32 assertion_failures=0 errors=0 skipped=0 pytest_rc=0`; salida `32 passed in 0.21s`, rc pytest `0`, recibos `revision/run.f7KTer/pytest.log`, `results.xml` y `pytest.rc`. `test_linea_con_datos_vivos` sigue excluido. El control negativo de `fsync` permanece eficaz (`llamadas == []`, `1 failed`, rc 1) en `revision/fsync/fsync-mutante.log`.

## Alcance excluido y pendiente

Una corrida anterior de 94 pruebas queda excluida del dictamen porque incluyó `test_linea_con_datos_vivos`, que lee `/proc` real. Se conserva comando, salida y efecto confirmado/desconocido en scratch privado sin copiar datos.

8 s queda refutado por la conciliación: 5 GSP y 1 de 6 controles sanos. No se implementó umbral, no se calibró en vivo y no se publicó corrección de foro. Falta revisión read-only del candidato, ruta efectiva de servicio, compatibilidad de consumidores y decisión operativa separada.

El reporte de privacidad sobre el SHA candidato está en scratch privado. El diff versionado de esta evidencia no contiene rutas de cuenta ni datos capturados.

### Reloj sintético del harness de `main` (incremental sobre 338c2448)

En `tests/test_muestreo_1s.py::_main_sintetico`, `main()` recibe la clase real `CalidadGPU` con una fábrica que le pasa un reloj sintético explícito. El `sleep` de cada vuelta avanza ese reloj exactamente 1 s antes de alimentar el `Pipe` sintético o el `os.pipe` local. Las pruebas de entrega idéntica comprueban `edad_entrega_s=0.0`, `edad_contenido_s=1.0`, y después de un tick vacío comprueban `edad_entrega_s=1.0`, `edad_contenido_s=2.0`. Las pruebas de cambio de identidad, fragmento recompuesto en `os.pipe` y lote A-B-A también comprueban edades exactas. No se modificó código de producción ni se definió umbral.

El bloque `Close check funcional copiable` de este README se extrajo sin cambios y corrió tres veces, con `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, bytecode/cache desactivados y `flock -x` sobre el lock autorizado. Cada ejecución clasificó `PASS tests=32 expected=32 assertion_failures=0 errors=0 skipped=0 pytest_rc=0`; logs: `~/scratch/blackbox/2026-11-21-deuda-retoma-director/calidad-gpu/reloj-338c/revision/run.F6KLUM/pytest.log`, `run.kC6WHs/pytest.log` y `run.Ml2U1N/pytest.log` (la última salida literal fue `32 passed in 0.22s`). `git diff --check` terminó con rc 0 y sin salida.

Controles negativos sobre copias scratch de `tools/muestreo_1s.py`, con el mismo test real seleccionado mediante `MUESTREO_1S_PATH`:

```bash
SCRATCH="$HOME/scratch/blackbox/2026-11-21-deuda-retoma-director/calidad-gpu/reloj-338c"
LOCK="$HOME/scratch/blackbox/2026-11-21-deuda-retoma-director/pruebas.lock"
```

- Mutante de producto que omite renovar `ultima_entrega` en una entrega idéntica: `flock -x "$LOCK" env MUESTREO_1S_PATH="$SCRATCH/negativos-finales/muestreo-producto-mutante.py" HOME="$SCRATCH/negativos-finales/producto/home" BLACKBOX_DATA="$SCRATCH/negativos-finales/producto/data" TMPDIR="$SCRATCH/negativos-finales/producto/tmp" PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -B -m pytest -p no:cacheprovider -q tests/test_muestreo_1s.py::test_main_entrega_igual_refresca_solo_edad_de_entrega`; `1 failed`, pytest rc 1, únicamente la aserción de `edad_entrega_s` del tick vacío (`2.0 == 1.0`), log `~/scratch/blackbox/2026-11-21-deuda-retoma-director/calidad-gpu/reloj-338c/negativos-finales/producto/pytest.log`.
- Mutante que sustituye `os.fsync(f.fileno())` por `pass`: `flock -x "$LOCK" env MUESTREO_1S_PATH="$SCRATCH/negativos-finales/muestreo-fsync-mutante.py" HOME="$SCRATCH/negativos-finales/fsync/home" BLACKBOX_DATA="$SCRATCH/negativos-finales/fsync/data" TMPDIR="$SCRATCH/negativos-finales/fsync/tmp" PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -B -m pytest -p no:cacheprovider -q tests/test_muestreo_1s.py::test_fsync_por_linea`; `1 failed`, pytest rc 1 en `llamadas == [f.fileno()] * 3` (`[]` observado), log `~/scratch/blackbox/2026-11-21-deuda-retoma-director/calidad-gpu/reloj-338c/negativos-finales/fsync/pytest.log`.
- CNR separado: `flock -x "$LOCK" env HOME="$SCRATCH/cnr-collection/home" BLACKBOX_DATA="$SCRATCH/cnr-collection/data" TMPDIR="$SCRATCH/cnr-collection/tmp" PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -B -m pytest -p no:cacheprovider -q tests/test_muestreo_1s.py::test_nodo_sintetico_inexistente --junitxml="$SCRATCH/cnr-collection/run.6zZClf/results.xml"` produjo `no tests ran`, pytest rc 4 y `COULD_NOT_RUN tests=0 assertion_failures=0 errors=0 skipped=0 pytest_rc=4`, log `~/scratch/blackbox/2026-11-21-deuda-retoma-director/calidad-gpu/reloj-338c/cnr-collection/run.6zZClf/pytest.log`.

Este delta cambia solo el fixture y las aserciones de `tests/test_muestreo_1s.py` y esta evidencia. La ficha y el `grep` canónico del frontmatter siguen abiertos.
