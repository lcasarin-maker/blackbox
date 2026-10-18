# Simplecode cutover — 2026-10-17 (completado en este repo)

El kit anterior se retiro entero (`.simplecode/run.py`, `runtime.zip`, `kit.lock`, ledger H1, baselines y hooks locales) y no
hay llamadas activas a su lanzador. La decision, con lo retirado y lo descartado, esta en `DECISIONS.md` (2026-10-17).

| Antes (kit) | Ahora |
|---|---|
| corruption-guard, truncation-guard | `tools/guardia_integridad.py` (+ `tests/test_guardia_integridad.py`) |
| pii-scan | `tools/guardia_pii.py` (+ `tests/test_guardia_pii.py`) |
| ruff, gitleaks (staged) | igual, nativos |
| pyright por atestacion de SHA | `pyright` directo en pre-push |
| coverage-100 por atestacion | `pytest` del producto en pre-push; `bb-cobertura-piso` para `bin/bb` |
| bash-sintaxis, inventario-spec | sin cambio |
| version-bump, ledger-schema, zero-debt, ship-freeze, backlog-verifier, hook-receipts, sunset-audit, H1 y demas procesos | retirados (ver DECISIONS.md) |

`COULD_NOT_RUN` declarado: la CI de GitHub no arranca en la cuenta por un error de facturacion; no cuenta como verde.
