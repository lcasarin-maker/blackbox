from __future__ import annotations

import copy
import json
from pathlib import Path
import runpy

import pytest

from tools import verify_cgroup_repro as subject


@pytest.fixture
def capture():
    """Synthetic complete observation set: never claimed as a host result."""
    runs = []
    for api, worker in subject.APIS.items():
        phases = ['before']
        if worker not in ('none', 'cpu_touch'):
            phases.append('before_allocation')
        phases.append('held')
        if worker == 'pytorch_empty':
            phases.append('allocator_cache_released')
        phases.append('after_release')
        rows = []
        for timestamp, phase in enumerate(phases, 1):
            current = 1048576 if api == 'cpu_touch' and phase == 'held' else 0
            rows.append(dict(phase=phase, pid=1, monotonic_ns=timestamp,
                             cgroup_path='/sys/fs/cgroup/'+api+'.scope',
                             proc_cgroup_error=None, mem_available_error=None,
                             host_memory_pressure_error=None,
                             requested_bytes=0 if api == 'none' else 1048576,
                             files={name: {'value': str(current) if name == 'memory.current' else '0', 'error': None}
                                    for name in ['memory.current', 'memory.events', 'memory.pressure', 'dmem.current']}))
        runs.append(dict(api=api, worker_api=worker, unit=api, requested_mib=1,
                         returncode=0, stdout='\n'.join(json.dumps(row) for row in rows)))
    return dict(schema=1, host={'boot_id': 'fixture'}, runs=runs)


def change_rows(capture, mutate):
    rows = [json.loads(line) for line in capture['runs'][1]['stdout'].splitlines()]
    mutate(rows)
    capture['runs'][1]['stdout'] = '\n'.join(json.dumps(row) for row in rows)


def test_complete_observations(capture):
    result = subject.verify(capture)
    assert result['status'] == 'pass'
    assert result['could_not_run_count'] == 0
    assert len(result['rows']) == 6


@pytest.mark.parametrize('mutate', [
    lambda x: x.update(schema=2),
    lambda x: x['host'].update(boot_id=''),
    lambda x: x['runs'].pop(),
    lambda x: x['runs'][0].update(worker_api='cuda_malloc'),
    lambda x: x['runs'][0].update(returncode=1),
    lambda x: x['runs'][0].update(requested_mib=True),
    lambda x: x['runs'][0].update(requested_mib=-1),
    lambda x: x['runs'][0].update(requested_mib=0),
    lambda x: x['runs'][0].update(requested_mib=33),
    lambda x: x['runs'][0].update(stdout=''),
    lambda x: x['runs'][0].update(stdout='[]'),
    lambda x: x['runs'][0].update(stdout='{'),
    lambda x: x['runs'][0].update(unit='different'),
])
def test_invalid_run_is_unknown(capture, mutate):
    mutate(capture)
    assert subject.verify(capture)['status'] == 'unknown'


@pytest.mark.parametrize('mutate', [
    lambda rows: rows.reverse(),
    lambda rows: rows.append(rows[0]),
    lambda rows: rows[1].update(monotonic_ns=1),
    lambda rows: rows[1].update(pid=2),
    lambda rows: rows[1].update(cgroup_path='/different.scope'),
    lambda rows: rows[1].update(requested_bytes=2),
    lambda rows: rows[0]['files']['memory.current'].update(value='bad'),
    lambda rows: rows[0]['files']['memory.current'].update(value=None),
])
def test_corrupted_observation_is_unknown(capture, mutate):
    change_rows(capture, mutate)
    assert subject.verify(capture)['status'] == 'unknown'


@pytest.mark.parametrize('key', ['proc_cgroup_error', 'mem_available_error', 'host_memory_pressure_error'])
def test_read_errors_preserved(capture, key):
    change_rows(capture, lambda rows: rows[0].update({key: 'denied'}))
    result = subject.verify(capture)
    assert result['status'] == 'unknown'
    assert result['could_not_run_count'] == 1
    assert 'denied' in result['could_not_run'][0]


def test_missing_file_and_read_error(capture):
    change_rows(capture, lambda rows: rows[0]['files'].pop('dmem.current'))
    change_rows(capture, lambda rows: rows[1]['files']['memory.pressure'].update(error='denied'))
    result = subject.verify(capture)
    assert result['status'] == 'unknown'
    assert result['could_not_run_count'] == 2


def test_duplicate_scope(capture):
    capture['runs'][1] = copy.deepcopy(capture['runs'][0])
    capture['runs'][1].update(api='cpu_touch', worker_api='cpu_touch')
    change_rows(capture, lambda rows: rows[1].update(requested_bytes=1048576))
    assert 'independent scopes' in subject.verify(capture)['could_not_run'][0]


@pytest.mark.parametrize('value', ['0', '1'])
def test_cpu_positive_control_can_fail(capture, value):
    change_rows(capture, lambda rows: rows[1]['files']['memory.current'].update(value=value))
    assert subject.verify(capture)['status'] == 'fail'


def test_idle_noise_can_fail_control(capture):
    rows = [json.loads(line) for line in capture['runs'][0]['stdout'].splitlines()]
    rows[1]['files']['memory.current']['value'] = '1048576'
    capture['runs'][0]['stdout'] = '\n'.join(json.dumps(row) for row in rows)
    assert subject.verify(capture)['status'] == 'fail'


def test_release_control_can_fail(capture):
    change_rows(capture, lambda rows: rows[-1]['files']['memory.current'].update(value='1048576'))
    assert subject.verify(capture)['status'] == 'fail'


@pytest.mark.parametrize('document', [None, [], {'schema': 1, 'host': []}])
def test_malformed_document(document):
    assert subject.verify(document)['status'] == 'unknown'


@pytest.mark.parametrize('status,rc', [('pass', 0), ('fail', 1), ('unknown', 2)])
def test_cli_verdicts(tmp_path, monkeypatch, capsys, status, rc):
    path = tmp_path/'capture.json'
    path.write_text('{}', encoding='utf-8')
    monkeypatch.setattr(subject, 'verify', lambda _: {'status': status})
    assert subject.main([str(path)]) == rc
    assert json.loads(capsys.readouterr().out)['status'] == status


@pytest.mark.parametrize('payload', [None, b'\xff', b'{'])
def test_cli_read_failure(tmp_path, capsys, payload):
    path = tmp_path/'capture.json'
    if payload is not None:
        path.write_bytes(payload)
    assert subject.main([str(path)]) == 2
    assert json.loads(capsys.readouterr().out)['could_not_run_count'] == 1


def test_script_entry(tmp_path, monkeypatch, capsys):
    path = tmp_path/'capture.json'
    monkeypatch.setattr('sys.argv', ['verify_cgroup_repro', str(path)])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(subject.__file__, run_name='__main__')
    assert exc.value.code == 2
    assert json.loads(capsys.readouterr().out)['status'] == 'unknown'
