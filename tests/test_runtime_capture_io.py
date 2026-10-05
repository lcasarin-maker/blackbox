"""Shared file-input regressions for every runtime evidence batch."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from tools import (
    runtime_batch01_controls,
    runtime_batch02_controls,
    runtime_batch03_controls,
    runtime_batch04_controls,
)
from tools.capture_io import read_regular_bytes
from test_runtime_batch02_controls import _base


CASES = (
    (runtime_batch01_controls, "DELTA-FORUM-3NODE-NCCL-IMAGE-AND-FIRST-REQUEST-01"),
    (runtime_batch02_controls, "DELTA-FORUM-GPTOSS-MULTINODE-RAY-CHANNEL-TIMEOUT-01"),
    (runtime_batch03_controls, "DELTA-FORUM-QWEN-LONG-AGENT-STOP-01"),
    (runtime_batch04_controls, "DELTA-ROOT-DSML-PARSER-RECOVERY-BOUNDARY-01"),
)


@pytest.mark.parametrize(("module", "card"), CASES)
def test_each_runtime_reader_accepts_regular_file_and_rejects_ambiguous_json(
    tmp_path: Path, module, card: str
) -> None:
    capture = tmp_path / "capture.json"
    capture.write_text("{}", encoding="utf-8")
    baseline = module.verify(card, capture)
    assert baseline["status"] == "unknown" and baseline["could_not_run"] == 1
    assert "raw capture unavailable" not in baseline["reason"]

    for malformed in ('{"sample":1,"sample":2}', '{"sample":NaN}'):
        capture.write_text(malformed, encoding="utf-8")
        result = module.verify(card, capture)
        assert result["status"] == "unknown" and result["could_not_run"] == 1
        assert "raw capture unavailable" in result["reason"]


@pytest.mark.parametrize(("module", "card"), CASES)
def test_each_runtime_reader_rejects_fifo_without_waiting_for_writer(
    tmp_path: Path, module, card: str
) -> None:
    fifo = tmp_path / "capture.fifo"
    os.mkfifo(fifo)
    script = (
        "import json,sys; from pathlib import Path; "
        f"from tools import {module.__name__.rsplit('.', 1)[-1]} as m; "
        f"print(json.dumps(m.verify({card!r}, Path(sys.argv[1]))))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, str(fifo)],
        capture_output=True,
        text=True,
        timeout=2,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["status"] == "unknown" and result["could_not_run"] == 1
    assert "regular file" in result["reason"]


@pytest.mark.parametrize(("module", "card"), CASES)
def test_each_runtime_reader_rejects_ancestor_symlink(
    tmp_path: Path, module, card: str
) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    capture = actual / "capture.json"
    capture.write_text("{}", encoding="utf-8")
    alias = tmp_path / "alias"
    alias.symlink_to(actual, target_is_directory=True)

    result = module.verify(card, alias / capture.name)
    assert result["status"] == "unknown" and result["could_not_run"] == 1
    assert "raw capture unavailable" in result["reason"]


@pytest.mark.parametrize(("module", "card"), CASES)
def test_unsupported_card_is_rejected_before_opening_capture(
    tmp_path: Path, module, card: str
) -> None:
    fifo = tmp_path / "unsupported.fifo"
    os.mkfifo(fifo)
    result = module.verify("unsupported-card", fifo)
    assert result["status"] == "unknown" and result["could_not_run"] == 1
    assert "no batch-" in result["reason"]


@pytest.mark.parametrize(("module", "card"), CASES)
def test_all_runtime_batches_reject_malformed_subject_and_version_tuples(
    module, card: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(module._VALIDATORS, card, lambda _document: None)
    valid = _base(card)
    baseline = module.assess(card, valid)
    assert baseline["status"] == "pass", baseline

    mutations = (
        lambda doc: doc["subject"].update(oem=42),
        lambda doc: doc["subject"].update(host_id=[]),
        lambda doc: doc["subject"].update(model={"alias": "forged"}),
        lambda doc: doc["subject"].update(software_versions=42),
        lambda doc: doc["subject"].update(software_versions={"engine": 42}),
        lambda doc: doc["subject"].update(software_versions={"": "version"}),
        lambda doc: doc["subject"].update(software_versions={}),
    )
    for mutate in mutations:
        malformed = json.loads(json.dumps(valid))
        mutate(malformed)
        result = module.assess(card, malformed)
        assert result["status"] == "unknown", result
        assert "subject." in result["reason"], result


def test_shared_reader_rejects_invalid_bound_and_parent_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="non-negative"):
        read_regular_bytes(tmp_path / "capture.json", -1)
    with pytest.raises(OSError, match="parent traversal"):
        read_regular_bytes(tmp_path / ".." / "capture.json", 10)
