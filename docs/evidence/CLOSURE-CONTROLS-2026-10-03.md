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

## Reparación oficial aterrizada

Productor: commit local `9a19c8be`, fuente y artefactos canónicos 9.3.2, primario limpio tras fast-forward. BB recibió 9.3.2 por `sync-satellites --runtime-only --plan` y `--apply`, sin editar ZIP a mano. El selector original pasó; el gate lee 35 archivos reales de tools, y el selector condena los negativos homoglyph/invisible. DEBT-JUDGE se mueve a done; ahora hay 96 fichas abiertas (dos cierres desde la fuente inicial de 98).

La suite nativa después del sync produjo `1123 passed in 145.43s (0:02:25)`; fallos 0, omitidas 0. El H1 de BB pasó con 0 stale. Pruebas y gate literales, lock, plan/aplicación en `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/scope-repair/`. El commit del productor pasó 6 hooks y emitió 8 avisos por priority desconocido; se mantienen esos avisos. Los controles kernel nuevos siguen en worktree: 125 pruebas enfocadas y cobertura explícita inicial 71 % sobre 872 sentencias, por lo que no se consideran listos para aterrizar ni cierran 13 investigaciones pendientes.

El primer antifraude tras mover DEBT-JUDGE detectó 1 contract_breach por secciones faltantes y 1 fallo colateral de esquema. Se corrigieron Root Cause, Regression Test, Verification Evidence e índice evidence. El esquema requiere además que los artefactos citados estén en HEAD; esa condición se valida después del commit del cierre, sin excepciones al instrumento. Se conserva la salida inicial en `scope-repair/backlog-before-record-fix.txt`.

Verificación posterior al commit 99c3591: el esquema y selector dieron `2 passed in 3.51s`; el antifraude dio fraudes 0, contract_breach 0, could_not_run 0, unverified 0. El cierre usa `relocated_prior_verification` con reason explícito porque el test y la reparación ya estaban en los commits 4b3595f/9a19c8be; el hook rechazó inicialmente `verified` sin cambio de source/test en el mismo commit. Se corrigió el contrato sin añadir prueba sintética. El commit final pasó 12 hooks; 4 se omitieron por no tener archivos de Python/Bash nuevos en ese commit documental; avisos priority conocidos: 5. Estas omisiones tienen ese alcance, y no sustituyen la suite nativa completa ejecutada sobre el cambio del kit.

## Inventario principal y ensayo de copia — 2026-10-03

`primary-selector-inventory.json` examina las 98 IDs originales contra el árbol `455d8ced`: 96 siguen abiertas; selectores pytest presentes=0, ausentes=64, otros comandos=32. La existencia se comprueba por AST, sin ejecutar los cierres; los borradores de los worktrees quedan fuera de ese conteo. Este registro impide confundir implementación en curso con integración verificada.

El coordinador ejecutó el exportador NVMe sobre un archivo sintético de 4096 bytes entre `/tmp` y `/dev/shm`, y después el retorno. Los dos pases conservan el hash y el origen; dos rechazos deliberados conservan su salida `could_not_run`. Conteos literales: pass=2, fail=0, could_not_run=2, resultados inesperados=0. Evidencia: `tasks/evidence/FEATURE-FORUM-NVME-READONLY-01/export-copy-lab/run.json`. La ficha NVMe continúa abierta por el alcance restante.

El exportador ahora emite `fail=0` y `could_not_run=0` en el pase, y `fail=0` con `could_not_run=1` ante imposibilidad. Validación posterior: `python3 -m pytest -q tests/test_nvme_readonly.py --cov=tools.nvme_readonly --cov-branch --cov-report=term-missing --cov-fail-under=100` devolvió rc0: `20 passed in 0.58s`; tabla literal de cobertura: `tools/nvme_readonly.py 145 0 56 0 100%` (Stmts/Miss/Branch/BrPart/Cover). Ruff pasó y Pyright declaró `0 errors, 0 warnings, 0 informations`.

## Revisión adversarial del borrador runtime lote 02

Dos mutaciones ejecutadas por el coordinador dieron falso `pass/could_not_run=0`: borrar toda identidad PID en MiniMax y sustituir las métricas M2 por dos filas prefill sin decode/proceso/host/reset limpio. Evidencia transcrita del output real: `runtime-batch02-root-negative.json`. El hash del borrador no se registró en esa ejecución; el archivo acredita el hallazgo revisado, no el comportamiento de una entrega futura. Se rechazó la integración y se solicitaron regresiones, matriz del alcance completo y controles de identidad y secuencias. La cobertura unitaria del 100% por sí sola deja estas omisiones sin demostrar.

## Validación integrada y negativo APT real

El gate canónico `python3 .simplecode/run.py simplecode.verification.coverage_target -q` primero devolvió rc1: `1 failed, 1125 passed in 142.42s`; `test_procesos_gpu_suman_la_memoria_unificada` seguía sustituyendo `_correr` y dejó pasar una consulta real por `_correr_resultado`. Se corrigieron las fixtures de consulta/procesos con `CompletedProcess`, preservando el control de memoria esperada de 44064 MiB. La suite focal de dos archivos pasó: `126 passed in 0.66s`.

El mismo gate, tras la corrección, devolvió rc0: `1126 passed in 143.39s`; serial lane `1126 deselected` porque ninguno lleva `mutates_real_source`. Cobertura: `5070/5070` sentencias, `missing_lines=0`, `excluded_lines=16` (preexistentes), watermark100%. No se midió rendimiento: pytest-benchmark informó desactivación por xdist. stdout/stderr, comando, hash del test y resumen se preservan en `native-coverage-after-fixture-fix/`; el fallo anterior sigue en `native-coverage-after-nvme/`. Son comprobaciones del árbol principal previo a integrar los nuevos controles de Luna.

El negativo APT ya se ejecutó con fuente Ubuntu incompatible arm64, configuración/cache/listas/logs aislados bajo `/tmp` y cero instalación. Resultado: update rc100/404 binary-arm64, indextargets rc0 con salida vacía, could_not_run=0. Evidencia: `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/wrong-source-canary/`. Su ficha sigue abierta para integrar y verificar el control completo del perfil e índices.

### Revisión adversarial runtime B04 — 2026-10-03

El coordinador reprodujo PASS en el fixture positivo de Triton y PASS tras sustituir la fuente auditada del allocator por un comentario `# NullAllocator caching_allocator_alloc`, recalculando su hash. El hash demuestra consistencia de bytes, y el predicado por nombres admite fuente sin implementación. Se rechazó ese control para integración y se pidió evidencia del código efectivo y canaries de lifetime/stream según la ficha. Recibo con hash del módulo antes/después: `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime-batch04-root-negative.json`. El segundo caso de fairness en ese recibo es inconcluso: su baseline devuelve unknown por falta de identidad/oracle y no acredita un falso PASS. Ninguna ficha fue cerrada con estos fixtures.

### Revisión de continuidad netconsole — 2026-10-03

El borrador del control exigía `bb telemetry --recent-jsonl`, subcomando ausente en bin/bb. La ejecución read-only `bash bin/bb telemetry --recent-jsonl` devolvió rc2 con `subcomando desconocido: telemetry`; recibo y SHA del módulo en `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/netconsole-continuity-command-negative.json`. Se pidió reutilizar la telemetría real de atom_gpu_telemetry.jsonl y vincular boot/reloj: __MONOTONIC_TIMESTAMP del journal no es comparable directamente con ts RFC3339. También se pidió comprobar rc de las capturas y admitir el diagnóstico de ip route get en stderr. El control conserva revisión pendiente pese a la cobertura de sus fixtures.

### Revisión de packing 4 KiB — 2026-10-04

El coordinador reprodujo PASS en verify_memory_saver para una asignación sin vínculo a workload de 4096 bytes de página y coste cero, texto arbitrario con SHA coherente y alignment_requirements=True. Recibo `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/memory-packing-root-negative.json`, con hashes del módulo antes/después. La matriz del agente citaba requisitos de HAL/DMA/cache/unmap/tracker/teardown, ownership y decisión medida que el predicado actual no comprobaba. Se rechazó el control y se pidió implementar el alcance íntegro de la ficha y corregir la matriz para distinguir comprobaciones ejecutables de requisitos pendientes. Tener PAGE_SIZE=4096 no satisface por sí solo el criterio de cierre.

### Recheck Triton y simulación APT vigente — 2026-10-04

Root reejecutó el mismo negativo de comentario-only contra el módulo runtime B04 corregido: baseline PASS y negativo FAIL por ausencia de implementación ejecutable. SHA del módulo idéntico antes/después; recibo `runtime-triton-root-recheck.json`. Esta aceptación cubre esa regresión y deja pendiente el cierre runtime íntegro.

La simulación read-only APT vigente terminó rc0 con 14 upgrades propuestos, cero instalaciones nuevas, cero removidos y un paquete retenido, could_not_run=0. Los cuatro InRelease al final conservan los hashes archivados. Recibo `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/current-upgrade-simulation.json`. No hubo upgrade real ni aprobación implícita de terceros.

### Revisión de aplicabilidad pstore — 2026-10-04

El verificador del borrador admitió PASS con OEM/BIOS/EC/driver desconocidos, un texto que solo enumera FPAC/PSCI/NMI y un supuesto documento vendor cuyo único contenido es el kernel local, recomendando RMA con motivo arbitrario. Evidencia `pstore-root-negative.json`, hash del módulo antes/después. Se rechazó el criterio por ausencia de identidad, diagnóstico/resolución aplicable y separación de las señales SBSA/DOE/link. Coincidencia de términos, URL o hash no acredita la recomendación. La revisión pidió soporte específico del OEM, sin exigir autenticación de origen imposible a las capturas suministradas.

### Inventario y ejecución runtime generados — 2026-10-04

La comparación de las 98 fichas contra source.json arroja 98 close_check intactos, cero cambiados, cero ausentes (`original-close-check-preservation.json`). El inventario AST de cuatro árboles (`selectors-current-trees.json`) es estructural: no prueba colección ni aceptación. Primary conserva 64 selectores ausentes; runtime define 38 incluyendo la ficha scope ya cerrada.

Root ejecutó los 37 selectores runtime abiertos, generados de sus comandos originales, en el worktree runtime: pytest rc1, 37 fallos de aserción en 0.67s. Cada uno devuelve unknown/could_not_run=1 por ausencia de runtime-capture.json; resultados funcionales pass=0, fail=0, unknown=37, could_not_run=37, IDs duplicados/ausentes=0. Evidencia literal `runtime-root-close-check-run/{run.json,stdout.txt,stderr.json}`. No se omitió ningún selector abierto; la ficha scope cerrada se excluye explícitamente de esta corrida. Esto demuestra bloqueo por captura ausente, no cumplimiento del alcance de cada predicado.

### Revisión de recuperación parser/MTP — 2026-10-04

Root construyó los sidecars oracle del fixture MTP B03 y obtuvo baseline PASS. Cambiar los PID antes/después de cancelar de 100 a 200 sigue PASS; MTP=-1 también sigue PASS. Recibo `mtp-parser-root-negative.json`, hashes del módulo estables antes/después. El baseline carecía de prueba del mismo proceso, eventos temporales de cancelación, finish/exit/restart y repetición tras restart exigidos por la ficha. Se rechazó para integración y se pidió matriz admitida fijada, controles específicos y cobertura de todos esos criterios. El floor100 anterior describe líneas/ramas ejecutadas y deja pendiente ese alcance semántico.

### Retorno exact-once runtime y APT canary — 2026-10-04

La herramienta oficial `python3 /home/lcasarin/.Codex/tools/triage.py merge --dir tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime-return-audit --expected tasks/evidence/CLOSURE-CONTROLS-2026-10-03/runtime.json --require status,reason,control_command` devuelve rc0, returned: 38 of 38. Ausentes=0, IDs desconocidos=0, duplicados=0, malformados=0. Los retornos se distribuyeron desde los batches originales, máximo diez IDs por archivo. Estados reportados: PASS=1, FAIL=0, UNKNOWN=37. Es prueba de retorno de estados del agente, no aceptación de predicados ni cierre del sujeto; snapshot de verdict con SHA en audit.json.

APT real en un repositorio file firmado con clave exclusiva del canary acepta baseline (rc0) y rechaza el mismo Packages alterado con Hash Sum mismatch (rc100) y el InRelease alterado con BADSIG (rc100). Los dos negativos conservan indextargets vacío en estados frescos aislados. pass=3, fail=0, could_not_run=0. Se archivó solo clave pública; temporal/clave privada eliminados. La contraparte sana ports arm64 también terminó update/gpgv rc0. Receipts completos y collector archivados en la ficha APT.

Los rechecks de los contraejemplos packing/pstore ahora devuelven UNKNOWN CNR1, en lugar del PASS anterior. `kernel-counterexamples-root-recheck.json` verifica únicamente esas regresiones y no declara completo el alcance de las fichas.

Las salidas stderr vacías de triage y pytest se conservan como JSON con string vacío, tamaño literal cero y SHA256 de bytes vacíos, sin fabricar salida ni exceptuar el guard de truncación.
