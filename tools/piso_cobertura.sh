#!/usr/bin/env bash
# Trinquete de cobertura para bin/bb. El numero no puede BAJAR en silencio.
#
# coverage-target no ve bash, asi que pasaba sin mirar el fichero que mas hace
# de este repo. tools/cobertura_bash.sh lo mide; esto pone el suelo.
# Para subir el piso se edita tests/cobertura_bb.piso a mano, con la corrida
# que lo justifica en el commit. Nunca se baja.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

piso_f=tests/cobertura_bb.piso
[ -f "$piso_f" ] || { echo "[bb-cobertura] falta $piso_f" >&2; exit 2; }
piso=$(tr -d ' \n' < "$piso_f")

# Si corre en hook de pre-push y ni bin/bb ni su suite cambiaron, la cobertura se mantiene
if [ -n "${PRE_COMMIT_FROM_REF:-}" ] && [ -n "${PRE_COMMIT_TO_REF:-}" ]; then
  zero="0000000000000000000000000000000000000000"
  base="$PRE_COMMIT_FROM_REF"
  if [ "$base" = "$zero" ]; then
    base=$(git rev-parse --abbrev-ref --symbolic-full-name @{upstream} 2>/dev/null || echo "origin/HEAD")
  fi
  if ! git diff --name-only "$base..$PRE_COMMIT_TO_REF" 2>/dev/null | grep -qE '^bin/bb$|^tests/test_bb_bash.py$'; then
    echo "[bb-cobertura] bin/bb y tests/test_bb_bash.py sin cambios en el rango del push; piso ${piso}% retenido (OK)"
    exit 0
  fi
fi

salida=$(tools/cobertura_bash.sh bin/bb \
         python3 -m pytest tests/test_bb_bash.py -q -p no:randomly) || {
  echo "[bb-cobertura] COULD_NOT_RUN: el medidor fallo" >&2; exit 2; }

pct=$(awk '$1=="bin/bb"{print $4}' <<<"$salida" | tr -d '%')
[ -n "$pct" ] || { echo "[bb-cobertura] COULD_NOT_RUN: sin cifra que leer" >&2; exit 2; }

if awk -v p="$pct" -v s="$piso" 'BEGIN{exit !(p+0 < s+0)}'; then
  echo "[bb-cobertura] FAIL: bin/bb al ${pct}%, por debajo del piso ${piso}%." >&2
  echo "[bb-cobertura] O se recupera la cobertura, o se justifica bajar el piso." >&2
  exit 1
fi
echo "[bb-cobertura] bin/bb al ${pct}% (piso ${piso}%)"
