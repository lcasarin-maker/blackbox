#!/usr/bin/env bash
# dmem_modulo.sh -- instala, mide y RETROCEDE el modulo NVIDIA 580.178.04 con memacct portado
# (FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01). Lo corre Luis con sudo y la consola a mano.
#
#   sudo bash tools/dmem_modulo.sh estado                 # que hay hoy; no cambia nada
#   sudo bash tools/dmem_modulo.sh enrolar                # mokutil --import de la llave existente (pide contrasena de un uso)
#   sudo bash tools/dmem_modulo.sh firma  <dir-con-.ko>   # firma los 5 modulos con la llave MOK
#   sudo bash tools/dmem_modulo.sh instala                # copia a updates/ + depmod + unidad guardia; NO descarga ni reinicia
#   (reiniciar a mano)
#   sudo bash tools/dmem_modulo.sh verifica               # tras el arranque: que modulo corre y si dmem tiene region
#   sudo bash tools/dmem_modulo.sh retrocede              # quita updates/, depmod: el siguiente arranque usa el de Canonical
#
# Seguridad: nada descarga modulos en marcha (vLLM y la pantalla siguen). El retroceso es borrar archivos que ESTE
# script copio (lista en $ESTADO/instalados.txt con sha256) y correr depmod. Si tras el arranque la GPU no responde,
# `bb-dmem-guardia.service` retrocede solo (sin reiniciar) y deja `$ESTADO/retrocedido`; si ni el SSH sube, desde la
# consola fisica: `sudo bash tools/dmem_modulo.sh retrocede && sudo reboot`.
set -euo pipefail

MODDIR=${BB_DMEM_MODDIR:-/lib/modules/$(uname -r)}
ESTADO=${BB_DMEM_ESTADO:-/var/lib/bb-dmem}
LLAVE_PRIV=${BB_DMEM_LLAVE_PRIV:-/var/lib/shim-signed/mok/MOK.priv}
LLAVE_PUB=${BB_DMEM_LLAVE_PUB:-/var/lib/shim-signed/mok/MOK.der}
SIGN=${BB_DMEM_SIGN:-/usr/src/linux-headers-$(uname -r)/scripts/sign-file}
DEPMOD=${BB_DMEM_DEPMOD:-depmod}
MODS=(nvidia nvidia-modeset nvidia-uvm nvidia-drm nvidia-peermem)
VER_ESPERADA=580.178.04
UNIDAD=/etc/systemd/system/bb-dmem-guardia.service

log() { echo "[dmem] $*"; }
die() { echo "[dmem] ERROR: $*" >&2; exit 1; }
raiz() { [ "$(id -u)" = 0 ] || [ -n "${BB_DMEM_SIN_RAIZ:-}" ] || die "necesita root: sudo bash $0 $1"; }

cmd_estado() {
    log "kernel: $(uname -r); Secure Boot: $(mokutil --sb-state 2>&1 | head -1)"
    log "llave $LLAVE_PUB: $(mokutil --test-key "$LLAVE_PUB" 2>&1 | tail -1)"
    log "modulo cargado: $(cat /sys/module/nvidia/version 2>/dev/null || echo ninguno), srcversion $(cat /sys/module/nvidia/srcversion 2>/dev/null || echo ?)"
    log "dmem.capacity: $(cat /sys/fs/cgroup/dmem.capacity 2>/dev/null | head -3 | tr '\n' ' ')(vacio = sin region)"
    if [ -f "$ESTADO/instalados.txt" ]; then log "instalados por este script:"; cat "$ESTADO/instalados.txt"; else log "nada instalado por este script"; fi
}

cmd_enrolar() {
    raiz enrolar
    [ -f "$LLAVE_PUB" ] || die "no existe $LLAVE_PUB"
    if mokutil --test-key "$LLAVE_PUB" 2>&1 | grep -q "is already enrolled"; then log "la llave ya esta enrolada"; return 0; fi
    log "mokutil pedira una contrasena de UN USO; en el proximo arranque aparece la pantalla azul MOK Manager:"
    log "Enroll MOK -> Continue -> Yes -> escribir esa contrasena -> Reboot. Hace falta teclado y pantalla fisicos."
    mokutil --import "$LLAVE_PUB"
}

cmd_firma() {
    raiz firma
    local src=${1:?uso: firma <directorio con los .ko>} m f
    [ -x "$SIGN" ] || die "falta $SIGN"
    [ -r "$LLAVE_PRIV" ] || die "no puedo leer $LLAVE_PRIV (root)"
    mkdir -p "$ESTADO/firmados"
    for m in "${MODS[@]}"; do
        f="$src/$m.ko"; [ -f "$f" ] || die "falta $f"
        modinfo "$f" | grep -q "^vermagic:.*$(uname -r)" || die "$f no es para $(uname -r)"
        modinfo "$f" | grep -q "^version:.*$VER_ESPERADA" || die "$f no es la version $VER_ESPERADA"
        cp "$f" "$ESTADO/firmados/$m.ko"
        "$SIGN" sha256 "$LLAVE_PRIV" "$LLAVE_PUB" "$ESTADO/firmados/$m.ko"
        modinfo "$ESTADO/firmados/$m.ko" | grep -q "^sig_key:" || die "$m no quedo firmado"
        log "firmado $m"
    done
}

cmd_instala() {
    raiz instala
    local m
    [ -d "$ESTADO/firmados" ] || die "primero: firma <dir>"
    if [ -n "${BB_DMEM_SIN_RAIZ:-}" ]; then log "(prueba) se omite la comprobacion de la llave enrolada"
    else mokutil --test-key "$LLAVE_PUB" 2>&1 | grep -q "is already enrolled" || die "la llave NO esta enrolada: el kernel rechazaria los modulos y la GPU no subiria. Primero: enrolar y reiniciar"; fi
    mkdir -p "$MODDIR/updates" "$ESTADO"
    [ ! -f "$ESTADO/instalados.txt" ] || die "ya hay una instalacion (retrocede primero)"
    : >"$ESTADO/instalados.txt"
    for m in "${MODS[@]}"; do
        cp "$ESTADO/firmados/$m.ko" "$MODDIR/updates/$m.ko"
        echo "$(sha256sum "$MODDIR/updates/$m.ko" | cut -d' ' -f1)  $MODDIR/updates/$m.ko" >>"$ESTADO/instalados.txt"
    done
    $DEPMOD -a "$(basename "$MODDIR")"
    rm -f "$ESTADO/retrocedido"
    if [ -z "${BB_DMEM_SIN_RAIZ:-}" ]; then
        cat >"$UNIDAD" <<UNIT
[Unit]
Description=bb: retrocede el modulo NVIDIA parcheado si la GPU no responde tras el arranque
After=multi-user.target
[Service]
Type=oneshot
ExecStart=/bin/bash $(readlink -f "${BASH_SOURCE[0]}") guardia
[Install]
WantedBy=multi-user.target
UNIT
        systemctl daemon-reload && systemctl enable bb-dmem-guardia.service
    fi
    log "instalado en $MODDIR/updates; NO se descargo nada. Reinicia cuando tengas la consola a mano."
}

cmd_guardia() {
    raiz guardia
    local i
    for i in $(seq 1 24); do nvidia-smi -L >/dev/null 2>&1 && { log "la GPU responde; el modulo parcheado se queda"; return 0; }; sleep 5; done  # blocking-sleep: espera acotada de arranque, 24 x 5 s -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01  # sunset-reviewed: 2.8 -- revalidado 2026-10-12: unidad de arranque de una sola pasada
    log "la GPU NO respondio en 120 s: retrocedo"
    cmd_retrocede
    touch "$ESTADO/retrocedido"
}

cmd_verifica() {
    local cargado=${1:-/sys/module/nvidia}
    log "version cargada: $(cat "$cargado/version" 2>/dev/null || echo ninguna)"
    log "modulo en uso: $(modinfo -F filename nvidia 2>/dev/null)"
    log "firmante: $(modinfo -F signer nvidia 2>/dev/null | head -1)"
    log "dmem.capacity: [$(cat /sys/fs/cgroup/dmem.capacity 2>/dev/null | tr '\n' ';')]"
    dmesg 2>/dev/null | grep -iE "memacct|dmem" | tail -5 | sed 's/^/[dmem] dmesg: /' || true
    grep -q . /sys/fs/cgroup/dmem.capacity 2>/dev/null && log "RESULTADO: HAY region dmem" || log "RESULTADO: dmem.capacity VACIO (el parche no dio region, o el modulo en uso es el de Canonical)"
}

cmd_retrocede() {
    raiz retrocede
    local f h restos=0
    [ -f "$ESTADO/instalados.txt" ] || { log "nada que retroceder"; return 0; }
    : >"$ESTADO/instalados.restos"
    while read -r h f; do
        [ -f "$f" ] || continue
        if [ "$(sha256sum "$f" | cut -d' ' -f1)" = "$h" ]; then rm -f "$f"; log "quitado $f"
        else log "ATENCION: $f cambio desde la instalacion; NO se borra y SEGUIRA cargandose"; echo "$h  $f" >>"$ESTADO/instalados.restos"; restos=1; fi
    done <"$ESTADO/instalados.txt"
    rmdir "$MODDIR/updates" 2>/dev/null || true
    $DEPMOD -a "$(basename "$MODDIR")"
    if [ "$restos" = 1 ]; then
        mv "$ESTADO/instalados.restos" "$ESTADO/instalados.txt"
        die "retroceso INCOMPLETO: quedan archivos alterados en $MODDIR/updates (lista en $ESTADO/instalados.txt); borralos a mano y corre depmod -a"
    fi
    rm -f "$ESTADO/instalados.txt" "$ESTADO/instalados.restos"
    [ -n "${BB_DMEM_SIN_RAIZ:-}" ] || { systemctl disable bb-dmem-guardia.service 2>/dev/null || true; rm -f "$UNIDAD"; }
    log "retrocedido: el siguiente arranque usa los modulos de Canonical"
}

case "${1:-}" in
    estado) cmd_estado ;; enrolar) cmd_enrolar ;; firma) shift; cmd_firma "$@" ;; instala) cmd_instala ;;
    guardia) cmd_guardia ;; verifica) shift; cmd_verifica "$@" ;; retrocede) cmd_retrocede ;;
    *) sed -n 2,16p "$0"; exit 2 ;;
esac
