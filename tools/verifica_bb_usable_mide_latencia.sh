#!/usr/bin/env bash
# Confirma que bb-usable esta MIDIENDO latencia de verdad, no solo que su
# unit DECLARA DISPLAY. Son cosas distintas: `Environment=` en el fichero
# de la unit cambia con un daemon-reload, pero el PROCESO ya arrancado sigue
# con el entorno que tenia al lanzarse -- systemctl show -p Environment
# refleja lo declarado, no lo que el proceso vivo respira. Sin este chequeo,
# DEBT-BB-USABLE-NUNCA-MIDIO-SU-PROPIA-LATENCIA se habria podido cerrar en
# falso: DISPLAY ya en el fichero, journal todavia escribiendo "sin DISPLAY"
# porque nadie reinicio el proceso.
set -euo pipefail

ultima=$(journalctl -u bb-usable -n 200 --no-pager -o cat | grep "latencia del escritorio" | tail -1)

case "$ultima" in
  *"sin DISPLAY"*) exit 1 ;;
  *"latencia del escritorio"*) exit 0 ;;
  *) exit 1 ;;
esac
