"""Real-evidence closure gates for hardware findings; absent captures remain unknown."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

import pytest

from tools import hardware_evidence
from tools.verify_wifi_isolation import verify as verify_wifi_isolation
from tools.verify_usb_hid_postupdate import verify as verify_usb_hid_postupdate
from tools.verify_gpu_clock_cap_ab import verify as verify_gpu_clock_cap
from tools.verify_clock_cap_tradeoff import verify as verify_clock_cap_tradeoff
from tools.forum_finding import evaluate as evaluate_forum_finding
from tools.verify_forum_finding import verify_forum_finding
from tools.apt_arm64_evidence import verify_capture as verify_apt_arm64_capture

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tasks/evidence/CLOSURE-CONTROLS-2026-10-03/hardware-batch-01.json'
CARDS = json.loads(SOURCE.read_text(encoding='utf-8'))
FORUM_IDS = [
    'FORUM-00-CX7-HOTPLUG-FAN-PROTECTION',
    'FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01',
    'FORUM-02-GX10-READ-INTEGRITY',
    'FEATURE-FORUM-SBSA-WATCHDOG-STATE-01',
    'FORUM-REALTEK-DRIVER-BINDING-01',
    'FEATURE-FORUM-GB10-RUNTIME-COMPAT-01',
    'FEATURE-FORUM-DESKTOP-SESSION-POSTUPDATE-01',
    'FORUM-00-KERNEL-INITRD-UPDATE-GATE',
    'FORUM-00-REALTEK-EEE-DIRECT-LINK',
    'FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT',
    'FEATURE-FORUM-RESCUE-RUNBOOK-01',
    'FORUM-02-PSTORE-KERNEL-REGRESSION',
    'FORUM-00-GB10-THERMAL-RESIDENCY-ADMISSION',
    'FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01',
    'FORUM-02-USB-UVC-EP0',
]


def _selector(command: str) -> str | None:
    match = re.search(r'tests/test_debt_registration_controls\.py::([A-Za-z0-9_]+)', command)
    return match.group(1) if match else None


def _assert_finding_passes(finding_id: str) -> None:
    result = hardware_evidence.verify(finding_id)
    assert result['status'] == 'pass', result
    assert result['fail'] == 0, result
    assert result['could_not_run'] == 0, result
    assert result['files'], result


def test_debt_close_check_verify_forum_finding_01() -> None:
    for finding_id in FORUM_IDS:
        _assert_finding_passes(finding_id)


def test_forum_finding_supports_every_original_id() -> None:
    for finding_id in FORUM_IDS:
        result = cast(dict[str, Any], verify_forum_finding(finding_id))
        assert result['status'] in {'pass', 'fail', 'unknown'}, (finding_id, result)
        assert result['status'] != 'fail', (finding_id, result)
        assert result['status'] == 'pass' or result['could_not_run'] > 0, (finding_id, result)


def test_debt_close_check_verify_gpu_clock_cap_ab_01() -> None:
    _assert_finding_passes('FEATURE-FORUM-GPU-CLOCK-CAP-AB-01')


def test_debt_close_check_verify_wifi_isolation_01() -> None:
    _assert_finding_passes('FEATURE-FORUM-WIFI-ISOLATION-01')


def test_debt_close_check_verify_usb_hid_postupdate_01() -> None:
    _assert_finding_passes('FEATURE-USB-HID-POSTUPDATE-CHECK')


def test_debt_close_check_verify_memory_saver_01() -> None:
    # The two source cards concern trace/4K packing; this control rejects a report-only bundle.
    for finding_id in ('FEATURE-MEMORYSAVER-02-TRAZADOR', 'FEATURE-MEMORYSAVER-04-PACKING-4K'):
        _assert_finding_passes(finding_id)


def test_delta_forum_apt_arm64_source_validation_01() -> None:
    evidence = ROOT / 'tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/commands.json'
    result = verify_apt_arm64_capture(evidence)
    assert result['status'] == 'pass', result
    assert result['fail'] == 0 and result['could_not_run'] == 0, result


def test_apt_arm64_raw_capture_preserves_missing_forum_negative() -> None:
    evidence = ROOT / 'tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/commands.json'
    result = verify_apt_arm64_capture(evidence)
    assert result['checks'] == {
        'architecture': 'pass', 'ubuntu_source': 'pass', 'effective_index': 'pass',
        'signed_index': 'pass', 'upgrade_simulation': 'pass',
        'bad_signature_negative': 'pass', 'bad_source_negative': 'unknown',
    }, result
    assert result['status'] == 'unknown' and result['could_not_run'] == 1, result


def test_apt_source_negative_classifier_rejects_archive_for_arm64(tmp_path: Path) -> None:
    source = tmp_path / 'commands.json'
    captured = json.loads((ROOT / 'tasks/evidence/DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01/commands.json').read_text(encoding='utf-8'))
    for row in captured['commands']:
        if row.get('argv') == ['cat', '/etc/apt/sources.list.d/ubuntu.sources']:
            row['stdout'] = row['stdout'].replace('ports.ubuntu.com/ubuntu-ports', 'archive.ubuntu.com/ubuntu')
    source.write_text(json.dumps(captured), encoding='utf-8')
    result = verify_apt_arm64_capture(source)
    assert result['status'] == 'fail', result
    assert result['fail'] == 1 and result['could_not_run'] == 0, result


def test_wifi_classifier_marks_local_host_failure_separately(tmp_path: Path) -> None:
    evidence = tmp_path / 'wifi'
    evidence.mkdir()
    (evidence / 'commands.json').write_text(json.dumps({
        'id': 'FEATURE-FORUM-WIFI-ISOLATION-01',
        'commands': [
            {'cmd': 'journalctl -u NetworkManager', 'exit': 0, 'stdout': 'no matching roam failure', 'stderr': ''},
            {'cmd': 'ping 127.0.0.1', 'exit': 1, 'stdout': '', 'stderr': 'host unreachable'},
            {'cmd': 'ping management', 'exit': 1, 'stdout': '', 'stderr': 'unreachable'},
        ],
    }), encoding='utf-8')
    result = verify_wifi_isolation(evidence)
    assert result['status'] == 'fail' and result['fail'] == 1, result


def test_usb_classifier_detects_unbound_attached_hid_device(tmp_path: Path) -> None:
    evidence = tmp_path / 'usb'
    evidence.mkdir()
    (evidence / 'commands.json').write_text(json.dumps({
        'id': 'FEATURE-USB-HID-POSTUPDATE-CHECK',
        'commands': [
            {'cmd': 'lsusb -t', 'exit': 0, 'stdout': 'Class=Human Interface Device, Driver=xhci-hcd', 'stderr': ''},
            {'cmd': 'lsmod', 'exit': 0, 'stdout': 'xhci_hcd 123 0', 'stderr': ''},
        ],
    }), encoding='utf-8')
    result = verify_usb_hid_postupdate(evidence)
    assert result['status'] == 'fail' and result['fail'] == 1, result


def test_gpu_clock_verifier_rejects_failed_nvidia_command(tmp_path: Path) -> None:
    evidence = tmp_path / 'gpu'
    evidence.mkdir()
    (evidence / 'commands.json').write_text(json.dumps({
        'id': 'FEATURE-FORUM-GPU-CLOCK-CAP-AB-01',
        'commands': [{'cmd': 'nvidia-smi -lgc 300,2200', 'exit': 1,
                      'stdout': '', 'stderr': 'Insufficient Permissions'}],
    }), encoding='utf-8')
    result = verify_gpu_clock_cap(evidence)
    assert result['status'] == 'fail' and result['fail'] == 1, result


def test_memory_saver_adapter_preserves_missing_evidence_as_could_not_run(tmp_path: Path) -> None:
    result = hardware_evidence.verify('FEATURE-MEMORYSAVER-02-TRAZADOR', tmp_path)
    assert result['status'] == 'unknown' and result['could_not_run'] == 1, result
    assert result['files'] and 'capture.json' in result['files'][0], result


def test_forum_gsp_preflight_is_recomputed_and_keeps_missing_negative_open(tmp_path: Path) -> None:
    source = ROOT / 'tasks/evidence/FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01'
    result = evaluate_forum_finding('FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01', source)
    assert result['status'] == 'unknown' and result['could_not_run'] == 1, result
    assert 'incident negative' in result['reason']

    tampered = tmp_path / 'gsp'
    tampered.mkdir()
    for filename in ('preflight.json', 'commands.json'):
        (tampered / filename).write_bytes((source / filename).read_bytes())
    document = json.loads((tampered / 'preflight.json').read_text(encoding='utf-8'))
    document['preflight_result'] = {'status': 'pass', 'findings': ['forged result']}
    (tampered / 'preflight.json').write_text(json.dumps(document), encoding='utf-8')
    invalid = evaluate_forum_finding('FEATURE-FORUM-GPU-GSP-BOOT-HEALTH-01', tampered)
    assert invalid['status'] == 'fail' and invalid['fail'] == 1, invalid


def test_provider_trace_fixture_controls_are_recomputed_but_not_treated_as_live_workload(tmp_path: Path) -> None:
    source = ROOT / 'tasks/evidence/FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01/provider-trace-run.json'
    result = evaluate_forum_finding('FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01', source.parent)
    assert result['status'] == 'unknown' and result['could_not_run'] == 1, result
    assert 'no real workload trace' in result['reason'], result

    tampered = tmp_path / 'provider'
    tampered.mkdir()
    document = json.loads(source.read_text(encoding='utf-8'))
    document['commands'][0]['stdout'] = '{"status":"fail","findings":["forged"],"unknowns":[],"could_not_run_count":0}'
    (tampered / source.name).write_text(json.dumps(document), encoding='utf-8')
    invalid = evaluate_forum_finding('FEATURE-FORUM-PROVIDER-FALLBACK-REGRESSION-01', tampered)
    assert invalid['status'] == 'fail' and invalid['fail'] == 1, invalid


def test_forum_pstore_requires_hash_verified_subject_and_negative_control(tmp_path: Path) -> None:
    import hashlib

    evidence = tmp_path / 'pstore'
    evidence.mkdir()
    subject = 'panic FPAC PSCI NMI kernel=6.17.0'
    negative = 'clean boot: no corrected-event markers present'
    source = 'NVIDIA supports kernel 6.17.0 for this firmware tuple'
    (evidence / 'finding.json').write_text(json.dumps({
        'schema': 1, 'id': 'FORUM-02-PSTORE-KERNEL-REGRESSION',
        'stack': {'oem': 'OEM', 'bios': '1.0', 'ec': '2.0', 'kernel': '6.17.0',
                  'driver': '570.0', 'boot_id': 'boot-123'},
        'pstore': {'boot_id': 'boot-123', 'raw_records': [
            {'content': subject, 'sha256': hashlib.sha256(subject.encode()).hexdigest()}]},
        'vendor_resolution': {'source_text': source,
            'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
            'source_url': 'https://docs.nvidia.com/example'},
        'recommendation': {'action': 'monitor', 'reason': 'matched vendor advisory'},
        'negative_control': {'content': negative,
            'sha256': hashlib.sha256(negative.encode()).hexdigest()},
    }), encoding='utf-8')
    passed = evaluate_forum_finding('FORUM-02-PSTORE-KERNEL-REGRESSION', evidence)
    assert passed['status'] == 'pass' and passed['fail'] == passed['could_not_run'] == 0, passed

    doc = json.loads((evidence / 'finding.json').read_text(encoding='utf-8'))
    doc['negative_control']['content'] += ' NMI'
    (evidence / 'finding.json').write_text(json.dumps(doc), encoding='utf-8')
    rejected = evaluate_forum_finding('FORUM-02-PSTORE-KERNEL-REGRESSION', evidence)
    assert rejected['status'] == 'fail' and rejected['fail'] == 1, rejected


def test_clock_tradeoff_reuses_thermal_inventory_but_preserves_missing_ab() -> None:
    result = verify_clock_cap_tradeoff()
    assert result['status'] == 'unknown' and result['could_not_run'] == 1, result
    assert result['checks']['thermal_inventory'] == 'pass', result
    assert result['checks']['matched_clock_runs'] == 'unknown', result


def _make_selector(finding_id: str):
    def test() -> None:
        _assert_finding_passes(finding_id)
    test.__name__ = _selector(next(x['close_check']['cmd'] for x in CARDS if x['id'] == finding_id)) or f'test_hardware_{finding_id.lower().replace("-", "_")}'
    test.__doc__ = f'Evidence gate for {finding_id}.'
    return test


# Expose selectors in this suite so the shared registration suite can re-export them.
_OWNED_IDS = set(FORUM_IDS) | {
    'FEATURE-FORUM-GPU-CLOCK-CAP-AB-01', 'FEATURE-MEMORYSAVER-02-TRAZADOR',
    'FEATURE-MEMORYSAVER-04-PACKING-4K', 'FEATURE-USB-HID-POSTUPDATE-CHECK',
    'FEATURE-FORUM-WIFI-ISOLATION-01', 'DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01',
    'DELTA-FORUM-CLOCK-CAP-TRADEOFF-AND-THERMAL-ZONE-GAP-01',
}
for _card in CARDS:
    if _card['id'] not in _OWNED_IDS:
        continue
    _name = _selector(_card['close_check']['cmd'])
    if _name and _name not in globals():
        globals()[_name] = _make_selector(_card['id'])


def test_bundle_rejects_wrong_identity_and_tampered_raw_capture(tmp_path: Path) -> None:
    bundle = tmp_path / 'bundle'
    bundle.mkdir()
    manifest = bundle / 'capture.json'
    manifest.write_text(json.dumps({'finding_id': 'OTHER', 'captures': []}), encoding='utf-8')
    wrong_subject = hardware_evidence.inspect_bundle('EXPECTED', bundle, set())
    assert wrong_subject['status'] == 'fail'

    raw = bundle / 'stdout.txt'
    raw.write_text('captured output', encoding='utf-8')
    manifest.write_text(json.dumps({
        'finding_id': 'EXPECTED',
        'captures': [{'path': 'stdout.txt', 'sha256': '0' * 64, 'claims': []}],
    }), encoding='utf-8')
    tampered = hardware_evidence.inspect_bundle('EXPECTED', bundle, set())
    assert tampered['status'] == 'fail'
    assert 'hash mismatch' in tampered['reason']


def test_bundle_marks_missing_observations_could_not_run(tmp_path: Path) -> None:
    bundle = tmp_path / 'bundle'
    bundle.mkdir()
    raw = bundle / 'stdout.txt'
    raw.write_text('read-only command output', encoding='utf-8')
    import hashlib

    manifest = bundle / 'capture.json'
    manifest.write_text(json.dumps({
        'finding_id': 'EXPECTED',
        'captures': [{'path': 'stdout.txt', 'sha256': hashlib.sha256(raw.read_bytes()).hexdigest()}],
    }), encoding='utf-8')
    missing = hardware_evidence.inspect_bundle('EXPECTED', bundle, {'observed_sensor_data'})
    assert missing['status'] == 'unknown'
    assert missing['could_not_run'] == 1
