# Hardware generated-batch routing manifest

The dispatcher in `tools/hardware_evidence.py` resolves generated membership through evaluator ID constants before generic evidence inventory, then imports only the matching verifier. `tools/verify_forum_finding.py` admits exact generated IDs through `is_generated_control_id`; existing forum IDs keep their current evaluator and unsupported IDs remain rejected.

| Generated source | Verifier | Capture contract | Current dependency |
| --- | --- | --- | --- |
| `hardware-batch-02.json` | `tools.hardware_batch02_controls.verify(id, directory)` | `commands.json`; native command rows; `unknown` when raw observations are missing | `tools.apt_sources.verify_release_signature` |
| `hardware-batch03-kernel-executor.json` | `tools.hardware_batch03_controls.verify(id, path)` | `capture.json`; bounded observations and hash-consistency receipts; `unknown` when evidence is missing | `tools.hitos_incidente._journal_time` in this WT revision |
| Legacy manifest/raw-reference reads | `tools.hardware_evidence` | `capture.json` and relative raw files; O_NOFOLLOW regular-file reads, strict JSON, 8 MiB bound | `tools.capture_io` (SHA listed below) |

`tests/test_hardware_batch_routes.py` compares source-generated IDs with each verifier's supported set and verifies every source row reaches its specific predicate. It also checks that an arbitrary ID remains rejected, and verifies legacy manifest readers reject FIFOs, symlinks, duplicate keys, and nonfinite constants. Root primary has advanced its Batch03 evaluator to a capture_io-backed revision; this WT intentionally retains the earlier exact dependency copy until root coordinates replacing it.

Current exact inputs and implementation hashes:

```text
9d68e373cd3f4b97962ee365d6d480f6c3e16848058f43f13e03eac1c0e4f5c5  hardware-batch-02.json
3190b62f924e95952c6b3ef7ebd29df8a1b751dc41873cbe4dd69c5f852e5e2f  hardware-batch03-kernel-executor.json
ef7f954e9f2a7945082ab7f38b4543bc97fc6ac1bb8056997b2d9807fea853da  hardware_batch02_controls.py
12f14f4305e35d861b70e71a7f5790172e0262c43316aff8b18cc351edde9a10  test_hardware_batch02_controls.py
a36c2d769ec9d99ec0a300428217903cfef953cffd872d84e3b2eb78efc50ef3  hardware_batch03_controls.py
c6539c8c43fbcbbcf754acab118e8c822cb5912e66dff6fc3d59da2e5c99a7f9  test_hardware_batch03_controls.py
e1ea761f00ff1d1127b25da780e6fea3c1856d335bcc74f05262e6de6b20ba4c  hardware_evidence.py
a07f49b5020661be75321266afd7f1e3fd48989aa702f88d35d0e8ed23eada63  verify_forum_finding.py
bfd4ed34ccff13c190da9b0f258c53a75e84df237b1c2b9a0739f503475ac370  capture_io.py (root-owned exact-SHA dependency)
a59113a93b9630c5cf33ce57278824842f1ff9398c8473b10aff3bf74b3e87fa  apt_sources.py (root-owned exact-SHA dependency)
e1ea761f00ff1d1127b25da780e6fea3c1856d335bcc74f05262e6de6b20ba4c  hardware_evidence.py
a07f49b5020661be75321266afd7f1e3fd48989aa702f88d35d0e8ed23eada63  verify_forum_finding.py
bfd4ed34ccff13c190da9b0f258c53a75e84df237b1c2b9a0739f503475ac370  capture_io.py (root-owned exact-SHA dependency)
0f15006e02e1940b207285a3b2bc2637e9b9b1160304853260a861417ae46f0a  test_hardware_batch_routes.py
187310f7d606a55851533008a9a2acf1c7949c2787e9eafe4644df0a78bc290d  /tmp/bb-controls-hardware-batch02-verdict.json
5f8f7c15f8800ee03d7ea60fed5a9e2131328c7b3b1be379cb0cfe42a97e2bdd  hardware_batch03_controls.py (root primary latest; not copied into this WT)
e55edadebb74dc010a1ceb56a092f894cbdb240047d41ed5fe295aa3e2af6bb6  test_hardware_batch03_controls.py (root primary latest; not copied into this WT)
```

The 17 generated findings in this WT return `unknown` against absent captures (10 Batch02 + 7 Batch03); routing does not close their subjects. Batch02 has 124 tests, Ruff clean, Pyright 0 errors/warnings/informations, and 100% scoped statement/branch coverage (wave53). Its ten evaluators implement native command parsers and criteria-specific negatives; primary captures and human trust anchors remain CNR. Combined Batch02, route, and this WT’s Batch03 tests report 174 PASS; Ruff/Pyright pass. The root-primary Batch03 evaluator is newer than this WT copy; root reports its 44-test suite and shared reader at 100% scoped coverage. Root-owned APT ARM64 routing is explicitly held at `unknown` pending its signed-source evaluator. No finding closure is claimed; hardware, workload, topology, soak, recovery, and rollback observations remain outstanding.
