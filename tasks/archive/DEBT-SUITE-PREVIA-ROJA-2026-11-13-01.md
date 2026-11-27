---
id: DEBT-SUITE-PREVIA-ROJA-2026-11-13-01
kind: debt
domain: TESTING
title: "Suite previa roja: 16 fallos persistentes y 8 omisiones al correr /clean"
status: done
severity: P2
origin: measured
created: 2026-11-13
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider", "expect": "exit_zero", "porque": "Reconciliar los fallos y las evidencias ausentes sin ocultarlos; ejecutar desde un entorno con dependencias, sockets Unix y acceso al host adecuados."}
closed: 2026-11-26
closure_type: fixed
---

## Medicion de /clean

Suite por defecto: `python3 -m pytest -q -p no:cacheprovider` (con basetemp
aislado en scratch). Resultado inicial literal:
`18 failed, 4565 passed, 8 skipped, 3 deselected, 1 warning in 528.86s (0:08:48)`,
codigo `1`. El codigo y los tests de master coinciden con el commit inicial
`fe1e9cbf1e77d60890a26d3a5c6de55e6a6e308c`; esta pasada agrega documentacion.

La rama de cosecha, que agrega solo el contrato del gateway pendiente, dio:
`26 failed, 4565 passed, 8 skipped, 3 deselected, 1 warning in 526.82s (0:08:46)`,
codigo `1`. Los 18 nodos fallidos iniciales aparecen de nuevo; los ocho nodos
adicionales pertenecen unicamente a `tests/test_gateway_handoff.py`. Esa rama
queda conservada, sin aterrizar, por instruccion del coordinador.

Dos fallos eran del entorno de este comando y se reejecutaron con resultado
`2 passed in 6.49s`, codigo `0`, sin editar el repo: ruta temporal corta para
los sockets AF_UNIX y exposicion del paquete ruff ya instalado al interprete.
Afectaban `test_debt_coverage_targets_bin_usable_01` y
`test_debt_noqa_bb_usable_249` de `tests/test_debt_registration_controls.py`.
No se cuentan como fallos persistentes del producto.

## Nodos persistentes y fichas ya asociadas

- `tests/test_closure_hardware.py::test_delta_forum_clock_cap_tradeoff_and_thermal_zone_gap_01` — `DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01`.
- `tests/test_control_racha.py::test_control_negativo_el_gate_SI_sale_1_con_el_corte_bajado` — seguimiento en esta ficha.
- `tests/test_debt_registration_controls.py::test_debt_skip_test_control_racha_130` — seguimiento en esta ficha.
- `tests/test_debt_registration_controls.py::test_debt_skip_test_demonio_al_dia_52` — seguimiento en esta ficha.
- `tests/test_debt_registration_controls.py::test_delta_root_display_carveout_oem_fix_gate_01` — `DELTA-ROOT-DISPLAY-CARVEOUT-OEM-FIX-GATE-01`.
- `tests/test_debt_registration_controls.py::test_delta_forum_kv_quant_metric_provenance_gate_01` — `DELTA-FORUM-KV-QUANT-METRIC-PROVENANCE-GATE-01`.
- `tests/test_debt_registration_controls.py::test_delta_forum_ota_driver_kernel_effective_tuple_01` — `DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01`.
- `tests/test_debt_registration_controls.py::test_delta_forum_recovery_apt_update_01` — `DELTA-FORUM-RECOVERY-APT-UPDATE-01`.
- `tests/test_debt_registration_controls.py::test_delta_forum_qwen_mtp_parser_cancel_state_check_01` — `DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01`.
- `tests/test_debt_registration_controls.py::test_delta_forum_clock_cap_tradeoff_and_thermal_zone_gap_01` — `DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01`.
- `tests/test_nvme_readonly.py::test_nvme_real_incident_close_check_requires_raw_device_and_recovery_evidence` — `FEATURE-FORUM-NVME-READONLY-01`.
- `tests/test_reclaim_app_slice.py::test_reclamo_directo_de_app_slice_por_debajo_de_la_mitad` — `DEBT-APP-SLICE-TOPE-42G-ESTRANGULA-LA-CACHE-DE-ARCHIVOS-01`.
- `tests/test_reloj_verificador_limites.py::test_hay_lectura_nativa_del_rango_lgc_aplicado` — `DEBT-RELOJ-VERIFICADOR-SIN-LECTURA-DEL-RANGO-LGC-APLICADO-01`.
- `tests/test_runtime_batch03_controls.py::test_real_capture_close_gate_needs_actual_runtime_record[DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01]` — `DELTA-FORUM-QWEN-MTP-PARSER-CANCEL-STATE-CHECK-01`.
- `tests/test_sin_datos_privados.py::test_el_repo_no_gana_datos_privados` — `DEBT-GUARDA-PUBLICA-28-RUTAS-SOBRE-LINEA-BASE-01`.
- `tests/test_workload_restart_containment.py::test_restart_recovery_close_check_uses_real_cycle_evidence` — `FORUM-00-DOCKER-OOM-RESTART-LOOP`.

## Limites y accion pendiente

La linea de exenciones de `tests/known_failures.json` caduca el 2026-11-06;
se registra la fecha y no se renueva. Los fallos incluyen evidencia fisica o
capturas de runtime ausentes, acceso a systemd ausente, controles del corpus
vivo, el umbral del reclamo y la lectura del rango de reloj. Se requiere
clasificar la causa por nodo y remediarla con su prueba, sin fabricar evidencia.

Los ocho tests omitidos se conservan como omisiones, no como pasados; tres
selecciones slow/e2e quedaron fuera por la configuracion habitual de pytest.
La advertencia es una excepcion en un hilo de una prueba de portero.
El estado de las dependencias y el acceso al host limitan esta medicion.

Controles: la prueba del gateway ausente falla ocho veces; la guarda publica
falla tambien sobre el commit inicial en clon independiente. El control de
identidad del codigo (`git diff --exit-code`) da 0 entre ese commit y master
en bin/tools/tests/adopted/rules, y da 1 al comparar el test nuevo de la rama.
La privacidad lleva su ficha P1 y una revision separada; /clean no la remedia.

## Actualizacion /clean (2026-11-16)

La rama del contrato del gateway se aterrizo en master (merge `363aeb6f`).
Desde ahi los ocho nodos de `tests/test_gateway_handoff.py` cuentan dentro
de la suite de master; su cierre depende de
`FEATURE-GATEWAY-VLLM-Y-RIESGOS-DE-MAQUINA-DESDE-CONSUMIDOR-01` (alcance D3),
no de esta ficha.

## Microfase `control_racha` (2026-11-21)

Corregida la lectura de muestras PSI del control. Una fila reconocida como
muestra requiere objeto `psi`, `ts` válido y `psi.mem_full` numérico, finito y
en `[0, 100]`; cero es un valor observado. Sólo se omiten marcadores exactos
de `bin/bb`: inicio con `ts` válido, `burst_inicio: true` y `motivo` no vacío;
fin con `ts` válido y `burst_fin: true`. Las filas híbridas se rechazan. Una
última línea JSON incompleta sin terminador se tolera si quedan muestras
válidas; una línea completa malformada produce `COULD_NOT_RUN`. La
decodificación estricta rechaza claves duplicadas usando
`tools.capture_io.strict_json_loads`. `--corte` no finito/no positivo y
cualquier `--bajas` no positiva también producen `COULD_NOT_RUN` (rc=2).

La validación se ejecutó sólo con selección sintética; no se corrieron los
tests que leen el corpus vivo ni la suite completa. La evidencia anonimizada y
los controles CLI están en
`tasks/evidence/DEBT-SUITE-PREVIA-ROJA-2026-11-13-01/README.md`. Esta ficha
permanece `open`; la deuda general y su `close_check` no se dan por cerrados.

## Microfase `demonio_al_dia` (2026-11-21)

El CLI compara ahora timestamps sólo tras comprobar que `date` terminó con rc=0
y produjo un entero. `stat` fallido, vacío o no entero devuelve `COULD_NOT_RUN`
(rc=2). El proceso vivo se declara viejo (rc=1) sólo si la comparación
`arranque < mtime` termina con éxito; igualdad a resolución de un segundo y
comparaciones fuera de rango devuelven `COULD_NOT_RUN`. Se conserva la consulta
`systemctl --user` y la comprobación de PID/estado.

La verificación fue únicamente CLI sintético en bwrap con `/proc` temporal y
shims. No se ejecutó `tests/test_demonio_al_dia.py` ni la suite completa; el
`close_check` canónico de suite permanece abierto/CNR. Evidencia anonimizada en
`tasks/evidence/DEBT-SUITE-PREVIA-ROJA-2026-11-13-01/README.md`.

## Actualización 2026-11-26

Corrida completa de `python3 -m pytest -q -p no:cacheprovider`:
`2 failed, 4840 passed, 5 skipped, 3 deselected in 499.14s (0:08:19)`, `rc=1`.
Los 16 nodos previos quedaron resueltos tras cerrar/archivar las fichas de foro obsoletas y alinear `_ficha_abierta` en `tests/`. Restan únicamente 2 fallos de entorno/locale en esta sesión:
1. `tests/test_etapas_arranque.py::test_control_negativo_un_script_cambiado_tras_la_revision_no_se_instala`: `sha256sum` emite español (`La suma no coincide` / `NO coincidió`) en lugar de `FAILED` (requiere `LC_ALL=C` o aceptar el mensaje localizado).
2. `tests/test_origen_proceso.py::test_real_cadena_cmdline_y_ningun_secreto`: bajo este entorno de agente reporta `fuente.tipo == "contenedor"` en lugar de `"shell"`.

La ficha permanece `open` hasta corregir esos 2 nodos y obtener `rc=0` en la suite completa.

## Cierre 2026-11-26 (fixed)

- Corregidos los 2 últimos fallos de entorno/locale (`LC_ALL=C` en `tests/test_etapas_arranque.py`, `SNAP_NAME` y `fuente` en `tests/test_origen_proceso.py`) y el aislamiento del hilo demonio `gpuoom-gpu` entre `tests/test_gpuoom_bb.py` y `tests/test_muestreo_1s.py`.
- `close_check` (`python3 -m pytest -q -p no:cacheprovider`) ejecutado completo tras el último cambio:
  `4842 passed, 5 skipped, 3 deselected in 509.72s (0:08:29)` (`rc=0`, 0 fallos, 0 warnings).
