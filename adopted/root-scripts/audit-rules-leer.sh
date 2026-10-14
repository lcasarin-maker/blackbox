#!/usr/bin/env bash
# bb-root-run audit-rules-leer -- SOLO LECTURA.
# Lee: /etc/audit/rules.d/*.rules (/etc/audit es ilegible para el usuario) y el estado
#      del subsistema audit del kernel (`auditctl -s`).
# Por que: para adoptar en bb las reglas de auditd que actuan sobre la maquina hay que
#      poder leerlas; sin root no se ve ni cuantas son.
# Desbloquea: FEATURE-OWNEAR-EN-BB-LO-QUE-ACTUA-SOBRE-LA-MAQUINA-01.
# Escribe: nada fuera de stdout. Sin red, sin argumentos.
set -euo pipefail
shopt -s nullglob

reglas=(/etc/audit/rules.d/*.rules)
echo "== ${#reglas[@]} ficheros *.rules en /etc/audit/rules.d"
for f in "${reglas[@]}"; do
  echo "== $f"
  cat -- "$f"
done
echo "== auditctl -s"
if command -v auditctl >/dev/null; then
  auditctl -s
else
  echo "auditctl no esta instalado"
fi
