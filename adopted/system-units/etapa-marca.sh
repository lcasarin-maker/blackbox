#!/usr/bin/env bash
# etapa-marca.sh <etapa> -- anota que este arranque llego a <etapa>. Lo corre bb-etapa@<etapa>.service (unidad de
#      SISTEMA, DefaultDependencies=no) desde su copia instalada /usr/local/sbin/bb-etapa-marca (root:root 0755).
# Escribe: (1) `<3>bb-etapa <etapa> <boot_id>` en /dev/kmsg, PRIMERO, porque llega aunque el disco no: al buffer del
#      kernel (pstore en un panic, journal, journal-udp-forward) y a la consola serie. Nivel 3 y no 4: con
#      `kernel.printk = 4 4 1 7` (procps, /etc/sysctl.d/10-console-messages.conf en Ubuntu 24.04) la consola solo
#      imprime niveles < 4, asi que un <4> nunca saldria por ttyS0. (2) Una linea JSON
#      {boot_id, etapa, monotonic, realtime} al final de /var/lib/blackbox/arranque/etapas.jsonl, con fsync del
#      archivo y del directorio (`sync ARCHIVO`, coreutils: fsync de ese archivo, no del sistema entero).
# Rota: si etapas.jsonl llega a 256 KiB (~200 arranques) pasa a etapas.jsonl.1 (una generacion; la anterior se pierde).
# Nunca rompe el arranque: una falla de escritura (disco de solo lectura, directorio ajeno o symlink) se anuncia en
#      stderr, que va al journal, y sale 0. Solo un nombre de etapa invalido sale 2: es un error de quien llama.
# monotonic: segundos de /proc/uptime (CLOCK_BOOTTIME), igual a CLOCK_MONOTONIC hasta la primera suspension, y en un
#      arranque no la hubo. realtime: $EPOCHREALTIME; antes de la sincronizacion NTP puede venir corrido.
# Sin Python: solo bash, coreutils y flock (util-linux), que estan antes de local-fs.target.
# Costuras de prueba: BB_ETAPA_DIR, BB_ETAPA_KMSG, BB_ETAPA_BOOT_ID, BB_ETAPA_UPTIME, BB_ETAPA_MAX_BYTES.
set -uo pipefail  # sin -e a proposito: cada falla se maneja y ninguna puede tumbar la unidad
umask 022
export LC_ALL=C  # $EPOCHREALTIME usa el separador decimal del locale; el JSON exige punto

etapa=${1:-}
if [[ ! "$etapa" =~ ^[a-z0-9][a-z0-9-]{0,40}$ ]]; then
  echo "etapa-marca: nombre de etapa invalido: '$etapa' (se espera ^[a-z0-9][a-z0-9-]{0,40}\$)" >&2
  exit 2
fi
dir=${BB_ETAPA_DIR:-/var/lib/blackbox/arranque}
kmsg=${BB_ETAPA_KMSG:-/dev/kmsg}
max=${BB_ETAPA_MAX_BYTES:-262144}
[[ "$max" =~ ^[0-9]+$ ]] || max=262144

boot=""
IFS= read -r boot 2>/dev/null <"${BB_ETAPA_BOOT_ID:-/proc/sys/kernel/random/boot_id}"
[[ "$boot" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || boot=desconocido
mono=""
read -r mono _ 2>/dev/null <"${BB_ETAPA_UPTIME:-/proc/uptime}"
[[ "$mono" =~ ^[0-9]+(\.[0-9]+)?$ ]] || mono=null
real=${EPOCHREALTIME:-}
[[ "$real" =~ ^[0-9]+\.[0-9]+$ ]] || real=null

if ! printf '<3>bb-etapa %s %s\n' "$etapa" "$boot" 2>/dev/null >>"$kmsg"; then
  echo "etapa-marca: no pude escribir en $kmsg" >&2
fi

# Un directorio que root va a escribir no puede ser symlink ni de otro dueno ni escribible por grupo/otros: el usuario
# podria redirigir la escritura. Se verifica, no se arregla (el mismo criterio que arranque-forense.sh).
seguro() {
  [[ ! -L "$1" && -d "$1" ]] || return 1
  [[ "$(stat -c '%u' -- "$1" 2>/dev/null)" == "$(id -u)" ]] || return 1
  local modo; modo=$(stat -c '%a' -- "$1" 2>/dev/null) || return 1
  (( (8#$modo & 8#022) == 0 ))
}

anota() {
  local d t f=$dir/etapas.jsonl lock=$dir/.etapas.lock tam
  # /var/lib/blackbox puede no existir aun (lo crea tambien arranque-forense): se crean los dos niveles, nada mas arriba
  for d in "$(dirname -- "$dir")" "$dir"; do
    if [[ ! -e "$d" && ! -L "$d" ]]; then
      # dos etapas a la vez en el primer arranque: si la otra lo creo primero, el mkdir de esta falla y no es error
      mkdir -m 0755 -- "$d" 2>/dev/null || [[ -d "$d" ]] || { echo "etapa-marca: no pude crear $d" >&2; return 1; }
    fi
    seguro "$d" || { echo "etapa-marca: $d no es un directorio propio y cerrado" >&2; return 1; }
  done
  for t in "$f" "$f.1" "$lock"; do
    [[ ! -L "$t" ]] || { echo "etapa-marca: $t es un symlink; no se toca" >&2; return 1; }
  done
  # Varias etapas corren a la vez (gpu-lista con basic, network-online con multi-user): el lock serializa rotar y anotar.
  {
    flock -w 5 9 || echo "etapa-marca: sin lock en 5 s; anoto igual" >&2
    tam=$(stat -c '%s' -- "$f" 2>/dev/null) || tam=0
    if (( tam >= max )); then
      mv -f -- "$f" "$f.1" || return 1
    fi
    printf '{"boot_id":"%s","etapa":"%s","monotonic":%s,"realtime":%s}\n' "$boot" "$etapa" "$mono" "$real" >>"$f" || return 1
    sync -- "$f" && sync -- "$dir"
  } 9>>"$lock"
}

if ! anota; then
  echo "etapa-marca: no pude anotar '$etapa' en $dir; el arranque sigue" >&2
fi
exit 0
