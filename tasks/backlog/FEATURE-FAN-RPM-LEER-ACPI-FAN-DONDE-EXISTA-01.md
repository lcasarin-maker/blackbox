---
id: FEATURE-FAN-RPM-LEER-ACPI-FAN-DONDE-EXISTA-01
kind: task
domain: THERMAL
title: "bb: leer RPM del ventilador por hwmon acpi_fan donde el dispositivo exista (FE con EC/SoC recientes) y declarar NOT_COLLECTED donde no"
status: open
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-26
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
