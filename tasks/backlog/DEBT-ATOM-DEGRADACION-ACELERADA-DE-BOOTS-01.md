---
id: DEBT-ATOM-DEGRADACION-ACELERADA-DE-BOOTS-01
kind: task
domain: HARDWARE
title: "La ATOM se sigue cayendo: ningun boot bate el record de 146.566 h (de Atlas DGX-464)"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-17
close_check: {"cmd": "bash tools/check_atom_degradacion_atlas.sh", "expect": "exit_zero", "porque": "Criterio de DGX-464 conservado verbatim: sale 0 solo sin espiral activa Y con el boot actual por encima del boot mas largo que termino en crash (146.566 h). Hoy sale 2 (COULD_NOT_RUN: un evento sin crash confirmado, boot 92a1de3d) y antes salia 1 (NO). Ni 1 ni 2 cierran."}
---

## Origen

Trasladada el 2026-10-17 por pedido de Luis desde Atlas `tasks/backlog/DGX-464` (la causa fisica de las caidas de la ATOM es de blackbox: la propia DGX-464 lo declara tras DGX-585). La historia completa, incluido el cierre en falso del 2026-09-16 y la reapertura del 2026-09-25, queda en la ficha de Atlas (`tasks/done/DGX-464.md` con `closure_type: relocated`). **No se cierra aqui por la suite del instrumento: solo por el comando de abajo.**

## Medido al trasladar (2026-10-17)

```
$ bash tools/check_atom_degradacion_atlas.sh   # rc=2
[atom_degradacion_resuelta] COULD_NOT_RUN  hay eventos sin señal demostrable de crash o líneas corruptas; no se puede declarar resuelta la espiral
```

Control negativo del propio comando: el `NO` (rc=1) esta documentado en la ficha de Atlas el 2026-09-28; el estado verde exige un boot > 146.566 h.

Hallazgo que viaja con la ficha (corregido el 2026-10-17 tras verificarlo en el codigo de Atlas): Atlas exige dano de journal o una linea de panic para confirmar un crash (`detect_atom_crash.crash_confirmado()` solo acepta `diagnostico` = `journal_danado` o `panic`); la fila `92a1de3d` tiene `diagnostico: sin_senal` (journal intacto, sin panic) mientras el dictamen de blackbox la clasifica CORTE_ABRUPTO, asi que el criterio devuelve rc=2 hasta que Luis decida si el veredicto CORTE_ABRUPTO de blackbox basta como prueba. No es un error de ninguno de los dos instrumentos: Atlas decide no adivinar.

## Relacionadas

`DEBT-ATOM-CORTES-OCT-2026-CAUSA-NO-DETERMINADA-01` (la causa), `DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01`, `DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01`.
