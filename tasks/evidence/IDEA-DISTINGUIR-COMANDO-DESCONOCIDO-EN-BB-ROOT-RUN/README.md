# Evidencia — IDEA-DISTINGUIR-COMANDO-DESCONOCIDO-EN-BB-ROOT-RUN

## Referencia histórica

Base exacta: `7c2d71584ba381fbda9a35cbc757b8efc25e266e`. Se conserva la evidencia que
acompañó esa base y el close_check original en el objeto versionado:

```sh
git show 7c2d71584ba381fbda9a35cbc757b8efc25e266e:tasks/evidence/IDEA-DISTINGUIR-COMANDO-DESCONOCIDO-EN-BB-ROOT-RUN/README.md
```

La revisión posterior confirmó colisión de rc 4: `adopted/root-scripts/apt-guardia-instalar.sh`
usa `exit 4` en líneas 82, 87, 190 y 211; `adopted/root-scripts/earlyoom-proteger.sh`
en líneas 74 y 114. `tools/reloj_atascado.py` conserva rc y salida en sus diagnósticos;
`tools/dmem_tope.py` trata cualquier rc distinto de cero como fallo.

## Selección del código reservado

Se eligió rc **193**. Cotejo literal del host, serializado con el lock:

```sh
TMPDIR=[RUTA_LOCAL_PRIVADA] flock -x [RUTA_LOCAL_PRIVADA] python3 -c 'import signal; n=max(int(s) for s in signal.valid_signals() if int(s)>0); print(f"max_signal={n} signal_exit_status_range=129..{128+n} reserved_candidate=193")'
```

```text
max_signal=64 signal_exit_status_range=129..192 reserved_candidate=193
```

193 es distinto de rechazo general 3, colisión histórica 4 y timeout 124; queda
fuera de `128+N` para todas las señales del host. Un nombre válido no aprobado
devuelve 193. Si un script aprobado devuelve 193, el runner devuelve 1, guarda
`rc=1` y `rc_script=193` en `evento=fin`, y muestra ambos valores en stderr. Para
scripts sin colisión, stderr y la fila `fin` mantienen su forma anterior y el rc se
propaga exactamente.

## Close check canónico

Se conservó intacto el selector original de la ficha. El mismo caso focal incluye la
colisión rc193, así que este close_check detecta si se omite el remapeo:

```sh
TMPDIR=[RUTA_LOCAL_PRIVADA] flock -x [RUTA_LOCAL_PRIVADA] python3 -m pytest tests/test_bb_root_run.py -k comando_desconocido_codigo_propio -q
```

```text
.                                                                        [100%]
1 passed, 68 deselected in 0.10s
```

## Suite focal y negativos

Banco crea manifiesto, scripts y salidas sintéticos en el scratch indicado por
`TMPDIR`; no usa sudo, archivos operativos, servicios ni hardware.

```sh
TMPDIR=[RUTA_LOCAL_PRIVADA] flock -x [RUTA_LOCAL_PRIVADA] python3 -m pytest tests/test_bb_root_run.py -q
```

```text
.....................................................................    [100%]
69 passed in 3.18s
```

La suite prueba los negativos solicitados: script aprobado `exit 193` -> retorno 1,
auditoría con ambos rc y stderr con ambos valores; script `exit 4` conserva rc y
stderr/fila `fin`; nombre desconocido devuelve 193; nombre malformado y hash
incorrecto conservan rc 3. La prueba de señales confirma que 193 está fuera de los
estados `128+N` medidos en este host.

Control mutacional del remapeo (plugin temporal de pytest en el scratch): se sustituye
`rc_publico_script` por identidad, omitiendo el mapeo. El mismo close_check falla como
debe; eso demuestra que detecta el defecto:

```sh
PYTHONPATH=[RUTA_LOCAL_PRIVADA] TMPDIR=[RUTA_LOCAL_PRIVADA] flock -x [RUTA_LOCAL_PRIVADA] python3 -m pytest -p omit_mapping_plugin tests/test_bb_root_run.py -k comando_desconocido_codigo_propio -q
```

```text
F                                                                        [100%]
____________________ test_comando_desconocido_codigo_propio ____________________
tests/test_bb_root_run.py:132: in test_comando_desconocido_codigo_propio
    assert b.run("rc-reservado") == 1
E   AssertionError: assert 193 == 1
E    +  where 193 = run('rc-reservado')
E    +    where run = <test_bb_root_run.Banco object at 0xe483e4a9a720>.run
----------------------------- Captured stderr call -----------------------------
[bb-root-run] rc=193 rc_script=193 salida=[RUTA_LOCAL_PRIVADA]
FAILED tests/test_bb_root_run.py::test_comando_desconocido_codigo_propio - AssertionError: assert 193 == 1
1 failed, 68 deselected in 0.07s
```

Este fallo es el negativo mutado esperado; la ejecución normal pasa. Suite normal:
69 passed; mutante: 1 failed; could_not_run: 0.

## Cierre local

Se mantuvieron sin cambio los scripts aprobados, el manifiesto y sudoers. El cambio
reduce la propagación exacta solo para el retorno reservado 193; la auditoría conserva
el original y la interfaz expone el retorno remapeado. El close_check canónico quedó
intacto; los negativos adicionales lo complementan.
