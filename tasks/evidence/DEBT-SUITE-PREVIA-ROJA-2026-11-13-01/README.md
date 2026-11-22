# Evidencia de microfases `control_racha` y `demonio_al_dia`

Fecha: 2026-11-21. Base común: `95e31d8296e42d0d65216df3e2b70f01e5d3df84`.
Las rutas `<scratch>` anonimizan los recibos, conservados en scratch privado.

## Microfase `control_racha`

### Reproducciones de falsos verdes

Con siete filas PSI altas, el corte real de 300 s debía bloquear. La base sí
retornó rc=1. Con `--corte nan`, o con siete `mem_full` ausentes, la misma base
imprimió `LIMPIO` y rc=0:

```text
python3 -B -m tools.control_racha --muestras <scratch>/alto --corte 300 --bajas 2
VEREDICTO: FALSO POSITIVO -- alguna regla reiniciaria la maquina fuera de todo incidente conocido.
rc=1

python3 -B -m tools.control_racha --muestras <scratch>/alto --corte nan --bajas 2
VEREDICTO: LIMPIO -- ninguna regla llega al corte. Margen del corte contra el peor caso sano: nanx
rc=0

python3 -B -m tools.control_racha --muestras <scratch>/sin-psi --corte 300 --bajas 2
VEREDICTO: LIMPIO -- ninguna regla llega al corte. Margen del corte contra el peor caso sano: 300000000000.00x
rc=0
```

### Marcadores mixtos: RED y GREEN

Las formas permitidas se cotejaron con el emisor versionado en `bin/bb`:
inicio: `ts`, `burst_inicio: true`, `motivo` texto; fin: `ts`, `burst_fin: true`.
También están las formas de metadato en `tests/test_cpu_top_invariante.py` y
en los commits `31f592bb` y `e893f10b`. El control de racha valida el timestamp
real y la forma exacta, sin importar el `ts` de texto de esa prueba ajena.

RED contra la implementación anterior; los dos híbridos (inicio/fin con
`mem_free_kb`) devolvieron `LIMPIO` rc=0 y fallaron por aserción, no por skip ni
`COULD_NOT_RUN`:

```text
python3 -m pytest -q -p no:cacheprovider --basetemp=<scratch>/red3 tests/test_control_racha.py -k "marcadores_de_burst_exactos or marcador_hibrido"
.FF.
2 failed, 2 passed, 33 deselected
```

GREEN, incluyendo positivos exactos para inicio y fin, rechazo de ambos
híbridos y tratamiento de `burst: true` como dato de una muestra PSI:

```text
python3 -m pytest -q -p no:cacheprovider --basetemp=<scratch>/green4 tests/test_control_racha.py -k "cli_"
24 passed, 14 deselected in 1.03s
could_not_run=0
```

El selector de registro de deuda usa una lectura sintética válida y mantiene el
control mutante de lanzador:

```text
python3 -m pytest -q -p no:cacheprovider --basetemp=<scratch>/debt-final2 tests/test_debt_registration_controls.py::test_debt_no_cover_control_racha_160
.                                                                        [100%]
1 passed in 0.35s
could_not_run=0
```

### Otros controles CLI

Claves JSON duplicadas (`mem_full` 77 seguido por 0), sobre las siete filas del
fixture proporcionado:

```text
python3 -B -m tools.control_racha --muestras <scratch>/duplicado --corte 300 --bajas 2
COULD_NOT_RUN: JSON inválido en <scratch>/duplicado/datos.jsonl:1
rc=2
```

El control final incluye valores sanos cero observados (rc=0), racha suficiente
(rc=1), y rc=2 para muestras sin `psi`, `psi` nulo/no objeto, PSI incompleta o
malformada, `mem_full` no numérico/no finito/fuera de `[0, 100]`, claves
duplicadas, cortes no finitos/no positivos y bajas no positivas.

La auditoría también mostró que el error de JSON por una cadena final sin cerrar
ubica `JSONDecodeError.pos` en la comilla inicial. La base devolvió
`COULD_NOT_RUN` para siete ceros seguidos del fragmento final `{"ts":"2025-01`;
la selección sintética Green confirma rc=0 con ese fragmento, sin terminador y
con muestras válidas previas. Una línea completa malformada con terminador y
claves duplicadas al EOF siguen devolviendo rc=2.

### Alcance

Las corridas usaron `HOME`, `BLACKBOX_DATA` y `TMPDIR` sintéticos, pytest sin
autoload/cache/bytecode y el flock acordado. No se leyó el corpus real por
defecto ni se ejecutaron los tests históricos que lo consumen, tests de
demonio/systemd, suite completa o cargas pesadas. La ficha de deuda permanece
abierta.

## Microfase `demonio_al_dia`

### Reproducción previa

`base.txt` registra el CLI en bwrap con `/proc` sintético, shim `systemctl` y
shim `stat`. Los casos de archivo anterior y posterior ya daban los resultados
esperados, pero igualdad devolvía rc=1 y `stat` fallido emitía
`integer expression expected` y también rc=1.

### RED y GREEN

Prueba nueva CLI aislada, antes del cambio de producción:

```text
python3 -m pytest -q -p no:cacheprovider --basetemp=<scratch>/red-full tests/test_demonio_al_dia_offline.py
......FFF...
3 failed, 9 passed in 0.23s
```

Los tres fallos reproducían mtime fuera de rango, `date` fallido con salida
numérica y `date` fuera de rango. La corrida RED anterior detectó igualdad,
`stat` fallido, vacío y texto no numérico: cuatro aserciones fallidas y cinco
pasadas. Los fallos fueron `assert result.returncode == expected`, no skips ni
`COULD_NOT_RUN` del arnés.

Después del cambio:

```text
python3 -m pytest -q -p no:cacheprovider --basetemp=<scratch>/green-final2 tests/test_demonio_al_dia_offline.py
............                                                             [100%]
12 passed in 0.21s
rc=0
```

Se ejecutaron 12 casos y hubo 0 skips/no ejecutados. Diez casos afirman
`COULD_NOT_RUN` rc=2: empate, stat fallido/vacío/no numérico/fuera de rango,
date fallido con salida, date fuera de rango, systemctl inaccesible, PID ausente
y fecha inválida. Archivo más viejo devuelve rc=0 y archivo más nuevo rc=1.
El log sintético verifica que ninguna recomendación `restart` se ejecuta.

Sintaxis y lint:

```text
bash -n tools/demonio_al_dia.sh && shellcheck tools/demonio_al_dia.sh
rc=0
```

### Control mutante

Se ejecutó en bwrap una copia scratch de `tools/demonio_al_dia.sh` desde la base
sin el arreglo, con el shim de igualdad. El control esperado del candidato es
rc=2; el mutante volvió a rc=1:

```text
fixture.service arranco 2025-01-02 00:00:00 UTC y /fixture/code.sh se modifico despues
el proceso vivo corre codigo VIEJO. Lo arregla: systemctl --user restart fixture.service
rc=1
```

Esto demuestra que el caso de empate distingue la regresión. El comando no
ejecutó `systemctl restart`; el texto es sólo la recomendación del mutante.

### Aislamiento y alcance

El aislamiento se prevalidó con `bwrap --unshare-all`, bind de sólo lectura de
`/usr` y `/lib`, `/proc` temporal y sin montar la raíz del host. Las pruebas
usan shims de `systemctl`, `stat` y `date`; ninguna consulta al gestor real,
`/proc` del host, `/sys`, journal, hardware, red o sudo. No se ejecutó
`tests/test_demonio_al_dia.py`, la suite global ni cargas. El estado canónico de
la ficha de suite sigue abierto/CNR.

## Candidato conjunto

El candidato se construyó sobre `95e31d8296e42d0d65216df3e2b70f01e5d3df84`
copiando los dos deltas netos aprobados, sin merge ni cherry-pick. Los cuatro
archivos de código y pruebas coinciden byte por byte con sus candidatos:

```text
control_racha.py       5279661405d7c985a3a715651086b7111de2a868ebd70172d2e8911297a3b284
test_control_racha.py  dc6ee09e2e6ea40c6d7c448df398c5b2d24f03d7fcba0aa41d96881e0abf8ce1
demonio_al_dia.sh      cad310ef2f2f15ca91d8bc9e9901c0262b6f16af7dd20a3340c10a78a8f4e171
test_demonio_offline   d8f84bbd67963f10707a0e28d76982e62b99fcaa7a267ec4026dec0d61655f9b
```

La corrida conjunta, con `HOME`, `BLACKBOX_DATA` y `TMPDIR` sintéticos,
autoload/cache/bytecode desactivados y el flock acordado, terminó así:

```text
python3 -m pytest -q -p no:cacheprovider --basetemp=<scratch>/pytest-control tests/test_control_racha.py -k cli_
24 passed, 14 deselected in 1.10s
python3 -m pytest -q -p no:cacheprovider --basetemp=<scratch>/pytest-debt tests/test_debt_registration_controls.py::test_debt_no_cover_control_racha_160
1 passed in 0.37s
python3 -m pytest -q -p no:cacheprovider --basetemp=<scratch>/pytest-daemon tests/test_demonio_al_dia_offline.py
12 passed in 0.22s
pipeline_rc=0
could_not_run=0, skips=0
```

Controles negativos sobre la implementación base (`95e31d82`) dieron fallos
de aserción, no CNR: `test_cli_lectura_invalida_es_could_not_run[psi0]` observó
`LIMPIO` rc=0 donde debía ser rc=2 (1 failed, 37 deselected); y el caso de
igualdad del demonio observó rc=1 y la recomendación de reinicio donde debía
ser CNR rc=2 (1 failed, 11 deselected). Ambos recibos literales están en
scratch privado. Los mutantes no ejecutaron recomendaciones ni tocaron
servicios.

La ficha conserva `status: open` y el `close_check` canónico de suite completa,
que continúa abierto/CNR. No se corrieron corpus vivo, tests de demonio real,
suite completa ni cargas pesadas.

El comparador de identidad también tuvo control negativo: agregar una línea a
una copia scratch del shell hizo que `cmp -s` retornara 1.

```text
cmp -s tools/demonio_al_dia.sh <scratch>/comparator/candidate.sh
cmp_mutated_rc=1 (expected 1)
```

El hook completo del commit pasó sus seis controles: ruff, gitleaks,
integridad, PII del rango de commit, sintaxis bash e inventario; todos con
`could_not_run=0`. Después se escaneó el árbol versionado del `HEAD` con
`simplecode policy --repo . pii -- --all-tracked`: `revisados=3995`
`hallazgos=0` `could_not_run=0`. El recibo literal del escaneo del `HEAD`
final, incluido su SHA, queda en scratch privado para no alterar el árbol tras
la comprobación.
