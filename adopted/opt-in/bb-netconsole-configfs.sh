#!/usr/bin/env bash
# bb-netconsole-configfs -- destino netconsole "bb" por configfs, con los parametros de /etc/blackbox/netconsole.conf.
# Lo instala tools/opt_in_captura.sh (capa netconsole-runtime) en /usr/local/sbin/bb-netconsole-configfs y lo corre
# bb-netconsole.service. La herramienta lo usa ademas, desde el repo, para validar la configuracion (un solo lector).
#
#   bb-netconsole-configfs arranca          # modprobe netconsole + crea y habilita /sys/kernel/config/netconsole/bb
#   bb-netconsole-configfs para             # deshabilita y rmdir del destino + modprobe -r netconsole
#   bb-netconsole-configfs valida [conf]    # solo lee: imprime la configuracion normalizada, o sale 3
#   bb-netconsole-configfs cmdline [conf]   # solo lee: el parametro de arranque equivalente (capa netconsole-arranque)
#
# La configuracion NO se ejecuta: se lee linea a linea, solo con las claves conocidas y cada valor validado.
# Costuras para pruebas con raiz falsa: BB_NC_ROOT (raiz), BB_NC_MODPROBE (modprobe).
set -euo pipefail

R=${BB_NC_ROOT:-}
R=${R%/}
CONF_DEF="$R/etc/blackbox/netconsole.conf"
DESTINO="$R/sys/kernel/config/netconsole/bb"
MODPROBE=${BB_NC_MODPROBE:-modprobe}
PUERTO_LOCAL=6665
PUERTO_REMOTO=6666

die() { echo "[bb-netconsole] ERROR: $*" >&2; exit 3; }
log() { echo "[bb-netconsole] $*"; }

es_ipv4() {
    local o
    [[ "$1" =~ ^([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})$ ]] || return 1
    for o in "${BASH_REMATCH[@]:1}"; do (( 10#$o <= 255 )) || return 1; done
    [ "$1" != 0.0.0.0 ] && [ "$1" != 255.255.255.255 ]
}

# Deja DEV, LOCAL_IP, REMOTE_IP, REMOTE_MAC y DRIVER (opcional: solo lo usa la capa de arranque).
lee_conf() {
    local conf=$1 linea clave valor n=0 vistos=" "
    [ -f "$conf" ] || die "no existe $conf (copia adopted/opt-in/netconsole.conf.ejemplo y rellenala)"
    DEV="" LOCAL_IP="" REMOTE_IP="" REMOTE_MAC="" DRIVER=""
    while IFS= read -r linea || [ -n "$linea" ]; do
        n=$((n + 1))
        linea=${linea%$'\r'}
        [[ "$linea" =~ ^[[:space:]]*(#|$) ]] && continue
        [[ "$linea" =~ ^([A-Z_]+)=(.*)$ ]] || die "$conf:$n: no es CLAVE=valor"
        clave=${BASH_REMATCH[1]} valor=${BASH_REMATCH[2]}
        [[ "$valor" =~ ^\"(.*)\"$ ]] && valor=${BASH_REMATCH[1]}
        case "$vistos" in *" $clave "*) die "$conf:$n: $clave repetida" ;; esac
        vistos+="$clave "
        case "$clave" in
            DEV) [[ "$valor" =~ ^[A-Za-z0-9_.-]{1,15}$ ]] || die "$conf:$n: DEV no es un nombre de interfaz: '$valor'"
                DEV=$valor ;;
            LOCAL_IP) es_ipv4 "$valor" || die "$conf:$n: LOCAL_IP no es una IPv4: '$valor'"; LOCAL_IP=$valor ;;
            REMOTE_IP) es_ipv4 "$valor" || die "$conf:$n: REMOTE_IP no es una IPv4: '$valor'"; REMOTE_IP=$valor ;;
            REMOTE_MAC) valor=${valor,,}
                [[ "$valor" =~ ^([0-9a-f]{2}:){5}[0-9a-f]{2}$ ]] || die "$conf:$n: REMOTE_MAC no es una MAC: '$valor'"
                [[ ! "$valor" =~ ^(00:){5}00$ ]] || die "$conf:$n: REMOTE_MAC no puede ser cero"
                REMOTE_MAC=$valor ;;
            DRIVER) [[ "$valor" =~ ^[A-Za-z0-9_-]{1,64}$ ]] || die "$conf:$n: DRIVER no es un nombre de modulo: '$valor'"
                DRIVER=$valor ;;
            *) die "$conf:$n: clave desconocida: $clave" ;;
        esac
    done <"$conf"
    for clave in DEV LOCAL_IP REMOTE_IP REMOTE_MAC; do
        [ -n "${!clave}" ] || die "$conf: falta $clave"
    done
    [ "$LOCAL_IP" != "$REMOTE_IP" ] || die "$conf: LOCAL_IP y REMOTE_IP son la misma"
}

# El modulo netconsole lee su parametro `netconsole` de la linea de comandos como `netconsole.netconsole=`
# (modprobe recoge `modulo.param=` de /proc/cmdline). Un `netconsole=` sin prefijo solo lo consume la version
# compilada dentro del kernel; con modulo, el kernel se lo pasa a init como variable de entorno y el destino no nace.
# `+` = formato extendido, igual que extended=1 por configfs.
token_cmdline() {
    printf 'netconsole.netconsole=+%s@%s/%s,%s@%s/%s\n' \
        "$PUERTO_LOCAL" "$LOCAL_IP" "$DEV" "$PUERTO_REMOTO" "$REMOTE_IP" "$REMOTE_MAC"
}

escribe() {  # atributo valor
    printf '%s\n' "$2" >"$DESTINO/$1" || return 1
}

quita_destino() {
    [ -d "$DESTINO" ] || return 0
    # Con el destino habilitado configfs no deja tocarlo; en configfs real el atributo siempre existe.
    if [ -f "$DESTINO/enabled" ]; then printf '0\n' >"$DESTINO/enabled" 2>/dev/null || true; fi
    rmdir -- "$DESTINO" || die "no se pudo quitar $DESTINO"
    log "destino bb quitado"
}

cmd_arranca() {
    lee_conf "$CONF_DEF"
    "$MODPROBE" netconsole || die "modprobe netconsole fallo (firma, Secure Boot o modulo ausente: mira dmesg)"
    [ -d "${DESTINO%/*}" ] || die "no existe ${DESTINO%/*}: kernel sin CONFIG_NETCONSOLE_DYNAMIC o configfs sin montar"
    quita_destino
    mkdir -- "$DESTINO"
    # extended solo se puede cambiar con el destino deshabilitado: va antes que enabled.
    if ! { escribe extended 1 && escribe dev_name "$DEV" && escribe local_ip "$LOCAL_IP" \
        && escribe remote_ip "$REMOTE_IP" && escribe remote_mac "$REMOTE_MAC" \
        && escribe local_port "$PUERTO_LOCAL" && escribe remote_port "$PUERTO_REMOTO"; }; then
        quita_destino
        die "configfs rechazo un atributo del destino"
    fi
    if ! escribe enabled 1 || [ "$(cat "$DESTINO/enabled")" != 1 ]; then
        quita_destino
        die "el kernel no habilito el destino: mira dmesg (netpoll: la NIC $DEV puede no soportar polling)"
    fi
    # La marca va al ring buffer del kernel: si el testigo la recibe, el camino entero funciona.
    printf '<6>bb-netconsole-marca destino=bb dev=%s\n' "$DEV" >"$R/dev/kmsg" || log "no se pudo escribir la marca en /dev/kmsg"
    log "destino bb habilitado por $DEV (extended=1, puerto remoto $PUERTO_REMOTO)"
}

cmd_para() {
    quita_destino
    # initstate solo existe para un modulo cargable; uno compilado dentro no se descarga.
    if [ -f "$R/sys/module/netconsole/initstate" ]; then
        "$MODPROBE" -r netconsole || die "modprobe -r netconsole fallo (otro destino lo sigue usando?)"
        log "modulo netconsole descargado"
    fi
}

case "${1:-}" in
    arranca) cmd_arranca ;;
    para) cmd_para ;;
    valida) lee_conf "${2:-$CONF_DEF}"
        printf 'DEV=%s\nLOCAL_IP=%s\nREMOTE_IP=%s\nREMOTE_MAC=%s\nDRIVER=%s\n' \
            "$DEV" "$LOCAL_IP" "$REMOTE_IP" "$REMOTE_MAC" "$DRIVER" ;;
    cmdline) lee_conf "${2:-$CONF_DEF}"; token_cmdline ;;
    *) sed -n 2,10p "$0"; exit 2 ;;
esac
