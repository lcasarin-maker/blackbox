# Swarm Luna: lotes de diez, 2026-10-03

La fuente se generó de tasks/backlog: 98 IDs únicos, nueve lotes de diez y uno de ocho. Tres agentes gpt-6-luna ejecutaron en worktrees aislados; la raíz revisó las propuestas. El escáner inicial registra TOTAL PENDIENTE 98, fuentes adicionales cero y ninguna fuente inaccesible. Fuente, lotes, salidas y contratos: tasks/evidence/SWARM-TENS-2026-10-03/.

## Alcance de cierre

Ninguna ficha experimental se cierra por un fixture. Los contratos y close_check permanecen intactos. El inventario estático del checkout principal encuentra 91 controles ausentes (selector de prueba, archivo de prueba o módulo), y siete comandos existentes. La primera cuenta confundió -q final con una ruta en dos comandos y se corrigió; el JSON final inspecciona los targets de pytest independientemente de sus flags.

Los comandos APT, NVMe y Docker pasan sobre capturas/fixtures actuales, pero las fichas requieren además guard integrado, ensayo nativo de copia/restauración o integración y recuperación. La reproducción cgroup conserva unknown y could_not_run_count 23. El drift reporta 41 revisados, dos divergencias, cero ausentes y uno suspendido. La comprobación raíz del guardián detecta que el archivo actual se modificó después del arranque del servicio; se preserva la decisión previa de desarrollar antes de intervenciones. Los tres eventos históricos siguen MISSING en el ledger principal. Los could_not_run del worktree por IPC o ledger ignorado ausente son distintos de esas comprobaciones nativas; ninguna ausencia del kit aislado se atribuye al host.

## Desarrollo integrado

- tools/netconsole_marker.py: lector offline de captura suministrada por operador. Literal presente, parcial al final, ausente o unknown; hashes exactos y procedencia sin autenticar; lectura máxima 1 MiB y marcador 1..1024 caracteres. El nombre separa su alcance del verificador completo ausente. El cierre sigue open; entrega, Secure Boot, persistencia y correlación necesitan evidencia. Ocho controles de límite, UTF-8, CLI, recibo y clasificación pasan.
- tools/openclaw_contract.py: contrasta max_tokens de la petición con maxTokens configurado, además del headroom. El control negativo del código anterior devolvía observed para 9000 tokens solicitados con cap configurado 8192; la corrección devuelve mismatch. No modifica ni ejecuta la petición. Fuente oficial consultada: https://docs.openclaw.ai/gateway/config-tools/custom-providers (precedencia del catálogo y cap de salida por proveedor/modelo); esto compara declaraciones, sin probar que el servidor imponga ese límite.

Los límites funcionales, entradas necesarias y revisiones de cada ficha están en los veredictos. No se ejecutaron workloads CUDA/LLM, hotplug, firmware, panic, reinicios ni modificaciones del host.

- tools/chat_sse_capture.py: recompone contenido visible por choice y conserva hash, longitud, finish_reason y distinción refusal/tool_calls/length/content_filter. Evalúa sólo sintaxis JSON con stop y terminación SSE; datos posteriores a finish, índices inválidos, surrogates y profundidad excesiva quedan inaccesibles o incompletos. `--json-summary-only` omite chunks y contenido, imprime conteos incluso cero y distingue válida (rc0), inválida (rc1) e incompleta/inaccesible/no evaluable (rc2). No valida esquema, respuesta correcta ni seguridad del modelo.
- tools/hitos_incidente.py: reconoce la marca por presión de memoria con campos journal _COMM/_SYSTEMD_UNIT concordantes; SYSLOG_IDENTIFIER aislado y formatos/timestamps desconocidos conservan could_not_run. Distingue kill_reported (systemd v255) de marked_for_killing (fuente main consultada). `systemctl --version` devuelve `systemd 255 (255.4-1ubuntu8.17)`. Fuentes primarias: [v255](https://github.com/systemd/systemd/blob/v255/src/oom/oomd-manager.c#L488) y [main](https://github.com/systemd/systemd/blob/main/src/oom/oomd-manager.c#L3198). Es clasificación de texto suministrado, no autenticación del journal ni prueba de terminación o causalidad.

`python3 -m pytest -q tests/test_1358_hitos_nvrm.py tests/test_chat_sse_capture.py tests/test_openclaw_contract.py tests/test_netconsole_marker.py` devuelve `76 passed in 0.57s`. El merge de veredictos devuelve literalmente `returned: 98 of 98`. Contratos comprobados: 98; contratos cambiados: 0; estados cambiados: 0; cierres experimentales: 0; agentes que declararon CERRADA: 0; cierres rechazados por raíz: 0.

La revisión raíz separó el lector parcial de netconsole del módulo verify_netconsole aún ausente, amplió pruebas de límites/CLI y ajustó OOMD al formato real de systemd 255. Las propuestas originales de agentes y los resultados de comandos en sus worktrees permanecen en los veredictos; no sustituyen la revisión del checkout principal.

## Validación final y límites

`python3 .simplecode/run.py simplecode.verification.coverage_target -q` devuelve `1118 passed in 107.41s` y cobertura Python 100.00%. La medición abarca los 35 módulos Python trackeados en tools, con las exclusiones previas intactas; no representa cobertura Bash ni pruebas nativas de las 98 investigaciones. La fase serial no tiene pruebas marcadas mutates_real_source (1118 deselected); pytest-benchmark se deshabilita por xdist y emite avisos, por tanto no se midió rendimiento.

Se corrigieron dos hallazgos de integración: Pyright rechazó None en una fixture con parámetro str; el esquema rechazó el informe de lote05 ubicado como Markdown bajo tasks/evidence. El informe vive ahora en docs/evidence. La primera suite global registró un fallo de esquema; la segunda pasó 1116 casos con cobertura 99.84% dentro de tolerancia, y los controles adicionales/finales llevan la medición a 100.00% sin bajar watermark ni añadir exclusiones. Ruff pasa; Pyright final tiene 0 errores, 0 warnings y 0 informations.

Ledger-schema: checked 283, passed 283, failed 0, unverified 0, avisos 0, could_not_run 0. H1: not-clean reasons 0. Zero-debt de código: PASSED 91, CONVICTED 0, COULD_NOT_RUN 0, 24 detectores, 0 exclusiones por volumen y 0 violaciones. Judge-Zero: HALLAZGOS 0 en los controles que corrieron, pero threat sweep leyó 0 archivos y sigue omitiendo tools: ese instrumento conserva su defecto abierto y no acredita seguridad del repo.

Swarm: 98/98 veredictos, 0 fichas cerradas por Luna, 0 cierres reclamados y rechazados por raíz. El escáner final se conserva junto al inicial. Las 91 rutas de verificación ausentes impiden ejecutar esos criterios; los siete controles existentes tampoco completan la evidencia experimental pendiente. La publicación sigue bloqueada por las fichas y gates de release registrados en el informe del kit 9.3.1.

Los tres ejecutores están terminados. Sus borradores originales, artefactos ignorados e historial se archivaron con SHA256 y modos verificados bajo .git/bb-instrument-archives/SWARM-TENS-2026-10-03/manifest.json; las versiones integradas incorporan la revisión raíz.

Backlog-verifier final: frauds 0, could_not_run 0, contract_breaches 0 y unverified 0. Declara 178 veredictos cacheados, el más antiguo de 24.3 días; esa parte del resultado conserva su antigüedad y no se presenta como captura fresca. Cobertura literal: 5060/5060 sentencias, 0 líneas faltantes y 16 exclusiones previas. Queda un único worktree principal; los tres temporales fueron retirados después de verificar el archivo recuperable de todos sus contenidos.
