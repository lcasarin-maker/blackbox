"""Close control for the pinned judge's tools/ threat-sweep scope."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_threat_sweep_reads_tools_and_rejects_injected_case(tmp_path: Path) -> None:
    """Read the real tools tree and prove homoglyph/invisible detection in it."""
    bundle = ROOT / ".simplecode/runtime.zip"
    lock = json.loads((ROOT / ".simplecode/kit.lock").read_text(encoding="utf-8"))
    assert hashlib.sha256(bundle.read_bytes()).hexdigest() == lock["artifact_sha256"]

    script = r"""
import json
import sys
from pathlib import Path
root = Path(sys.argv[1])
probe_root = Path(sys.argv[2])
sys.path.insert(0, str(root / ".simplecode/runtime.zip"))
from simplecode.verification import adversarial_judge as judge
present, absent = judge.sweep_coverage(root)
files = judge.collect_threat_sources(root)
expected = sorted(p for p in (root / "tools").rglob("*.py") if p.is_file())
observed = sorted(p for p in files if p.is_relative_to(root / "tools"))
clean = judge._audit_code_threats(root, files)
tools = probe_root / "tools"
tools.mkdir()
sample = tools / "injected.py"
sample.write_text("def s" + chr(0x435) + "nd_mail():\n    return None\n", encoding="utf-8")
injected_files = judge.collect_threat_sources(probe_root)
homoglyph = judge._audit_code_threats(probe_root, injected_files)
sample.write_text('TOOL = "send' + chr(0x200b) + '_mail"\n', encoding="utf-8")
invisible = judge._audit_code_threats(probe_root, judge.collect_threat_sources(probe_root))
print(json.dumps({
    "tools_in_scope": "tools" in present and "tools" not in absent,
    "expected_tools": len(expected),
    "observed_tools": len(observed),
    "complete_tools": expected == observed and bool(observed),
    "clean_findings": clean,
    "homoglyph_findings": homoglyph,
    "invisible_findings": invisible,
}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(ROOT), str(tmp_path)],
        cwd=ROOT, capture_output=True, text=True, timeout=10, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    verdict = json.loads(result.stdout)
    assert verdict["tools_in_scope"] is True, verdict
    assert verdict["complete_tools"] is True and verdict["observed_tools"] > 0, verdict
    assert verdict["clean_findings"] == [], verdict
    assert verdict["homoglyph_findings"] == [
        "Homoglyph / confusables detected in tools/injected.py"
    ], verdict
    assert verdict["invisible_findings"] == [
        "Invisible character threat detected in tools/injected.py"
    ], verdict
