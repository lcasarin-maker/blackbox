---
id: DEBT-KIT-SYNC-DE-FLOTA-NO-ESCALONA-LOS-PROYECTOS-01
kind: task
domain: MEMORY
title: "El comando de sync de flota del kit reparte a todos los proyectos a la vez; debe escalonarlos"
status: done
closed_at: 2026-10-17
closure_type: void_wontfix
reason: "el kit de Simplecode que se sincronizaba a la flota se retiro entero de este repo el 2026-10-17 (DECISIONS.md); ya no hay sync de flota ni atestaciones por commit que escalonar"
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-16
close_check: {"cmd": "test ! -e .simplecode/run.py", "expect": "exit_zero", "porque": "El sujeto desaparecio: sin lanzador del kit no hay sync de flota ni atestacion por commit."}
---

## Medido
Voto de Luis 2026-10-16 (`DECISIONS.md`, `sync_de_flota_escalonado`): el portero local ordena las suites de esta maquina, pero el reparto del sync lo lanza el kit de simplecode. Bloqueada por upstream: debe cambiarse en simplecode. `twiner`, `020` y `atlas` tambien debian confirmar la regla provisional.

## Medido 2026-10-17: la atestacion de cobertura por commit tambien es una estampida
Con el kit 10.2.4 el hook post-commit lanza `coverage_attestation --background`, una suite completa con cobertura, por CADA commit. `.simplecode/evidence/coverage_attestation_attempts.jsonl` (103 intentos en 2 dias, 88 el 2026-10-16 y 15 el 2026-10-17): 39 `started`, 28 `could-not-run`, 17 `superseded`, 10 `attested`, 9 `failed`; 103 min de suite sumados. Con la memoria libre en 15 % `earlyoom` mato workers de pytest de esas corridas y de los push (2 pushes caidos por `worker crashed`, sin test fallido). El escalonamiento que pide esta ficha debe cubrir tambien las atestaciones en segundo plano: una a la vez por maquina, y la nueva reemplaza a la anterior ANTES de arrancar, no despues.

## Medido 2026-10-17, 09:10 (la ATOM "super sluggish"): un sync de flota ya causo una hora de suite
- 08:20:26-27: cuatro scopes `run-r*` con `.simplecode/run.py simplecode.verification.*` de simplecode arrancaron dentro del mismo segundo (journal del usuario), mas un servicio batch de otro proyecto desde las 08:16.
- 08:23: otra sesion commiteo `chore(kit): sync satellite kit to simplecode 10.2.6` (2d8df6e1) en ESTE repo; el anterior fue `10.2.4` a las 23:48 del dia 16 (dos syncs en 9 h). El hook post-commit lanzo la atestacion de cobertura.
- `coverage_attestation_attempts.jsonl`: 08:23:39 `started` pid 155078; 09:24:43 `failed` tras 61.1 min (la suite sin carga tarda 4-6 min), y un segundo intento del mismo SHA `failed` tras 24.9 min. El log: `3 failed, 3726 passed ... in 3659.62s`, un worker de xdist caido (`worker 'gw1' crashed`) y dos fallas que pasan solas (`test_el_que_mas_crece_lleva_su_origen_en_la_muestra`: 1 passed en 2 s).
- Las muestras de `bb` 08:24-09:24 nombran un solo worker de pytest-xdist al 100 % de un nucleo durante 60 minutos; carga 11-16; a las 09:15-09:19 `MemAvailable` bajo a 21 GiB con `mem_full` 5.6 %.
Conclusion: el escalonamiento que pide esta ficha debe cubrir tambien lo que un commit de sync dispara en cada proyecto (la atestacion completa), no solo el reparto del comando de sync.

## Medido 2026-10-17, 20:50: el gate de pyright de los satelites resuelve `simplecode` del arbol del repo madre, no del kit fijado
El push de 4.6.0 fallo en `pyright (type checking)`: `tools/mutacion_alcanza.py` -> `"mutation_verify" is unknown import symbol`. Causa: pyright usa el paquete `simplecode` instalado en editable desde el repo madre (`python3 -c "import simplecode; print(simplecode.__file__)"` -> `.../projects/simplecode/src/simplecode/__init__.py`) y otra sesion lo estaba reestructurando en ese momento (`git status` del madre: 417 borrados y 75 añadidos sin commitear desde las 20:27; `src/simplecode/verification/` quedo con `__init__.py` y `pii_scan.py`). Misma causa que `python3 -m simplecode.cli audit` dejando de existir ("choose from check, integrity, pii"). Un satelite puede quedar bloqueado en su push por trabajo sin commitear de otro proyecto. En este repo se corrigio la unica importacion afectada cargandola con `importlib` del zip del kit (commit del mismo dia); el defecto de fondo es del gate del kit: debe resolver `simplecode` desde `.simplecode/runtime.zip`, no del entorno. Quien use `python3 -m simplecode.cli` en este repo debe usar `python3 .simplecode/run.py simplecode.cli` (el ejecutor del kit).

## Cierre 2026-10-17
Voto de Luis: sustituir por completo el Simplecode anterior. Las mediciones de arriba (08:20 y 09:10) quedan como la razon medida de por que la pila anterior era lenta: cada commit lanzaba una suite completa de atestacion y un sync de flota la disparaba a la vez en todos los proyectos.
