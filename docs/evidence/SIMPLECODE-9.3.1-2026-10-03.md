# Actualización canónica de Simplecode 9.3.1

Se aplicó `PYTHONPATH=/home/lcasarin/projects/simplecode/src /home/lcasarin/projects/simplecode/.venv/bin/python -m simplecode.cli sync-satellites --projects-dir /home/lcasarin/projects --target /home/lcasarin/projects/blackbox --apply`.
Resultado literal: `UPDATED (canonical config), RUNTIME_INSTALLED (8.9.6 -> 9.3.1), KIT_LOCK_INSTALLED`. El plan posterior devuelve cero desfases; `MAKEFILE_ABSENT` es informativo.

La configuración añade gitleaks sobre todo el historial en pre-push y cinco prioridades. Pre-commit 4.6.2 emite cinco `Unexpected key(s) ... priority`; estas claves se ignoran. Se conserva la configuración canónica y se registra el defecto de integración, pendiente del productor.

Los 16 gates de pre-commit pasan. La afirmación H1 SPEC-L319, única afectada, se reaudita: controles negativos y regresiones dan `19 passed in 26.61s`; el gate H1 devuelve `not-clean reasons: 0`. Evidencia y lock en `tasks/evidence/SIMPLECODE-9.3.1-2026-10-03/`.

El barrido `AGENT_THREAT_TREES` del productor sigue limitado a src, scripts, daemon, central e installer. Omite tools; el pendiente upstream permanece abierto. Las 98 fichas experimentales conservan sus contratos y estado.

La primera ejecución completa detectó `1 failed, 1095 passed in 106.13s`: la regresión de backlog_md_freeze llamaba al órgano retirado por c1e09060. Se adaptó el control al retiro efectivo y se eliminó su excepción obsoleta. La historia y close_check de la ficha permanecen registrados.

La repetición estable de `python3 .simplecode/run.py simplecode.verification.coverage_target -q` termina con `1096 passed in 103.13s` y `[coverage-ratchet] OK: Current coverage 100.00% meets watermark 100.00%`. La fase serial tiene 1096 deselected, porque no hay pruebas con mutates_real_source.

Pre-push conserva cinco resultados fallidos en su primera ejecución: cobertura (corregida y repetida arriba), bb-cobertura-piso (el comando pasó con 40.1%, piso 32.8%, pero pre-commit detectó cambios concurrentes del árbol), version-bump (20 sunsets pendientes antes de 2.4), ship-freeze (98 fichas, could_not_run 0) y telemetry-disposition (could_not_dispose 2, eventos abedf207b89fd73e y 8e952805d8c2ef3a). Pyright, secretos históricos, schema y backlog-verifier pasan. Este informe declara los fallos; la publicación permanece bloqueada.

Los tres worktrees de ejecutores, ya integrados, se archivaron con verificación SHA256 y modos de cada archivo, incluidos los ignorados, y bundle Git verificado. Se retiraron sin force; permanece un único worktree. Archivo recuperable: `.git/bb-instrument-archives/2026-10-03/manifest.json`. Las tres integraciones de historial tuvieron 13 hooks sin entrada cada una; esos skips no representan ejecución de los controles.
