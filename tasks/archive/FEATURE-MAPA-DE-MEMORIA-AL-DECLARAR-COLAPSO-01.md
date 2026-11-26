---
id: FEATURE-MAPA-DE-MEMORIA-AL-DECLARAR-COLAPSO-01
kind: task
domain: MEMORY
title: "Mapa de memoria por unidad en el instante en que bb-usable declara COLAPSO (el reinicio del 2026-10-16 quedo sin el)"
status: done
closed_at: 2026-11-21
closure_type: fixed
reason: "Terra aprobó el SHA 95828b0a8f56e1f7b33435e5acc363936b223ccf (dictamen 9f459a67). Mapa independiente al declarar COLAPSO, enumeración que propaga ramas ilegibles como NOT_COLLECTED, captura acotada a 1 s y cola de hasta cuatro recibos si un worker anterior sigue activo. La lectura tardía no se presenta como contemporánea; los errores de append no se reintentan. Límites: mapa de cgroups de app.slice y dmem disponible; memoria CUDA que no se cobra al cgroup permanece fuera. Un timeout deja NOT_COLLECTED con timestamp original cuando se libera el worker; cola llena se anuncia y ese recibo no se persiste. No desplegado: requiere reiniciar bb-usable.service. Linaje local privado: f9c3865897ce1cada021061e8c159ed0a83de62c; no publicar este commit ni la evidencia histórica asociada."
evidence: {"validation": "tasks/evidence/FEATURE-MAPA-DE-MEMORIA-AL-DECLARAR-COLAPSO-01/README.md", "logs": "tasks/evidence/FEATURE-MAPA-DE-MEMORIA-AL-DECLARAR-COLAPSO-01/green.out", "negative_control": "tasks/evidence/FEATURE-MAPA-DE-MEMORIA-AL-DECLARAR-COLAPSO-01/red.out"}
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-30
close_check: {"cmd": "python3 -m pytest -q tests/test_mapa_memoria_colapso.py", "expect": "exit_zero", "porque": "Pasa cuando la declaracion de COLAPSO de bin/bb-usable publica junto a su registro un mapa_memoria de las unidades de app.slice, conserva el control negativo (sin declaracion, sin mapa) y no altera la secuencia fijada en tests/fixtures/bb_usable_caracterizacion.json."}
---

## Hueco

`FEATURE-MAPA-DE-MEMORIA-FORENSE-AL-ACTUAR-01` (cerrada el 2026-10-30) pone el mapa en el escalon de `bin/bb-usable`,
en `vigilante_memavail` y en el portero. La declaracion de COLAPSO de `bin/bb-usable` no estaba en su alcance y sigue
sin mapa: `origen_al_declarar_colapso` guarda solo el origen de los 10 mayores procesos. Es la accion del 2026-10-16
(reinicio de la maquina) cuya causa quedo "inferida, no medida" en
`DEBT-COLAPSO-CONFINADO-A-APP-SLICE-REINICIA-LA-MAQUINA-ENTERA-01`.

El 2026-10-30, el close_check original daba rc=4 porque el archivo de pruebas aún no existía; ese resultado es un antecedente fechado.

## Para cerrar

1. Decidir donde va la fila: el registro de origen de `capturar_origen("colapso", ...)` se escribe solo si el origen
   se pudo leer, asi que el mapa no puede depender de el; leer quien consume `$BLACKBOX_DATA/escalon/` y `origen/`
   antes de anadir un tipo de fila.
2. Reusar `mapa_al_matar` de `bin/bb-usable` (o generalizarlo) dentro del try de `origen_al_declarar_colapso`.
3. `tests/test_mapa_memoria_colapso.py`: la declaracion deja el mapa; sin declaracion no; un mapa roto no cambia la
   caricia ni el log; la caracterizacion de bb-usable no se regraba.

## Cierre 2026-11-21

Implementacion y prueba focal en `tasks/evidence/FEATURE-MAPA-DE-MEMORIA-AL-DECLARAR-COLAPSO-01/`. La captura se
publica en `escalon/` separada de `origen/`, una vez por episodio realmente declarado; una racha confinada puede
declararse después y dos bajas confirmadas rearman el siguiente episodio. Captura y append usan worker único y plazo
de un segundo. Reauditoría independiente Terra `9f459a67` aprobó el SHA completo consignado arriba.

## Limites declarados

Los de la ficha madre: la memoria CUDA no cobrada al cgroup queda fuera salvo `dmem`, y nada corre hasta que Luis
reinicie `bb-usable.service`.
