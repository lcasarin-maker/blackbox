---
id: IDEA-DISTINGUIR-COMANDO-DESCONOCIDO-EN-BB-ROOT-RUN
kind: debt
title: "Distinguir con un código de retorno propio el comando desconocido en bb-root-run"
status: done
severity: P3
origin: asserted
satd_family: CODE_DESIGN_DEBT
close_check: {"cmd": "python3 -m pytest tests/test_bb_root_run.py -k comando_desconocido_codigo_propio -q", "expect": "exit_zero"}
created: 2026-11-10
---

## Contexto

En la base 7c2d7158 el runner usaba rc 4 tanto para nombre válido ausente como para cualquier script aprobado que devolviera 4; `apt-guardia-instalar` y `earlyoom-proteger` tienen ese retorno legítimo. Luis autorizó un código reservado para desconocido, manteniendo todos los rc aprobados salvo el reservado; esa colisión se convierte a fallo genérico y se conserva el original en auditoría.

## Criterio de cierre

Un nombre válido ausente del manifiesto devuelve 193. Otros rechazos conservan rc 3. Los scripts aprobados propagan sus rc, salvo rc 193, que devuelve el fallo genérico rc 1; solo en esa colisión, `auditoria.jsonl` y stderr muestran `rc` devuelto separado de `rc_script` original. En las demás ejecuciones se conserva la forma anterior de stderr y fila `fin`. rc 193 está fuera de los estados de salida por señal del host (129..192) y de los otros rc operativos 3 y 124.

## Implementación y auditoría local

Se implementó solo en `tools/bb_root_run.py`; no cambiaron scripts aprobados, manifiesto ni sudoers. Banco offline prueba script rc 193 -> rc 1 con `rc_script=193`, script rc 4 -> rc 4 sin cambios en stderr/fila `fin`, nombre desconocido -> rc 193 y rechazos sintácticos/hash -> rc 3.

El `close_check` canónico conserva su comando original (`comando_desconocido_codigo_propio`) y ahora falla si se omite el remapeo. Resultado: 69 pruebas focales pasan; el mutante de remapeo produce el fallo esperado. Revisión local del diff confirmó que no se alteraron validaciones privilegiadas ni scripts/manifest/sudoers. Cierre local en este worktree; no implica despliegue.

## Origen

Idea de Luis en sus conversaciones con agentes, cosecha de ideas de proyecto-local del 2026-11-10. Ideas agrupadas: I-Chat-0688.
