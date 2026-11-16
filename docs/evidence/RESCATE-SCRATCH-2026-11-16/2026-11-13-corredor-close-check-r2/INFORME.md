# Corredor close-check r2

Fecha: 2026-11-13. Alcance: candidato blackbox `6194cf8fb0bd1ac657935c98c5779e952079fa93`, política pre-push instalada. Sin publicar ni modificar el repo.

## Sujeto y contrato

`git rev-parse HEAD origin/master` → `6194cf8fb0bd1ac657935c98c5779e952079fa93` y `dd5b7098b3714219a3a5fc6a2c17964c0baa4d7f`. SHA-256 instalado de `~/.local/bin/simplecode`: `10dd470d321eecc1f8ffda31193d49c855bccf449fcee62a107d9af2311be4b3`. `source-r2.json` fija SHA-256 política `bee585a24f25cf94e59cf98b75b9bb5d8c9f7f034019d5339d96b4612020cbd5`; `production_policy_changed=false`. Contrato `close-check`: policy nativa, `args: []`, `read_only=true`, `git_context=true`, hook `pre-push`, base `origin/master`, código 2 CNR.

## Corredor positivo

Comando literal:

```sh
simplecode verify --repo . --hook pre-push --fresh --no-observe --impact-base dd5b7098b3714219a3a5fc6a2c17964c0baa4d7f
```

Salida: `commit=6194cf8fb0bd1ac657935c98c5779e952079fa93`; `counts={could_not_run:0, fail:0, pass:4, pending:0}`; `ready=true`; selección evaluó rango explícito con 17 rutas, 4 aplicables y 1 no aplicable. Gates seleccionados: privacidad publicación PASS (5 pruebas); pytest impacto PASS (314 módulos parseados; 0 pruebas impactadas); ceremony PASS (`dd5b7098..6194cf8f`); close-check PASS (`fichas_cerradas=0 ejecuta=0 no_ejecuta=0`). `bb-cobertura-piso` no aplicable.

El PASS close-check solo expresa disponibilidad del reporte; `no_ejecuta=0` cuenta el rango analizado, no ejecución de cierres. Las tres fichas de privacidad siguen abiertas y las cuatro aceptaciones rojas son deuda conocida. Las salidas no incluyen diagnósticos sensibles.

## Control negativo de rango

Comando literal:

```sh
simplecode verify --repo . --hook pre-push --fresh --no-observe --impact-base deadbeefdeadbeefdeadbeefdeadbeefdeadbeef
```

Salida: `counts={could_not_run:0, fail:0, pass:5, pending:0}`, `ready=true`; selección `evaluated=false`, `base=null`, razón: base no resuelve a commit. El runner detectó rango inválido, pero corrió cinco filas aplicables (incluyó `bb-cobertura-piso`, 119560 ms) e informó PASS global. El control revela que el instrumento no bloquea el reporte por rango inválido; no es un CNR. Limitación instrumental.

## Dictamen y límites

Reporte COMPLETE del corredor pre-push; el sujeto no queda aprobado para publicación ni se afirma ejecución/cierre. No se corrió suite global ni se tocó política, parche propuesto o simplecode. No se leyó lista privada ni se usaron servicios/hardware. Control negativo de guarda de privacidad con dato ficticio: CNR, no corrido en esta pasada. El parche simplecode sigue como propuesta con R1–R3 pendientes; las aceptaciones de privacidad siguen abiertas.
