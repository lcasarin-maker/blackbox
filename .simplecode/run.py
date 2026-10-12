#!/usr/bin/env python3
"""Run the explicitly pinned Simplecode runtime."""
import hashlib
import json
import os
import runpy
import sys
import zipfile
from pathlib import Path

# runtime-resolver:v1 -- the hook preamble reads this marker: a runner that
# carries it finds and verifies its own runtime.zip, so a clone with a
# tracked run.py + kit.lock and no zip is not a hook-level COULD_NOT_RUN.
here = Path(__file__).resolve().parent
lock_path = here / "kit.lock"


def refuse(message):
    print(f"[simplecode] COULD_NOT_RUN: {message}", file=sys.stderr)
    raise SystemExit(2)


if not lock_path.is_file():
    refuse("kit.lock is missing; run explicit sync apply")
try:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
except (OSError, ValueError) as exc:
    refuse(f"kit.lock cannot be read: {exc}")
wanted = str(lock.get("artifact_sha256"))
cache_root = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "simplecode"
cached = cache_root / wanted / "runtime.zip"
mother = Path(os.environ.get("SIMPLECODE_MOTHER") or Path.home() / "projects" / "simplecode")
# Only a bundle whose sha256 IS the lock's is ever imported; the order is
# local copy, the cache `sync` fills, then the mother checkout.
runtime = None
tried = []
for candidate in (here / "runtime.zip", cached, mother / ".simplecode" / "runtime.zip"):
    try:
        bundle = candidate.read_bytes()
    except OSError:
        tried.append(f"{candidate} (absent)")
        continue
    if hashlib.sha256(bundle).hexdigest() == wanted:
        runtime = candidate
        break
    tried.append(f"{candidate} (sha256 differs from kit.lock)")
if runtime is None:
    refuse(f"no runtime.zip matches kit.lock artifact_sha256 {wanted}; tried: " + "; ".join(tried)
           + "; run explicit sync apply")
if runtime != cached:
    try:
        cached.parent.mkdir(parents=True, exist_ok=True)
        partial = cached.with_name(f"runtime.zip.{os.getpid()}")
        partial.write_bytes(bundle)
        os.replace(partial, cached)
    except OSError as exc:  # ponytail: cache is best-effort, the verified bundle already runs; trigger: a satellite whose only copy is the mother's and the mother moves
        print(f"[simplecode] runtime cache not written ({cached}): {exc}", file=sys.stderr)
try:
    with zipfile.ZipFile(runtime) as zf:
        manifest = json.loads(zf.read("RUNTIME_MANIFEST.json").decode("utf-8"))
        entries = [
            (name, zf.read(name))
            for name in sorted(name for name in zf.namelist() if name.endswith((".py", ".yaml")))
        ]
except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
    refuse(f"runtime identity cannot be verified: {exc}")
actual_bundle_sha = wanted
content = hashlib.sha256()
for name, data in entries:
    content.update(name.encode("utf-8"))
    content.update(data)
if manifest.get("content_sha256") != content.hexdigest():
    refuse("runtime.zip does not match its content manifest; run explicit sync apply")
if lock.get("content_sha256") != manifest.get("content_sha256"):
    refuse("runtime manifest differs from kit.lock; run explicit sync apply")
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
