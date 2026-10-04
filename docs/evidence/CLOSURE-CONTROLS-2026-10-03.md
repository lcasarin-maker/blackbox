# Swarm de cierre — 2026-10-03

Objetivo activo: desarrollar los controles faltantes y ejecutar acciones/evidencias necesarias. Luna ejecuta; root revisa. Los lotes salen de la fuente de 98 fichas y contienen como máximo 10 IDs. El registro inicial exact-once devolvió `returned: 98 of 98`; describe cobertura de seguimiento, no cumplimiento de los criterios ni aceptación del código.

## Estado actual verificado — 2026-10-04

La fuente original conserva 98 IDs: 2 fichas en done, 96 abiertas y 0 diccionarios `close_check` modificados. La auditoría actual está en `original-98-preservation-after-docker-nvme.json`. Los apartados posteriores conservan la cronología; sus conteos previos describen cada momento.

La última corrección hardware pasa 110 pruebas, con 0 fallos y 0 sin ejecutar. El CSV nativo NVIDIA identifica GB10 y driver 580.178.04; su parseo quedó verificado. Los comandos físicos GPU/WiFi/USB siguen UNKNOWN/rc2. Recibos: `hardware-csv-ssh-followup-primary.json`, `native-nvidia-csv-reader-recheck.json` y `hardware-three-original-followup-recheck.json`.

El gate de higiene de código registra 140 archivos, 0 hallazgos y 0 sin ejecutar; Pyright registra 0 errores, 0 avisos y 0 informaciones. Son comprobaciones de código. La última suite general, con Docker y NVMe integrados, registra 1960 aprobadas, 117 fallidas y 4 omitidas; cobertura literal `TOTAL 14645 420 6202 315 96%`. El seguimiento nativo registra 25 aprobadas, 0 fallidas, 0 omitidas y 0 sin ejecutar: resuelve 13 fallos del sandbox y verifica el archivo del demonio, con solapamiento de casos entre ambas corridas. Los conteos se mantienen separados. Quedan 104 nodos fallidos: 103 controles requieren evidencia de cierre y 1 gate exige los artefactos SMI en HEAD; el seguimiento de esquema resolvió el aviso de contexto e2e, con 0 avisos actuales. Recibos: `all-controls-global-c-terminal.json` y `global-c-native-followup-terminal.json`. La validación global sigue fallida.

Los mapas generados cubren 13 IDs kernel, 37 runtime y 47 hardware, más el ID judge ya cerrado excluido del mapa runtime. Root verificó los IDs y los comandos originales; los merges exact-once devolvieron 13/13, 37/37 y 47/47. Las dos capturas locales con igual contenedor/digest vLLM acreditan identidad parcial, sin acreditar modelo, request ni resultado. Artefactos: `kernel-readonly-root-integrated/`, `runtime37-external-root-integrated/` y `hardware-readonly-root-integrated/`.

Se encontraron dos brechas de implementación en los comandos de cierre por archivo de tests: Docker reinicios y NVMe. El primero pasa 10 pruebas unitarias del contador, pero omite recuperación, conservación de datos y rollback reales. El segundo acredita el lector y una copia regular entre filesystems, mientras deja pendiente OEM y recuperación del dispositivo. Ambos controles quedaron integrados en los mismos archivos: NVMe 28 unitarios aprobados y un selector UNKNOWN por siete capturas ausentes; Docker 20 unitarios aprobados y un selector UNKNOWN por falta de restart-cycle. Los 17 y 10 tests originales respectivamente conservaron su AST. Recibos `nvme-real-selector-primary-integration.json` y `docker-real-selector-primary-integration.json`. Las fichas siguen abiertas.

Despliegue: 41 archivos revisados, 2 divergentes, 0 ausentes, 1 suspendido y 0 sin ejecutar. Los cuatro hashes del script de despliegue revisado siguen vigentes. La autorización solicitada sigue pendiente; no se cambió el host.

El escaneo previo de privacidad de artefactos pendientes registró 490 archivos textuales revisados, 45 hallazgos y 27 binarios que el escáner textual no pudo inspeccionar; precede a los últimos recibos y al derivado redactado. La revisión separada de ocho bases SQLite de cobertura registró 0 hallazgos y 0 sin ejecutar; las 19 keyrings tienen revisión de paquetes separada. Estos resultados conservan sus ámbitos y no convierten el escaneo textual en un pase. Los cambios siguen sin commit/push.

La captura privilegiada de DRM/watchdog está preparada en `capture-drm-watchdog-readonly.sh`: tres consultas de solo lectura, timeout de cinco segundos por consulta, salida JSON con hashes y tamaños completos. `drm-watchdog-capture-script-review.json` registra sintaxis rc0 y rechazo sin root rc2; consultas privilegiadas ejecutadas=0, cierres físicos=0, could_not_run=1. La ejecución requiere al operador con sudo. Este recibo verifica preparación y rechazo, sin acreditar valores DRM ni propietario watchdog.

El recheck AST de los 64 selectores originalmente ausentes registra 64 bindings presentes, 0 ausentes y 0 sin ejecutar (`original-64-selector-presence-current.json`). Acredita existencia en primary, sin probar semántica ni cierre físico. Luna ejecutó el selector original SMI: `1 passed in 4.81s`, exit 0, recorrido CLI `bb sample` con shim sano/error/bloqueado. La ficha extra enlaza la captura actual y declara el alcance de software. El seguimiento literal de `ledger_schema` registra `checked=284 passed=283 failed=1 unverified=0 avisos=0 could_not_run=0`; el fallo restante exige las tres evidencias SMI en HEAD. Recibo `ledger-schema-after-smi-context.json`.

La revisión de aterrizaje encontró un falso PASS en batch02: JSON `false` se comparaba con código de proceso cero en SM121 y compilación fría. Root reprodujo el PASS en SHA `bbc0b95cf43903b393b850b1b5a450d4f0cf13ec920af0bae6c36a8cf3a767e4`; Luna reutilizó `_integer` para exigir enteros exactos. La misma entrada ahora devuelve UNKNOWN/CNR1. El archivo completo da `10 failed, 25 passed in 0.12s`: los diez fallos corresponden a capturas físicas ausentes, con 0 casos omitidos. Pyright focal: `0 errors, 0 warnings, 0 informations`; zero-debt: 140 archivos, 0 hallazgos, 0 sin ejecutar. Se conserva un intento del harness sin PYTHONPATH, rc1/CNR1, y la repetición corregida. Recibos `runtime-b02-bool-root-reproduction.json`, `runtime-b02-bool-root-recheck.json` y `runtime-b02-root-final-suite.json`. La suite global C precede esta corrección y sus conteos siguen históricos; la validación actual de esta modificación es focal. Fichas: 2 done, 96 abiertas; close_check intactos.

La revisión de procedencia reconcilia los 45 matches textuales: 26 nombres tar, 8 canarios, 9 contactos públicos APT y 2 direcciones de origen indeterminado. Root verificó los 45 hashes/ubicaciones: 0 ausentes, 0 adicionales, 0 errores, 0 sin ejecutar. La revisión Luna conserva sus 27 binarios sin inspeccionar y su limitación sobre la fuente canónica; root comprobó después que la línea del test existe en el archivo canónico y en HEAD, con 0 sin ejecutar. Eso prueba ubicación, sin probar origen ficticio. Se preparó `simplecode-producer-validation/reviewed-producer.redacted.patch`, dos sustituciones, original intacto; el derivado sirve para revisión y pierde aplicación directa. La elección de conservación/publicación está pendiente. Recibos `publication-artifact-pii-provenance-review-20261004.json`, `publication-pii-classification-root-integrity.json`, `publication-indeterminate-canonical-source-root-review.json` y `publication-producer-redaction-candidate.json`. Esta revisión no convierte el scanner en un pase ni cierra fichas físicas.

## Registro cronológico — primer cierre verificado

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

### Revisión nativa del control GPU clock A/B — 2026-10-04

El fixture positivo del agente hardware da PASS con comandos nvidia-smi que contienen --bb-phase, opción ajena al CLI, y cap apply posterior a todas las filas capped. La consulta inicial en sandbox devolvió rc9/CNR1 por acceso al driver; la consulta readonly autorizada del host devolvió rc2: Option --bb-phase is not recognized. Ambas observaciones se conservan separadas en gpu-clock-root-negative.json. Ningún comando de ajuste de clocks se ejecutó. Se rechazó para integración y se pidió metadata de fase real, cronología, rc del workload, soak predeclarado, idle/control y load/unload, resultados de fallo/latencia y confirmación de política restaurada, conforme a la ficha.

### Revisión adversarial posterior de packing y persistencia

- `packing-comparability-root-negative.json`: el helper de costes aceptó stock con request 4096 y packed con request 8192; las cargas difieren. Se requiere comparabilidad antes de concluir coste/portabilidad. Es una prueba sintética del instrumento, no una medición del host.
- `netconsole-persistence-root-negative.json`: el baseline y la variante `options netconsole nonsense=1` produjeron ambos `None` (sin hallazgo) en el helper de persistencia. Se requiere ligar parámetros al destino aprobado y capturar/restaurar modo además del contenido. No se configuró netconsole ni se emitió un marcador.
- `native-suite-parser-validation.json` conserva la corrida principal completa: 1139 passed, 1 failed, 101.28 s; 5111/5111 sentencias cubiertas, 16 exclusiones preexistentes. El fallo es el escáner PII sobre rutas públicas DEP11 con arroba; el gate sigue fallando y los manifiestos firmados se conservan íntegros.

- `mtp-request-schema-root-negative.json`: el control MTP pasó con un baseline sintético y también al sustituir todos los bytes de petición por texto arbitrario no JSON, recalculando coherentemente hashes de entrada/sidecar/eventos. La integridad criptográfica no valida una petición de inferencia ni la liga al modelo y herramientas. Corrección asignada: validar y ligar el payload API real y los oráculos al sujeto/perfil. No hubo ejecución de servidor, HTTP ni GPU.

### Revisión de alcance del control de clock

La implementación de hardware conserva pendientes: cap seleccionado por dueño y confirmado por driver; comparación de workload/modelo/entrada/stack; confirmación de rango efectivo aplicado/restaurado; cobertura temporal del soak, throttle y señales de energía. El snapshot instantáneo dentro de 300–2800 MHz no prueba restauración de la política. Se asignaron estas correcciones y se eliminó de la ficha un párrafo duplicado del mismo post 376039, conservando su contenido en la segunda referencia. No se modificó el close_check ni se cambió el reloj del host.

### Colección real del módulo de registro original

`registration-collection-current.json` archiva cuatro ejecuciones `python3 -m pytest --collect-only -q tests/test_debt_registration_controls.py`, todas rc0/could_not_run=0. De los 98 comandos originales, 64 apuntan a este módulo y 34 usan otros comandos. Primary: 0 presentes/64 ausentes; runtime: 37 presentes/27 ausentes; kernel: 0/64; hardware: 0/64. Estos conteos prueban presencia de nodos, no aprobación de controles ni cierres. Las fábricas dinámicas en otros módulos y helpers con nombres similares no satisfacen el comando original; se asignó registrar las delegaciones en la ruta exacta.

### Repetición de regresiones de persistencia y comparabilidad

`packing-netconsole-root-recheck.json` fija hashes actuales de ambos módulos: la fixture de persistencia actualizada pasa el helper (None), mientras la variante `options netconsole nonsense=1` con SHA coherente produce FAIL específico por entrada activa ausente. La comparación de packing parte de baseline PASS y cambia sólo el request/backing del lado packed; ahora produce UNKNOWN/could_not_run=1 por workload mismatch. Son controles sintéticos de regresión del instrumento, no evidencia de host ni cierre de experimentos. Sigue en revisión que la decisión de coste considere el total comparable antes de exigir un candidato.

### Primera integración Kernel al árbol principal

Se importaron cinco verificadores, tres archivos de pruebas/helpers y tres delegaciones en el módulo literal de registro; manifiesto con hashes en `kernel-integration/import-manifest.json`. Primary: 102 pruebas unitarias pasan; tres selectores originales fallan por evidencia real pendiente, conservando stdout. Ruff pasa; Pyright canónico revela 93 errores de tipos en tests nuevos (0 warnings/0 informations), asignados a corrección sin suprimir diagnósticos. La cifra 206 reportada por worker requiere reconciliar su comando exacto; no se usa como conteo de esta corrida principal. `kernel-integration/primary-validation.json` conserva ambos resultados. Ninguna ficha cambia de estado.

### Ejecución de los 13 comandos Kernel originales en primary

`kernel-integration/primary-all-original-commands.json` preserva los 13 comandos literales y stdout/stderr: 0 rc0, 13 no cero, 0 timeouts/errores de lanzamiento. Ocho CLIs producen JSON UNKNOWN (repro reporta could_not_run=23; siete restantes, 1 cada uno); tres selectores fallan por esos pendientes; un CLI compartido de forum sigue ausente hasta integrar hardware. No se suman contadores de selectores y CLIs que evalúan el mismo sujeto. Batches generados 10+3 y triage canónico: returned 13 of 13, 0 missing/unknown IDs/duplicated/malformed; subject pass=0 fail=0 unknown=13. Integridad del retorno no prueba cierre ni ausencia de deuda.

### Corrección del gate de tipos y reparto de la siguiente ola

El ejecutor corrigió los Optional con validaciones explícitas. Salida primaria canónica archivada en `kernel-integration/primary-pyright-fixed.txt`: 0 errors, 0 warnings, 0 informations; rc0. `primary-units-fixed.txt`: comando focal de dos archivos, 102 passed in 0.34s. Las 206 pruebas del reporte previo pertenecen a seis archivos, un alcance distinto; la discrepancia queda explicada sin sumar ejecuciones como pruebas nuevas.

Para continuar todos los pendientes se generó `hardware-batch03-kernel-executor.json` directamente del source hardware, posiciones20:27 (7 IDs). El ejecutor Kernel toma ese subconjunto en archivos nuevos aislados; Hardware conserva lote02 y el resto. Los retornos se reconciliarán con el source47 completo. No se redujo el alcance98 ni se cambiaron close_checks.

### Gate global integrado y remediación del índice de evidencia

`kernel-integration/integrated-global-native-validation.json`: 1264 passed, 8 failed, 138.12s; cobertura de sentencias 6800/6800, 0 missing, 16 exclusiones previas. Seis nodos evaluaban dos veces tres cierres Kernel pendientes; otros fallos: PII e índice schema.

El índice schema identificó la matriz documental ubicada bajo tasks/evidence como tarea fuera de carpetas gobernadas. Se movió sin cambiar bytes a `docs/evidence/KERNEL-CLOSURE-CRITERIA-2026-10-03.md` (hash y modo en `kernel-integration/criteria-matrix-relocation.json`). Repetición literal `python3 -m pytest -q tests/test_debt_registration_controls.py::test_debt_schema_evidence_index_scope_01`: 1 passed in 3.43s. Se quitaron únicamente tres wrappers duplicados de `test_closure_kernel_selectors.py`; los helpers y los tres nodos originales de registro siguen ejecutando los mismos controles completos. Ningún close_check se modificó. El gate global aún tiene cierres pendientes y PII; no se afirma limpio.

El parche propuesto de seguridad de Simplecode mostró dos regresiones comprobadas (atributos verify/host). `simplecode-insecure-targets-root-negative.json` archiva casos y hash del detector. Se devolvió al ejecutor antes de aplicar/sync; literal protegido y asignación ejecutable deben conservar distinta clasificación.

### Preservación de criterios tras integrar Kernel

`original-close-check-after-kernel-integration.json` compara todos los diccionarios close_check e identidades con el source original98: 98 iguales, 0 cambiados, 0 ambiguos/ausentes; 2 rutas done y 96 backlog. El contenido de las fichas puede documentar progreso sin alterar su exigencia original.

### PII de evidencias aún sin versionar

`pending-evidence-pii-review.json` usa el scanner propuesto del productor sobre 74 archivos tasks/docs nuevos o modificados, incluidos no tracked: 31 findings, 0 could_not_run. Treinta corresponden a paths DEP11 en una variante de formato nativo de seis campos que el primer parche no reconoce; el restante es un contacto institucional publicado en el Label del manifiesto firmado de libnvidia-container. Se conservaron valores sólo como hash/máscara en este reporte. Corrección asignada al productor con negativos; los manifests firmados permanecen intactos. Este barrido exploratorio no sustituye el gate canónico posterior al sync y no se declara limpio.


Avance del parser Deb822 (2026-10-04): las suites con ruta exacta terminada en `/` omiten Components; las suites de distribución los requieren. Se valida también la combinación inválida de ambos formatos. `python3 -m pytest -q tests/test_apt_sources.py --cov=tools.apt_sources --cov-branch --cov-fail-under=100`: **60 passed in 0.19s**, 289 sentencias y 124 ramas, 0 faltantes, 100 %. Ruff: `All checks passed!`; gate Pyright canónico: `0 errors, 0 warnings, 0 informations`. could_not_run=0 en esta validación. Recibo: `tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/deb822-exact-path-unit-validation.json`. La ficha sigue abierta: falta el control original compuesto, aprobación de fuentes y política de antigüedad.


Ampliación de integridad nativa (2026-10-04): `python3 tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/all-effective-index-hashes-collector.txt` produjo `{"indices": 137, "pass": 137, "fail": 0, "could_not_run_count": 0}`. Se verificaron todos los tipos de índices efectivos enumerados, sin filtrar sólo Packages, contra METAKEY/hash/tamaño de los manifiestos archivados y verificados por su Signed-By específico; se comprobó estabilidad del archivo durante lectura. El recibo conserva comandos y hash del collector. No prueba aprobación, vigencia, actualización fresca ni cobertura completa de índices configurados pero ausentes. La ficha sigue abierta.


Auditoría batch03 térmico (2026-10-04): captura canónica de solo lectura `tools.thermal_coverage.capture(Path("/"))` dio observed, could_not_run=0 y Linux en host.system. El lector propuesto buscaba system en top-level, campo ausente que el fixture inventaba. Se preservó el contraejemplo en thermal-collector-schema-root-audit.json y se devolvió al agente para reparación. También se señalaron el sello de rechazo de un comando inexistente y el vínculo de límites OEM a inventario en lugar de documentación OEM. El bloque continúa sin integrar ni cerrar fichas.


Componente criptográfico reutilizable (2026-10-04): `verify_release_signature` en tools/apt_sources.py copia entradas regulares acotadas a 8 MiB, sin seguir symlink final ni bloquear en FIFO, y ejecuta gpgv con keyrings explícitos sobre esos bytes. Las copias temporales se eliminan al salir; sólo conserva VALIDSIG y hashes, sin UID. Firma inválida bloquea; clave ausente, proceso inaccesible/salida truncada o formato incompleto producen could_not_run. No concede aprobación ni vigencia. Unit validation: 75 passed in 0.27s, 337 sentencias/138 ramas, 0 missing/partial, 100%; Ruff y Pyright canónico pasan. Replay del componente sobre los mismos 25 manifiestos archivados: pass=25, fail=0, could_not_run=0, changed_manifests=0. Recibos signature-component-unit-validation.json y signature-component-native-replay.json. Original close_check aún pendiente; ficha open.


Revisión del bloque batch03 reparado: se verificó la ejecución focal del worker y se preservó stdout literal en hardware-batch03-root-validation.json. El lector usa host.system y el test incluye el collector canónico sobre raíz fixture. La cobertura de ramas sigue incompleta; el bloque permanece sin integrar. Se pidió completar auditoría criterio→predicado y negativos de las rutas de rechazo antes del gate de 100%.


Aislamiento de confianza (2026-10-04): gpgv ahora usa homedir temporal explícito además de los keyrings proporcionados. Un negativo real intenta verificar el baseline firmado con la clave NVIDIA ajena: devuelve could_not_run=1, fail=0, ningún VALIDSIG y comprueba eliminación del home temporal. El suite focal da 76 passed in 0.27s, 337 sentencias y 138 ramas al 100%; Ruff pasa. Replay tras cambio:25 pass,0 fail,0 could_not_run,0 changed_manifests. Recibos signature-isolated-trust-unit-validation.json y signature-isolated-trust-native-replay.json. La clave ajena es un negativo esperado del test, separado de la ejecución válida del suite; aprobación y vigencia siguen pendientes.


Componente de ensayos APT aislados (2026-10-04): check_isolated_update_control recalcula aceptación o rechazo desde argv/rc/stdout/stderr, con apt-config dump sin hooks, directorios bajo raíz propia /tmp, Error-Mode=any, arquitectura arm64 y rechazo explícito de repos inseguros. Rechaza índices residuales en negativos y cambios de comando hacia install. Receipt authors, source bytes/trust/timing/cleanup siguen siendo gates separados. Recomputación de cinco ensayos archivados (Ubuntu sano, fuente incorrecta, file sano, hash y firma alterados):5 pass,0 fail,0 could_not_run. Suite focal:95 passed in 0.31s,377 sentencias/162 ramas,0 missing/partial,100%; Ruff pasa. Recibos isolated-update-control-replay.json e isolated-update-control-unit-validation.json. Original close_check compuesto sigue pendiente, ficha open.


Contraejemplo de firmware batch02 (2026-10-04): baseline sintético del fixture PASS; postinst que invoca `exec sh /usr/lib/vendor/fw-helper.sh` con cuerpo del helper ausente también PASS. La ficha exige detectar escritores indirectos y fallar cerrado ante evidencia faltante. Se preservó el resultado en firmware-indirect-helper-root-negative.json y se devolvió al agente para corregir cadena de scripts. Se señaló además que el fixture de firma inventaba GOOD signature para dpkg-sig y que gpgv sobre un .deb no demuestra la cadena APT Release→Packages→paquete. Sin intervención de firmware real. Permisos: receipt approved_by dentro del bundle sólo es una afirmación; faltan decisiones humanas reales para los ensayos invasivos, ninguna inferida del objetivo global.


Segundo contraejemplo firmware batch02 (2026-10-04): query PSID/fw en BDF03:00.0 permanece fijo, pero se cambia lspci BusMaster+ a BDF04:00.0; el lector propuesto sigue PASS. firmware-device-binding-root-negative.json conserva ambos bundles sintéticos completos y resultados para reproducir. Se devolvió al agente para vincular query PSID/firmware, BME, mlx5 e ibv al mismo dispositivo. Identidad faltante debe ser UNKNOWN; identidad contradictoria FAIL. El bloque sigue sin integrar.


Auditoría memoria batch02 (2026-10-04): free -b available=60000 es convertido por el lector a61440000, factor1024 indebido; swap tiene el mismo defecto, mientras RSS de ps sí usa KiB. Prueba nativa read-only ps sobre pid_max+1 devuelve rc1 con stdout/stderr vacíos; el fixture usaba rc0 para ausencia y el lector rechaza el estado real. memory-units-and-absent-pid-root-audit.json preserva ambas observaciones; se devolvió al agente para corrección y regresiones, sin terminar procesos ni ejecutar soak real.


Capturas truncadas (2026-10-04): check_isolated_update_control ahora conserva could_not_run cuando config/update/targets declara stdout o stderr truncado, aunque el prefijo tenga rc100 y el marcador esperado. Seis negativos baseline-first cubren los tres receipts y ambas salidas. Suite:101 passed in 0.32s,377 sentencias/162 ramas,0 missing/partial,100%; Ruff pasa. Recibo isolated-update-truncation-unit-validation.json. Cierre integral sigue pendiente.


Recheck raíz de memoria batch02 (2026-10-04): memory-units-and-absent-pid-root-recheck.json confirma free -b60000→60000bytes, swap10000→10000bytes, RSS6291456bytes desde6144KiB y cliente detenido por ps rc1 vacío con servidor aún running. Suite del worker34passed0.05s; sin soak real ni cierre de ficha.


Gate completo de productor archivado (2026-10-04): sesión97422 terminó rc0; log16965bytes SHA256e8f7f25ffee80da93312429a9325a1cc27e14192f9915cf79602d30832abc98a, coverage90112bytes SHA256e032969214cb0a1b6a93c50a9036ca903626c21b11cbbe07d53b17cbd60ce593. El log literal dice22469stmts,0miss,100%; sus líneas de progreso contienen4418dots,0F,0E,0s,0k,0x,0X. Artefactos preservados en simplecode-producer-validation/. Alcance: productor aislado antes del último assert público de JSON inválido, no suite BB ni sujetos experimentales. La nueva corrida final6430 está identificada por el agente, con COVERAGE_FILE estable y stdout persistido; no se aplicó ni distribuyó el kit todavía.


Gate final6430 archivado:22477stmts,0miss,100%; líneas de progreso4418dots,0F/E/s/k/x/X. Antes de aplicar el productor, root encontró un falso negativo de binding JSON: filaDEP11 legítima sola tiene0 findings; fila con siteajeno sola1finding; documento mezclando ambas tiene0 findings. es_meta_key_dep11_json toma cualquier fila válida del documento como excepción para otras líneas. simplecode-json-row-binding-root-negative.json conserva tres inputs/resultados exactos. No se aplicó producer ni distribuyó kit; se devolvió al agente para vincular cada línea a su propio objeto. Cobertura100% no acredita ese requisito semántico.


Recheck firmware batch02 (2026-10-04): baseline sintético PASS; cambiar argv lspci al BDF04:00.0 mientras flint consulta03:00.0 ahora UNKNOWN; helper invocado ausente UNKNOWN; helper con flash FAIL. firmware-binding-and-helper-root-recheck.json conserva resultados/hash del lector. Se señaló que el fixture de VALIDSIG sigue abreviado y que el vínculo firma→bytes exactos de Release necesita comprobación, no sólo coincidencia textual. No hubo flash ni autenticación real de ese fixture.

## Estado integrado del 2026-10-04: disponibilidad y pendientes

La auditoría de los 98 comandos originales registra 65 selectores, 29 comandos de módulos, 2 scripts y 2 archivos de tests disponibles, con 0 ausentes. Es disponibilidad estructural, no cierre de sujetos. Las 98 fichas originales mantienen 2 done y 96 open; la deuda adicional de consultas NVIDIA quedó cerrada aparte. Recibos: `original-command-availability-after-all-selectors.json` y `original-98-close-check-after-integrations.json`.

La validación integrada de hardware lotes02/03 dio 171 pruebas pasando y 100% de cobertura; runtime dio 183 pruebas unitarias pasando, 37 selectores de captura separados, y 100% de cobertura de sus seis módulos. Sus 37 comandos originales siguen UNKNOWN/CNR37, con retorno exact-once comprobado. El enrutador/proveedor pasa 93 pruebas; la cobertura de otros evaluadores hardware y del APT integral permanece parcial.

La suite general terminó con rc1: 1789 passed, 103 failed, cobertura mostrada 94%. El recibo terminal `all-controls-global-terminal.json` conserva 101 fallos de controles de cierre y 2 regresiones de código/documentación. El recheck de las dos regresiones pasó el selector de latencia del proveedor; el esquema de la ficha NVIDIA sigue fallando por evidencia sin commitear en HEAD y requiere metadatos detector (añadidos después del recheck). El objetivo sigue activo y estos cambios siguen sin commit/push.


Integración posterior de CLI hardware: ocho archivos con SHA verificado; 34 passed in 0.38s en primary. Los tres comandos originales GPU/Wi-Fi/USB devuelven JSON UNKNOWN y rc2, corrigiendo el falso éxito de stdout vacío. Cierre físico: 0 PASS, 0 FAIL, 3 UNKNOWN. El recheck del enrutador/proveedor más el selector de overflow pasó 94 tests in 0.23s. Recibos `hardware-cli-primary-integration-20261004.json` y `hardware-cli-primary-real-checks-20261004.json`.


Integración posterior de telemetría: lector JSONL acotado, sin claves duplicadas ni números no finitos (incluido overflow 1e999); estados originales conservados y placeholders pendientes. Primary: `python3 -m pytest -q tests/test_verify_telemetry_dispositions.py` → `9 passed in 0.10s`. El close_check original devuelve rc1/MISSING para los tres eventos históricos. Hash del ledger antes/después idéntico; recibo `telemetry-reader-primary-integration-20261004.json`. Esta corrección del instrumento no sustituye la evidencia histórica ausente.


Integración final APT y hostdiag: primary APT sources+selector 222 passed in 1.10s, 1279 sentencias/578 ramas,0 missing/partial,100%. El selector original permanece rc1/UNKNOWN por controles de evidencia integral ausentes. Hostdiag primary132 passed in 2.66s,578 sentencias/218 ramas,100%. Captura nativa sysfs-only parcial/CNR2:10PCI16interfaces, sin comandos ni cambios del host. Fuentes literales y baseline nativo de Targets-Remove solicitados para reforzar reproducibilidad. Recibos `apt-integral-final-primary-integration.json`, `hostdiag-primary-integration-20261004.json` y `native-sysfs-primary-summary-20261004.json`.


Reproducción independiente de semántica APT: `apt-target-native-root-replay-20261004.json` preserva fuente/config/argv/stdout de dos casos `apt-get indextargets --no-release-info` aislados, con Dir::Etc::main deshabilitado además de sourceparts/parts propios. Translations1→0, Packages conservado, rc0 en ambos. Sin update/install/adquisición. La captura Luna reproducible se preservó como `apt-target-native-luna-reproducible-20261004.json`; el nuevo test permanece en WT mientras corre la suite general b sobre primary congelado.


Revalidación final de los29 comandos de módulos originales, generados desde `original-close-check-preservation.json`: merge exact-once `returned: 29 of 29`,0timeouts;27UNKNOWN/rc2,1MISSING histórico/rc1 y1PASS operativo APT/rc0 con closure open. GPU/Wi-Fi/USB ya devuelven UNKNOWN estructurado. Cierres físicos0. Logs y veredictos literales en `direct-29-final-exact-once/`; resumen `direct-29-final-summary.json`.


Suite general b terminal:1938passed102failed404.46s,14455sentencias388miss6104ramas289partial97%; source changes0. 101fallos de controles pendientes y1gate de evidencia sin commitear enHEAD. Recibo `all-controls-global-b-terminal.json`; sourcefreeze levantado. Último test nativo APT baseline/remove integrado después de la suite y pasa separado.

Revisión de viabilidad runtime lote01:9IDs generados desde fuente, hashes de fichas comprobados,9capturas runtime ausentes; triage returned9of9. Inventario local reutilizable no sustituye trazas ni pruebas de modelo/ranks. Topología remota sin acceso en sesión no equivale a prueba de ausencia física. Mapa de requisitos/acciones en `runtime-readonly-batch01-review/`.


Mapa runtime completo:37IDs en lotes9/10/10/8, sourcehash/fichashashes y rutas de captura revalidadas porroot; triage `returned: 37 of 37`.0capturas runtime originales presentes,37UNKNOWN. El mapa describe requisitos específicos y próximos comandos sin declarar ausentes los peers físicos no observados. Archivos `runtime-readonly-all37-review/`.

Higiene posterior: gate repo-wide zero_debt reportó9 grupos/143 hallazgos detallados (salida JSONL visible sólo parcial),CNR0;8 archivos unencoded_file_io y1archivo de assertions delegadas. Este último quedó en0hallazgos/CNR0 tras nombres explícitos de helper y alias; AST normalizado idéntico al original. Selector proveedor pasa; selectorGPU sigue UNKNOWN/CNR1. Recibo `delegated-assertion-helper-rename.json`; Luna trabaja los8archivos de codificación desde fuente generada.


Corrección de alcance de observación cgroups: vista nativa require_escalated root confirmó mount cgroup2 rw, PAGE_SIZE4096, controllers con dmem, archivos raíz capacity/current leíblesvacíos (4observaciones,CNR0). Vista sandbox ro no acredita montaje host. Registro `native-cgroup-capability-root-summary-20261004.json`; no escrituras ni configuración. Controlador disponible no demuestra registro/cargo GPU NVIDIA.


Contraprueba runtime numérica:root reprodujo probe sobre primary y contó56 mutaciones individuales de integer→True aúnPASS, basadas sólo enfixtures. Se preservaron código/outputSHA yscript (`runtime-bool-primary-root-negative.json`); Luna corrige tipos B01enWT. No constituye captura física ni cierre. Recheck independiente de SSHmodos locales sobreWTactual rechazó -V,-G,-Q aúncon tokenpeer/stdout no vacío; recibo `wifi-local-ssh-mode-root-recheck.json`. Sin integración de fuentes hardware todavía.


Auditoría adicional numérica B01:4fixtures sanos PASS siguenPASS tras peak_bytes=-1,planned_mtu=0,observed_mtu=-1,rank=-1. Inputs/resultadoscompletos preservados en `runtime-numeric-range-root-negative.json`; se devolvieron al agente para rango>=0bytes/ranks y>0MTU, con criterio originalintacto. Revisión deSSH pidió conservar -n paraejecuciónremota válida porque sólo redirige stdin, conforme maninstalado; no equipararlo a -N.


Integración B01tipo/rango:65unitarios pasan,9selectores reales separados. Root reprodujo17mutaciones exactas porSHA deinputs:14booleanos→UNKNOWN/CNR1,3rangos→FAIL; además4contrapruebas propias de rango ahoraFAIL. Inputs únicos yresultadosen `runtime-b01-primary-replay/`. Metadata no consumida porpredicados noesprueba de campo medido. Sin cierre físico.

Integraciónencoding8:8paresSHA yASTnormalizadoscomprobados,79keywordsutf8;516pruebas pasan1.95s. Triageprimary returned8of8. Gatewhole-repozero_debt posterior rc0 (log `bb-zero-debt-after-encoding8.log`). Es higiene de código, no cierre de96investigaciones ni pase de suitegeneral.


Integración primera tanda hardware lectores:6pathsSHAexactos,17casos reproducidos conresultadoesperado; familyprimary108pass2fail. CSVlegítima driver,name requiereparsecolumna driver_version; fixtureSSH genérico no acredita rechazo deconexión yquedaUNKNOWN. Se devuelven ambasregresionesmásSSHflagsagrupados alagente. Logs `bb-hardware-command-reader-primary-tests.log`, `hardware-command-reader-primary-integration.json`, `hardware-17-primary-replay.json`. La tanda aún tienevalidaciónfallida; no cierre físico.
