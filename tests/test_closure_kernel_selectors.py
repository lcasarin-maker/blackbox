"""Shared pass rule for close-check selectors that run production evaluators on investigation evidence.

A selector built on `_require_pass` fails while the real raw inputs are absent or
incomplete. Unit fixtures live separately (test_closure_kernel.py and friends)
and cannot turn an investigation green.

The cgroup-plan, netconsole and rcu-panic-pstore selectors that lived here were
retired on 2026-10-14 with their meta-fichas (closed as `duplicate`): each
subject ficha's own close_check runs `tools.verify_cgroup_plan`,
`tools.verify_netconsole` or `tools.verify_rcu_panic_pstore` directly.
"""
from __future__ import annotations


def _require_pass(subject: str, result: dict[str, object]) -> None:
    assert result.get("status") == "pass" and result.get("could_not_run_count") == 0, (
        f"{subject} closure remains open: {result!r}"
    )
