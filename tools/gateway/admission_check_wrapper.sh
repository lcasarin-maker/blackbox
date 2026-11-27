#!/usr/bin/env bash
set -euo pipefail
CFG="${1:-${BB_GATEWAY_CONFIG:-}}"
if [ -z "$CFG" ] || [ ! -f "$CFG" ]; then
  echo "ERROR: falta archivo de configuracion (BB_GATEWAY_CONFIG o argumento 1)" >&2
  exit 2
fi
exec /srv/ai/gpu_governance/admission_check.sh "$CFG" "${2:-ai-nemotron}"
