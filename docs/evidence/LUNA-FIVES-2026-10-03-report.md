# Ola Luna de cinco fichas — 2026-10-03

El inventario inicial tenía 99 pendientes. La ola tomó cinco fichas generadas desde esa fuente y las agrupó por causa en tres ejecutores Luna: APT (3), runtime (1) y OTA (1). Coordinación y reejecución independiente: Codex.

## Resultado

- Luna runtime: una ficha cerrada, DELTA-FORUM-RUNTIME-VERSION-CAPTURE-01. La prueba física independiente registró seis asignaciones, máximo agregado 4194304 bytes, readback completo, CUDA Runtime API 13000 y could_not_run=0. Se conservaron kernel, DGX release, driver, boot ID, versiones e imágenes Docker y estado GPU antes/después. Esto acredita captura y ensayo CUDA corto; la compatibilidad de serving sigue abierta en su ficha padre.
- Luna APT: cero cierres, tres fichas abiertas. Fuentes arm64 y firma local observadas; firma alterada rechazada; planes reales simulados con y sin remoción crítica discriminados. Faltan el caso de fuentes incompatibles, recuperación del host afectado y guard APT/OEM instalado.
- Luna OTA: cero cierres, una ficha abierta. Desarrollo integrado: release DGX declarado, versión NVIDIA cargada/en disco, MemAvailable y PSI. Faltan matriz OEM soportada y canario/recuperación/rollback.

El cierre runtime inicial se rechazó una vez por contrato incompleto: faltaban fecha, traslado a done e índice de evidencias commiteadas. Root completó esos datos y conservó el criterio original. Una lectura fallida adicional ocurrió porque root movió la ficha durante la primera suite; se repitió la validación con árbol estable. Se preservan las salidas incompletas.

## Reparto y deuda restante

Comandos y salidas literales:

```
python3 /home/lcasarin/.Codex/tools/triage.py merge --dir tasks/evidence/LUNA-FIVES-2026-10-03/wave01-verdicts --expected tasks/evidence/LUNA-FIVES-2026-10-03/batch_00.json --require status,evidence,reason
returned: 5 of 5

python3 /home/lcasarin/.Codex/tools/triage.py merge --dir tasks/evidence/LUNA-FIVES-2026-10-03/all-verdicts --expected tasks/evidence/LUNA-FIVES-2026-10-03/source.json --require status,evidence,reason
returned: 99 of 99
```

IDs ausentes: 0; duplicados: 0; desconocidos: 0; malformados: 0. Los 94 ajenos a esta ola conservaron la clasificación de la revisión anterior, identificada por fuente en remaining-classification.json; no se presentan como revisados nuevamente por Luna. Incluyen tres decisiones pendientes. El escáner posterior imprime TOTAL PENDIENTE (sin duplicar) 98. El esquema imprime checked=282 passed=282 failed=0 unverified=0 avisos=80 could_not_run=0. Backlog verifier: fraude=0, contract_breach=0, could_not_run=0, unverified=0.

Los lotes siguientes de cinco quedan generados. Su clasificación vigente requiere evidencia/recursos del sujeto o decisión de Luis. La skill [/0](/home/lcasarin/.agents/skills/0/SKILL.md) manda: «Bloqueada […] No se lanza; va al reporte final con su bloqueador nombrado». no se repiten las mismas investigaciones sin recursos nuevos. Los bloqueos individuales están en all-verdicts y remaining-classification.json.

## Validación e incidencias

La primera suite produjo 1 failed, 890 passed y una lectura ilegible durante el traslado. Tras corregir y commitear el cierre: 891 passed, 3494/3498 sentencias, cuatro sin cubrir. Aunque el ratchet aceptó 99.89%, se añadieron seis controles negativos de inspección de imagen, carga/símbolo CUDA y resultado API inválido. Validación final literal: `897 passed in 92.35s`; `Current coverage 100.00% meets watermark 100.00%`. Sentencias cubiertas: 3498/3498; missing=0; excluded=16 (mismo conjunto previo de Protocol). La fase serial informa 897 deselected porque ningún test porta mutates_real_source; la fase paralela ejecuta las 897 pruebas. La salida final de suite/cobertura se conserva junto con este reporte.

Los recibos faltantes de cherry-pick se validaron mediante el instrumento nativo sobre los seis SHA completos: GIT_VERIFIED_RETROACTIVE. Son reejecuciones históricas, no recibos originales. Los checks Bash sin archivos y Ruff/Rule B3/zero-debt sin fuente aplicable se imprimen como DID NOT RUN; could_not_run final=0. Se mantienen dos entradas antiguas del baseline de recibos, sin añadir entradas; expiración 2026-10-08. H1 sigue verde para sus afirmaciones actuales; la procedencia temporal figura en h1-final.txt. PII: hallazgos=0, could_not_run=0.

La redacción APT retiró dos direcciones públicas de contacto con el mecanismo existente; originales privados preservados y hashes/modos registrados. No se alteraron paquetes, configuración del host, servicio, clocks ni la investigación cruda pendiente de decisión. Se conservan cuatro errores previos de Pyright en el colector crudo bb_forum_fetch.py. Los nuevos helpers tienen verificación de tipos sin errores. Versión aplicada por instrumento nativo: 2.2.2. Sin push.
