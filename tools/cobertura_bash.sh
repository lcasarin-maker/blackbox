#!/usr/bin/env bash
# Mide que lineas de un script bash ejecuta una suite.
#
# coverage.py instrumenta Python; bin/bb es bash y no aparece en ningun informe
# del repo. bash sabe trazarse solo: BASH_ENV se interpreta ANTES de correr un
# script no interactivo, asi que desde ahi se arma BASH_XTRACEFD + set -x con un
# PS4 que imprime fichero y linea. Sin dependencias nuevas.
#
# Uso: tools/cobertura_bash.sh <sujeto> <comando de la suite...>
set -euo pipefail

sujeto=${1:?falta el sujeto, p.ej. bin/bb}
shift
[ $# -gt 0 ] || { echo "falta el comando de la suite" >&2; exit 2; }

raiz=$(git rev-parse --show-toplevel)
abs=$(readlink -f "$raiz/$sujeto")
[ -f "$abs" ] || { echo "no existe: $abs" >&2; exit 2; }

tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
traza="$tmp/traza"; : > "$traza"

cat > "$tmp/bashenv.sh" <<'EOF'
PS4='+${BASH_SOURCE}:${LINENO}:'
exec {__cov_fd}>>"$BB_COV_TRAZA"
BASH_XTRACEFD=$__cov_fd
set -x
EOF

BB_COV_TRAZA="$traza" BASH_ENV="$tmp/bashenv.sh" "$@" >"$tmp/suite.log" 2>&1 || true
rc_suite=$?

# lineas vistas: las que la traza atribuye al sujeto.
#
# `\++` y no `\+`. Bash REPITE el primer caracter de PS4 tantas veces como
# profundidad de anidamiento tenga lo que ejecuta: `+` en el cuerpo principal,
# `++` dentro de una funcion llamada desde `$(...)`, `+++` un nivel mas. El
# patron anterior anclaba en UN solo `+`, asi que contaba como SIN CUBRIR todo
# lo que corre en una substitucion, una tuberia o un subshell -- que en bin/bb
# es casi todo, porque el muestreo se arma con `x=$(funcion)`.
#
# Medido el 2026-09-25: corriendo SOLO los tres tests de `slices_mem`, que la
# ejecutan entera, 11 de sus 14 lineas salian sin cubrir. El bug no estaba en
# la funcion; estaba aqui. Se usa `\K` en vez de lookbehind porque el lookbehind
# de PCRE tiene que ser de ancho fijo y este prefijo no lo es.
grep -oP "^\++\Q$abs\E:\K\d+(?=:)" "$traza" 2>/dev/null | sort -u > "$tmp/vistas" || : > "$tmp/vistas"

# lineas candidatas: ejecutables de verdad. Se excluyen las que bash NUNCA
# puede emitir -- cuerpos de heredoc, continuaciones de linea, interiores de
# comillas simples multilinea (los programas awk de bin/bb), comentarios y
# cierres estructurales, que xtrace no imprime jamas.
awk '
  function limpia(s) { sub(/^[ \t]+/, "", s); sub(/[ \t]+$/, "", s); return s }
  {
    l = limpia($0)
    if (en_heredoc) { if (l == fin_heredoc) en_heredoc = 0; next }
    if (en_comilla) { if (gsub(/'"'"'/, "&") % 2 == 1) en_comilla = 0; next }
    if (continua)   { continua = ($0 ~ /\\$/); next }

    # las definiciones de funcion NO se trazan: bash emite el cuerpo, nunca la
    # cabecera. Contarlas hincha el "sin cubrir" con lineas inalcanzables.
    salta = (l == "" || l ~ /^#/ \
             || l ~ /^(fi|done|esac|else|then|do|\}|\{|;;|\)|\*\))$/ \
             || l ~ /^(function[ ]+)?[A-Za-z_][A-Za-z0-9_]*[ ]*\(\)[ ]*\{?$/)

    if (!salta) print NR

    if ($0 ~ /<<-?[ ]*'"'"'?[A-Za-z_][A-Za-z0-9_]*'"'"'?/) {
      fin = $0; sub(/.*<<-?[ ]*/, "", fin); gsub(/'"'"'/, "", fin)
      sub(/[ \t].*$/, "", fin); fin_heredoc = fin; en_heredoc = 1; next
    }
    if (l !~ /^#/ && gsub(/'"'"'/, "&") % 2 == 1) { en_comilla = 1; next }
    if ($0 ~ /\\$/) continua = 1
  }
' "$abs" | sort -u > "$tmp/candidatas"

tot=$(wc -l < "$tmp/candidatas")
cub=$(comm -12 "$tmp/candidatas" "$tmp/vistas" | wc -l)
pct=$(awk -v c="$cub" -v t="$tot" 'BEGIN{printf "%.1f", t ? 100*c/t : 0}')

printf '%-12s %6s %8s %7s\n' FICHERO LINEAS CUBIERTAS PCT
printf '%-12s %6d %8d %6s%%\n' "$sujeto" "$tot" "$cub" "$pct"
echo
echo "SIN CUBRIR (numero de linea):"
# prefijadas con L y separadas por comas: una corrida de numeros a secas hace
# que pii-scan la lea como un RFC/CURP y bloquee el push (medido 2026-09-24).
comm -13 "$tmp/vistas" "$tmp/candidatas" | sort -n | sed 's/^/L/' \
  | paste -sd, - | fold -s -w 78
echo
echo
echo "LIMITE DECLARADO: mide lineas EJECUTADAS, no ramas ni condiciones. Las"
echo "candidatas excluyen heredocs, continuaciones y comillas simples multilinea,"
echo "que xtrace no puede emitir; un fallo de ese analisis inventaria lineas"
echo "inalcanzables como sin cubrir, nunca al reves."
