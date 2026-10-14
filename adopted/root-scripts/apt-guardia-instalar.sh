#!/usr/bin/env bash
# bb-root-run apt-guardia-instalar -- instala bb-apt-guardia: un hook DPkg::Pre-Install-Pkgs que hace abortar a APT,
#      antes de llamar a dpkg, cualquier transaccion que quite un paquete de data/apt-paquetes-criticos.txt.
# Escribe: /usr/local/sbin/bb-apt-guardia (root:root 0755) y /etc/apt/apt.conf.d/00-bb-apt-guardia (root:root 0644),
#      cada uno por temporal .bb-apt-guardia.XXXXXX en su directorio y mv; y una caja 0700 /run/bb-apt-guardia.XXXXXX
#      que se borra al salir. Nada mas. No hay copia de respaldo porque nunca sobrescribe: cada destino debe estar
#      ausente (se crea) o ser byte a byte el nuevo (no se toca); cualquier otro contenido hace que se niegue.
# Ejecuta (sin red): `apt-config dump` y `apt-config shell` (lectura); `apt-get -s autoremove` con la configuracion
#      real, antes y despues (rc 0: APT sigue leyendo su configuracion); y dos transacciones APT REALES sobre la caja
#      (APT_CONFIG que solo carga 00-bb-apt-guardia, copia de /var/lib/dpkg/status, Dir::Bin::dpkg = stub que solo
#      anota sus argumentos): `remove nvidia-system-station` debe abortar sin que el stub reciba --remove, y
#      `remove tree` debe pasar con el stub recibiendo --remove tree. dpkg real no corre en ninguna.
# Si una validacion falla, borra lo que ESTA corrida creo (primero el .conf, despues el hook) y sale 5.
# Por que: `apt remove` de una aplicacion ordinaria arrastra nvidia-system-station y el autoremove siguiente ofrece
#      el escritorio (hilo 348170; medido aqui el 2026-10-07: 352 de 353 hojas). `apt-get -s` no corre hooks, asi
#      que la guardia solo se puede probar con una transaccion real; por eso la caja.
# Desbloquea: FEATURE-APT-CRITICAL-METAPACKAGE-GUARD.
# Guardas: ni los destinos, ni sus directorios pueden ser symlink; los directorios deben ser de root y no escribibles
#      por grupo ni otros; un hook ya presente debe ser de root y 0755; si existe 00-bb-apt-guardia.disabled (guardia
#      suspendida) no se reactiva; el temporal se compara con su sha256 antes de moverlo; nvidia-system-station y
#      tree deben estar instalados (sin ellos la validacion no puede salir negativa ni positiva: rc 4, nada tocado).
# Permitir una transaccion: sudo apt -o BB::Apt-Guardia::Permitir=1 <orden>. Desactivar: renombrar el .conf a
#      00-bb-apt-guardia.disabled. Revertir: sudo rm /etc/apt/apt.conf.d/00-bb-apt-guardia /usr/local/sbin/bb-apt-guardia.
# Sin argumentos.
set -euo pipefail
umask 022

conf=/etc/apt/apt.conf.d/00-bb-apt-guardia
dir_conf=/etc/apt/apt.conf.d
hook=/usr/local/sbin/bb-apt-guardia
dir_hook=/usr/local/sbin
estado_dpkg=/var/lib/dpkg/status
sha_conf=3269efff042ce8ee68d49969fa107bb440fb7ec8aab900b268a6d6994e20ade6
sha_hook=a7396902b2639f8eefd7bdd94090e0c3bed58e82c0e11c28ced506cc1416adb5
critico=nvidia-system-station
inocuo=tree
instalado_ok="install ok installed"
tmp=
caja=
creo_conf=0
creo_hook=0
trap 'if [[ -n "$tmp" ]]; then rm -f -- "$tmp"; fi; if [[ -n "$caja" ]]; then rm -rf -- "$caja"; fi' EXIT

for p in "$dir_conf" "$dir_hook" "$conf" "$hook" "$conf.disabled"; do
  if [[ -L "$p" ]]; then
    echo "apt-guardia-instalar: $p es un symlink; no se toca" >&2
    exit 3
  fi
done
for d in "$dir_conf" "$dir_hook"; do
  if [[ ! -d "$d" ]] || [[ "$(stat -c '%u' -- "$d")" != "0" ]] || (( 8#$(stat -c '%a' -- "$d") & 8#022 )); then
    echo "apt-guardia-instalar: $d no es un directorio de root o es escribible por grupo/otros; no se toca" >&2
    exit 3
  fi
done
if [[ -e "$conf.disabled" ]]; then
  echo "apt-guardia-instalar: $conf.disabled existe (guardia suspendida); no se reactiva" >&2
  exit 3
fi
e_conf=ausente
if [[ -e "$conf" ]]; then
  e_conf=otro
  if [[ -f "$conf" && "$(sha256sum < "$conf" | cut -d' ' -f1)" == "$sha_conf" ]]; then
    e_conf=nuevo
  fi
fi
e_hook=ausente
if [[ -e "$hook" ]]; then
  e_hook=otro
  if [[ -f "$hook" && "$(sha256sum < "$hook" | cut -d' ' -f1)" == "$sha_hook" && "$(stat -c '%u %a' -- "$hook")" == "0 755" ]]; then
    e_hook=nuevo
  fi
fi
echo "== estado: $conf $e_conf, $hook $e_hook"
if [[ "$e_conf" == otro || "$e_hook" == otro ]]; then
  echo "apt-guardia-instalar: un destino existe con contenido, dueno o modo distinto del conocido; no se toca" >&2
  exit 3
fi
for paquete in "$critico" "$inocuo"; do
  if [[ "$(dpkg-query -W -f='${Status}' -- "$paquete" 2> /dev/null || true)" != "$instalado_ok" ]]; then
    echo "apt-guardia-instalar: $paquete no esta instalado; la validacion no podria discriminar; no se toca" >&2
    exit 4
  fi
done
if ! apt-get -s -o Debug::NoLocking=1 autoremove > /dev/null; then
  echo "apt-guardia-instalar: la simulacion de autoremove ya falla ANTES de instalar; no se toca" >&2
  exit 4
fi

if [[ "$e_hook" == ausente ]]; then
  tmp="$(mktemp "$dir_hook/.bb-apt-guardia.XXXXXX")"
  cat > "$tmp" <<'HOOK'
#!/bin/bash
# bb-apt-guardia: hook DPkg::Pre-Install-Pkgs de APT (protocolo version 3). Lo instala
# `sudo -n bb-root-run apt-guardia-instalar` (FEATURE-APT-CRITICAL-METAPACKAGE-GUARD).
# APT le pasa por stdin el plan que va a dar a dpkg. Si alguna linea **REMOVE** nombra un
# paquete de la lista de abajo, sale 1 y APT aborta ANTES de llamar a dpkg: no se aplica nada.
# Un plan sin esas remociones sale 0. No ejecuta ningun programa: solo builtins de bash.
# No corre bajo `apt-get -s`: la simulacion de APT no invoca hooks de dpkg.
# Permitir UNA transaccion: sudo apt -o BB::Apt-Guardia::Permitir=1 <la misma orden>
# Desactivar: sudo mv /etc/apt/apt.conf.d/00-bb-apt-guardia /etc/apt/apt.conf.d/00-bb-apt-guardia.disabled
set -euo pipefail

declare -A critico=()
while IFS= read -r p; do
  if [[ -n "$p" && "$p" != \#* ]]; then
    critico["$p"]=1
  fi
done <<'LISTA'
# Paquetes cuya remocion bloquea bb-apt-guardia (FEATURE-APT-CRITICAL-METAPACKAGE-GUARD).
# Un nombre por linea; '#' abre comentario de linea entera. Medido en el host el 2026-10-14
# (dpkg -l, apt-mark showhold, GRUB_DEFAULT de adopted/system-config/etc_default_grub).
# Esta lista la lee tools/verify_apt_critical_removals.py (verificador y colector); el hook
# usr_local_sbin_bb-apt-guardia (en adopted/pendiente-de-despliegue/, o en adopted/system-config/
# una vez desplegado) la lleva copiada y un test
# exige que sean iguales. Cambiarla obliga a regenerar el hook y el script sellado.
#
# Metapaquetes DGX OS (componente common de repo.download.nvidia.com/baseos)
nvidia-system-core
nvidia-system-extra
nvidia-system-station
nvidia-system-station-common
nvidia-system-station-core
nvidia-system-station-localization
nvidia-system-station-utils
nvidia-system-utils
# Identidad y actualizacion de la plataforma (dgx-spark-ota-update-meta esta en hold)
dgx-release
dgx-repo
dgx-spark-mlnx-hotplug
dgx-spark-ota-update-meta
dgxstation-desktop
dgxstation-grub
gigabyte-oobe-customize
# Kernel fijado en GRUB_DEFAULT (6.17.0-1032-nvidia) y su modulo NVIDIA
linux-image-6.17.0-1032-nvidia
linux-modules-6.17.0-1032-nvidia
linux-modules-nvidia-580-open-6.17.0-1032-nvidia
# Driver NVIDIA (rama 580, la soportada para Spark)
nvidia-driver-580-open
nvidia-kernel-common-580
# Arranque
grub-common
grub-efi-arm64
grub-efi-arm64-bin
grub-efi-arm64-signed
grub2-common
shim-signed
# Escritorio y red (hilos 348170 y 350340: autoremove ofrecia quitarlos)
gdm3
network-manager
ubuntu-desktop
ubuntu-desktop-minimal
LISTA

cabecera=
IFS= read -r cabecera || true
if [[ "$cabecera" != "VERSION 3" ]]; then
  echo "bb-apt-guardia: APT no envio 'VERSION 3' (llego '$cabecera'); se aborta la transaccion" >&2
  exit 1
fi
permitir=0
while IFS= read -r linea; do
  if [[ -z "$linea" ]]; then
    break
  fi
  if [[ "$linea" == "BB::Apt-Guardia::Permitir=1" ]]; then
    permitir=1
  fi
done
bloqueados=()
while read -r nombre _ _ _ _ _ _ _ accion; do
  if [[ -n "$nombre" && "${accion:-}" == "**REMOVE**" && -n "${critico[$nombre]+x}" ]]; then
    bloqueados+=("$nombre")
  fi
done
if (( ${#bloqueados[@]} == 0 )); then
  exit 0
fi
echo "bb-apt-guardia: esta transaccion quita paquetes criticos de la plataforma: ${bloqueados[*]}" >&2
if (( permitir == 1 )); then
  echo "bb-apt-guardia: permitida por -o BB::Apt-Guardia::Permitir=1" >&2
  exit 0
fi
echo "bb-apt-guardia: no se aplica nada. Para permitir ESTA transaccion: sudo apt -o BB::Apt-Guardia::Permitir=1 <la misma orden>" >&2
exit 1
HOOK
  if [[ "$(sha256sum < "$tmp" | cut -d' ' -f1)" != "$sha_hook" ]]; then
    echo "apt-guardia-instalar: el hook generado no tiene el sha256 esperado; no se toca" >&2
    exit 4
  fi
  chmod 0755 -- "$tmp"
  chown root:root -- "$tmp"
  mv -fT -- "$tmp" "$hook"
  tmp=
  creo_hook=1
  echo "== creado $hook ($sha_hook)"
fi
if [[ "$e_conf" == ausente ]]; then
  tmp="$(mktemp "$dir_conf/.bb-apt-guardia.XXXXXX")"
  cat > "$tmp" <<'CONF'
// bb-apt-guardia (FEATURE-APT-CRITICAL-METAPACKAGE-GUARD). Lo instala `sudo -n bb-root-run apt-guardia-instalar`.
// Antes de cada llamada a dpkg, APT pasa el plan a /usr/local/sbin/bb-apt-guardia, que aborta la
// transaccion si quita un paquete critico. Permitir una: sudo apt -o BB::Apt-Guardia::Permitir=1 ...
// Desactivar: renombrar este fichero a 00-bb-apt-guardia.disabled (APT ignora .disabled en silencio).
DPkg::Pre-Install-Pkgs { "/usr/local/sbin/bb-apt-guardia"; };
DPkg::Tools::Options::/usr/local/sbin/bb-apt-guardia::Version "3";
CONF
  if [[ "$(sha256sum < "$tmp" | cut -d' ' -f1)" != "$sha_conf" ]]; then
    echo "apt-guardia-instalar: el .conf generado no tiene el sha256 esperado; no se toca" >&2
    exit 4
  fi
  chmod 0644 -- "$tmp"
  chown root:root -- "$tmp"
  mv -fT -- "$tmp" "$conf"
  tmp=
  creo_conf=1
  echo "== creado $conf ($sha_conf)"
fi

fallo=
echo "== configuracion real, DPkg::Pre-Install-Pkgs:"
volcado="$(apt-config dump DPkg::Pre-Install-Pkgs)" || fallo="el volcado de la configuracion salio con error"
echo "$volcado"
version="$(apt-config shell V DPkg::Tools::Options::/usr/local/sbin/bb-apt-guardia::Version)" || fallo="la consulta de la configuracion salio con error"
linea_hook='DPkg::Pre-Install-Pkgs:: "/usr/local/sbin/bb-apt-guardia";'
if [[ $'\n'"$volcado"$'\n' != *$'\n'"$linea_hook"$'\n'* || "$version" != "V='3'" ]]; then
  fallo="${fallo:-la configuracion real no registra el hook con protocolo 3 ($version)}"
fi
if [[ -z "$fallo" ]] && ! apt-get -s -o Debug::NoLocking=1 autoremove > /dev/null; then
  fallo="la simulacion de autoremove falla con la guardia instalada"
fi
if [[ -z "$fallo" ]]; then
  caja="$(mktemp -d /run/bb-apt-guardia.XXXXXX)"
  mkdir -p -- "$caja/parts" "$caja/state" "$caja/cache/archives/partial" "$caja/log"
  cp -- "$estado_dpkg" "$caja/status"
  cp -- "$conf" "$caja/parts/00-bb-apt-guardia"
  cat > "$caja/dpkg" <<'STUB'
#!/bin/sh
for a in "$@"; do
  case "$a" in --print-foreign-architectures|--print-architecture) exec /usr/bin/dpkg "$a";; esac
done
echo "$*" >> "$(dirname "$0")/dpkg.log"
exit 0
STUB
  chmod 0755 -- "$caja/dpkg"
  printf 'Dir::Etc::main "/dev/null";\nDir::Etc::parts "%s/parts";\n' "$caja" > "$caja/apt.conf"
  opciones=(-o Debug::NoLocking=1 -o "Dir::State=$caja/state" -o Dir::State::lists=/var/lib/apt/lists -o "Dir::State::status=$caja/status" -o "Dir::Cache=$caja/cache" -o "Dir::Log=$caja/log" -o "Dir::Bin::dpkg=$caja/dpkg")
  aislada="$(APT_CONFIG="$caja/apt.conf" apt-config "${opciones[@]}" shell P Dir::Etc::parts/ B Dir::Bin::dpkg || true)"
  if [[ "$aislada" != "P='$caja/parts/'"$'\n'"B='$caja/dpkg'" ]]; then
    fallo="la caja no aisla la configuracion de APT ($aislada); no se transacciona"
  fi
fi
if [[ -z "$fallo" ]]; then
  rc=0
  APT_CONFIG="$caja/apt.conf" apt-get "${opciones[@]}" -y remove "$critico" > "$caja/critico.txt" 2>&1 || rc=$?
  echo "== caja: remove $critico, rc $rc"
  grep -E '^(E:|bb-apt-guardia:)' "$caja/critico.txt" || true
  if [[ "$rc" == 0 ]] || ! grep -q '^bb-apt-guardia: esta transaccion quita' "$caja/critico.txt" || grep -qs -e '--remove' "$caja/dpkg.log"; then
    fallo="la remocion de $critico no fue abortada por la guardia antes de dpkg"
  fi
fi
if [[ -z "$fallo" ]]; then
  rc=0
  APT_CONFIG="$caja/apt.conf" apt-get "${opciones[@]}" -y remove "$inocuo" > "$caja/inocuo.txt" 2>&1 || rc=$?
  echo "== caja: remove $inocuo, rc $rc. El stub de dpkg recibio:"
  cat "$caja/dpkg.log" 2> /dev/null || true
  if [[ "$rc" != 0 ]] || ! grep -qs -e "--remove $inocuo" "$caja/dpkg.log"; then
    fallo="la remocion inocua de $inocuo no llego a dpkg (rc $rc)"
  fi
fi

if [[ -n "$fallo" ]]; then
  echo "apt-guardia-instalar: VALIDACION FALLIDA: $fallo" >&2
  if [[ "$creo_conf" == 1 ]]; then
    rm -f -- "$conf"
    echo "apt-guardia-instalar: borrado $conf (lo creo esta corrida)" >&2
  fi
  if [[ "$creo_hook" == 1 ]]; then
    rm -f -- "$hook"
    echo "apt-guardia-instalar: borrado $hook (lo creo esta corrida)" >&2
  fi
  exit 5
fi
echo "== guardia activa y validada: $critico abortado antes de dpkg, $inocuo permitido"
