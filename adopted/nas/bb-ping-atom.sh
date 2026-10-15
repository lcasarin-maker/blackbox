#!/bin/sh
# bb-ping-atom.sh: observador externo de la ATOM, para correr en el NAS QNAP (FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01).
#
# Un ping por segundo a la ATOM; una linea por segundo en el log: `<epoch> ok` o `<epoch> fail`.
# Un ping que corre en la ATOM muere con ella; este corre en otro equipo y sobrevive al corte.
# El log se rota por numero de lineas (BB_MAX_LINEAS) para no llenar el NAS. Solo POSIX sh y busybox
# (ping -c 1 -W 1, date +%s, sleep 1, tail, wc, mv): sin bashismos.
#
# INSTALACION EN EL QNAP (la hace Luis; nada de esto esta ejecutado ni probado en el NAS real):
#   1. Copiar este archivo a una carpeta compartida del NAS, p. ej. /share/Public/bb/bb-ping-atom.sh
#      (por SMB desde la ATOM o con File Station). Editar BB_ATOM_IP y BB_LOG aqui abajo (un BB_* del entorno manda sobre el valor escrito, para pruebas).
#   2. Darle permiso de ejecucion (SSH esta cerrado: usar un Task Scheduler de una sola vez o la
#      consola del panel web):  chmod 755 /share/Public/bb/bb-ping-atom.sh
#   3. Arranque automatico, UNA de dos vias:
#      a) Task Scheduler / Programador de tareas (panel web, Panel de control): tarea de usuario root,
#         disparador "al arrancar", comando:
#             nohup /share/Public/bb/bb-ping-atom.sh >/dev/null 2>&1 &
#      b) autorun.sh: en QTS hay que habilitar "Run user defined processes during startup"
#         (Panel de control > Hardware > General) y poner el mismo comando en autorun.sh de la
#         particion de configuracion (el procedimiento exacto depende de la version de QTS;
#         ver la documentacion de QNAP "Running Your Own Application at Startup").
#   4. Arrancarlo ahora sin reiniciar el NAS:  nohup /share/Public/bb/bb-ping-atom.sh >/dev/null 2>&1 &
#   5. Leerlo:  tail -n 5 /share/Public/bb/ping-atom.log   (cada linea: epoch y ok|fail)
#      Un solo proceso a la vez: el script rehusa arrancar si ya hay otro (directorio de bloqueo).
#   6. En la ATOM, el `sync` de tools/observador_ping.py lo trae por smbclient cada 5 min.
#
# El reloj del NAS decide los epoch: si esta desviado, la hora de "ultima respuesta" tambien. Hay que
# tenerlo en NTP (QTS: Panel de control > Hora del sistema).

BB_ATOM_IP="${BB_ATOM_IP:-192.168.1.50}"                       # EDITAR: IP o nombre de la ATOM
BB_LOG="${BB_LOG:-/share/Public/bb/ping-atom.log}"         # EDITAR: ruta del log en el NAS
BB_MAX_LINEAS="${BB_MAX_LINEAS:-172800}"                            # 2 dias a 1 linea/s (~2.5 MB)
BB_CADA_N="${BB_CADA_N:-600}"                                   # cada cuantas lineas se comprueba la rotacion

LOCK="$BB_LOG.lock"
if ! mkdir "$LOCK" 2>/dev/null; then
    pid=$(cat "$LOCK/pid" 2>/dev/null)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        echo "bb-ping-atom: ya corre (pid $pid)" >&2
        exit 1
    fi
    # el bloqueo es de un proceso muerto: se retoma
    rm -rf "$LOCK"
    mkdir "$LOCK" || exit 1
fi
echo "$$" >"$LOCK/pid"
trap 'rm -rf "$LOCK"; exit 0' INT TERM

n=0
while :; do
    t=$(date +%s)
    if ping -c 1 -W 1 "$BB_ATOM_IP" >/dev/null 2>&1; then
        echo "$t ok" >>"$BB_LOG"
    else
        echo "$t fail" >>"$BB_LOG"
    fi
    n=$((n + 1))
    if [ "$n" -ge "$BB_CADA_N" ]; then
        n=0
        total=$(wc -l <"$BB_LOG")
        if [ "$total" -gt "$BB_MAX_LINEAS" ]; then
            tail -n "$BB_MAX_LINEAS" "$BB_LOG" >"$BB_LOG.tmp" && mv "$BB_LOG.tmp" "$BB_LOG"
        fi
    fi
    # un ping fallido ya consumio ~1 s (-W 1): solo se duerme si el segundo no ha cambiado
    [ "$(date +%s)" = "$t" ] && sleep 1
done
