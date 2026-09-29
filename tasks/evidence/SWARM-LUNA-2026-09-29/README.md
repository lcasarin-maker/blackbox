# Ola Luna interrumpida — 2026-09-29

Base: `72d190d`. Cuatro agentes `gpt-6-luna`, razonamiento high, en worktrees aislados. Los cuatro terminaron con error de límite de uso; no entregaron veredictos. No se sustituyeron por otro modelo.

## Resultado

- Fichas antes: 8. Fichas después: 8.
- Cerradas por Luna: 0. Cerradas por otros modelos: 0.
- Veredictos CERRADA rechazados por el orquestador: 0 (recibidos: 0).
- `triage.py merge`: returned 0 of 8; missing 8. Ola INCOMPLETA.
- could_not_run del trabajo delegado: 8 fichas por límite de uso.
- Cambios productivos: 0; despliegues: 0; commits de agentes: 0.
- El archivo `tests/test_audit_watchdog.py` del worktree watchdog está vacío y se conserva allí; carece de prueba recuperable.

Se detiene por la regla de /0: una ola que cierra cero termina la ejecución. Las ocho fichas conservan status open y sus close_check originales. No se generaron veredictos ficticios para completar el merge.

## Lotes y punto de reanudación

| Grupo | Fichas | Worktree |
|---|---:|---|
| guardia | 2 | /home/lcasarin/.codex/worktrees/bb-guardia-debt/blackbox |
| watchdog | 1 | /home/lcasarin/.codex/worktrees/bb-watchdog-debt/blackbox |
| termica | 2 | /home/lcasarin/.codex/worktrees/bb-thermal-debt/blackbox |
| scan | 3 | /home/lcasarin/.codex/worktrees/bb-scan-debt/blackbox |

Los lotes `batch_*.json` y `items.json` se generaron desde las fichas. Cada id pendiente y su grupo constan en esos archivos. Reutilizar estos worktrees tras comprobar su estado al reanudar; cada uno seguía en `72d190d` al inspeccionarlo.

## Suite inicial y límites

Comando: `python3 -m pytest tests -q`.
Salida literal final: `30 failed, 475 passed, 4 skipped in 169.83s (0:02:49)`.
Salida completa: `baseline-tests.txt`.

could_not_run identificado: 3 pruebas por restricciones de entorno (una de systemd bus y dos sockets Unix). Las otras 27 fallas requieren diagnóstico; varias muestran JSONDecodeError al leer muestras. No se atribuyen automáticamente al sandbox. Las 4 omitidas se reportan aparte. La suite no acredita salud del producto.

Evidencia de inventario: `debt-before.txt`, `debt-after.txt`. El escáner cuenta 8 fichas; esa cifra no representa un diagnóstico de las 27 fallas restantes de la suite. Evidencia de completitud fallida: `triage-merge.txt`.
