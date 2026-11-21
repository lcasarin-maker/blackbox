#!/bin/bash
set -eu
repo=$(git rev-parse --show-toplevel)
base=c3e3e23b3b531ad45daad2f21ebb709a6c1ebd82
git merge-base --is-ancestor "$base" HEAD
git diff --quiet "$base" -- bin/bb-vigilante-motor tools/motor_solicitudes.py tools/workload_restart_policy.py adopted/systemd-user/ai-nemotron-vigilante.service adopted/systemd-user/ai-nemotron-vigilante.timer
printf 'base=%s head=%s\n' "$base" "$(git rev-parse HEAD)"
sha256sum "$repo/tasks/evidence/BB-RUST-MOTOR-PARIDAD-01/ejecucion/ejecutar.sh" "$repo/tasks/evidence/BB-RUST-MOTOR-PARIDAD-01/ejecucion/medir.py"
work=$(mktemp -d "$HOME/scratch/blackbox/2026-11-21-motor-XXXXXX")
mkdir -p "$work/bin" "$work/data"
cat > "$work/bin/python3" <<'EOF'
#!/bin/sh
exec /usr/bin/python3 -B -I "$@"
EOF
cat > "$work/bin/awk" <<'EOF'
#!/bin/sh
exec /usr/bin/gawk "$@"
EOF
cat > "$work/bin/systemctl" <<'EOF'
#!/bin/sh
printf 'systemctl %s\n' "$*" >> /work/effects.log
case "$*" in
 *ExecMainStartTimestamp*) echo '2020-01-01 00:00:00 UTC';;
 *ActiveState*) echo active;;
esac
EOF
cat > "$work/bin/curl" <<'EOF'
#!/bin/sh
printf 'curl %s\n' "$*" >> /work/effects.log
case "$*" in *chat/completions*) [ -z "${FAKE_DELAY:-}" ] || sleep "$FAKE_DELAY"; printf '%s' "${FAKE_CHAT:-200}";; esac
EOF
cat > "$work/bin/notify-send" <<'EOF'
#!/bin/sh
printf 'notify %s\n' "$*" >> /work/effects.log
EOF
cat > "$work/bin/snapshot" <<'EOF'
#!/bin/sh
printf 'snapshot %s\n' "$*" >> /work/effects.log
EOF
chmod 755 "$work/bin/"*
printf 'work=%s\n' "$work"
printf 'command: bwrap --unshare-user --unshare-pid --unshare-net --unshare-ipc --ro-bind /usr /usr --symlink usr/lib /lib --symlink usr/bin /bin --proc /proc --dev /dev --tmpfs /tmp --ro-bind %q /repo --bind %q /work --chdir /work /usr/bin/python3 -B -I /repo/tasks/evidence/BB-RUST-MOTOR-PARIDAD-01/ejecucion/medir.py' "$repo" "$work"
if [ "$#" -gt 0 ]; then printf ' %q' "$@"; fi
printf '\n'
bwrap --unshare-user --unshare-pid --unshare-net --unshare-ipc --ro-bind /usr /usr --symlink usr/lib /lib --symlink usr/bin /bin --proc /proc --dev /dev --tmpfs /tmp --ro-bind "$repo" /repo --bind "$work" /work --chdir /work /usr/bin/python3 -B -I /repo/tasks/evidence/BB-RUST-MOTOR-PARIDAD-01/ejecucion/medir.py "$@"
