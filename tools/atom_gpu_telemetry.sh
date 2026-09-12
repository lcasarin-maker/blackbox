#!/bin/bash
# Reemplazo minimo del extraviado Atlas/tools/atom_gpu_telemetry.py.
#
# bin/bb (ATLAS_TELEMETRY, bb status "termica de Atlas", bb scan seccion 8)
# lee JSONL de ~/projects/Atlas/logs/atom_gpu_telemetry.jsonl. Ese proyecto
# (~/projects/Atlas) no existe en esta maquina y no se encontro published en
# ningun sitio (ni en el owner del repo ni en busqueda publica de codigo) --
# ver `bb drift`. Esto NO es una recuperacion de Atlas: es una
# reimplementacion, en bash, de solo los campos que bin/bb realmente
# consume (evento "muestra": sm_clk_mhz/gpu_util_pct/throttle/gpu_procs;
# evento "temp_critica" con corroboracion). No reproduce el resto de Atlas
# (agent_findings, clasificacion de harvest, etc.), y no actua sobre lo que
# mide -- blackbox es deliberadamente de solo lectura (SPEC.md, "Out of
# scope: actuar sobre lo que mide").
set -uo pipefail

OUT="${ATLAS_TELEMETRY:-$HOME/projects/Atlas/logs/atom_gpu_telemetry.jsonl}"
INTERVAL=5              # segundos entre muestras -- misma cadencia citada en suspended/MANIFIESTO.md
PROCS_EVERY=3           # gpu_procs solo 1 de cada N muestras (coste de --query-compute-apps)
SYNC_EVERY=12           # ~1 minuto: los datos deben sobrevivir a un corte duro
RETENTION_DAYS=30
NVSMI_TIMEOUT=10

# Umbral PROVISIONAL: el trip point documentado en README.md es 104C: este
# valor no sale de un incidente propio calibrado en esta maquina, igual que
# los umbrales de PSI (tasks/backlog/DEBT-PSI-UMBRALES-SIN-CALIBRAR.md).
TEMP_CRIT_C=95
CONFIRM_N=3             # muestras consecutivas por encima del umbral para "corrobora"

mkdir -p "$(dirname "$OUT")"

now_iso() { date -u '+%Y-%m-%dT%H:%M:%S'; }

# Bitmask NVML real (nvmlClocksThrottleReasonXxx), no una cadena inventada:
# asi "0x0000000000000000" del original sigue significando "nada activo" y
# el resto de bits siguen donde nvidia-smi/pynvml los documentan.
throttle_hex() {
  local block bits=0
  block=$(timeout "$NVSMI_TIMEOUT" nvidia-smi -q -d PERFORMANCE 2>/dev/null) || { echo ""; return; }
  block=$(printf '%s\n' "$block" | sed -n '/Clocks Event Reasons$/,/Clocks Event Reasons Counters/p')
  reason_is_active() {
    printf '%s\n' "$block" | grep -F "$1" | head -1 | sed -E 's/^[^:]*:? *//' | tr -d ' \t' | grep -qx 'Active'
  }
  reason_is_active "Idle"                        && bits=$((bits | 0x1))
  reason_is_active "Applications Clocks Setting" && bits=$((bits | 0x2))
  reason_is_active "SW Power Cap"                && bits=$((bits | 0x4))
  reason_is_active "HW Slowdown"                 && bits=$((bits | 0x8))
  reason_is_active "Sync Boost"                  && bits=$((bits | 0x10))
  reason_is_active "SW Thermal Slowdown"         && bits=$((bits | 0x20))
  reason_is_active "HW Thermal Slowdown"         && bits=$((bits | 0x40))
  reason_is_active "HW Power Brake Slowdown"     && bits=$((bits | 0x80))
  reason_is_active "Display Clock Setting"       && bits=$((bits | 0x100))
  printf '0x%016x' "$bits"
}

# 1 de cada PROCS_EVERY muestras: JSON de gpu_procs + total en MiB, o "" si
# no toca esta vez (el llamador omite la clave entera, bb ya trata su
# ausencia como "sin cambio" -- ver bin/bb linea ~952).
gpu_procs_json() {
  local rows total=0 first=1 json="["
  rows=$(timeout "$NVSMI_TIMEOUT" nvidia-smi --query-compute-apps=process_name,used_memory \
    --format=csv,noheader,nounits 2>/dev/null) || { echo ""; return; }
  [ -z "$rows" ] && { echo '[]|0'; return; }
  while IFS=',' read -r nombre mem; do
    nombre=$(printf '%s' "$nombre" | sed -e 's/^ *//' -e 's/ *$//' -e 's/\\/\\\\/g' -e 's/"/\\"/g')
    mem=$(printf '%s' "$mem" | tr -d ' ')
    [ -z "$nombre" ] && continue
    total=$((total + ${mem:-0}))
    [ "$first" -eq 1 ] || json+=","
    json+="{\"nombre\":\"$nombre\",\"mem_mib\":${mem:-0}}"
    first=0
  done <<<"$rows"
  json+="]"
  echo "${json}|${total}"
}

# Poda simple: se queda solo con lineas de los ultimos RETENTION_DAYS dias,
# comparando el prefijo de fecha de "ts" (primer campo del objeto, ver
# comentario sobre el truco awk -F'"' en bin/bb). Sin esto el JSONL crece
# sin limite -- a 5s de cadencia son ~17k lineas/dia.
prune() {
  [ -f "$OUT" ] || return
  local cutoff tmp
  cutoff=$(date -u -d "-${RETENTION_DAYS} days" '+%Y-%m-%d' 2>/dev/null) || return
  tmp="${OUT}.tmp.$$"
  if awk -v c="$cutoff" -F'"' '{if (substr($4,1,10) >= c) print}' "$OUT" > "$tmp" 2>/dev/null; then
    mv "$tmp" "$OUT"
  else
    rm -f "$tmp"
  fi
}

n=0
hot_streak=0
last_prune=$(date +%s)

while :; do
  ts=$(now_iso)
  read -r clk util temp < <(timeout "$NVSMI_TIMEOUT" nvidia-smi \
    --query-gpu=clocks.sm,utilization.gpu,temperature.gpu --format=csv,noheader,nounits 2>/dev/null \
    | tr -d ',' )

  if [ -z "${temp:-}" ]; then
    # nvidia-smi no respondio: registrar el timeout es el dato, no un error
    # a silenciar (mismo motivo que gpu_sampler.sh -- un cuelgue del driver
    # deja a nvidia-smi colgado y esa fila es la unica evidencia posible).
    printf '{"ts":"%s","evento":"muestra","status":"TIMEOUT"}\n' "$ts" >> "$OUT"
  else
    throttle=$(throttle_hex)
    procs_field=""
    if [ $((n % PROCS_EVERY)) -eq 0 ]; then
      pj=$(gpu_procs_json)
      if [ -n "$pj" ]; then
        procs_json="${pj%|*}"
        procs_total="${pj##*|}"
        procs_field=",\"gpu_procs\":${procs_json},\"gpu_mem_total_mib\":${procs_total}"
      fi
    fi
    printf '{"ts":"%s","evento":"muestra","sm_clk_mhz":%s,"gpu_util_pct":%s,"temp_c":%s,"throttle":"%s"%s}\n' \
      "$ts" "$clk" "$util" "$temp" "${throttle:-0x0000000000000000}" "$procs_field" >> "$OUT"

    # Corroboracion: una lectura aislada por encima del umbral es ruido de
    # sensor (README: 1093 de 1223 descartadas en la maquina original);
    # CONFIRM_N consecutivas es un evento real.
    if [ "${temp:-0}" -ge "$TEMP_CRIT_C" ]; then
      hot_streak=$((hot_streak + 1))
      if [ "$hot_streak" -eq "$CONFIRM_N" ]; then
        printf '{"ts":"%s","evento":"temp_critica","temp_c":%s,"corroboracion":"corrobora"}\n' \
          "$ts" "$temp" >> "$OUT"
      fi
    else
      if [ "$hot_streak" -gt 0 ] && [ "$hot_streak" -lt "$CONFIRM_N" ]; then
        printf '{"ts":"%s","evento":"temp_critica","temp_c":%s,"corroboracion":"descarta"}\n' \
          "$ts" "$temp" >> "$OUT"
      fi
      hot_streak=0
    fi
  fi

  n=$((n + 1))
  [ $((n % SYNC_EVERY)) -eq 0 ] && sync
  if [ $(( $(date +%s) - last_prune )) -ge 3600 ]; then
    prune
    last_prune=$(date +%s)
  fi

  sleep "$INTERVAL"
done
