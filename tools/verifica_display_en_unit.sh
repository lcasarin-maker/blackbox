#!/usr/bin/env bash
# Confirma que una unit de SISTEMA declara DISPLAY en su Environment -- sin
# eso, un sondeo que llama a xset/xdotool contra la sesion grafica devuelve
# None en cada vuelta (DEBT-BB-USABLE-NUNCA-MIDIO-SU-PROPIA-LATENCIA).
#
# Existe como script aparte, sin tuberia, porque backlog_verifier prohibe
# el operador `|` en un verification_command (Prohibited shell injection or
# pipeline operators).
set -euo pipefail

unit="${1:?uso: verifica_display_en_unit.sh <unit>}"

entorno=$(systemctl show "$unit" -p Environment --value)
case "$entorno" in
  *DISPLAY=*) exit 0 ;;
  *) exit 1 ;;
esac
