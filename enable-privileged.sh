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
# el dueno de la sesion grafica: quien invoco el sudo, no root
DUENO="${SUDO_USER:-$(logname 2>/dev/null || id -un)}"
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
  if [ -f /etc/systemd/system/docker.slice.d/99-blackbox.conf ]; then
    run rm -f /etc/systemd/system/docker.slice.d/99-blackbox.conf
    run rmdir --ignore-fail-on-non-empty /etc/systemd/system/docker.slice.d
    echo "  techo de docker.slice retirado"
  fi
  if [ -f /etc/systemd/system/system.slice.d/99-blackbox.conf ]; then
    run rm -f /etc/systemd/system/system.slice.d/99-blackbox.conf
    run rmdir --ignore-fail-on-non-empty /etc/systemd/system/system.slice.d
    echo "  techo de system.slice retirado -- REQUIERE: systemctl daemon-reload"
  fi
  if [ -f "$BACKUP/docker-daemon.json" ]; then
    run cp "$BACKUP/docker-daemon.json" /etc/docker/daemon.json
    echo "  /etc/docker/daemon.json restaurado -- REQUIERE: systemctl restart docker"
    echo "  (no se reinicia solo: tirar los contenedores es decision tuya)"
  else
    echo "  /etc/docker/daemon.json: sin copia previa, NO se toca"
  fi
  if [ -f "$BACKUP/linger-estaba" ]; then
    if [ "$(cat "$BACKUP/linger-estaba")" = "no" ]; then
      run loginctl disable-linger "$DUENO"
      echo "  linger de $DUENO devuelto a 'no' (como estaba antes)"
    else
      echo "  linger de $DUENO ya estaba activo antes: NO se toca"
    fi
  else
    echo "  linger: sin copia previa, NO se toca"
  fi
  if [ -f /etc/sysctl.d/99-blackbox-panic.conf ]; then
    run rm -f /etc/sysctl.d/99-blackbox-panic.conf
    run sysctl -q -w kernel.panic=0
    echo "  kernel.panic devuelto a 0 (el kernel vuelve a colgarse en un panic)"
  fi
  if [ -f /etc/systemd/system/user.slice.d/99-blackbox-escritorio.conf ]; then
    run rm -f /etc/systemd/system/user.slice.d/99-blackbox-escritorio.conf \
              /etc/systemd/system/user-.slice.d/99-blackbox-escritorio.conf \
              /etc/systemd/system/session-.scope.d/99-blackbox-escritorio.conf \
              "/etc/systemd/system/user@.service.d/99-blackbox-escritorio.conf"
    run rmdir --ignore-fail-on-non-empty /etc/systemd/system/user.slice.d \
              /etc/systemd/system/user-.slice.d \
              /etc/systemd/system/session-.scope.d \
              /etc/systemd/system/user@.service.d
    DESK_BASE_REV="$(getent passwd "$DUENO" | cut -d: -f6)/.config/systemd/user"
    for sub in session.slice.d app.slice.d app-gnome-.scope.d \
               snap.antigravity.antigravity-.scope.d; do
      run rm -f "$DESK_BASE_REV/$sub/99-blackbox-escritorio.conf"
      run rmdir --ignore-fail-on-non-empty "$DESK_BASE_REV/$sub"
    done
    echo "  proteccion de memoria del escritorio retirada (vuelve a memory.low=0"
    echo "  en toda la cadena: el reclamo deja de distinguir tu ventana de un arnes)"
  fi
  if [ -f /etc/systemd/system/sysstat-collect.timer.d/override.conf ]; then
    run rm -f /etc/systemd/system/sysstat-collect.timer.d/override.conf
    run rmdir --ignore-fail-on-non-empty /etc/systemd/system/sysstat-collect.timer.d
    echo "  drop-in de sysstat-collect retirado (con ENABLED=false, sar deja de recolectar)"
  fi
  if [ -f /etc/systemd/system/atom-clock-lock.service ]; then
    run systemctl disable atom-clock-lock.service
    run rm -f /etc/systemd/system/atom-clock-lock.service
    echo "  atom-clock-lock retirado (el clock de la GPU vuelve a arrancar sin tope)"
  fi
  if [ -f /etc/systemd/system/nvrm-watch.timer ]; then
    run systemctl disable --now nvrm-watch.timer
    run rm -f /etc/systemd/system/nvrm-watch.timer \
              /etc/systemd/system/nvrm-watch.service \
              /usr/local/bin/nvrm-watch.sh
    echo "  nvrm-watch retirado (el precursor NVRM OOM deja de vigilarse)"
  fi
  if [ -f /etc/systemd/system/earlyoom.service.d/override.conf ]; then
    run rm -f /etc/systemd/system/earlyoom.service.d/override.conf
    run rmdir --ignore-fail-on-non-empty /etc/systemd/system/earlyoom.service.d
    echo "  drop-in de earlyoom retirado (vuelve a ser matable antes que sus victimas)"
  fi
  if [ -f /etc/sysctl.d/99-nvidia-unified-memory.conf ]; then
    run rm -f /etc/sysctl.d/99-nvidia-unified-memory.conf
    echo "  afinado de memoria unificada retirado -- los valores EN CALIENTE siguen"
    echo "  puestos hasta el proximo arranque"
  fi
  if [ -f /etc/sysctl.d/99-freeze-panic.conf ]; then
    run rm -f /etc/sysctl.d/99-freeze-panic.conf
    echo "  99-freeze-panic retirado: hung_task, softlockup y hardlockup dejan de"
    echo "  entrar en panic tras el proximo arranque (en caliente siguen armados)"
  fi
  if [ -f /etc/sysctl.d/99-sysrq.conf ]; then
    run rm -f /etc/sysctl.d/99-sysrq.conf
    echo "  99-sysrq retirado (Alt+SysRq deja de responder tras reiniciar)"
  fi
  DESK_BASE_TECHO="$(getent passwd "$DUENO" | cut -d: -f6)/.config/systemd/user"
  if [ -f "$DESK_BASE_TECHO/app.slice.d/99-blackbox.conf" ]; then
    run rm -f "$DESK_BASE_TECHO/app.slice.d/99-blackbox.conf"
    run rmdir --ignore-fail-on-non-empty "$DESK_BASE_TECHO/app.slice.d"
    echo "  techo de app.slice retirado -- REQUIERE: systemctl --user daemon-reload"
    echo "  (vuelve a MemoryMax=infinity: nada limita las sesiones de agente)"
  fi
  if [ -f /etc/systemd/system.conf.d/99-blackbox-watchdog.conf ]; then
    run rm -f /etc/systemd/system.conf.d/99-blackbox-watchdog.conf
    run rmdir --ignore-fail-on-non-empty /etc/systemd/system.conf.d
    echo "  drop-in del watchdog de hardware retirado (system.conf:34 sigue en pie)"
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
# El drop-in que hace que recolecte cada minuto SI es de este repo, y hasta el
# 2026-09-28 vivia solo en la maquina y en `adopted/`: un clon no tenia con que
# reponerlo. Es el que sostiene la frase de arriba -- "dispara la recoleccion
# cada minuto igualmente" --, asi que sin el gana ENABLED="false" y sar se
# queda sin datos.
run mkdir -p /etc/systemd/system/sysstat-collect.timer.d
run cp adopted/system-config/etc_systemd_system_sysstat-collect.timer.d_override.conf \
       /etc/systemd/system/sysstat-collect.timer.d/override.conf
echo "  drop-in de sysstat-collect puesto (OnCalendar=*:00/01, precision 1 s)"

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

# --- 4b. los vigilantes de la GPU que solo vivian en la maquina -----------
# Los tres ficheros de este bloque se adoptaron el 2026-09-24 y hasta el
# 2026-09-28 ningun script los instalaba: eran un retrato. `bb drift` los
# comparaba igual, o sea que podia reportar una divergencia cuyo remedio no
# existia en el repo.
echo
echo "-- 4b. clock de la GPU y vigilante de NVRM OOM --"
# `atom-clock-lock` fija -lgc 300,2800 en cada arranque para evitar los
# transitorios de boost que confluyen con el limite termico (DGX-342/344/345).
run cp adopted/system-config/etc_systemd_system_atom-clock-lock.service \
       /etc/systemd/system/atom-clock-lock.service
# `nvrm-watch` mira el journal del kernel cada 5 min buscando
# "NVRM: ... Out of memory", una señal asociada a algunos reportes de NVIDIA
# #1358. Puede aparecer sin cuelgue, y hay cuelgues sin esa señal; se registra
# como evidencia y no como predictor suficiente.
run cp adopted/system-config/usr_local_bin_nvrm-watch.sh /usr/local/bin/nvrm-watch.sh
run chmod 0755 /usr/local/bin/nvrm-watch.sh
run cp adopted/system-config/etc_systemd_system_nvrm-watch.service \
       /etc/systemd/system/nvrm-watch.service
run cp adopted/system-config/etc_systemd_system_nvrm-watch.timer \
       /etc/systemd/system/nvrm-watch.timer
run systemctl daemon-reload
run systemctl enable atom-clock-lock.service
run systemctl enable --now nvrm-watch.timer
echo "  atom-clock-lock armado (oneshot tras nvidia-persistenced)"
echo "  nvrm-watch armado (cada 5 min, 2 min tras el arranque)"
echo
echo "  CONTROL NEGATIVO -- mira el sujeto, no este informe:"
echo "    systemctl is-enabled atom-clock-lock.service   # espera: enabled"
echo "    systemctl is-active nvrm-watch.timer           # espera: active"
echo "    nvidia-smi -q -d CLOCK | grep -A1 'Applications Clocks'"

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
    # DEBT-EARLYOOM-DESARMADO-POR-EL-AND-DEL-SWAP, medido 2026-09-28: el
    # gatillo de earlyoom es un AND memoria+swap ("both memory and swap must
    # be below minimum"). MemAvailable llego a 0.19 % ese dia y earlyoom NO
    # disparo -- el swap seguia al 65 % libre, muy por encima del umbral de
    # `-s 10`. `-s 100,100` abre las dos compuertas (mem y swap por
    # separado) sin tocar la punteria de arriba: con las dos abiertas la
    # victima seria VLLM::EngineCor (oom_score 1026), no claude-desktop
    # (866, y --avoid lo baja mas). `-s 100` a secas NO basta: deja el
    # SIGKILL en "swap <= 50 %", y el swap estaba al 65 %.
    sed -i "s/-s 10\b/-s 100,100/" /etc/default/earlyoom
    systemctl restart earlyoom.service
    echo "  --prefer ahora: $(grep -o "\-\-prefer '[^']*'" /etc/default/earlyoom)"
    echo "  -s ahora: $(grep -oE '\-s [0-9,]+' /etc/default/earlyoom)"
  else
    echo "  [dry-run] quitaria vllm de --prefer y anadiria pytest"
    echo "  [dry-run] cambiaria -s 10 a -s 100,100 (AND memoria+swap, DEBT-EARLYOOM-DESARMADO-POR-EL-AND-DEL-SWAP)"
  fi
  # El drop-in que le da CAP_KILL y lo saca de la mira del OOM killer tambien
  # era solo-maquina hasta el 2026-09-28. Sin el, el vigilante es matable antes
  # que sus victimas, que es lo mismo que no tenerlo.
  run mkdir -p /etc/systemd/system/earlyoom.service.d
  run cp adopted/system-config/etc_systemd_system_earlyoom.service.d_override.conf \
         /etc/systemd/system/earlyoom.service.d/override.conf
  run systemctl daemon-reload
  run systemctl restart earlyoom.service
  echo "  drop-in puesto: OOMScoreAdjust=-1000, CAP_IPC_LOCK/SYS_NICE/KILL"
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
# Mitigacion parcial, no causa raíz demostrada. Un reportero del hilo lo puso
# a 0 y observó que un cuelgue silencioso pasó a OOM global recuperable; otros
# resultados muestran que no evita todos los fallos: hashcat produjo OOM
# recuperable y el prefill siguió colgándose con el parámetro en 0. El OOM
# global todavía puede matar procesos ajenos (sshd, NetworkManager,
# contenedores); el valor no garantiza que el host sobreviva.
# El contenido sale de `adopted/`, no de aqui dentro. Hasta el 2026-09-28 este
# bloque lo escribia con un heredoc IDENTICO al fichero adoptado: dos fuentes
# de verdad para los mismos cuatro renglones, y `bb drift` vigilando justo la
# copia que el script NO usaba. Verificado byte a byte antes de cambiarlo --
# `diff` del heredoc contra el adoptado dio 0, y 1 contra otro fichero.
run cp adopted/system-config/etc_modprobe.d_99-blackbox-uvm.conf \
       /etc/modprobe.d/99-blackbox-uvm.conf
echo "  /etc/modprobe.d/99-blackbox-uvm.conf escrito desde adopted/"
echo "  valor EN CALIENTE (no cambia hasta recargar el modulo o reiniciar):"
echo "    $(cat /sys/module/nvidia_uvm/parameters/uvm_global_oversubscription 2>/dev/null || echo '?')"

# --- 8c. afinado de memoria del kernel para memoria unificada -------------
# vm.min_free_kbytes = 1 GiB (reserva atomica de emergencia),
# vfs_cache_pressure = 150 (desaloja page cache antes de fragmentar el espacio
# contiguo que pide la GPU) y swappiness = 15. La cabecera del fichero cita
# `knowledge/hardware/ai_top_atom_unified_memory_oom_mitigation.md`, que NO
# esta en este repo -- la referencia queda como esta, sin fingir que se puede
# abrir desde aqui. Los tres valores estan en la maquina desde antes de
# adoptarlo; lo que faltaba era poder reponerlos.
run cp adopted/system-config/etc_sysctl.d_99-nvidia-unified-memory.conf \
       /etc/sysctl.d/99-nvidia-unified-memory.conf
run sysctl -q -p /etc/sysctl.d/99-nvidia-unified-memory.conf
echo "  afinado puesto. CONTROL NEGATIVO, sobre el sujeto:"
echo "    sysctl -n vm.min_free_kbytes vm.vfs_cache_pressure vm.swappiness"
echo "      espera: 1048576 / 150 / 15"

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

# --- 9. techo de memoria para los contenedores ---------------------------
echo
echo "-- 9. techo agregado de Docker (DEBT-DOCKER-FUERA-DEL-TECHO) --"
if [ ! -S /var/run/docker.sock ] && ! command -v docker >/dev/null 2>&1; then
  echo "  docker no esta en esta maquina: nada que acotar"
else
  echo "  Medido el 2026-09-24: los contenedores cuelgan de"
  echo "  system.slice/docker-<id>.scope, hermanos del demonio -- un drop-in"
  echo "  sobre docker.service NO los toca. Y 3 de 5 no tenian techo propio."

  if [ -f /etc/docker/daemon.json ]; then
    run cp -n /etc/docker/daemon.json "$BACKUP/docker-daemon.json"
  fi
  # se MEZCLA, no se sobrescribe: daemon.json ya declara el runtime de nvidia
  if [ "$DRY" = 1 ]; then
    echo "  [dry-run] anadir \"cgroup-parent\": \"docker.slice\" a /etc/docker/daemon.json"
  else
    python3 - <<'PYEOF'
import json, pathlib
p = pathlib.Path("/etc/docker/daemon.json")
d = json.loads(p.read_text(encoding="utf-8")) if p.exists() and p.read_text(encoding="utf-8").strip() else {}
if d.get("cgroup-parent") == "docker.slice":
    print("  daemon.json ya apunta a docker.slice, sin cambios")
else:
    d["cgroup-parent"] = "docker.slice"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=4) + "\n", encoding="utf-8")
    print("  daemon.json: cgroup-parent = docker.slice (el resto se conservo)")
PYEOF
  fi

  run mkdir -p /etc/systemd/system/docker.slice.d
  run cp adopted/system-config/etc_systemd_system_docker.slice.d_99-blackbox.conf \
         /etc/systemd/system/docker.slice.d/99-blackbox.conf
  echo "  techo puesto: MemoryMax=14G, MemorySwapMax=4G sobre docker.slice"
  echo
  echo "  NO SURTE EFECTO HASTA REINICIAR EL DEMONIO, y eso TIRA los"
  echo "  contenedores -- incluido el vLLM. Cuando te venga bien:"
  echo "    sudo systemctl daemon-reload && sudo systemctl restart docker"
  echo
  echo "  CONTROL NEGATIVO -- despues del reinicio, comprueba el SUJETO, no el informe:"
  echo "    cat /proc/\$(docker inspect -f '{{.State.Pid}}' nemotron-server)/cgroup"
  echo "      espera:  0::/docker.slice/docker-<id>.scope    (NO system.slice)"
  echo "    cat /sys/fs/cgroup/docker.slice/memory.max"
  echo "      espera:  15032385536                          (NO 'max')"
  echo "    Si sigue diciendo system.slice o 'max', el techo NO esta puesto"
  echo "    por mucho que este informe diga que si."
fi

# --- Techo de system.slice (DEBT-TECHOS-SIN-CALIBRAR, voto de Luis 2026-09-27)
#
# Sin el, `system.slice` entraba en el presupuesto por lo que USABA y no por lo
# que prometia, y los compromisos sumaban 121.8 GiB sobre 121.1 disponibles.
run mkdir -p /etc/systemd/system/system.slice.d
run cp adopted/system-config/etc_systemd_system_system.slice.d_99-blackbox.conf \
       /etc/systemd/system/system.slice.d/99-blackbox.conf
echo "  techo puesto: MemoryMax=12G sobre system.slice (pico medido 10.8)"
echo
echo "  NO SURTE EFECTO HASTA:  sudo systemctl daemon-reload"
echo "  (no reinicia nada: system.slice ya existe, solo se le aplica el limite)"
echo
echo "  CONTROL NEGATIVO -- comprueba el SUJETO, no este informe:"
echo "    cat /sys/fs/cgroup/system.slice/memory.max"
echo "      espera:  12884901888                          (NO 'max')"
echo "    Si dice 'max', el techo NO esta puesto por mucho que esto diga que si."

# --- 10. los servicios del usuario arrancan sin login --------------------
echo
echo "-- 10. linger: que un reinicio automatico no deje el stack caido --"
echo "  Medido en el arranque del 2026-09-24 14:11:31 -- user@1000.service y"
echo "  ai-nemotron.service arrancaron LOS DOS a las 18:33:07, cuando el dueno"
echo "  entro al escritorio: 4 h 21 min 36 s sin stack de inferencia. Con"
echo "  Linger=no y sin autologin en GDM, una unidad de usuario 'enabled' no"
echo "  arranca en el boot: espera a una sesion."
echo "  bb-usable lleva FailureAction=reboot-immediate, asi que un rescate"
echo "  automatico de madrugada cuesta exactamente esa brecha."
LINGER_ANTES=$(loginctl show-user "$DUENO" -p Linger --value 2>/dev/null || echo "?")
if [ ! -f "$BACKUP/linger-estaba" ]; then
  run sh -c "printf '%s' '$LINGER_ANTES' > '$BACKUP/linger-estaba'"
fi
if [ "$LINGER_ANTES" = "yes" ]; then
  echo "  linger de $DUENO ya estaba activo: nada que hacer"
else
  run loginctl enable-linger "$DUENO"
  echo "  linger activado para $DUENO (antes: $LINGER_ANTES)"
  echo
  echo "  ALCANCE: arrancan TODAS sus unidades 'enabled', no solo el vLLM --"
  echo "  tambien pipewire, gnome-keyring y tracker, sin sesion grafica. Es"
  echo "  ruido, no dano. Y el vLLM vuelve a pedir 68 GB nada mas arrancar: su"
  echo "  propio admission_check es lo unico que lo frena."
  echo
  echo "  CONTROL NEGATIVO -- no te fies de este informe, mira el sujeto:"
  echo "    loginctl show-user $DUENO -p Linger        # espera Linger=yes"
  echo "    ls /var/lib/systemd/linger/$DUENO          # el fichero tiene que existir"
  echo "  Y la prueba de verdad es el proximo arranque:"
  echo "    systemd-analyze --user blame | head        # tras bootear SIN entrar"
  echo "    journalctl -b -u user@\$(id -u $DUENO).service | head -1"
  echo "    Si su marca de tiempo va pegada al boot y no a tu login, funciono."
fi

# --- 11. que un panic reinicie, en vez de colgarse ----------------------
echo
echo "-- 11. kernel.panic: la ultima capa, por debajo de bb-usable --"
PANIC_ANTES=$(sysctl -n kernel.panic 2>/dev/null || echo "?")
echo "  /etc/sysctl.d/99-freeze-panic.conf (2026-09-09, NO es de este repo: sale"
echo "  del hilo del foro de NVIDIA #358951) obliga al kernel a entrar en panic"
echo "  ante hung_task 120s, softlockup y hardlockup. Su proposito alli era"
echo "  DIAGNOSTICO -- panic + kdump para capturar -- no recuperacion."
echo "  kdump SI esta armado aqui (ready to kdump, kexec_crash_loaded=1,"
echo "  crashkernel=1G-:512M), asi que un panic ya reinicia por kexec."
echo "  Lo que kernel.panic=$PANIC_ANTES deja sin cubrir es el caso en que kdump FALLA:"
echo "  si __crash_kexec() no arranca el kernel de captura, panic() honra"
echo "  panic_timeout, y con 0 se queda parada para siempre."
# El fichero del que habla el parrafo de arriba tambien se instala desde aqui
# desde el 2026-09-28. No es de este repo -- sale del hilo del foro-- pero
# estaba adoptado sin que nada pudiera reponerlo, y es la mitad de la que
# depende la otra: sin `99-freeze-panic` no hay panic que `kernel.panic` pueda
# temporizar. Ordenacion comprobada: "99-blackbox-panic" va ANTES que
# "99-freeze-panic" y no hay clave compartida, asi que el orden no decide nada.
run cp adopted/system-config/etc_sysctl.d_99-freeze-panic.conf \
       /etc/sysctl.d/99-freeze-panic.conf
run sysctl -q -p /etc/sysctl.d/99-freeze-panic.conf
# Y el SysRq, que es la unica via de recuperacion manual cuando el escritorio
# ya no responde pero el kernel todavia lee el teclado.
run cp adopted/system-config/etc_sysctl.d_99-sysrq.conf /etc/sysctl.d/99-sysrq.conf
run sysctl -q -p /etc/sysctl.d/99-sysrq.conf
run cp adopted/system-config/etc_sysctl.d_99-blackbox-panic.conf \
       /etc/sysctl.d/99-blackbox-panic.conf
run sysctl -q -p /etc/sysctl.d/99-blackbox-panic.conf
echo "  kernel.panic: $PANIC_ANTES -> 10 (reinicia 10 s si kdump no pudo)"
echo
echo "  CONTROL NEGATIVO -- mira el sujeto, no este informe:"
echo "    sysctl -n kernel.panic          # espera 10, no 0"
echo "  Y comprueba que el watchdog de hardware sigue alimentado:"
echo "    journalctl -b 0 | grep -i 'hardware watchdog'"
echo "    espera: Using hardware watchdog 'SBSA Generic Watchdog' ... /dev/watchdog0"
echo "    OJO: /sys/class/watchdog/watchdog0/timeleft NO sirve de instrumento"
echo "    en esta maquina -- reporta ~40 anos. El journal es lo que vale."

# --- 12. el watchdog de hardware, a prueba de actualizaciones -----------
echo
echo "-- 12. watchdog SBSA: que sobreviva a una actualizacion de systemd --"
echo "  Medido el 2026-09-24: RuntimeWatchdogSec=60 vive en"
echo "  /etc/systemd/system.conf:34, editado a mano. El paquete systemd"
echo "  REESCRIBE ese fichero al actualizar, asi que la ultima capa de"
echo "  proteccion desapareceria en silencio hasta el siguiente cuelgue."
run mkdir -p /etc/systemd/system.conf.d
run cp adopted/system-config/etc_systemd_system.conf.d_99-blackbox-watchdog.conf \
       /etc/systemd/system.conf.d/99-blackbox-watchdog.conf
echo "  drop-in puesto (mismo valor que ya hay: 60 s, sin cambio de conducta)"
echo
echo "  CONTROL NEGATIVO -- el journal es lo unico que prueba que esta armado:"
echo "    journalctl -b 0 | grep -i 'hardware watchdog'"
echo "    espera: Using hardware watchdog 'SBSA Generic Watchdog' ... /dev/watchdog0"
echo "    NO uses /sys/class/watchdog/watchdog0/timeleft: en esta maquina"
echo "    reporta ~40 anos, o sea no distingue alimentado de no alimentado."

# --- 13. proteger la memoria del escritorio del reclamo -------------------
echo
echo "-- 13. memory.low: que el reclamo se lleve los arneses, no tu ventana --"
echo "  Medido el 2026-09-25, la manana del reinicio por 'casi no se podia"
echo "  escribir': memory.low = 0 y memory.min = 0 en user.slice, en app.slice"
echo "  y en session.slice. NADA estaba protegido del reclamo. La ventana en la"
echo "  que escribes y el arnes que se come la memoria son hermanos sin"
echo "  ninguna prioridad relativa."
echo "  Esa noche el swap paso de 16383 MiB libres a 12067: 4.3 GB expulsados y"
echo "  nunca recuperados, con el 53 % de la RAM libre."
echo
echo "  NO es un problema de CPU, y eso se DESCARTO con experimento: una rampa"
echo "  de carga midiendo el ida y vuelta al servidor X dio 4 ms en reposo y"
echo "  8 ms con 40 quemadores sobre 20 nucleos. Dar prioridad de CPU al"
echo "  escritorio habria sido la respuesta obvia y habria sido inutil."
run mkdir -p /etc/systemd/system/user.slice.d \
             /etc/systemd/system/user-.slice.d \
             /etc/systemd/system/session-.scope.d \
             /etc/systemd/system/user@.service.d
run cp adopted/system-config/etc_systemd_system_user.slice.d_99-blackbox-escritorio.conf \
       /etc/systemd/system/user.slice.d/99-blackbox-escritorio.conf
run cp adopted/system-config/etc_systemd_system_user-.slice.d_99-blackbox-escritorio.conf \
       /etc/systemd/system/user-.slice.d/99-blackbox-escritorio.conf
run cp adopted/system-config/etc_systemd_system_session-.scope.d_99-blackbox-escritorio.conf \
       /etc/systemd/system/session-.scope.d/99-blackbox-escritorio.conf
run cp "adopted/system-config/etc_systemd_system_user@.service.d_99-blackbox-escritorio.conf" \
       "/etc/systemd/system/user@.service.d/99-blackbox-escritorio.conf"
# El cuarto nivel es un slice del GESTOR DE USUARIO: su sitio canonico es el
# drop-in de usuario, igual que el techo de app.slice que ya vive ahi. Se
# instala con la propiedad de $DUENO, no de root, o su propio systemd no lo lee.
DESK_BASE="$(getent passwd "$DUENO" | cut -d: -f6)/.config/systemd/user"
# Los tres ultimos niveles son unidades del GESTOR DE USUARIO: su sitio canonico
# es el drop-in de usuario, igual que el techo de app.slice que ya vive ahi.
for par in \
  "session.slice.d:home_lcasarin_.config_systemd_user_session.slice.d_99-blackbox-escritorio.conf" \
  "app.slice.d:home_lcasarin_.config_systemd_user_app.slice.d_99-blackbox-escritorio.conf" \
  "app-gnome-.scope.d:home_lcasarin_.config_systemd_user_app-gnome-.scope.d_99-blackbox-escritorio.conf" \
  "snap.antigravity.antigravity-.scope.d:home_lcasarin_.config_systemd_user_snap.antigravity.antigravity-.scope.d_99-blackbox-escritorio.conf"
do
  run mkdir -p "$DESK_BASE/${par%%:*}"
  run cp "adopted/system-config/${par#*:}" "$DESK_BASE/${par%%:*}/99-blackbox-escritorio.conf"
done
# El TECHO de app.slice (MemoryMax=42G) es otro fichero y otra cosa que la
# proteccion de arriba: aquel reparte prioridad de reclamo, este pone el limite
# duro. Vive en el mismo sitio y por eso se instala aqui.
#
# ESTE ES EL FICHERO QUE COSTO LA FICHA. El 2026-09-28 se voto bajarlo de 48G a
# 42G, se edito dentro de `adopted/` y se corrio `sudo ./enable-privileged.sh`
# DOS VECES sin que el techo se moviera, porque ningun script lo copiaba.
# Docker bajo a 14 y system entro en 12, asi que los compromisos pasaron de
# 121.8 GiB sobre 121.1 a 124.1 sobre 121.1: el estado intermedio quedo PEOR
# que el de partida, y desde el repo no habia forma de verlo. Se cerro
# copiandolo a mano, fuera de todo script.
run mkdir -p "$DESK_BASE/app.slice.d"
run cp adopted/system-config/home_lcasarin_.config_systemd_user_app.slice.d_99-blackbox.conf \
       "$DESK_BASE/app.slice.d/99-blackbox.conf"
run chown -R "$DUENO": "$DESK_BASE"
echo "  techo de app.slice puesto: MemoryMax=42G"
echo "  NO SURTE EFECTO HASTA:  systemctl --user daemon-reload   (como $DUENO,"
echo "  no como root: es el gestor de usuario quien lo lee)"
echo "  CONTROL NEGATIVO -- sobre el cgroup, no sobre este informe:"
echo "    cat /sys/fs/cgroup/user.slice/user-\$(id -u $DUENO).slice/user@\$(id -u $DUENO).service/app.slice/memory.max"
echo "      espera:  45097156608                            (NO 51539607552 ni 'max')"
echo "  OJO con la ruta: /sys/fs/cgroup/app.slice NO existe -- app.slice es del"
echo "  gestor de usuario y cuelga de user@<uid>.service. Medirlo en la ruta"
echo "  equivocada el 2026-09-28 casi hizo registrar 'app.slice sin techo'."
echo
echo "  siete niveles puestos:"
echo "    user.slice 8G . user-<uid>.slice 8G . session-<N>.scope 2G (Xorg)"
echo "    user@.service 6G . session.slice 2G (gnome-shell, dbus, pipewire)"
echo "    app.slice 4G  -- no se protege a si mismo: PASA la proteccion abajo"
echo "    app-gnome-<lo que sea>.scope 2G       <- LA VENTANA donde escribes"
echo "    snap.antigravity.antigravity-<uuid>.scope 2G"
echo
echo "  COMO DISCRIMINA, que es lo unico que hace que esto sirva: dentro de"
echo "  app.slice la proteccion va a los hijos que la PIDEN. La piden los"
echo "  scopes de ventana; NO la pide el scope del arnes"
echo "  (app-com.anthropic.Claude-<pid>.scope), medido hoy en 19.74 GB"
echo "  actuales y 22.70 GB de pico contra 1.29 GB de la ventana. El arnes"
echo "  queda entero reclamable sin tener que nombrarlo."
echo
echo "  ALCANCE, declarado: el prefijo de antigravity esta DERIVADO del journal"
echo "  del 2026-09-25, no verificado sobre una unit viva. Comprueba con"
echo "  'systemctl --user show <scope> -p MemoryLow -p DropInPaths' la proxima"
echo "  vez que lo abras. El mecanismo SI esta verificado, sobre el scope de la"
echo "  ventana de Claude: MemoryLow=3221225472 aplicado por prefijo."
echo
echo "  CONTROL NEGATIVO -- no te fies de este informe, mira los cgroups:"
echo "    cat /sys/fs/cgroup/user.slice/memory.low                  # espera 6442450944"
echo "    cat /sys/fs/cgroup/user.slice/user-1000.slice/session-*.scope/memory.low"
echo "    cat /sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/session.slice/memory.low"
echo "    Un 0 en cualquiera de esos rompe la cadena entera: en cgroup v2 la"
echo "    proteccion de un hijo esta acotada por la del padre."
echo "    Y 'bb status' lo comprueba solo, por el DATO y no por el fichero."
echo
echo "  El nivel de usuario necesita que SU systemd recargue:"
echo "    systemctl --user daemon-reload"
echo "  Los niveles de /etc necesitan que la sesion grafica se reinicie para"
echo "  que session-<N>.scope nazca con el drop-in: vale un logout, no un boot."

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
