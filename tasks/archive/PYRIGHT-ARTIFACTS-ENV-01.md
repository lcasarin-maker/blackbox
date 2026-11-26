---
id: PYRIGHT-ARTIFACTS-ENV-01
kind: task
domain: VERDICT
title: "La fila pyright recibe su directorio de artefactos"
status: done
severity: P2
origin: detected
satd_family: BLIND_INSTRUMENT
created: 2026-11-23
close_check: {"cmd": "python3 -c \"import json,sys;r=[x for x in json.load(open('temis.json'))['checks'] if x['id']=='pyright'][0];sys.exit(0 if '--artifacts-env' in r['policy']['args'] and 'TEMIS_NATIVE_ARTIFACTS_DIR' in r['inherit_env'] else 1)\"", "expect": "exit_zero", "porque": "La fila pyright debe declarar --artifacts-env y heredar la variable; sin ellos Temis da could_not_run."}
closed_at: 2026-11-23
closure_type: fixed
reason: "La fila pyright declara el selector y hereda la variable; verificado con veredicto real y con control negativo."
---

## Causa raíz

La fila `pyright` de `temis.json` (política `types`) exige un directorio de artefactos propio. Sin selector `--artifacts-env` ni la variable en `inherit_env`, la fila daba `could_not_run` y nunca emitía veredicto.

## Corrección

Se añadió `--artifacts-env TEMIS_NATIVE_ARTIFACTS_DIR` a los argumentos de la política y la variable a `inherit_env`. Es el mismo mecanismo que usa la fila vitest de otro repositorio de la flota. Solo cambia `temis.json`.

## Evidencia (`temis verify --hook ci --fresh`, directorio 0700 propio)

- Con la variable exportada: fila pyright `fail` (veredicto real; 71 errores de tipos, 2 advertencias, 351 archivos analizados). Las demás filas del hook ci pasan.
- Sin la variable (control negativo): fila pyright `could_not_run`, motivo `required environment variable absent`.
- Control negativo del close_check: contra el `temis.json` previo al cambio sale 1; contra el nuevo sale 0.

Los 71 errores de tipos son deuda previa que el contrato ya no oculta; quedan fuera de esta ficha.
