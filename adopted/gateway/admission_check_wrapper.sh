#!/bin/bash
# Envuelve admission_check.sh leyendo el umbral de active_engine.json en vez
# de un numero fijo en el .service -- el mismo JSON que ya gobierna imagen,
# modelo y memoria del contenedor (ver /srv/ai/gateway/main.py). Motivo:
# el .service traia "85" hardcodeado desde antes de que container_memory_gb
# bajara a 75 (adopcion sin DSpark, DGX-142); el numero quedo desincronizado
# y bloqueaba reinicios legitimos con memoria real de sobra.
set -euo pipefail
CONFIG="${1:-/srv/ai/gateway/active_engine.json}"
SERVICE_NAME="${2:-ai-nemotron}"
GB=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['admission_check_gb'])" "$CONFIG")
exec /srv/ai/gpu_governance/admission_check.sh "$GB" "$SERVICE_NAME"
