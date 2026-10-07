"""Non-expiring signed InRelease canary for tools.apt_sources.verify_release_signature.

Why it exists: the first canary (DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/signed-integrity-canary)
was signed by a key generated with a 1-day expiry (`--quick-generate-key ... sign 1d`). Since
2026-10-05T06:10:41Z gpgv reports EXPKEYSIG for it and the verifier correctly blocks, so a test
that expected `pass` from it became a time bomb. That canary is kept untouched (other ledgers pin
its hashes) and now serves as the expired-key negative control.

This canary uses `never` as key expiry and omits Valid-Until: it authenticates bytes only;
freshness is a separate gate. The private key lives only in a temporary GPG home that is removed
on exit. Run from the repo root:
    python3 tasks/evidence/DEBT-PRUEBAS-SIN-FICHA-CRUDA-01/signature-canary/collect_signature_canary.py
"""
from __future__ import annotations

import datetime
import email.utils
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

OUT = Path(__file__).resolve().parent


def main() -> int:
    rows: list[dict] = []

    def run(argv: list[str]) -> subprocess.CompletedProcess:
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        result = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        rows.append({"argv": argv, "started_at": started, "exit_code": result.returncode,
                     "stdout": result.stdout, "stderr": result.stderr})
        return result

    with tempfile.TemporaryDirectory(prefix="bb-apt-signature-canary-") as directory:
        root = Path(directory)
        home = root / "gpg"
        home.mkdir(mode=0o700)
        prefix = ["gpg", "--homedir", str(home), "--batch", "--pinentry-mode", "loopback", "--passphrase", ""]
        assert run(prefix + ["--quick-generate-key", "BB APT signature canary", "rsa2048", "sign", "never"]).returncode == 0
        keyring = root / "keyring.gpg"
        assert run(prefix + ["--output", str(keyring), "--export"]).returncode == 0
        package = (b"Package: bb-canary\nVersion: 1\nArchitecture: arm64\nMaintainer: BB canary\n"
                   b"Description: signature canary\nFilename: bb-canary.deb\nSize: 0\nSHA256: " + b"0" * 64 + b"\n\n")
        now = datetime.datetime.now(datetime.timezone.utc)
        release = ("Origin: BB signature canary\nLabel: BB signature canary\nSuite: canary\nCodename: canary\n"
                   f"Date: {email.utils.format_datetime(now, usegmt=True)}\nArchitectures: arm64\nSHA256:\n"
                   f" {hashlib.sha256(package).hexdigest()} {len(package)} Packages\n")
        (root / "Release").write_text(release, encoding="utf-8")
        assert run(prefix + ["--armor", "--output", str(root / "InRelease"), "--clearsign", str(root / "Release")]).returncode == 0
        (OUT / "canary-public-keyring.gpg").write_bytes(keyring.read_bytes())
        (OUT / "baseline.InRelease").write_bytes((root / "InRelease").read_bytes())
        (OUT / "baseline.Packages").write_bytes(package)
        temporary_root = directory
    recheck_home = tempfile.mkdtemp(prefix="bb-apt-signature-recheck-")
    recheck = run(["gpgv", "--homedir", recheck_home, "--status-fd=1", "--keyring",
                   str(OUT / "canary-public-keyring.gpg"), str(OUT / "baseline.InRelease")])
    subprocess.run(["rm", "-r", recheck_home], check=True)
    report = {
        "scope": "Temporary key, never-expiring, private half destroyed with its GPG home; signs bytes only.",
        "temporary_root": temporary_root, "temporary_root_removed": not Path(temporary_root).exists(),
        "commands": rows,
        "sha256": {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest()
                   for name in ("canary-public-keyring.gpg", "baseline.InRelease", "baseline.Packages")},
    }
    (OUT / "run.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ok = recheck.returncode == 0 and "VALIDSIG" in recheck.stdout and "EXPKEYSIG" not in recheck.stdout
    print(json.dumps({"archived_recheck_ok": ok, "sha256": report["sha256"]}, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
