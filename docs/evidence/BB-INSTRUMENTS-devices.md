# BB instruments: device inventory execution

Five device instrument cards received partial implementation on
`codex/bb-inst-devices`. All five source cards remain `status: open`; their
original `close_check` fields remain unchanged. No experimental closure was
attempted.

`tools.host_diagnostics` now reads USB vendor/product IDs, manufacturer,
product, serial when exposed, and negotiated sysfs speed; correlates HID entries
to the nearest USB device ancestor through contained sysfs symlinks; and captures watchdog identity, state,
timeout, and nowayout while reporting owner `UNKNOWN`. It never reads serial
attributes from devices that lack them: absent serial is reported as `unknown`,
and inaccessible serial is `could_not_run`. Vendor/product IDs alone do not
establish a unique or stable UUID. This inventory does not test USB RAID link
admission. The reader checks resolved attribute paths stay inside the supplied
sysfs root and never opens `/dev/watchdog`. Missing required or inaccessible
files remain visible as `could_not_run`. Existing Realtek PCI binding coverage
is reused.

## Local read-only capture

Command: `python3 -m tools.host_diagnostics > tasks/evidence/BB-INSTRUMENTS-2026-10-03/devices.capture.json`

The subsequent JSON summary command reported:

```json
{"could_not_run": 15, "hid_entries": 0, "report_status": "partial", "usb_entries": 16, "usb_inventory_status": "ok", "watchdog_owner": "UNKNOWN", "watchdog_status": "ok"}
```

The complete native JSON is preserved at
`tasks/evidence/BB-INSTRUMENTS-2026-10-03/devices.capture.json`. The capture
command exited `2`, the instrument's exit for a nonzero `could_not_run` count.

The USB sample included a `GenesysLogic USB2.1 Hub` at `1-1` with sysfs speed
`480`, and PCI binding reported interface `enP7s7` bound to `r8127`, module
version `11.014.00-NAPI`. These are observations from this host, not device
acceptance tests. Zero HID entries means this capture supplies no positive HID
correlation evidence. The report had 15 `could_not_run` observations across
all diagnostic checks, so it is partial.

## Validation

`python3 -m pytest -q tests/test_device_inventory.py --cov=tools.host_diagnostics --cov-branch --cov-report=term-missing`:
`13 passed in 0.13s`. The full-module summary is `285 Stmts, 172 Miss,
98 Branch, 2 BrPart, 37%`; its missing statements belong to pre-existing
diagnostic helpers outside the new inventory. The coverage JSON had no missing
statements or branch edges on the added lines (`tools/host_diagnostics.py`
lines 147–245).

`python3 -m pytest -q tests/test_host_diagnostics.py`:
`33 passed in 1.52s`.

`python3 -m ruff check tools/host_diagnostics.py tests/test_device_inventory.py tests/test_host_diagnostics.py`:
`All checks passed!`

`python3 -m pyright tools/host_diagnostics.py`:
`0 errors, 0 warnings, 0 informations`.

The refreshed local capture remains `partial` with `could_not_run=15`, USB
inventory `ok` with 16 entries, and zero HID entries. Capture command exit was
2, consistent with the nonzero `could_not_run` count. Watchdog metadata and
Realtek binding observations remain as recorded above.

## Card disposition

- `DEBT-CLOSE-CHECK-VERIFY-USB-HID-POSTUPDATE-01`: instrumentation developed;
  no post-update real-device capture or close-check verifier.
- `DELTA-FORUM-USB-RAID-LINK-ADMISSION-01`: USB identity/speed inventory
  developed; link admission, hardware-specific compatibility, and rollback
  remain untested.
- `FEATURE-FORUM-SBSA-WATCHDOG-STATE-01`: watchdog metadata developed;
  owner remains `UNKNOWN`, and ownership, OEM compatibility, and recovery
  remain unverified.
- `FEATURE-USB-HID-POSTUPDATE-CHECK`: HID-to-USB correlation developed; this
  host exposed zero HID entries, and post-update keyboard/access testing
  remains unavailable.
- `FORUM-REALTEK-DRIVER-BINDING-01`: existing PCI binding instrumentation
  reused; package compatibility and warm/cold reboot A/B evidence remain
  unavailable.
