# Revisión de factibilidad de instrumentos — 2026-10-03

Este documento registra la factibilidad de las tandas indicadas, separando la capacidad de desarrollo del cierre experimental. Los `close_check` y estados de backlog se conservan. `needs_capture` indica datos de sujeto que el repositorio todavía no observa; `needs_contract` indica que no hay un contrato común suficientemente preciso; `needs_decision` indica una decisión de host pendiente; `deferred_lab` preserva la decisión vigente de desarrollar primero y posterga ensayos hasta habilitar laboratorio. Las capturas raw tienen procedencia declarada, no autenticada por hashes.

## Tanda 01

Fuente generada: `tasks/evidence/BB-INSTRUMENTS-2026-10-03/feasibility-01.json` (5 IDs); dictamen: `/tmp/bb-inst-feasibility-01-verdict.json`.

El código de cgroup ya contiene `tools/verify_cgroup_repro.py`, que recalcula fases, identidad, deltas y calibración CPU desde filas crudas de la fase 01. El instrumento declara explícitamente que no demuestra contención GPU ni autenticidad de origen. La deuda `VERIFY-CGROUP-PLAN` apunta a fases 02–05; sus fichas describen pruebas distintas y dependientes. La evidencia actual de 02 es mapa/probe ABI preparatorio, 03 es inspección/build sin runtime, 04 es readiness condicionado y 05 es protocolo más controles del host. Falta la traza real de 02, el stack runtime y límites de 03, el hueco/diff condicionado de 04 y la comparación expuesta de 05. No se derivó un schema de captura inexistente.

`VERIFY-FORUM-FINDING` agrega 15 asuntos heterogéneos. El test de deuda y los close checks nombran validaciones específicas, pero no hay esquema compartido de origen/evidencia/controles para 15 clases. Para implementarlo hace falta un contrato con adapters por ID, pruebas positivas y negativas recalculables y `fail`/`unknown`/`could_not_run` explícitos; la mera presencia de informe no basta.

La ficha de clock-cap tiene telemetría instalada y progreso local que confirma declaración 300,2800 y cero pruebas A/B. El siguiente dato es un par base/cap y rollback observado en un OEM/driver/stack identificado, con workload, clocks aplicados, throughput y ventana; no se alteraron clocks. La ficha memory-saver contiene definición y ABI del probe de fase 02, además de comparación de diseño 4K; no contiene traza runtime del cargo/memcg ni medición de backing de páginas 4K bajo el workload. No se ejecutó probe con root ni carga GPU.

La captura Wi-Fi actual reconoce interface Wi-Fi `DOWN` y Ethernet `UP`, pero la secuencia citada `WRONG_KEY` → `no-secrets` y probe local sano/remoto inaccesible no está capturada. El cierre exige A/B de roam y política reversible, que puede tocar NetworkManager o servicios. El laboratorio queda diferido por la decisión vigente de desarrollar primero los instrumentos; el host permaneció sin cambios.

Comandos de inspección literal: `rg -n "verify_cgroup_plan|verify_forum_finding|verify_gpu_clock_cap_ab|verify_memory_saver|verify_wifi_isolation|clock.cap|nvidia-smi -lgc" tools tests docs/evidence tasks/evidence/FEATURE-1358-CGROUP-01-REPRO tasks/backlog/FEATURE-1358-CGROUP-0*.md tasks/backlog/FEATURE-FORUM-GPU-CLOCK-CAP-AB-01.md tasks/backlog/FEATURE-MEMORYSAVER-*.md tasks/backlog/FEATURE-FORUM-WIFI-ISOLATION-01.md` → solo existía `verify_cgroup_repro.py` para la reproducción fase 01 y la declaración de pruebas de host. `find tasks/evidence -maxdepth 3 -path '*WIFI-ISOLATION*' -o -path '*GPU-CLOCK-CAP-AB*' -o -path '*MEMORYSAVER*'` → evidencia actual de observación Wi-Fi y fases de memory-saver, sin capturas A/B para estos cierres.

No se añadieron herramientas ni pruebas vacías: para los seis criterios citados, código que afirme aceptación a partir de logs no capturados o valores caller-supplied sería una medición ficticia. El detalle por ID y la siguiente entrada concreta está en el veredicto de la tanda.

## Tanda 02

Fuente generada: `tasks/evidence/BB-INSTRUMENTS-2026-10-03/feasibility-02.json` (5 IDs); dictamen: `/tmp/bb-inst-feasibility-02-verdict.json`.

`tools.nvme_readonly` ya evalúa snapshots capturados de forma observable: exige ruta/serial, correlaciona la señal de medio con el mismo registro, discrimina raíz `ro`, consulta inválida/ilegible y estado sin errores (sin llamarlo salud física). La copia exige destino en otro filesystem, regularidad/estabilidad/hash y evita sobrescritura. Comando literal `python3 -m pytest tests/test_nvme_readonly.py -q` → `20 passed in 0.17s`. Esto ejecuta datos temporales de control, no un medio NVMe sospechoso ni una recuperación de laboratorio.

`tools.workload_restart_policy` implementa un ledger de intentos persistido por identidad de workload; usa lock interproceso, replace+fsync y trata errores de estado o reloj regresado como `could_not_run`. Comando `python3 -m pytest tests/test_workload_restart_containment.py -q` → `10 passed in 0.30s`. Es una primitiva de admisión y no conecta ni detiene/reinicia Docker. La integración runtime/target y el canario con recovery/reboot quedan diferidos hasta habilitar el laboratorio; no se llamó a Docker para cambiar estado.

`tools.verify_telemetry_dispositions` está conectado al ledger y sus tests distinguen faltantes, rows malformados, disposición pendiente, evidencia vacía y ledger inaccesible. Comando `python3 -m pytest tests/test_verify_telemetry_dispositions.py -q` → `3 passed in 0.05s`. La evidencia raw recuperada de los tres eventos contiene comandos, rc e identidades, sin stdout/stderr: los dos pre-commit no tienen resultado por hook; repetir `bash -n` contra el blob conocido pasa y no restituye el staged source histórico. No hay dictamen defendible hasta recuperar outputs originales o una reproducción que determine cada defecto.

`tools.thermal_coverage` enumera sensores y errores sin emitir juicio de seguridad. `tools.recipe_memory` conserva la captura, etiqueta los parámetros caller-provided como no verificados y devuelve unknown con valores faltantes; no convierte un presupuesto declarativo en admisión funcional. Comando `python3 -m pytest tests/test_diagnostic_admission_prototypes.py -k 'recipe_memory or thermal_coverage' -q` → `10 passed, 6 deselected in 0.03s`. Los captures de estas fichas son readonly del host actual; no sustituyen el stack ASUS/UEFI/soak térmico, ni las medidas completas y canario funcional de la receta. La entrada exacta que falta por ID está detallada en el JSON de dictamen.

Se reutilizan estos cinco instrumentos/tests existentes; no se añadieron tests espejo ni schemas nuevos. Sus salidas positivas ejercitan lógica del instrumento, no cierran el trabajo experimental.

## Tanda 09

Fuente generada: `tasks/evidence/BB-INSTRUMENTS-2026-10-03/feasibility-09.json` (5 IDs); dictamen: `/tmp/bb-inst-feasibility-09-verdict.json`.

La ficha `FEATURE-1358-CGROUP-01-REPRO` ya implementó lector/verificador de seis APIs basado en stdout JSONL y controles de CPU/no asignación; revalida consistencia, no autentica origen ni demuestra contención GPU. Se corrió el close_check exacto como análisis del JSON existente, sin ejecutar GPU: `python3 -m tools.verify_cgroup_repro tasks/evidence/FEATURE-1358-CGROUP-01-REPRO/run-profile-integration.json`. Salida literal (campos del JSON): `"status": "unknown"`, `"could_not_run_count": 23`, scope `"observation consistency and CPU calibration; no native GPU containment or provenance proof"`; `command_rc=2`. Deltas recalculados: CPU `33554432`, cudaMalloc `0`/repeat `0`, managed `33816576`, pytorch_empty `0` bytes. Las 23 lecturas inaccesibles son `dmem.current` ausentes de las muestras por fase. Por tanto se reutiliza el verificador tal como está y el resultado no satisface el close check.

Las fichas 02–05 no tienen el runtime que el verificador plan necesitaría. 02 exige una traza de asignación/owner/memcg/flags, no el mapa estático de símbolos. 03 tiene build 615 contra headers, con módulos no instalados/cargados y sin GSP/userspace validado; requiere canario compatible de dos cgroups. 04 está condicionado a un hueco probado por 02/03, por lo que no procede redactar un parser de patch genérico antes de conocer el sujeto. 05 documenta host controls pero registra cero ensayos A/B y cero segundos de exposición; requiere el workload/ventana exacta con raw results de ambos brazos. Se detallan entradas por ficha en el JSON de dictamen.

## Tanda 10

Fuente generada: `tasks/evidence/BB-INSTRUMENTS-2026-10-03/feasibility-10.json` (5 IDs); dictamen: `/tmp/bb-inst-feasibility-10-verdict.json`.

Clock-cap: ya hay telemetry de clocks, potencia, temperaturas y throttling, pero la evidencia local conserva la política declarada `300,2800`, `0` pruebas A/B y `0` cambios. Faltan OEM/driver exactos, brazos baseline/cap bajo misma carga, readback aplicado y rollback efectivo; no se modificó ni ejercitó GPU. Fijar parser después de tener filas crudas reales.

Provider fallback: `tools.provider_trace.py` consume JSONL request-scoped y preserva worker/PID/latency por transiciones, con controles de GPU sana, CPU intencional, respawn a CPU y datos incompletos. Comando literal `python3 -m pytest tests/test_provider_trace.py -q` → `12 passed in 0.04s`. La captura del host en `validator-run.json` es `unknown` por falta de requests, provider solicitado/observado, respawn y evidence ID; los JSONL de control son sintéticos. Falta una traza cruda del workload exacto y controles/soporte/rollback, no más parser fixture.

Wi-Fi: la observación actual distingue WLAN down de Ethernet up, pero no contiene logs de asociación `WRONG_KEY`/`no-secrets` ni time-series común de host local y SSH remoto. Como la validación además requiere roam/recovery A/B y rollback en el stack GX10 headless, los ensayos de intervención quedan diferidos hasta habilitar el laboratorio según la decisión vigente de desarrollar primero los instrumentos. No se tocó configuración ni se reinició servicio.

MemorySaver fase 02: `kernel_charges.bt`, revisión de firmas ABI y probe-list son fuente y lista estática; la captura de probes, parser en ejecución y memcg owner exigen privilegios y workload real, así que faltan trace cruda/control CPU/no-GPU y asignación CUDA. Fase 04: la comparación de diseño y datos de perfil/integridad no miden backing real de page tables UVM, tabla hoja elegible ni contabilidad/teardown. Hacen falta medidas de bytes, alineación HAL/build, sharing y cargo/descargo bajo workload exacto; solo una diferencia medida autoriza considerar un patch.

No se añadieron herramientas o pruebas a esta tanda: cada rama carece de datos de sujeto, y crear un parser antes de capturas fijadas inventaría el contrato. La evidencia por ID marca el next input concreto.
