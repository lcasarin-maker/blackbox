---
id: DEBT-BB-SIN-COBERTURA-MEDIDA
kind: debt
title: bin/bb tiene 18 tests y cero cobertura MEDIDA -- coverage no instrumenta bash
status: open
severity: P3
origin: asserted
satd_family: UNMEASURED_COVERAGE
created: 2026-09-24
close_check: {"cmd": "grep -qE '^bin/bb +[0-9]+' tasks/evidence/DEBT-BB-SIN-COBERTURA-MEDIDA/cobertura.txt", "expect": "exit_zero"}
---

## Que pasa

`tests/test_bb_bash.py` ejerce el ejecutable real con 18 tests y 7 mutantes en
rojo. Eso prueba que los caminos probados **estan** probados. No dice nada de
los que no.

`coverage.py` instrumenta Python. `bin/bb` es bash: no aparece en ningun informe
de cobertura del repo, asi que el gate `coverage-target` pasa sin haber mirado
una sola linea del fichero que mas hace en este proyecto. Es el caso exacto que
la politica de reportes nombra: un instrumento con cero capturas no es evidencia
de que el sujeto este limpio, es un defecto del instrumento.

La parte honesta de lo que se dijo el 2026-09-24 fue "NO hay cobertura MEDIDA".
La parte deshonesta fue dejarlo ahi.

## Como se cierra

`bash` sabe trazar: `BASH_XTRACEFD` + `set -x` con `PS4='+${BASH_SOURCE}:${LINENO}:'`
da las lineas ejecutadas sin dependencias nuevas (rung 4 de la escalera: la
herramienta ya lo hace). Con eso:

1. Envolver la suite para que cada invocacion de `bin/bb` trace a un fichero.
2. Reducir las lineas vistas contra las lineas ejecutables del fichero.
3. Volcar el informe a `tasks/evidence/DEBT-BB-SIN-COBERTURA-MEDIDA/cobertura.txt`,
   que es lo que el `close_check` exige.
4. Control negativo obligatorio: borrar un test y comprobar que el porcentaje
   BAJA. Un medidor de cobertura que no puede bajar no mide.

Alternativa si lo anterior resulta fragil: `kcov`, que hace esto mismo ya
hecho -- pero es dependencia nueva, y la escalera dice que se intenta lo de
arriba primero.

## Limite declarado

Un porcentaje de cobertura sobre bash seguira sin decir que las ramas estan
bien probadas, solo que se ejecutaron. Los 7 mutantes en rojo dicen mas sobre
calidad que cualquier porcentaje; esta ficha cubre el otro eje, el de lo que
nadie toca.
