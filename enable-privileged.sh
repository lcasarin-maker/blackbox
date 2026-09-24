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
#   4. accounting de GPU -- sin esto, `bb scan` solo ve procesos de GPU VIVOS;
#      el que ya salio para cuando se corre el scan es invisible.
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
  if systemctl list-unit-files bb-usable.service >/dev/null 2>&1; then
    run systemctl disable --now bb-usable.service
    run rm -f /etc/systemd/system/bb-usable.service
    echo "  bb-usable desarmado y retirado"
  fi
  if [ -f "$BACKUP/earlyoom" ]; then
    run cp "$BACKUP/earlyoom" /etc/default/earlyoom
    run systemctl restart earlyoom.service
    echo "  /etc/default/earlyoom restaurado"
  else
    echo "  /etc/default/earlyoom: sin copia previa, NO se toca"
  fi
  if [ -f /etc/modprobe.d/99-blackbox-uvm.conf ]; then
    run rm -f /etc/modprobe.d/99-blackbox-uvm.conf
    echo "  uvm_global_oversubscription vuelve a su defecto (tras reiniciar)"
  fi
  if [ -f "$BACKUP/grub" ]; then
    run cp "$BACKUP/grub" /etc/default/grub
    run update-grub
    echo "  /etc/default/grub restaurado (kernel por defecto y menu como estaban)"
  else
    echo "  /etc/default/grub: sin copia previa, NO se toca"
  fi
  if [ -f /etc/audit/rules.d/10-blackbox-signals.rules ]; then
    run rm -f /etc/audit/rules.d/10-blackbox-signals.rules
    run augenrules --load
    echo "  regla de auditoria de senales retirada (DGX-438 se queda sin instrumento)"
  fi
  run rm -f /etc/security/limits.d/99-blackbox-core.conf
  run rm -f /etc/systemd/coredump.conf.d/99-blackbox.conf
  echo "  limites y coredump.conf de blackbox retirados"
  if command -v nvidia-smi >/dev/null 2>&1; then
    run nvidia-smi -am 0 && echo "  accounting mode de GPU apagado"
  fi
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

# --- 4. accounting mode de GPU -------------------------------------------
# `bb scan` solo veia procesos de GPU VIVOS via --query-compute-apps: el que
# ya salio para cuando se corre el scan quedaba invisible, justo la pregunta
# forense de "quien uso la GPU antes del fallo". Accounting mode retiene
# pid/gpu_util/mem_util/memoria_max/tiempo por proceso hasta que se limpian o
# el driver se reinicia. Verificado 2026-09-11: apagado por defecto, y
# `nvidia-smi -am 1` sin root falla con "Insufficient Permissions".
#
# NO sobrevive un reinicio del driver por si solo, a diferencia de los
# ficheros de arriba -- si hace falta que sobreviva un reboot, sumar
# `nvidia-smi -am 1` como segundo ExecStart del oneshot que ya reaplica -lgc
# en el arranque (adopted/system-config/etc_systemd_system_atom-clock-lock.
# service), fuera del alcance de este script.
echo
echo "-- 4. accounting de GPU (bb scan: quien uso la GPU y ya salio) --"
if command -v nvidia-smi >/dev/null 2>&1; then
  if run nvidia-smi -am 1; then
    echo "  accounting mode: Enabled (hasta el proximo reinicio del driver)"
  else
    echo "  no se pudo activar accounting mode (revisa el error de arriba)"
  fi
else
  echo "  nvidia-smi no disponible, se omite"
fi

# --- 5. vigilante de usabilidad (bb-usable) ------------------------------
echo
echo "-- 5. vigilante de usabilidad --"
# Por que: RuntimeWatchdogSec=60 estaba armado los dias 22 y 23 y no disparo
# ninguna de las dos veces, porque vigila a PID 1 y PID 1 estaba sano (570 a
# 1578 lineas de journal por hora durante el congelamiento). bb-usable
# contesta la otra pregunta -- si la maquina sirve -- pidiendo 64 MiB y
# tocandolos. Ver bin/bb-usable para la calibracion y sus margenes.
# Esto NO desarma el watchdog de PID 1: convive con el.
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ "$DRY" = 0 ]; then
  sed "s|/home/lcasarin/projects/blackbox|$SELF_DIR|g" \
      "$SELF_DIR/systemd/bb-usable.service" > /etc/systemd/system/bb-usable.service
  systemctl daemon-reload
  systemctl enable --now bb-usable.service
else
  echo "  [dry-run] instalaria /etc/systemd/system/bb-usable.service y lo activaria"
fi
echo "  bb-usable armado: sonda cada 30s, plazo 300s, WatchdogSec=360,"
echo "  FailureAction=reboot-immediate"

# --- 6. punteria de earlyoom ---------------------------------------------
echo
echo "-- 6. punteria de earlyoom --"
# Medido 2026-09-22 05:51:40: earlyoom disparo UNA vez en 17h45m y mato
# 'VLLM::EngineCor' -- 33 GiB de GPU, el proceso util -- dejando vivos a los
# veinte workers de pytest que eran la causa. No fue mala suerte: 'vllm'
# estaba en --prefer. Esto lo saca de ahi y mete a 'pytest'.
#
# LIMITE DECLARADO: esto corrige la punteria, NO el umbral. earlyoom solo
# sabe leer MemAvailable y SwapFree, y MemAvailable marco 56 % durante las
# 17 horas -- por eso disparo una vez y nunca mas. Con esta correccion
# seguira sin disparar en un caso como los medidos. Quien cubre eso es
# bb-usable, no earlyoom.
if [ -f /etc/default/earlyoom ]; then
  run cp -n /etc/default/earlyoom "$BACKUP/earlyoom"
  if [ "$DRY" = 0 ]; then
    sed -i "s/--prefer '(vllm|VLLM|python3|triton)'/--prefer '(pytest|python3|triton)'/" \
        /etc/default/earlyoom
    systemctl restart earlyoom.service
    echo "  --prefer ahora: $(grep -o "\-\-prefer '[^']*'" /etc/default/earlyoom)"
  else
    echo "  [dry-run] quitaria vllm de --prefer y anadiria pytest"
  fi
else
  echo "  /etc/default/earlyoom no existe, se omite"
fi

# --- 7. quien manda el SIGTERM (DEBT-DGX-438) ----------------------------
echo
echo "-- 7. auditoria de senales: quien mata a quien --"
# Por que: DEBT-DGX-438 lleva abierta desde el 2026-09-08. Algo mata procesos
# python de fondo con SIGTERM a intervalos irregulares (10-15 min) y no se
# sabe que. Descartados CON evidencia: systemd-oomd (`is-enabled` -> not-found,
# ni instalado), la mitigacion de atom_gpu_telemetry.py (usa SIGSTOP/SIGCONT,
# no mata) y liberation_watchdog.py (no envia kill a nadie). Vivos: earlyoom y
# un cgroup ajeno con TimeoutStopSec. Los dos mandan la senal por syscall, o
# sea que los dos caen en una regla de auditoria -- y auditd YA corre aqui.
#
# Medido 2026-09-23 sobre /var/log/audit: 0 eventos de syscall kill en las
# 4 h 08 min que cubria el anillo. No es que nadie matara: es que nadie
# miraba. Falta la regla, no el demonio.
if [ "$DRY" = 0 ] && ! command -v auditctl >/dev/null 2>&1; then
  echo "  auditctl no esta: se omite (instala auditd para cerrar DGX-438)"
else
  run mkdir -p /etc/audit/rules.d
  if [ "$DRY" = 0 ]; then
    cat >/etc/audit/rules.d/10-blackbox-signals.rules <<'RULES'
## blackbox -- DEBT-DGX-438: quien manda la senal que mata.
## Se carga con `augenrules --load`. El numero 10 es para entrar ANTES que la
## regla estandar que genera el diluvio de abajo: auditd resuelve por primera
## coincidencia, asi que un `never` posterior no serviria de nada.

## (1) Callar el diluvio, sin cegar la regla que lo produce.
## La regla estandar `reboot_cmd` audita loginctl/systemctl para saber quien
## reinicio la maquina. rustdesk.service la dispara sondeando sesiones:
## medido 2026-09-23, 12934 de 12961 execve del anillo eran /usr/bin/loginctl
## -- 99.8 % del registro -- a 1.9/s con solo el servicio root, y a 14.6/s
## mientras vive su hijo --server. A esa tasa el anillo (5 x 8 MiB) cae de
## 248 min a 37 min, y una captura de kill envejeceria antes de que nadie la
## lea. Esta linea excluye SOLO la invocacion de demonio: los 12934 llevan
## auid=unset y un humano deja auid puesto (control corrido el 2026-09-23:
## `loginctl` desde esta terminal quedo con auid=1000, y antes de ese control
## habia 0 eventos de loginctl con auid humano en tres ficheros del anillo;
## systemctl da 106 con auid=1000 frente a 10 unset). Lo que reboot_cmd
## existe para ver -- una persona apagando la maquina -- se sigue auditando.
-a never,exit -F arch=b64 -S execve -F exe=/usr/bin/loginctl -F auid=unset

## (2) La captura. kill/tkill llevan la senal en a1; tgkill la lleva en a2,
## asi que van en lineas distintas -- una sola regla con -F a1 dejaria pasar
## todo tgkill sin que nada lo dijera.
-a always,exit -F arch=b64 -S kill -S tkill -F a1=15 -k blackbox_sigterm
-a always,exit -F arch=b64 -S tgkill -F a2=15 -k blackbox_sigterm
-a always,exit -F arch=b64 -S kill -S tkill -F a1=9 -k blackbox_sigkill
-a always,exit -F arch=b64 -S tgkill -F a2=9 -k blackbox_sigkill
RULES
    augenrules --load >/dev/null 2>&1 || auditctl -R /etc/audit/rules.d/10-blackbox-signals.rules >/dev/null 2>&1 || true
  else
    echo "  [dry-run] escribiria /etc/audit/rules.d/10-blackbox-signals.rules y la cargaria"
  fi

  # VERIFICAR, no suponer. Los ficheros de rules.d se concatenan en orden
  # lexico, y un `-D` (borra todas las reglas) en un fichero que ordene
  # DESPUES de 10- dejaria estas reglas escritas en disco y ausentes del
  # kernel. Eso se lee igual que "instalado" y no lo esta, asi que se mira.
  if [ "$DRY" = 0 ]; then
    if auditctl -l 2>/dev/null | grep -q "blackbox_sigterm"; then
      echo "  reglas CARGADAS en el kernel (auditctl -l las ve)"
      echo "  emisor y victima quedan en /var/log/audit; se leen con: bb sigterm"
    else
      echo "  AVISO: las reglas se escribieron pero auditctl -l NO las ve."
      echo "  Algo las esta borrando despues de cargarlas -- lo tipico es un -D"
      echo "  en un fichero de /etc/audit/rules.d que ordene despues de 10-."
      echo "  Comprueba:  grep -rn '^-D' /etc/audit/rules.d/"
      echo "  Hasta que aparezcan ahi, DGX-438 sigue sin instrumento y"
      echo "  'bb sigterm' te lo dira en vez de darte un cero limpio."
    fi
    echo
    echo "  CONTROL NEGATIVO -- comprueba que la captura de verdad funciona:"
    echo "    sleep 300 & kill -TERM \$!    # y luego:  bb sigterm '5 minutes ago'"
    echo "    Tiene que salir una fila con TU terminal como emisor. Si sale"
    echo "    vacia, la regla no esta capturando por mucho que -l la liste."
  fi
fi

# --- 8. mitigaciones del bug de NVIDIA #1358 -----------------------------
echo
echo "-- 8. mitigaciones del cuelgue por memoria unificada (NVIDIA #1358) --"
# Por que: esta maquina se congelo TRES veces (2026-09-22 x2, 2026-09-24) y el
# boot del primer caso tiene 203 ocurrencias de
#   NVRM: Check failed: Out of memory [NV_ERR_NO_MEMORY] ... _memdescAllocInternal
# que es la firma exacta de NVIDIA/open-gpu-kernel-modules#1358, abierto y sin
# fix. Tres reporteros independientes en GB10, tres cargas distintas (vLLM,
# hashcat, DeepSeek+NCCL); uno lo disparo con `hashcat -I`, una consulta de
# identificacion de dispositivo.
#
# MEDIDO AQUI antes de escribir esto: los cgroups NO ven esa memoria. 7 GiB de
# GPU tomados con torch -> el memory.current del slice sube 15 MiB, el 0.2 %.
# Por eso el techo de app.slice no cubre este fallo y hacen falta estas dos.
#
# Las dos salen del hilo, ninguna esta medida en NUESTRA carga, y se aplican
# juntas por decision de Luis (2026-09-24) aceptando que si deja de
# congelarse no sabremos cual de las dos lo arreglo.

# --- 8a. uvm_global_oversubscription -------------------------------------
# El asignador UVM admite peticiones por encima de lo disponible fisicamente
# esperando reconciliarlas despues, y eso es lo que convierte un fallo de
# asignacion que deberia ser limpio en un cuelgue. Un reportero del hilo lo
# puso a 0: el cuelgue silencioso IRRECUPERABLE paso a un OOM global
# RECUPERABLE. Sigue barriendo procesos ajenos (vio morir sshd,
# NetworkManager, contenedores) -- protege la caja, no lo que corre en ella.
if [ "$DRY" = 0 ]; then
  cat >/etc/modprobe.d/99-blackbox-uvm.conf <<'CONF'
# blackbox: NVIDIA/open-gpu-kernel-modules#1358 -- sin esto, una peticion de
# memoria unificada por encima de lo disponible cuelga el host entero en vez
# de fallar. Con esto, el kernel puede al menos matar y sobrevivir.
options nvidia_uvm uvm_global_oversubscription=0
CONF
  echo "  /etc/modprobe.d/99-blackbox-uvm.conf escrito"
else
  echo "  [dry-run] escribiria /etc/modprobe.d/99-blackbox-uvm.conf"
fi
echo "  valor EN CALIENTE (no cambia hasta recargar el modulo o reiniciar):"
echo "    $(cat /sys/module/nvidia_uvm/parameters/uvm_global_oversubscription 2>/dev/null || echo '?')"

# --- 8b. volver al kernel 6.17.0-1032-nvidia ------------------------------
# Un reportero con 2 Sparks: 7 de 7 arranques fallidos en 7.0.0-1019-nvidia y
# el MISMO driver sobre 6.17.0-1032-nvidia funciono a la primera y siguio
# estable. Nosotros corremos el primero y tenemos el segundo instalado, con su
# linux-modules-nvidia-580-open correspondiente (comprobado con dpkg).
KOBJ="6.17.0-1032-nvidia"
if [ ! -e "/boot/vmlinuz-$KOBJ" ]; then
  echo "  AVISO: /boot/vmlinuz-$KOBJ no existe. NO se toca GRUB."
elif ! dpkg -l "linux-modules-nvidia-580-open-$KOBJ" >/dev/null 2>&1; then
  echo "  AVISO: no hay modulos nvidia para $KOBJ. Arrancar ahi dejaria la GPU"
  echo "  sin driver, que es peor que el bug. NO se toca GRUB."
elif [ "$DRY" = 0 ]; then
  run cp -n /etc/default/grub "$BACKUP/grub"
  SUB=$(awk -F"'" '/^submenu/ {print $2; exit}' /boot/grub/grub.cfg 2>/dev/null)
  ENT=$(awk -F"'" "/menuentry .*$KOBJ'/ {print \$2; exit}" /boot/grub/grub.cfg 2>/dev/null)
  if [ -z "$ENT" ]; then
    echo "  AVISO: no encuentro la entrada de GRUB para $KOBJ. NO se toca GRUB."
  else
    [ -n "$SUB" ] && DEF="$SUB>$ENT" || DEF="$ENT"
    sed -i "s|^GRUB_DEFAULT=.*|GRUB_DEFAULT=\"$DEF\"|" /etc/default/grub
    # Escotilla: hoy el menu esta OCULTO con timeout 0. Cambiar el kernel por
    # defecto sin dejar forma de elegir otro es quedarse sin salida si el
    # nuevo no arranca. 5 segundos de menu es el precio.
    sed -i 's|^GRUB_TIMEOUT_STYLE=.*|GRUB_TIMEOUT_STYLE=menu|' /etc/default/grub
    sed -i 's|^GRUB_TIMEOUT=.*|GRUB_TIMEOUT=5|' /etc/default/grub
    update-grub >/dev/null 2>&1
    echo "  GRUB_DEFAULT -> $DEF"
    echo "  menu de arranque VISIBLE 5s (escotilla si $KOBJ no arranca)"
  fi
else
  echo "  [dry-run] pondria GRUB_DEFAULT en la entrada de $KOBJ y el menu a 5s"
fi

echo
echo "  NINGUNA DE LAS DOS ESTA ACTIVA HASTA QUE REINICIES."
echo "  Despues, comprueba las dos:"
echo "    uname -r                                                  # espera $KOBJ"
echo "    cat /sys/module/nvidia_uvm/parameters/uvm_global_oversubscription  # espera 0"
echo "  Y si vuelve a congelarse, la firma a buscar es:"
echo "    journalctl -k -b -1 | grep -c _memdescAllocInternal"

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
