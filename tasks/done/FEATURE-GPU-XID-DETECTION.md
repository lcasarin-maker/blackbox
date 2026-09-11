---
id: FEATURE-GPU-XID-DETECTION
kind: task
title: bb scan grep-ea NVRM OOM pero nunca codigos Xid del driver NVIDIA
status: done
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-09-09
closed_at: 2026-09-09
close_check: {"cmd": "grep -q 'Xid' tasks/done/FEATURE-GPU-XID-DETECTION.md", "expect": "exit_zero", "porque": "cierre solo con evidencia real (comando + salida + control negativo) en el done, patron DEBT-DGX-438."}
evidence: {"e2e": "tasks/evidence/FEATURE-GPU-XID-DETECTION/e2e.txt", "fail": "tasks/evidence/FEATURE-GPU-XID-DETECTION/fail.txt", "fail_control_negativo_nvidia_smi": "$ PATH=/tmp/fakepath_test ./bin/bb scan '5 minutes ago' | grep 'nvidia-smi responde'\n  nvidia-smi responde ahora:   NO (timeout o error...)\n(fakepath_test = symlinks a coreutils SIN nvidia-smi -- probar con PATH=/usr/bin:/bin fallo, porque nvidia-smi vive en /usr/bin y seguia encontrandose)", "pass": "tasks/evidence/FEATURE-GPU-XID-DETECTION/pass.txt", "pass_extraccion_fixture": "grep -k no permite inyectar en /dev/kmsg sin root, asi que la extraccion se probo en aislamiento contra 2 lineas reales de Xid (codigos 79 y 119, formato NVIDIA verbatim):\n$ printf '...NVRM: Xid (PCI:0000:01:00): 79...\\n...NVRM: Xid (PCI:0000:01:00): 119...\\n...NVRM: Xid (PCI:0000:01:00): 79...\\n' | grep -oE 'Xid \\(PCI:[^)]*\\): [0-9]+' | grep -oE '[0-9]+$' | sort | uniq -c | sort -rn\n    codigo 79     x2\n    codigo 119    x1", "pass_real": "$ ./bin/bb scan '5 minutes ago' | sed -n '/Xid del driver/,/^$/p'\n-- Xid del driver NVIDIA --\n  eventos Xid:                 0\n  nvidia-smi responde ahora:   si\n(0 es la linea base real de esta maquina -- journalctl -k nunca vio un Xid historico)"}
reason: Se agrego deteccion de codigos Xid (fallos de hardware/firmware del driver NVIDIA distintos de OOM) a cmd_scan, agrupados por codigo igual que los core dumps, mas un chequeo de disponibilidad de nvidia-smi con timeout explicito en la misma seccion (no en bb status como decia el plan original -- se puso junto al resto de la seccion Xid por cohesion, mismo efecto). Bug real atrapado en el camino: la primera extraccion del codigo (`awk -F'Xid[^0-9]*'`) confundia los digitos de la direccion PCI ('0000:01:00') con el codigo Xid real, devolviendo '0000:01:00):' en vez de '79' -- se corrigio extrayendo el numero que sigue a '): ' especificamente.
---

## Root Cause

`cmd_scan` (seccion 1, "OOM del kernel y del driver NVIDIA") solo buscaba
`NVRM.*(Out of memory|NV_ERR_NO_MEMORY)`. Los codigos Xid -- la forma en que
el driver NVIDIA reporta fallos de hardware/firmware que NO son OOM (timeout
de RPC del GSP, fallo de init de firmware, ECC, etc.) -- no se buscaban en
ningun lado de `bin/bb`.

## Regression Test

No hay suite de pytest para este repo bash (`bin/bb` es el 100% del codigo ejecutable). La regresion mecanica es el propio `close_check` de esta ficha:

```
grep -q 'Xid' tasks/done/FEATURE-GPU-XID-DETECTION.md
```

que falla si el marcador de codigo desaparece de `bin/bb`. La regresion real se corrio a mano contra datos de produccion antes y despues del fix -- ver Verification Evidence.

## Verification Evidence

**pass_real**:
```
$ ./bin/bb scan '5 minutes ago' | sed -n '/Xid del driver/,/^$/p'
-- Xid del driver NVIDIA --
  eventos Xid:                 0
  nvidia-smi responde ahora:   si
(0 es la linea base real de esta maquina -- journalctl -k nunca vio un Xid historico)
```

**pass_extraccion_fixture**:
```
grep -k no permite inyectar en /dev/kmsg sin root, asi que la extraccion se probo en aislamiento contra 2 lineas reales de Xid (codigos 79 y 119, formato NVIDIA verbatim):
$ printf '...NVRM: Xid (PCI:0000:01:00): 79...\n...NVRM: Xid (PCI:0000:01:00): 119...\n...NVRM: Xid (PCI:0000:01:00): 79...\n' | grep -oE 'Xid \(PCI:[^)]*\): [0-9]+' | grep -oE '[0-9]+$' | sort | uniq -c | sort -rn
    codigo 79     x2
    codigo 119    x1
```

**fail_control_negativo_nvidia_smi**:
```
$ PATH=/tmp/fakepath_test ./bin/bb scan '5 minutes ago' | grep 'nvidia-smi responde'
  nvidia-smi responde ahora:   NO (timeout o error...)
(fakepath_test = symlinks a coreutils SIN nvidia-smi -- probar con PATH=/usr/bin:/bin fallo, porque nvidia-smi vive en /usr/bin y seguia encontrandose)
```

## Fichas HARVEST de origen (cosecha de Atlas, evaluadas 2026-09-09)

- HARVEST-374016-dgx-spark-gb10-gpu-fails-to-initialize-gsp-fi
- HARVEST-379959-gb10-spontaneous-reboots-after-july-2026-upda
- HARVEST-348223-dgx-spark-gpu-crash
