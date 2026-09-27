#!/usr/bin/env bash
# El veredicto de `bb status` no se mueve entre corridas con el sujeto quieto.
#
# Por que existe
# --------------
# `bb status` reportaba FALTA sobre `earlyoom con la punteria puesta` 1 de cada 6
# corridas, con el instrumento demostrablemente armado
# (DEBT-BB-STATUS-DICE-FALTA-SOBRE-UN-INSTRUMENTO-ARMADO, 2026-09-27). La causa
# era `set -o pipefail` mas una tuberia a `grep -q`: grep cierra su stdin al
# primer match, el productor recibe SIGPIPE y muere con 141, y pipefail propaga
# ESE 141. Es una CARRERA, asi que falla a veces.
#
# De ahi la forma de este chequeo. El criterio no es el VALOR del veredicto:
# es su ESTABILIDAD. Una sola corrida buena no distingue arreglado de
# afortunado, y eso no es teoria -- es literalmente como se encontro el defecto:
# la version previa de bin/bb dijo FALTA y la actual dijo armado minutos
# despues, en la misma maquina, y la primera lectura fue "lo rompi yo".
#
# Vigila la CLASE, no la fila: cualquier chequeo de `bb status` que se vuelva
# flaky por cualquier razon mueve el resumen y esto sale 1.
#
# Salidas:
#   0  el resumen fue identico en las N corridas
#   1  el resumen se movio -- se imprime cada variante con su cuenta
#   2  COULD_NOT_RUN: no se pudo obtener un resumen legible
set -uo pipefail

CORRIDAS="${1:-8}"
BB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/bin/bb"

if [ ! -x "$BB" ]; then
    echo "COULD_NOT_RUN: no existe o no es ejecutable $BB" >&2
    exit 2
fi

tmp=$(mktemp) || { echo "COULD_NOT_RUN: sin temporal" >&2; exit 2; }
trap 'rm -f "$tmp"' EXIT

for _ in $(seq 1 "$CORRIDAS"); do
    # El resumen entero, que es lo que un lector usa para decidir si hace falta
    # correr enable-privileged.sh.
    linea=$("$BB" status 2>/dev/null | grep -oE 'armado: *[0-9]+ *falta: *[0-9]+ *ciego: *[0-9]+')
    if [ -z "$linea" ]; then
        echo "COULD_NOT_RUN: bb status no imprimio un resumen legible" >&2
        exit 2
    fi
    echo "$linea" >>"$tmp"
done

distintos=$(sort -u "$tmp" | grep -c .)
if [ "$distintos" -eq 1 ]; then
    echo "bb status estable en $CORRIDAS corridas: $(sort -u "$tmp")"
    exit 0
fi

echo "bb status INESTABLE: $distintos resumenes distintos en $CORRIDAS corridas"
sort "$tmp" | uniq -c | sed 's/^/  /'
echo
echo "El sujeto no cambio entre corridas, asi que la diferencia es del chequeo."
echo "Candidato conocido: una tuberia a 'grep -q' bajo 'set -o pipefail' --"
echo "grep cierra su stdin al primer match y pipefail propaga el 141 del"
echo "productor. Se arregla sin tuberia: capturar en variable y usar 'case'."
exit 1
