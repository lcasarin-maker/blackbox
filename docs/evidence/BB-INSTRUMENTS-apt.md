# APT and OTA instrument work (2026-10-03)

`tools/apt_sources.py` now reads only the live `/etc/apt/sources.list.d/ubuntu.sources`, obtains the native package architecture, enumerates effective APT index tuples through `apt-get indextargets`, and projects the existing `memory_profile` observations into a DGX OS / OTA / kernel / loaded-driver / on-disk-driver tuple. It uses `tools.host_diagnostics.run_readonly` for fixed, bounded commands. It does not change the host.

For binary `deb` sources, the diagnostic blocks the observed exact pair `archive.ubuntu.com` + `/ubuntu` + `arm64`. It excludes `Enabled: no` and source-only `deb-src` entries, matches URI hostname and path exactly, redacts URI credentials and query data, and preserves unknown mirrors as unassessed. The report reads just `ubuntu.sources`; effective `indextargets` includes the available APT index inventory, while non-ports endpoints are explicitly listed as unassessed. The output status is `observed`, never `pass`, absent a specific detected contradiction. OTA values carry `provenance unverified` and `support_verdict: not evaluated`.

The live read-only capture is [apt-sources-capture.json](../../tasks/evidence/BB-INSTRUMENTS-2026-10-03/apt-sources-capture.json). Command: `python3 -m tools.apt_sources > tasks/evidence/BB-INSTRUMENTS-2026-10-03/apt-sources-capture.json`; exit code: `0`. The capture reports `status=observed`, `could_not_run_count=0`, native architecture `arm64`, 54 distinct effective tuples, zero malformed source URIs, and 26 unassessed effective index tuples. It preserves the per-target records in `captured_index_targets` (including duplicate target records) and strips URI authentication/query data. Its one parsed Ubuntu source stanza expands into four `ports.ubuntu.com/ubuntu-ports` suite tuples. The observed OTA tuple is DGX SW build `7.2.3`, OTA `7.6.0`, kernel `6.17.0-1032-nvidia`, loaded and on-disk driver `580.178.04`, with their observed equality. This is an inventory, not a support verdict.

The previous read-only APT capture [commands.json](../../tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/commands.json) preserves these exact signature checks:

- `gpgv --keyring /usr/share/keyrings/ubuntu-archive-keyring.gpg /var/lib/apt/lists/ports.ubuntu.com_ubuntu-ports_dists_noble-updates_InRelease` returned `0`; stderr records `Good signature from "Ubuntu Archive Automatic Signing Key (2018) <redacted-contact>"`.
- A temporary copy with a modified signed `Suite` field returned `1`; stderr records `BAD signature`.

Those results apply to that captured InRelease object and keyring. The current tool does not verify signatures, freshness, all configured source files, mirror synchronization, package provenance, OEM support, or a kernel/driver compatibility matrix. The changed-suite negative is a parser-adjacent cryptographic control, not a reproduction of the forum's incompatible-source failure.

Validation output from the bundled Python environment:

```text
$ python3 -m pytest -q tests/test_apt_sources.py
...............                                                          [100%]
15 passed in 0.07s

$ python3 -m ruff check tools/apt_sources.py tests/test_apt_sources.py
All checks passed!

$ python3 -m pyright tools/apt_sources.py
0 errors, 0 warnings, 0 informations

$ python3 -m coverage run --branch --source=tools.apt_sources -m pytest -q tests/test_apt_sources.py && python3 -m coverage report -m
...............                                                          [100%]
15 passed in 0.11s
Name                   Stmts   Miss Branch BrPart  Cover   Missing
------------------------------------------------------------------
tools/apt_sources.py     186      0     76      0   100%
------------------------------------------------------------------
TOTAL                    186      0     76      0   100%
```

`could_not_run > 0` remains non-clean by construction: file access, architecture, command failures, incomplete tuples, malformed URIs, and truncated command output stay visible and increment the printed count. Unit controls cover malformed Deb822, an exact arm64 endpoint mismatch, a URL-host spoof, disabled/source-only stanzas, credentials, malformed URIs and tuples, inaccessible reads, failed commands, and truncation.

The five cards retain `status: open` and their existing `close_check` values. The instrument work does not reproduce an actual source failure, an OTA compatibility failure, an APT recovery path, or a desktop-login failure.

## Controles tardíos de rutas de URI — 2026-10-03

Se añadieron controles de `apt-get indextargets` para URI HTTPS sin hostname, URI sin esquema y endpoint IPv6 con puerto, credenciales y query efímeras. Las dos URI inválidas producen errores sin conservar la URI; la URI válida retiene `https://[2001:db8::7]:8443/ubuntu` y descarta usuario, password y query. No se cambió código de producción.

Comando focal conjunto literal: `python3 -m coverage run --branch --source=tools.apt_sources,tools.kernel_capture -m pytest -q tests/test_apt_sources.py tests/test_kernel_capture.py` → `32 passed in 0.23s`.

Cobertura literal: `python3 -m coverage report -m --include='tools/apt_sources.py,tools/kernel_capture.py'` → `tools/apt_sources.py 186 0 76 0 100%`; `tools/kernel_capture.py 96 0 26 0 100%`; total `282 statements, 0 missed, 102 branches, 0 partial, 100%`.

`python3 -m ruff check tools/apt_sources.py tests/test_apt_sources.py tools/kernel_capture.py tests/test_kernel_capture.py` → `All checks passed!`. `python3 -m pyright tools/apt_sources.py tools/kernel_capture.py` → `0 errors, 0 warnings, 0 informations`. Intentar incluir tests en Pyright: `python3 -m pyright tools/apt_sources.py tests/test_apt_sources.py tools/kernel_capture.py tests/test_kernel_capture.py` → error explícito `Import "pytest" could not be resolved` en `tests/test_apt_sources.py:9`; Pyright sí pasa para los dos módulos de producción. No se ocultó ni excluyó el resultado fallido.

Gate literal: `python .simplecode/run.py simplecode.worktree.zero_debt --root . --mode zero --gate` → `[zero-debt] files scanned: 86 findings: 0 files with findings: 0`; `PASSED=86 CONVICTED=0 EXEMPT_CORPUS=0 EXEMPT_FIXTURE=0 EXEMPT_VENDORED=0 COULD_NOT_RUN=0`; `could_not_run: 0`; `violations: 0`; exit `0`.
