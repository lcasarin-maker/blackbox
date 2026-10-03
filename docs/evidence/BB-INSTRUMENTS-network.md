# Network instrumentation evidence — 2026-10-03

`tools.host_diagnostics` records native `ip -j link` interface fields,
sysfs MTU/carrier/operstate, and existing PCI binding data. When
`/sys/class/infiniband` exposes devices, it records PCI identity, port state,
GID/type/netdev associations, and the RDMA `fw_ver` value. Interface firmware
has no generic sysfs field in this inventory and remains `unknown`. The
instrument keeps physical attachment `UNKNOWN` and transport validation
`not_run`.

## Local captures

The focused inventory capture was produced with:

```sh
python3 -c 'import json; from pathlib import Path; from tools.host_diagnostics import network_inventory; print(json.dumps(network_inventory(Path("/")), sort_keys=True))' > tasks/evidence/BB-INSTRUMENTS-2026-10-03/network.capture.json
```

It returned exit code `0`. The inventory status is `could_not_run`: the exact
`ip -j link show` query failed with `Cannot open netlink socket: Operation not
permitted`, while sysfs enumerated 16 interfaces. Consequently all 16 are
recorded as missing from the inaccessible IP query. The RDMA sysfs directory
was enumerable and contained zero HCA entries. Physical attachment is
`UNKNOWN`; transport validation is `not_run`.

The corresponding full host diagnostics capture is preserved separately at
`tasks/evidence/BB-INSTRUMENTS-2026-10-03/network.full-capture-initial.json`.
Its command was `python3 -m tools.host_diagnostics > tasks/evidence/BB-INSTRUMENTS-2026-10-03/network.full-capture-initial.json` and returned exit code `2` with report status `partial` and `could_not_run=20`. That number counts every JSON status node carrying `could_not_run`, including aggregate and child nodes; it is not a count of independent queries. The full capture includes the pre-existing read-only `ethtool --show-eee enP7s7` query, which reported `Cannot get control socket: Operation not permitted`. No network setting was changed.

In the full capture, sysfs reported MTU 1500 on `enP7s7`; PCI binding observed BDF
`0007:01:00.0`, vendor/device `0x10ec:0x8127`, driver/module `r8127`, and module
version `11.014.00-NAPI`. The denied IP query prevents cross-checking those
records against native IP JSON. These observations do not establish cabling,
connector identity, peer connectivity, a universal MTU target, or NCCL/RDMA
workload health.

## Validation

`python3 -m pytest -q tests/test_device_inventory.py tests/test_network_inventory.py tests/test_host_diagnostics.py --cov=tools.host_diagnostics --cov-branch --cov-report=term-missing`:
`66 passed in 1.88s`; coverage reported `381 Stmts, 0 Miss, 136 Branch, 0
BrPart, 100%`.

`python3 -m ruff check tools/host_diagnostics.py tests/test_network_inventory.py tests/test_device_inventory.py tests/test_host_diagnostics.py`:
`All checks passed!`

`pyright tools/host_diagnostics.py`:
`0 errors, 0 warnings, 0 informations`. A Pyright run including test files could not resolve the `pytest` stubs in this worktree.

The five related cards remain open with their original status and `close_check`.
No host network, RDMA, firmware, or link state was changed.
