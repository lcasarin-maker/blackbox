---
id: DEBT-ATOM-DEGRADACION-ACELERADA-DE-BOOTS-01
kind: task
domain: HARDWARE
title: "La ATOM se sigue cayendo: ningun boot bate el record de 146.566 h (de una referencia externa)"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-17
close_check: {"cmd": "grep -qx 'rc=0' tasks/evidence/DEBT-ATOM-DEGRADACION-ACELERADA-DE-BOOTS-01/criterio_de_cierre.txt", "expect": "exit_zero", "porque": "Especificacion pendiente: el archivo no existe hoy y el criterio falla. El cierre lo mide una evidencia LOCAL, sin ejecutar el otro repo (bb no corre codigo ajeno ni nombra su checkout, boleta #18 A del 2026-11-01): el criterio de DGX-464 del consumidor de conocimiento, conservado verbatim alli, se corre en su repo y su salida se guarda aqui con la linea exacta `rc=<codigo>` mas el stdout y la fecha de la corrida. Solo `rc=0` cierra: sin espiral activa Y con el boot actual por encima del boot mas largo que termino en crash (146.566 h). El 2026-10-17 salia 2 (COULD_NOT_RUN: un evento sin crash confirmado, boot 92a1de3d) y antes 1 (NO); ni 1 ni 2 cierran. Sustituye al script que ejecutaba el criterio desde el checkout del otro repo, retirado el 2026-11-01."}
---

## Origen

Trasladada el 2026-10-17 por pedido de Luis desde una referencia externa (la causa fisica de las caidas de la ATOM es de blackbox: la propia una referencia externa lo declara tras una referencia externa). La historia completa, incluido el cierre en falso del 2026-09-16 y la reapertura del 2026-09-25, queda en la ficha del consumidor de conocimiento (una referencia externa con `closure_type: relocated`). **No se cierra aqui por la suite del instrumento: solo por el comando de abajo.**

## Medido al trasladar (2026-10-17)

```
$ bash una referencia externa   # rc=2
[atom_degradacion_resuelta] COULD_NOT_RUN  hay eventos sin señal demostrable de crash o líneas corruptas; no se puede declarar resuelta la espiral
```

Control negativo del propio comando: el `NO` (rc=1) esta documentado en la ficha del consumidor de conocimiento el 2026-09-28; el estado verde exige un boot > 146.566 h.

Hallazgo que viaja con la ficha (corregido el 2026-10-17 tras verificarlo en el codigo del consumidor de conocimiento): el consumidor de conocimiento exige dano de journal o una linea de panic para confirmar un crash (`detect_atom_crash.crash_confirmado()` solo acepta `diagnostico` = `journal_danado` o `panic`); la fila `92a1de3d` tiene `diagnostico: sin_senal` (journal intacto, sin panic) mientras el dictamen de blackbox la clasifica CORTE_ABRUPTO, asi que el criterio devuelve rc=2 hasta que Luis decida si el veredicto CORTE_ABRUPTO de blackbox basta como prueba. No es un error de ninguno de los dos instrumentos: el consumidor de conocimiento decide no adivinar.

## Relacionadas

`DEBT-ATOM-CORTES-OCT-2026-CAUSA-NO-DETERMINADA-01` (la causa), `DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01`, `DEBT-COLAPSO-05-OCT-ENJAMBRE-DE-PROCESOS-SIN-TECHO-01`.

## Voto de Luis 2026-10-17: el criterio del consumidor de conocimiento se mantiene estricto
El veredicto CORTE_ABRUPTO de blackbox NO basta como prueba de crash para esta ficha: el evento `92a1de3d` (diagnostico `sin_senal`, sin journal danado ni linea de panic) sigue fuera de la serie y el criterio devuelve rc=2 hasta que una caida traiga evidencia real. Descartado: aceptar CORTE_ABRUPTO como prueba (baja la vara de la serie de record; se deduce de que el journal calla sin cierre, no de una señal de la caida). Costo aceptado: la ficha no se puede cerrar con lo que hay hoy.
