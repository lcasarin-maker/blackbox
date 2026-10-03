# Boot and backup-destination instrumentation — 2026-10-03

`tools.host_diagnostics` adds a narrowly scoped backup destination guard and a
read-only current-boot inventory. The guard is exposed through
`--check-backup-destination` and requires explicit `--backup-mountpoint`,
`--backup-source`, and `--backup-uuid` arguments. It checks that the directory
exists under the live root, then asks native `findmnt` for JSON `TARGET,SOURCE,UUID`
using `--mountpoint` and demands exact equality for all three values. Missing
identity input yields `unknown`; an unmounted exact target or mismatch yields
`block`; inaccessible or incomplete metadata yields `unknown`.

Example form (supply the expected values from an independently trusted backup
configuration):

```sh
python3 -m tools.host_diagnostics --check-backup-destination --backup-mountpoint /mnt/backup --backup-source /dev/sdb1 --backup-uuid 01234567-89ab-cdef-0123-456789abcdef
```

A match reports only an observed identity. It grants no permission to write or
restore and cannot prevent the mount from changing after the check (TOCTOU).
This implementation performs no backup, media read, restore, remount, or write.
Fixture roots are rejected for the live CLI; tests inject a fake `findmnt`
runner. An existing directory without an exact mount is a blocking negative
control. Positive, UUID mismatch, device mismatch, parent-mount-only, missing
UUID, denied query, malformed JSON, and path escape controls are covered in
`tests/test_boot_storage_inventory.py`.

The boot inventory reads the running release from the supplied filesystem
root's `proc/sys/kernel/osrelease` (or an explicit test input), confines those
proc paths and boot artifact symlinks to that root, and reports only whether the
current release's `vmlinuz` and `initrd.img` artifacts are present. Artifact
presence does not establish package consistency or bootability; no target
release, OTA compatibility, OEM support, or recovery was tested. DRM command
line capture filters to the `nvidia-drm.modeset`/`nvidia_drm.modeset` keys and
emits only documented boolean spellings; any other value becomes `unknown`.
The raw `/proc/cmdline` is never emitted. The effective sysfs modeset value is
reported independently. Existing `gpu_runtime_capture` and session/service
queries remain the source for GSP and rescue-related observations; they do not
prove GSP failure recovery or rescue access.

## Local capture

The exact capture command was:

```sh
python3 -c 'import json; from pathlib import Path; from tools.host_diagnostics import backup_destination_check, boot_state_inventory, gpu_runtime_capture, mount_summary; print(json.dumps({"backup_destination": backup_destination_check(Path("/"), None, None, None), "boot_state": boot_state_inventory(Path("/")), "gpu_runtime_existing": gpu_runtime_capture(), "root_mount_summary": mount_summary(Path("/"))}, indent=2, sort_keys=True))' > tasks/evidence/BB-INSTRUMENTS-2026-10-03/boot.capture.json
```

It returned exit code `0`; that means collection completed, not that the
machine passed the checks. The captured backup guard is `unknown` because no
trusted expected source/UUID/mountpoint was supplied; it did not run `findmnt`.
The running release is `6.17.0-1032-nvidia`; both corresponding `vmlinuz` and
`initrd.img` files were observed present. The effective DRM modeset sysfs read
returned `could_not_run` (`PermissionError`), and the filtered command line had
no recognized modeset override. `nvidia-smi` returned code 9 with “couldn't
communicate with the NVIDIA driver”; therefore GPU/GSP health is
`could_not_run`. CUDA Runtime reported 13.0, which does not establish device
availability. The root mount summary was readable. Five JSON nodes carried
`could_not_run`; that count includes nested status nodes and is not a count of
independent queries.

## Validation

`python3 -m pytest -q tests/test_boot_storage_inventory.py tests/test_device_inventory.py tests/test_network_inventory.py tests/test_host_diagnostics.py --cov=tools.host_diagnostics --cov-branch --cov-report=term-missing`:
`102 passed in 1.92s`; coverage reported `483 Stmts, 0 Miss, 178 Branch, 0
BrPart, 100%`.

`python3 -m ruff check tools/host_diagnostics.py tests/test_boot_storage_inventory.py tests/test_host_diagnostics.py tests/test_device_inventory.py tests/test_network_inventory.py`:
`All checks passed!`

`pyright tools/host_diagnostics.py`:
`0 errors, 0 warnings, 0 informations`.
