# Swarm de cierre — 2026-10-03

Objetivo activo: desarrollar los controles faltantes y ejecutar acciones/evidencias necesarias. Luna ejecuta; root revisa. Los lotes salen de la fuente de 98 fichas y contienen como máximo 10 IDs. El registro inicial exact-once devolvió `returned: 98 of 98`; describe cobertura de seguimiento, no cumplimiento de los criterios ni aceptación del código.

## Cierre verificado

`DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES` pasó de backlog a done. El servicio de usuario estaba inactive con un timestamp histórico. El control ahora requiere active/running, PID válido existente y arranque posterior al código. La indicación de reinicio distingue gestor de usuario y sistema. Se validó con 32 pruebas nativas, 0 omitidas, y se inició el servicio con exit 0. El close_check original pasó sobre el proceso iniciado Sat 2026-10-03 22:09:18 CST. Evidencia: `tasks/evidence/DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES/recierre-2026-10-03.txt`.

Quedan 97 fichas en backlog. Sus criterios y comandos de cierre se conservan.

## Validación del checkout principal

- `python3 -m pytest -q -n 4 -m 'not slow and not e2e and not mutates_real_source'`, con acceso nativo: `1122 passed in 138.71s (0:02:18)`; fallos 0, omitidas 0.
- Corrida previa aislada: `12 failed, 1106 passed, 4 skipped in 195.14s (0:03:15)`. Sus fallos incluyen acceso denegado al bus systemd y bind de sockets. Se conserva el resultado; no se añadieron exenciones.
- Backlog verifier nativo: fraudes 0, could_not_run 0, contract_breaches 0, unverified 0; 283 fichas gobernadas. Su caché contiene 178 veredictos, el más antiguo de 24.4 días: este gate no declara todas las filas recién ejecutadas.
- Ruff focal: `All checks passed!`; Pyright focal: `0 errors, 0 warnings, 0 informations`.
- Zero-debt de código: PASSED 91, CONVICTED 0, COULD_NOT_RUN 0; 24 detectores, 0 excluidos. Este instrumento no sustituye los cierres del backlog.

El diff staged reportó 16 líneas con espacios al final en `root-suite.txt`, exclusivamente el stdout literal de pytest (`E    `). Se conservan esos bytes como evidencia; los archivos de código no presentan ese hallazgo.

Salidas literales y fuente: `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/`.

## Trabajo en revisión

Los ejecutores están separados en kernel (13 IDs), runtime (38) y hardware (47), con sublotes de 10. Root rechazó un prototipo hardware que siempre devolvía unknown y un prototipo runtime que aceptaba declaraciones pass sin interpretar los datos. También rechazó selectores experimentales que aprobaban evidencia ausente. Esas entregas se están corrigiendo; no se integraron ni cerraron fichas por ellas.

La reparación del scope de amenazas se probó en una copia aislada del productor: 31 pruebas pasaron y el bundle candidato leyó 37 archivos de tools en el worktree de runtime. El bundle oficial del principal sigue omitiendo tools; la ficha permanece abierta. Un worktree real del productor prepara la reparación y su versión. Falta validación y aterrizaje oficial antes de sincronizar el kit del principal.

## Acciones pendientes

El despliegue de dos archivos requiere contraseña sudo. El script revisado `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/deploy-drift-reviewed.sh` verifica los cuatro hashes originales, conserva backups con permisos y propietarios, instala exclusivamente los dos destinos y ejecuta drift. No se ejecutó este despliegue. El diagnóstico nativo de solo lectura contiene 6 could_not_run; el diagnóstico aislado contiene 21. La captura kernel aislada contiene 1 could_not_run por pstore sin acceso. Ninguna acredita ensayos de panic, recovery, firmware ni carga CUDA.

No se publicó esta ola. El objetivo permanece activo; el informe registra trabajo comprobado y pendientes.

## Continuación: control de scope incorporado

Tras el commit 282833b se añadió el close_check faltante de DEBT-JUDGE. Sobre el kit oficial el selector produce `1 failed in 0.17s` (exit 1): compara 35 módulos reales con un scope que omite tools. Esta es evidencia negativa del defecto vigente, no un cierre. El resultado anterior de 1122 pruebas corresponde al checkout previo a este control; ahora este selector está rojo hasta reparar y sincronizar el productor. Ruff y Pyright del test nuevo pasan; could_not_run del selector: 0. El productor en worktree continúa en validación, sin release ni sync del principal.
