---
id: DEBT-GUARDA-PUBLICA-28-RUTAS-SOBRE-LINEA-BASE-01
kind: debt
domain: SECURITY
title: "Rojo previo: 28 archivos publicados exceden la linea base de datos privados"
status: open
severity: P1
origin: measured
created: 2026-11-13
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider tests/test_sin_datos_privados.py", "expect": "exit_zero", "porque": "La guarda debe pasar sin ampliar la linea base ni debilitar su patron o sus controles negativos; remediacion separada con revisor."}
---

## Rojo previo medido

Comando exacto: `python3 -m pytest -q -p no:cacheprovider tests/test_sin_datos_privados.py`.
Salida resumida literal: `1 failed, 4 passed`; codigo `1`.
Falla `test_el_repo_no_gana_datos_privados`: 28 archivos exceden la linea base
`tests/fixtures/datos_privados_baseline.json`. Se documentan rutas y conteos;
el contenido detectado se reserva para una revision separada.

La misma falla aparece en el commit previo a /clean,
`fe1e9cbf1e77d60890a26d3a5c6de55e6a6e308c`: `1 failed, 4 passed in 3.31s`,
codigo `1`, en un clon local independiente de ese commit.
Los cuatro tests restantes comprueban el patron firmado, fixtures limpios y
fixtures que deben disparar la guarda; el comparador devuelve vacio con cuentas
iguales y detecta un archivo nuevo o una cuenta mayor. Ese es el control negativo.

## Rutas y conteos

Las 28 rutas y sus cuentas fueron contrastadas con los blobs de `origin/master`
en `7ae6f669db5c73d51afed87e68dfae6c2f66a8d7`: todas ya estaban publicadas,
con la misma cuenta. Columna "base": ausencia en el JSON equivale a cero.
Una ruta se expresa como patron univoco para que el inventario de rutas no
reintroduzca el nombre que busca la propia guarda; `git ls-files -- '<patron>'`
recupera su nombre exacto. El inventario completo local conserva el nombre literal.

| Ruta | Base | Actual y remoto | Desde (exceso continuo) |
|---|---:|---:|---|
| `DECISIONS.md` | 0 | 2 | `df4925aafb90` |
| `SPEC.md` | 1 | 5 | `abc42f4e875c` (limite: 80 revisiones) |
| `adopted/boton-rojo-keep.txt` | 0 | 3 | `abc42f4e875c` |
| `adopted/gateway/admission_check_wrapper.sh` | 0 | 2 | `7a84acf11c65` |
| `adopted/solo-registro.txt` | 0 | 1 | `e22921e45c21` |
| `adopted/systemd-user/bb-muestreo-corte.service` | 0 | 1 | `e22921e45c21` |
| `bin/bb` | 0 | 6 | `28bfec9ddc79` |
| `logs/memory_gate.jsonl` | 0 | 18 | `c329248f18f1` |
| `tasks/backlog/DEBT-CAIDAS-DURAS-7-0-MODULO-PARCHADO-01.md` | 0 | 7 | `e9eee190d357` |
| `tasks/backlog/DEBT-MEMORIA-GPU-SIN-LIMITE-APLICADO-COLAPSOS-5-Y-6-NOV-01.md` | 0 | 5 | `e9eee190d357` |
| `tasks/backlog/DEBT-MOTOR-LLM-CAIDAS-CUDA-SIN-CAUSA-01.md` | 0 | 8 | `7a84acf11c65` |
| `tasks/backlog/FEATURE-GATEWAY-VLLM-Y-RIESGOS-DE-MAQUINA-DESDE-*.md` | 0 | 20 | `fe1e9cbf1e77` |
| `tasks/backlog/FEATURE-PRUEBA-KERNEL-7-0-1025-UNA-VEZ-01.md` | 0 | 1 | `16cd76512f9a` |
| `tasks/backlog/IDEA-DECLARAR-DUENIO-UNICO-DEL-MONITOREO-Y-AREAS.md` | 0 | 1 | `002e4f2d7eff` |
| `tasks/backlog/IDEA-DISTINGUIR-COMANDO-DESCONOCIDO-EN-BB-ROOT-RUN.md` | 0 | 1 | `002e4f2d7eff` |
| `tasks/backlog/IDEA-REENCOLAR-TRABAJO-PERDIDO-TRAS-CAIDA-DE-LA-MAQUINA.md` | 0 | 1 | `8a2d2254094d` |
| `tasks/backlog/IDEA-RESPETAR-MARCA-DE-DIAGNOSTICO-EN-PRUEBAS-DEL-PRODUCTO.md` | 0 | 1 | `002e4f2d7eff` |
| `tasks/backlog/IDEA-TABULAR-BLOQUEADORES-Y-BOLETA-DE-DESBLOQUEO.md` | 0 | 1 | `002e4f2d7eff` |
| `tasks/done/FEATURE-VENTANA-GPU-NOCTURNA-SECUENCIA-01.md` | 0 | 5 | `eb4932585361` |
| `tasks/evidence/FEATURE-VENTANA-GPU-NOCTURNA-SECUENCIA-01/pass.txt` | 0 | 1 | `eb4932585361` |
| `tests/test_bb_wol.py` | 0 | 6 | `4a03ddd8ce1c` |
| `tests/test_boton_rojo.py` | 0 | 24 | `abc42f4e875c` |
| `tests/test_inventario.py` | 0 | 1 | `7a84acf11c65` |
| `tools/boton_rojo.py` | 0 | 2 | `abc42f4e875c` |
| `tools/inventario.py` | 0 | 3 | `7a84acf11c65` |
| `tools/motor_solicitudes.py` | 0 | 2 | `28bfec9ddc79` |
| `tools/testigo/bb_alarma.py` | 0 | 1 | `2d1f92fdeac5` |
| `tools/testigo/bb_wol.py` | 0 | 4 | `4a03ddd8ce1c` |

Se recorrio `git log --format=%H --max-count=80 origin/master -- <ruta>`
desde la punta y se conto el patron sobre cada blob de `git show <sha>:<ruta>`,
hasta encontrar una cuenta dentro de la base o la creacion del archivo.
"Desde" designa el comienzo del tramo continuo medido que excede la base actual,
no un juicio sobre el criterio de privacidad vigente cuando se escribio el commit.
Para SPEC.md se agoto el limite: el origen exacto queda pendiente de medir.

## Accion pendiente

Remediacion separada con revisor: clasificar cada hallazgo, sanear sin copiar el
contenido sensible a evidencias publicas y volver a correr la guarda y sus controles.
No editar la linea base ni la guarda. La limpieza Git conserva este rojo previo;
esta ficha registra el problema y no lo declara resuelto.
