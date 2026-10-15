#!/usr/bin/env bash
# bb-root-run watchdog-propietario -- SOLO LECTURA.
# Lee: que procesos tienen abierto /dev/watchdog o /dev/watchdog0 (`fuser -v`, que hace
#      stat del dispositivo y recorre /proc/*/fd; NO lo abre: abrir /dev/watchdog lo arma
#      y su cierre sin 'V' puede reiniciar la maquina), el boot_id y el estado sysfs del
#      watchdog0 (identity, state, timeout, nowayout, bootstatus).
# Por que: sin root /proc/1/fd es ilegible y `fuser` del usuario sale 1 sin decir nada,
#      asi que el propietario queda UNKNOWN; el verificador exige un unico PID.
# Desbloquea: FEATURE-FORUM-SBSA-WATCHDOG-STATE-01.
# Escribe: nada fuera de stdout. Sin red, sin argumentos.
set -euo pipefail

wd=/sys/class/watchdog/watchdog0

echo "== boot_id"
cat /proc/sys/kernel/random/boot_id
echo "== fuser -v de los dos nodos del watchdog"
rc=0
fuser -v /dev/watchdog /dev/watchdog0 || rc=$?
echo "fuser rc=$rc (0: alguien lo tiene abierto; 1: nadie, o no se pudo ver)"
echo "== $wd"
for a in identity state timeout nowayout bootstatus; do
  if [[ -r "$wd/$a" ]]; then
    printf '%s=%s\n' "$a" "$(cat -- "$wd/$a")"
  else
    echo "$a: ilegible o ausente"
  fi
done
