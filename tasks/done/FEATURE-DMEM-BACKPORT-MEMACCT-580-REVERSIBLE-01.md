---
id: FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01
kind: task
domain: GPU
title: "Backport reversible de memacct (dmem) a los modulos abiertos 580.178.04, con la misma version de driver"
status: done
closed_at: 2026-10-12
closure_type: fixed
reason: "Backport de memacct a 580.178.04 cargado (firmado con la MOK) y medido: region en dmem.capacity y carga CUDA contabilizada; reversible con tools/dmem_modulo.sh retrocede."
evidence: {"pass": "tasks/evidence/FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01.pass.txt", "fail": "tasks/evidence/FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01.fail.txt", "e2e": "tasks/evidence/FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01.e2e.txt"}
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

## Que afectaria subir de rama (simulacion de apt, sin root, 2026-10-12)
Comandos: `apt-get -s install nvidia-driver-610-open linux-modules-nvidia-610-open-6.17.0-1032-nvidia` y la variante con paquetes 610 explicitos. Resultados literales: la primera da `22 nuevos se instalaran, 17 para eliminar`; la segunda `24 nuevos, 16 para eliminar`.
- **Quita toda la rama 580:** `libnvidia-compute-580` (libcuda), `nvidia-utils-580`, `libnvidia-gl-580`, `nvidia-driver-580-open` y los modulos `linux-modules-nvidia-580-open-6.17.0-1032-nvidia` y `-7.0.0-1019-nvidia`.
- **La rama 610 no es instalable limpia por apt:** el meta `nvidia-driver-610-open` depende de `nvidia-driver-615-open`, y aun con paquetes 610 explicitos apt trae las bibliotecas 615 (`libnvidia-compute-615`, `libnvidia-gl-615`...). Resultado: modulos 610 (firmados por Canonical, 610.x) con bibliotecas de usuario 615.71.09: versiones distintas entre modulo y biblioteca.
- **615 no tiene modulos firmados para nuestro kernel:** `apt-cache search` solo lista `linux-modules-nvidia-{580,595,610}-open-6.17.0-1032-nvidia`; los de 615 son para kernels 6.8 (aws, gke, oracle, nvidia 6.8.0-1064). Para 615 en 6.17 quedaria `nvidia-dkms-615-open` (DKMS no instalado) y una llave MOK enrolada para Secure Boot.
- **El contenedor de vLLM** usa `runtime=nvidia`: recibe del host las bibliotecas `libcuda.so.<version>`; hoy `libcuda.so.580.178.04`. Con 615 correria sobre bibliotecas distintas (no probado con la imagen vllm v0.27.1).
- **Retroceso:** no hay instantaneas (ext4 en `/dev/nvme0n1p2`). `libnvidia-compute-580 580.178.04-0ubuntu0.24.04.1` aun se sirve desde noble-updates y noble-security y hay 2 .deb de NVIDIA en la cache de apt: reinstalarlo es probable, no garantizado a futuro.
- **Herramientas propias que leen `nvidia-smi` y los mensajes NVRM** (muestreador, freno termico que consulta Atlas, firmas) podrian cambiar de formato: no medido.
- **DGX OS:** repos `nvidia-dgx` y `nvidia-spark-repo` y `dgx-spark-ota-update-meta` presentes: una actualizacion OTA podria reimponer 580; no medido.
Conclusion: por apt NO hay una subida limpia ni reversible garantizada; el backport con la MISMA version 580.178.04 evita el cambio de bibliotecas y de contenedor, a costa de enrolar una llave MOK (reversible con `mokutil --delete`).

## Medicion previa al backport (2026-10-12, voto "medir primero")

Medido en esta maquina (driver 580.178.04), sin tocar el driver:
- `nvidia-smi -q -d MEMORY`: `FB Memory Usage Total/Reserved/Used/Free = N/A` y `BAR1 = N/A`. GB10 no declara framebuffer dedicado.
- `nvidia-smi --query-compute-apps` de un proceso torch: 196 MiB -> 2244 MiB tras 2 GiB -> 4292 MiB tras 4 GiB -> 194 MiB al liberar. El driver contabiliza por proceso, pero eso es otra via (RM por cliente), no la de memacct.

Leido en el codigo 615 (`src/nvidia/src/kernel/mem_mgr/`):
- `memacct.c`: la region se crea con `memmgrGetTotalRamSizeBytes(...)` y si es 0 hace `region %llx zero size, ignoring` y retorna sin registrar.
- `video_mem.c:621-629`: `memacctTryCharge` solo corre si el atributo es `NVOS32_ATTR_LOCATION_VIDMEM`.

Inferencia (no probada): con FB total N/A, el tamano de la region puede ser 0 y memacct no registrar nada; y si las asignaciones de GB10 son de sysmem, tampoco pasan por `video_mem.c`. En ese caso el backport es esfuerzo sin efecto. Lo que lo confirmaria o refutaria: cargar el modulo 615 en un entorno aislado con `LEVEL_INFO` y leer `/sys/fs/cgroup/dmem.capacity` (exige modulos propios, es decir MOK) o encontrar en 615 la salida de `memmgrGetTotalRamSizeBytes` para GB10 (no leido todavia).
Estado: el backport queda condicionado; no se pide la llave MOK hasta leer esa funcion para chip GB10.

### Lectura decisiva del codigo 615 (2026-10-12, misma sesion)
- `g_gpu_arch_nvoc.c:113-120`: `bGpuArchIsZeroFb = true` para `ChipHal: GB10B | GB10C | GB20B | GB20C`.
- `mem_mgr.c:4178-4190`: si `bGpuArchIsZeroFb`, `memmgrGetTotalRamSizeBytes` devuelve 0 ("[zero-FB, No local RAM] TOTAL_RAM_SIZE = 0").
- `memacct.c:455-462`: con tamano 0, "region zero size, ignoring" y no se registra region en dmem.
Conclusion de lectura: en una GB10 de ese HAL, `memacct` no crea region y `dmem.capacity` seguiria vacio; el backport no daria limite alguno. Consistente con `nvidia-smi` FB = N/A.
Lo que NO esta cerrado: que ESTE chip sea GB10B/GB10C no se puede leer desde el espacio de usuario (`Model: Unknown`; PCI 10de:2e12 no esta en una tabla del codigo; el HAL sale de un registro). Estado: fuerte indicio de que la ficha y FEATURE-DMEM-BOOSTERS-ADAPTAR-A-GB10-01 no tienen objeto en esta maquina; no se cierran hasta confirmar el HAL con el modulo cargado (exige modulos propios) o con una version de NVIDIA que cambie GB10 a FB no cero. No se pide la llave MOK.

### Origen de la llave MOK existente (investigado 2026-10-12, pregunta de Luis)
`/var/lib/shim-signed/mok/MOK.der|priv` se crearon el 2026-09-12 00:44:07, 14 s despues de `apt-get -y install doca-ofed` (00:43:51, usuario lcasarin), que arrastro el paquete `dkms` 1:3.4.3 (instalado 00:43:53). Con Secure Boot activo, el paquete genera una llave de firma de modulos (CN "<host> Secure Boot Module Signature key", Code Signing, valida hasta 2126). La instalacion fue `-y` (sin preguntas), asi que nunca se enrolo. `/var/log/apt/term.log` muestra a DKMS firmando con ella los modulos DOCA/OFED (`mlnx-ofed-kernel-dkms`, `xpmem-dkms`, `isert-dkms`...). Esos modulos no cargaban sin enrolar. A las 08:29 `apt-get -f install` y a las 08:34 `apt-get purge doca-ofed ... mlnx-ofed-kernel-dkms ...` retiraron todo; `dkms` quedo en estado `rc` (config residual). Hoy `/var/lib/dkms` no existe, no hay modulos DKMS instalados, y la llave sobrevivio sin uso. Enrolada hoy: solo la CA de Canonical. Conclusion: reutilizable sin crear otra; el enrolamiento sigue pendiente de la decision de Luis.

## Root Cause
El driver 580.178.04 no trae memacct (llega con 610); sin el, dmem.capacity esta vacio y ningun cgroup paga por la memoria de GPU.

## Regression Test
tests/test_dmem_parche_contrato.py (el parche conserva el cobro, la liberacion y la traduccion del limite) y tools/dmem_modulo.sh retrocede para la reversion.

## Verification Evidence
Las tres rutas de evidencia del frontmatter: `tasks/evidence/FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01.fail.txt` (el close_check fallaba antes), `.pass.txt` (pasa despues) y `.e2e.txt` (sujeto vivo: dmem.capacity, `bb gpumem` contra `nvidia-smi`). Medicion literal en `tasks/evidence/FEATURE-DMEM-BACKPORT-MEMACCT-580-REVERSIBLE-01/medicion.txt`.
