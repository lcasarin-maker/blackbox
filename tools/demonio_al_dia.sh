#!/usr/bin/env bash
# Comprueba que el PROCESO VIVO de una unit arranco DESPUES de la ultima
# modificacion de su codigo.
#
# Por que existe
# --------------
# El 2026-09-26 esta maquina murio de un kernel panic que `bb-usable` estaba
# armado para cortar. El arreglo del defecto se escribe en `bin/bb-usable`, pero
# el demonio carga el codigo AL ARRANCAR: codigo correcto en disco con el
# defecto todavia en memoria es exactamente el estado en que la maquina murio, y
# desde el repo no se distingue de estar arreglado.
#
# Tambien se escribio porque ya me equivoque con esto: el 2026-09-26 reporte el
# estado de un proceso que habia muerto en el panico ocho horas antes, midiendo
# el PID viejo y presentandolo como actual.
#
# Tres salidas, y la tercera es la razon de que esto no sea un one-liner:
#   0  el proceso vivo corre el codigo actual
#   1  el proceso vivo corre codigo VIEJO -- hace falta `systemctl restart`
#   2  COULD_NOT_RUN -- no se pudo leer. No es "esta al dia" ni "esta viejo".
set -u

# --user opcional, ANTES de los posicionales: la unit vive en el gestor de
# systemd del USUARIO (~/.config/systemd/user/), no en el del sistema, y
# systemctl los trata como namespaces distintos -- sin este flag, consultar
# una unit de usuario devuelve vacio (COULD_NOT_RUN), no un error que lo diga.
# Anadido para bb-guardia-proceso.service (DEBT-PROCESO-SIN-TECHO...), que es
# unit de usuario a proposito: matar un proceso del mismo usuario no necesita
# root.
alcance=()
if [ "${1:-}" = "--user" ]; then
    alcance=(--user)
    shift
fi

unit="${1:?uso: demonio_al_dia.sh [--user] <unit> <fichero-de-codigo>}"
codigo="${2:?uso: demonio_al_dia.sh [--user] <unit> <fichero-de-codigo>}"

if ! command -v systemctl >/dev/null 2>&1; then
    echo "COULD_NOT_RUN: sin systemctl en esta maquina" >&2
    exit 2
fi
if [ ! -f "$codigo" ]; then
    echo "COULD_NOT_RUN: no existe $codigo" >&2
    exit 2
fi

if ! observacion=$(systemctl "${alcance[@]}" show "$unit" \
    -p ActiveState -p SubState -p MainPID -p ExecMainStartTimestamp 2>/dev/null); then
    echo "COULD_NOT_RUN: no se pudo consultar $unit" >&2
    exit 2
fi
activo="" subestado="" pid="" arranque=""
while IFS='=' read -r clave valor; do
    case "$clave" in
        ActiveState) activo="$valor" ;;
        SubState) subestado="$valor" ;;
        MainPID) pid="$valor" ;;
        ExecMainStartTimestamp) arranque="$valor" ;;
    esac
done <<< "$observacion"
if [ "$activo" != active ] || [ "$subestado" != running ] \
    || [[ ! "$pid" =~ ^[1-9][0-9]*$ ]] || [ ! -d "/proc/$pid" ]; then
    echo "COULD_NOT_RUN: $unit carece de proceso vivo verificable (estado=$activo/$subestado pid=$pid)" >&2
    exit 2
fi
if [ -z "$arranque" ]; then
    # Unit parada, inexistente, o un systemd que no publica la propiedad. Una
    # cadena vacia leida como numero da 0 y el veredicto saldria "viejo" por
    # ceguera, que es un COULD_NOT_RUN disfrazado de negativo.
    echo "COULD_NOT_RUN: $unit no publica ExecMainStartTimestamp (parada?)" >&2
    exit 2
fi

vivo=$(date -d "$arranque" +%s 2>/dev/null)
if [ -z "$vivo" ]; then
    echo "COULD_NOT_RUN: no se pudo parsear '$arranque'" >&2
    exit 2
fi
mod=$(stat -c %Y "$codigo")

if [ "$vivo" -gt "$mod" ]; then
    echo "$unit arranco $arranque, despues de la ultima modificacion de $codigo"
    exit 0
fi
echo "$unit arranco $arranque y $codigo se modifico despues"
if [ "${#alcance[@]}" -gt 0 ]; then
    echo "el proceso vivo corre codigo VIEJO. Lo arregla: systemctl --user restart $unit"
else
    echo "el proceso vivo corre codigo VIEJO. Lo arregla: sudo systemctl restart $unit"
fi
exit 1
