#!/usr/bin/env bash
# Confirma que una unit de systemd oneshot tiene un TimeoutStartSec real, no
# infinity -- sin eso, una sola corrida colgada apaga el instrumento hasta el
# reinicio (DEBT-BB-SAMPLE-SIN-TECHO-DE-TIEMPO-SE-QUEDO-COLGADO-EN-EL-COLAPSO).
#
# Existe como script aparte, sin `bash -c` ni tuberia, porque
# backlog_verifier prohibe las dos formas en un verification_command: la
# primera por poder smugglear codigo inline, la segunda por operador de shell.
set -euo pipefail

alcance=()
if [ "${1:-}" = "--user" ]; then
  alcance=(--user)
  shift
fi
unit="${1:?uso: verifica_timeout_start.sh [--user] <unit>}"

valor=$(systemctl "${alcance[@]}" show "$unit" -p TimeoutStartUSec --value)
[ "$valor" != "infinity" ]
