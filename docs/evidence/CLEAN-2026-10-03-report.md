# Limpieza y correcciones — 2026-10-03

Los 80 avisos del ledger y los cuatro errores de Pyright quedaron corregidos. La versión resultante es 2.3.0. Las fuentes, veredictos y salidas literales están en `tasks/evidence/CLEAN-2026-10-03/`.

## Validación medida

- `python3 .simplecode/run.py simplecode.verification.ledger_schema --root . --check`: `checked=283 passed=283 failed=0 unverified=0 avisos=0 could_not_run=0`; 186 fichas done con E2E legible y atribuido.
- `python3 .simplecode/run.py simplecode.verification.coverage_target -q`: 903 pruebas pasaron. El alcance configurado es `tools`: 3498/3498 statements, 100%, 16 exclusiones existentes, cobertura de ramas desactivada. Los recolectores de investigación quedan fuera de ese alcance; su medición separada dio 81% (135 statements, 25 missing).
- Pyright: 0 errores. Ruff: All checks passed. Verificador de cierres: fraude=0, could_not_run=0, incumplimientos=0, unverified=0.
- Triage generado y fusionado: 80/80 avisos, 9/9 ramas con cambios y 20/20 renovaciones de exenciones, cada ID exactamente una vez.
- Se reejecutaron los controles de las 20 exenciones antes de renovarlas para 2.3. No se añadieron supresiones ni baselines.

## Cambios y conservación

Los recolectores de foro ahora son fuentes mantenidas y portables, con controles offline de JSON, reintentos, paginación e importación. El control de servicios distingue entre evidencia ilegible y servicio ausente; la comprobación viva de bb-usable pasó tras el reinicio ya realizado.

Se consolidó la historia útil de las ramas anteriores y se retiraron 32 worktrees secundarios. Los bundles de Git y archivos privados se verificaron antes de retirar los árboles: discrepancias=0. Queda el checkout principal y master como única rama local.

Se preservaron 6732 archivos originales de investigación, 220125371 bytes, con SHA256 y modos verificados, discrepancias=0. Los gates detectaron 392 hallazgos de secretos en 375 rutas y 126 hallazgos de integridad en 61 rutas: 436 rutas únicas en conjunto. Los originales permanecen en el archivo privado ignorado; el manifiesto y los resultados curados quedan publicados. La investigación histórica mantiene su could_not_run=1 por un post parcial.

El commit histórico del foro fue verificado con el productor nativo: 12 controles pasaron, 4 DID NOT RUN por alcance vacío y could_not_run=0. Las dos entradas antiguas del baseline de recibos siguen iguales y vencen el 2026-10-08.

## Alcance pendiente

Quedan 97 fichas abiertas y 186 done. El detector zero-debt reportó 0 condenas, 0 could_not_run y 0 violaciones; ese resultado describe sus detectores, mientras las fichas abiertas conservan sus requisitos.

El barrido de amenazas del kit lee 0 archivos porque su lista fija omite tools/. Se registró DEBT-JUDGE-THREAT-SWEEP-TOOLS-01 con un control positivo y otro negativo exigidos para su cierre. El auditor de mocks sí detectó un control insuficiente, que fue corregido. Los cambios operativos que esperan decisión del usuario conservan ese estado.

## Resultado de publicación

`git push origin master` terminó con exit 1. Gitleaks de los commits salientes pasó. En la etapa pre-push pasaron 15 controles y fallaron 2; could_not_run=0. Tipos, cobertura Python, cobertura Bash, esquema, versión, integridad de líneas, recibos y los otros controles terminaron en PASS. El defecto de alcance del barrido de amenazas descrito arriba limita la interpretación de su PASS.

`ship-freeze` bloquea las 97 fichas abiertas: baseline aplicable=0. `backlog-verifier` detectó un cierre que reproduce: DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES. bb-guardia-proceso.service arrancó el 2026-09-30 14:40:12 CST, antes de la modificación actual del archivo. El cierre histórico conserva su evidencia; la comprobación actual queda fallida. La configuración apunta a bin/bb-guardia-proceso y sus 20 pruebas pasaron. Reiniciar esa protección activa requiere una decisión operativa separada y sigue pendiente.

La versión 2.3.0 queda comiteada localmente, con el árbol limpio; el remoto conserva su estado anterior porque el push fue rechazado por los gates.
