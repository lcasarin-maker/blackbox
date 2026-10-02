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

## Delta y prevención/resolución

atom_gpu_telemetry.py lee zonas cada5s, corroboración exige carga GPU≥60W y mitigación se limita a tres jobs propios. La cobertura para calor CPU/idle y modelos residentes requiere prueba; esta auditoría del código deja pendiente demostrar un miss en incidente real.

Reutilizar muestras existentes para distinguir GPU/CPU/SoC, headroom por zona, residencia y concurrencia. Evaluar admisión y acciones sobre workloads con ownership explícito; conservar debounce/controles antispikes. Probar una rama corroborada CPU/idle y conectar fan/CX7; parar procesos por nombre o matar servicios compartidos carece de objetivo verificable.

## Validación, riesgo y cierre

calor CPU sostenido, fan detenido en idle, spike ACPI aislado, GPU caliente real y sensores ilegibles. A/B por OEM/firmware/modelos con presupuesto y soak declarados, medir throughput local antes de afirmar mejora; control sin modelos residentes y rollback de políticas. Dar una acción preventiva verificada o declarar limitación, jamás convertir permiso/sensor faltante en sano.

El verificador de close_check todavía debe implementarse; ejecutar esta ficha exige evidencia adicional y deja registradas las consultas que no pueden correr. Ningún cambio del host se aplica al registrar la propuesta. Detalle fuente preservado en tasks/evidence/SWARM-LUNA-FORUM-2026-10-02/findings_*.json y threads/.

## Avance de ejecución 2026-10-02

Revisión de _corroboracion confirma que historial caliente sostenido con carga GPU ociosa devuelve descarta. No existe medición local que calibre reemplazo seguro para CPU/idle; 0 cambios de compuerta, 0 A/B y 0 claims de throughput. Falta medir sensores independientes/CPU y fan con controles antispike antes de automatizar pausa.

Evidencia y pendientes: `tasks/evidence/FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION/progress.txt`. Conserva `open`; la captura de estado verifica el instrumento y deja pendiente el ensayo de recuperación/prevención requerido.

[369381](https://forums.developer.nvidia.com/t/369381) añade un FE A.7/BIOS 5.36_0ACUM018/kernel 6.17.0-1014/driver 580.142 que cuelga bajo vLLM en 4–60 minutos y pierde ping/SSH; `FieldDiag GpuStress` falla de forma repetible con MODS020000021139 (“temperature limits exceeded or thermal sensor broken/miscalibrated”), incluso después de reinstalar DGX OS 7.5. NVIDIA aprobó RMA. Este caso requiere separar temperatura excesiva, sensor defectuoso y pérdida de telemetría; capturar FieldDiag y sensores antes de carga, bloquear soak si el diagnóstico falla y preservar ruta RMA. Las respuestas de otros dueños sobre repaste/96°C/GPU clock caps no son una corrección validada para el FE y quedan fuera como recomendación.

[372469](https://forums.developer.nvidia.com/t/372469) aporta otro caso térmico distinto: un FE falla `FieldDiag powerStress` con MODS020000600139, mientras GX10 de otros dueños pasan FieldDiag pero uno se apaga durante inference TP a 80–81°C y 41–45W. Los workloads de stress de esos GX10 no reproducen el apagado. Registrar OEM, workload, temperatura/potencia y test diagnóstico juntos; un PASS de FieldDiag no excluye shutdown durante el perfil real, y un FAIL de powerStress/thermal no autoriza generalizar el mecanismo entre OEM.

[380282](https://forums.developer.nvidia.com/t/380282) provides a more controlled idle thermal comparison on two matching ASUS GX10s: unplugging HDMI alone while the same X11 session stays active raises GPU36→45°C and ACPI39.8→47.9°C in five minutes at P8/3.48–3.71W; a headless GDM control remains at GPU34–36°C. No RPM/PWM signal is exposed and NVIDIA has no ASUS fan-control details. The power-based fan-curve explanation and proposed USB/HDMI/CX7 dummy loads are user hypotheses/workarounds, with added power draw; do not recommend them. Reproduce display hotplug/idle state with OEM sensor/fan diagnostics and matched control.

[381029](https://forums.developer.nvidia.com/t/381029) is a low-confidence external cooling experiment: an author claims ~18°C lower temperature on GX10 and ~150% cooling improvement on a Spark with a forced-air shroud; attached graphs/schematics were not independently audited here. Treat as an optional laboratory A/B only, with OEM clearance, airflow, noise, power and matching-workload checks; it does not establish that overheating is eliminated.

[361960](https://forums.developer.nvidia.com/t/dgx-spark-gb10-fans-do-not-spin-in-headless-boot-mode-temperature-rises-to-70-c/361960) reports a fan/temperature anomaly on one of two matched ASUS GX10 units: 7.5/580.173.02/6.17-1029, affected unit GPU 55–58°C and ~3.8–4W in P8 with a slower audible fan; its headless control stayed at 34–35°C. HDMI plus an active X11 session reduced the affected unit to 36–40°C, and unplugging HDMI while the same session stayed active increased it again. A prior DGX OS 7.4 report blamed headless boot, but NVIDIA could not reproduce and another owner had no issue headless. Treat display state as an A/B factor, not an established root cause. The same evidence is cross-posted in [380282](https://forums.developer.nvidia.com/t/380282). Screenshots from the initial post remain uninspected.

[370198](https://forums.developer.nvidia.com/t/dgx-spark-runs-hot-and-firmware-update-keeps-repeating/370198) compares two bundled FE Sparks; one idles 10–15°C hotter and Dashboard repeats a firmware update five times. A CLI `apt dist-upgrade` plus `fwupdmgr refresh/upgrade` reportedly completes the update, but the hotter unit remains hot at idle. FieldDiag r9.257.3 passed GPU, CPU, power, thermal, SSD and memory tests. This is a useful control case: a PASS and a successful firmware update do not clear a persistent idle-temperature delta. Images are uninspected; firmware IDs and actual temperatures are not recoverable from their text.

[362277](https://forums.developer.nvidia.com/t/unexpected-shutdown-during-comfyui-inference-on-dgx-spark-occurs-on-two-units/362277) reports hard shutdowns after 1–2 ComfyUI inference steps on two FE systems while a different Spark handles 250 concurrent requests. Three FieldDiag runs per affected unit passed; the owner reports a power limit suppresses the shutdown, without publishing its value or controlled retest. Other participants attribute this to power draw or heat, and one similar owner received an RMA recommendation. Keep FieldDiag PASS separate from workload stability; any power cap is a temporary, workload/OEM-specific A/B with performance and rollback evidence, not a global fix.

[364635](https://forums.developer.nvidia.com/t/running-hot-even-at-idle/364635) asks whether four idling Sparks run hotter with CX7 connected; it contains no temperature, power or diagnostic result. Use only as a prompt for a matched cable-connected/disconnected control.

[348562](https://forums.developer.nvidia.com/t/suggestions-for-reducing-idle-power-consumption/348562) adds an ASUS Ascent GX10-specific firmware candidate: two users report socket idle power changing from about 40 W to 24–25 W after an OS update plus additional firmware then in `lvfs-testing`; one had to unplug the ConnectX-7 cable to trigger the saving. A reply claims another 2 GB available memory. Exact firmware/build and loaded-workload power were not supplied, and the author flags the firmware as pre-release. Record as a canary-only vendor update candidate with wall-socket measurement, cable/RDMA controls, loaded soak and rollback; do not generalize to FE or recommend pre-release updates as a default.


[381549](https://forums.developer.nvidia.com/t/381549) reporta CPU a 92–95°C en un nodo head y luego 86°C después de retirar underclock de GPU, mientras su par estaba en 63°C. Otro dueño de Gigabyte AI TOP ATOM refiere CPU en los 90°C con baja utilización CPU durante inferencia. Las causas y sugerencias (underclock, ventilador externo/PWM, pasta térmica) no fueron aisladas ni verificadas. Añadir perfil separado de temperatura CPU/GPU, fan/airflow y workload en ambos nodos; rechazar admisión o escalar conforme a límites OEM, sin asumir que bajar GPU clocks enfría la CPU. Imágenes del hilo no fueron inspeccionadas.
