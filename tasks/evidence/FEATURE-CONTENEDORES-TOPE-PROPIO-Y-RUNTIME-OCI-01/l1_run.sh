#!/usr/bin/env bash
# Nivel 1: un contenedor rootless REAL a traves del envoltorio (sin root, sin Docker).
# uso: L1_DIR=<dir de trabajo> bash l1_run.sh <repo> <id> <modo> [directo]
#   modo: none | estricto | gpu | gpuok | gpuover | roto
#   directo: control negativo, runc SIN envoltorio.
# El runtime real es runc rootless con --systemd-cgroup: el contenedor cae en
# app.slice/bblab-<id>.scope del systemd de usuario.
set -u
S=${L1_DIR:?define L1_DIR}
AQUI=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$1 ID=$2 MODO=$3
B=$S/b-$ID
rm -rf "$B"; mkdir -p "$B"
(cd "$B" && runc spec --rootless) || exit 9
python3 "$AQUI/l1_prep.py" "$B" "app.slice:bblab:$ID" "$MODO" >/dev/null
export BLACKBOX_DATA=$S/data BB_OCI_REAL_RUNTIME=runc
ST=$S/state; mkdir -p "$ST"
echo "== create $ID ($MODO)"
if [ "${4:-}" = directo ]; then
  echo "(control negativo: runc directo, SIN envoltorio)"
  runc --root "$ST" --rootless=true --systemd-cgroup create --bundle "$B" "$ID"
else
  python3 "$REPO/tools/bb_oci_runtime.py" --root "$ST" --rootless=true --systemd-cgroup create --bundle "$B" "$ID"
fi
echo "rc_create=$?"
CG=/sys/fs/cgroup/user.slice/user-$(id -u).slice/user@$(id -u).service/app.slice/bblab-$ID.scope
if [ -d "$CG" ]; then
  python3 "$REPO/tools/bb_oci_runtime.py" --root "$ST" --rootless=true --systemd-cgroup start "$ID" && echo "start rc=0; procesos en el cgroup: $(wc -l <"$CG/cgroup.procs")"
  echo "cgroup=$CG memory.max=$(cat "$CG/memory.max") memory.swap.max=$(cat "$CG/memory.swap.max") pids.max=$(cat "$CG/pids.max")"
else
  echo "cgroup ausente: $CG"
fi
python3 "$REPO/tools/bb_oci_runtime.py" --root "$ST" --rootless=true --systemd-cgroup delete --force "$ID" 2>&1
echo "rc_delete=$?"
