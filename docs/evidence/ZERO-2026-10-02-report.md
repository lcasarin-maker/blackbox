# Ola de deuda y limpieza: 2026-10-03

Reinicio confirmado: `systemctl show bb-usable.service -p ActiveState -p SubState -p MainPID -p ActiveEnterTimestamp` devuelve active/running, PID 4137024, 2026-10-03 00:10:01 CST. El proceso cargó después de la modificación de bin/bb-usable.

La fuente final contiene 168 fichas: 68 cerradas y 100 abiertas; 97 bloqueadas por evidencia, verificadores o dependencias pendientes y 3 decisiones: dos recolectores de investigación y sincronización de dos archivos del host. El merge de triage devuelve 168/168, sin ausentes, duplicados, desconocidos ni malformados. El corpus total gobernado tiene 282 fichas: 182 done y 100 abiertas.

Se corrigieron tipos locales, observabilidad de pruebas, validación de boot_id, privacidad de diagnósticos y controles negativos nativos. La auditoría H1 registró 12 afirmaciones con 0 violaciones después de contrastar código, pruebas y capturas del host. Se publicó localmente la versión 2.2.0 y los 20 sunsets quedan vigentes.

El pre-push completo falló: 12 hooks pasaron y 5 fallaron. Cobertura de sentencias: 3372/3372, missing=0, excluded=16 (Protocol de CUDA); esta medición no mide ramas. Los recolectores pendientes producen 6 hallazgos agregados en 2 archivos, 15 incidencias JSONL y 4 errores Pyright. Ship-freeze registra 100 fichas abiertas bloqueantes, could_not_run=0. Hay además 24 aplazamientos nativos: 20 sunsets, 3 órganos inaplicables y 1 presupuesto firmado.

Después de ese pre-push se corrigió el alcance del close_check de nueve eventos: juzga sus nueve IDs; el gate global sigue vigente. `python3 .simplecode/run.py simplecode.verification.backlog_verifier --root . --no-revert --gate` devuelve frauds=0, could_not_run=0, contract_breaches=0 y unverified=0; declara 109 resultados cacheados, el más antiguo de 23.6 días. Las cuatro incidencias actuales de telemetría se clasificaron como defectos confirmados con sus salidas originales. El informe posterior devuelve HALLAZGOS=0, could_not_dispose=0, pending_grace=0 y historical_undisposed=3. Esos tres eventos antiguos siguen en ficha abierta porque falta evidencia histórica.

Permanecen tres bloqueos de publicación: zero-debt por los recolectores, Pyright por esos mismos archivos y ship-freeze por las 100 fichas abiertas. No se hizo push ni se añadió baseline, amnistía o cutoff. La higiene conserva capturas crudas pendientes de decisión y worktrees recientes o sin integrar; no había candidatos aprobados para poda o archivo.

Límites conservados: calibración de latencia sin episodio positivo (rc=2), intentos iniciales impedidos por sandbox, dos consultas de SHA inválidas y una fuente parcial del foro con could_not_run=1. Esas limitaciones históricas permanecen en la evidencia; el resultado no declara al sistema libre de deuda.

Evidencia reproducible: [fuente](../../tasks/evidence/ZERO-2026-10-02/workload-final-source.json), [triage](../../tasks/evidence/ZERO-2026-10-02/final-triage.txt), [pre-push completo](../../tasks/evidence/ZERO-2026-10-02/prepush-after-final.txt), [cobertura](../../tasks/evidence/ZERO-2026-10-02/full-coverage-final.json), [verificación de cierres](../../tasks/evidence/ZERO-2026-10-02/backlog-verifier-after-scope.txt), [telemetría](../../tasks/evidence/ZERO-2026-10-02/telemetry-final-b6ca/telemetry-report-final.txt).
