#!/usr/bin/env bash
# bb-root-run dmem-tope-aplicar -- pone dmem.max (tope de memoria de GPU) al cgroup del motor vLLM y a user.slice.
# Escribe: dmem.max del cgroup del motor y de user.slice (bajo /sys/fs/cgroup), y UNA copia de los valores previos en
#      /var/lib/blackbox/dmem-tope-previo.json (root:root 0644). Nada mas.
# Por que: el modulo NVIDIA parcheado ya COBRA la memoria de GPU por cgroup y hace cumplir dmem.max (medido 2026-10-12);
#      sin tope puesto, un proceso que se desboca se come la region entera y arrastra al motor. Los topes salen de lo
#      medido en gpumem_historial.jsonl (2026-10-13..16): pico del motor 35.23 GiB; pico de user.slice 25.89 GiB en un
#      arranque y 5.26 GiB en el otro. Motor 40 GiB + user.slice 8 GiB = 48 GiB, bajo la capacidad de la region (50.1 GiB).
# Guardas: la region sale de dmem.capacity y debe ser UNA; el cgroup del motor es el de los procesos cuyo comm es
#      VLLM::EngineCor y debe ser UN solo cgroup de la forma /<x>.slice/<y>.scope; el consumo actual de cada cgroup debe
#      caber en su tope (si no, no se toca nada: el motor quedaria sobre el tope); la suma de topes debe caber en la
#      capacidad; si una escritura falla o la lectura de vuelta no coincide, se devuelven los valores previos.
#      Revierte con `bb-root-run dmem-tope-quitar`.
# Desbloquea: FEATURE-LIMITADOR-INTEGRAR-LANZADOR-FALLA-CERRADO-01.
# Sin red, sin argumentos.
set -euo pipefail
umask 022

raiz=${BB_DMEM_CGROUP_RAIZ:-/sys/fs/cgroup}   # el runner construye el entorno desde cero: en produccion no se puede cambiar
base=${BB_DMEM_ESTADO:-/var/lib/blackbox}
proc=${BB_DMEM_PROC:-/proc}
comm_motor=VLLM::EngineCor
tope_motor_gib=40
tope_user_gib=8
gib=1073741824
msg=
archivo=

fallo() { echo "dmem-tope-aplicar: $msg" >&2; exit 3; }
leer() { while read -r r v; do if [[ "$r" == "$region" ]]; then echo "$v"; fi; done < "$archivo"; }

[[ -f "$raiz/dmem.capacity" ]] || { msg="no hay dmem.capacity: el modulo no da region"; fallo; }
[[ $(grep -c . "$raiz/dmem.capacity") -eq 1 ]] || { msg="dmem.capacity no tiene exactamente UNA region"; fallo; }
read -r region capacidad < "$raiz/dmem.capacity"
[[ "$capacidad" =~ ^[0-9]+$ ]] || { msg="capacidad ilegible: $capacidad"; fallo; }

rutas=
for c in "$proc"/[0-9]*/comm; do
  read -r nombre 2>/dev/null < "$c" || continue
  [[ "$nombre" == "$comm_motor" ]] || continue
  pid=${c#"$proc"/}
  pid=${pid%/comm}
  rutas+=$(sed -n 's/^0:://p' "$proc/$pid/cgroup")$'\n'
done
ruta_motor=$(printf '%s' "$rutas" | sort -u | grep . || true)
[[ -n "$ruta_motor" ]] || { msg="no hay proceso $comm_motor: el motor no esta corriendo"; fallo; }
[[ $(printf '%s\n' "$ruta_motor" | wc -l) -eq 1 ]] || { msg="los procesos $comm_motor estan en mas de un cgroup: $ruta_motor"; fallo; }
[[ "$ruta_motor" =~ ^/[a-z0-9.-]+\.slice/[a-zA-Z0-9_.:-]+\.scope$ ]] || { msg="cgroup inesperado del motor: $ruta_motor"; fallo; }

motor="$raiz$ruta_motor"
usuario="$raiz/user.slice"
tope_motor=$((tope_motor_gib * gib))
tope_user=$((tope_user_gib * gib))
((tope_motor + tope_user <= capacidad)) || { msg="los topes no caben en la capacidad ($capacidad B)"; fallo; }

for cg in "$motor" "$usuario"; do
  [[ -f "$cg/dmem.max" && -f "$cg/dmem.current" ]] || { msg="$cg no tiene archivos dmem (el padre no delega dmem)"; fallo; }
  [[ ! -L "$cg" ]] || { msg="$cg es un symlink"; fallo; }
done
archivo="$motor/dmem.current"; actual_motor=$(leer)
archivo="$usuario/dmem.current"; actual_user=$(leer)
[[ "$actual_motor" =~ ^[0-9]+$ && "$actual_user" =~ ^[0-9]+$ ]] || { msg="consumo ilegible"; fallo; }
((actual_motor <= tope_motor)) || { msg="el motor usa $actual_motor B, por encima del tope $tope_motor B: no se toca nada"; fallo; }
((actual_user <= tope_user)) || { msg="user.slice usa $actual_user B, por encima del tope $tope_user B: no se toca nada"; fallo; }

[[ -d "$base" && ! -L "$base" ]] || { msg="$base no es un directorio normal"; fallo; }
archivo="$motor/dmem.max"; previo_motor=$(leer)
archivo="$usuario/dmem.max"; previo_user=$(leer)
printf '{"region":"%s","motor":{"cgroup":"%s","previo":"%s"},"user":{"cgroup":"%s","previo":"%s"}}\n' \
  "$region" "$motor" "$previo_motor" "$usuario" "$previo_user" > "$base/dmem-tope-previo.json"

if ! { printf '%s %s\n' "$region" "$tope_motor" > "$motor/dmem.max" && printf '%s %s\n' "$region" "$tope_user" > "$usuario/dmem.max"; } 2>/dev/null; then
  ok=0
else
  archivo="$motor/dmem.max"; leido_motor=$(leer)
  archivo="$usuario/dmem.max"; leido_user=$(leer)
  ok=1
  [[ "$leido_motor" == "$tope_motor" && "$leido_user" == "$tope_user" ]] || ok=0
fi
if [[ "$ok" -ne 1 ]]; then
  printf '%s %s\n' "$region" "$previo_motor" > "$motor/dmem.max" || true
  printf '%s %s\n' "$region" "$previo_user" > "$usuario/dmem.max" || true
  msg="la escritura fallo o la lectura de vuelta no coincide; se devolvieron los valores previos"
  fallo
fi
echo "dmem-tope-aplicar: motor=$tope_motor B, user.slice=$tope_user B en $region (previos guardados en $base/dmem-tope-previo.json)"
