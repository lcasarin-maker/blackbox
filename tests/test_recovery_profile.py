"""Missing evidence and an empty archive must stay distinct."""
from pathlib import Path
import runpy

import pytest

from tools import recovery_profile as profile


def test_complete_state_with_separate_signatures(tmp_path):
    for name in profile.STATE_PATHS:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('1\n', encoding="utf-8")
    device = tmp_path / 'sys/class/watchdog/watchdog0'
    device.mkdir(parents=True)
    for name in ('identity', 'state', 'status', 'timeout', 'nowayout', 'bootstatus'):
        (device / name).write_text('active', encoding="utf-8")
    archive = tmp_path / 'sys/fs/pstore'
    archive.mkdir(parents=True)
    (archive / 'dmesg-efi-1').write_text('FPAC PSCI NMI SBSA DOE RCU private detail', encoding="utf-8")
    result = profile.capture(tmp_path)
    assert result['could_not_run'] == 0
    assert result['watchdog_device_count'] == 1
    record = result['pstore']['records'][0]
    assert record['signals'] == ['FPAC', 'PSCI', 'NMI', 'SBSA', 'DOE', 'RCU']
    assert len(record['normalized_text_sha256']) == 64
    assert 'value' not in record


def test_missing_interfaces_are_counted(tmp_path):
    result = profile.capture(tmp_path)
    assert result['status'] == 'partial'
    assert result['could_not_run'] == len(profile.STATE_PATHS) + 2
    assert result['watchdog_device_count'] == 0


def test_empty_readable_pstore_is_read_not_recovery_proof(tmp_path):
    assert profile.pstore(tmp_path)['record_count'] == 0
    assert profile.pstore(tmp_path)['status'] == 'read'


def test_denied_and_binary_record(monkeypatch, tmp_path):
    file = tmp_path / 'record'
    file.write_bytes(b'\xff')
    assert profile.pstore(tmp_path)['records'][0]['status'] == 'could_not_run'
    monkeypatch.setattr(Path, 'read_text', lambda *_, **__: (_ for _ in ()).throw(PermissionError('denied')))
    assert profile.read(file)['status'] == 'could_not_run'


def test_unread_pstore_record_counts(monkeypatch, tmp_path):
    archive = tmp_path / 'sys/fs/pstore'
    archive.mkdir(parents=True)
    (archive / 'bad').write_bytes(b'\xff')
    monkeypatch.setattr(profile, 'STATE_PATHS', ())
    (tmp_path / 'sys/class/watchdog').mkdir(parents=True)
    result = profile.capture(tmp_path)
    assert result['could_not_run'] == 1


def test_cli(capsys):
    with pytest.raises(SystemExit):
        runpy.run_path(str(Path(profile.__file__)), run_name='__main__')
    assert 'could_not_run' in capsys.readouterr().out


def test_clean_cli_exit(monkeypatch, capsys):
    monkeypatch.setattr(profile, 'capture', lambda: {'could_not_run': 0})
    assert profile.main() == 0
    assert 'could_not_run' in capsys.readouterr().out
