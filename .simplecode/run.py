#!/usr/bin/env python3
"""Run the explicitly pinned Simplecode runtime."""
import hashlib
import json
import runpy
import sys
import zipfile
from pathlib import Path

here = Path(__file__).resolve().parent
runtime = here / "runtime.zip"
lock_path = here / "kit.lock"

if not runtime.is_file():
    raise SystemExit("simplecode runtime.zip is missing; run explicit sync apply")
if not lock_path.is_file():
    raise SystemExit("simplecode kit.lock is missing; run explicit sync apply")
try:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    bundle = runtime.read_bytes()
    with zipfile.ZipFile(runtime) as zf:
        manifest = json.loads(zf.read("RUNTIME_MANIFEST.json").decode("utf-8"))
        entries = [
            (name, zf.read(name))
            for name in sorted(name for name in zf.namelist() if name.endswith((".py", ".yaml")))
        ]
except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
    raise SystemExit(f"simplecode runtime identity cannot be verified: {exc}") from exc
actual_bundle_sha = hashlib.sha256(bundle).hexdigest()
if lock.get("artifact_sha256") != actual_bundle_sha:
    raise SystemExit("simplecode runtime.zip differs from kit.lock; run explicit sync apply")
content = hashlib.sha256()
for name, data in entries:
    content.update(name.encode("utf-8"))
    content.update(data)
if manifest.get("content_sha256") != content.hexdigest():
    raise SystemExit("simplecode runtime.zip does not match its content manifest; run explicit sync apply")
if lock.get("content_sha256") != manifest.get("content_sha256"):
    raise SystemExit("simplecode runtime manifest differs from kit.lock; run explicit sync apply")
if len(sys.argv) < 2:
    raise SystemExit("usage: run.py MODULE [ARGS...]   |   run.py --version")
if sys.argv[1] in ("--version", "-V"):
    print(f"simplecode {manifest.get('simplecode_version', '?')} "
          f"(content {str(manifest.get('content_sha256', '?'))[:12]})")
    print(f"  bundle: {runtime}")
    print(f"  artifact: {actual_bundle_sha[:12]}")
    raise SystemExit(0)
module = sys.argv[1]
sys.path.insert(0, str(runtime))
sys.argv = sys.argv[1:]
runpy.run_module(module, run_name="__main__")
