---
id: FEATURE-MAPA-DE-MEMORIA-AL-DECLARAR-COLAPSO-01
kind: task
domain: MEMORY
title: "Mapa de memoria por unidad en el instante en que bb-usable declara COLAPSO (el reinicio del 2026-10-16 quedo sin el)"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-30
close_check: {"cmd": "python3 -m pytest -q tests/test_mapa_memoria_colapso.py", "expect": "exit_zero", "porque": "Especificacion pendiente: el archivo de pruebas no existe hoy (rc=4 el 2026-10-30). Pasa solo cuando la declaracion de COLAPSO de bin/bb-usable deje un mapa_memoria (tools/mapa_memoria.captura) de las unidades de app.slice junto a su registro, con control negativo (sin declaracion, sin mapa) y sin cambiar la secuencia fijada en tests/fixtures/bb_usable_caracterizacion.json."}
---

## Hueco

`FEATURE-MAPA-DE-MEMORIA-FORENSE-AL-ACTUAR-01` (cerrada el 2026-10-30) pone el mapa en el escalon de `bin/bb-usable`,
en `vigilante_memavail` y en el portero. La declaracion de COLAPSO de `bin/bb-usable` no estaba en su alcance y sigue
sin mapa: `origen_al_declarar_colapso` guarda solo el origen de los 10 mayores procesos. Es la accion del 2026-10-16
(reinicio de la maquina) cuya causa quedo "inferida, no medida" en
`DEBT-COLAPSO-CONFINADO-A-APP-SLICE-REINICIA-LA-MAQUINA-ENTERA-01`.

## Para cerrar

1. Decidir donde va la fila: el registro de origen de `capturar_origen("colapso", ...)` se escribe solo si el origen
   se pudo leer, asi que el mapa no puede depender de el; leer quien consume `$BLACKBOX_DATA/escalon/` y `origen/`
   antes de anadir un tipo de fila.
2. Reusar `mapa_al_matar` de `bin/bb-usable` (o generalizarlo) dentro del try de `origen_al_declarar_colapso`.
3. `tests/test_mapa_memoria_colapso.py`: la declaracion deja el mapa; sin declaracion no; un mapa roto no cambia la
   caricia ni el log; la caracterizacion de bb-usable no se regraba.

## Limites declarados

Los de la ficha madre: la memoria CUDA no cobrada al cgroup queda fuera salvo `dmem`, y nada corre hasta que Luis
reinicie `bb-usable.service`.
