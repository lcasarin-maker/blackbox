---
id: FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01
kind: task
domain: GPU
title: "Backport reversible de memacct (dmem) a los modulos abiertos 580.178.04, con la misma version de driver"
status: open
severity: P2
origin: asserted
satd_family: BLIND_INSTRUMENT
created: 2026-10-12
close_check: {"cmd": "grep -q memacct_backport_probado tasks/evidence/FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01/medicion.txt", "expect": "exit_zero", "porque": "Voto de Luis 2026-10-12: probar de forma reversible si el driver puede registrar y contabilizar memoria GPU/UMA en dmem. Cierra con una medicion en esta maquina: region en dmem.capacity, un cgroup con dmem.max y la carga CUDA contabilizada (o la prueba medida de que GB10 no pasa por esa ruta), con control negativo y la reversion verificada."}
---

## Por que este camino y no subir a 615
- Subir a 615 SI afecta lo actual: el modulo y las librerias de usuario deben coincidir (hoy `libnvidia-*-580 580.178.04-0ubuntu0.24.04.1` y modulos abiertos `nvidia-580-open` de Canonical); DGX OS fija 580 con `dgx-spark-ota-update-meta`; no se sabe si el contenedor de vLLM (v0.27.1) funciona con userspace 615. No reversible limpio (disco ext4 sin instantaneas).
- Un backport con la MISMA version 580.178.04 deja intactas las librerias de usuario y vLLM.
## Medido hoy (2026-10-12)
- Modulo actual: `/lib/modules/6.17.0-1032-nvidia/kernel/nvidia-580-open/nvidia.ko`, firmado por `Canonical Ltd. Kernel Module Signing`; sin DKMS; Secure Boot activo; hay `gcc 13.3`, `make 4.3` y `linux-headers-6.17.0-1032-nvidia`.
- Divergencia 580.178.04 -> 610.43.02 en los archivos que toca `memacct`: `video_mem.c` 43 lineas distintas de 1629/1652; `mem_mgr.c` 155 de 4231/4240; `os.c` 682 de 5961/6293; `os-interface.c` 251 de 2740/2909. `memacct.c` y `memacct.h` son nuevos (404 en 580). Los enganches en `video_mem.c` son pocos (`memacctTryCharge` en la asignacion y `memacctReleaseCharge` en la liberacion).
## Plan por partes
1. Compilar los modulos 580.178.04 SIN cambios desde el tag y comprobar que reproducen los del paquete (control).
2. Aplicar el backport de memacct a una copia; compilar.
3. Firmar: requiere una llave de confianza. Hoy solo confia en Canonical; la llave propia de `/var/lib/shim-signed/mok` no consta como enrolada (`mokutil --test-key` no pudo consultarlo). Enrolarla exige `sudo mokutil --import` y confirmar en el arranque con contrasena en la consola fisica: es un cambio de confianza de Secure Boot, reversible con `mokutil --delete`. DECISION DE LUIS.
4. Instalar en `/lib/modules/6.17.0-1032-nvidia/updates/` (gana a `kernel/`), `depmod -a` y reiniciar (no se puede `rmmod` en vivo: vLLM y el escritorio usan el modulo).
5. Medir; revertir: borrar `updates/*.ko`, `depmod -a`, reiniciar; opcional `mokutil --delete`.
## Riesgos declarados
Si el modulo falla al cargar no hay GPU ni pantalla hasta revertir (queda SSH). Hacerlo con ventana acordada y la reversion preescrita. Incognita que decide todo: si las asignaciones CUDA de GB10 pasan por `video_mem.c` y si `memmgrGetTotalRamSizeBytes` != 0 (si es 0 la region se ignora).
