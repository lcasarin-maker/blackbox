#!/usr/bin/env bash
# opt_in_captura.sh -- capas OPT-IN de captura de arranque y de panico para la ATOM (adopted/opt-in/LEEME.md).
# NADA se activa por defecto: sin argumentos, o con cualquier invocacion ambigua, solo describe (plan) y no escribe.
# Lo corre Luis con sudo, UNA capa a la vez y con la consola delante.
#
#   bash tools/opt_in_captura.sh estado                         # que capas hay aplicadas y si siguen intactas
#   bash tools/opt_in_captura.sh plan [capa]                    # modo seco: que escribiria y que correria
#   sudo bash tools/opt_in_captura.sh [--kernel VER] aplica <capa>
#   sudo bash tools/opt_in_captura.sh retrocede <capa>
#
# Capas: netconsole-runtime netconsole-arranque pstore-tras-panico grub-marca panic-temprano
#
# Seguridad: cada aplica comprueba sus precondiciones y valida antes de escribir; respalda byte a byte, con sha256,
# en /var/lib/blackbox/opt-in/<capa>/ cada fichero que va a cambiar; si algo falla a medias deshace lo escrito.
# grub.cfg se genera aparte (grub-mkconfig -o, lo mismo que update-grub), se valida con grub-script-check, y solo
# entonces sustituye al vigente. retrocede verifica los sha256 y se niega si algo cambio fuera de la herramienta.
# La herramienta nunca reinicia la maquina.
#
# Costuras (pruebas con raiz falsa): --root DIR (o BB_OPTIN_ROOT) y cada comando de la maquina por BB_OPTIN_<CMD>
# (GRUB_MKCONFIG GRUB_SCRIPT_CHECK GRUB_EDITENV UPDATE_INITRAMFS LSINITRAMFS FINDMNT LSBLK SYSTEMCTL MODPROBE).
# Con una raiz falsa, un comando sin su costura cuenta como AUSENTE: una prueba nunca toca la maquina real.
# Salidas: 0 bien, 2 invocacion ambigua (se muestra el plan), 3 negativa (no se cambio nada).
set -euo pipefail
umask 022

CAPAS=(netconsole-runtime netconsole-arranque pstore-tras-panico grub-marca panic-temprano)
PLANTILLAS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/adopted/opt-in"
CONFIGFS_SH="$PLANTILLAS/bb-netconsole-configfs.sh"
ESTADO_REL=var/lib/blackbox/opt-in
CONF_REL=etc/blackbox/netconsole.conf
GRUB_CFG_REL=boot/grub/grub.cfg
GRUBENV_REL=boot/grub/grubenv
MODULES_REL=etc/initramfs-tools/modules
UNIDAD=bb-netconsole.service

log() { echo "[opt-in] $*"; }
die() { echo "[opt-in] ERROR: $*" >&2; exit 3; }

ROOT=${BB_OPTIN_ROOT:-}
KERNEL=""
ARGS=()
while [ $# -gt 0 ]; do
    case "$1" in
        --root) [ $# -ge 2 ] || die "--root sin directorio"; ROOT=$2; shift 2 ;;
        --root=*) ROOT=${1#--root=}; shift ;;
        --kernel) [ $# -ge 2 ] || die "--kernel sin version"; KERNEL=$2; shift 2 ;;
        --kernel=*) KERNEL=${1#--kernel=}; shift ;;
        *) ARGS+=("$1"); shift ;;
    esac
done
if [ -n "$ROOT" ]; then
    [ -d "$ROOT" ] || die "--root $ROOT no es un directorio"
    ROOT=$(cd "$ROOT" && pwd -P)
    [ "$ROOT" != / ] || ROOT=""
fi
[ -z "$KERNEL" ] || [[ "$KERNEL" =~ ^[A-Za-z0-9._+-]+$ ]] || die "--kernel no es una version de kernel: '$KERNEL'"

r() { printf '%s/%s' "$ROOT" "$1"; }          # ruta en la raiz; $1 relativa, sin / inicial
dir_capa() { r "$ESTADO_REL/$1"; }
es_capa() { local c; for c in "${CAPAS[@]}"; do [ "$c" = "${1:-}" ] && return 0; done; return 1; }
aplicada() { [ -f "$(dir_capa "$1")/aplicada" ]; }

# Comando de la maquina por su costura. Con raiz falsa y sin costura: ausente (sale 1), nunca el real.
herramienta() {
    local var="BB_OPTIN_$1" v
    v=${!var:-}
    if [ -z "$v" ]; then
        [ -z "$ROOT" ] || return 1
        v=$2
    fi
    command -v -- "$v" 2>/dev/null
}

# sha256 de un fichero, "L:<sha del destino>" de un symlink, "-" si no existe, "?" si es otra cosa.
huella() {
    if [ -L "$1" ]; then printf 'L:%s' "$(readlink -- "$1" | sha256sum | cut -d' ' -f1)"
    elif [ -f "$1" ]; then sha256sum -- "$1" | cut -d' ' -f1
    elif [ -e "$1" ]; then printf '?'
    else printf -- '-'; fi
}

# ---------------------------------------------------------------------------------------------------------------
# Transaccion de una capa. manifiesto: una linea por cambio, `tipo<TAB>sha_antes<TAB>sha_despues<TAB>ruta`, en el
# orden en que se hizo; tipo = fichero | enlace | dir. Cada linea se escribe ANTES del cambio que describe, asi que
# una aplica cortada a medias tambien se puede retroceder. `aplicada` se crea al final, cuando todo valido.
# ---------------------------------------------------------------------------------------------------------------
TX_DIR=""
TX_ABIERTA=0
AJENOS=""   # ficheros que un comando cambio sin que hubiera respaldo: un deshacer no los devuelve

tx_abre() {
    local estado top="" rel=$ESTADO_REL
    TX_DIR=$(dir_capa "$1")
    [ ! -e "$TX_DIR" ] || die "ya hay estado de $1 en $TX_DIR (estado lo explica; retrocede $1 primero)"
    estado=$(r "$ESTADO_REL")
    if [ ! -d "$estado" ]; then
        # El directorio mas alto que crea la herramienta queda anotado en .creado: retrocede lo quita al vaciarse.
        while [ "$rel" != . ] && [ ! -d "$(r "$rel")" ]; do top=$rel; rel=$(dirname "$rel"); done
        mkdir -p -- "$estado"
        printf '%s\n' "$top" >"$estado/.creado"
    fi
    mkdir -- "$TX_DIR" "$TX_DIR/respaldo"
    : >"$TX_DIR/manifiesto"
    TX_ABIERTA=1
}

anota() { printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" >>"$TX_DIR/manifiesto"; }

# Crea los directorios que falten encima de $1 (relativa) y los anota, para quitarlos al retroceder.
asegura_padre() {
    local rel faltan=()
    rel=$(dirname "$1")
    while [ "$rel" != . ] && [ ! -d "$(r "$rel")" ]; do faltan=("$rel" "${faltan[@]}"); rel=$(dirname "$rel"); done
    for rel in "${faltan[@]}"; do anota dir - - "$rel"; mkdir -- "$(r "$rel")"; done
}

# Copia byte a byte (con modo, dueno y fechas) y comprueba que el respaldo tiene el sha256 del original.
respalda() {
    local rel=$1 antes=$2 copia="$TX_DIR/respaldo/$1"
    mkdir -p -- "$(dirname "$copia")"
    cp -a -- "$(r "$rel")" "$copia"
    [ "$(huella "$copia")" = "$antes" ] || die "el respaldo de /$rel no coincide con el original"
}

# Instala el contenido de $3 en $1 (relativa). Modo $2 ("-" = el del fichero que se sustituye).
tx_escribe() {
    local rel=$1 modo=$2 src=$3 dst antes despues tmp
    dst=$(r "$rel")
    antes=$(huella "$dst")
    [ "$antes" != "?" ] && [ "${antes#L:}" = "$antes" ] || die "/$rel no es un fichero regular; no se toca"
    despues=$(huella "$src")
    [ "$antes" != - ] || [ "$modo" != - ] || die "falta el modo de /$rel"
    asegura_padre "$rel"
    [ "$antes" = - ] || respalda "$rel" "$antes"
    anota fichero "$antes" "$despues" "$rel"
    tmp="$dst.bb-opt-in.$$"
    cat -- "$src" >"$tmp"
    if [ "$modo" = - ]; then chmod --reference="$dst" -- "$tmp"; chown --reference="$dst" -- "$tmp"
    else chmod "$modo" -- "$tmp"; fi
    mv -f -- "$tmp" "$dst"
}

tx_enlaza() {  # ruta relativa, destino del symlink
    local rel=$1 dst
    dst=$(r "$rel")
    [ "$(huella "$dst")" = - ] || die "/$rel ya existe; no se toca"
    asegura_padre "$rel"
    anota enlace - "L:$(printf '%s\n' "$2" | sha256sum | cut -d' ' -f1)" "$rel"
    ln -s -- "$2" "$dst"
}

tx_cierra() {
    printf 'capa=%s\nkernel=%s\n' "$1" "${KERNEL:--}" >"$TX_DIR/aplicada"
    TX_ABIERTA=0
    log "$1 APLICADA. Respaldo y sha256 en ${TX_DIR#"$ROOT"}; retroceso: sudo bash tools/opt_in_captura.sh retrocede $1"
}

# Devuelve UNA entrada del manifiesto a como estaba antes de aplicar.
restaura() {  # tipo sha_antes ruta-relativa
    local dst tmp
    dst=$(r "$3")
    case "$1" in
        dir) rmdir -- "$dst" 2>/dev/null || [ ! -e "$dst" ] || log "AVISO: queda /$3 (tiene contenido que no es de esta capa)" ;;
        enlace) rm -f -- "$dst" ;;
        fichero)
            # tambien el temporal de una escritura que una senal corto entre el cat y el mv
            rm -f -- "$dst".bb-opt-in.*
            if [ "$2" = - ]; then rm -f -- "$dst"
            else tmp="$dst.bb-opt-in.$$"; cp -a -- "$TX_DIR/respaldo/$3" "$tmp" && mv -f -- "$tmp" "$dst"; fi ;;
    esac
}

# Quita el estado de la capa y, si la herramienta creo el arbol de estado y ya quedo vacio, tambien ese arbol.
borra_estado_capa() {
    local estado top rel=$ESTADO_REL
    find "$TX_DIR" -depth -delete
    estado=$(r "$ESTADO_REL")
    [ -f "$estado/.creado" ] || return 0
    [ -z "$(find "$estado" -mindepth 1 -maxdepth 1 ! -name .creado -print -quit)" ] || return 0
    top=$(cat -- "$estado/.creado")
    rm -f -- "$estado/.creado"
    while rmdir -- "$(r "$rel")" 2>/dev/null && [ "$rel" != "$top" ] && [ "$rel" != . ]; do rel=$(dirname "$rel"); done
}

# Una aplica que falla a medias (negativa, error o senal) deshace lo que ya escribio, en orden inverso.
tx_deshace() {
    local tipo antes despues rel fallos=0
    TX_ABIERTA=0
    log "deshaciendo lo que esta aplica alcanzo a escribir"
    while IFS=$'\t' read -r tipo antes despues rel; do
        if [ "$tipo" != dir ] && [ "$(huella "$(r "$rel")")" = "$antes" ]; then continue; fi
        restaura "$tipo" "$antes" "$rel" || { log "AVISO: no se pudo restaurar /$rel"; fallos=1; }
    done < <(tac -- "$TX_DIR/manifiesto")
    if [ "$fallos" = 0 ] && [ -n "$AJENOS" ]; then
        borra_estado_capa; log "deshecho lo que tenia respaldo; NO se pudo devolver:$AJENOS (revisalo a mano)"
    elif [ "$fallos" = 0 ]; then borra_estado_capa; log "deshecho: la raiz quedo como estaba"
    else log "deshecho INCOMPLETO: el respaldo sigue en ${TX_DIR#"$ROOT"}; corre retrocede"; fi
}
trap 'rc=$?; [ "$TX_ABIERTA" != 1 ] || tx_deshace; exit "$rc"' EXIT
trap 'exit 130' INT TERM

# ---------------------------------------------------------------------------------------------------------------
# Linea de comandos y grub.cfg
# ---------------------------------------------------------------------------------------------------------------
contiene() { [[ " $1 " == *" $2 "* ]]; }      # $1 contiene la palabra $2
no_contiene() { ! contiene "$1" "$2"; }

# GRUB_CMDLINE_LINUX_DEFAULT como la arma grub-mkconfig (default/grub y despues default/grub.d/*.cfg en orden C),
# con el candidato $1 (nombre en grub.d) y su contenido $2 en su sitio. Solo lee: el candidato no toca el disco.
cmdline_simulada() {
    local nombre=${1:-} contenido=${2:-}
    (
        set +eu
        GRUB_CMDLINE_LINUX_DEFAULT=""
        d=$(r etc/default/grub.d)
        # shellcheck source=/dev/null
        [ ! -f "$(r etc/default/grub)" ] || . "$(r etc/default/grub)" >/dev/null 2>&1
        while IFS= read -r b; do
            # shellcheck source=/dev/null
            if [ "$b" = "$nombre" ]; then eval "$contenido" </dev/null >/dev/null 2>&1; else . "$d/$b" </dev/null >/dev/null 2>&1; fi
        done < <( { for f in "$d"/*.cfg; do [ ! -e "$f" ] || basename "$f"; done; [ -z "$nombre" ] || echo "$nombre"; } \
                  | LC_ALL=C sort -u)
        printf '%s\n' "$GRUB_CMDLINE_LINUX_DEFAULT"
    )
}

# Valida un grub.cfg generado contra el vigente. Imprime el motivo y sale 1 si no sirve.
valida_grub_cfg() {  # nuevo vigente palabra-esperada(vacia=ninguna) marca(vacia|marca)
    local nuevo=$1 vigente=$2 raiz
    "$GSC" "$nuevo" >/dev/null 2>&1 || { echo "grub-script-check lo rechaza"; return 1; }
    awk -v tok="$3" '
        $1 == "linux" { n++; if (NF < 3) vacias++; else if ($0 !~ /[[:space:]]root=/) sinroot++
                        if (tok != "" && index(" " $0 " ", " " tok " ")) con++ }
        END { if (!n) print "no tiene ninguna linea linux"; else if (vacias) print vacias " linea(s) linux sin argumentos"
              else if (sinroot) print sinroot " linea(s) linux sin root="; else if (tok != "" && !con) print "ninguna entrada lleva " tok
              exit (!n || vacias || sinroot || (tok != "" && !con)) }' "$nuevo" || return 1
    while IFS= read -r raiz; do
        grep -qF -- " $raiz" "$nuevo" || { echo "perdio $raiz"; return 1; }
    done < <(grep -o 'root=[^[:space:]]*' "$vigente" | sort -u)
    if [ "${4:-}" = marca ]; then
        awk '/load_env/ && !l { l = NR } /save_env bb_prev_recordfail/ && !m { m = NR } END { exit !(l && m && l < m) }' "$nuevo" \
            || { echo "la marca bb_prev_* no queda despues del load_env de 00_header"; return 1; }
    fi
}

# grub-mkconfig -o a un fichero aparte, validacion, y solo entonces sustituye a grub.cfg (con respaldo).
regenera_grub() {  # palabra-esperada [marca]
    local nuevo="$TX_DIR/grub.cfg.nuevo" bitacora="$TX_DIR/grub-mkconfig.log" motivo
    "$MK" -o "$nuevo" >"$bitacora" 2>&1 || { cat -- "$bitacora" >&2; die "grub-mkconfig fallo; grub.cfg no se toco"; }
    motivo=$(valida_grub_cfg "$nuevo" "$(r "$GRUB_CFG_REL")" "$1" "${2:-}") \
        || die "el grub.cfg generado no sirve ($motivo); grub.cfg no se toco"
    tx_escribe "$GRUB_CFG_REL" - "$nuevo"
    rm -f -- "$nuevo" "$bitacora"
    log "grub.cfg regenerado y validado (grub-script-check, root= en cada entrada${1:+, $1 presente})"
}

# ---------------------------------------------------------------------------------------------------------------
# initramfs (capa netconsole-arranque)
# ---------------------------------------------------------------------------------------------------------------
patron_modulo() { printf '%s' "${1//[-_]/[-_]}"; }   # modprobe trata - y _ como iguales
modulo_presente() {  # modulo: .ko* bajo lib/modules/KERNEL, o compilado dentro (modules.builtin)
    local base pat
    base=$(r "lib/modules/$KERNEL")
    pat=$(patron_modulo "$1")
    [ -n "$(find "$base" -name "$pat.ko*" -print -quit 2>/dev/null)" ] || modulo_builtin "$1"
}
modulo_builtin() { grep -Eq "/$(patron_modulo "$1")\.ko$" "$(r "lib/modules/$KERNEL/modules.builtin")" 2>/dev/null; }

foto() {  # ruta<TAB>tamano<TAB>mtime de los ficheros directos de cada directorio relativo dado
    local d
    for d in "$@"; do
        [ ! -d "$(r "$d")" ] || find "$(r "$d")" -maxdepth 1 \( -type f -o -type l \) -printf "$d/%P\t%s\t%T@\n"
    done | LC_ALL=C sort
}

# update-initramfs -u -k KERNEL reescribe el initrd y su sha en /var/lib/initramfs-tools: los dos se respaldan antes.
# Cualquier otro fichero que aparezca en esos directorios se anota como nuevo (retrocede lo quita); si cambiara uno
# que ya existia y no tiene respaldo, la capa se niega y se deshace.
genera_initrd() {
    local rel tipo antes rc=0 tam t
    local -a propios=("boot/initrd.img-$KERNEL" "var/lib/initramfs-tools/$KERNEL")
    local -A previo=()
    for rel in "${propios[@]}"; do
        antes=$(huella "$(r "$rel")")
        [ "$antes" = - ] || respalda "$rel" "$antes"
        anota fichero "$antes" PENDIENTE "$rel"
    done
    while IFS=$'\t' read -r rel tam t; do previo[$rel]="$tam $t"; done < <(foto boot var/lib/initramfs-tools)
    log "corriendo: update-initramfs -u -k $KERNEL"
    "$UI" -u -k "$KERNEL" || rc=$?
    while IFS=$'\t' read -r rel tam t; do
        case " ${propios[*]} " in *" $rel "*) continue ;; esac
        if [ -z "${previo[$rel]+x}" ]; then anota fichero - "$(huella "$(r "$rel")")" "$rel"
        elif [ "${previo[$rel]}" != "$tam $t" ]; then AJENOS+=" /$rel"; fi
        unset 'previo[$rel]'
    done < <(foto boot var/lib/initramfs-tools)
    for rel in "${!previo[@]}"; do case " ${propios[*]} " in *" $rel "*) ;; *) AJENOS+=" /$rel (borrado)" ;; esac; done
    # Las lineas PENDIENTE pasan a llevar el sha256 que dejo update-initramfs.
    while IFS=$'\t' read -r tipo antes t rel; do
        [ "$t" != PENDIENTE ] || t=$(huella "$(r "$rel")")
        printf '%s\t%s\t%s\t%s\n' "$tipo" "$antes" "$t" "$rel"
    done <"$TX_DIR/manifiesto" >"$TX_DIR/manifiesto.nuevo"
    mv -f -- "$TX_DIR/manifiesto.nuevo" "$TX_DIR/manifiesto"
    [ -z "$AJENOS" ] || die "update-initramfs cambio ficheros sin respaldo:$AJENOS (no se pueden devolver)"
    [ "$rc" = 0 ] || die "update-initramfs fallo (rc=$rc)"
}

valida_initrd() {
    local lista m
    lista=$("$LSI" "$(r "boot/initrd.img-$KERNEL")") || die "lsinitramfs no pudo leer el initrd nuevo"
    for m in "$NC_DRIVER" netconsole; do
        modulo_builtin "$m" && continue
        grep -Eq -- "(^|/)$(patron_modulo "$m")\.ko(\.[a-z0-9]+)?$" <<<"$lista" || die "el initrd nuevo no trae $m.ko"
    done
    log "initrd validado: trae $NC_DRIVER y netconsole"
}

# ---------------------------------------------------------------------------------------------------------------
# Precondiciones: las mismas para plan (informa) y aplica (se niega con cualquier FALTA).
# ---------------------------------------------------------------------------------------------------------------
FALTAS=0
GSC="" MK="" UI="" LSI="" TOKEN="" NC_DEV="" NC_DRIVER=""
chequea() {  # descripcion comando...
    local d=$1; shift
    if "$@"; then echo "    ok: $d"; else echo "    FALTA: $d"; FALTAS=$((FALTAS + 1)); fi
}
usa() { local v; v=$(herramienta "$2" "$3") || return 1; printf -v "$1" '%s' "$v"; }   # VAR COSTURA comando
existe() { [ -e "$(r "$1")" ] || [ -L "$(r "$1")" ]; }
no_existe() { ! existe "$1"; }
no_aplicada() { ! aplicada "$1"; }
sin_hooks_post_update() { [ -z "$(find "$(r etc/initramfs/post-update.d)" -mindepth 1 -print -quit 2>/dev/null)" ]; }
modules_sin_netconsole() { ! grep -Eq '^[[:space:]]*netconsole([[:space:]]|$)' "$(r "$MODULES_REL")" 2>/dev/null; }
hay_kernel() { [ -n "$KERNEL" ] && [ -f "$(r "boot/initrd.img-$KERNEL")" ] && [ -d "$(r "lib/modules/$KERNEL")" ]; }

lee_netconsole() {
    local salida clave valor
    salida=$(BB_NC_ROOT=$ROOT bash "$CONFIGFS_SH" valida "$(r "$CONF_REL")") || return 1
    while IFS='=' read -r clave valor; do
        case "$clave" in DEV) NC_DEV=$valor ;; DRIVER) NC_DRIVER=$valor ;; esac
    done <<<"$salida"
    TOKEN=$(BB_NC_ROOT=$ROOT bash "$CONFIGFS_SH" cmdline "$(r "$CONF_REL")")
}

precond_grub() {
    chequea "grub-script-check (sin el no se valida grub.cfg y la capa se niega)" usa GSC GRUB_SCRIPT_CHECK grub-script-check
    chequea "grub-mkconfig (lo que corre update-grub)" usa MK GRUB_MKCONFIG grub-mkconfig
    chequea "/$GRUB_CFG_REL existe" existe "$GRUB_CFG_REL"
}

precond_cmdline() {  # nombre-en-grub.d contenido
    local actual candidata
    chequea "/etc/default/grub.d/$1 no existe" no_existe "etc/default/grub.d/$1"
    [ -n "$TOKEN" ] || return 0
    actual=$(cmdline_simulada)
    candidata=$(cmdline_simulada "$1" "$2")
    echo "    linea de comandos (GRUB_CMDLINE_LINUX_DEFAULT) hoy:  ${actual:-<vacia>}"
    echo "    linea de comandos tras aplicar:                      ${candidata:-<vacia>}"
    chequea "$TOKEN no esta ya en la linea de comandos" no_contiene "$actual" "$TOKEN"
    chequea "la linea resultante no queda vacia y lleva $TOKEN" contiene "$candidata" "$TOKEN"
}

# save_env de GRUB solo escribe bien el grubenv en un sistema de ficheros simple: /boot en ext4, sin LVM ni RAID.
boot_simple() {
    local fm lb salida fstype fuente tipo
    usa fm FINDMNT findmnt || { echo "    (sin findmnt no se puede comprobar /boot)"; return 1; }
    usa lb LSBLK lsblk || { echo "    (sin lsblk no se puede comprobar /boot)"; return 1; }
    salida=$("$fm" -n -o FSTYPE,SOURCE -T "$(r boot)") || return 1
    read -r fstype fuente <<<"$salida"
    echo "    /boot vive en: ${fstype:-?} sobre ${fuente:-?}"
    [ "$fstype" = ext4 ] || return 1
    case "$fuente" in /dev/mapper/* | /dev/md* | /dev/dm-*) return 1 ;; /dev/*) ;; *) return 1 ;; esac
    tipo=$("$lb" -n -d -o TYPE "$fuente") || return 1
    echo "    tipo del dispositivo: $tipo"
    [ "$tipo" = part ] || [ "$tipo" = disk ]
}

snippet() {  # capa -> nombre en /etc/default/grub.d
    case "$1" in
        netconsole-arranque) echo 90-bb-netconsole.cfg ;;
        pstore-tras-panico) echo 91-bb-pstore-tras-panico.cfg ;;
        panic-temprano) echo 92-bb-panic-temprano.cfg ;;
    esac
}
contenido_snippet() {  # capa -> plantilla con el parametro ya puesto
    local t
    t=$(<"$PLANTILLAS/etc_default_grub.d_$(snippet "$1")")
    printf '%s\n' "${t//@NETCONSOLE@/$TOKEN}"
}

precond() {
    local capa=$1
    case "$capa" in
        netconsole-runtime)
            chequea "/$CONF_REL valido" lee_netconsole
            chequea "sintaxis de bb-netconsole-configfs" bash -n "$CONFIGFS_SH"
            chequea "netconsole-arranque no esta aplicada (dos destinos duplicarian cada mensaje)" no_aplicada netconsole-arranque
            chequea "/usr/local/sbin/bb-netconsole-configfs no existe" no_existe usr/local/sbin/bb-netconsole-configfs
            chequea "/etc/systemd/system/$UNIDAD no existe" no_existe "etc/systemd/system/$UNIDAD"
            chequea "/etc/systemd/system/multi-user.target.wants/$UNIDAD no existe" \
                no_existe "etc/systemd/system/multi-user.target.wants/$UNIDAD" ;;
        netconsole-arranque)
            chequea "/$CONF_REL valido" lee_netconsole
            chequea "DRIVER definido en /$CONF_REL" test -n "$NC_DRIVER"
            chequea "--kernel ${KERNEL:-<falta>} con /boot/initrd.img-* y /lib/modules/*" hay_kernel
            if hay_kernel && [ -n "$NC_DRIVER" ]; then
                chequea "modulo $NC_DRIVER para $KERNEL" modulo_presente "$NC_DRIVER"
                chequea "modulo netconsole para $KERNEL" modulo_presente netconsole
            fi
            chequea "update-initramfs" usa UI UPDATE_INITRAMFS update-initramfs
            chequea "lsinitramfs (valida el initrd nuevo)" usa LSI LSINITRAMFS lsinitramfs
            chequea "/etc/initramfs/post-update.d vacio (un hook copiaria el initrd fuera del respaldo)" sin_hooks_post_update
            chequea "netconsole no figura ya en /$MODULES_REL" modules_sin_netconsole
            chequea "netconsole-runtime no esta aplicada (dos destinos duplicarian cada mensaje)" no_aplicada netconsole-runtime
            precond_grub
            precond_cmdline "$(snippet "$capa")" "$(contenido_snippet "$capa")" ;;
        pstore-tras-panico | panic-temprano)
            if [ "$capa" = panic-temprano ]; then TOKEN=panic=30; else TOKEN=crash_kexec_post_notifiers; fi
            precond_grub
            precond_cmdline "$(snippet "$capa")" "$(contenido_snippet "$capa")" ;;
        grub-marca)
            TOKEN=""
            precond_grub
            chequea "/etc/grub.d/09_bb_etapa no existe" no_existe etc/grub.d/09_bb_etapa
            chequea "/$GRUBENV_REL existe (save_env no lo crea)" existe "$GRUBENV_REL"
            chequea "/boot en ext4 sin LVM ni RAID" boot_simple ;;
    esac
}

cambios() {  # capa -> lo que escribiria y correria
    case "$1" in
        netconsole-runtime) cat <<TXT
    escribe: /usr/local/sbin/bb-netconsole-configfs (0755), /etc/systemd/system/$UNIDAD (0644)
    enlaza:  /etc/systemd/system/multi-user.target.wants/$UNIDAD (= systemctl enable, sin recargar systemd)
    NO arranca la unidad ni carga el modulo: eso lo hace Luis con 'sudo systemctl start $UNIDAD'
TXT
            ;;
        netconsole-arranque) cat <<TXT
    modifica: /$MODULES_REL (anade DRIVER y netconsole, en ese orden)
    escribe:  /etc/default/grub.d/$(snippet "$1") (0644)
    corre:    update-initramfs -u -k ${KERNEL:-<kernel>} (respaldo del initrd), grub-mkconfig + validacion -> /$GRUB_CFG_REL
TXT
            ;;
        pstore-tras-panico | panic-temprano) cat <<TXT
    escribe: /etc/default/grub.d/$(snippet "$1") (0644)
    corre:   grub-mkconfig + validacion -> /$GRUB_CFG_REL (con respaldo)
TXT
            ;;
        grub-marca) cat <<TXT
    escribe: /etc/grub.d/09_bb_etapa (0755)
    corre:   grub-mkconfig + validacion -> /$GRUB_CFG_REL (con respaldo)
TXT
            ;;
    esac
}

# ---------------------------------------------------------------------------------------------------------------
# aplica
# ---------------------------------------------------------------------------------------------------------------
aplica_snippet() {  # capa (con TOKEN ya puesto por precond)
    local tmp
    tmp="$TX_DIR/snippet.nuevo"
    contenido_snippet "$1" >"$tmp"
    tx_escribe "etc/default/grub.d/$(snippet "$1")" 0644 "$tmp"
    rm -f -- "$tmp"
}

cmd_aplica() {
    local capa=$1 tmp
    [ -n "$ROOT" ] || [ "$(id -u)" = 0 ] || die "necesita root: sudo bash $0 aplica $capa"
    ! aplicada "$capa" || die "$capa ya esta aplicada (estado la describe)"
    FALTAS=0
    log "precondiciones de $capa:"
    precond "$capa"
    [ "$FALTAS" = 0 ] || die "$capa: $FALTAS precondicion(es) sin cumplir; no se escribio nada"
    tx_abre "$capa"
    case "$capa" in
        netconsole-runtime)
            tx_escribe usr/local/sbin/bb-netconsole-configfs 0755 "$CONFIGFS_SH"
            tx_escribe "etc/systemd/system/$UNIDAD" 0644 "$PLANTILLAS/etc_systemd_system_$UNIDAD"
            tx_enlaza "etc/systemd/system/multi-user.target.wants/$UNIDAD" "/etc/systemd/system/$UNIDAD" ;;
        netconsole-arranque)
            tmp="$TX_DIR/modules.nuevo"
            if [ -f "$(r "$MODULES_REL")" ]; then
                cat -- "$(r "$MODULES_REL")" >"$tmp"
                [ ! -s "$tmp" ] || [ -z "$(tail -c1 -- "$tmp")" ] || echo >>"$tmp"
            else : >"$tmp"; fi
            printf '# bb opt-in netconsole-arranque: el driver de %s antes que netconsole\n%s\nnetconsole\n' \
                "$NC_DEV" "$NC_DRIVER" >>"$tmp"
            if [ -f "$(r "$MODULES_REL")" ]; then tx_escribe "$MODULES_REL" - "$tmp"; else tx_escribe "$MODULES_REL" 0644 "$tmp"; fi
            rm -f -- "$tmp"
            aplica_snippet "$capa"
            genera_initrd
            valida_initrd
            regenera_grub "$TOKEN" ;;
        pstore-tras-panico | panic-temprano)
            aplica_snippet "$capa"
            regenera_grub "$TOKEN" ;;
        grub-marca)
            tx_escribe etc/grub.d/09_bb_etapa 0755 "$PLANTILLAS/etc_grub.d_09_bb_etapa"
            regenera_grub "" marca ;;
    esac
    tx_cierra "$capa"
    case "$capa" in
        netconsole-runtime)
            log "siguiente paso, con el testigo escuchando (nc -ul 6666): sudo systemctl start $UNIDAD"
            log "y comprobar: journalctl -k | grep -E 'netconsole|bb-netconsole-marca'" ;;
        *) log "surte efecto en el proximo arranque; la herramienta no reinicia. Salida de emergencia: adopted/opt-in/LEEME.md" ;;
    esac
}

# ---------------------------------------------------------------------------------------------------------------
# retrocede
# ---------------------------------------------------------------------------------------------------------------
capas_que_tocan() {  # ruta-relativa capa-excluida
    local c
    for c in "${CAPAS[@]}"; do
        [ "$c" != "$2" ] || continue
        [ ! -f "$(dir_capa "$c")/manifiesto" ] || ! cut -f4 "$(dir_capa "$c")/manifiesto" | grep -qxF -- "$1" || printf '%s ' "$c"
    done
}

# Imprime cada conflicto y sale 1 si hay alguno. Solo lee.
verifica_retroceso() {
    local capa=$1 d tipo antes despues rel actual otras malos=0
    d=$(dir_capa "$capa")
    [ -f "$d/manifiesto" ] || { echo "  falta $d/manifiesto"; return 1; }
    while IFS=$'\t' read -r tipo antes despues rel; do
        [ "$tipo" != dir ] || continue
        actual=$(huella "$(r "$rel")")
        if [ "$actual" = "$despues" ]; then
            if [ "$tipo" = fichero ] && [ "$antes" != - ] && [ "$(huella "$d/respaldo/$rel")" != "$antes" ]; then
                echo "  el respaldo de /$rel falta o no tiene el sha256 que se anoto ($antes)"; malos=1
            fi
        elif [ "$actual" != "$antes" ]; then
            echo "  /$rel cambio fuera de la herramienta: sha256 ${actual:0:16}, aplica dejo ${despues:0:16}"
            otras=$(capas_que_tocan "$rel" "$capa")
            [ -z "$otras" ] || echo "    (lo regenero otra capa aplicada despues: retrocede antes $otras)"
            malos=1
        fi
    done <"$d/manifiesto"
    if [ "$capa" = netconsole-runtime ] && [ -f "$(r sys/module/netconsole/initstate)" ] && [ -z "$MP" ]; then
        echo "  netconsole esta cargado y no hay modprobe para descargarlo"; malos=1
    fi
    return "$malos"
}

para_runtime() {
    local sc script
    if usa sc SYSTEMCTL systemctl; then
        "$sc" stop "$UNIDAD" || log "AVISO: systemctl stop $UNIDAD fallo; el script quita el destino igual"
    else log "sin systemctl: no se detiene la unidad"; fi
    script=$(r usr/local/sbin/bb-netconsole-configfs)
    [ -f "$script" ] || script=$CONFIGFS_SH
    BB_NC_ROOT=$ROOT BB_NC_MODPROBE=${MP:-modprobe} bash "$script" para
}

limpia_grubenv() {
    local ge env
    env=$(r "$GRUBENV_REL")
    grep -q '^bb_prev_' "$env" 2>/dev/null || return 0
    if usa ge GRUB_EDITENV grub-editenv; then
        "$ge" "$env" unset bb_prev_recordfail bb_prev_default bb_prev_boot_once && log "quitadas las bb_prev_* de /$GRUBENV_REL"
    else log "AVISO: sin grub-editenv quedan las bb_prev_* en /$GRUBENV_REL (GRUB las ignora sin 09_bb_etapa)"; fi
}

MP=""
cmd_retrocede() {
    local capa=$1 conflictos tipo antes despues rel
    [ -n "$ROOT" ] || [ "$(id -u)" = 0 ] || die "necesita root: sudo bash $0 retrocede $capa"
    TX_DIR=$(dir_capa "$capa")
    [ -d "$TX_DIR" ] || { log "$capa no esta aplicada: nada que retroceder"; return 0; }
    usa MP MODPROBE modprobe || MP=""   # aqui y no en verifica_retroceso, que corre en un subshell
    if ! conflictos=$(verifica_retroceso "$capa"); then
        printf '%s\n' "$conflictos" >&2
        die "retrocede $capa se niega: no se cambio nada. Revisa a mano (adopted/opt-in/LEEME.md, retroceso manual)"
    fi
    [ "$capa" != netconsole-runtime ] || para_runtime
    while IFS=$'\t' read -r tipo antes despues rel; do
        if [ "$tipo" != dir ] && [ "$(huella "$(r "$rel")")" != "$despues" ]; then continue; fi
        restaura "$tipo" "$antes" "$rel"
        [ "$tipo" = dir ] || log "devuelto /$rel"
    done < <(tac -- "$TX_DIR/manifiesto")
    [ "$capa" != grub-marca ] || limpia_grubenv
    borra_estado_capa
    log "$capa RETROCEDIDA: cada fichero quedo byte a byte como antes de aplicar"
}

# ---------------------------------------------------------------------------------------------------------------
# estado y plan: solo leen
# ---------------------------------------------------------------------------------------------------------------
cmd_estado() {
    local capa d tipo antes despues rel actual e cmdline v lista=()
    log "raiz: ${ROOT:-/}"
    for capa in "${CAPAS[@]}"; do
        d=$(dir_capa "$capa")
        if aplicada "$capa"; then log "$capa: APLICADA"; lista+=("$capa")
        elif [ -d "$d" ]; then log "$capa: INCOMPLETA (una aplica se corto a medias: sudo bash $0 retrocede $capa)"
        else log "$capa: no aplicada"; continue; fi
        [ -f "$d/manifiesto" ] || continue
        while IFS=$'\t' read -r tipo antes despues rel; do
            [ "$tipo" != dir ] || continue
            actual=$(huella "$(r "$rel")")
            if [ "$actual" = "$despues" ]; then e="intacto"
            elif [ "$actual" = "$antes" ]; then e="como antes de aplicar"
            else e="CAMBIADO fuera de la herramienta (retrocede se negara)"; fi
            log "    /$rel: $e"
        done <"$d/manifiesto"
    done
    log "aplicadas: ${lista[*]:-ninguna}"
    # Lo que de verdad recibio el kernel en marcha: una capa de arranque solo vale tras reiniciar.
    if [ -r "$(r proc/cmdline)" ]; then
        cmdline=$(<"$(r proc/cmdline)")
        for v in netconsole.netconsole= crash_kexec_post_notifiers panic=; do
            if [[ " $cmdline " == *" $v"* ]]; then log "arranque en marcha: lleva $v"; else log "arranque en marcha: sin $v"; fi
        done
    fi
    d=$(r sys/kernel/config/netconsole/bb)
    if [ -d "$d" ]; then log "destino netconsole bb: enabled=$(cat -- "$d/enabled" 2>/dev/null || echo ?)"
    else log "destino netconsole bb: no existe"; fi
    if [ -r "$(r "$GRUBENV_REL")" ]; then
        grep '^bb_prev_' "$(r "$GRUBENV_REL")" | sed 's/^/[opt-in] grubenv: /' || log "grubenv: sin bb_prev_*"
    fi
}

descripcion() {
    case "$1" in
        netconsole-runtime) echo "unidad tras network-online.target: carga netconsole y crea el destino bb por configfs" ;;
        netconsole-arranque) echo "netconsole desde el initramfs y en la linea de comandos: captura el arranque entero" ;;
        pstore-tras-panico) echo "crash_kexec_post_notifiers: pstore guarda el panico aunque kdump este cargado" ;;
        grub-marca) echo "/etc/grub.d/09_bb_etapa: GRUB guarda recordfail y la entrada por defecto en bb_prev_*" ;;
        panic-temprano) echo "panic=30: un panico antes de sysctl reinicia a los 30 s en vez de quedarse parado" ;;
    esac
}

cmd_plan() {  # capa, o vacio = todas
    local capa
    for capa in "${CAPAS[@]}"; do
        [ -z "${1:-}" ] || [ "$1" = "$capa" ] || continue
        FALTAS=0 TOKEN=""
        log "== $capa: $(descripcion "$capa")"
        if aplicada "$capa"; then log "  APLICADA; retroceso: sudo bash tools/opt_in_captura.sh retrocede $capa"; continue; fi
        log "  precondiciones:"
        precond "$capa"
        log "  cambios si se aplica:"
        cambios "$capa"
        log "  retroceso: sudo bash tools/opt_in_captura.sh retrocede $capa"
        if [ "$FALTAS" = 0 ]; then log "  se puede aplicar: sudo bash tools/opt_in_captura.sh${KERNEL:+ --kernel $KERNEL} aplica $capa"
        else log "  NO se puede aplicar hoy: $FALTAS precondicion(es) sin cumplir"; fi
    done
    log "modo seco: no se escribio nada"
}

ambigua() {
    log "invocacion ambigua o incompleta ('${ARGS[*]:-}'): no se escribe nada; este es el plan"
    cmd_plan ""
    exit 2
}

# Una sola instancia por raiz: el candado es el directorio raiz abierto en lectura (no escribe nada).
candado() {
    exec 9<"${ROOT:-/}"
    flock -n 9 || die "otra instancia de opt_in_captura corre sobre ${ROOT:-/}"
}

set -- "${ARGS[@]+"${ARGS[@]}"}"
case "${1:-plan}" in
    estado) [ $# -le 1 ] || ambigua; cmd_estado ;;
    plan) [ $# -le 2 ] || ambigua; [ -z "${2:-}" ] || es_capa "$2" || ambigua; cmd_plan "${2:-}" ;;
    aplica | retrocede)
        { [ $# -eq 2 ] && es_capa "$2"; } || ambigua
        candado
        if [ "$1" = aplica ]; then cmd_aplica "$2"; else cmd_retrocede "$2"; fi ;;
    -h | --help | ayuda) sed -n 2,24p "$0" ;;
    *) ambigua ;;
esac
