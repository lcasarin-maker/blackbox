---
id: IDEA-DISTINGUIR-COMANDO-DESCONOCIDO-EN-BB-ROOT-RUN
kind: debt
title: "Distinguir con un código de retorno propio el comando desconocido en bb-root-run"
status: open
severity: P3
origin: asserted
satd_family: CODE_DESIGN_DEBT
close_check: {"cmd": "python3 -m pytest tests/test_bb_root_run.py -k comando_desconocido_codigo_propio -q", "expect": "exit_zero"}
created: 2026-11-10
---

## Contexto

El runner de comandos root con manifiesto y suma de verificación ya existe, pero todo rechazo sale con el mismo código 3. Se pidió que un comando fuera del manifiesto tenga un código distinto de los demás rechazos (suma que no coincide, argumentos inválidos), para que quien lo invoque sepa qué falló sin leer el mensaje.

## Criterio de cierre

bb-root-run sale con un código propio y documentado cuando el nombre no está en el manifiesto; los otros rechazos conservan los suyos; una prueba cubre cada código y falla si se unifican de nuevo.

## Origen

Idea de Luis en sus conversaciones con agentes, cosecha de ideas de proyecto-local del 2026-11-10. Ideas agrupadas: I-Chat-0688.
