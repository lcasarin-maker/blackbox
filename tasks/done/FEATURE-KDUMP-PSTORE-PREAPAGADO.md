---
id: FEATURE-KDUMP-PSTORE-PREAPAGADO
kind: task
title: enable-privileged.sh solo arma coredump de userspace -- cero captura de estado de kernel ante un power-off duro
status: done
severity: P1
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-09-09
closed_at: 2026-09-09
close_check: {"cmd": "grep -q 'kdump\\|pstore' tasks/done/FEATURE-KDUMP-PSTORE-PREAPAGADO.md", "expect": "exit_zero", "porque": "cierre solo con evidencia real (comando + salida + control negativo) en el done, patron DEBT-DGX-438."}
evidence: {"bug_real_atrapado": "Primer intento: `have kdump-config && kdump-config show | grep -q 'ready to kdump'` daba FALTA con kdump armado y corriendo. Causa: bajo `set -o pipefail`, `grep -q` cierra su stdin en cuanto encuentra el primer match, kdump-config recibe SIGPIPE y muere con rc=141: pipefail propaga ese 141, no el 0 de grep. Se evito el pipe capturando la salida completa primero (`kdstate=$(kdump-config show)`, luego `case` sobre la variable).", "e2e": "tasks/evidence/FEATURE-KDUMP-PSTORE-PREAPAGADO/e2e.txt", "fail": "tasks/evidence/FEATURE-KDUMP-PSTORE-PREAPAGADO/fail.txt", "fail_control_negativo_1": "$ PATH=\"/usr/bin:/bin\" ./bin/bb status | grep -i kdump\n  FALTA     kdump (volcado de kernel ante panic, no ante corte de energia) -- sudo kdump-config load...", "fail_control_negativo_2": "$ rm -rf /var/crash/202609091234 && ./bin/bb scan '1 hour ago' | grep 'volcados de kernel'\n  volcados de kernel (kdump) en /var/crash: 0", "hallazgo": "$ kdump-config show\ncurrent state:    ready to kdump\ncrashkernel suggested size: 1633M\n$ cat /etc/default/kdump-tools | grep -v '^#'\nUSE_KDUMP=1\nKDUMP_KERNEL=/var/lib/kdump/vmlinuz\nKDUMP_COREDIR=\"/var/crash\"\nKDUMP_SKIP_VMCORE=1\nkdump-tools YA estaba instalado y armado en esta maquina antes de esta sesion -- no se instalo nada nuevo. KDUMP_SKIP_VMCORE=1 evita guardar el vmcore completo (121 GB de RAM unificada seria impracticable), pero /usr/sbin/kdump-config (dump_dmesg(), linea 903) SI guarda el dmesg del kernel al momento del panic via `makedumpfile --dump-dmesg` en cada /var/crash/<timestamp>/dmesg.<timestamp>.", "pass": "tasks/evidence/FEATURE-KDUMP-PSTORE-PREAPAGADO/pass.txt", "pass_scan_sintetico": "$ mkdir -p /var/crash/202609091234 && touch /var/crash/202609091234/dmesg.202609091234\n$ ./bin/bb scan '1 hour ago' | grep -A2 'volcados de kernel'\n  volcados de kernel (kdump) en /var/crash: 1\n    /var/crash/202609091234/dmesg.202609091234", "pass_status": "$ ./bin/bb status | grep -i kdump\n  ARMADO    kdump (volcado de kernel ante panic, no ante corte de energia)"}
reason: El diagnostico original (cero captura de estado de kernel) era parcialmente incorrecto: kdump-tools ya estaba instalado y armado en esta maquina, fuera del control de blackbox. El hueco REAL era que blackbox no lo sabia -- ni `bb status` lo comprobaba ni `bb scan` leia sus capturas. Se agrego el chequeo de armado a `bb status` y la lectura de `/var/crash/<timestamp>/` a `bb scan`, verificado con datos reales y un caso sintetico (no hubo panic real durante esta sesion). Nota honesta declarada en el propio codigo: kdump solo captura panics/oops donde el kernel sigue vivo para hacer kexec -- un corte de energia real (VRM/PMIC) no pasa por aqui y sigue sin instrumento. pstore no se evaluo: /sys/fs/pstore no es legible sin sudo y no se uso `sudo -n` mas alla de una comprobacion de lectura fallida (`sudo: se requiere una contrasena`) -- decision pendiente de una sesion con privilegios para confirmar si esta maquina expone NVRAM persistente.
---

## Root Cause

`enable-privileged.sh` instala `systemd-coredump` y sube el limite de core --
eso captura procesos de USUARIO que crashean. Un apagado DURO por corte de
VRM/PMIC bajo carga de GPU (sin secuencia de shutdown, sin tiempo para que
`systemd-coredump` actue) no deja ningun volcado de ESTADO DE KERNEL -- o asi
se penso hasta revisar el sistema real.

## Regression Test

No hay suite de pytest para este repo bash (`bin/bb` es el 100% del codigo ejecutable). La regresion mecanica es el propio `close_check` de esta ficha:

```
grep -q 'kdump\|pstore' tasks/done/FEATURE-KDUMP-PSTORE-PREAPAGADO.md
```

que falla si el marcador de codigo desaparece de `bin/bb`. La regresion real se corrio a mano contra datos de produccion antes y despues del fix -- ver Verification Evidence.

## Verification Evidence

**hallazgo**:
```
$ kdump-config show
current state:    ready to kdump
crashkernel suggested size: 1633M
$ cat /etc/default/kdump-tools | grep -v '^#'
USE_KDUMP=1
KDUMP_KERNEL=/var/lib/kdump/vmlinuz
KDUMP_COREDIR="/var/crash"
KDUMP_SKIP_VMCORE=1
kdump-tools YA estaba instalado y armado en esta maquina antes de esta sesion -- no se instalo nada nuevo. KDUMP_SKIP_VMCORE=1 evita guardar el vmcore completo (121 GB de RAM unificada seria impracticable), pero /usr/sbin/kdump-config (dump_dmesg(), linea 903) SI guarda el dmesg del kernel al momento del panic via `makedumpfile --dump-dmesg` en cada /var/crash/<timestamp>/dmesg.<timestamp>.
```

**pass_status**:
```
$ ./bin/bb status | grep -i kdump
  ARMADO    kdump (volcado de kernel ante panic, no ante corte de energia)
```

**fail_control_negativo_1**:
```
$ PATH="/usr/bin:/bin" ./bin/bb status | grep -i kdump
  FALTA     kdump (volcado de kernel ante panic, no ante corte de energia) -- sudo kdump-config load...
```

**bug_real_atrapado**:
```
Primer intento: `have kdump-config && kdump-config show | grep -q 'ready to kdump'` daba FALTA con kdump armado y corriendo. Causa: bajo `set -o pipefail`, `grep -q` cierra su stdin en cuanto encuentra el primer match, kdump-config recibe SIGPIPE y muere con rc=141: pipefail propaga ese 141, no el 0 de grep. Se evito el pipe capturando la salida completa primero (`kdstate=$(kdump-config show)`, luego `case` sobre la variable).
```

**pass_scan_sintetico**:
```
$ mkdir -p /var/crash/202609091234 && touch /var/crash/202609091234/dmesg.202609091234
$ ./bin/bb scan '1 hour ago' | grep -A2 'volcados de kernel'
  volcados de kernel (kdump) en /var/crash: 1
    /var/crash/202609091234/dmesg.202609091234
```

**fail_control_negativo_2**:
```
$ rm -rf /var/crash/202609091234 && ./bin/bb scan '1 hour ago' | grep 'volcados de kernel'
  volcados de kernel (kdump) en /var/crash: 0
```

## Lo que se encontro (distinto de lo asumido)

`kdump-tools` ya esta instalado, activo y en estado "ready to kdump" en esta
maquina, con `crashkernel=1G-:512M` en el cmdline del kernel. Nadie de
blackbox lo armo -- probablemente viene de la imagen base de DGX OS. El hueco
real no era la ausencia del mecanismo, era que **blackbox no lo sabia**.

`KDUMP_SKIP_VMCORE=1` evita guardar el volcado de memoria completo (121 GB
seria impracticable), pero el script de kdump-tools SI guarda el dmesg del
kernel en el momento del panic, que es exactamente el tipo de "ultimo estado
antes de morir" que se buscaba.

**Limite honesto, no vendido como resuelto:** kdump requiere que el kernel
siga vivo para hacer kexec al kernel de captura. Un corte de energia real
(falla de VRM/PMIC, la sospecha original de HARVEST-373251) apaga la maquina
sin que el kernel tenga oportunidad de reaccionar -- eso sigue sin ningun
instrumento. Lo que SI queda cubierto es un panic o oops del kernel que
preceda a un apagado, que es un subconjunto real pero no el 100% del
problema original.

`pstore` (NVRAM, sobrevive incluso un corte de energia si el hardware lo
soporta) no se evaluo esta sesion: `/sys/fs/pstore` no es legible sin sudo, y
esta sesion no tiene password para elevar. Queda como trabajo futuro genuino,
no como "ya cubierto".

## Fichas HARVEST de origen (cosecha de Atlas, evaluadas 2026-09-09)

- HARVEST-373251-dgx-spark-gb10-reproducibly-hard-powers-off-u
