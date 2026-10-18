# Simplecode cutover — 2026-10-17 (completado en este repo)

El kit anterior se retiro entero (`.simplecode/run.py`, `runtime.zip`, `kit.lock`, ledger H1, baselines y hooks locales) y no
hay llamadas activas a su lanzador. La decision, con lo retirado y lo descartado, esta en `DECISIONS.md` (2026-10-17).

| Antes (kit) | Ahora |
|---|---|
| corruption-guard, truncation-guard | Simplecode 11.1.0, `corruption_guard` staged y árbol completo |
| pii-scan | Simplecode 11.1.0, `pii_scan --files` staged y `--all-tracked` pre-push; roles exactos en `tasks/pii_allow.txt` |
| ruff, gitleaks (staged) | igual, nativos |
| pyright por atestacion de SHA | `pyright` directo en pre-push |
| coverage-100 por atestacion | `pytest` del producto en pre-push; `bb-cobertura-piso` para `bin/bb` |
| bash-sintaxis, inventario-spec | sin cambio |
| version-bump, ledger-schema, zero-debt, ship-freeze, backlog-verifier, hook-receipts, sunset-audit, H1 y demas procesos | retirados (ver DECISIONS.md) |

`COULD_NOT_RUN` declarado: la CI de GitHub no arranca en la cuenta por un error de facturacion; no cuenta como verde.

La migración del 2026-10-18 retiró las dos copias nativas y sus tests; las pruebas de los motores viven en Simplecode. El pin de commit está en `.pre-commit-config.yaml`.
