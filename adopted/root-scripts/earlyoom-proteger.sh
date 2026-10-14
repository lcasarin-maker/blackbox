#!/usr/bin/env bash
# bb-root-run earlyoom-proteger -- cambia /etc/default/earlyoom para que earlyoom deje de elegir al motor vLLM.
# Escribe: /etc/default/earlyoom (root:root 0644, por temporal .earlyoom.XXXXXX en /etc/default y mv), y UNA copia
#      del fichero viejo en /var/lib/blackbox/etc_default_earlyoom.<sha256 viejo> (root:root 0644). Si earlyoom no
#      queda activo tras el reinicio, devuelve esa copia a su sitio. Nada mas.
# Ejecuta: earlyoom --dryrun con los argumentos nuevos (no mata nada) para validar las regex antes de escribir;
#      `systemctl restart earlyoom`, `systemctl is-active earlyoom` y `journalctl -u earlyoom -n 5`.
# Por que: earlyoom mando SIGTERM a 'VLLM::EngineCor' (el contenedor tiene oom_score_adj 500) porque --avoid no lo
#      nombraba; los umbrales (-r 60 -m 10 -s 100,100) no cambian.
# Desbloquea: DEBT-EARLYOOM-MATA-AL-MOTOR-VLLM-01.
# Guardas: el fichero actual debe ser byte a byte el conocido (sha256 abajo) o el nuevo (entonces no hace nada, rc 0);
#      ni el fichero, ni /etc/default, ni /var/lib/blackbox, ni la copia pueden ser symlink; /var/lib/blackbox debe ser
#      de root y no escribible por grupo ni otros; el temporal se comprueba contra el sha256 nuevo antes de moverlo.
# Sin red, sin argumentos.
set -euo pipefail
umask 022

conf=/etc/default/earlyoom
dir_conf=/etc/default
base=/var/lib/blackbox
sha_viejo=7e8a44b63203bbcab11613f82f32fbf565dbc789efe395b944965a5a2e3abcbc
sha_nuevo=89fe78dade9afa4d8df1e51627d119b145102c3a21dd140a0f4a44f8b4b13c8e
bak="$base/etc_default_earlyoom.$sha_viejo"
espera=3
tmp=
tmp2=
trap 'if [[ -n "$tmp" ]]; then rm -f -- "$tmp"; fi; if [[ -n "$tmp2" ]]; then rm -f -- "$tmp2"; fi' EXIT

for p in "$dir_conf" "$conf" "$base" "$bak"; do
  if [[ -L "$p" ]]; then
    echo "earlyoom-proteger: $p es un symlink; no se toca" >&2
    exit 3
  fi
done
if [[ ! -f "$conf" ]]; then
  echo "earlyoom-proteger: $conf no existe o no es un fichero regular" >&2
  exit 3
fi
actual="$(sha256sum < "$conf" | cut -d' ' -f1)"
if [[ "$actual" == "$sha_nuevo" ]]; then
  echo "earlyoom-proteger: $conf ya tiene el contenido nuevo; no se toca"
  systemctl is-active earlyoom || true
  exit 0
fi
if [[ "$actual" != "$sha_viejo" ]]; then
  echo "earlyoom-proteger: $conf tiene sha256 $actual, ni el conocido ($sha_viejo) ni el nuevo; no se toca" >&2
  exit 3
fi

# Validacion: los mismos argumentos que EARLYOOM_ARGS (uno por linea; systemd quita las comillas simples), con
# --dryrun. Una regex que no compila hace salir a earlyoom al instante (rc 6); viva tras $espera s, timeout da 124.
mapfile -t args <<'ARGS'
-r
60
-m
10
-s
100,100
--avoid
(claude-desktop|pipewire|wireplumber|dbus-daemon|gnome-shell|gnome-session|Xorg|gdm|sshd|systemd|journal|xdg-|antigravity|vllm|VLLM|docker|containerd|^bb-)
--prefer
(pytest|xdist|triton|bb-portero)
ARGS
rc=0
timeout "$espera" earlyoom --dryrun "${args[@]}" > /dev/null 2> /dev/null || rc=$?
if [[ "$rc" != 124 ]]; then
  echo "earlyoom-proteger: earlyoom --dryrun con los argumentos nuevos salio $rc (se esperaba seguir vivo, 124); no se toca" >&2
  exit 4
fi

tmp="$(mktemp "$dir_conf/.earlyoom.XXXXXX")"
cat > "$tmp" <<'NUEVO'
# Configuración de DGX-201 (Atlas), 2026-08-21.
#
# Umbrales: los DEFAULT de earlyoom (SIGTERM 10%, SIGKILL 5%). No se copian los
# del hilo de NVIDIA (-m 3): en 121 GB serían 3.6 GB, y el default ya disparó
# tarde -- a 5.92% con el swap en cero.
#
# -r 60: un renglón por minuto en el journal. El default (-r 3600) deja una
# lectura por hora, y la curva de memoria es justo lo que hizo falta
# reconstruir a mano después de cada episodio.
#
# --avoid: el escritorio y la sesión. El 2026-08-21 earlyoom mató 21 procesos
# de claude-desktop y ninguno del consumidor real.
#
# 2026-10-14 (voto de Luis, DEBT-EARLYOOM-MATA-AL-MOTOR-VLLM-01): --avoid suma el
# motor vLLM ('vllm', 'VLLM::EngineCor'), docker, containerd y los procesos cuyo
# nombre empieza por bb-; --prefer suma xdist y bb-portero. earlyoom 1.7 compara la
# regex (POSIX extendida, sin anclar) contra /proc/<pid>/comm, 15 caracteres, y
# --avoid solo RESTA 300 al oom_score (--prefer suma 300): no es una exclusion.
# El contenedor vLLM tiene oom_score_adj 500; con badness 1038 quedaria en 738.
EARLYOOM_ARGS="-r 60 -m 10 -s 100,100 --avoid '(claude-desktop|pipewire|wireplumber|dbus-daemon|gnome-shell|gnome-session|Xorg|gdm|sshd|systemd|journal|xdg-|antigravity|vllm|VLLM|docker|containerd|^bb-)' --prefer '(pytest|xdist|triton|bb-portero)'"
NUEVO
if [[ "$(sha256sum < "$tmp" | cut -d' ' -f1)" != "$sha_nuevo" ]]; then
  echo "earlyoom-proteger: el contenido generado no tiene el sha256 nuevo; no se toca" >&2
  exit 4
fi
chmod 0644 -- "$tmp"
chown root:root -- "$tmp"

# Copia del viejo ANTES de sustituir: /var/lib/blackbox se verifica, no se arregla.
if [[ -e "$base" ]]; then
  if [[ "$(stat -c '%u' -- "$base")" != "0" ]] || (( 8#$(stat -c '%a' -- "$base") & 8#022 )); then
    echo "earlyoom-proteger: $base no es de root o es escribible por grupo/otros" >&2
    exit 3
  fi
else
  install -d -m 0755 -o root -g root -- "$base"
fi
install -m 0644 -o root -g root -- "$conf" "$bak"
if [[ "$(sha256sum < "$bak" | cut -d' ' -f1)" != "$sha_viejo" ]]; then
  echo "earlyoom-proteger: la copia $bak no coincide con el original; no se toca" >&2
  exit 3
fi
mv -f -- "$tmp" "$conf"
tmp=
echo "== $conf: de $sha_viejo a $sha_nuevo (copia del viejo: $bak)"

systemctl restart earlyoom || true
sleep "$espera"
estado="$(systemctl is-active earlyoom || true)"
echo "== earlyoom tras el reinicio (is-active): $estado"
echo "== journalctl -u earlyoom -n 5"
journalctl -u earlyoom -n 5 --no-pager || true
if [[ "$estado" != active ]]; then
  echo "earlyoom-proteger: earlyoom no quedo activo; se restaura $bak" >&2
  tmp2="$(mktemp "$dir_conf/.earlyoom.XXXXXX")"
  install -m 0644 -o root -g root -- "$bak" "$tmp2"
  mv -f -- "$tmp2" "$conf"
  tmp2=
  systemctl restart earlyoom || true
  sleep "$espera"
  estado="$(systemctl is-active earlyoom || true)"
  echo "== earlyoom tras restaurar (is-active): $estado" >&2
  exit 5
fi
