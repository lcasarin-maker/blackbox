---
id: FEATURE-1358-A2-EXPORTACION-EXTERNA
kind: task
domain: GPU
title: "Exportación opcional de telemetría fuera del host"
status: done
reason: "Alcance local implementado y verificado; despliegue y utilidad durante incidentes se declaran aparte."
closed_at: 2026-10-02
evidence: {"pass": "tasks/evidence/FEATURE-1358-A2-EXPORTACION-EXTERNA/pass.txt", "fail": "tasks/evidence/FEATURE-1358-A2-EXPORTACION-EXTERNA/fail.txt", "e2e": "tasks/evidence/FEATURE-1358-A2-EXPORTACION-EXTERNA/e2e.txt"}
satd_family: BLIND_INSTRUMENT
closure_type: fixed
severity: P2
origin: asserted
created: 2026-10-02
close_check: {"cmd": "python3 -m pytest -q tests/test_1358_telemetria.py -k \"udp or dry_run\"", "expect": "exit_zero", "porque": "Comportamiento y controles negativos del alcance implementado, sin afirmar despliegue."}
---

## Contexto

Derivada de NVIDIA/open-gpu-kernel-modules#1358 y la comparación del 2026-10-02.

## Alcance

Reutilizar productor tools/atom_gpu_telemetry.py. Exportar datagrama UDP opcional a destino configurado, sin inventar receptor ni destino y sin habilitar transmisión por defecto. Fallo de exportación visible y no detiene muestreo; tamaño acotado.

## Verificación y límite

`BLACKBOX_UDP_DESTINATION=IP:PORT` activa un datagrama por muestra; sin variable no se abre socket. Solo acepta IP literal para evitar resolución DNS en el bucle. `--dry-run` no escribe y por eso omite la exportación. El JSON es compacto, limitado a 1200 bytes y usa una lista de campos permitidos sin hostname, PID ni procesos GPU. Incluye boot_id y hasta ocho temperaturas por zona. El envío tiene timeout de 100 ms; errores de dirección o socket se informan en stderr y no salen de `exportar_udp` ni detienen el muestreo. La muestra se exporta después de ejecutar la mitigación y antes de abrir/escribir el JSONL local.

Pruebas locales: mocks y destino loopback; no se inició receptor ni hubo envío externo. Cierre local implementado y cubierto por `tests/test_1358_telemetria.py`. El despliegue y la utilidad ante fallas reales quedan sin validar.

## Root Cause

La telemetría GPU se guardaba localmente, por lo que un incidente que impida leer el host puede dejar los datos inaccesibles. El envío optativo agrega un destino configurable; no afirma que la exportación haya corregido el problema de NVIDIA.

## Regression Test

`tests/test_1358_telemetria.py` valida payload acotado, exclusión de identificadores, destino IP literal, fallo visible, loopback y que `--dry-run` no envía.

## Verification Evidence

Salidas reales de pytest: `tasks/evidence/FEATURE-1358-A2-EXPORTACION-EXTERNA/{pass,fail,e2e}.txt`. Sin receptor externo ni despliegue.
