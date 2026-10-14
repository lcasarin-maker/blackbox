#!/usr/bin/env bash
# bb-root-run crontabs-leer -- SOLO LECTURA.
# Lee: /var/spool/cron/crontabs/* (directorio 1730 root:crontab, ilegible para el usuario).
# Por que: los crontabs de usuario son trabajo que actua sobre la maquina y que bb aun no
#      inventaria; sin root no se puede ni listar el directorio.
# Desbloquea: FEATURE-OWNEAR-EN-BB-LO-QUE-ACTUA-SOBRE-LA-MAQUINA-01.
# Aviso: un crontab puede llevar un secreto en linea; la salida queda en un fichero 0644.
# Escribe: nada fuera de stdout. Sin red, sin argumentos.
set -euo pipefail
shopt -s nullglob

dir=/var/spool/cron/crontabs
echo "== ls -la $dir"
ls -la -- "$dir"
tabs=("$dir"/*)
echo "== ${#tabs[@]} crontabs"
for f in "${tabs[@]}"; do
  echo "== $f"
  cat -- "$f"
done
