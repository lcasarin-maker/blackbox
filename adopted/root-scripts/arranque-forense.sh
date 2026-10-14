#!/usr/bin/env bash
# bb-root-run arranque-forense -- copia el rastro forense del arranque a un lugar que el usuario puede leer.
# Escribe: SOLO bajo /var/lib/blackbox (root:root 0755, el destino tambien): copia de /sys/fs/pstore/* y de la tabla
#      ACPI BERT, la salida de `dmidecode -t bios` y `-t 45`, y UNA fila nueva en pstore/arranque.jsonl por ejecucion
#      (hasta cuando no hay nada: la ausencia se declara con pstore_archivos 0).
# Lee: /sys/fs/pstore (0750 root), /sys/firmware/acpi/tables/BERT, dmidecode.
# Por que: reboot_verdict y bb incident no pueden mirar si un panic o el firmware dejaron rastro (pstore es ilegible
#      para el usuario) ni rellenar las versiones de UEFI/EC/PD sin pedir sudo en pleno incidente.
# Desbloquea: FEATURE-LECTOR-PSTORE-BERT-ROOT-01.
# Guardas: ni /var/lib/blackbox ni pstore pueden ser symlink ni escribibles por grupo/otros ni de otro dueno que root
#      (el usuario podria redirigir una escritura de root); nada de lo copiado se ejecuta; solo ficheros regulares.
# Sin red, sin argumentos.
set -euo pipefail
umask 022

base=/var/lib/blackbox
dest="$base/pstore"
for p in "$base" "$dest"; do
  if [[ -L "$p" ]]; then
    echo "arranque-forense: $p es un symlink; no se toca" >&2
    exit 3
  fi
done
# /var/lib/blackbox debe ser de root y cerrado a grupo/otros ANTES de escribir: se verifica, no se arregla.
if [[ -e "$base" ]]; then
  if [[ "$(stat -c '%u' -- "$base")" != "0" ]] || (( 8#$(stat -c '%a' -- "$base") & 8#022 )); then
    echo "arranque-forense: $base no es de root o es escribible por grupo/otros" >&2
    exit 3
  fi
else
  install -d -m 0755 -o root -g root -- "$base"
fi
# pstore/ puede venir de pstore-preparar, que lo dejo del usuario: aqui pasa a root (el usuario pierde la escritura
# en ese instante, asi que despues de este bloque nadie mas puede cambiar su contenido).
if [[ -e "$dest" ]]; then
  if [[ "$(stat -c '%u' -- "$dest")" != "0" ]]; then
    chown -h -- root:root "$dest"
  fi
  chmod 0755 -- "$dest"
else
  install -d -m 0755 -o root -g root -- "$dest"
fi
if [[ "$(stat -c '%u' -- "$dest")" != "0" ]] || (( 8#$(stat -c '%a' -- "$dest") & 8#022 )); then
  echo "arranque-forense: $dest no quedo de root o es escribible por grupo/otros" >&2
  exit 3
fi
# Lo que el usuario dejo dentro antes del chown: un symlink en un destino de escritura haria seguir a root.
for t in "$dest/arranque.jsonl" "$base/dmidecode-bios.txt.nuevo" "$base/dmidecode-t45.txt.nuevo"; do
  if [[ -L "$t" ]]; then
    echo "arranque-forense: $t es un symlink; no se toca" >&2
    exit 3
  fi
done

boot="$(cat /proc/sys/kernel/random/boot_id)"
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
copiados=0
shopt -s nullglob
for f in /sys/fs/pstore/*; do
  if [[ -f "$f" && ! -L "$f" ]]; then
    install -m 0644 -o root -g root -- "$f" "$dest/${boot}-$(basename -- "$f")"
    copiados=$((copiados + 1))
  fi
done

bert=ausente
if [[ -f /sys/firmware/acpi/tables/BERT && ! -L /sys/firmware/acpi/tables/BERT ]]; then
  install -m 0644 -o root -g root -- /sys/firmware/acpi/tables/BERT "$dest/${boot}-BERT.bin"
  bert=copiada
fi

fw=NOT_COLLECTED
if command -v dmidecode >/dev/null; then
  if dmidecode -t bios > "$base/dmidecode-bios.txt.nuevo" 2>/dev/null; then
    mv -f -- "$base/dmidecode-bios.txt.nuevo" "$base/dmidecode-bios.txt"
    fw=bios
  else
    rm -f -- "$base/dmidecode-bios.txt.nuevo"
  fi
  if dmidecode -t 45 > "$base/dmidecode-t45.txt.nuevo" 2>/dev/null; then
    mv -f -- "$base/dmidecode-t45.txt.nuevo" "$base/dmidecode-t45.txt"
    fw="$fw+t45"
  else
    rm -f -- "$base/dmidecode-t45.txt.nuevo"
  fi
fi

printf '{"ts":"%s","boot_id":"%s","pstore_archivos":%d,"bert":"%s","firmware":"%s"}\n' \
  "$ts" "$boot" "$copiados" "$bert" "$fw" >> "$dest/arranque.jsonl"
chmod 0644 -- "$dest/arranque.jsonl"
echo "== arranque.jsonl (ultima fila)"
tail -n 1 -- "$dest/arranque.jsonl"
