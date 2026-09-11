#!/usr/bin/env bash
# Arma las piezas de blackbox que necesitan root. Idempotente y reversible.
#
#   sudo ./enable-privileged.sh           aplica
#   sudo ./enable-privileged.sh --revert  deshace
#   ./enable-privileged.sh --dry-run      ensena que haria, sin tocar nada
#
# Que cambia y por que:
#   1. systemd-coredump  -- hoy ulimit -c = 0 y no hay coredumpctl: ningun
#      proceso deja volcado. Es lo que impidio saber por que murio el
#      renderizador de claude-desktop el 2026-09-07.
#   2. sysstat ENABLED   -- el paquete esta instalado y el servicio activo,
#      pero con ENABLED="false": sus datos paran el 2026-08-27.
#   3. limite de core    -- sin esto, systemd-coredump recibe procesos truncados.
#
# NO cambia kernel.dmesg_restrict: `journalctl -k` ya da el log del kernel a
# este usuario (grupo adm), asi que abrir dmesg no anade informacion.

set -euo pipefail

REVERT=0; DRY=0
for a in "$@"; do
  case "$a" in
    --revert) REVERT=1 ;;
    --dry-run) DRY=1 ;;
    *) echo "opcion desconocida: $a" >&2; exit 2 ;;
  esac
done

BACKUP="/var/backups/blackbox"
run() { if [ "$DRY" = 1 ]; then echo "  [dry-run] $*"; else "$@"; fi; }

if [ "$DRY" = 0 ] && [ "$(id -u)" != "0" ]; then
  echo "hace falta root: sudo $0 $*" >&2; exit 1
fi

# ------------------------------------------------------------------- revertir
if [ "$REVERT" = 1 ]; then
  echo "== revirtiendo =="
  if [ -f "$BACKUP/sysstat" ]; then
    run cp "$BACKUP/sysstat" /etc/default/sysstat
    echo "  /etc/default/sysstat restaurado"
  else
    echo "  /etc/default/sysstat: sin copia previa, NO se toca"
  fi
  run rm -f /etc/security/limits.d/99-blackbox-core.conf
  run rm -f /etc/systemd/coredump.conf.d/99-blackbox.conf
  echo "  limites y coredump.conf de blackbox retirados"
  echo
  echo "  systemd-coredump NO se desinstala (quitarlo devuelve core_pattern a"
  echo "  apport, y esa decision es tuya): sudo apt remove systemd-coredump"
  exit 0
fi

# -------------------------------------------------------------------- aplicar
echo "== armando blackbox (parte privilegiada) =="
run mkdir -p "$BACKUP"

# --- 1. systemd-coredump ------------------------------------------------
echo
echo "-- 1. captura de core dumps --"
if command -v coredumpctl >/dev/null 2>&1; then
  echo "  systemd-coredump ya instalado"
else
  echo "  instalando systemd-coredump (esto sustituye apport como core_pattern)"
  run apt-get install -y systemd-coredump
fi

# Techo de disco: un renderer de Electron o un proceso node rondan los 4 GB,
# asi que sin limite unos pocos crashes llenan /var.
run mkdir -p /etc/systemd/coredump.conf.d
if [ "$DRY" = 0 ]; then
  cat >/etc/systemd/coredump.conf.d/99-blackbox.conf <<'CONF'
# blackbox: techo explicito para que los volcados no llenen /var
[Coredump]
Storage=external
Compress=yes
ProcessSizeMax=8G
ExternalSizeMax=8G
MaxUse=20G
KeepFree=50G
CONF
else
  echo "  [dry-run] escribiria /etc/systemd/coredump.conf.d/99-blackbox.conf"
fi
echo "  techo de volcados: 20G maximo, 8G por proceso, 50G siempre libres"

# --- 2. limite de core --------------------------------------------------
echo
echo "-- 2. limite de core --"
if [ "$DRY" = 0 ]; then
  cat >/etc/security/limits.d/99-blackbox-core.conf <<'CONF'
# blackbox: permitir volcados completos (systemd-coredump aplica su propio techo)
*  soft  core  unlimited
*  hard  core  unlimited
CONF
else
  echo "  [dry-run] escribiria /etc/security/limits.d/99-blackbox-core.conf"
fi
echo "  ulimit -c pasa a unlimited en sesiones NUEVAS (hay que reentrar)"

# systemd no lee limits.conf para sus servicios; los de usuario van aparte
run mkdir -p /etc/systemd/system.conf.d
if [ "$DRY" = 0 ]; then
  printf '[Manager]\nDefaultLimitCORE=infinity\n' >/etc/systemd/system.conf.d/99-blackbox.conf
  mkdir -p /etc/systemd/user.conf.d
  printf '[Manager]\nDefaultLimitCORE=infinity\n' >/etc/systemd/user.conf.d/99-blackbox.conf
else
  echo "  [dry-run] DefaultLimitCORE=infinity en system.conf.d y user.conf.d"
fi

# --- 3. sysstat ---------------------------------------------------------
# NO se toca. /etc/default/sysstat dice ENABLED="false", pero el drop-in
# /etc/systemd/system/sysstat-collect.timer.d/override.conf dispara la
# recoleccion cada minuto igualmente, y hay datos frescos (comprobado
# 2026-09-07: sa20260907 escrito hace <1 min). Cambiar ENABLED aqui seria
# arreglar un problema que no existe, guiandose por la variable en vez de
# por los datos.
echo
echo "-- 3. historico de sar --"
if [ -n "$(find /var/log/sysstat -name "sa$(date +%Y%m%d)" -mmin -10 2>/dev/null)" ]; then
  echo "  sar YA recolecta (datos de hace menos de 10 min): no se toca nada"
else
  echo "  sar sin datos frescos. Revisa el drop-in antes de cambiar ENABLED:"
  echo "    systemctl list-timers sysstat-collect.timer"
  echo "    cat /etc/systemd/system/sysstat-collect.timer.d/override.conf"
fi

# --- recarga ------------------------------------------------------------
echo
run systemctl daemon-reexec

echo
echo "== estado tras aplicar =="
if [ "$DRY" = 0 ]; then
  echo "  core_pattern: $(cat /proc/sys/kernel/core_pattern)"
  echo "  coredumpctl:  $(command -v coredumpctl >/dev/null && echo presente || echo AUSENTE)"
  echo "  sysstat:      $(grep -h '^ENABLED' /etc/default/sysstat 2>/dev/null || echo '?')"
  echo
  echo "  CONTROL NEGATIVO -- comprueba que la captura de verdad funciona:"
  echo "    sleep 60 & kill -SEGV \$!    # y luego:  coredumpctl list"
  echo "    Si no aparece una fila, la captura NO esta armada por mucho que"
  echo "    este informe diga que si."
  echo
  echo "  El limite de core solo aplica a sesiones nuevas: cierra y reabre"
  echo "  la terminal, o reinicia, antes de fiarte de 'bb status'."
fi
