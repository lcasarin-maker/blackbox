#!/usr/bin/env bash
# Two reviewed files only; backups preserve original ownership and modes.
set -euo pipefail
repo=/home/lcasarin/projects/blackbox
[ "$(id -u)" -eq 0 ] || { echo 'Run through sudo bash.' >&2; exit 2; }
cd "$repo"
sha256sum --check <<'HASHES'
50c7a17100a131e0d27be3c5b97a81855c65815e8d702d39b3a40e2768b3ead4  adopted/system-config/etc_modprobe.d_99-blackbox-uvm.conf
ff4e43c4009274f1c939de971535f1d3266da70fd3e2f5403488a25edbf9422f  adopted/system-config/usr_local_bin_nvrm-watch.sh
eec7f60614a254cf9fc900dfe5024bef4b64aec0b1e9fb9440913b661f929dc9  /etc/modprobe.d/99-blackbox-uvm.conf
793a65b7e4ec57a677d47bbad51fb3488fd1bd1225864d55201354fa506ba521  /usr/local/bin/nvrm-watch.sh
HASHES
for target in /etc/modprobe.d/99-blackbox-uvm.conf /usr/local/bin/nvrm-watch.sh; do
    [ -f "$target" ] && [ ! -L "$target" ] || exit 2
done
bash -n adopted/system-config/usr_local_bin_nvrm-watch.sh
backup=$(mktemp -d /var/tmp/bb-drift-backup.XXXXXXXX)
cp --archive /etc/modprobe.d/99-blackbox-uvm.conf "$backup/99-blackbox-uvm.conf"
cp --archive /usr/local/bin/nvrm-watch.sh "$backup/nvrm-watch.sh"
sha256sum "$backup/99-blackbox-uvm.conf" "$backup/nvrm-watch.sh" > "$backup/sha256.txt"
stat -c '%a %u %g %n' "$backup/99-blackbox-uvm.conf" "$backup/nvrm-watch.sh" > "$backup/modes.txt"
printf 'Backup: %s\n' "$backup"
install -o root -g root -m 0644 adopted/system-config/etc_modprobe.d_99-blackbox-uvm.conf /etc/modprobe.d/99-blackbox-uvm.conf
install -o root -g root -m 0755 adopted/system-config/usr_local_bin_nvrm-watch.sh /usr/local/bin/nvrm-watch.sh
cmp adopted/system-config/etc_modprobe.d_99-blackbox-uvm.conf /etc/modprobe.d/99-blackbox-uvm.conf
cmp adopted/system-config/usr_local_bin_nvrm-watch.sh /usr/local/bin/nvrm-watch.sh
bash -n /usr/local/bin/nvrm-watch.sh
bash bin/bb drift
# Rollback if needed: cp --archive "$backup/99-blackbox-uvm.conf" /etc/modprobe.d/99-blackbox-uvm.conf
#                    cp --archive "$backup/nvrm-watch.sh" /usr/local/bin/nvrm-watch.sh
