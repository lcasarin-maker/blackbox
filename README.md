# blackbox

A black box for NVIDIA GB10-class AI workstations — DGX Spark, ASUS Ascent
GX10, Gigabyte AI TOP ATOM, and the other partner boxes built on the same
chip. It records what you need to diagnose a failure **after** it happens,
and tells you which instrument isn't armed *before* the next one.

This hardware class is new enough that a lot of the failure modes are still
being figured out in public, one NVIDIA forum thread at a time: silent
shutdowns under load, GPUs that fall back to CPU with no error, USB
controllers that die, unified memory that reports numbers `nvidia-smi`
can't explain. `blackbox` exists so the *next* failure on one of these boxes
leaves evidence, instead of another "it just turned off, no idea why" thread.

---

## Why this exists

On 2026-09-07 a GUI application on one of these machines hung: main process
alive, window on screen, **zero renderer processes**, and a stale
`SingletonLock` making every relaunch fail silently.

The post-mortem ruled out everything measurable — no RAM OOM, no segfault, no
thermal throttle, GPU responsive, temperatures at 62–79°C against a 104°C
trip point — and **never reached root cause**, because `ulimit -c` was 0 and
`systemd-coredump` wasn't installed. The renderer died and left nothing
behind.

That gap — instrumentation that isn't armed until after you needed it — is
what this repo closes. Not just for that one incident: browsing the NVIDIA
developer forum turns up the same shape of problem over and over on this
hardware class (see [Known failure classes](#known-failure-classes-in-the-wild)
below), usually closed as "reflash and hope" because nobody captured a core
dump, an Xid code, or a PCIe AER log at the moment it happened.

## Hardware this targets

Built and tested on a **Gigabyte AI TOP ATOM** (NVIDIA GB10, 20 aarch64
cores, 121 GB unified memory, Ubuntu 24.04) — the same chip shared by:

- NVIDIA DGX Spark
- ASUS Ascent GX10
- Gigabyte AI TOP ATOM
- other OEM boxes built on the same GB10 module

Most of the forensic logic (Xid codes, PCIe/AER, xHCI, unified-memory
quirks, PSI) is GB10-specific, not DGX-Spark-brand-specific — it should work
unmodified on any box built on this chip. Issues and PRs from other GB10
hardware are welcome; see [Contributing](#contributing).

---

## Usage

```
bb status              which instrument is armed and which isn't
bb scan ["since X"]    failure report over a time window (default: "2 hours ago")
bb snapshot [reason]   full forensic dump, right now
bb hw                  hardware inventory and applied limits
bb drift               diff between what's adopted in the repo and what's deployed
bb protect             raise the core-dump limit on processes already running (prlimit)
bb who [pid]           which processes are heavy and WHO launched them (unit, parent, cwd)
bb sample              one sample (fired by the per-minute timer)
bb install             install the user timer
```

Full install:

```bash
./bin/bb install              # no privileges needed
sudo ./enable-privileged.sh   # core dumps (see below)
```

`enable-privileged.sh` supports `--dry-run` and `--revert`.

---

## What it watches

`blackbox` doesn't duplicate telemetry that already exists on a healthy
Ubuntu box (`sar`, `journald`, `earlyoom`) — it reads those, and adds the
signals that a stock install doesn't produce on its own:

| Signal | Why it's not covered elsewhere |
|---|---|
| GPU Xid codes | `nvidia-smi`/dmesg carry them, but nothing greps for them by default — Xid is how the driver reports firmware faults and RPC timeouts, and it looks nothing like an OOM or a segfault |
| xHCI/USB controller death | Zero coverage in a stock install: no "HC died", no speed-fallback, no enumeration conflicts |
| PCIe power/AER events | Cross-referenced against OOM and thermal so a hard power-off gets one verdict instead of three unrelated logs |
| PCIe replay counters | NVML-level link retransmit counts, from `nvidia-smi -q`'s PCI section — a replay can happen without the kernel ever writing an AER log line, so this is a second, independent signal, not a duplicate of the AER grep above |
| GPU clock/pstate vs. throttle | Clock and pstate are cheap to sample every few seconds; almost nothing correlates them with the thermal trip point |
| GPU 0% with active load | Correlates reserved GPU memory with sustained 0% utilization — the signature of a silent fallback to CPU |
| Boot stuck in GDM | `journalctl -b -1` for "gdm started, no login followed" — a layer below the desktop-app checks |
| Kernel vs. userspace GUI hang | Two-probe check: is the NVIDIA kernel module loaded, is the display manager actually up |
| OCI/nvidia-container-runtime prestart hook | Catches the silent fallback to "legacy" mode with no real GPU, where the container still reports "Up" |
| NVIDIA's own Field Diagnostic results | If `dgx-spark-fieldiag` (NVIDIA's official RMA pre-check suite) was run in the scan window, its `summary.json` verdict is read and cross-referenced — blackbox never installs or runs it itself, since it's deliberately disruptive (kills the GUI, stops docker, 30–40 min) |
| kdump | Confirms it's actually installed and captured a crash, instead of trusting the unit's `enabled` state |
| PSI (`/proc/pressure`) | Neither `MemFree` nor `MemAvailable` says how much time was actually spent *stalled* waiting on memory — PSI does |
| Named throttle reasons + lifetime counters | `nvidia-smi`'s binary throttle flag doesn't say *why* — `-q -d PERFORMANCE` separates SW power cap from HW/SW thermal slowdown from HW power-brake, plus how many seconds each has accumulated since the last driver reload |
| GPU processes that already exited | `--query-compute-apps` only sees what's running *now* — accounting mode (`bb`'s privileged setup step) keeps per-PID GPU usage around after the process is gone, for exactly the question a post-mortem actually asks |

Every check that can't run is counted and printed, never silently skipped.
**A report with `could_not_run > 0` is not a clean report**, however many
other rows pass.

### Lessons this hardware taught us the hard way

- **`OnBootSec`/`OnUnitActiveSec` user timers don't fire reliably** when the
  user manager starts late relative to boot. Use `OnCalendar` instead —
  measured: a monotonic timer produced zero triggers in 57 minutes on this
  box; `OnCalendar` didn't have the problem.
- **GPU memory doesn't read from `--query-gpu` on GB10.** `memory.total`,
  `memory.used`, `memory.free` all return `[N/A]`. What works is
  `--query-compute-apps=pid,process_name,used_memory`, summed. Because
  memory is unified (one NUMA node), those GB come out of the same pool the
  desktop uses.
- **Config saying "disabled" doesn't mean the collector isn't running.**
  `/etc/default/sysstat` can say `ENABLED="false"` while a drop-in timer
  fires `sar` every minute anyway. Check the data (file mtime), not the
  variable.
- **Arming capture doesn't protect what's already running.** Installing
  `systemd-coredump` isn't retroactive — a process keeps the core limit it
  inherited at start. `bb protect` fixes this live with `prlimit`, without
  restarting anything.
- **A logged event isn't a corroborated event.** One telemetry stream on
  this box logged 1223 "critical temperature" events; the same stream's own
  correlation logic discarded 1093 of them as isolated sensor spikes and
  corroborated 4. Aggregating by event name alone would have reported 1223
  thermal alarms where there were 4.

---

## Known failure classes in the wild

A sample of what other GB10 owners have hit and reported on the NVIDIA
developer forum — grouped by the failure class `blackbox` tries to catch
before it becomes an unsolved thread:

**Silent shutdown / power-off under load**
- [Shutting down under load, MODS 020000600139](https://forums.developer.nvidia.com/t/dgx-spark-shutting-down-under-load-mods-020000600139/372469)
- [Reproducibly hard powers off under GPU load, zero crash capture](https://forums.developer.nvidia.com/t/dgx-spark-gb10-reproducibly-hard-powers-off-under-gpu-load-fully-updated-zero-crash-capture/373251)
- [Sparks have recently powered off randomly](https://forums.developer.nvidia.com/t/sparks-have-recently-powered-off-randomly/376103)
- [Shut down without rebooting](https://forums.developer.nvidia.com/t/dgx-spark-shut-down-without-rebooting/369716)

**GPU faults / driver crashes**
- [GB10 GPU fails to initialize GSP firmware, SEC2 secure boot timeout](https://forums.developer.nvidia.com/t/dgx-spark-gb10-gpu-fails-to-initialize-gsp-firmware-sec2-secure-boot-timeout-rminitadapter-0x622028-rma/374016)
- [GB10 spontaneous reboots, GSP health check fail, NVRM assert flood](https://forums.developer.nvidia.com/t/gb10-spontaneous-reboots-after-july-2026-update-gsp-health-check-fail-nvrm-assert-flood-gpu-user-shared-data-c-373/379959)
- [Can not reset spark GPU](https://forums.developer.nvidia.com/t/can-not-reset-spark-gpu/354395)
- [DGX Spark GPU crash](https://forums.developer.nvidia.com/t/dgx-spark-gpu-crash/348223)

**USB / xHCI**
- [xHCI controller HC died, crashes with RealSense streaming](https://forums.developer.nvidia.com/t/dgx-spark-xhci-controller-hc-died-crashes-with-realsense-d435i-streaming-30fps-depth-rgb/355453)
- [All USB connections fall back to 480 Mbps (USB 2.0)](https://forums.developer.nvidia.com/t/all-usb-connections-fall-back-to-480-mbps-usb-2-0/362015)
- [USB-C enclosure always falls back to USB2.0 on soft replug](https://forums.developer.nvidia.com/t/asm2464pd-usb-c-3-2-2x2-enclosure-always-fall-back-to-usb2-0-480-mbps-soft-replug/380009)

**Thermal / fan**
- [Low fan speed, high temps, device very hot](https://forums.developer.nvidia.com/t/dgx-spark-low-fan-speed-high-temps-device-very-hot/348760)
- [Fan not spinning, 80°C at idle, 0% GPU utilization](https://forums.developer.nvidia.com/t/dgx-spark-gb10-fan-not-spinning-80-c-at-idle-with-0-gpu-utilization/370080)
- [What are normal temps under load — is 94.6°C too hot?](https://forums.developer.nvidia.com/t/what-are-normal-temps-under-load-is-94-6c-too-hot/377375)
- [Thermal throttling after EC/UEFI updates, fans not ramping](https://forums.developer.nvidia.com/t/dgx-spark-gb10-thermal-throttling-after-ec-uefi-updates-acpi-zones-96-97c-fans-not-ramping/377044)

**GPU stuck at 0% / silent CPU fallback**
- [GPU usage 0% after 24h, Open WebUI](https://forums.developer.nvidia.com/t/dgx-spark-gpu-usage-0-after-24-hours-open-webui/353683)
- [vLLM 100% CPU usage when idle, again](https://forums.developer.nvidia.com/t/vllm-100-cpu-usage-when-idle-again/362964)
- [GPU clock pinned at 721 MHz under full load, not liftable via nvidia-smi](https://forums.developer.nvidia.com/t/dgx-spark-gb10-gpu-clock-pinned-at-721-mhz-under-full-load-no-throttling-not-liftable-via-nvidia-smi/376039)

**Boot / kernel / driver install**
- [DGX won't boot, tried all documented methods](https://forums.developer.nvidia.com/t/dgx-wont-boot-tried-all-documented-methods-from-public-documentation-and-this-forum/373187)
- [Kernel panic](https://forums.developer.nvidia.com/t/kernel-panic/352519)
- [Boot failure after installing an LLM model](https://forums.developer.nvidia.com/t/dgx-spark-boot-failure-after-installing-llm-model/347951)
- [My GUI is gone and nvidia-smi is not working](https://forums.developer.nvidia.com/t/my-gui-is-gone-and-nvidia-smi-is-not-working/366211)

**Networking**
- [Ethernet connection unstable after Nov 2025 update (EEE workaround)](https://forums.developer.nvidia.com/t/dgx-spark-ethernet-connection-unstable-after-november-2025-update-eee-energy-efficient-ethernet-workaround/354764)
- [Ethernet port is not working](https://forums.developer.nvidia.com/t/ethernet-port-on-dgx-spark-is-not-working/366125)
- [Weird network behaviour](https://forums.developer.nvidia.com/t/weird-network-behaviour/351340)

None of these threads are ours — they're other owners of this hardware
class hitting the same blind spots `blackbox` is built to close. If your
report has the same shape ("it just died, nvidia-bug-report.sh didn't help,
no core dump, no clear Xid"), that's exactly the gap this project targets.

---

## Related work

`blackbox` isn't the only project reacting to this hardware class's rough
edges, and it isn't trying to duplicate what already exists elsewhere:

- **[sparkview](https://github.com/parallelArchitect/sparkview)** — a live
  TUI dashboard for GB10 boxes: GPU/CPU/PSI/clock-throttle state in real
  time, plus an anomaly auto-logger that starts recording *before* a human
  notices something is wrong. `blackbox`'s use of `/proc/pressure` (PSI) as
  the signal that catches what `MemFree`/`MemAvailable` miss was informed by
  sparkview's write-up on the same [forum thread](https://forums.developer.nvidia.com/t/sparkview-gpu-monitor-tool-with-gb10-aware-unified-memory-handling/366877)
  this repo cites above. The two tools are complementary, not overlapping:
  sparkview watches the machine *live*; `blackbox` is what you run *after*,
  to reconstruct a window of time nobody was staring at when it happened.
- **[nvml-unified-shim](https://github.com/parallelArchitect/nvml-unified-shim)**
  — fixes NVML memory reporting on unified-memory platforms. Independent
  confirmation of the same quirk this README documents above: on GB10,
  `nvmlDeviceGetMemoryInfo` reports `total ≈ MemTotal`, which is not
  allocatable memory, and both projects landed on the same workaround
  (derive used/available from the host side, not from NVML's own total).

If you maintain a tool in this space and it belongs here, open a PR.

---

## A platform gap that makes this harder than it should be: no cgroup accounting for GPU/unified memory

A good chunk of the OOM-adjacent failures above trace back to one thing:
**Linux cgroups have no concept of GPU memory**, and on unified-memory
hardware like GB10 that's worse than on a discrete-GPU box. The system
`memory` controller (`memory.max`, `memory.events`, PSI's
`/proc/pressure/memory`) only ever sees host RSS. A process that maps 15 GB
of *unified* memory through the NVIDIA driver can starve every other process
on the machine — GPU or not, because it's the same physical pool — without
that memory ever showing up against any cgroup's accounting, and without
tripping the cgroup OOM killer the way a plain RSS overrun would.

The practical result, measured on this hardware: the only way we found to
cap an interactive process before it takes the desktop down with it is a
userspace wrapper (`systemd-run --scope -p MemoryMax=...`) that limits host
RSS — which is not what unified memory actually consumes, so it's a
best-effort fence, not a real limit. There is no kernel-level primitive
equivalent to `cpu.max` for GPU compute share, no `gpu.pressure` file
alongside `/proc/pressure/memory`, and no cgroup-visible OOM event when a
process gets killed or aborts because it couldn't get unified memory instead
of RAM. See the full write-up in the forum post linked from this repo's
issues, or the [Contributing](#contributing) section if you have data from
other GB10 boxes that confirms or contradicts this.

### A community hypothesis worth testing: UVM page-migration livelock

**Unverified — this is a third-party forum claim, not something confirmed
on this hardware.** One report on the NVIDIA developer forum, describing
the same "dies under sustained load, fine at idle, no warning, no log"
pattern documented above, proposes a specific mechanism: on GB10, weights +
KV cache + CUDA workspace share the same 128 GB unified pool, and if total
allocation creeps too close to the ceiling during a long-running job, the
result isn't a clean OOM — it's a UVM (Unified Virtual Memory) page-migration
livelock that hard-locks the machine with no warning and no log, because the
OOM-killer never fires. That would explain why this failure class evades
every log-based detector, including this repo's own DGX-438 (the
still-unexplained periodic SIGTERM killer, see `tasks/backlog/`): a livelock
during page migration wouldn't route through the kernel OOM path, the
cgroup OOM path, or PSI at all, since none of those instrument UVM directly.

The mitigation the same report credits, in order: cap the memory a server
actually claims (in vLLM, `--gpu-memory-utilization` at 0.85–0.92 rather than
0.94+, leaving 10–15 GB of headroom) and update platform firmware (BIOS/BMC,
separate from OS/driver packages). Two more items commonly paired with it —
locking GPU clocks and capping GPU power draw via `nvidia-smi -pl` — are
worth a hardware-specific gut check before following blindly: on this box,
clock locking (`nvidia-smi -lgc 300,2800`) is already applied via a boot-time
systemd unit, but `-pl` power capping is **not supported at all** —
`nvidia-smi -q -d POWER` returns `N/A` for every power-limit field
(current/requested/default/min/max) on this GB10. If you're on different
GB10 hardware and `-pl` works for you, that's useful data in itself — open
an issue.

If `bb scan`/`bb sample` ever catch a hang with this exact fingerprint —
unified memory near its ceiling, no kernel OOM, no thermal event, no Xid —
that would be the first real evidence either for or against this theory on
this specific box, instead of another anonymous forum report.

---

## Install

```bash
git clone https://github.com/lcasarin-maker/blackbox.git
cd blackbox
./bin/bb install              # per-user sampling timer, no privileges
sudo ./enable-privileged.sh   # systemd-coredump + core-dump disk cap
```

Everything blackbox writes lives under `$BLACKBOX_DATA`
(default: `~/.local/share/blackbox`). `enable-privileged.sh` is idempotent
and reversible (`--revert`, `--dry-run`).

No dependencies beyond what a stock Ubuntu install already has: coreutils,
procps, systemd, `nvidia-smi`. Python is only used for one small,
fully-tested close-check helper (`tools/check_harvest_accepted.py`) — the
tool itself is plain bash.

## Hardening

`bin/bb` and `enable-privileged.sh` pass `shellcheck` with zero warnings
(a few `info`-level suggestions on `ls`/`ps` usage against
kernel/systemd-controlled paths are left as-is — not exploitable in this
context, and `find`/`pgrep` equivalents would be less readable for no real
gain here). Run it yourself before sending a PR:

```bash
shellcheck bin/bb enable-privileged.sh
```

Two things worth knowing if you're touching either script:

- **`bin/bb` deliberately does not use `set -e`** (only `set -uo pipefail`).
  A forensic scanner that dies on the first failing sub-check instead of
  counting it and moving on defeats its own purpose — `could_not_run > 0`
  has to survive to the final report, not abort it.
- **`$BLACKBOX_DATA` is `chmod 700` on every run**, not just at creation —
  it holds full command-lines of other processes (`bb who`/`scan`/`sample`),
  and an already-existing data directory from before this was added won't
  fix itself from an idempotent `mkdir -p` alone.

## Contributing

This started as instrumentation for one machine and is being opened up
because the failure modes above are clearly not specific to that one box.
Useful contributions:

- **Data from other GB10 hardware** (DGX Spark, ASUS Ascent GX10, Gigabyte
  AI TOP ATOM, other OEM boxes) — does a given check fire correctly on your
  unit? Different
  thermal trip points, different USB topology, different firmware revision
  are all useful data points, not just bug reports.
- **New forensic checks** for failure classes not yet covered — a PR should
  say what signal it reads, how it was verified to fire on a real case, and
  how it was verified to *stay silent* on a healthy one (`bb scan`/`bb
  status` report `could_not_run` explicitly; a check that can't fail is a
  defect in the check, not evidence the machine is fine).
- **Corrections** — anything above stated more confidently than the
  evidence supports. Everything in this README was measured on one unit;
  where it says "on this hardware" it means exactly that, not "on all GB10
  hardware."

Issues and PRs welcome. Open an issue first for anything that touches
`enable-privileged.sh` (root) or the systemd unit files, since those are
the parts with real blast radius on someone else's machine.

## License

MIT — see [LICENSE](LICENSE).
