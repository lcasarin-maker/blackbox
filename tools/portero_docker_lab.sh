#!/usr/bin/env bash
# portero_docker_lab.sh -- daemon de Docker de LABORATORIO para probar el
# envoltorio de runtime OCI de bb (tools/bb_oci_runtime.py) sin tocar produccion.
#
# Uso (lo ejecuta Luis con sudo; NIVEL 2 de FEATURE-CONTENEDORES-TOPE-PROPIO-Y-RUNTIME-OCI-01):
#   sudo bash tools/portero_docker_lab.sh up      # levanta containerd + dockerd de laboratorio
#   sudo bash tools/portero_docker_lab.sh prueba  # crea contenedores de prueba y mide su cgroup
#   sudo bash tools/portero_docker_lab.sh status  # estado (no necesita root para casi nada)
#   sudo bash tools/portero_docker_lab.sh down    # apaga y borra TODO lo que up creo
#
# POR QUE UN SEGUNDO DAEMON Y NO EL DE PRODUCCION. El dockerd de produccion
# (pid de /run/docker.pid, socket /var/run/docker.sock) sirve nemotron-server,
# atlas-pgvector, librechat, mongo-librechat y proyecto-A-pg a otras sesiones.
# Cambiarle el runtime exige reiniciarlo. Aqui todo es propio: socket, data-root,
# exec-root, pidfile, daemon.json, containerd (con su socket, root y state), el
# namespace de containerd y el slice de cgroup.
#
# POR QUE UN CONTAINERD PROPIO. El dockerd de produccion usa el containerd del
# sistema (--containerd=/run/containerd/containerd.sock, medido 2026-10-12). Un
# segundo dockerd que se colgara de ese containerd compartiria su namespace
# `moby` con produccion. Este script arranca otro containerd con el plugin CRI y
# el NRI desactivados (el NRI escucharia en /var/run/nri/nri.sock, el mismo del
# containerd del sistema).
#
# POR QUE `bblab.slice` Y NO `docker-lab.slice`. En systemd el guion es jerarquia:
# `docker-lab.slice` es HIJO de `docker.slice` y compartiria su tope de 14 GiB
# con vLLM. `bblab.slice` cuelga de la raiz y lleva su propio tope.
#
# UNICO CONTACTO CON PRODUCCION: `docker save` de una imagen (lectura) para
# cargarla en el laboratorio. Ningun otro comando habla con el socket de produccion.

set -euo pipefail

REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
WRAPPER="$REPO/tools/bb_oci_runtime.py"
EVIDENCIA="$REPO/tasks/evidence/FEATURE-CONTENEDORES-TOPE-PROPIO-Y-RUNTIME-OCI-01"

RUN_DIR=/run/bb-lab
LAB_SOCK=${BB_LAB_SOCK:-$RUN_DIR/docker.sock}  # sobreescribible SOLO para probar la guarda
LAB_HOST="unix://$LAB_SOCK"
DATA_ROOT=/var/lib/bb-docker-lab
EXEC_ROOT=/run/bb-docker-lab
PIDFILE=$RUN_DIR/dockerd.pid
CONF_DIR=$RUN_DIR/conf
# /run esta montado noexec (medido 2026-10-12: "fork/exec .../bb-runtime: permission denied"): el lanzador vive en el data-root.
BIN_DIR=$DATA_ROOT/bin
CTRD_SOCK=$RUN_DIR/containerd.sock
CTRD_PID=$RUN_DIR/containerd.pid
CTRD_ROOT=$DATA_ROOT/containerd
CTRD_STATE=$RUN_DIR/containerd-state
LAB_DATA=$DATA_ROOT/blackbox-data
SLICE=bblab.slice
NS=bblab
IMAGE=${BB_LAB_IMAGE:-postgres:16-alpine}
REAL_RUNTIME=${BB_LAB_REAL_RUNTIME:-nvidia-container-runtime}

PROD_SOCKS=(/var/run/docker.sock /run/docker.sock)
PROD_DATA_ROOT=/var/lib/docker
PROD_CTRD_SOCK=/run/containerd/containerd.sock

die() { echo "[lab] ERROR: $*" >&2; exit 1; }
log() { echo "[lab] $*"; }

# Guarda: antes de CADA subcomando. Resuelve enlaces simbolicos, asi que un
# socket de laboratorio que apunte al de produccion se detecta.
guarda() {
    local real p
    real=$(readlink -m "$LAB_SOCK")
    for p in "${PROD_SOCKS[@]}"; do
        [ "$real" != "$(readlink -m "$p")" ] ||
            die "el socket del laboratorio ($LAB_SOCK -> $real) es el de produccion ($p); no se actua"
    done
    [ "$(readlink -m "$DATA_ROOT")" != "$PROD_DATA_ROOT" ] || die "data-root del laboratorio es el de produccion"
    [ "$(readlink -m "$CTRD_SOCK")" != "$(readlink -m "$PROD_CTRD_SOCK")" ] ||
        die "el containerd del laboratorio es el del sistema"
}

# Todo docker del laboratorio pasa por aqui: -H explicito, sin DOCKER_HOST ni contexto.
labdocker() {
    guarda
    env -u DOCKER_HOST -u DOCKER_CONTEXT docker -H "$LAB_HOST" "$@"
}

# Prueba positiva de que el daemon al otro lado es el de laboratorio.
es_lab() {
    local raiz
    raiz=$(labdocker info --format '{{.DockerRootDir}}' 2>/dev/null) || return 1
    [ "$raiz" = "$DATA_ROOT" ]
}

asegura_lab() {
    es_lab || die "el daemon en $LAB_SOCK no responde o no tiene DockerRootDir=$DATA_ROOT; no se actua"
}

requiere_root() { [ "$(id -u)" = 0 ] || die "'$1' necesita root: sudo bash $0 $1"; }

# /proc/<pid> y no `kill -0`: sin root, kill -0 a un proceso de root da EPERM y `status` decia "abajo" con el daemon arriba (medido 2026-10-12).
vivo() { [ -f "$1" ] && [ -d "/proc/$(cat "$1")" ]; }

# Espera acotada a que exista un socket: 60 x 0.5 s.
espera_socket() {
    for _ in $(seq 1 60); do
        [ -S "$1" ] && return 0
        sleep 0.5
    done
    die "el socket $1 no aparecio en 30 s (log: $2)"
}

escribe_configs() {
    mkdir -p "$CONF_DIR" "$BIN_DIR" "$CTRD_STATE" "$CTRD_ROOT" "$LAB_DATA" "$EXEC_ROOT"
    cat >"$CONF_DIR/containerd.toml" <<EOF
version = 3
root = "$CTRD_ROOT"
state = "$CTRD_STATE"
disabled_plugins = ["io.containerd.grpc.v1.cri", "io.containerd.cri.v1.images", "io.containerd.cri.v1.runtime", "io.containerd.nri.v1.nri"]
[grpc]
  address = "$CTRD_SOCK"
[ttrpc]
  address = "$CTRD_SOCK.ttrpc"
[debug]
  address = "$RUN_DIR/containerd-debug.sock"
[metrics]
  address = ""
EOF
    local py
    py=$(command -v python3) || die "no hay python3"
    cat >"$BIN_DIR/bb-runtime" <<EOF
#!/bin/sh
# Lanzador del envoltorio para el daemon de laboratorio (daemon.json no pasa entorno).
export BLACKBOX_DATA="$LAB_DATA"
export BB_OCI_REAL_RUNTIME="$REAL_RUNTIME"
exec "$py" "$WRAPPER" "\$@"
EOF
    chmod 0755 "$BIN_DIR/bb-runtime"
    ! findmnt -T "$BIN_DIR" -no OPTIONS | grep -qw noexec || die "$BIN_DIR esta en un montaje noexec: el runtime no se podria ejecutar"
    cat >"$CONF_DIR/daemon.json" <<EOF
{
  "runtimes": {"bb": {"path": "$BIN_DIR/bb-runtime"}},
  "default-runtime": "bb",
  "cgroup-parent": "$SLICE",
  "exec-opts": ["native.cgroupdriver=systemd"]
}
EOF
}

cmd_up() {
    requiere_root up
    guarda
    vivo "$PIDFILE" && die "ya hay un dockerd de laboratorio (pid $(cat "$PIDFILE"))"
    [ -f "$WRAPPER" ] || die "no existe $WRAPPER"
    mkdir -p "$RUN_DIR"
    escribe_configs

    # Tope del slice del laboratorio: --runtime (vive en /run, no en /etc; `down` lo revierte).
    # BB_LAB_MEM sube el tope del laboratorio (por defecto 1G); nunca mas de 24G: es un slice de PRUEBA dentro de una maquina cuyo
    # vLLM de produccion ya usa ~41 GiB de GPU, y la estampida del 11-oct fue justamente falta de techo.
    local mem_bytes
    mem_bytes=$(numfmt --from=iec "${BB_LAB_MEM:-1G}") || die "BB_LAB_MEM invalido: ${BB_LAB_MEM:-}"
    [ "$mem_bytes" -le $((24 * 1024 * 1024 * 1024)) ] || die "BB_LAB_MEM=${BB_LAB_MEM} supera el maximo de 24G"
    systemctl start "$SLICE"
    systemctl set-property --runtime "$SLICE" MemoryMax="$mem_bytes" MemorySwapMax=0 TasksMax=2048
    [ "$(cat "/sys/fs/cgroup/$SLICE/memory.max")" = "$mem_bytes" ] ||
        die "$SLICE no quedo con memory.max=$mem_bytes: $(cat "/sys/fs/cgroup/$SLICE/memory.max" 2>&1)"

    DOCKER0_ANTES=0; ip link show docker0 >/dev/null 2>&1 && DOCKER0_ANTES=1
    log "arrancando containerd de laboratorio ($CTRD_SOCK); docker0 de produccion antes: $DOCKER0_ANTES"
    setsid containerd --config "$CONF_DIR/containerd.toml" >"$RUN_DIR/containerd.log" 2>&1 &
    echo $! >"$CTRD_PID"
    espera_socket "$CTRD_SOCK" "$RUN_DIR/containerd.log"

    log "arrancando dockerd de laboratorio ($LAB_SOCK)"
    setsid dockerd \
        --config-file "$CONF_DIR/daemon.json" \
        --host "$LAB_HOST" \
        --data-root "$DATA_ROOT" \
        --exec-root "$EXEC_ROOT" \
        --pidfile "$PIDFILE" \
        --containerd "$CTRD_SOCK" \
        --containerd-namespace "$NS" \
        --containerd-plugins-namespace "$NS-plugins" \
        --bridge=bblab0 --bip=172.31.250.1/24 --iptables=false --ip6tables=false --ip-forward=false \
        --ip-masq=false --userland-proxy=false \
        >"$RUN_DIR/dockerd.log" 2>&1 &
    espera_socket "$LAB_SOCK" "$RUN_DIR/dockerd.log"
    # GUARDA: el laboratorio NO puede tocar el puente de produccion (2026-10-12 07:55:30: `--bridge=none` borro docker0 del host y
    # atlas-pgvector quedo sin red 5 h hasta que Luis reinicio Docker a las 13:16). Si docker0 existia antes de `up` y ya no, se aborta.
    if [ "$DOCKER0_ANTES" = 1 ] && ! ip link show docker0 >/dev/null 2>&1; then
        log "ERROR: docker0 de PRODUCCION desaparecio al arrancar el laboratorio; apagando el laboratorio"
        kill -TERM "$(cat "$PIDFILE")" 2>/dev/null || true
        die "el laboratorio borro docker0: no se continua (reinicia Docker de produccion para recrearlo)"
    fi
    for _ in $(seq 1 60); do labdocker info >/dev/null 2>&1 && break; sleep 0.5; done
    asegura_lab

    log "cargando $IMAGE desde produccion (docker save, solo lectura)"
    env -u DOCKER_HOST -u DOCKER_CONTEXT docker -H "unix://${PROD_SOCKS[0]}" save "$IMAGE" | labdocker load
    log "arriba. Runtimes: $(labdocker info --format '{{json .Runtimes}}' | tr -d '\n' | cut -c1-200)"
    log "default runtime: $(labdocker info --format '{{.DefaultRuntime}}')"
}

cmd_status() {
    guarda
    if vivo "$CTRD_PID"; then log "containerd lab: vivo (pid $(cat "$CTRD_PID"))"; else log "containerd lab: abajo"; fi
    if vivo "$PIDFILE"; then log "dockerd lab: vivo (pid $(cat "$PIDFILE"))"; else log "dockerd lab: abajo"; fi
    if [ -S "$LAB_SOCK" ] && labdocker info --format '{{.DockerRootDir}} {{.DefaultRuntime}} {{.CgroupDriver}}' 2>/dev/null; then
        labdocker ps -a --format '{{.Names}} {{.Status}}'
    else
        log "sin respuesta en $LAB_SOCK"
    fi
    if [ -d "/sys/fs/cgroup/$SLICE" ]; then
        log "$SLICE memory.max=$(cat "/sys/fs/cgroup/$SLICE/memory.max") pids.max=$(cat "/sys/fs/cgroup/$SLICE/pids.max")"
    else
        log "$SLICE: sin cgroup"
    fi
    [ -f "$LAB_DATA/oci_runtime.jsonl" ] && tail -n 5 "$LAB_DATA/oci_runtime.jsonl"
    return 0
}

# --- prueba ---------------------------------------------------------------
FALLOS=0
NO_CORRIO=0
SALIDA=""

anota() { echo "$*"; SALIDA+="$*"$'\n'; }

cgroup_de() {  # ruta del cgroup v2 del proceso principal del contenedor
    local pid
    pid=$(labdocker inspect -f '{{.State.Pid}}' "$1" 2>/dev/null) || return 1
    [ "$pid" -gt 0 ] || return 1
    echo "/sys/fs/cgroup$(sed -n 's/^0:://p' "/proc/$pid/cgroup")"
}

# caso_corre <nombre> <mem> <swap> <pids> <docker run args...>: debe ARRANCAR con esos topes.
caso_corre() {
    local nombre=$1 emem=$2 eswap=$3 epids=$4 cg salida
    shift 4
    if ! salida=$(labdocker run -d --network none --name "$nombre" "$@" --entrypoint sleep "$IMAGE" 300 2>&1); then
        anota "COULD_NOT_RUN $nombre: docker run fallo: $salida"
        NO_CORRIO=$((NO_CORRIO + 1)); return
    fi
    if ! cg=$(cgroup_de "$nombre"); then
        anota "COULD_NOT_RUN $nombre: sin pid/cgroup"; NO_CORRIO=$((NO_CORRIO + 1)); return
    fi
    local mem swap pids
    mem=$(cat "$cg/memory.max"); swap=$(cat "$cg/memory.swap.max"); pids=$(cat "$cg/pids.max")
    if [ "$mem $swap" = "$emem $eswap" ] && { [ "$epids" = "*" ] || [ "$pids" = "$epids" ]; }; then
        anota "PASS $nombre: $cg memory.max=$mem memory.swap.max=$swap pids.max=$pids"
    else
        anota "FAIL $nombre: $cg memory.max=$mem memory.swap.max=$swap pids.max=$pids (esperado $emem $eswap $epids)"
        FALLOS=$((FALLOS + 1))
    fi
}

# caso_rechazo <nombre> <docker run args...>: el envoltorio debe RECHAZARLO.
caso_rechazo() {
    local nombre=$1 salida id n
    shift
    if salida=$(labdocker run -d --network none --name "$nombre" "$@" --entrypoint sleep "$IMAGE" 300 2>&1); then
        anota "FAIL $nombre: arranco y debia rechazarse ($salida)"; FALLOS=$((FALLOS + 1)); return
    fi
    id=$(labdocker inspect -f '{{.Id}}' "$nombre" 2>/dev/null || echo "?")
    n=$(grep -F "\"contenedor\": \"$id\"" "$LAB_DATA/oci_runtime.jsonl" 2>/dev/null | grep -c '"decision": "RECHAZAR"' || true)
    if [ "${n:-0}" -ge 1 ]; then
        anota "PASS $nombre: rechazado por el envoltorio (registro RECHAZAR x$n). docker dijo: ${salida//$'\n'/ }"
    else
        anota "FAIL $nombre: docker run fallo pero el registro no tiene RECHAZAR para $id: ${salida//$'\n'/ }"
        FALLOS=$((FALLOS + 1))
    fi
}

limpia_prueba() {
    local c
    for c in bblab-control bblab-sintope bblab-estricto bblab-gpu-sin-etiqueta bblab-gpu-desborda; do
        labdocker rm -f "$c" >/dev/null 2>&1 || true
    done
}

cmd_prueba() {
    requiere_root prueba
    guarda
    asegura_lab
    limpia_prueba
    trap limpia_prueba EXIT
    local G=$((1024 * 1024 * 1024))
    anota "# prueba nivel 2 $(date -Iseconds) -- daemon $LAB_SOCK, runtime real $REAL_RUNTIME, imagen $IMAGE"
    # Control negativo: runc directo, sin envoltorio. Debe quedar SIN tope:
    # prueba que la medicion puede salir 'max'.
    # pids '*': sin envoltorio los fija el DefaultTasksMax de systemd (152777 medido), no Docker.
    caso_corre bblab-control max max '*' --runtime runc
    caso_corre bblab-sintope $((3 * G)) 0 2048
    caso_corre bblab-estricto 67108864 0 16 --memory 64m --memory-swap 64m --pids-limit 16
    caso_rechazo bblab-gpu-sin-etiqueta -e NVIDIA_VISIBLE_DEVICES=all
    caso_rechazo bblab-gpu-desborda -e NVIDIA_VISIBLE_DEVICES=all --annotation bb.gpu_budget_gib=60
    anota "fallos=$FALLOS could_not_run=$NO_CORRIO"
    anota "--- registro del envoltorio (ultimas 12 lineas de $LAB_DATA/oci_runtime.jsonl)"
    anota "$(tail -n 12 "$LAB_DATA/oci_runtime.jsonl" 2>/dev/null || echo 'NOT_COLLECTED: sin registro')"

    mkdir -p "$EVIDENCIA"
    local f
    f="$EVIDENCIA/prueba-nivel2-$(date +%Y%m%dT%H%M%S).txt"
    printf '%s' "$SALIDA" >"$f"
    if [ "$FALLOS" -eq 0 ] && [ "$NO_CORRIO" -eq 0 ]; then
        printf '\n## Nivel 2 (%s)\n\nruntime_oci_probado: 5 de 5 casos, control negativo incluido; salida literal en %s.\n' \
            "$(date -Iseconds)" "$(basename "$f")" >>"$EVIDENCIA/medicion.txt"
        log "PASS: anotado runtime_oci_probado en $EVIDENCIA/medicion.txt"
    else
        log "NO probado: fallos=$FALLOS could_not_run=$NO_CORRIO; salida en $f (medicion.txt no se toca)"
    fi
    if [ -n "${SUDO_USER:-}" ]; then chown -R "$SUDO_USER:" "$EVIDENCIA"; fi
    [ "$FALLOS" -eq 0 ] && [ "$NO_CORRIO" -eq 0 ]
}

# --- vllm: arranca vLLM REAL (modelo chico) bajo el envoltorio, mide memoria y lo apaga -------------
# Uso: sudo BB_LAB_MEM=16G BB_LAB_IMAGE=vllm/vllm-openai:v0.27.1 bash tools/portero_docker_lab.sh up
#      sudo bash tools/portero_docker_lab.sh vllm [modelo=qwen3-8b-nvfp4] [gpu_gib=12]
# Mide: tope de cgroup que dejo el envoltorio, pico de cgroup, MemAvailable minimo del anfitrion a 1 Hz durante la carga,
# si el servidor responde una peticion, y que el contenedor se apaga y deja el lab limpio. Aborta (docker stop) si
# MemAvailable baja de 12 GiB: el lab NO puede repetir lo que el techo evita.
cmd_vllm() {
    requiere_root vllm
    guarda
    asegura_lab
    local modelo=${1:-qwen3-8b-nvfp4} gpu_gib=${2:-12} n=bblab-vllm cg t0 min_kb=999999999 estado=""
    local ruta="/srv/ai/models/llm/$modelo"
    [ -d "$ruta" ] || die "no existe el modelo $ruta"
    case "$IMAGE" in vllm/*) ;; *)
        # `up` carga la imagen de BB_LAB_IMAGE; este subcomando suele correr en OTRO sudo sin esa variable (fallo de la primera instruccion, 2026-10-12): busca una ya cargada
        IMAGE=$(labdocker images --format '{{.Repository}}:{{.Tag}}' | grep '^vllm/' | head -1)
        [ -n "$IMAGE" ] || die "no hay imagen vllm/* cargada en el laboratorio (up con BB_LAB_IMAGE=vllm/vllm-openai:<tag>)";;
    esac
    labdocker rm -f "$n" >/dev/null 2>&1 || true
    local util
    util=$(awk -v g="$gpu_gib" 'BEGIN{printf "%.3f", g/121.7}')
    labdocker run -d --name "$n" --network none -e NVIDIA_VISIBLE_DEVICES=all -e VLLM_HOST_IP=127.0.0.1 \
        --annotation "bb.gpu_budget_gib=$gpu_gib" -v "/srv/ai/models:/models:ro" \
        "$IMAGE" "/models/llm/$modelo" --served-model-name prueba --gpu-memory-utilization "$util" \
        --max-model-len 4096 --max-num-seqs 4 --host 127.0.0.1 --port 8000 >/dev/null || { anota "COULD_NOT_RUN vllm: docker run fallo (¿la imagen no tiene el entrypoint de vllm serve? ¿GPU sin anotacion?)"; return 1; }
    cg=$(cgroup_de "$n") || { anota "COULD_NOT_RUN vllm: sin cgroup"; return 1; }
    anota "# vllm $modelo gpu_gib=$gpu_gib util=$util imagen=$IMAGE"
    anota "cgroup $cg memory.max=$(cat "$cg/memory.max") swap.max=$(cat "$cg/memory.swap.max") pids.max=$(cat "$cg/pids.max")"
    t0=$(date +%s)
    while [ $(( $(date +%s) - t0 )) -lt 900 ]; do
        local av; av=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
        [ "$av" -lt "$min_kb" ] && min_kb=$av
        if [ "$av" -lt $((12 * 1024 * 1024)) ]; then estado="ABORTADO: MemAvailable $((av / 1024)) MiB < 12 GiB"; break; fi
        if labdocker exec "$n" python3 -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2).status==200 else 1)" >/dev/null 2>&1; then estado="LISTO en $(( $(date +%s) - t0 )) s"; break; fi
        labdocker inspect -f '{{.State.Running}}' "$n" 2>/dev/null | grep -q true || { estado="MURIO: $(labdocker logs --tail 5 "$n" 2>&1 | tr '\n' ' ' | cut -c1-300)"; break; }
        sleep 1  # blocking-sleep: espera acotada (900 s) del arranque de un modelo, 1 Hz para medir MemAvailable -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01  # sunset-reviewed: 3.3 -- re-revisado 2026-10-13 contra 3.2: `git blame` de la linea 348 (804713d5) es anterior al bump 3.2.0 (e8e5aa8d), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.1: `git blame` de la linea 348 (93850773) es anterior al bump 3.1.0 (7a5bd48b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 3.0: `git blame` de la linea 348 (92598b79) es anterior al bump 2.9.1 (ab63e2b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 2.9: `git blame` de la linea 340 (831ce38f) no cambio desde su revision anterior; la razon sigue valiendo: revalidado 2026-10-12: arnes de laboratorio de una pasada ; re-revisado 2026-10-13 contra 3.1: la linea no cambio desde 20256295 (git blame de esta linea)
    done
    [ -n "$estado" ] || estado="TIMEOUT 900 s sin /health"
    anota "estado: $estado"
    anota "pico del cgroup: memory.peak=$(cat "$cg/memory.peak" 2>/dev/null || echo NOT_COLLECTED) bytes; MemAvailable minimo del anfitrion: $((min_kb / 1024)) MiB"
    case "$estado" in LISTO*)
        anota "peticion: $(labdocker exec "$n" python3 -c "import urllib.request,json;r=urllib.request.Request('http://127.0.0.1:8000/v1/completions',json.dumps({'model':'prueba','prompt':'1+1=','max_tokens':8}).encode(),{'Content-Type':'application/json'});print(json.load(urllib.request.urlopen(r,timeout=120))['choices'][0]['text'])" 2>&1 | tail -1 | cut -c1-120)";; esac
    labdocker rm -f "$n" >/dev/null 2>&1 || true
    mkdir -p "$EVIDENCIA"
    printf '%s' "$SALIDA" >"$EVIDENCIA/prueba-vllm-$(date +%Y%m%dT%H%M%S).txt"
    if [ -n "${SUDO_USER:-}" ]; then chown -R "$SUDO_USER:" "$EVIDENCIA"; fi
    case "$estado" in LISTO*) return 0 ;; *) return 1 ;; esac
}

# Mata un proceso del laboratorio solo si su cmdline nombra rutas del laboratorio.
para() {
    local pidf=$1 marca=$2 pid
    vivo "$pidf" || return 0
    pid=$(cat "$pidf")
    tr '\0' ' ' <"/proc/$pid/cmdline" | grep -qF -- "$marca" ||
        die "pid $pid de $pidf no lleva '$marca' en su cmdline; no se mata"
    kill -TERM "$pid"
    for _ in $(seq 1 60); do kill -0 "$pid" 2>/dev/null || return 0; sleep 0.5; done
    log "pid $pid sigue vivo tras 30 s; KILL"
    kill -KILL "$pid" 2>/dev/null || true
}

cmd_down() {
    requiere_root down
    guarda
    if [ -S "$LAB_SOCK" ] && es_lab; then
        local ids
        mapfile -t ids < <(labdocker ps -aq)
        [ "${#ids[@]}" -eq 0 ] || labdocker rm -f "${ids[@]}" >/dev/null
    fi
    para "$PIDFILE" "$CONF_DIR/daemon.json"
    para "$CTRD_PID" "$CONF_DIR/containerd.toml"
    local m
    findmnt -rn -o TARGET | { grep -E "^($DATA_ROOT|$EXEC_ROOT|$RUN_DIR)(/|$)" || true; } | sort -r | while read -r m; do
        umount -l "$m" || log "no se pudo desmontar $m"
    done
    ip link show bblab0 >/dev/null 2>&1 && ip link del bblab0 || true
    systemctl stop "$SLICE" 2>/dev/null || true
    systemctl revert "$SLICE" 2>/dev/null || true
    rm -rf --one-file-system "$DATA_ROOT" "$EXEC_ROOT" "$RUN_DIR"
    local resto=0 p
    for p in "$DATA_ROOT" "$EXEC_ROOT" "$RUN_DIR" "/sys/fs/cgroup/$SLICE"; do
        if [ -e "$p" ]; then log "RESTO: $p"; resto=$((resto + 1)); fi
    done
    log "down: restos=$resto"
    [ "$resto" -eq 0 ]
}

case "${1:-}" in
    up) cmd_up ;;
    status) cmd_status ;;
    prueba) cmd_prueba ;;
    vllm) shift; cmd_vllm "$@" ;;
    down) cmd_down ;;
    *) echo "uso: sudo bash $0 up|status|prueba|vllm|down" >&2; exit 2 ;;
esac
