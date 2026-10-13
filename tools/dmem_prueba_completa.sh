#!/usr/bin/env bash
# dmem_prueba_completa.sh -- UNA corrida que responde todo lo que se puede medir con el modulo parcheado cargado, para no
# reiniciar a ciegas (FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01).
# Uso (root):  sudo bash tools/dmem_prueba_completa.sh [--contenedor]
# Por cada forma de pedir memoria de GPU: ¿dmem.current sube?  (esperado por el barrido de ioctl del 2026-10-12:
#   cudaMalloc, expandable_segments, cudaMallocAsync y CUDA graph entran por la clase RM 0x3e y DEBEN cobrar;
#   pinned (cudaHostAlloc) y managed (UVM) NO pasan por 0x3e y NO cobran: se miden para tenerlos escritos).
# Ademas: rechazo sobre dmem.max con control negativo (sin tope y bajo tope), fuga (dmem.current al salir = 0), y lectura
# SOLO LECTURA del cobro de los contenedores en marcha. --contenedor suma una prueba con un contenedor efimero (usa GPU ~1 GiB).
# No toca ningun cgroup de produccion: solo lee sus dmem.current.
# rc 0 = todo lo esperado; 3 sin region; 4 un caso que debia cobrar no cobra; 5 no rechaza sobre el tope; 6 control fallo; 7 fuga.
set -uo pipefail
RAIZ=${BB_DMEM_RAIZ:-/sys/fs/cgroup}
PY=${BB_DMEM_PYTHON:-python3}
CONTENEDOR=0; [ "${1:-}" = "--contenedor" ] && CONTENEDOR=1
log() { echo "[dmem-completa] $*"; }
[ "$(id -u)" = 0 ] || { echo "necesita root" >&2; exit 2; }
CAP=$(cat "$RAIZ/dmem.capacity" 2>/dev/null || true)
[ -n "$CAP" ] || { log "SIN region dmem: corre el modulo de Canonical o el parche no dio region"; exit 3; }
REGION=$(echo "$CAP" | awk 'NR==1{print $1}')
log "region: $REGION ($(echo "$CAP" | awk 'NR==1{print $2}') bytes); modulo: $(modinfo -F filename nvidia 2>/dev/null)"
grep -qw dmem "$RAIZ/cgroup.subtree_control" || echo "+dmem" >"$RAIZ/cgroup.subtree_control"
if [ -n "${SUDO_USER:-}" ]; then
    SITIO=$(sudo -u "$SUDO_USER" "$PY" -c 'import site; print(site.getusersitepackages())' 2>/dev/null || true)
    [ -z "$SITIO" ] || export PYTHONPATH="$SITIO:${PYTHONPATH:-}"
fi
T=$(mktemp -d); CGS=()
limpia() { for c in "${CGS[@]}"; do rmdir "$RAIZ/$c" 2>/dev/null || true; done; rm -rf "$T"; docker rm -f bb-dmem-ct >/dev/null 2>&1 || true; }
trap limpia EXIT
cat >"$T/pide.py" <<'PY'
import ctypes, os, sys
import torch
caso, mib = sys.argv[1], int(sys.argv[2])
n = mib << 20
cg = open("/proc/self/cgroup").read().strip().split("::")[1]
def actual():
    return open("/sys/fs/cgroup%s/dmem.current" % cg).read().strip().replace("\n", ";")
try:
    torch.zeros(1, device="cuda"); torch.cuda.synchronize()          # el contexto no cuenta: se mide la asignacion
    base = actual()
    if caso in ("empty", "expandable", "async"):
        x = torch.empty(n, dtype=torch.uint8, device="cuda")
    elif caso == "pinned":
        x = torch.empty(n, dtype=torch.uint8, pin_memory=True)
    elif caso == "managed":
        p = ctypes.c_void_p(); r = ctypes.CDLL("libcudart.so.13").cudaMallocManaged(ctypes.byref(p), ctypes.c_size_t(n), 1)
        assert r == 0, "cudaMallocManaged rc=%s" % r
    elif caso == "graph":
        s = torch.cuda.Stream(); g = torch.cuda.CUDAGraph()
        with torch.cuda.stream(s):
            torch.ones(8, device="cuda") * 2
        torch.cuda.synchronize()
        with torch.cuda.graph(g):
            y = torch.empty(n, dtype=torch.uint8, device="cuda"); y.fill_(1)
    torch.cuda.synchronize()
    print("OK base=%s despues=%s" % (base, actual()))
except Exception as e:
    print("OOM" if "out of memory" in str(e).lower() else "ERR " + str(e)[:100])
PY
corre() {  # $1 cgroup  $2 caso  $3 MiB  $4 env extra opcional
    mkdir -p "$RAIZ/$1"; CGS+=("$1")
    local salida
    salida=$(sh -c "echo \$\$ >'$RAIZ/$1/cgroup.procs'; exec env ${4:-} '$PY' '$T/pide.py' '$2' '$3'" 2>&1 || true)
    echo "$salida" | grep -E '^(OK|OOM|ERR)' | tail -1 || true
    echo "$salida" | grep -qE '^(OK|OOM|ERR)' || echo "ERR sin veredicto: $(echo "$salida" | tail -2 | tr '\n' ' ')"
}
cobrado() {  # bytes cobrados por la asignacion = despues - base (el contexto CUDA ya cobra ~206 MB al crearse)
    local a d
    a=$(echo "$1" | sed -n 's/.*base=[^ ]* \([0-9]*\) despues=.*/\1/p'); d=$(echo "$1" | sed -n 's/.*despues=[^ ]* \([0-9]*\).*/\1/p')
    [ -n "$a" ] && [ -n "$d" ] && echo $((d - a)) || echo 0
}
MIB=256; MINIMO=$((MIB * 1048576 * 3 / 4)); RC=0   # 75 %: cudaMallocAsync cobra ~87 % de lo pedido (224 de 256 MiB, medido 2026-10-12); pinned/managed cobran 0
declare -A ESPERA=( [empty]=cobra [expandable]=cobra [async]=cobra [graph]=cobra [pinned]=no_cobra [managed]=no_cobra )
log "--- 1. que formas de pedir memoria cobran (pide $MIB MiB cada una, cgroup sin tope)"
for caso in empty expandable async graph pinned managed; do
    envx=""
    [ "$caso" = expandable ] && envx="PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"
    [ "$caso" = async ] && envx="PYTORCH_CUDA_ALLOC_CONF=backend:cudaMallocAsync"
    r=$(corre "bb-dmem-$caso" "$caso" "$MIB" "$envx")
    b=$(cobrado "$r"); b=${b:-0}
    if [ "$b" -ge "$MINIMO" ]; then real=cobra; else real=no_cobra; fi
    marca="ok"; [ "$real" = "${ESPERA[$caso]}" ] || { marca="INESPERADO"; [ "${ESPERA[$caso]}" = cobra ] && RC=4; }
    log "  $caso: esperado=${ESPERA[$caso]} real=$real ($b bytes) [$marca]  <- $r"
done
log "--- 2. rechazo sobre dmem.max, con controles (el rechazo llega como OOM o como cudaErrorUnknown: el libcuda de 580 no conoce el estado 0x8D)"
mkdir -p "$RAIZ/bb-dmem-tope" "$RAIZ/bb-dmem-holgado"; CGS+=("bb-dmem-tope" "bb-dmem-holgado")
echo "$REGION 512M" >"$RAIZ/bb-dmem-tope/dmem.max"; echo "$REGION 2048M" >"$RAIZ/bb-dmem-holgado/dmem.max"
CON=$(corre bb-dmem-tope empty 1024); LIBRE=$(corre bb-dmem-libre empty 1024); CABE=$(corre bb-dmem-holgado empty 1024)
log "  tope 512M, pide 1024 MiB:               ${CON:0:110}"
log "  control sin tope, pide 1024 MiB:        ${LIBRE%% *}   (debe ser OK)"
log "  control tope 2048M, pide 1024 MiB:      ${CABE%% *}   (debe ser OK)"
case "$LIBRE$CABE" in OK*OK*) ;; *) log "  un control fallo: la prueba no distingue"; [ "$RC" = 0 ] && RC=6 ;; esac
case "$CON" in OOM*|"ERR CUDA error: unknown error"*|*cudaErrorUnknown*|ERR*unknown\ error*) log "  rechazo sobre el tope: SI" ;;
    *) log "  NO rechazo sobre el tope"; [ "$RC" = 0 ] && RC=5 ;; esac
log "--- 3. fuga: dmem.current de un cgroup tras salir su proceso debe ser 0"
for c in bb-dmem-empty bb-dmem-tope bb-dmem-libre bb-dmem-holgado; do
    v=$(grep -E "^$REGION " "$RAIZ/$c/dmem.current" 2>/dev/null | awk '{print $2}'); v=${v:-NA}
    log "  $c: dmem.current tras salir = $v"; { [ "$v" = 0 ] || [ "$v" = NA ]; } || { [ "$RC" = 0 ] && RC=7; }
done
log "--- 4. contenedores en marcha (SOLO LECTURA, no se pone ningun tope; 0 es esperable si vLLM aun carga el modelo: comparar con nvidia-smi)"
for id in $(docker ps -q 2>/dev/null); do
    n=$(docker inspect -f '{{.Name}}' "$id" | tr -d /); d="$RAIZ/docker.slice/docker-$(docker inspect -f '{{.Id}}' "$id").scope"
    log "  $n: $(grep -E "^$REGION " "$d/dmem.current" 2>/dev/null || echo 'sin dmem.current')"
done
if [ "$CONTENEDOR" = 1 ]; then
    log "--- 5. contenedor efimero con tope (usa la imagen de vLLM, runtime nvidia, ~1 GiB de GPU)"
    IMG=$(docker ps --format '{{.Image}}' --filter name=nemotron-server | head -1)
    mkdir -p "$T/gate"; cp "$T/pide.py" "$T/gate/pide.py"
    ID=$(docker run -d --rm --name bb-dmem-ct --runtime=nvidia --entrypoint sh -v "$T/gate:/gate" "$IMG" -c \
         'while [ ! -e /gate/go ]; do sleep 0.2; done; python3 /gate/pide.py empty 1024 > /gate/out 2>&1')
    D="$RAIZ/docker.slice/docker-$ID.scope"
    echo "$REGION 512M" >"$D/dmem.max" && touch "$T/gate/go"
    for _ in $(seq 1 60); do [ -s "$T/gate/out" ] && break; sleep 1; done
    log "  contenedor con tope 512M pide 1024 MiB: $(grep -E '^(OK|OOM|ERR)' "$T/gate/out" | tail -1)  (esperado OOM)"
fi
log "rc=$RC (0 = todo lo esperado)"
exit $RC
