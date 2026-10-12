#!/usr/bin/env bash
# dmem_reconstruye.sh -- el reparador: vuelve a hacer el modulo NVIDIA parcheado (memacct + zero-FB) para un kernel o driver nuevo.
# Decision de Luis 2026-10-12: no se bloquean las actualizaciones; `tools/dmem_monitor.py` avisa y este script reconstruye.
#
#   bash tools/dmem_reconstruye.sh [kernel=$(uname -r)] [driver=<version del modulo de Canonical>] [--seco]
#
# Sin root: baja el tag de NVIDIA (o BB_DMEM_FUENTE=<repo local>), aplica data/dmem/memacct-580.patch con `git apply --check`
# primero, compila bajo systemd-run (MemoryMax 8G, sin swap), y deja los .ko SIN FIRMAR en
# ~/.local/share/blackbox/dmem/construidos/<driver>-<kernel>/ con sus sha256. NO instala ni reinicia: imprime los comandos
# con sudo (firma + instala), porque eso cambia el arranque y es decision de quien lo corre.
# --seco: solo comprueba que el parche aplica al tag (rc 0 aplica, rc 4 NO aplica); no compila.
# rc: 0 ok, 3 falta algo (headers, tag, git), 4 el parche NO aplica a ese driver (hay que portarlo de nuevo), 5 compilo mal o el .ko no verifica.
set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PARCHE=${BB_DMEM_PARCHE:-$REPO/data/dmem/memacct-580.patch}
SECO=0; ARGS=()
for a in "$@"; do [ "$a" = "--seco" ] && SECO=1 || ARGS+=("$a"); done
KERNEL=${ARGS[0]:-$(uname -r)}
DRIVER=${ARGS[1]:-$(modinfo -F version "/lib/modules/$KERNEL/kernel/nvidia-580-open/nvidia.ko" 2>/dev/null || true)}
FUENTE=${BB_DMEM_FUENTE:-https://github.com/NVIDIA/open-gpu-kernel-modules}
CACHE=${BB_DMEM_CACHE:-$HOME/.cache/bb-dmem}
DATOS=${BLACKBOX_DATA:-$HOME/.local/share/blackbox}
MODS=(nvidia nvidia-modeset nvidia-uvm nvidia-drm nvidia-peermem)
log() { echo "[dmem-reconstruye] $*"; }
fallo() { local rc=$1; shift; echo "[dmem-reconstruye] ERROR: $*" >&2; exit "$rc"; }

[ -n "$DRIVER" ] || fallo 3 "no pude leer la version del driver (modulo de Canonical de $KERNEL ausente); pasala como segundo argumento"
[ -f "$PARCHE" ] || fallo 3 "falta el parche $PARCHE"
mkdir -p "$CACHE"
SRC=$CACHE/nv-$DRIVER-$$
trap 'rm -rf "$SRC"' EXIT
git clone -q --depth 1 --branch "$DRIVER" "$FUENTE" "$SRC" 2>/dev/null || fallo 3 "no pude obtener el tag $DRIVER de $FUENTE"
cd "$SRC"
git apply --check "$PARCHE" 2>"$CACHE/apply-$DRIVER.err" || { head -5 "$CACHE/apply-$DRIVER.err" >&2; fallo 4 "el parche NO aplica a $DRIVER: hay que portarlo de nuevo (detalle en $CACHE/apply-$DRIVER.err)"; }
log "el parche aplica a $DRIVER"
[ "$SECO" = 1 ] && { log "--seco: no se compila"; exit 0; }

[ -d "/lib/modules/$KERNEL/build" ] || fallo 3 "faltan los headers de $KERNEL (/lib/modules/$KERNEL/build)"
git apply "$PARCHE"
log "compilando bajo systemd-run (MemoryMax 8G, sin swap)..."
systemd-run --user --scope -q -p MemoryMax=8G -p MemorySwapMax=0 -p TasksMax=2000 nice -n 10 -- \
    make modules -j4 SYSSRC="/lib/modules/$KERNEL/build" >"$CACHE/build-$DRIVER-$KERNEL.log" 2>&1 || fallo 5 "make fallo; ultimas lineas en $CACHE/build-$DRIVER-$KERNEL.log"
OUT=$DATOS/dmem/construidos/$DRIVER-$KERNEL
mkdir -p "$OUT"
for m in "${MODS[@]}"; do
    f=kernel-open/$m.ko
    [ -f "$f" ] || fallo 5 "falta $f tras compilar"
    modinfo -F vermagic "$f" | grep -q "^$KERNEL" || fallo 5 "$m: vermagic no es $KERNEL"
    [ "$(modinfo -F version "$f")" = "$DRIVER" ] || fallo 5 "$m: version no es $DRIVER"
    cp "$f" "$OUT/$m.ko"
done
nm "$OUT/nvidia.ko" | grep -q "dmem_cgroup_try_charge" || fallo 5 "nvidia.ko no importa dmem_cgroup_try_charge: el parche no quedo en el modulo"
( cd "$OUT" && sha256sum ./*.ko >SHA256SUMS )
log "listo: $OUT (sin firmar)"
log "para instalarlo (cambia el arranque; hazlo con la consola a mano):"
log "  sudo bash tools/dmem_modulo.sh retrocede   # si hay una instalacion previa"
log "  sudo bash tools/dmem_modulo.sh firma $OUT && sudo bash tools/dmem_modulo.sh instala"
