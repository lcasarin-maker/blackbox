---
id: DEBT-PORTERO-IGNORA-SU-INTERRUPTOR-01
kind: task
domain: MEMORY
title: "El portero actua siempre: tools/portero.py no lee su interruptor (observar/actuar/off)"
status: open
severity: P2
origin: detected
detector: {"rule": "grep -c interruptores tools/portero.py == 0 mientras interruptores.json declara un modo 'portero'", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-14
close_check: {"cmd": "python3 -m pytest -q tests/test_portero.py::test_demonio_respeta_el_interruptor", "expect": "exit_zero", "porque": "Cierra cuando el demonio consulta interruptores.modo('portero') y una prueba demuestra las tres ramas: en off no hace nada, en observar registra lo que haria sin crear scopes ni congelar, en actuar adopta. Hoy la prueba no existe (rc=4) porque el demonio no tiene esa rama."}
---

## Medido (2026-10-14)
Resto declarado al cerrar `DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01` (ver su `medicion.txt`):

- `python3 -c "from tools import interruptores as i;print(i.modo('portero'))"` -> `actuar`.
- `grep -c interruptores tools/portero.py` -> `0` (rc=1). `cmd_demonio` llama a `_ciclo`, que llama a `aplica` sin condicion: el demonio crea scopes y congela con cualquier modo.
- Consecuencia medida: `tasks/evidence/FEATURE-PORTERO-UNIVERSAL-DE-LA-MAQUINA-01/medicion.txt` dice "el demonio esta en observar, solo registra", y ese mismo dia el portero ya actuaba (los tres `turno`/`fin` y, desde 13:54 UTC, `congelar`/`descongelar` en `portero.jsonl`). La boleta de Luis del 2026-10-14 pedia observar primero y descartaba actuar directo: el interruptor no podia garantizarlo.

## Arreglo propuesto
`cmd_demonio` lee `interruptores.modo("portero")` en cada vuelta (es un archivo de pocos bytes): `off` no observa ni actua; `observar` registra las acciones con `"modo": "observar"` sin llamar a `_adopta`/`congela`; `actuar` como hoy. Prueba con `Efectos` falsos y un `interruptores.json` temporal para las tres ramas, y control negativo: en `observar` el ejecutor falso no recibe ninguna llamada.

## Arreglo (2026-10-14, worktree agent-a0e9d357) -- close_check rc=0, listo para cerrar
Evidencia: `tasks/evidence/DEBT-PORTERO-IGNORA-SU-INTERRUPTOR-01/medicion.txt` (close_check antes rc=4, con la prueba y el codigo viejo rc=1, despues rc=0; 12 mutaciones muertas de 12).

Comportamiento por modo (docstring de `tools/portero.py`):
- `off`: el demonio no lee /proc, PSI ni cgroups y no actua; una fila `{"accion": "off", "modo": "off"}` al entrar en off, ninguna mas mientras siga. `--contenedores` tampoco corre.
- `observar`: mide y decide igual (`decide` sigue pura); `aplica` no llama al ejecutor ni escribe `cgroup.freeze`; registra `habria_<accion>` con `"modo": "observar"`, una vez por cambio de motivo. Contenedores: `acotaria` sin `docker update`. Como nada se adopta, lo registrado es la primera decision sobre cada arbol, no la secuencia que `actuar` produciria.
- `actuar`: como antes; sus filas no llevan `modo`.
- El modo se relee en cada vuelta: cambiarlo no exige reiniciar `bb-portero.service`.
- Unica accion fuera de `actuar` (decidida en este arreglo, no estaba en la ficha): descongelar los scopes `bb-portero-*` que el propio portero dejo congelados (lista app.slice, no lee /proc). Sin esto, pasar de `actuar` a `off`/`observar` con una suite congelada la dejaria congelada para siempre, porque nadie le volveria a dar turno. Es volver al comportamiento de antes del portero.

`bb portero run --clase suite -- cmd` (decidido con el codigo): es una peticion EXPLICITA de quien lanza su propio comando, no el demonio actuando sobre un arbol ajeno, asi que en TODO modo lanza bajo `bb-portero-<clase>-<pid>.scope` con el tope de la clase. El interruptor solo gobierna la cola: `actuar` espera turno (como antes); `observar` decide una vez, registra `habria_esperar` si le habria tocado esperar y lanza sin esperar, siempre en `app.slice` (nunca `mover`); `off` no entra a la cola. Medido: ningun hook del repo llama hoy a `bb portero run` (`grep -rn "portero run"`: solo bin/bb ayuda, el docstring y las fichas).

Modo real al arreglar: `actuar` -> el comportamiento de produccion de esta ficha no cambia (lee un archivo de pocos bytes por vuelta; `bb portero estado` gana la clave `modo`).
