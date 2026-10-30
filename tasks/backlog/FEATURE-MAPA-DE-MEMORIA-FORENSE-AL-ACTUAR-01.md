---
id: FEATURE-MAPA-DE-MEMORIA-FORENSE-AL-ACTUAR-01
kind: task
domain: MEMORY
title: "Mapa de memoria por dueno y rango capturado en el instante en que una guardia actua (idea del /internal/memory de Athena's Engine)"
status: open
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
