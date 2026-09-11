#!/bin/bash
# Admission control for GPU-heavy services (Opción B, task #8/H6/H34).
#
# Real constraint discovered this session: Docker's --memory limit does not
# govern unified/GPU memory on this hardware (H6, re-confirmed with live data
# 2026-07-27 — nemotron-server's 95GB Docker limit sat at 12GB cgroup usage
# while the process actually held ~98GB of unified memory). No kernel/driver
# level enforcement exists either (H34 — the dmem cgroup controller exists
# structurally but the installed NVIDIA driver, 580.173.02, doesn't populate
# it). The only real lever left is refusing to START a new GPU-heavy process
# when there isn't room, checked at the moment systemd is about to launch it.
#
# Usage: admission_check.sh <required_gb> <service_name_for_logging>
# Exit 0 = OK to proceed. Exit 1 = refused, not enough free memory.
#
# DESKTOP_RESERVE_GB added after H35 (2026-07-27): a real OOM killed the
# user's desktop IDE (antigravity) and forced a hard reset. Root cause
# included this check treating the full unified-memory pool as available
# for AI services, with no reservation for the desktop/GUI environment
# (Antigravity, Firefox, GNOME) that runs on this same machine and competes
# for the same 121GB. This is a snapshot check, not a reservation — it does
# NOT account for a service (like Nemotron) continuing to grow in memory for
# ~13 minutes after passing this check, so it reduces but does not eliminate
# the risk of a repeat.
set -euo pipefail

DESKTOP_RESERVE_GB=18
REQUIRED_GB="${1:?Usage: admission_check.sh <required_gb> <service_name>}"
SERVICE_NAME="${2:-unknown}"

AVAILABLE_GB=$(free -g | awk '/^Mem:/ {print $7}')  # "disponible" column, not just "libre"
USABLE_GB=$((AVAILABLE_GB - DESKTOP_RESERVE_GB))

echo "[admission_check] $SERVICE_NAME requires ${REQUIRED_GB}GB; ${AVAILABLE_GB}GB available, ${DESKTOP_RESERVE_GB}GB reserved for desktop/OS, ${USABLE_GB}GB usable"

if [ "$USABLE_GB" -lt "$REQUIRED_GB" ]; then
  echo "[admission_check] REFUSED: ${SERVICE_NAME} needs ${REQUIRED_GB}GB but only ${USABLE_GB}GB is usable (after the ${DESKTOP_RESERVE_GB}GB desktop reserve)." >&2
  echo "[admission_check] Check what else is running (docker ps, free -h) before retrying." >&2
  exit 1
fi

echo "[admission_check] OK: proceeding with $SERVICE_NAME start"
exit 0
