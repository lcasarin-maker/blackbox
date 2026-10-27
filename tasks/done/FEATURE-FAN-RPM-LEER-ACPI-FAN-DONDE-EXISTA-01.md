---
id: FEATURE-FAN-RPM-LEER-ACPI-FAN-DONDE-EXISTA-01
kind: task
domain: THERMAL
title: "bb: leer RPM del ventilador por hwmon acpi_fan donde el dispositivo exista (FE con EC/SoC recientes) y declarar NOT_COLLECTED donde no"
status: done
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-26
closed_at: 2026-10-27
evidence: {"fail": "tasks/evidence/FEATURE-FAN-RPM-LEER-ACPI-FAN-DONDE-EXISTA-01/fail.txt", "pass": "tasks/evidence/FEATURE-FAN-RPM-LEER-ACPI-FAN-DONDE-EXISTA-01/pass.txt"}
close_check: {"cmd": "python3 -m pytest -q tests/test_fan_rpm.py -k acpi_fan", "expect": "exit_zero", "porque": "Especificacion pendiente, no prueba existente: exige leer fan1_input de un hwmon cuyo name sea acpi_fan (fixture), NOT_COLLECTED con motivo cuando no existe (caso de esta ATOM) y nunca cero como sustituto."}
---

## Origen

`FEATURE-FAN-RPM` (done) cerro con la afirmacion de que el EC del DGX Spark no publica RPM por ninguna via estandar. El hilo
[386805](https://forums.developer.nvidia.com/t/386805), posts 1 y 11 (DGX Spark FE, DGX OS 7.6.0, kernel 7.0.0-1019, EC 0x03000d07,
SoC 0x02009e0f), lo contradice para esa combinacion: lee `/sys/class/hwmon/hwmon*/fan1_input` en el hwmon cuyo `name` es
`acpi_fan` (fans 2,030 / 2,075 rpm en reposo) y expone `\_SB.FAN0/FAN1` como `cooling_device` con `max_state` 100. El hilo
[378945](https://forums.developer.nvidia.com/t/378945/14) (zneill) pide justo esa lectura en estado sano y en falla.

## Medido en esta ATOM (2026-10-26)

Ningun hwmon `acpi_fan` y ningun `cooling_device` de ventilador (solo 20 `Processor` y 6 `PCIe_Port_Link_Speed`). La afirmacion de
`FEATURE-FAN-RPM` sigue siendo cierta aqui y es falsa en otras unidades: depende del OEM y de la version de EC/SoC/kernel.

## Alcance

Un lector de solo lectura que busque `acpi_fan` y devuelva RPM por ventilador; sin dispositivo: `NOT_COLLECTED: sin hwmon acpi_fan`.
Nunca 0 como sustituto de "no hay dato" (un ventilador parado es un 0 real y debe distinguirse). Incluir la identidad del dispositivo
(OEM, EC, SoC) en la salida. Reutilizar la lectura de zonas termicas de `atom_gpu_telemetry.py`.

## Control negativo exigido

Fixture con `acpi_fan` => RPM; sin `acpi_fan` => `NOT_COLLECTED`; `fan1_input` = 0 => `0` con la etiqueta de ventilador detenido, no
`NOT_COLLECTED`. Un test que solo prueba el caso con dispositivo no cierra la ficha.

## Cierre (2026-10-27)

### Donde se expone y por que

`python3 -m tools.thermal_coverage --acpi-fan [--root R] [--forense-dir D]`, funcion `thermal_coverage.acpi_fan()`.
Es el menor cambio porque `tools/thermal_coverage.py` ya recorria `sys/class/hwmon/hwmon*` bajo un `--root` sustituible, ya leia
`fan*_input` como rpm con `_channel()` y ya leia `/sys/class/dmi/id`; la identidad EC/BIOS sale de `incident_report.firmware_recogido()`,
el helper que ya parsea `/var/lib/blackbox/dmidecode-t45.txt` (ninguna fuente nueva). El modo por defecto de `thermal_coverage` no cambia.

La ficha pedia reutilizar la lectura de zonas de `atom_gpu_telemetry.py`; no se uso: ese modulo lee `thermal_zone*` (temperatura) y no
recorre hwmon ni acepta raiz sustituible, asi que el helper reutilizable para hwmon era `thermal_coverage`. Meter RPM en cada muestra del
muestreador cambiaria el sampler en vivo, que esta ficha no pide.

Limite declarado: `bin/bb` NO llama `tools.thermal_coverage` (no existe `bb ventilador`); el lector se invoca como modulo. Cablearlo es
una linea en el `case` de `bin/bb`, pero tocaria la cobertura del piso de `bb`; queda fuera de este cierre.

### Semantica

- hwmon con `name == acpi_fan` => un registro por `fanN_input` con `rpm` entero y `estado` `girando`.
- `fanN_input` = 0 => `rpm: 0`, `estado: detenido` (lectura valida, `could_not_run` no sube).
- sin ningun hwmon `acpi_fan` => `status: NOT_COLLECTED`, `motivo: "NOT_COLLECTED: sin hwmon acpi_fan"`, `ventiladores: []`; si algun
  `name` fue ilegible, el motivo lo dice (no se descarta que ese hwmon fuera `acpi_fan`).
- `fanN_input` ilegible, no entero o negativo => `rpm: null`, `estado: "NOT_COLLECTED: <motivo>"`; nunca 0. Un canal malo no oculta los
  demas (`status: partial`).
- exit 0 solo si `could_not_run == 0`; si no, 2 (misma convencion que el modo por defecto).

### Evidencia

`tasks/evidence/FEATURE-FAN-RPM-LEER-ACPI-FAN-DONDE-EXISTA-01/fail.txt` (close_check rc=4 antes; tests nuevos contra el codigo anterior:
7 failed; cuatro mutantes del lector, cada uno atrapado) y `pass.txt` (close_check 7 passed rc=0; corrida real en esta ATOM:
`NOT_COLLECTED: sin hwmon acpi_fan`, GIGABYTE AI TOP ATOM, EC Firmware=3.5.11, rc=2).

Fila de SPEC.md desactualizada (no editada, invalida el ledger H1): la de `tools/thermal_coverage.py` no menciona el modo `--acpi-fan`
ni `tests/test_fan_rpm.py`.
