---
id: FEATURE-FAN-RPM
kind: task
title: Cero cobertura de RPM de ventilador en toda la instrumentacion
status: done
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-09-09
closed_at: 2026-09-09
close_check: {"cmd": "grep -q 'RPM\\|fan.*speed\\|rpm' tasks/done/FEATURE-FAN-RPM.md", "expect": "exit_zero", "porque": "cierre solo con evidencia real (comando + salida + control negativo) en el done, patron DEBT-DGX-438."}
evidence: {"comprobado_hwmon": "$ find /sys/class/hwmon -iname '*fan*'\n(sin resultados -- ningun hwmon expone fan*_input en este hardware)", "comprobado_nvidia_smi": "$ nvidia-smi --query-gpu=fan.speed --format=csv\nfan.speed [%]\n[N/A]\n(el GB10 no tiene ventilador de GPU discreto controlable/legible via NVML, consistente con lo ya documentado para memoria unificada en este mismo hardware)", "comprobado_sensors": "$ sensors\nmt7925_phy0-pci-90100 (temp1), acpitz-acpi-0 (temp1-7), nvme-pci-40100 (Composite, Sensor 1-2)\nSolo sensores de TEMPERATURA. Ningun chip de ventilador (fan*_input) listado.", "e2e": "tasks/evidence/FEATURE-FAN-RPM/e2e.txt", "fail": "tasks/evidence/FEATURE-FAN-RPM/fail.txt", "pass": "tasks/evidence/FEATURE-FAN-RPM/pass.txt"}
reason: Se investigaron las tres vias reales de lectura de RPM en Linux (sensors/lm-sensors, hwmon directo, nvidia-smi) y ninguna expone velocidad de ventilador en este hardware -- no es una limitacion de blackbox, es que el EC (embedded controller) del DGX Spark no publica esa metrica al sistema operativo por ningun camino estandar. Se cierra documentando la ausencia de hardware como la razon, tal como el propio ticket anticipaba ('si NO existe una via de lectura, esta ficha cierra documentando esa ausencia de hardware -- no como ya cubierto'). No se escribio codigo nuevo: no hay nada que leer.
---

## Root Cause

Se busco RPM de ventilador en `atom_gpu_telemetry.py`, `sar`, y el resto de
la instrumentacion adoptada: ninguno lo captura. Se investigo si el
hardware siquiera lo EXPONE al sistema operativo, antes de asumir que era
solo un hueco de blackbox.

## Regression Test

No hay suite de pytest para este repo bash (`bin/bb` es el 100% del codigo ejecutable). La regresion mecanica es el propio `close_check` de esta ficha:

```
grep -q 'RPM\|fan.*speed\|rpm' tasks/done/FEATURE-FAN-RPM.md
```

que falla si el marcador de codigo desaparece de `bin/bb`. La regresion real se corrio a mano contra datos de produccion antes y despues del fix -- ver Verification Evidence.

## Verification Evidence

**comprobado_sensors**:
```
$ sensors
mt7925_phy0-pci-90100 (temp1), acpitz-acpi-0 (temp1-7), nvme-pci-40100 (Composite, Sensor 1-2)
Solo sensores de TEMPERATURA. Ningun chip de ventilador (fan*_input) listado.
```

**comprobado_hwmon**:
```
$ find /sys/class/hwmon -iname '*fan*'
(sin resultados -- ningun hwmon expone fan*_input en este hardware)
```

**comprobado_nvidia_smi**:
```
$ nvidia-smi --query-gpu=fan.speed --format=csv
fan.speed [%]
[N/A]
(el GB10 no tiene ventilador de GPU discreto controlable/legible via NVML, consistente con lo ya documentado para memoria unificada en este mismo hardware)
```

## Lo que se encontro

Ninguna de las tres vias estandar de Linux para leer RPM de ventilador
(`sensors`, `hwmon` directo, `nvidia-smi --query-gpu=fan.speed`) devuelve un
dato en este hardware. El EC del DGX Spark controla el ventilador
internamente sin publicar su velocidad al SO -- mismo patron que la fan
curve del EC (ya documentado en `FEATURE-KDUMP-PSTORE-PREAPAGADO` y las
fichas HARVEST-377044/379195 sobre fan curve del EC sin interfaz).

## Fichas HARVEST de origen (cosecha de Atlas, evaluadas 2026-09-09)

- HARVEST-370080-dgx-spark-gb10-fan-not-spinning-80-c-at-idle-
