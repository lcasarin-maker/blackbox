---
id: DEBT-CONTROL-RACHA-VENTANA-2026-10-21-1706-SIN-ETIQUETAR-01
kind: task
domain: MEMORY
title: "test_control_racha falla sobre el corpus real: racha sostenida de 451 s el 2026-10-21 17:06 fuera de toda ventana de incidente etiquetada"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-30
close_check: {"cmd": "python3 -m pytest -q -p no:cacheprovider tests/test_control_racha.py::test_el_gate_sale_0_sobre_el_corpus_real", "expect": "exit_zero", "porque": "Falla hoy en master (medido 2026-10-30, antes de cualquier cambio de esta sesion): corpus 25719 muestras 2026-10-15 a 2026-10-30, 9 ventanas de incidente excluidas, y las reglas de 1, 2, 3 y 6 bajas dan FALSO POSITIVO en 2026-10-21 17:06:32 con un maximo sostenido sano de 451 s. Pasa cuando esa ventana este etiquetada como incidente con evidencia independiente de PSI, o cuando se demuestre otra lectura, sin recalibrar el umbral."}
---

## Medido (2026-10-30, `python3 -m pytest -q tests/test_control_racha.py -k corpus_real`)

El control corre `tools/control_racha.py` sobre las muestras reales de bb. Salida: "ventanas de incidente excluidas: 9 ... corte de accion: 300s umbral: 10%"; las cuatro reglas dan "FALSO POSITIVO en 2026-10-21 17:06:32", "max sostenido sano 451 s". Es decir: hubo una racha de presion sostenida mas larga que el watchdog de 360 s de `bb-usable` en una ventana que ningun incidente etiquetado cubre, y la maquina no reinicio.

## Evidencia independiente de que hubo un incidente (no es PSI)

- `tasks/evidence/FEATURE-ADMISION-TODO-O-NADA-CON-HOLGURA-REAL-01/medicion.txt`: colapso medido el 2026-10-21 a las 16:38:03 (admision de suite a las 16:36:27).
- `journalctl --since "2026-10-21 16:30" --until "2026-10-21 17:20"`: `blackbox-sample.service: Main process exited, code=killed, status=15/TERM` repetido desde las 16:38:49 hasta al menos las 16:45:04.

## Precedente

`DECISIONS.md` 2026-10-14 (voto de Luis, racha-118): se etiqueta la ventana como incidente con evidencia independiente de PSI y NO se recalibra la regla (recalibrar haria que la maquina tardara mas en reiniciarse ante un colapso real). Las ventanas viven en `tools/calibra_psi.py::INCIDENTES`.

## Para cerrar

1. Confirmar con una fuente que no sea PSI (sar, journal, `bb sample`) los limites de la ventana 16:38 a ~17:15 del 2026-10-21.
2. Anadir la ventana a `INCIDENTES` con su evidencia, como se hizo con la del 2026-10-05; el close_check debe pasar sin tocar el umbral.
3. Si la evidencia no sostiene un incidente, entonces es un hallazgo mayor: una racha de 451 s con PSI alto sin reinicio contradice la regla del watchdog y se abre decision de Luis.

Descubierta por dos agentes de `/cerrar-deuda` al correr sus suites completas; no tenia ficha.
