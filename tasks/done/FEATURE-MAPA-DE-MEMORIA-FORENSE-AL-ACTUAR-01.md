---
id: FEATURE-MAPA-DE-MEMORIA-FORENSE-AL-ACTUAR-01
kind: task
domain: MEMORY
title: "Mapa de memoria por dueno y rango capturado en el instante en que una guardia actua (idea del /internal/memory de Athena's Engine)"
status: done
closed_at: 2026-10-30
closure_type: fixed
reason: "tools/mapa_memoria.captura (stdlib, nunca lanza) arma por unidad clase y rango de data/rangos_memoria.json, memory.current, anon/file/shmem, memory.swap.current y dmem.current (con gpumem._pares); lo ilegible es NOT_COLLECTED. Lo llevan en la fila de su evento el escalon de bin/bb-usable al matar (antes de la senal), vigilante_memavail en cada fila que registra (antes de detener) y el portero al congelar y en habria_negado medido. Tope: 10 unidades de mayor memory.current mas la unidad sobre la que se actua, el resto contado (3.6 KB por fila medidos en esta maquina). 30 pruebas: sin accion no hay mapa, un mapa roto no cambia decision ni accion, y el codigo de antes (fe42e666) falla las cinco (a). Caracterizaciones de portero y bb-usable sin regrabar y en verde. bin/bb-usable no desplegado."
evidence: {"pass": "tasks/evidence/FEATURE-MAPA-DE-MEMORIA-FORENSE-AL-ACTUAR-01/pass.txt", "fail": "tasks/evidence/FEATURE-MAPA-DE-MEMORIA-FORENSE-AL-ACTUAR-01/fail.txt", "e2e": "tasks/evidence/FEATURE-MAPA-DE-MEMORIA-FORENSE-AL-ACTUAR-01/e2e.txt"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-30
close_check: {"cmd": "python3 -m pytest -q tests/test_mapa_memoria_al_actuar.py", "expect": "exit_zero", "porque": "Especificacion pendiente: el archivo de pruebas no existe hoy (rc=4 medido el 2026-10-30), asi que falla. Pasa solo cuando una accion de bb-usable, memavail o portero deje junto a su evento un mapa con anon, file, shmem y swap por dueno, y una prueba con control negativo (sin accion, sin mapa) lo demuestre."}
---

## Idea de origen y hueco propio

Athena's Engine expone `GET /internal/memory`, el mapa de quien tiene que memoria por prioridad (`Atlas/knowledge/references/github_com_xangel82_Athena_Engine.md`, seccion de servicios). El hueco de bb es medido: `DEBT-COLAPSO-CONFINADO-A-APP-SLICE-REINICIA-LA-MAQUINA-ENTERA-01` declara que el 2026-10-16 NO se capturo que tarea estaba atascada, ni `memory.stat` (anon, file, shmem), ni el swap de `app.slice`; `bb-usable` actuo (reinicio de la maquina) sin ese dato y la causa quedo como "inferido, no medido".

## Adaptacion

Cada vez que una guardia actua (escalon de `bb-usable`, `vigilante_memavail` en `actuar`, `portero` al congelar o negar) escribe, junto a su evento, un mapa de ese instante: por scope/unidad dueno, su clase o rango (cuando exista, ver `FEATURE-ARBITRO-MEMORIA-UNIFICADA-POR-PRIORIDAD-01`), `memory.current`, anon, file, shmem, `memory.swap.current` y la memoria de GPU de `tools/gpumem.py`. Es forense puro: no cambia ninguna decision.

## Para cerrar

1. Reutilizar lo que existe y leerlo antes de escribir codigo: el registro de origen de `bin/bb-usable`, `tools/origen_proceso.py`, `tools/gpumem.py`, `tools/presupuesto_memoria.py`. Aun no leidos en esta ficha.
2. Costo acotado: el mapa se escribe solo cuando hay accion, nunca en el camino de decision, y con tope de tamano por fila.
3. `tests/test_mapa_memoria_al_actuar.py`: (a) una accion simulada deja el mapa con los cinco campos; (b) control negativo: sin accion no se escribe mapa; (c) lectura ilegible de `memory.stat` deja `NOT_COLLECTED` en ese campo, nunca cero.

## Limites declarados

La memoria CUDA no contabilizada por cgroup sigue fuera salvo la que ve `dmem` (ver `FEATURE-1358-CGROUP-*`).

## Cierre (2026-10-30)

Lo leido antes de escribir: `tools/origen_proceso.py` (vocabulario NOT_COLLECTED, captura con plazo en bb-usable),
`tools/gpumem.py` (`_pares` lee `dmem.current`; se reusa cargado por ruta), `tools/presupuesto_memoria.py` (lee
`memory.current` por slice; no da nada por unidad que sirva aqui) y el registro de origen de `bin/bb-usable`
(`_cargar_origen` carga modulos de tools/ por ruta sin tocar sys.path; se generalizo con un parametro y carga tambien
`tools/mapa_memoria.py`).

Diseno: un modulo, `tools/mapa_memoria.py`, sin dependencias fuera de la biblioteca estandar (bb-usable corre como
root con FailureAction=reboot y lo carga por ruta; el portero tambien corre como script). `captura(rutas, clases,
obligatorias, tope)` nunca lanza; cada guardia ademas lo llama dentro de su propio try/except. El mapa va en la MISMA
fila del evento, clave `mapa_memoria`:

- escalon de `bin/bb-usable`: solo cuando hay objetivo (`accion == "matar"`), despues de decidir y antes de
  `ejecutar_muerte`; unidades = hijas de cada app.slice, mas el scope del objetivo siempre.
- `tools/vigilante_memavail.py`: en cada fila que registra (solo registra cuando dispara, en `observar` y `actuar`),
  antes de detener; unidades = las mismas que vio `elige_culpable`, mas la culpable siempre. Clase y rango con
  `RANGOS.clases`, lo mismo que uso la decision.
- `tools/portero.py`: en la fila de un `congelar` ejecutado (arbol observado, no virtual) y en `habria_negado` con
  `necesario_kb` (negativa medida, aplica y turno). No en `habria_congelar` de `observar`, ni en `admitir`,
  `esperar`, `descongelar` ni en la negativa NOT_COLLECTED: no son congelar ni negar.

Tope por fila: 10 unidades de mayor `memory.current` (las ilegibles al final) mas la unidad sobre la que se actua, y
del resto `omitidas`, `omitidas_bytes_legibles` y `omitidas_ilegibles`. Medido aqui: 68 unidades bajo
`user@1000.service` y 33 en app.slice; las 10 mayores dejan fuera 0.55 GB y 0.17 GB; el mapa pesa 3.6 KB por fila.
Solo se lee `memory.stat`, swap y dmem de las elegidas.

Interruptor: ninguno nuevo. Con el interruptor de cada guardia en `off` no hay filas, igual que antes. Con
`portero_admision` en `off` las filas no cambian: la caracterizacion del portero y `test_off_no_cambia_ni_decide_ni_las_filas`
pasan sin regrabar fixtures. Las filas de accion real (congelar ejecutado, muerte del escalon, disparo de memavail)
llevan un campo mas.

Limites declarados:
- Memoria CUDA no cobrada al cgroup: fuera, salvo la que ve `dmem` con el modulo parcheado. Hoy no existe
  `dmem.current` por cgroup en esta maquina: `gpu_dmem` sale NOT_COLLECTED en todas las unidades (e2e.txt).
- `bin/bb-usable` no esta desplegado: el demonio que corre es el de antes hasta que Luis reinicie `bb-usable.service`.
  Lo mismo para `bb-portero.service` y el vigilante memavail (no instalado).
- El mapa se toma ANTES de la accion en bb-usable y memavail; en el escalon eso suma a la muerte el tiempo del mapa
  (1.6 ms medidos aqui sin presion; bajo estancamiento, leer cgroupfs puede tardar mas, sin el `mmap_lock` de ningun
  proceso).
- La declaracion de COLAPSO de bb-usable (la que reinicia la maquina, el caso del 2026-10-16) no esta en el alcance de
  esta ficha: sigue sin mapa. Abierta como `FEATURE-MAPA-DE-MEMORIA-AL-DECLARAR-COLAPSO-01`.
- El control del control (`test_f_...`) usa `git show fe42e666...`: sin historia de git esa prueba falla, no se salta.
