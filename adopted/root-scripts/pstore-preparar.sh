#!/usr/bin/env bash
# bb-root-run pstore-preparar -- UNICA escritura: crea /var/lib/blackbox/pstore.
# Escribe: mkdir -p /var/lib/blackbox/pstore (el padre queda root:root 0755), y ese
#      directorio pasa a ser del usuario SUDO_UID con modo 0755. Nada mas.
# Lee: el listado de /sys/fs/pstore (0750 root, ilegible para el usuario).
# Por que: el lector de pstore/BERT necesita un destino propio del usuario donde copiar
#      los registros de panico, y saber si hay alguno.
# Desbloquea: FEATURE-LECTOR-PSTORE-BERT-ROOT-01.
# Guardas: SUDO_UID numerico y distinto de 0; ni el padre ni el destino pueden ser
#      symlink; el padre debe ser de root y no escribible por grupo ni otros (si no, el
#      usuario podria cambiar el destino por un symlink y el chown caeria donde quisiera).
# Sin red, sin argumentos.
set -euo pipefail
umask 022

padre=/var/lib/blackbox
destino="$padre/pstore"
uid_root=0

uid="${SUDO_UID:-}"
if [[ ! "$uid" =~ ^[0-9]+$ ]] || [[ "$uid" == 0 ]]; then
  echo "pstore-preparar: SUDO_UID ausente, no numerico o 0: '$uid'" >&2
  exit 3
fi
for p in "$padre" "$destino"; do
  if [[ -L "$p" ]]; then
    echo "pstore-preparar: $p es un symlink; no se toca" >&2
    exit 3
  fi
done
mkdir -p -- "$padre"
if [[ "$(stat -c '%u' -- "$padre")" != "$uid_root" ]] || (( 8#$(stat -c '%a' -- "$padre") & 8#022 )); then
  echo "pstore-preparar: $padre no es de root o es escribible por grupo/otros" >&2
  exit 3
fi
mkdir -p -- "$destino"
chown -h -- "$uid" "$destino"
chmod 0755 -- "$destino"
echo "== $destino"
ls -ld -- "$destino"
echo "== ls -la /sys/fs/pstore"
ls -la /sys/fs/pstore
