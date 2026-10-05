"""Close-check selectors run the production evaluators on investigation evidence.

These selectors intentionally fail while the real raw inputs are absent or
incomplete. Unit fixtures live separately in test_closure_kernel.py and cannot
turn an investigation green.
"""
from __future__ import annotations

import json
from pathlib import Path

from tools.verify_cgroup_plan import verify as verify_cgroup
from tools.verify_cgroup_repro import verify as verify_cgroup_repro
from tools.verify_netconsole import verify as verify_netconsole
from tools.verify_rcu_panic_pstore import verify as verify_rcu

ROOT = Path(__file__).resolve().parents[1]


def _require_pass(subject: str, result: dict[str, object]) -> None:
    assert result.get("status") == "pass" and result.get("could_not_run_count") == 0, (
        f"{subject} closure remains open: {result!r}"
    )


Outcome = tuple[str, dict[str, object]]


def open_closures(outcomes: list[Outcome]) -> list[Outcome]:
    """The (subject, result) pairs that are not a clean pass with zero could_not_run."""
    return [
        (subject, result)
        for subject, result in outcomes
        if not (result.get("status") == "pass" and result.get("could_not_run_count") == 0)
    ]


def closure_selector_cgroup_plan_01() -> list[Outcome]:
    repro_path = ROOT / "tasks/evidence/FEATURE-1358-CGROUP-01-REPRO/run-profile-integration.json"
    outcomes: list[Outcome] = [
        ("FEATURE-1358-CGROUP-01-REPRO",
         verify_cgroup_repro(json.loads(repro_path.read_text(encoding="utf-8")))),
    ]
    phases = (
        ("02-traza", "FEATURE-1358-CGROUP-02-TRAZA"),
        ("03-nativo", "FEATURE-1358-CGROUP-03-NATIVO"),
        ("04-parche", "FEATURE-1358-CGROUP-04-PARCHE"),
        ("05-cuelgues", "FEATURE-1358-CGROUP-05-CUELGUES"),
    )
    for phase, evidence_id in phases:
        outcomes.append((f"{evidence_id}/{phase}",
                         verify_cgroup(phase, ROOT / "tasks" / "evidence" / evidence_id)))
    return outcomes


def closure_selector_netconsole_01() -> list[Outcome]:
    return [("FEATURE-FORUM-NETCONSOLE-01",
             verify_netconsole(ROOT / "tasks/evidence/FEATURE-FORUM-NETCONSOLE-01"))]


def closure_selector_rcu_panic_pstore_01() -> list[Outcome]:
    return [("FEATURE-FORUM-RCU-PANIC-PSTORE-01",
             verify_rcu(ROOT / "tasks/evidence/FEATURE-FORUM-RCU-PANIC-PSTORE-01"))]

