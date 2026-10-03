"""Injected-failure controls for the repo's SPEC and ledger-preservation hooks."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / ".simplecode" / "run.py"


def _run(module: str, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), module, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )


def test_spec_check_passes_then_rejects_missing_objective(tmp_path: Path) -> None:
    (tmp_path / "SPEC.md").write_text(
        """# Sample specification

## 0. Objective
**Mission**: Verify the native SPEC checker.

## Purpose
Keep the policy explicit.

## Why now
The hook claims to enforce required sections.

## Who is the user
A repository maintainer.

## In scope
- Validate the specification structure.

## Out of scope
- Deploy the application.

## Python version
Python 3.12.

## Deployment target
A local repository.

## ADRs
| ADR | Status |
| --- | --- |
| 0001 | Accepted |

## Risks
| Risk | Likelihood |
| --- | --- |
| Missing requirement | Low |

## Acceptance Criteria
- The native check passes valid content.
""",
        encoding="utf-8",
    )
    good = _run("simplecode.cli_spec", "check", cwd=tmp_path)
    assert good.returncode == 0, good.stdout + good.stderr
    assert "All checks passed" in good.stdout

    spec = tmp_path / "SPEC.md"
    spec.write_text(spec.read_text(encoding="utf-8").replace("## 0. Objective\n", ""), encoding="utf-8")
    bad = _run("simplecode.cli_spec", "check", cwd=tmp_path)
    assert bad.returncode == 1, bad.stdout + bad.stderr
    assert "FAIL Objective" in bad.stdout
    assert "[spec-check] FAIL" in bad.stdout


def test_no_perder_lineas_passes_then_rejects_deleted_tracked_lines(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    entry = tmp_path / "tasks" / "backlog" / "probe.md"
    entry.parent.mkdir(parents=True)
    entry.write_text("one\ntwo\nthree\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "tasks/backlog/probe.md"], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "-c", "user.name=Control Test", "-c",
         "user.email=control@example.invalid", "commit", "-qm", "baseline"],
        check=True,
    )
    good = _run("simplecode.verification.no_perder_lineas", "--root", str(tmp_path), cwd=tmp_path)
    assert good.returncode == 0, good.stdout + good.stderr
    assert "candidatas=1 revisadas=1 pierden=0 could_not_run=0" in good.stdout

    entry.write_text("one\ntwo\n", encoding="utf-8")
    bad = _run("simplecode.verification.no_perder_lineas", "--root", str(tmp_path), cwd=tmp_path)
    assert bad.returncode == 1, bad.stdout + bad.stderr
    assert "pierden=1" in bad.stdout
    assert "[no-perder-lineas] FAIL" in bad.stdout
