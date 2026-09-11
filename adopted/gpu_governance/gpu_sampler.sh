#!/bin/bash
# Telemetría continua de GPU para Atom — creado 2026-08-28.
#
# Motivo (medido): el congelamiento del 2026-08-28 00:52:31 no dejó rastro
# diagnosticable. sar (10 min) y memory_monitor (5 min) registraron memoria,
# CPU, carga e I/O — todos sanos a 111 s del fallo (34 GB disponibles,
# 0 procesos bloqueados). El único subsistema sin serie temporal era la GPU.
#
# Lo más importante que hace este script NO es registrar valores sanos: es
# registrar cuando nvidia-smi NO RESPONDE. Un cuelgue del driver deja a
# nvidia-smi colgado, y esa fila `status=TIMEOUT` es la evidencia que este
# fallo no pudo dejar. Por eso cada llamada lleva `timeout` y por eso se
# hace `sync` periódico: los datos deben sobrevivir a un corte duro.
set -uo pipefail

INTERVAL=15                 # segundos entre muestras
PMON_EVERY=4                # pmon (procesos gráficos) 1 de cada N muestras
SYNC_EVERY=4                # sync a disco 1 de cada N muestras
RETENTION_DAYS=30
LOG_DIR=/srv/ai/logs/gpu
NVSMI_TIMEOUT=10

HDR='ts,status,util_gpu,util_mem,temp_c,power_w,sm_clk,pstate,throttle,sys_avail_mb,sys_used_mb,compute_procs,gfx_procs'

mkdir -p "$LOG_DIR"
n=0
gfx=''

while :; do
  ts=$(date '+%Y-%m-%dT%H:%M:%S')
  f="$LOG_DIR/gpu_telemetry_$(date '+%Y-%m-%d').csv"
  [ -f "$f" ] || echo "$HDR" > "$f"

  # --- métricas a nivel GPU. El timeout es el instrumento, no un detalle. ---
  gpu=$(timeout "$NVSMI_TIMEOUT" nvidia-smi \
        --query-gpu=utilization.gpu,utilization.memory,temperature.gpu,power.draw,clocks.current.sm,pstate,clocks_throttle_reasons.active \
        --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ')
  rc=$?

  if [ $rc -eq 124 ]; then
    # nvidia-smi colgado: el driver no responde. ESTA es la fila que importa.
    echo "$ts,TIMEOUT,,,,,,,,$(free -m | awk '/^Mem:/{print $7","$3}'),," >> "$f"
    logger -t gpu-sampler "TIMEOUT: nvidia-smi no respondió en ${NVSMI_TIMEOUT}s"
    sync
    sleep "$INTERVAL"; continue
  fi
  if [ -z "$gpu" ]; then
    echo "$ts,ERROR,,,,,,,,$(free -m | awk '/^Mem:/{print $7","$3}'),," >> "$f"
    sync
    sleep "$INTERVAL"; continue
  fi

  # --- procesos de cómputo con memoria unificada real (MiB) ---
  cp_=$(timeout "$NVSMI_TIMEOUT" nvidia-smi \
        --query-compute-apps=pid,process_name,used_memory \
        --format=csv,noheader,nounits 2>/dev/null \
        | awk -F', *' '{n=$2; sub(/.*\//,"",n); printf "%s:%s:%s;", $1, n, $3}')

  # --- procesos gráficos (Xorg, gnome-shell): el lado del display ---
  if [ $((n % PMON_EVERY)) -eq 0 ]; then
    gfx=$(timeout "$NVSMI_TIMEOUT" nvidia-smi pmon -c 1 2>/dev/null \
          | awk '$1 !~ /^#/ && $3=="G" {printf "%s:%s:%s;", $2, $10, $4}')
  fi

  mem=$(free -m | awk '/^Mem:/{print $7","$3}')
  echo "$ts,OK,$gpu,$mem,$cp_,$gfx" >> "$f"

  n=$((n + 1))
  [ $((n % SYNC_EVERY)) -eq 0 ] && sync
  # poda diaria barata: sólo cuando el contador da la vuelta
  [ $((n % 240)) -eq 0 ] && find "$LOG_DIR" -name 'gpu_telemetry_*.csv' -mtime "+$RETENTION_DAYS" -delete 2>/dev/null

  sleep "$INTERVAL"
done
