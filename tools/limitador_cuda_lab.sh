#!/usr/bin/env bash
# Laboratorio del limitador CUDA (FEATURE-LIMITADOR-LD-PRELOAD-CUDA-GB10-01): compila HAMi-core en una copia aislada y
# corre los cuatro casos con torch. Sale distinto de 0 si el limitador no rechaza sobre el tope (B) o si el control
# negativo (D, sin variable) NO corre sin tope: un instrumento que no puede dar el veredicto contrario no mide.
# Uso: tools/limitador_cuda_lab.sh <directorio-con-clon-de-HAMi-core>   (no ejecuta nada del clon; solo lo compila)
set -u
SRC=${1:?uso: $0 <clon de HAMi-core>}
W=$(mktemp -d); cp -r "$SRC" "$W/h"; mkdir "$W/h/build"; cd "$W/h/build" || exit 3
# Debug: el build.sh oficial. Release usa -fvisibility=hidden y el hook queda sin simbolos (limita NADA y dice "Initializing").
cmake .. -DDLSYM_HOOK_ENABLE=1 -DMULTIPROCESS_LIMIT_ENABLE=1 -DHOOK_MEMINFO_ENABLE=1 -DHOOK_NVML_ENABLE=1 \
  -DCMAKE_BUILD_TYPE=Debug -DTEST_DEVICE_ID=0 -DCUDA_HOME=/usr/local/cuda >/dev/null 2>&1 && make -j4 vgpu >/dev/null 2>&1 || { echo "NOT_COLLECTED: no compila"; exit 3; }
L=$PWD/libvgpu.so
[ "$(nm -D "$L" | grep -c ' T cu')" -gt 0 ] || { echo "FAIL: sin simbolos cu* exportados (build Release?)"; exit 4; }
cat > "$W/t.py" <<'PY'
import sys, torch
n = int(sys.argv[1]) << 20
try:
    torch.empty(n, dtype=torch.uint8, device="cuda"); torch.cuda.synchronize(); print("OK")
except Exception as e:
    print("OOM" if "out of memory" in str(e).lower() else "ERR")
PY
corre() { rm -f /tmp/cudevshr.cache; env "${@:2}" python3 "$W/t.py" "$1" 2>&1 | grep -E '^(OK|OOM|ERR)$' | tail -1; }
B=$(corre 1024 CUDA_DEVICE_MEMORY_LIMIT=512m LD_PRELOAD="$L"); C=$(corre 256 CUDA_DEVICE_MEMORY_LIMIT=512m LD_PRELOAD="$L"); D=$(corre 1024 LD_PRELOAD="$L")
echo "B(512m,pide 1024)=$B  C(512m,pide 256)=$C  D(sin variable,pide 1024)=$D"
[ "$B" = OOM ] && [ "$C" = OK ] && [ "$D" = OK ] && { echo "limitador_verificado"; rm -rf "$W"; exit 0; }
echo "FAIL: se esperaba B=OOM C=OK D=OK"; rm -rf "$W"; exit 1
