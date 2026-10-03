---
id: FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION
kind: task
domain: THERMAL
title: "Validar contención térmica para residencia de modelos y calor CPU o idle"
status: open
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-02
close_check: {"cmd": "python3 -m tools.verify_forum_finding --id FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION --evidence tasks/evidence/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION", "expect": "exit_zero", "porque": "Verificador propuesto pendiente: requiere evidencia del caso positivo, controles negativos, compatibilidad OEM y recuperación/rollback; la ficha registra trabajo abierto."}
---

## Fuente y evidencia

[348760](https://forums.developer.nvidia.com/t/348760), [349668](https://forums.developer.nvidia.com/t/349668). 348760 reúne reportes OEM heterogéneos y un A/B de un autor: detener tres modelos residentes inactivos reduce temperatura y aumenta throughput. 349668 aclara GPU rail power frente a SoC/sistema. Las cifras del foro son mediciones del autor, con adjuntos sin revisar; mecanismo y generalización pendientes.

[365302](https://forums.developer.nvidia.com/t/dual-spark-ducted-cooling-cage/365302) aporta imágenes inspeccionadas de prototipos con intake/cage distintos y una captura GX10 del post 342: GPU 96% ocupada, 70°C, 89.98 W, 5% CPU y 6 GB unificada usados. La captura confirma estado de carga, pero no el antes/después de la mejora de 18°C anunciada ni una comparación A/B del ducto; los datos gráficos no identifican un baseline pareado. Las imágenes de 365302/159 muestran otro OEM y workload (MSI EdgeXpert, 96% GPU, 73°C, 53W); la tabla de 365302/217 no conserva leyendas completas. Usar estas fuentes como evidencia para exigir OEM, intake, posición de ventilador, potencia, workload y baseline pareados en un ensayo; no adoptar una cifra térmica universal ni copiar un diseño que pueda cubrir respiraderos. Copias revisadas de las imágenes están en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/attachments-root/`.

## Delta y prevención/resolución

atom_gpu_telemetry.py lee zonas cada5s, corroboración exige carga GPU≥60W y mitigación se limita a tres jobs propios. La cobertura para calor CPU/idle y modelos residentes requiere prueba; esta auditoría del código deja pendiente demostrar un miss en incidente real.

Reutilizar muestras existentes para distinguir GPU/CPU/SoC, headroom por zona, residencia y concurrencia. Evaluar admisión y acciones sobre workloads con ownership explícito; conservar debounce/controles antispikes. Probar una rama corroborada CPU/idle y conectar fan/CX7; parar procesos por nombre o matar servicios compartidos carece de objetivo verificable.

El hilo [373482](https://forums.developer.nvidia.com/t/deliberations-on-4-sparks-cluster-advantages/373482) añade relatos de apagado térmico al apilar dos nodos bajo carga (post 31), fallo de alimentación CX7 en primer arranque tras actualizar firmware que el autor recuperó drenando alimentación (post 32), y hasta 60 °C en escape durante carga TP4 (post 36). Son observaciones de usuarios sin modelo OEM/firmware completo ni control o reproducción; usarlas para incluir arranque frío/caliente, estado CX7 y zonas de escape en el soak. El post 37 solo enlaza una propuesta de underclock; no valida seguridad ni pérdida de rendimiento y no justifica aplicar un límite de reloj.

## Validación, riesgo y cierre

calor CPU sostenido, fan detenido en idle, spike ACPI aislado, GPU caliente real y sensores ilegibles. A/B por OEM/firmware/modelos con presupuesto y soak declarados, medir throughput local antes de afirmar mejora; control sin modelos residentes y rollback de políticas. Dar una acción preventiva verificada o declarar limitación, jamás convertir permiso/sensor faltante en sano.

El verificador de close_check todavía debe implementarse; ejecutar esta ficha exige evidencia adicional y deja registradas las consultas que no pueden correr. Ningún cambio del host se aplica al registrar la propuesta. Detalle fuente preservado en tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_*.json y threads/.

## Índice de propuestas registradas del swarm NVIDIA categoría 721

- **`BB-GX10-IDLE-POWER-FIRMWARE`** — Ascent GX10 high idle power is ~40W in the thread; two owners report ~24–25W wall/socket after OS and additional firmware update, with physical ConnectX-7 cable removal also required in one report. Fuente: [348562](15).
- **`BB-GX10-POSTCRASH-POWER-RESIDENCY`** — An ASUS Ascent GX10 owner reports GB10 power remaining around 5–9W with low performance after workload crash/OOM or occasionally boot, until shutdown and power-brick removal. NVIDIA says its FieldDiag bundles show no issue and… Fuente: [366590](https://forums.developer.nvidia.com/t/366590/1).

**DELTA-FORUM-DUALSPARK-POWER-RESET-RECOVERY-01.** En el hilo de dos GB10 [361639, post 293](https://forums.developer.nvidia.com/t/361639/293), un usuario de Qwen3.5-122B-FP8 reportó que, después de apagar y desconectar alimentación USB-C, recuperó SCP sobre ConnectX a >700 MB/s, respuesta general del sistema y benchmark llama-benchy (p. ej. tg32 ~32.5 tok/s en esa configuración). No publicó A/B repetido ni aisló el estado del suministro, CX7, clocks, cableado o workload; cuenta como recuperación reportada, no como causa/fix universal. Añadir la secuencia a la investigación existente de baja potencia/rendimiento: guardar muestras y logs fuera del host, comparar clocks/potencia/rendimiento y enlace CX7 antes/después, y ejecutar shutdown limpio según OEM antes de retirar/reconectar alimentación en un nodo canary. No ejecutar ciclo automático ni recomendarlo como intervención general; preservar datos y rollback de cualquier cambio de cable/configuración.
- **`BB-GX10-HIGHCONTEXT-NO-POST-POWERON`** — An ASUS GX10 owner reports a high-context workload freeze near 120K tokens followed by power-on ending after about two seconds without BIOS; overnight power drain and a second Spark adapter did not restore boot. The proposed internal… Fuente: [383964](https://forums.developer.nvidia.com/t/383964/4).
- **`BB-GB10-OEM-SHUTDOWN-AND-IDLE-THERMAL-CONTROLS`** — Across user reports in a mixed Spark/Gigabyte AI Top Atom discussion: one shutdown attributed to thermal behavior reportedly stopped after BIOS update (versions not stated); a separate owner of two Atoms and two Sparks says both OEMs… Fuente: [372608](https://forums.developer.nvidia.com/t/372608/5).
- **`BB-GB10-THERMAL-SILENT-LOCK-RMA-VALIDATION`** — One A.7 Spark reports repeatable hard power loss under GPU load without pstore, vmcore, OOM, Xid or thermal-trip logs; idle GPU reported at 47–48C and last sample at 79C/82W. In a separate two-FE case, 12 silent locks during 262K… Fuente: [373251](https://forums.developer.nvidia.com/t/373251/1).
- **`BB-FE-THERMAL-FIELDDIAG-POWER-CUTOFF-COVERAGE`** — An MSI GX10 owner reports hard power cutoff around GPU burn temperature 80C and attached no-boot thermal FieldDiag code 020000021139; FE Spark owners elsewhere report similar silent cutoff even while generic FieldDiag passes. Another… Fuente: [358034](https://forums.developer.nvidia.com/t/358034/1).


## Índice de hallazgos asociados

- **`BB-POWER-TELEMETRY-BOUNDARY`** — NVIDIA clarifies that nvidia-smi reports GPU power only; GB10 SoC CPU+GPU is rated 140 W TDP while the full system can reach 240 W. Separate user reports associate very low GPU power/temperature and slow inference with one-minute AC… Fuente: [349668](https://forums.developer.nvidia.com/t/dgx-spark-power-clarification/349668/1).


## Índice de propuestas del lote 00

- `FORUM-00-MIXED-CPU-GPU-QUALITY-ADMISSION` — [Detect quality regressions when CPU OCR and GPU inference share GB10 UMA](); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-POWER-STATE-UNKNOWN-LOAD-VS-DEGRADED` — [Classify low GPU power by workload and power-state evidence before treating it as a fault](); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-THERMAL-POWERSTRESS-DIAG-COVERAGE` — [Keep thermal and power-loss incidents open when the installed diagnostic stack cannot run](https://forums.developer.nvidia.com/t/376103); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-DUAL-NODE-THERMAL-CONTROLS` — [Measure CPU/SoC and cooling headroom under CX7 plus inference before choosing clock or airflow changes](https://forums.developer.nvidia.com/t/381192); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.
- `FORUM-00-VLLM-CPU-THERMAL-ADMISSION` — [Measure CPU-bound vLLM inference heat and verify container affinity before capping CPU frequency](https://forums.developer.nvidia.com/t/383939); detalle, confidence y close check en `tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_00.json`.


[373199](https://forums.developer.nvidia.com/t/373199) describes user cooling experiments on ASUS GX10: a USB base fan reports roughly 6–8°C lower GPU temperature in one setup; a separate extraction-fan plus 2GHz GPU clock cap reports <1% performance loss and about 10°C lower peaks, explicitly without hard data; another dual-GX10 cardboard/fan prototype claims a 20–25°C drop. The posts mix orientation, fan placement, clocks, ambient conditions and workload, and omit complete firmware/ambient/test controls. The linked STL/ZIP and key images were not inspected. Treat as a low-confidence candidate for an OEM-specific A/B thermal-soak test; do not apply a clock cap or external fan as a universal fix. Measure inlet/zone/GPU/CPU temperature, clocks, wall power, fan behavior and useful throughput against matched controls; test OEM limits, dust, noise, PSU cooling and reversible rollback. **DELTA-FORUM-THERMAL-AUXILIARY-COOLING-AND-CLOCK-CAP-01**.


[372662](https://forums.developer.nvidia.com/t/372662) adds workload-specific clock-cap evidence: owner-reported LLM decode tests often show near-no throughput change at ~2GHz, while one image-generation test loses ~12.5%; another TP2/diffusion comparison reports 0–7.5% changes. A controlled, cooled cuBLAS sweep in post 36 reports −4.5% SGEMM throughput at 2GHz and −9% at 1.8GHz without thermal throttling, while an L2-fitting control tracks clocks more directly. In post 45 one owner’s hottest ACPI zone reads 7–17°C above `nvidia-smi` GPU-die temperature. This supports a two-part local study—sample all effective temperature zones with freshness/type/OEM metadata, and compare matched decode, prefill, image-generation, model-load and concurrent workloads at stock versus a user-selected cap. It does not validate the post 43/45 community governor (only three days reported), its thresholds, or a universal 2GHz/80°C policy; its scripts, sudoers/service suggestions and linked source remain unaudited. Roll back to verified original clock policy, confirm applied clocks and workload throughput, and stop the test if OEM thermal/power diagnostics fail. **DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01**.

## DELTA-ROOT-SUBAMBIENT-COOLING-AND-UMA-CANARY-01 — refrigeración subambiente y presión UMA

Fuente: https://forums.developer.nvidia.com/t/375158. Revisados los 7 cuerpos y las 5 imágenes. El montaje usa ducto de cartón/cinta desde aire acondicionado a dos unidades apiladas. La captura AI TOP ATOM muestra CPU 74 °C, GPU 65 °C y RAM 95.8%; falta baseline comparable y duración. El relato de menor temperatura sigue siendo una afirmación del autor.

Acción propuesta: evaluar ambiente, humedad/punto de rocío, flujo y CPU/SoC/GPU junto con admisión UMA y salud de escritorio/SSH antes de aceptar una intervención subambiente. Riesgos: condensación, obstrucción y presión de memoria pese a GPU fría. Cierre: canario prolongado del workload y stack exactos, raw logs y comparación controlada; restaurar montaje y parámetros previos si falla. La revisión visual registra evidencia, no valida el montaje ni su eficacia.

### Adjuntos revisados — 373199

Fuente: https://forums.developer.nvidia.com/t/373199. Revisadas 26 imágenes y 3 ZIP; inspección estructural de CAD, sin simulación ni prueba física. Fotos/renders muestran extractor, filtro y prototipos intake específicos de GX10. Captura19: GPU 60 °C, 28 W, 1976 MHz, 95% en ventana15:01:11–15:03:03; no incluye baseline ni medida de rendimiento para sostener el <1% declarado. Foto31: dosGX10 verticales, ventiladores laterales y cartón; carece de termometría comparativa. El autor del CAD declara diseño pendiente de impresión/validación y ausencia de GX10 propio. Gate A/B debe separar orientación, fan, filtro, clockcap y workload; conservar montaje previo como rollback. El archivo CAD y un instante de telemetría no acreditan eficacia ni compatibilidad física.

## BB-LOCAL-EXTRACTOR-VALIDATION-01 — extractor instalado por Luis

Luis reportó el 2026-10-02 que instaló una solución casera con extractor de aire y observó una mejora de rendimiento. Montaje físico existente; magnitud y reducción de crashes/hangs pendientes de medición. Incorporar esta intervención local al diseño preventivo y de remediación de BB.

Validación: documentar OEM/equipo, montaje, orientación, alimentación y ambiente; conservar el montaje actual como referencia operativa. Comparar modelo, stack, contexto, concurrencia y duración equivalentes con throughput útil, latencia, temperaturas GPU/CPU/SoC, clocks, potencia y throttling, junto a UMA/swap/PSI, progreso del servicio y respuesta SSH/escritorio. Separar el efecto del extractor de cambios de clocks/software. Si falta una condición previa comparable, registrar la mejora cualitativa y medir estabilidad del montaje actual.

Cierre: prueba reproducible bajo carga sostenida con criterios de rendimiento y estabilidad; parametrizar margen térmico por OEM/workload a partir de evidencia. Riesgos: flujo obstruido o recirculación, polvo, vibraciones, alimentación y temperatura de la fuente. Rollback: conservar descripción del montaje original y restaurar parámetros verificados ante degradación. Este registro autoriza investigación; cualquier prueba disruptiva o modificación física requiere alcance específico.

## Estado de publicación de esta investigación

Propuesta abierta. Los comandos de cierre describen el verificador y evidencia requeridos; esta rama publica investigación y fichas, sin implementación ni resultados de ejecución de los mecanismos propuestos.

### DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01 — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "DELTA-FORUM-THERMAL-TELEMETRY-COVERAGE-01",
    "title": "Expose thermal and platform sensor blind spots by OEM",
    "source_threads": [
      "377044",
      "371614"
    ],
    "failure": "ASUS GX10 user reports sustained inference with ACPI zones 0/5 at 96.6C, GPU thermal slowdown active and fan telemetry N/A; later posts contain distinct hard cutoffs, including one at reported 79C with power loss and OOM lines preceding some outages. Retail Spark audit reports DCGM energy fields cover GPU but no CPU/SoC/powercap energy; community sensor module is blocked by Secure Boot on retail. NVIDIA says FE did not reproduce the OEM case.",
    "current_coverage": "Thermal readiness tracks GPU temp/throttle and platform thermal signals; fan RPM/PWM and CPU/SoC energy channels may be unavailable and coverage differs by OEM/firmware.",
    "gap_or_complement": "Report per-source sensor capability, staleness and absent fan/rail coverage; capture synchronized GPU/ACPI/clock/counter/workload/journal/firmware versions. Keep thermal throttling, OOM, and abrupt power loss as distinct event classes; do not claim fan curve or firmware root cause from correlation. Use only stable signed OEM firmware unless vendor gives test channel procedure and rollback.",
    "evidence_level": "High for user-reported synchronized ASUS thermal telemetry; medium for cross-firmware relationship; low for causal fan/thermal diagnosis because attached archives were not inspected and NVIDIA could not reproduce on FE.",
    "risks": [
      "No Linux fan PWM/RPM makes fan attribution inferential.",
      "Cross-OEM capsule testing or downgrade can brick or void warranty.",
      "Missing CPU energy data must not be presented as total system energy."
    ],
    "closure": "On exact OEM SKU, run controlled inference soak with synchronized sensor coverage/clock/throttle/journal receipt, prove gaps are visible, compare stable vendor firmware only under approved A/B and rollback, test power-loss and OOM classifiers separately, and retain independent power-cut evidence.",
    "backlog_card": "tasks/backlog/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION.md",
    "merge_into": "FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION"
  }
]
```

### BB-FIELDDIAG-REAL-WORKLOAD-COVERAGE-GAP — propuesta del dive

Fuente y criterios conservados del registro de investigación:

```json
[
  {
    "id": "BB-FIELDDIAG-REAL-WORKLOAD-COVERAGE-GAP",
    "source_threads": [
      "354205",
      "362585"
    ],
    "source_posts": [
      "https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205/1",
      "https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205/11",
      "https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205/23",
      "https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205/29",
      "https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205/32",
      "https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205/43",
      "https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205/45",
      "https://forums.developer.nvidia.com/t/random-reboots-and-00-screen/354205/47",
      "https://forums.developer.nvidia.com/t/msi-edgexpert-suddenly-power-off-during-llama-benchy-possible-pd-firmware-issue/362585/1",
      "https://forums.developer.nvidia.com/t/msi-edgexpert-suddenly-power-off-during-llama-benchy-possible-pd-firmware-issue/362585/5",
      "https://forums.developer.nvidia.com/t/msi-edgexpert-suddenly-power-off-during-llama-benchy-possible-pd-firmware-issue/362585/8",
      "https://forums.developer.nvidia.com/t/msi-edgexpert-suddenly-power-off-during-llama-benchy-possible-pd-firmware-issue/362585/9",
      "https://forums.developer.nvidia.com/t/msi-edgexpert-suddenly-power-off-during-llama-benchy-possible-pd-firmware-issue/362585/14",
      "https://forums.developer.nvidia.com/t/msi-edgexpert-suddenly-power-off-during-llama-benchy-possible-pd-firmware-issue/362585/15",
      "https://forums.developer.nvidia.com/t/msi-edgexpert-suddenly-power-off-during-llama-benchy-possible-pd-firmware-issue/362585/23",
      "https://forums.developer.nvidia.com/t/msi-edgexpert-suddenly-power-off-during-llama-benchy-possible-pd-firmware-issue/362585/25"
    ],
    "failure": "Dos hilos reportan fallos de disponibilidad durante tareas reales pese a Field Diagnostics PASS. En DGX Spark FE P4242/BIOS 5.36_0ACUM018/kernel 6.17.0-1014-nvidia, reboots continuaron en idle/browser y un lector independiente pegó firmas pstore FPAC/PSCI/NMI y SBSA watchdog, además de DOE/PCIe x0; vendor pidió RMA sin resultado en hilo. En cluster con MSI EdgeXpert y DGX Spark FE, vLLM/Ray Qwen3.5-397B GPTQ-Int4 produjo HTTP500 a 100K y apagado de nodo a 200K; propietario dice que reemplazo RMA sí completó bench depths a 250K/conc 8. Otros autores informan shutdown bajo >85W y FieldDiag PASS. Versiones exactas, OEM, temperatura y cargas varían, ninguna causa común demostrada.",
    "current_coverage": "FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION ya separa FieldDiag PASS de estabilidad bajo workload y contempla un FE/GX10 apagándose en inferencia. Estas fuentes añaden un patrón de falsos negativos en condiciones concretas de inferencia/context-depth, junto a resultados RMA; FORUM-02-PSTORE-KERNEL-REGRESSION conserva las firmas de kernel del caso FE.",
    "gap_or_complement": "Cruzar un PASS/FAIL del FieldDiag con un canary de workload reproducible apropiado al síntoma: modelo/checkpoint y digest de imagen fijos, context depths 0/65K/100K/200K, concurrencia, duración y power delivery; registrar resultado funcional y salud por nodo, CPU/GPU/SoC/ACPI térmicas, potencia/clocks/throttling, logs/pstore, FW slots exactos y errores del servicio. En reinicio, conservar pstore y journal antes de reset. Tratar una unidad que cae repetidamente en canary aunque FieldDiag pase como fallo operativo para soporte/RMA; comparar unidad de control compatible. No afirmar que PD FW, temperatura, firmware, watchdog o kernel sean causa sin A/B aislado, y no promover clock caps, CX7 disconnect ni watchdog-off como solución general.",
    "confidence": "Alta para los resultados relatados en los posts y el contraste FieldDiag PASS vs prueba práctica; media-baja para repetibilidad independiente y generalización OEM. Las imágenes, adjuntos de campo de 354205 y ZIP/SOS compartidos no se leyeron; el texto del post 45 es análisis de usuario sin confirmación oficial.",
    "risks": [
      "Un benchmark de larga ventana puede apagar equipos defectuosos; debe ejecutarse solo con administración local/SSH testada, workload acotado y recuperación disponible.",
      "Bajar clocks limita rendimiento y no aísla hardware frente a energía, firmware o thermals; desconectar CX7 elimina clustering y desactivar watchdog retira una protección.",
      "FieldDiag PASS es resultado de una batería concreta, no garantía de salud; una unidad sana en un control no exonera al DUT."
    ],
    "closure": "Con el OEM y firmware identificados, demostrar en control sano y en caso reproducible qué cobertura entrega FieldDiag y qué fallo real queda fuera. Repetir el canary exacto con réplicas en múltiples profundidades y registrar cada intento, reinicio, HTTP500, CPU/GPU/SoC thermal/power, pstore y estado de recuperación. Confirmar criterios de escalación/RMA con el vendor y demostrar evidencia legible después de fallo; conservar pruebas que no puedan correr como could_not_run y mantener la política de admisión abierta hasta prevención o recuperación probada.",
    "merge_into": "FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION"
  }
]
```
