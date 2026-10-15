"""Last uncovered line of forum_hardware_subjects: the non-finite compute-app memory guard."""
from __future__ import annotations

from tools import forum_hardware_subjects as subjects
from tools.forum_hardware_subjects import _parse_compute_app


def test_parse_compute_app_rejects_memory_that_overflows_to_infinity() -> None:
    # 400 digits parse to float inf; int(inf * 1024 * 1024) would raise OverflowError.
    assert _parse_compute_app("123, python3, " + "9" * 400 + " MiB") is None


def test_parse_compute_app_accepts_finite_memory() -> None:
    assert _parse_compute_app("123, python3, 2 MiB") == {
        "pid": 123, "name": "python3", "bytes": 2 * 1024 * 1024}


def test_a_subject_with_required_cases_but_no_check_fails_with_a_reason_instead_of_a_keyerror(monkeypatch, tmp_path):
    # IDS/REQUIRED extended without its CHECKS entry: the verdict must be a reasoned "fail", not an unhandled KeyError.
    monkeypatch.setitem(subjects.REQUIRED, "FORUM-99-NO-CHECK", {})
    assert subjects._evaluate_simple({}, "FORUM-99-NO-CHECK", tmp_path) == ("fail", "unsupported subject predicate")
