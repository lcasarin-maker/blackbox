#!/usr/bin/env bash
# bb-root-run nvidia-bug-report -- corre `nvidia-bug-report.sh` (necesita root) y deja el .log.gz legible por el usuario.
# Escribe: SOLO bajo /var/lib/blackbox (root:root 0755): "$base/nvidia-bug-report.nuevo.log.gz" (lo genera
#      nvidia-bug-report.sh con --output-file, que comprime y anade .gz) y, con un mv, "$base/nvidia-bug-report.log.gz" 0644.
#      Cada corrida sustituye a la anterior; `bb reloj` copia el fichero a la carpeta de incidente si es de su corrida.
# Lee: lo que recoge nvidia-bug-report.sh (dmesg, lspci, nvidia-smi, registros del controlador y de Xorg); el fichero
#      puede llevar datos personales y no se publica sin revisarlo.
# Por que: NVIDIA (zneill, hilo 386060/6) pide el bug-report capturado ANTES de quitar la corriente alterna cuando el reloj
#      de GPU atascado reaparece; `bb reloj` lo pide aqui al ver ATASCADO, sin sudo interactivo en pleno incidente.
# Desbloquea: FEATURE-RELOJ-CAPTURA-DE-INCIDENTE-ANTES-DE-QUITAR-AC-01.
# Guardas: ni /var/lib/blackbox ni los ficheros de salida pueden ser symlink; la base debe ser de root y no escribible por
#      grupo/otros (se verifica, no se arregla). Sin red, sin argumentos. Tarda minutos: timeout 600 s en el manifiesto.
set -euo pipefail
umask 022

base=/var/lib/blackbox
if [[ -L "$base" ]]; then
  echo "nvidia-bug-report: $base es un symlink; no se toca" >&2
  exit 3
fi
if [[ -e "$base" ]]; then
  if [[ "$(stat -c '%u' -- "$base")" != "0" ]] || (( 8#$(stat -c '%a' -- "$base") & 8#022 )); then
    echo "nvidia-bug-report: $base no es de root o es escribible por grupo/otros" >&2
    exit 3
  fi
else
  install -d -m 0755 -o root -g root -- "$base"
fi
for t in "$base/nvidia-bug-report.nuevo.log" "$base/nvidia-bug-report.nuevo.log.gz" "$base/nvidia-bug-report.log.gz"; do
  if [[ -L "$t" ]]; then
    echo "nvidia-bug-report: $t es un symlink; no se toca" >&2
    exit 3
  fi
done

rm -f -- "$base/nvidia-bug-report.nuevo.log" "$base/nvidia-bug-report.nuevo.log.gz"
nvidia-bug-report.sh --output-file "$base/nvidia-bug-report.nuevo.log"
mv -f -- "$base/nvidia-bug-report.nuevo.log.gz" "$base/nvidia-bug-report.log.gz"
chmod 0644 -- "$base/nvidia-bug-report.log.gz"
echo "nvidia-bug-report: $base/nvidia-bug-report.log.gz"
