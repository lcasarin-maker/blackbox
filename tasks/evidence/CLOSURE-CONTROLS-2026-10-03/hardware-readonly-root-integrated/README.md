# Hardware evidence/read-only action map

Source: `tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware.json` (SHA-256 `1894059c90079e614cceae0d7630ac98081dcba0e93942e69ec482a42763a96f`). The source yielded 47 unique IDs; generated batches contain 10, 10, 10, 10, and 7 cards. The final map preserves each card's exact `close_check`, lists existing evidence references with hashes/sizes, and records the current gap, useful read-only step (if any), and external prerequisite. Exact-once validation: 47 rows, 47 unique IDs, every source ID present once.

No host command was run for this mapping. Existing observations remain observations, not proof of closure; source/evidence hashes establish byte consistency only.

## Best next read-only observations

These can reduce a specific evidence gap, but they do not close the larger card by themselves:

- `FORUM-00-KERNEL-INITRD-UPDATE-GATE`: bounded read-only package ownership/version and `modinfo` path/signature provenance may clarify current package/module readiness. The current preflight has permission-denied APT lock and missing `apt_check`/`module_ready` results. Do not run package operations.
- `FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT`: a privileged read-only value of `/sys/module/nvidia_drm/parameters/modeset` can replace the current permission-denied observation. OTA compatibility still needs target/recovery evidence.
- `FEATURE-FORUM-SBSA-WATCHDOG-STATE-01`: a privileged read-only owner attribution for `/dev/watchdog0` may resolve the current unprivileged `fuser` rc1/empty ambiguity. OEM recovery policy remains separate.
- `FORUM-REALTEK-DRIVER-BINDING-01`: read-only `dpkg-query -S` and `modinfo` provenance can add package owner/signature to the already observed r8127 PCI binding/version; reboot A/B and rollback remain open.
- `DELTA-FORUM-OTA-DRIVER-KERNEL-EFFECTIVE-TUPLE-01` and `FEATURE-FORUM-GB10-RUNTIME-COMPAT-01`: reuse the archived native NVIDIA GB10/580.178.04 receipt and current kernel identity. This binds the present tuple only; no OTA/runtime behavior claim follows.
- `DELTA-ROOT-BACKUP-MOUNT-BOOT-IDENTITY-01`: once the intended backup device and expected UUID are known/attached, read-only `findmnt`/`lsblk` plus `boot_id` can bind the actual mount. No destination is currently evidenced.

## Implementation gaps to fix before interpreting the existing close checks

- `FORUM-00-DOCKER-OOM-RESTART-LOOP`: ten unit tests currently pass without a physical containment control. Add the real control to `tests/test_workload_restart_containment.py` and its source-generated registration; a controlled OOM/restart subject test is still required later.
- `FEATURE-FORUM-NVME-READONLY-01`: `tests/test_nvme_readonly.py` lacks the original selector for a real subject check. Add the real source-generated selector/assertion; the existing instrument and regular-file copy checks remain signals-only. Physical NVMe/OEM recovery claims need distinct evidence.

## Other blockers

Most remaining rows need a real peripheral/adapter/peer, an approved workload or reboot/hotplug/recovery procedure, an independent trusted dataset, exact OEM documentation, or a human disposition. Those prerequisites and specific gaps are recorded per row in `hardware-readonly-evidence-map.json`. I did not repeat broad hardware inventory or initiate any workload/network/firmware/power action.
