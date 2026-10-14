#!/usr/bin/env bash
# Sale 0 solo si, DESPUES de aplicar el cambio de earlyoom (la copia del archivo viejo en /var/lib/blackbox marca la fecha) y con al
# menos 14 dias de journal desde entonces, earlyoom no mando ninguna senal al motor (VLLM::EngineCor o vllm).
# close_check de DEBT-EARLYOOM-MOTOR-SIGUE-ELEGIBLE-01. Sale 2 si todavia no pasaron 14 dias (no es un cero: es "aun no se puede decir").
set -euo pipefail
dir="${BB_FORENSE_DIR:-/var/lib/blackbox}"
copia=$(find "$dir" -maxdepth 1 -name "etc_default_earlyoom.*" 2>/dev/null | head -n 1 || true)
[ -n "$copia" ] || { echo "sin copia del archivo viejo: el cambio de earlyoom no se aplico" >&2; exit 2; }
desde=$(date -d "@$(stat -c %Y "$copia")" '+%Y-%m-%d %H:%M:%S')
dias=$(( ( $(date +%s) - $(stat -c %Y "$copia") ) / 86400 ))
[ "$dias" -ge 14 ] || { echo "aun no: pasaron $dias dias desde $desde (hacen falta 14)" >&2; exit 2; }
n=$(journalctl -u earlyoom --since "$desde" --no-pager 2>/dev/null | grep -cE 'sending SIG(TERM|KILL) to process [0-9]+ uid [0-9]+ "(VLLM::EngineCor|vllm)"' || true)
echo "senales de earlyoom al motor desde $desde: $n"
[ "$n" -eq 0 ]
