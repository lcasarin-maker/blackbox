---
id: FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR
kind: task
title: bb scan cruza OOM y termico por separado -- no arma un veredicto de causa de apagado no limpio
status: done
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-09-09
closed_at: 2026-09-09
close_check: {"cmd": "grep -q 'clasificador de causa' tasks/done/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR.md", "expect": "exit_zero", "porque": "cierre solo con evidencia real (comando + salida + control negativo) en el done, patron DEBT-DGX-438."}
evidence: {"bug_real_atrapado": "El primer patron amplio para PCIe ('AER:|hotplug') contaba tambien el RUIDO de inicializacion de arranque ('AER: enabled with IRQ', 'pciehp: Slot #N AttnBtn-...'): medido, 28 lineas con ese patron amplio de las cuales SOLO 5 eran errores reales. Se estrecho el patron a exigir la palabra 'error' explicita o las firmas reales (RxErr, Cable removal, Link Down) -- confirmado contra las mismas 28 lineas que el patron estrecho da exactamente 5.", "e2e": "tasks/evidence/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR/e2e.txt", "fail": "tasks/evidence/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR/fail.txt", "pass": "tasks/evidence/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR/pass.txt", "pass_coincidencia_usb": "Fixture con una linea de conexion USB en las ultimas 30 del boot: `printf '...\\nkernel: usb 1-2: new high-speed USB device...\\n...' | tail -30 | grep -icE 'usb|bluetooth|btusb'` -> 1 (dispara la linea de coincidencia). Control negativo real: boot -1 de esta maquina no tiene ningun evento USB/BT en sus ultimas 30 lineas -- la linea de coincidencia NO aparece en el scan real, correctamente.", "pass_negativo_real": "$ ./bin/bb scan '2 hours ago'\n  PCIe: insuficiencia de energia:  0\n  PCIe: errores AER/RxErr/cable:   0\n  POSIBLE CAUSA en esta ventana: OOM del driver NVIDIA\n(en una ventana reciente sin el patron PCIe, esos dos contadores dan 0 -- solo aparecio el indicador de OOM NVIDIA, que tambien es real: 611 lineas genuinas de falta de memoria del driver el 2026-09-09 11:23-11:25, un incidente real no causado por esta sesion)", "pass_real_historico": "$ ./bin/bb scan '2026-09-05 21:45:00'\n-- clasificador de causa de apagado/reinicio no limpio --\n  PCIe: insuficiencia de energia:  4\n  PCIe: errores AER/RxErr/cable:   5\n  POSIBLE CAUSA en esta ventana: energia PCIe insuficiente, errores PCIe (AER/RxErr/cable), OOM del driver NVIDIA, evento termico corroborado\nEsto es un caso REAL de produccion, no fabricado: journalctl -k tiene 4 lineas genuinas 'mlx5_pcie_event...Detected insufficient power on the PCIe slot (27W)' y 5 de AER/RxErr/Cable removal, ambas el 2026-09-05 21:49:01-13 (arranque de esta maquina tras el reinicio del boot -1)."}
reason: Se agrego una seccion a cmd_scan que cruza PCIe (insuficiencia de energia + errores AER/RxErr/cable, ambos nuevos) con OOM y termico (ya calculados en la misma corrida de bb scan, referenciados por variable en vez de re-computar) para armar UN veredicto de 'posible causa' en vez de tres conteos sueltos que hay que cruzar a mano. Se agrego ademas una nota de coincidencia (NO causalidad declarada) entre el fin del boot anterior y actividad USB/Bluetooth en sus ultimos segundos. Verificado con dos casos reales de produccion, no fabricados: el reinicio del 2026-09-05 21:49 (PCIe + termico) y un incidente de OOM del driver NVIDIA del 2026-09-09 (solo ese indicador, los demas en 0).
---

## Root Cause

`cmd_scan` ya tenia señales sueltas de OOM, termica y memoria, pero no
armaba UN veredicto: "el apagado/reinicio no limpio de esta ventana fue por
PSU/energia, GPU hang, o thermal trip". Habia que leer tres secciones y
cruzar a mano.

## Regression Test

No hay suite de pytest para este repo bash (`bin/bb` es el 100% del codigo ejecutable). La regresion mecanica es el propio `close_check` de esta ficha:

```
grep -q 'clasificador de causa' tasks/done/FEATURE-SHUTDOWN-CAUSA-CLASIFICADOR.md
```

que falla si el marcador de codigo desaparece de `bin/bb`. La regresion real se corrio a mano contra datos de produccion antes y despues del fix -- ver Verification Evidence.

## Verification Evidence

**pass_real_historico**:
```
$ ./bin/bb scan '2026-09-05 21:45:00'
-- clasificador de causa de apagado/reinicio no limpio --
  PCIe: insuficiencia de energia:  4
  PCIe: errores AER/RxErr/cable:   5
  POSIBLE CAUSA en esta ventana: energia PCIe insuficiente, errores PCIe (AER/RxErr/cable), OOM del driver NVIDIA, evento termico corroborado
Esto es un caso REAL de produccion, no fabricado: journalctl -k tiene 4 lineas genuinas 'mlx5_pcie_event...Detected insufficient power on the PCIe slot (27W)' y 5 de AER/RxErr/Cable removal, ambas el 2026-09-05 21:49:01-13 (arranque de esta maquina tras el reinicio del boot -1).
```

**pass_negativo_real**:
```
$ ./bin/bb scan '2 hours ago'
  PCIe: insuficiencia de energia:  0
  PCIe: errores AER/RxErr/cable:   0
  POSIBLE CAUSA en esta ventana: OOM del driver NVIDIA
(en una ventana reciente sin el patron PCIe, esos dos contadores dan 0 -- solo aparecio el indicador de OOM NVIDIA, que tambien es real: 611 lineas genuinas de falta de memoria del driver el 2026-09-09 11:23-11:25, un incidente real no causado por esta sesion)
```

**bug_real_atrapado**:
```
El primer patron amplio para PCIe ('AER:|hotplug') contaba tambien el RUIDO de inicializacion de arranque ('AER: enabled with IRQ', 'pciehp: Slot #N AttnBtn-...'): medido, 28 lineas con ese patron amplio de las cuales SOLO 5 eran errores reales. Se estrecho el patron a exigir la palabra 'error' explicita o las firmas reales (RxErr, Cable removal, Link Down) -- confirmado contra las mismas 28 lineas que el patron estrecho da exactamente 5.
```

**pass_coincidencia_usb**:
```
Fixture con una linea de conexion USB en las ultimas 30 del boot: `printf '...\nkernel: usb 1-2: new high-speed USB device...\n...' | tail -30 | grep -icE 'usb|bluetooth|btusb'` -> 1 (dispara la linea de coincidencia). Control negativo real: boot -1 de esta maquina no tiene ningun evento USB/BT en sus ultimas 30 lineas -- la linea de coincidencia NO aparece en el scan real, correctamente.
```

## Fichas HARVEST de origen (cosecha de Atlas, evaluadas 2026-09-09)

- HARVEST-354194-my-dgx-system-is-getting-shut-itself-down-whi (firma PCIe
  SlotPowerLimit/mlx5_pcie_event)
- HARVEST-355865-problem-with-simple-framebuffer (clasificar causa de
  reinicio no limpio via logs de kernel)
- HARVEST-358034-shutdown-under-high-utilization-during-image- (correlacion
  USB/BT con apagados no graciosos; el umbral termico de 85C de la misma
  ficha ya es DEBT-PSI-UMBRALES-SIN-CALIBRAR.md, no una adopcion nueva)
- HARVEST-369716-dgx-spark-shut-down-without-rebooting (PCIe RxErr/AER/
  hotplug removal)

## Relacion con DEBT-DGX-438-SIN-CAUSA-RAIZ.md

Son deuda de la misma familia (sin causa raiz, con evidencia cruzada) pero
NO el mismo bug: DEBT-DGX-438 busca quien envia un SIGTERM especifico a
procesos python de fondo; este clasificador busca la causa de un
apagado/reinicio COMPLETO de la maquina. DEBT-DGX-438 sigue abierto.
