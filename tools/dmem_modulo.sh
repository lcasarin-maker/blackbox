#!/usr/bin/env bash
# dmem_modulo.sh -- instala, mide y RETROCEDE el modulo NVIDIA 580.178.04 con memacct portado
# (FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01). Lo corre Luis con sudo y la consola a mano.
#
#   sudo bash tools/dmem_modulo.sh estado [--kernel V]    # que hay hoy (en V, por defecto el kernel en marcha); no cambia nada
#   sudo bash tools/dmem_modulo.sh enrolar                # mokutil --import de la llave existente (pide contrasena de un uso)
#   sudo bash tools/dmem_modulo.sh firma  <dir-con-.ko>   # firma los 5 modulos con la llave MOK
#   sudo bash tools/dmem_modulo.sh instala                # copia a updates/ + depmod + unidad guardia; NO descarga ni reinicia
#   (reiniciar a mano)
#   sudo bash tools/dmem_modulo.sh verifica               # tras el arranque: que modulo corre y si dmem tiene region
#   sudo bash tools/dmem_modulo.sh retrocede [--kernel V] # quita updates/ de V (defecto: uname -r), depmod -a V: V arranca con el de Canonical
#   (--kernel: desde OTRO kernel, p. ej. el de rescate en GRUB, actua sobre V y no sobre el que corre; sin updates/ en V sale 0 sin tocar nada)
#
# Seguridad: nada descarga modulos en marcha (vLLM y la pantalla siguen). El retroceso es borrar archivos que ESTE
# script copio (lista en $ESTADO/instalados.txt con sha256) y correr depmod. Si tras el arranque la GPU no responde,
# `bb-dmem-guardia.service` retrocede solo (sin reiniciar) y deja `$ESTADO/retrocedido`; si ni el SSH sube, desde la
# consola fisica: `sudo bash tools/dmem_modulo.sh retrocede && sudo reboot` (o, arrancado en otro kernel,
# `retrocede --kernel <el parchado>`). La guardia anota su decision como etapa de arranque (adopted/system-units/).
set -euo pipefail

MODROOT=${BB_DMEM_MODROOT:-/lib/modules}
MODDIR=${BB_DMEM_MODDIR:-$MODROOT/$(uname -r)}
ESTADO=${BB_DMEM_ESTADO:-/var/lib/bb-dmem}
LLAVE_PRIV=${BB_DMEM_LLAVE_PRIV:-/var/lib/shim-signed/mok/MOK.priv}
LLAVE_PUB=${BB_DMEM_LLAVE_PUB:-/var/lib/shim-signed/mok/MOK.der}
SIGN=${BB_DMEM_SIGN:-/usr/src/linux-headers-$(uname -r)/scripts/sign-file}
DEPMOD=${BB_DMEM_DEPMOD:-depmod}
MODS=(nvidia nvidia-modeset nvidia-uvm nvidia-drm nvidia-peermem)
VER_ESPERADA=580.178.04
UNIDAD=/etc/systemd/system/bb-dmem-guardia.service
NVSMI_TIMEOUT=${BB_DMEM_NVSMI_TIMEOUT:-10}   # tope de CADA nvidia-smi: un driver colgado no cuelga la guardia
GUARDIA_PLAZO=${BB_DMEM_GUARDIA_PLAZO:-120}  # segundos de reintentos antes de retroceder
ETAPA_MARCA=${BB_DMEM_ETAPA_MARCA:-/usr/local/sbin/bb-etapa-marca}

log() { echo "[dmem] $*"; }
die() { echo "[dmem] ERROR: $*" >&2; exit 1; }
raiz() { [ "$(id -u)" = 0 ] || [ -n "${BB_DMEM_SIN_RAIZ:-}" ] || die "necesita root: sudo bash $0 $1"; }

# --kernel <version>: MODDIR pasa a $MODROOT/<version>. Sin el, el kernel en marcha (uname -r), como siempre.
elige_kernel() {
    [ "$#" -eq 0 ] && return 0
    { [ "$#" -eq 2 ] && [ "$1" = --kernel ]; } || die "uso: $ACCION [--kernel <version>]"
    [[ "$2" =~ ^[A-Za-z0-9][A-Za-z0-9._+~-]*$ ]] || die "version de kernel invalida: $2"
    MODDIR=$MODROOT/$2
}

cmd_estado() {
    log "kernel en marcha: $(uname -r); elegido: $(basename "$MODDIR"); Secure Boot: $(mokutil --sb-state 2>&1 | head -1)"
    log "llave $LLAVE_PUB: $(mokutil --test-key "$LLAVE_PUB" 2>&1 | tail -1)"
    log "modulo cargado (kernel en marcha): $(cat /sys/module/nvidia/version 2>/dev/null || echo ninguno), srcversion $(cat /sys/module/nvidia/srcversion 2>/dev/null || echo ?)"
    log "dmem.capacity: $(cat /sys/fs/cgroup/dmem.capacity 2>/dev/null | head -3 | tr '\n' ' ')(vacio = sin region)"
    if [ -d "$MODDIR/updates" ]; then log "$MODDIR/updates (lo que ese kernel carga antes que el de Canonical):"; sha256sum "$MODDIR"/updates/*.ko 2>/dev/null || true
    else log "$MODDIR no tiene updates/: ese kernel carga los modulos de Canonical"; fi
    if [ -f "$ESTADO/instalados.txt" ]; then log "instalados por este script:"; cat "$ESTADO/instalados.txt"; else log "nada instalado por este script"; fi
}

# mokutil --test-key SALE 1 cuando la llave ya esta enrolada; con pipefail eso tumbaba el `| grep -q` (medido 2026-10-12)
llave_enrolada() { local o; o=$(mokutil --test-key "$LLAVE_PUB" 2>&1 || true); grep -q "is already enrolled" <<<"$o"; }

# Que la llave este enrolada no basta: cada .ko tiene que estar firmado CON ELLA. sig_key de modinfo es la serie del
# certificado firmante (sign-file firma con issuer+serial); se compara con la serie de $LLAVE_PUB. Un .ko sin firma, o
# firmado con otra llave (un firmados/ de una corrida vieja), el kernel lo rechaza con Secure Boot y la GPU no sube.
serie() { tr -d ': \n' | tr 'a-f' 'A-F' | sed 's/^0*//'; }
firmas_de_la_llave() {
    local m s llave
    llave=$(openssl x509 -inform DER -in "$LLAVE_PUB" -noout -serial 2>/dev/null | sed 's/^serial=//' | serie) || true
    [ -n "$llave" ] || { log "ATENCION: no pude leer la serie de $LLAVE_PUB con openssl"; return 1; }
    for m in "${MODS[@]}"; do
        s=$(modinfo -F sig_key "$ESTADO/firmados/$m.ko" 2>/dev/null | serie) || true
        [ -n "$s" ] || { log "ATENCION: $ESTADO/firmados/$m.ko NO esta firmado"; return 1; }
        [ "$s" = "$llave" ] || { log "ATENCION: $m.ko esta firmado con la llave de serie $s, no con $LLAVE_PUB (serie $llave)"; return 1; }
    done
    log "los ${#MODS[@]} modulos estan firmados con $LLAVE_PUB (serie $llave)"
}

cmd_enrolar() {
    raiz enrolar
    [ -f "$LLAVE_PUB" ] || die "no existe $LLAVE_PUB"
    if llave_enrolada; then log "la llave ya esta enrolada"; return 0; fi
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
        grep -q "^vermagic:.*$(uname -r)" < <(modinfo "$f") || die "$f no es para $(uname -r)"
        grep -q "^version:.*$VER_ESPERADA" < <(modinfo "$f") || die "$f no es la version $VER_ESPERADA"
        cp "$f" "$ESTADO/firmados/$m.ko"
        "$SIGN" sha256 "$LLAVE_PRIV" "$LLAVE_PUB" "$ESTADO/firmados/$m.ko"
        grep -q "^sig_key:" < <(modinfo "$ESTADO/firmados/$m.ko") || die "$m no quedo firmado"
        log "firmado $m"
    done
}

cmd_instala() {
    raiz instala
    local m
    [ -d "$ESTADO/firmados" ] || die "primero: firma <dir>"
    if [ -n "${BB_DMEM_SIN_RAIZ:-}" ]; then log "(prueba) se omite la comprobacion de la llave enrolada"
    else llave_enrolada || die "la llave NO esta enrolada: el kernel rechazaria los modulos y la GPU no subiria. Primero: enrolar y reiniciar"; fi
    firmas_de_la_llave || die "hay un modulo que no firmo la llave enrolada: el kernel lo rechazaria y la GPU no subiria. Primero: firma <dir>"
    mkdir -p "$MODDIR/updates" "$ESTADO"
    [ ! -f "$ESTADO/instalados.txt" ] || die "ya hay una instalacion (retrocede primero; si es de otro kernel: retrocede --kernel <version>)"
    : >"$ESTADO/instalados.txt"
    for m in "${MODS[@]}"; do
        cp "$ESTADO/firmados/$m.ko" "$MODDIR/updates/$m.ko"
        echo "$(sha256sum "$MODDIR/updates/$m.ko" | cut -d' ' -f1)  $MODDIR/updates/$m.ko" >>"$ESTADO/instalados.txt"
    done
    $DEPMOD -a "$(basename "$MODDIR")"
    rm -f "$ESTADO/retrocedido"
    if [ -z "${BB_DMEM_SIN_RAIZ:-}" ]; then
        # SIN `systemctl daemon-reload`: con Docker en cgroup `systemd`, recargar systemd puede quitarle el acceso a la GPU a
        # los contenedores en marcha (hilo 352743 del foro; produccion corre vLLM asi). La unidad nueva se carga en el arranque.
        # Sin DefaultDependencies y pedida por basic.target: hasta 2026-11 corria tras multi-user.target, y un arranque
        # que se colgaba antes de llegar ahi no retrocedia nunca. TimeoutStartSec=300 > plazo de 120 s + el ultimo
        # nvidia-smi (10 s) + la pausa + el retroceso: systemd no la mata a media decision.
        local nueva; nueva=$(mktemp)
        cat >"$nueva" <<UNIT
[Unit]
Description=bb: retrocede el modulo NVIDIA parcheado si la GPU no responde tras el arranque
DefaultDependencies=no
After=local-fs.target systemd-modules-load.service
Conflicts=shutdown.target
Before=shutdown.target
[Service]
Type=oneshot
TimeoutStartSec=300
ExecStart=/bin/bash $(readlink -f "${BASH_SOURCE[0]}") guardia
[Install]
WantedBy=basic.target
UNIT
        cmp -s "$nueva" "$UNIDAD" 2>/dev/null || cp "$nueva" "$UNIDAD"
        rm -f "$nueva"
        systemctl enable --no-reload bb-dmem-guardia.service >/dev/null 2>&1 || true
    fi
    log "instalado en $MODDIR/updates; NO se descargo nada. Reinicia cuando tengas la consola a mano."
}

# La decision de la guardia queda como etapa de arranque (etapas.jsonl y /dev/kmsg); sin la marca instalada, solo el log.
marca_etapa() {
    if [ -x "$ETAPA_MARCA" ]; then "$ETAPA_MARCA" "$1" || log "la marca de etapa $1 fallo"
    else log "sin $ETAPA_MARCA (adopted/system-units/LEEME-etapas.md): la decision $1 no queda como etapa"; fi
}

cmd_guardia() {
    raiz guardia
    local fin=$((SECONDS + GUARDIA_PLAZO)) salida
    while :; do
        # timeout en CADA intento: un nvidia-smi colgado (driver atascado) dejaba la guardia esperando para siempre
        if salida=$(timeout "$NVSMI_TIMEOUT" nvidia-smi -L 2>/dev/null) && grep -q '^GPU ' <<<"$salida"; then
            log "la GPU responde; el modulo parcheado se queda"; marca_etapa guardia-dmem-gpu-ok; return 0
        fi
        [ "$SECONDS" -lt "$fin" ] || break
        sleep 5  # blocking-sleep: espera acotada de arranque, plazo de $GUARDIA_PLAZO s -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01
    done
    log "la GPU NO respondio en $GUARDIA_PLAZO s (cada nvidia-smi con tope de $NVSMI_TIMEOUT s): retrocedo"
    marca_etapa guardia-dmem-retrocede
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

# Solo toca lo instalado en $MODDIR/updates (el kernel en marcha, o el de --kernel): las lineas de instalados.txt de
# otro kernel se conservan, y depmod corre para ESE kernel. Antes borraba todas y corria depmod para el que corre: desde
# otro kernel dejaba al parchado con un modules.dep que apuntaba a archivos borrados.
cmd_retrocede() {
    raiz retrocede
    local f h restos=0 otros=0
    [ -f "$ESTADO/instalados.txt" ] || { log "nada que retroceder"; return 0; }
    [ -d "$MODDIR/updates" ] || { log "$MODDIR no tiene updates/: nada que retroceder en ese kernel (no se toca nada)"; return 0; }
    : >"$ESTADO/instalados.restos"
    while read -r h f; do
        case "$f" in "$MODDIR/updates/"*) ;; *) echo "$h  $f" >>"$ESTADO/instalados.restos"; otros=$((otros + 1)); continue ;; esac
        [ -f "$f" ] || continue
        if [ "$(sha256sum "$f" | cut -d' ' -f1)" = "$h" ]; then rm -f "$f"; log "quitado $f"
        else log "ATENCION: $f cambio desde la instalacion; NO se borra y SEGUIRA cargandose"; echo "$h  $f" >>"$ESTADO/instalados.restos"; restos=1; fi
    done <"$ESTADO/instalados.txt"
    rmdir "$MODDIR/updates" 2>/dev/null || true
    $DEPMOD -a "$(basename "$MODDIR")"
    if [ "$restos" = 1 ]; then
        mv "$ESTADO/instalados.restos" "$ESTADO/instalados.txt"
        die "retroceso INCOMPLETO: quedan archivos alterados en $MODDIR/updates (lista en $ESTADO/instalados.txt); borralos a mano y corre depmod -a $(basename "$MODDIR")"
    fi
    if [ "$otros" -gt 0 ]; then
        mv "$ESTADO/instalados.restos" "$ESTADO/instalados.txt"
        log "retrocedido $(basename "$MODDIR"); quedan $otros archivos de OTRO kernel en $ESTADO/instalados.txt (no se tocan): retrocede --kernel <version>"
        return 0
    fi
    rm -f "$ESTADO/instalados.txt" "$ESTADO/instalados.restos"
    [ -n "${BB_DMEM_SIN_RAIZ:-}" ] || { systemctl disable --no-reload bb-dmem-guardia.service >/dev/null 2>&1 || true; rm -f "$UNIDAD"; }   # --no-reload: ver instala
    log "retrocedido $(basename "$MODDIR"): su siguiente arranque usa los modulos de Canonical"
}

ACCION=${1:-}
case "$ACCION" in
    estado) shift; elige_kernel "$@"; cmd_estado ;; enrolar) cmd_enrolar ;; firma) shift; cmd_firma "$@" ;; instala) cmd_instala ;;
    guardia) cmd_guardia ;; verifica) shift; cmd_verifica "$@" ;; retrocede) shift; elige_kernel "$@"; cmd_retrocede ;;
    *) sed -n 2,18p "$0"; exit 2 ;;
esac
