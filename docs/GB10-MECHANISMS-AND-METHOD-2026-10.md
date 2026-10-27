# GB10 field notes, 2026-10: mechanisms, commands and method

Purpose: let another GB10 owner repeat each measurement on their own unit and compare numbers. Every claim carries a command, the
output measured here and its limit. Reports taken from forum threads are labeled **reported** and were not verified on this unit.

**Unit measured:** one Gigabyte AI TOP ATOM, DGX OS 7.2.3, kernel 6.17.0-1032-nvidia, driver 580.178.04 (open modules, locally built and
signed), Secure Boot enabled. `sudo dmidecode -t 45` reports BIOS 5.36_0ACUM08, EC 3.5.11 (fwupd: 0x0300050b), PD0 and PD1 each
FW1 5.22 / FW2 5.0. One unit. No claim here generalizes to other OEMs or to the NVIDIA Founders Edition.

## 1. Mechanisms at a glance

| # | Mechanism | State on this unit | Command | bb component | Card |
|---|---|---|---|---|---|
| A | Stuck GPU clock (500-850 MHz, zero throttle reasons) | episode 2026-10-12, recovered by power drain; detector in place | `bb reloj` | `tools/reloj_atascado.py` | FEATURE-RELOJ-ATASCADO-SEGUNDO-EJE-TFLOPS-Y-GUARDA-DE-OCUPACION-01 |
| B | Firmware inventory per boot (PD, EC, BIOS) | recorded at every boot since 2026-10-26 | `tail -n 1 /var/lib/blackbox/pstore/arranque.jsonl` | `adopted/root-scripts/arranque-forense.sh` | FEATURE-RELOJ-CAPTURA-PD-FIRMWARE-Y-TRANSICION-01 |
| C | Fan RPM through `acpi_fan` hwmon | absent on this unit; present on a reported FE | `python3 -m tools.thermal_coverage --acpi-fan` | `tools/thermal_coverage.py` | FEATURE-FAN-RPM-LEER-ACPI-FAN-DONDE-EXISTA-01 |
| D | CX7 hotplug removal on an uncabled single node | fires 18-20 s after `Hotplug enabled`, 3 of 3 boots read | `journalctl -k -b 0 \| grep -i cx7-pcie-hotplug` | `bb huella` (`cx7_hotplug`) | FORUM-00-CX7-HOTPLUG-FAN-PROTECTION |
| E | Boot userspace time growing (9.6 s to 132.6 s) | cause open; `systemd-tmpfiles-setup` is the growing unit | section 6 | `/etc/systemd/system/systemd-tmpfiles-setup.service.d/50-bb-trace.conf` (not in repo) | DEBT-ARRANQUE-USERSPACE-CRECE-TMPFILES-1M48-01 |
| F | `io` cgroup controller available to user scopes after reboot | working after one reboot | section 7 | portero (`tools/`) | DEBT-PORTERO-IO-MAX-EN-CLASE-SUITE-01 |

## 2. A: stuck GPU clock

**Signature (reported in forum threads 376039, 386060, 387029; measured here on 2026-10-12):** under full load the SM clock sits at
500-850 MHz and 10-20 W with utilization near 95 %, `clocks_throttle_reasons.active` reads `0x0`, `nvidia-smi -lgc` is accepted and
ignored, and a warm reboot does not clear it. Idle clock readings are not diagnostic, since GB10 clocks float at idle.

**Detector axes (`bb reloj`).** Verdict by median SM clock under load with no throttle reason:
`ATASCADO` below 1000 MHz, `SANO` at 1400 MHz or more (the threshold the community test in thread 362737 uses), `INDETERMINADO`
between or without enough loaded samples. Second axis, active test only: TFLOP/s below **60** with clock below 1400 MHz and no throttle
reason also gives `ATASCADO`. The 60 comes from healthy GX10 units (88.8-93.7 TFLOP/s reported in thread 387029); this unit read
**77.4 TFLOPS** after recovery, so 60 stays **provisional** and the output says so. `INDETERMINADO` carries one of `THROTTLE_ACTIVO`,
`RELOJ_EN_BANDA`, `RELOJ_ALTO_RENDIMIENTO_BAJO`, `CARGA_NO_PUDO_CORRER`, `NOT_COLLECTED` as its reason. With other compute processes
on the GPU the active test still loads it, judges by clock and power only, and marks the TFLOP/s `tflops_valido: false`.

**Run it.** Passive verdict from the telemetry tail, or an active 15 s matmul that loads the GPU:

```bash
./bin/bb reloj            # passive
./bin/bb reloj --prueba   # active; needs PyTorch with CUDA; a busy GPU invalidates only the TFLOP/s
```
Exit codes: 0 `SANO`, 1 `ATASCADO`, 2 `INDETERMINADO`. Under `--arranque` only, `CARGA_NO_PUDO_CORRER` with other processes on the
GPU exits 0, so the boot unit is not marked `Failed` by the environment; the row in `reloj_arranque.jsonl` keeps the reason.

**Negative controls measured.** The new tests fail against the code before the change (`-k "ocupada"` and `-k "bajo_no_atascado"` returned
exit 5 on the previous master, 7 and 4 passed after). The original `-k tflops` selector already passed before the change (exit 0), so
that card's check was tightened to `-k "test_tflops_"` (exit 5 before, 6 passed after).

**Declared limits.**
- Until card DEBT-RELOJ-ARRANQUE-GPU-OCUPADA-POR-EL-MOTOR-01, another process on the GPU stopped the active test before loading
  (`GPU_OCUPADA`). On 2026-10-26 the boot-time run returned that verdict because an Atlas process held 4.5 GiB, so the boot check
  measured nothing. The fix (load anyway, judge by clock, TFLOP/s marked invalid) is in code; a real boot has not run it yet.
- `inicio()` now returns the last closed episode and appends each episode to `episodios_reloj.jsonl`. The telemetry that held the
  2026-10-12 transition was rotated before the instrument existed in this form.
- Cause (power delivery or PD negotiation) is not measured.

**Recovery reported by owners (not documented by NVIDIA, and one report says it did not work):** shut down, unplug the AC cord at the
wall and at the brick, unplug USB, wait at least 5 minutes, reconnect wall, then brick, then unit. Thread 387029 reports 2 of 2 units
recovered; thread 376039 reports waits up to 8 hours and one failure.

## 3. B: firmware inventory per boot

`bb-arranque-forense.service` runs `sudo -n /usr/local/sbin/bb-root-run arranque-forense`. `bb-root-run` executes only scripts whose
sha256 sits in a root-owned manifest, so changing `adopted/root-scripts/arranque-forense.sh` requires reinstalling the manifest.

Row written per run (values from `sudo dmidecode -t 45`, SMBIOS firmware inventory):

```json
{"ts":"...","boot_id":"...","pstore_archivos":0,"bert":"ausente","firmware":"bios+t45","pd0":"PD0 FW1: 5.22, FW2: 5.0","pd1":"PD1 FW1: 5.22, FW2: 5.0","ec":"3.5.11","bios":"5.36_0ACUM08"}
```

Values enter the JSON only if they match `^[A-Za-z0-9 ._:,+-]{1,80}$`; otherwise the field is `NOT_COLLECTED: <reason>`.

**Install and verify (root).** Review what you approve, install, then check:

```bash
python3 -m tools.bb_root_manifest --propose     # prints the install command with expected hashes
python3 -m tools.bb_root_manifest --check; echo rc=$?
systemctl --user start bb-arranque-forense.service
tail -n 1 /var/lib/blackbox/pstore/arranque.jsonl
```
Measured: before installing, `--check` gave `aprobados iguales: 10, cambios: 1`, rc=1; after, `iguales: 11, cambios: 0`, rc=0, and
the new row carried the four values. By its code the runner rejects a script whose hash differs from the manifest with rc 3 (not
run here: the install followed the merge directly). Older rows have no `pd0`, so history starts at the install.

**Limits.** `dmidecode` needs root and bb runs without it, hence the sealed runner. `dmesg` with root shows no UCSI, Type-C or PD
lines on this unit, so **PD negotiation has no local source**; nobody has named one (asked of NVIDIA in thread 386060).

## 4. C: fan RPM

Thread 386805 (reported, Founders Edition, DGX OS 7.6.0) reads `/sys/class/hwmon/hwmon*/fan1_input` on the hwmon whose `name` is
`acpi_fan`. This unit has hwmon `acpitz`, `nvme`, `mt7925_phy0` and 26 `cooling_device` entries (20 `Processor`, 6 `PCIe_Port_Link_Speed`),
none a fan.

```bash
python3 -m tools.thermal_coverage --acpi-fan; echo rc=$?
```
Measured here: `NOT_COLLECTED: sin hwmon acpi_fan`, rc=2. A reading of 0 rpm returns `0` labeled stopped, never `NOT_COLLECTED`.
Tests (`tests/test_fan_rpm.py`) cover with and without the device, a zero reading, and an unreadable file, and four mutants that
return the wrong silent value all fail them.

## 5. D: CX7 hotplug on a single node

Thread 378945, post 22 (reported, FE): with no cable in the CX7 ports, `cx7-pcie-hotplug` logs `Cable removal` about 16 s after boot,
the CX7 leaves the PCIe bus, idle power drops, and the EC's idle fan logic (power-based per posts 17-19) stops the fans.

```bash
journalctl -k -b 0 --no-pager | grep -iE "mlx5_core.*Cable unplugged|cx7-pcie-hotplug"
lspci | grep -iE "mellanox|connectx" || echo "no ConnectX on the bus"
ls -la /etc/nvidia/cx7-hotplug-enabled
```
Measured here: `Hotplug enabled` then `Cable removal` 18, 19 and 20 s later at three boots, no ConnectX in `lspci`
(`lspci` itself listed 7 NVIDIA devices, so the filter works), marker file present, `hotplug_enabled` = 1.

**Not shown:** that the fans of this unit stop. The unit exposes no fan sensor, so a physical check is the only observation. No
workaround was applied here. The `nvfancontrol` module (github.com/Z841973620/dgx-spark-fan-override) hard-codes physical address
`0x933dd000` taken from an FE with EC 0x03000508; this unit has EC 0x0300050b, so it was **not** loaded.

## 6. E: boot userspace time growing

```bash
systemd-analyze                                   # firmware, loader, kernel, userspace
systemd-analyze blame | head -12
# tmpfiles-setup duration per stored boot, from the journal:
for b in $(journalctl --list-boots --no-pager | awk '{print $1}'); do
  journalctl -b $b --no-pager -o short-unix _PID=1 | grep -E "(Starting|Finished) systemd-tmpfiles-setup" ; done
```
Measured series (tmpfiles-setup / userspace, seconds): 2.9/23, 0.4/23, 0.7/10, 5.5/15, 22.0/29, 40.4/48, 30.4/55, 95.4/120, 108.2/133
(boots from 2026-10-12 to 2026-10-26). Firmware (about 71 s) and kernel (about 4.5 s) stayed constant.

**Refuted so far, each with its measurement:**
- Creation work: `sudo strace -f -ttt ... systemd-tmpfiles --create --exclude-prefix=/dev` ran in 0.14 s (2536 calls).
- Deleting `/tmp` (356,222 files, 8.0 GB at 34 min after boot, on ext4): a 30,000-file benchmark deleted 57,193 files/s with the cache
  dropped, so about 6 s. Script: create 30,000 files of 23 KiB, `sync`, `echo 3 > /proc/sys/vm/drop_caches`, time `rm -rf`.
- Root private temp directories: each `/tmp/systemd-private-*` and `/var/tmp/systemd-private-*` held 2 files, 8 KiB (state of the
  current boot, not of the previous shutdown).
- Network mounts: none. NVMe or ext4 errors in the kernel log: none.

**Open.** Next boot captures the real step. The drop-in below runs the same command under `strace -c -w` and falls back to the plain
command if `strace` fails; the summary lands in `/var/lib/blackbox/tmpfiles-boot-<epoch>.strace-c`. Revert by renaming it to `.off`.

```ini
# /etc/systemd/system/systemd-tmpfiles-setup.service.d/50-bb-trace.conf
[Service]
ExecStart=
ExecStart=/bin/sh -c '/usr/bin/strace -f -c -w -o /var/lib/blackbox/tmpfiles-boot-$(date +%%s).strace-c /usr/bin/systemd-tmpfiles --create --remove --boot --exclude-prefix=/dev || exec /usr/bin/systemd-tmpfiles --create --remove --boot --exclude-prefix=/dev'
```
`systemd 255` has no `--dry-run` or `--verbose` for `systemd-tmpfiles`; two commands written for this investigation failed for that reason.

## 7. F: `io.max` for user scopes

```bash
cat /sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/cgroup.subtree_control   # cpu memory pids at first
systemd-run --user --scope -q -p "IOWriteBandwidthMax=/dev/nvme0n1 500M" \
  sh -c 'c=/sys/fs/cgroup$(cut -d: -f3 /proc/self/cgroup); echo "io.max: [$(cat $c/io.max)]"'
systemd-run --user --scope -q sh -c 'c=/sys/fs/cgroup$(cut -d: -f3 /proc/self/cgroup); echo "io.max: [$(cat $c/io.max)]"'
```
Prerequisite: a system drop-in `Delegate=cpu memory pids io` for `user@.service`, then **one reboot** (the user manager detects
controllers when it starts). Measured after the reboot: the capped scope printed `io.max: [259:0 rbps=max wbps=500000000 ...]`, the
uncapped scope printed `io.max: []`, and `subtree_control` listed `io` only after the first unit asked for it. Throughput check with
`dd if=/dev/zero of=FILE bs=1M count=1024 oflag=direct` inside such a scope: **509 MB/s capped, 4.0 GB/s uncapped.**

## 8. Method

- **One card per pending item,** each with a `close_check` that must fail today. A check that already passes cannot show the work was
  done: one such case (`-k tflops`) was found and tightened.
- **Negative control with every verification:** the new tests run against the old code and fail; mutants of the new code fail.
- **Delegated work is re-run by the orchestrator** before merging: the check must fail on the main branch and pass on the branch.
- **A report with `could_not_run > 0` is not clean.** The debt scanner prints each source it looked at, including those that do not exist.
- **Nothing is deleted to suspend it:** rename, record the hash, set an expiry.
- **Deployments that change root-owned state are written as exact commands with expected hashes** and run by the owner.

## 9. Corrections made along the way

- The first version of the PD card stated that no bb code captured PD firmware. `arranque-forense` already copied `dmidecode -t 45`;
  the search had looked for the text "pd firmware" and not for the file name `dmidecode-t45`. What was missing was history and a link
  to the verdict.
- `FEATURE-FAN-RPM` had closed claiming no standard path exposes fan RPM. That holds for this ATOM and fails for a reported FE.
- Restarting `gnome-shell` from inside the assistant session closed the session; the command belongs to the owner over SSH or a TTY.

## 10. Source threads

| Thread | Used for |
|---|---|
| 386060 (stuck clock, ATOM) | signature, detector, NVIDIA's data requests |
| 387029 (45 s check, GX10 numbers) | healthy and stuck TFLOP/s, recovery order, busy-GPU guard |
| 378945 (fans stop when the screen is dark) | power-based idle fan logic, CX7 hotplug precondition |
| 386805 (FE fans barely speed up) | `acpi_fan` hwmon, EC 0x03000d07 behavior |
| 377069 (EC rollback) | rollback reports that did and did not work |
| 387012 (ATOM stopped fan after updates) | unexpected restart, link cycling |
