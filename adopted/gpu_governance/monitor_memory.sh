#!/bin/bash
# Opción E (task #8/H6): detección, no prevención — no hay forma de prevenir
# técnicamente un choque de memoria unificada en este hardware (H6, H34), así
# que al menos lo detectamos rápido. H25 tardó ~un día en notarse porque
# nada monitoreaba esto; este timer corre cada 5 min.
#
# Umbral subido de 10GB a 25GB tras H35 (2026-07-27): un OOM real tumbó el
# sistema (mató `antigravity`, forzó hard reset) con Nemotron todavía
# creciendo hacia su pico — a 10GB de margen ya era demasiado tarde para que
# un humano reaccionara antes del colapso.
set -euo pipefail

THRESHOLD_GB=25
LOG_PATH="/srv/ai/logs/memory_monitor.log"

AVAILABLE_GB=$(free -g | awk '/^Mem:/ {print $7}')
TIMESTAMP=$(date '+%Y-%m-%dT%H:%M:%S')

if [ "$AVAILABLE_GB" -lt "$THRESHOLD_GB" ]; then
  MSG="$TIMESTAMP WARNING: only ${AVAILABLE_GB}GB memoria disponible (umbral: ${THRESHOLD_GB}GB)"
  echo "$MSG" >> "$LOG_PATH"
  echo "$MSG"
  docker ps --format "{{.Names}}: {{.Status}}" >> "$LOG_PATH"
  logger -t gpu-memory-monitor "$MSG"
else
  echo "$TIMESTAMP OK: ${AVAILABLE_GB}GB disponibles" >> "$LOG_PATH"
fi
