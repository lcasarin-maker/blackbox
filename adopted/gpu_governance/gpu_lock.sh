#!/bin/bash
# Shared mutex for ad-hoc GPU-heavy scripts (Opción C, task #8/H6).
# NOT wired into the production systemd services (ai-nemotron.service,
# ai-ollama.service) — those are meant to coexist concurrently, a lock held
# for their whole lifetime would break that. This is for manual/experimental
# work (bake-off candidates, fine-tuning runs, local_llm_worker.py-style
# scripts) where you want "only one experimental GPU-heavy thing at a time,"
# reusing the same flock pattern already verified in tools/local_llm_worker.py.
#
# Usage: gpu_lock.sh -- <command> [args...]
# Blocks until the lock is free, then execs the command holding the lock for
# its entire runtime (released automatically when it exits, even on crash).
set -euo pipefail

LOCK_PATH="/srv/ai/gpu_governance/gpu.lock"

if [ "${1:-}" != "--" ]; then
  echo "Usage: gpu_lock.sh -- <command> [args...]" >&2
  exit 2
fi
shift

echo "[gpu_lock] Waiting for lock ($LOCK_PATH)..."
echo "[gpu_lock] Will run once acquired: $*"
exec flock "$LOCK_PATH" "$@"
