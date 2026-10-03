# Swarm Luna: foro NVIDIA GB10 — 2026-10-02

Estado: informe de investigación cerrado con límites de cobertura explícitos. Investigación y registro de backlog autorizados por Luis; fixes propuestos pendientes de implementación y validación.

Inventario: categoría 721, 2163 hilos únicos, 73 páginas, paginación agotada. Snapshot vivo del foro: los hilos pueden cambiar después de esta descarga. Fuente: https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/dgx-spark-gb10/721

Tres ejecutores gpt-6-luna, razonamiento high; lotes generados desde items.json con triage.py split. Cada lote contiene 721 IDs. El inventario cuenta hilos listados; la lectura completa y los adjuntos tienen cobertura separada. Un ID devuelto por triage prueba presencia de veredicto, no profundidad de lectura.

La recuperación usa post_stream.stream y páginas de 20 IDs faltantes para evitar tratar los primeros posts como el hilo completo. Se preservan JSON, texto y metadatos de descarga en threads/. Los adjuntos binarios requieren revisión adicional; enlaces preservados no equivalen a contenido leído.

Resultados: 2163/2163 veredictos; 1056 irrelevantes, 558 relevantes, 548 cubiertos por propuestas existentes y 1 could_not_run. Capturados 28934 cuerpos: 28933 completos revisados y 1 parcial (367696/post38), que el propio foro entrega truncado incluso por raw/JSON; revisions responde 404. Los conteos listados y post_stream difieren porque el snapshot está vivo.

La unión exact-once devuelve `returned: 2163 of 2163`, con missing=0, unknown=0, duplicated=0 y malformed=0. Esta prueba verifica cobertura de IDs; la lectura queda documentada por hilo. El registro contiene 239 propuestas distintas, 240 registros de fuente y 26 fichas canónicas: sin ficha=0, ambiguas=0. Un ID compartido por dos lotes conserva ambas fuentes. Véanse el [índice portátil](INDEX.md), [FINAL-AUDIT.json](../../../tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/FINAL-AUDIT.json) y [registration-progress.json](../../../tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/registration-progress.json).

Adjuntos centrales revisados de forma selectiva: logs, ZIP, PDF y capturas, con hashes/cobertura en las notas de adjuntos y archivos de attachments-root. Los adjuntos secundarios, repositorios enlazados y binarios mantienen cobertura parcial explícita; el informe no acredita revisión exhaustiva de cada recurso externo. Los registros MFT propietarios carecen de decodificación del proveedor. could_not_run=1 exige conservar la limitación junto a los resultados.

Verificación documental: `python3 tools/inventario.py --check` imprime `[inventario] HALLAZGOS: 0`; `git diff --check` termina con código0. No acreditan eficacia de las intervenciones propuestas.

## Capturas crudas locales

El snapshot de hilos, adjuntos y metadatos permanece local y no forma parte de esta publicación. Al terminar la curación, se prevé trasladarlo a `.simplecode/evidence/research/SWARM-LUNA-FORUM-2026-10-02/`; hasta que ese traslado se verifique, la ruta sigue siendo un destino propuesto. El inventario curado conserva rutas, hashes y límites de revisión. Para volver a capturar, consultar la categoría 721 en el foro NVIDIA y recuperar cada `post_stream.stream`, registrando fecha, paginación, cuerpo completo y SHA-256. El endpoint listado no garantiza que el snapshot siga idéntico. Los adjuntos no revisados, repositorios enlazados y binarios siguen con cobertura parcial; no afirmamos inspección total.

## Alcance ampliado por Luis

BB debe prevenir además de capturar y recuperar. El dive incluye fixes, drivers, firmware, parches, configuración de kernel/runtime y recomendaciones preventivas. Las propuestas se registran con compatibilidad OEM/versiones, evidencia y confianza, riesgos, validación y rollback. Este trabajo autoriza investigación y fichas, no aplicación de parches o cambios del host.

## Objetivo de BB corregido

`SPEC.md` define prevenir y resolver crashes y hangs, preservar uso interactivo y recuperar la máquina. La captura y las sondas sirven para elegir intervenciones y verificar su eficacia. Una ficha o un resultado de esquema válido registra trabajo pendiente; la protección exige prueba del mecanismo bajo el fallo objetivo.

## Orden preventivo del backlog

1. Evitar admitir cargas que pueden bloquear el host: pico de carga y cold-prefill, memoria UMA y CUDA efectivamente atribuible, concurrencia, KV cache y presupuesto para escritorio/SSH. Reutilizar el trabajo `FEATURE-1358-CGROUP-*`; los límites declarados necesitan demostrar contención CUDA real.
2. Probar fixes soportados en el OEM y stack exactos: kernel/initrd/módulo firmado, firmware por componente y digest del runtime. Conservar un arranque conocido y comprobar después GPU, sesión, red y una inferencia funcional. Una versión más nueva y un HTTP 200 aislado aportan evidencia insuficiente de reparación.
3. Tratar ventilación y energía en idle/residencia/carga: GPU W representa una parte del sistema; medir SoC y pared cuando corresponda. Evaluar el control nativo CX7 antes de blacklist. Los caps CPU/GPU requieren lectura efectiva, A/B y restauración del estado anterior.
4. Recuperar sin repetir el fallo: una carga identificada, presupuesto de reinicios y ruta de gestión independiente. Conservar datos/logs; verificar rollback y canales SSH/TTY/display por separado. La imagen de instalación puede sobrescribir disco: ensayo de recuperación en medio reemplazable antes de usarla sobre datos.
5. Distinguir avería de hardware de configuración: integridad de lecturas, NVMe readonly y FieldDiag. Un PASS en otra condición conserva el incidente abierto si hashes cambian o el sistema vuelve a colgarse; RMA corresponde a evidencia OEM, sin atribuir causa a SSD/RAM sin prueba.

## Qué medir y parametrizar para decidir

Cada ensayo registra OEM/SKU, placa, firmware efectivo por componente, DGX build, kernel, driver, módulo/firma, imagen/digest y paquetes reales; modelo, backend, cuantización, contexto, lote, concurrencia, fase fría/caliente y pico observado. Registrar boot ID, reloj monotónico, última respuesta funcional, canales que sobreviven, Xid/RCU/pstore y estado previo a cualquier recuperación.

Parametrizar el presupuesto de memoria y el margen del host según pico medido; límites de contexto/concurrencia y tiempo de carga; duración y condiciones del soak; freshness/debounce de sensores; disparador y alcance de cada acción; número máximo de reintentos, cooldown, estado de rollback y expiración/vigía de suspensiones. Conservar el mecanismo nativo que cubra cada caso antes de añadir una dependencia o un daemon.

Para eficacia, contar intentos, fallos reproducidos, fallos tras intervención, pérdida de datos, latencia/disponibilidad del canal interactivo, recuperaciones y rollbacks correctos, incluidos controles negativos. Cero capturas de un instrumento durante incidentes exige investigar su cobertura; cero incidentes en una prueba exige registrar condiciones y duración, sin generalizar a todos los workloads.

## Límites de evidencia

Fix oficial con versión/alcance identificado, resultado del propietario, hipótesis comunitaria y propuesta local mantienen estados separados. Los adjuntos binarios y repositorios enlazados tienen revisión separada del texto capturado. Las recetas con purgas, escritura de firmware, Secure Boot desactivado, caps reverse-engineered o parches externos permanecen propuestas hasta validación y rollback. Esta investigación tuvo cero aplicaciones de esas recetas sobre el host.

## Intervención local ya existente

Luis informó que instaló un extractor de aire casero y observó mejor rendimiento. Queda registrado como `BB-LOCAL-EXTRACTOR-VALIDATION-01` en la ficha térmica. La mejora es cualitativa: magnitud y reducción de crashes/hangs pendientes de medir. Usar el montaje actual como referencia operativa; documentar flujo, OEM, ambiente y workload, y comparar rendimiento y estabilidad con condiciones equivalentes. BB debe incorporar el margen térmico efectivo junto al presupuesto de UMA y la salud del runtime.
