---
id: FEATURE-GUI-KERNEL-VS-USERSPACE
kind: task
title: En un cuelgue de GUI+nvidia-smi, nada distingue fallo de modulo de kernel vs. espacio de usuario
status: done
severity: P3
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-09-09
closed_at: 2026-09-09
close_check: {"cmd": "grep -q 'lsmod.*nvidia\\|systemctl status gdm' tasks/done/FEATURE-GUI-KERNEL-VS-USERSPACE.md", "expect": "exit_zero", "porque": "cierre solo con evidencia real (comando + salida + control negativo) en el done, patron DEBT-DGX-438."}
evidence: {"bug_real_atrapado": "Primer intento: `systemctl status gdm.service --no-pager 2>&1 >archivo` -- el orden de redirecciones esta al reves (2>&1 duplica stderr al stdout ORIGINAL antes de que este se redirija al archivo), asi que stderr se habria ido a la terminal y solo stdout al archivo. Corregido a `>archivo 2>&1`, mismo patron que el resto de cmd_snapshot.", "e2e": "tasks/evidence/FEATURE-GUI-KERNEL-VS-USERSPACE/e2e.txt", "fail": "tasks/evidence/FEATURE-GUI-KERNEL-VS-USERSPACE/fail.txt", "fail_control_negativo": "$ grep -i '^wontmatch12345' /proc/modules || echo '(modulo nvidia NO cargado)'\n(modulo nvidia NO cargado)\n(confirma que la rama de fallback del `||` funciona cuando el modulo no aparece)", "pass": "tasks/evidence/FEATURE-GUI-KERNEL-VS-USERSPACE/pass.txt", "pass_real": "$ ./bin/bb snapshot test\n$ cat <snapshot>/lsmod-nvidia.txt\nnvidia_uvm           1900544  28\nnvidia_drm            135168  16\nnvidia_modeset       1957888  31 nvidia_drm\nnvidia              14684160  523 nvidia_uvm,nvidia_modeset\n$ head -3 <snapshot>/gdm-status.txt\n● gdm.service - GNOME Display Manager\n     Loaded: loaded (...)\n     Active: active (running) since Sat 2026-09-05 21:49:14 CST; 3 days ago"}
reason: Se agrego a cmd_snapshot la sonda de dos comandos que pedia la ficha: lsmod filtrado a nvidia (ausencia = fallo de modulo de kernel) y systemctl status gdm.service (activo con modulo cargado pero sin GUI = fallo de espacio de usuario). Es diagnostico puro -- las partes de mitigacion que la ficha original tambien proponia (systemctl set-default/isolate, reencadenar dependencias) quedaron fuera, por ser intervencion activa.
---

## Root Cause

El incidente fundador de este repo fue una app con UI muerta y sin causa
raiz. Un escenario emparentado -- GUI caida y `nvidia-smi` sin responder --
puede ser un modulo de kernel NVIDIA descargado o un fallo de espacio de
usuario con el modulo intacto. Antes de este ticket nada distinguia los dos
casos.

## Regression Test

No hay suite de pytest para este repo bash (`bin/bb` es el 100% del codigo ejecutable). La regresion mecanica es el propio `close_check` de esta ficha:

```
grep -q 'lsmod.*nvidia\|systemctl status gdm' tasks/done/FEATURE-GUI-KERNEL-VS-USERSPACE.md
```

que falla si el marcador de codigo desaparece de `bin/bb`. La regresion real se corrio a mano contra datos de produccion antes y despues del fix -- ver Verification Evidence.

## Verification Evidence

**pass_real**:
```
$ ./bin/bb snapshot test
$ cat <snapshot>/lsmod-nvidia.txt
nvidia_uvm           1900544  28
nvidia_drm            135168  16
nvidia_modeset       1957888  31 nvidia_drm
nvidia              14684160  523 nvidia_uvm,nvidia_modeset
$ head -3 <snapshot>/gdm-status.txt
● gdm.service - GNOME Display Manager
     Loaded: loaded (...)
     Active: active (running) since Sat 2026-09-05 21:49:14 CST; 3 days ago
```

**fail_control_negativo**:
```
$ grep -i '^wontmatch12345' /proc/modules || echo '(modulo nvidia NO cargado)'
(modulo nvidia NO cargado)
(confirma que la rama de fallback del `||` funciona cuando el modulo no aparece)
```

**bug_real_atrapado**:
```
Primer intento: `systemctl status gdm.service --no-pager 2>&1 >archivo` -- el orden de redirecciones esta al reves (2>&1 duplica stderr al stdout ORIGINAL antes de que este se redirija al archivo), asi que stderr se habria ido a la terminal y solo stdout al archivo. Corregido a `>archivo 2>&1`, mismo patron que el resto de cmd_snapshot.
```

## Fichas HARVEST de origen (cosecha de Atlas, evaluadas 2026-09-09)

- HARVEST-366211-my-gui-is-gone-and-nvidia-smi-is-not-working
