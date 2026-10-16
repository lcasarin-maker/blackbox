#!/usr/bin/env bash
# bb-root-run dmem-tope-quitar -- devuelve dmem.max del motor y de user.slice a los valores que guardo dmem-tope-aplicar.
# Escribe: dmem.max de los dos cgroups que dmem-tope-aplicar registro en /var/lib/blackbox/dmem-tope-previo.json (los
#      resuelve de ese fichero, que es de root, y exige que sigan bajo /sys/fs/cgroup y que sean un <x>.slice/<y>.scope
#      o user.slice). Borra ese fichero al terminar bien. Nada mas.
# Por que: el retroceso del tope. Si el motor ya no existe (otro id de cgroup), solo avisa y sigue con el otro cgroup.
# Desbloquea: FEATURE-LIMITADOR-INTEGRAR-LANZADOR-FALLA-CERRADO-01.
# Sin red, sin argumentos.
set -euo pipefail
umask 022

raiz=${BB_DMEM_CGROUP_RAIZ:-/sys/fs/cgroup}
base=${BB_DMEM_ESTADO:-/var/lib/blackbox}
previo="$base/dmem-tope-previo.json"
msg=
archivo=

fallo() { echo "dmem-tope-quitar: $msg" >&2; exit 3; }
leer() { while read -r r v; do if [[ "$r" == "$region" ]]; then echo "$v"; fi; done < "$archivo"; }

[[ -f "$previo" && ! -L "$previo" ]] || { msg="no hay $previo: nada que quitar"; fallo; }
[[ $(stat -c %u "$previo") -eq ${BB_DMEM_UID_ESPERADO:-0} ]] || { msg="$previo no es de root"; fallo; }
region=$(jq -er .region "$previo")
for quien in motor user; do
  cg=$(jq -er ".$quien.cgroup" "$previo")
  valor=$(jq -er ".$quien.previo" "$previo")
  [[ "$cg" =~ ^"$raiz"/[a-z0-9.-]+\.slice/[a-zA-Z0-9_.:-]+\.scope$ || "$cg" == "$raiz/user.slice" ]] || { msg="cgroup fuera de lo permitido: $cg"; fallo; }
  [[ "$valor" == max || "$valor" =~ ^[0-9]+$ ]] || { msg="valor previo ilegible: $valor"; fallo; }
  if [[ ! -f "$cg/dmem.max" ]]; then
    echo "dmem-tope-quitar: $cg ya no existe; se omite"
    continue
  fi
  printf '%s %s\n' "$region" "$valor" > "$cg/dmem.max"
  archivo="$cg/dmem.max"; leido=$(leer)
  [[ "$leido" == "$valor" ]] || { msg="$cg: lei $leido y esperaba $valor"; fallo; }
  echo "dmem-tope-quitar: $cg dmem.max=$valor"
done
rm -f -- "$previo"
