"""Independent negative controls for phase capture input safety."""
from pathlib import Path
import os
import pytest
from tools.verify_memory_saver import verify


@pytest.mark.parametrize("raw", ['{"schema":1,"schema":2}', '{"value":NaN}', '{"value":Infinity}'])
def test_ambiguous_phase_json_is_unknown(tmp_path: Path, raw: str) -> None:
    (tmp_path / "capture.json").write_text(raw, encoding="utf-8")
    result = verify("02-trazador", tmp_path)
    assert result["status"] == "unknown"


def test_phase_fifo_and_ancestor_symlink_are_unknown(tmp_path: Path) -> None:
    os.mkfifo(tmp_path / "capture.json")
    assert verify("02-trazador", tmp_path)["status"] == "unknown"
    target = tmp_path / "real"
    target.mkdir()
    (target / "capture.json").write_text('{}', encoding="utf-8")
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    assert verify("02-trazador", link)["status"] == "unknown"


def test_unsupported_phase_rejected_before_reading(tmp_path: Path) -> None:
    os.mkfifo(tmp_path / "capture.json")
    assert verify("unsupported", tmp_path)["status"] == "fail"
