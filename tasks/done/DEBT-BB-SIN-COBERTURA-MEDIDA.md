---
id: DEBT-BB-SIN-COBERTURA-MEDIDA
kind: debt
title: bin/bb tenia 18 tests y cero cobertura MEDIDA -- coverage.py no instrumenta bash
status: done
severity: P3
origin: asserted
satd_family: UNMEASURED_COVERAGE
created: 2026-09-24
closed_at: 2026-09-24
close_check: {"cmd": "grep -qE '^bin/bb +[0-9]+' tasks/evidence/DEBT-BB-SIN-COBERTURA-MEDIDA/cobertura.txt", "expect": "exit_zero", "porque": "la ficha pedia un numero medido sobre bin/bb; el close_check exige que ese numero exista en la evidencia, no una promesa."}
evidence: {"pass": "tasks/evidence/DEBT-BB-SIN-COBERTURA-MEDIDA/cobertura.txt", "fail": "tasks/evidence/DEBT-BB-SIN-COBERTURA-MEDIDA/trinquete.txt", "e2e": "tasks/evidence/DEBT-BB-SIN-COBERTURA-MEDIDA/control-negativo.txt"}
reason: "Se escribio tools/cobertura_bash.sh (BASH_ENV + BASH_XTRACEFD + PS4, sin dependencias nuevas) y bin/bb quedo medido: 146 de 829 lineas, 17.6%. Se le puso trinquete (tools/piso_cobertura.sh + hook pre-push bb-cobertura-piso + tests/cobertura_bb.piso) para que no baje en silencio. Los dos controles negativos se CORRIERON, no se argumentaron."
---

## Root Cause

`coverage.py` instrumenta Python. `bin/bb` es bash y es el 100% del codigo
ejecutable de este repo, asi que el gate `coverage-target` pasaba en cada push
**sin haber mirado una sola linea del fichero que mas hace**. Un instrumento
que no puede capturar nada del sujeto no es evidencia de que el sujeto este
limpio: es un defecto del instrumento.

`tests/test_bb_bash.py` prueba que los caminos probados estan probados. No
decia nada de los que no, y nadie podia afirmar un porcentaje -- ni yo, que el
2026-09-24 lo declare como hueco en prosa y lo deje ahi.

## Regression Test

```
tools/piso_cobertura.sh
```

Corre como hook `pre-push` (`bb-cobertura-piso`, en `.simplecode/local_hooks.yaml`,
que es la fuente que `satellite_sync` preserva). Lee `tests/cobertura_bb.piso`
y falla si el porcentaje cae por debajo. El piso se sube a mano, con la corrida
que lo justifica en el commit; nunca se baja en silencio.

## Verification Evidence

- `pass` -- `tasks/evidence/.../cobertura.txt`: la medicion, `bin/bb 829 146 17.6%`,
  con la lista literal de lineas sin cubrir.
- `e2e` -- `control-negativo.txt`: **el medidor puede salir negativo**. Suite
  vacia -> `0.0%`. Tres de los dieciocho tests (`-k cap`) -> `4.3%`. Los
  dieciocho -> `17.6%`.
- `fail` -- `trinquete.txt`: **el gate puede bloquear**. Con el piso a `99.0`,
  `rc=1` y el motivo impreso; con el piso real, `rc=0`.

Un fallo del instrumento se encontro y se corrigio en el camino: contaba las
17 cabeceras `nombre() {` como sin cubrir, y bash no traza una definicion de
funcion, solo su cuerpo. Sin ese arreglo el denominador era 846 en vez de 829 y
el informe inventariaba lineas inalcanzables como deuda.

## Limite declarado

**17.6% es bajo, y el numero es el hallazgo, no la solucion.** Mide lineas
EJECUTADAS, no ramas ni condiciones: un `if` cuyo `else` nunca corre cuenta como
cubierto. Lo que este cierre entrega es que el numero existe, que se puede
comparar y que no puede caer callado. Subirlo es trabajo ordinario de tests, y
el piso es ahora quien lo exige.
