---
id: DEBT-PORTERO-NO-CLASIFICA-TANDAS-DE-LIBREOFFICE-DE-OTROS-PROYECTOS-01
kind: task
domain: MEMORY
title: "El portero no clasifica las tandas de LibreOffice de otros proyectos"
status: done
closed_at: 2026-10-17
closure_type: fixed
reason: "clasifica() da clase `libreoffice` a soffice/soffice.bin/oosplash con --headless y --convert-to (por forma, nunca por proyecto); la clase lleva turnos=1 y un techo de modo `observar` (Clase.modo + modo_efectivo) que hace que aplica y turno solo registren habria_* aunque el interruptor diga actuar. La clase suite queda igual: caracterizacion grabada contra el portero sin modificar."
evidence: {"pass": "tasks/evidence/DEBT-PORTERO-NO-CLASIFICA-TANDAS-DE-LIBREOFFICE-DE-OTROS-PROYECTOS-01.pass.txt", "fail": "tasks/evidence/DEBT-PORTERO-NO-CLASIFICA-TANDAS-DE-LIBREOFFICE-DE-OTROS-PROYECTOS-01.fail.txt", "e2e": "tasks/evidence/DEBT-PORTERO-NO-CLASIFICA-TANDAS-DE-LIBREOFFICE-DE-OTROS-PROYECTOS-01.e2e.txt"}
severity: P2
origin: detected
detector: {"rule": "tests/test_portero_clase_trabajo_ajeno.py::test_una_conversion_de_libreoffice_headless_tiene_clase", "confidence": 1.0}
satd_family: BLIND_INSTRUMENT
created: 2026-10-17
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider --runxfail tests/test_portero_clase_trabajo_ajeno.py::test_una_conversion_de_libreoffice_headless_tiene_clase", "expect": "exit_zero", "porque": "Medido 2026-10-17: el portero clasifica por forma (pytest y hooks pre-push/pre-commit de cualquier proyecto -> suite), pero una tanda de 13 procesos soffice --headless de otro proyecto no tiene clase y entra sin cola ni tope; con la memoria libre en 15 % earlyoom mato workers de pytest de un push (journal 23:36:28). Cierra cuando clasifica() le da clase a una conversion de LibreOffice headless y la cola la admite de una en una, entrando primero en observar."}
---

## Medido
- 2026-10-17, tras 3 pushes fallidos: `ps` mostro 13 procesos `soffice.bin --headless` (perfiles `soffice_perfil_preparacion_*`, tanda del proyecto otro proyecto) mas las suites `pre-push` de Atlas y Twiner. Carga 27-31 y `MemAvailable` 15 %.
- `journalctl -u earlyoom` 23:36:28: SIGTERM a un `python` de 1522 MiB (worker de xdist del push de este repo). Dos pushes cayeron por `worker crashed`, sin que ningun test fallara (pasan solos).
- `tools/portero.py::clasifica` clasifica por la forma del comando: pytest y hooks pre-push/pre-commit -> `suite`, de cualquier proyecto. `soffice` devuelve `None`: sin clase, sin cola y sin tope.

## Voto de Luis 2026-10-17
Abrir esta ficha. Entra primero en `observar` (registra lo que haria, como el resto del portero), no en `actuar`. Descartado: dejar que cada proyecto se autorregule (cada push sigue expuesto a que earlyoom mate sus workers).

## Que falta
Una clase para conversiones de LibreOffice headless (por forma, no por nombre de proyecto), con su tope y turnos, la prueba de `clasifica` de arriba y, antes de pasar a `actuar`, medir una tanda real. Riesgo a vigilar: congelar un trabajo ajeno puede alargarlo; el portero ya excluye lo que sostiene `index.lock`.

## Root Cause

`clasifica()` solo conocia la forma `suite` (pytest y hooks pre-push/pre-commit) y `CLASES` solo tenia esa clase:
un arbol `oosplash -> soffice.bin --headless --convert-to` devolvia `None`, y `_arboles_por_forma` lo descartaba
sin cola ni tope. Ademas el modo era uno solo para todo el portero (el interruptor `portero`, hoy en `actuar`):
anadir una clase la habria puesto a congelar y adoptar arboles de otro proyecto en cuanto se reiniciara el demonio,
contra el voto de entrar primero en `observar`.

Arreglo (tools/portero.py):
- `clasifica()`: `libreoffice` cuando argv[0] o argv[1] (lanzador de shell) es `soffice`, `soffice.bin` u
  `oosplash` y estan `--headless` y `--convert-to`. Se evalua despues de `suite`, que no cambia.
- `Clase.modo` (defecto `actuar`) es el techo de modo de la clase; `modo_efectivo()` toma el mas restrictivo
  (off < observar < actuar) entre el interruptor y ese techo. `aplica()` lo calcula por accion; `turno()` y
  `cmd_run` por clase. `suite` tiene techo `actuar`: su modo efectivo es el del interruptor, como antes.
- Clase `libreoffice`: MemoryMax 1 GiB, MemoryHigh 90 %, TasksMax 64, turnos 1, umbral RSS 0, techo `observar`.
  Medido 2026-10-17 sobre una tanda viva (30 s): 545 pids, hasta 10 soffice.bin a la vez, RSS de uno <= 236 220
  kB, suma <= 1 916 156 kB, vida ~1 s, <= 4 hilos. 20 GiB (suite) + 1 GiB caben en el app.slice de 42 GiB.

## Regression Test

- `tests/test_portero_caracterizacion_suite.py` (commit 10db38c4, ANTES del arreglo): `decide()` y `aplica()`
  (observar, off, y actuar sin efecto) de la clase `suite` en 16 escenarios (admitir; cola de dos y tres; turno
  ocupado congela al nuevo; al liberarse descongela al mas antiguo; index.lock no se congela; pre-push si; fuera de
  app.slice; ligero; PSI; freno termico; holgura; presupuesto; excluido Atlas; NOT_COLLECTED; /proc ilegible),
  grabados en `tests/fixtures/portero_suite_caracterizacion.json` contra el portero sin modificar. Control
  negativo: con 2 turnos en suite sale rojo.
- `tests/test_portero_clase_trabajo_ajeno.py`: clasifica (4 formas si, 5 no: shell que la nombra, GUI sin
  --headless, sin --headless, servidor `--accept`, driver del lote), pytest que nombra soffice sigue `suite`, la
  cola admite de una en una, las conversiones no cambian lo decidido para `suite`, `modo_efectivo` (off gana),
  aplica con el interruptor en `actuar` solo registra `habria_*` con `modo: observar` y no llama a systemd ni
  escribe cgroup.freeze (control: con techo `actuar`, la misma entrada llama a busctl), off registra off, y
  `turno` de `libreoffice` no espera (control: `suite` en el mismo mundo si espera).
- Ningun test existente cambio.

## Verification Evidence

- fail: el close_check sale 1 sobre 6ed1d1d0 (`assert None is not None`).
- pass: el close_check sale 0; 126 passed en las suites del portero + test_sin_datos_privados; 70 passed en
  inventario, memavail, procesos protegidos y controles de hooks; pyright 0 errores; ruff limpio.
- e2e: lee_estado/observar/decide/aplica reales contra la tanda viva, interruptor en `actuar`: 148 arboles en 15
  ciclos, 15 habria_admitir + 133 habria_congelar con `modo: observar`, 0 llamadas al ejecutor, 0 cgroup.freeze.
  Cinco mutaciones, cada una roja y revertida byte a byte.

## Avance 2026-10-17 -- lo que queda en manos de Luis

- Despliegue: el demonio corre el codigo anterior hasta que Luis reinicie el servicio de usuario:
  `systemctl --user restart bb-portero.service`. No necesita sudo ni cambiar el interruptor (sigue en `actuar`;
  la clase nueva queda en `observar` por su techo).
- Costo medido de `observar`: una fila por conversion, 4.86 filas/s y 3.4 kB/s en `portero.jsonl` mientras corre
  una tanda (101 195 bytes en 30 s; el log entero pesa hoy 2 179 486 bytes). El diccionario `ultimo` del demonio
  gana una clave por conversion (una por raiz) y no se poda.
- Que medir en `observar` antes de pasar la clase a `actuar` (cambiar `modo="observar"` por `"actuar"` en la clase,
  con voto): cuantas conversiones por tanda habria congelado y cuanto habria alargado la tanda (cada conversion
  vive ~1 s y llegan hasta 10 a la vez: turnos=1 las serializaria); si coincide con PSI alto o con suites del
  portero en curso; y si adoptar arboles que viven ~1 s con un intervalo de 2 s choca con pids que salen
  (DEBT-PORTERO-ADOPCION-CHOCA-CON-PIDS-QUE-SALEN-01). La alternativa a evaluar con esos datos es gobernar la tanda
  entera (su servicio) en vez de cada conversion.
