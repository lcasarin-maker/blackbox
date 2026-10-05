from __future__ import annotations

import json
from pathlib import Path

from tools.hardware_evidence import verify
from tools.verify_forum_finding import verify_forum_finding
from tools.hardware_batch02_controls import IDS as BATCH02_IDS
from tools.hardware_batch03_controls import CARD_IDS as BATCH03_IDS

ROOT = Path(__file__).resolve().parents[1]


def _ids(name: str) -> list[str]:
    document = json.loads((ROOT / "tasks/evidence/CLOSURE-CONTROLS-2026-10-03" / name).read_text(encoding="utf-8"))
    return [row["id"] for row in document]


def test_every_generated_batch02_id_routes_to_raw_predicate(tmp_path: Path) -> None:
    generated = _ids("hardware-batch-02.json")
    assert tuple(generated) == BATCH02_IDS
    for finding_id in generated:
        result = verify(finding_id, tmp_path / finding_id)
        assert result["status"] == "unknown", (finding_id, result)
        assert result["could_not_run"] == 1, (finding_id, result)
        assert "commands.json" in result["files"][0]


def test_every_generated_batch03_id_routes_to_domain_predicate(tmp_path: Path) -> None:
    generated = _ids("hardware-batch03-kernel-executor.json")
    assert set(generated) == BATCH03_IDS
    for finding_id in generated:
        result = verify_forum_finding(finding_id, tmp_path / finding_id)
        assert result["status"] == "unknown", (finding_id, result)
        assert result["could_not_run"] == 1, (finding_id, result)
        assert "raw card capture unavailable" in str(result["reason"])


def test_unregistered_forum_id_remains_rejected(tmp_path: Path) -> None:
    result = verify_forum_finding("DELTA-FORUM-NOT-A-REAL-FINDING", tmp_path)
    assert result["status"] == "fail"
    assert result["fail"] == 1


def test_manifest_reader_rejects_duplicate_keys_and_nonfinite_constants(tmp_path: Path) -> None:
    from tools.hardware_evidence import _load_manifest

    manifest = tmp_path / "capture.json"
    for text in (
        '{"finding_id":"subject","finding_id":"other","captures":[{"path":"raw.txt"}]}',
        '{"finding_id":"subject","captures":[{"path":"raw.txt","value":NaN}]}',
    ):
        manifest.write_text(text, encoding="utf-8")
        loaded, error = _load_manifest(manifest, "subject")
        assert loaded is None and error is not None and error["status"] == "fail"


def test_manifest_reader_rejects_fifo_and_symlink_without_blocking(tmp_path: Path) -> None:
    import os

    from tools.hardware_evidence import _load_manifest

    fifo = tmp_path / "capture.json"
    os.mkfifo(fifo)
    loaded, error = _load_manifest(fifo, "subject")
    assert loaded is None and error is not None and error["status"] == "fail"

    source = tmp_path / "source.json"
    source.write_text('{"finding_id":"subject","captures":[]}', encoding="utf-8")
    link = tmp_path / "capture-link.json"
    link.symlink_to(source)
    loaded, error = _load_manifest(link, "subject")
    assert loaded is None and error is not None and error["status"] == "fail"


def test_apt_arm64_route_preserves_exact_domain_gate_count(tmp_path: Path) -> None:
    finding_id = "DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01"
    hardware = verify(finding_id, tmp_path / finding_id)
    forum = verify_forum_finding(finding_id, tmp_path / finding_id)
    assert hardware["status"] == "unknown" and hardware["could_not_run"] == 12
    assert hardware["fail"] == 0 and hardware["criteria_unimplemented"]
    assert forum["status"] == "unknown" and forum["could_not_run"] == 12
    assert forum["fail"] == 0 and forum["criteria_unimplemented"]


def test_capture_inventory_uses_bounded_regular_nofollow_reads(tmp_path: Path, monkeypatch) -> None:
    import hashlib
    import os

    from tools import hardware_evidence

    evidence = tmp_path / "evidence"
    evidence.mkdir()
    manifest = evidence / "capture.json"
    target = evidence / "raw.txt"
    target.write_text("raw payload", encoding="utf-8")
    row = {"path": "raw.txt", "sha256": hashlib.sha256(b"raw payload").hexdigest()}
    _, files, error = hardware_evidence._capture_files(evidence, manifest, [row])
    assert error is None and str(target) in files

    outside = tmp_path / "outside.txt"
    outside.write_text("raw payload", encoding="utf-8")
    link = evidence / "linked.txt"
    link.symlink_to(outside)
    _, _, error = hardware_evidence._capture_files(
        evidence, manifest, [{"path": "linked.txt", "sha256": row["sha256"]}])
    assert error is not None and error["status"] == "fail"

    fifo = evidence / "pipe.txt"
    os.mkfifo(fifo)
    _, _, error = hardware_evidence._capture_files(
        evidence, manifest, [{"path": "pipe.txt", "sha256": row["sha256"]}])
    assert error is not None and error["status"] == "fail"

    monkeypatch.setattr(hardware_evidence, "MAX_CAPTURE_BYTES", 4)
    _, _, error = hardware_evidence._capture_files(
        evidence, manifest, [{"path": "raw.txt", "sha256": row["sha256"]}])
    assert error is not None and "8 MiB" in error["reason"]
