#!/usr/bin/env bash
# Cada fichero de `adopted/system-config/` o lo instala un script, o esta
# declarado como SOLO-REGISTRO. Nada queda en medio.
#
# Por que existe, medido el 2026-09-28
# ------------------------------------
# `adopted/system-config/` tiene 27 ficheros y `enable-privileged.sh` instala
# 10. Los otros 17 son un retrato de la maquina que ningun script puede volver a
# aplicar -- y `bb drift` los compara igual, asi que reporta divergencias sin
# remedio disponible.
#
# El coste no es teorico. Ese dia se edito el techo de `app.slice` (48G -> 42G)
# dentro de `adopted/`, se corrio `sudo ./enable-privileged.sh` dos veces, y el
# techo no se movio porque ese fichero no esta entre los 10. Docker bajo a 14 y
# system entro en 12, asi que los compromisos pasaron de 121.8 GiB sobre 121.1
# a 124.1 sobre 121.1: el estado intermedio quedo PEOR que el de partida. Se
# cerro copiando el fichero a mano.
#
# Tres desenlaces, y el 2 es un desenlace y no un fallo
# ----------------------------------------------------
#   0  cada adoptado esta instalado o declarado solo-registro
#   1  hay adoptados sin camino a la maquina y sin declararlo
#   2  COULD_NOT_RUN -- falta el directorio o el script que se audita
set -u
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADOPTADOS="$RAIZ/adopted/system-config"
INSTALADOR="$RAIZ/enable-privileged.sh"
# Los que NO se instalan a proposito se declaran aqui, con su motivo. Un fichero
# en esta lista es una decision escrita; uno fuera de ella y fuera del
# instalador es un hueco.
DECL="$RAIZ/adopted/solo-registro.txt"

[ -d "$ADOPTADOS" ] || { echo "COULD_NOT_RUN: no existe $ADOPTADOS"; exit 2; }
[ -f "$INSTALADOR" ] || { echo "COULD_NOT_RUN: no existe $INSTALADOR"; exit 2; }

huecos=0
total=0
for f in "$ADOPTADOS"/*; do
  [ -f "$f" ] || continue
  total=$((total + 1))
  base="$(basename "$f")"
  if grep -qF "$base" "$INSTALADOR"; then continue; fi
  if [ -f "$DECL" ] && grep -qF "$base" "$DECL"; then continue; fi
  echo "  SIN CAMINO  $base"
  huecos=$((huecos + 1))
done

echo "adoptados: $total   sin camino a la maquina ni declaracion: $huecos"
if [ "$huecos" -gt 0 ]; then
  echo "Un adoptado sin instalador es un retrato, no una configuracion: editarlo"
  echo "no cambia la maquina, y \`bb drift\` reporta una divergencia sin remedio."
  echo "Arreglo: anadirlo a $INSTALADOR, o declararlo en $DECL con su motivo."
  exit 1
fi
echo "OK: cada adoptado se instala o esta declarado solo-registro."
