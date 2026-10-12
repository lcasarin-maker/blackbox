#!/usr/bin/env bash
# dmem_prueba.sh -- prueba POSTERIOR al arranque con el modulo parcheado (FEATURE-DMEM-PARCHE-REGION-Y-COBRO-SYSMEM-GB10-01).
# Uso (root): sudo bash tools/dmem_prueba.sh [MiB-que-pide=1024] [tope-MiB=512]
# Respuesta que da: ¿hay region dmem?, ¿cobra el cgroup que pide GPU?, ¿rechaza sobre dmem.max?, ¿con control negativo?
# rc 0 = las tres pruebas dan lo esperado; 3 = sin region (el parche no dio region o corre el modulo de Canonical);
# 4 = hay region pero NO cobra (cudaMalloc no pasa por la ruta cobrada); 5 = no rechaza sobre el tope; 6 = el control
# sin tope fallo (la prueba no distingue).
set -euo pipefail
PIDE=${1:-1024}; TOPE=${2:-512}
RAIZ=${BB_DMEM_RAIZ:-/sys/fs/cgroup}
PY=${BB_DMEM_PYTHON:-python3}
log() { echo "[dmem-prueba] $*"; }
[ "$(id -u)" = 0 ] || [ -n "${BB_DMEM_SIN_RAIZ:-}" ] || { echo "necesita root" >&2; exit 2; }
CAP=$(cat "$RAIZ/dmem.capacity" 2>/dev/null || true)
[ -n "$CAP" ] || { log "NO HAY region dmem (dmem.capacity vacio): el parche no dio region o corre el modulo de Canonical"; exit 3; }
REGION=$(echo "$CAP" | awk 'NR==1{print $1}')
log "region: $REGION ($(echo "$CAP" | awk 'NR==1{print $2}') bytes)"
grep -qw dmem "$RAIZ/cgroup.subtree_control" || echo "+dmem" >"$RAIZ/cgroup.subtree_control"
T=$(mktemp -d); trap 'rmdir "$RAIZ/bb-dmem-con" "$RAIZ/bb-dmem-sin" 2>/dev/null || true; rm -rf "$T"' EXIT
cat >"$T/pide.py" <<'PY'
import sys, torch
n = int(sys.argv[1]) << 20
try:
    x = torch.empty(n, dtype=torch.uint8, device="cuda"); torch.cuda.synchronize()
    print("OK", open(sys.argv[2]).read().strip().replace("\n", ";"))
except Exception as e:
    print("OOM" if "out of memory" in str(e).lower() else "ERR " + str(e)[:80])
PY
corre() {  # $1 cgroup, $2 MiB
    mkdir -p "$RAIZ/$1"
    sh -c "echo \$\$ >'$RAIZ/$1/cgroup.procs'; exec '$PY' '$T/pide.py' '$2' '$RAIZ/$1/dmem.current'" 2>&1 | grep -E '^(OK|OOM|ERR)' | tail -1
}
# 1) cobra: con tope holgado, dmem.current sube
echo "$REGION max" >"$RAIZ/bb-dmem-sin/dmem.max" 2>/dev/null || { mkdir -p "$RAIZ/bb-dmem-sin"; }
SIN=$(corre bb-dmem-sin 256)
log "control sin tope, pide 256 MiB: $SIN"
case "$SIN" in OK*) ;; *) log "el control sin tope fallo: la prueba no distingue"; exit 6 ;; esac
echo "$SIN" | grep -qE "$REGION [1-9]" || { log "hay region pero dmem.current no sube: NO cobra"; exit 4; }
# 2) rechaza sobre el tope
mkdir -p "$RAIZ/bb-dmem-con"; echo "$REGION ${TOPE}M" >"$RAIZ/bb-dmem-con/dmem.max"
CON=$(corre bb-dmem-con "$PIDE")
log "con dmem.max=${TOPE}M, pide $PIDE MiB: $CON"
[ "$CON" = OOM ] || { log "NO rechazo sobre el tope"; exit 5; }
# 3) control negativo: el mismo tope, pide menos que el tope
BAJO=$(corre bb-dmem-con $((TOPE / 4)))
log "con dmem.max=${TOPE}M, pide $((TOPE / 4)) MiB (debe pasar): $BAJO"
case "$BAJO" in OK*) log "dmem_prueba_ok: cobra, rechaza sobre el tope y deja pasar bajo el tope" ;; *) log "el pedido bajo el tope tambien fallo"; exit 5 ;; esac
