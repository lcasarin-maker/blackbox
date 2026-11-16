# Limpieza hacia adelante de privacidad — 2026-11-13

Alcance: remediacion de HEAD y gate obligatorio; reescritura pendiente.
Ficha `DEBT-GUARDA-PUBLICA-28-RUTAS-SOBRE-LINEA-BASE-01` sigue abierta.
21 archivos A tratados; 7 B admitidos con cuentas exactas y MOTIVOS, total 41.
SPEC.md conserva una referencia de compatibilidad exigida por el inventario,
dentro de su umbral anterior; el usuario de SPEC.md:297 fue retirado.

## Commits

d5bad497 fix(privacy): parametrizar destinos locales y sanear clase A
d9967fc9 test(privacy): admitir siete contratos de compatibilidad clase B
fec92311 gate(privacy): exigir guarda del snapshot completo en cada push
c9f28ae5 docs(privacy): registrar controles, transformaciones y reescritura pendiente
5d49599c docs(privacy): expresar rutas del comando con HOME

## Guarda y controles, comandos y salidas literales

`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_sin_datos_privados.py`

Antes: `1 failed, 4 passed in 3.31s`, rc=1.
Despues: `5 passed in 3.32s`, rc=0.
Tras la primera ampliacion documental: `5 passed in 3.92s`, rc=0.

Configuracion externa, regresion antes: `4 failed in 0.08s`, rc=1;
focal de WoL, boton rojo y configuracion despues: `41 passed in 13.06s`, rc=0.
Los destinos salen del codigo; la ausencia de configuracion bloquea.
Estos tests precedieron a la implementacion y comprueban lectura externa y ausencia.

Control en clon Git dentro de scratch, ejecutor real:
`PYTHONDONTWRITEBYTECODE=1 python3 "$HOME/scratch/blackbox/2026-11-13-remediacion/control.py"`.
Salida: `gate-limpio rc 0`, `guarda-negativa rc 1`, `gate-negativo rc 1`.
El ejecutor invoca `simplecode verify --hook pre-push --impact-base HEAD^`.
Guarda directa con el dato plantado: `1 failed, 4 passed in 4.52s`.
Luego lo comete en la copia y deja limpio el archivo del disco antes del gate.
El fallo de la fila obligatoria mide ese commit, aunque el disco ya esta limpio.

gate-limpio: `{"could_not_run": 0, "fail": 0, "pass": 5, "pending": 0}`.
Filas: datos-privados-publicacion=pass, pytest=pass, bb-cobertura-piso=pass, ceremony=pass, close-check=pass.

gate-negativo: `{"could_not_run": 0, "fail": 1, "pass": 3, "pending": 0}`.
Filas: datos-privados-publicacion=fail, pytest=pass, ceremony=pass, close-check=pass.

gate-final: `{"could_not_run": 0, "fail": 2, "pass": 3, "pending": 0}`.
Filas: datos-privados-publicacion=fail, pytest=fail, bb-cobertura-piso=pass, ceremony=pass, close-check=pass.

El primer gate del repo (c9f28ae5) detecto la ruta absoluta con usuario que
copie por error al documentar el comando; esa misma guarda y pytest bloquearon.
Se publico la correccion en un commit nuevo local, expresando la ruta con HOME;
se conserva la historia, y esa incorporacion/retirada cuenta en el inventario
para purga posterior. Los comandos originales completos permanecen en scratch.

Gate de repo: `PYTHONDONTWRITEBYTECODE=1 TMPDIR="$HOME/scratch/blackbox/r13" simplecode verify --hook pre-push --impact-base origin/master`.

## Suite y comparacion

Ejecutable y argumentos: `python3 -m pytest -q -p no:cacheprovider` con
basetemp en scratch de este repo y PYTHONDONTWRITEBYTECODE=1.
Lectura literal de la salida: `tail -n 1 "$HOME/scratch/blackbox/2026-11-13-remediacion/suite.txt"`.

`17 failed, 4570 passed, 8 skipped, 3 deselected, 1 warning in 618.35s (0:10:18)`; rc=1.

Comparador: `PYTHONDONTWRITEBYTECODE=1 python3 "$HOME/scratch/blackbox/2026-11-13-remediacion/comparar.py"`.
Resultado: baseline_count=18, actual_count=17, new=[], now_pass solo
`tests/test_sin_datos_privados.py::test_el_repo_no_gana_datos_privados`.
Control del comparador con un nodo ajeno: nuevos_real=0, nuevos_control=1.
Los otros 17 nodos de la ficha previa persisten, incluidos sus dos fallos de entorno.
La suite sigue roja; 8 skipped y 3 deselected se conservan como omisiones.

## Despliegues desalineados

- `/usr/local/lib/blackbox/tools/boton_rojo.py`: configurar usuario en
  `/etc/blackbox/rojo.json` o BB_ROJO_CONFIG/BB_ROJO_USUARIO antes de actualizar.
- Unit de usuario `bb-muestreo-corte.service`: crear
  `%h/.config/blackbox/muestreo.env` con BB_MUESTREO_SCRIPT antes de desplegar.
  El script que ejecuta actualmente queda donde esta, pendiente de su ficha.
- Copia autonoma de `bb_wol.py` en la Dell: configurar BB_WOL_CONFIG antes
  de actualizarla; ubicacion de la copia por comprobar al desplegar.
- `bb_alarma.py`: solo cambia el ejemplo; alarma.json privado ya conserva
  el comportamiento. La copia distribuida conserva el ejemplo anterior.
- `adopted/solo-registro.txt`: comentario neutralizado; revisar drift de la
  copia instalada, que se conserva hasta coordinar su actualizacion.

Sin operaciones de despliegue, instalaciones, sudo ni reinicios de servicios.
Ejemplos sinteticos versionados en config/; archivos locales ignorados.

## Evidencia transformada

Las huellas originales y transformadas se midieron, no se reconstruyeron.
La ficha distingue las copias redactadas de sus bytes originales; las referencias
historicas a huellas de otros artefactos conservan ese significado historico.

- `logs/memory_gate.jsonl`: anterior `da6ffaff00e224f484b3fb87429b1827d40c3e269fa6506c682c39e2f70dba3f`, transformado `5a57d6f24bfa1182462ace6727337348982aaebde696c313ce82dec30cd559ad`.

- `tasks/evidence/FEATURE-VENTANA-GPU-NOCTURNA-SECUENCIA-01/pass.txt`: anterior `ae17b1b6b0d264ce0718e82f1deb7c1178e43008c0f934c71c6cfee4d714db18`, transformado `2218392d122b75a1425490f1ef99c7c6fab2e46e90bbaec48ce5dc3e67e7d975`.

## Historia preparada, sin ejecucion de la segunda parte

Recorrido completo: `git log -p --all --no-ext-diff --format=COMMIT_PRIVACIDAD:%H`.
Se aplica la regex firmada a lineas agregadas y retiradas; dos fixtures sinteticos
explicitos se excluyen. Los candidatos adicionales quedan por adjudicar,
segun instruccion del coordinador; la lista prioriza conservar cualquier A retirado.
Archivo privado: `~/scratch/blackbox/2026-11-13-reescritura/valores-a-purgar.NO-PUBLICAR.txt`,
modo 600, formato marca TAB valor exacto, 78 valores distintos.

Conteos por clase: `{"HOST": 1, "IP_LAN": 25, "KB": 2, "MAC": 33, "PROYECTO": 16, "USUARIO": 1, "commits_afectados": 681}`.

Conteos por marca: `{"A-confirmado": 13, "A-histórico": 10, "candidato-sintético": 55}`.

A-confirmado: identidad presente en los archivos A de la evaluacion, SPEC
restringido al usuario. A-historico: tokens privados identificados por el patron.
Los IP/MAC restantes quedan por adjudicar como candidatos, incluidos posibles
valores operativos retirados. Las variantes de mayusculas se conservan exactas.

## Omisiones y estado

No se pudo correr en guarda y controles de privacidad: 0.
No se pudo correr segun counts de los gates: 0; pendientes=0.
Close-check informa `fichas_cerradas=1 ejecuta=0 no_ejecuta=1` sobre la ficha
historica de la ventana GPU: su ejecutor compuesto no esta en la lista.
Se conserva esa omision explicita; la evidencia transformada no cierra esa carencia.
Suite: 8 omitidos, 3 deseleccionados y 17 fallos persistentes.
Memoria de continuidad pendiente al coordinador por la restriccion de escrituras.
Reescritura, adjudicacion de candidatos y despliegues pendientes; ficha abierta.

Referencias observadas (`git rev-parse master origin/master`):

5d49599cfbec95fcb86ac2b0e8a3b2aef49c925f
dc1b544284c19cbea5f31db8b5c5b2a4863a07f9
