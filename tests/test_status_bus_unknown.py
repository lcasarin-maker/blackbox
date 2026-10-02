"""Service lookup failures must remain unknown, rather than inactive."""
from pathlib import Path
import subprocess

import pytest

BB = Path(__file__).resolve().parents[1] / 'bin' / 'bb'


@pytest.mark.parametrize(('query', 'query_rc', 'journal', 'journal_rc', 'expected'), [
    ('Failed to connect to bus: Operation not permitted', 1, '', 0, 'CIEGO'),
    ('Failed to connect to bus: No such file or directory', 1, '', 0, 'CIEGO'),
    ('LoadState=not-found\nActiveState=inactive', 0, '', 0, 'FALTA'),
    ('LoadState=loaded\nActiveState=inactive', 0, '', 0, 'FALTA'),
    ('LoadState=loaded\nActiveState=active', 0, '', 0, 'FALTA'),
    ('LoadState=loaded\nActiveState=active', 0,
     '[bb-usable] latencia del escritorio: 0.02s', 0, 'ARMADO'),
    ('LoadState=loaded\nActiveState=active', 0, 'Permission denied', 1, 'CIEGO'),
    ('LoadState=loaded\nActiveState=active', 0,
     'Hint: You are currently not seeing messages from other users and the system.', 0, 'CIEGO'),
    ('', 0, '', 0, 'CIEGO'),
])
def test_lookup_classification(query, query_rc, journal, journal_rc, expected):
    source = BB.read_text(encoding="utf-8")
    helper = source[source.index('status_usable() {'):source.index('cmd_status() {')]
    script = '''
set -uo pipefail
armed=0; missing=0; blind=0; CNR=0
chk() { if [ "$2" -eq 0 ]; then armed=$((armed+1)); echo ARMADO; else missing=$((missing+1)); echo FALTA; fi; }
ciego() { blind=$((blind+1)); echo CIEGO; }
cannot_run() { CNR=$((CNR+1)); }
systemctl() { printf '%s\\n' "$QUERY"; return "$QUERY_RC"; }
fake_journal() { printf '%s\\n' "$JOURNAL"; return "$JOURNAL_RC"; }
JOURNALCTL=fake_journal
''' + helper + '\nstatus_usable\nprintf "%s %s %s %s\\n" "$armed" "$missing" "$blind" "$CNR"\n'
    import os
    result = subprocess.run(['bash', '-c', script], env={**os.environ,
        'QUERY': query, 'QUERY_RC': str(query_rc), 'JOURNAL': journal,
        'JOURNAL_RC': str(journal_rc)}, text=True, capture_output=True, check=True)
    assert result.stdout.splitlines()[0] == expected
    assert result.stdout.splitlines()[1] == {
        'ARMADO': '1 0 0 0', 'FALTA': '0 1 0 0', 'CIEGO': '0 0 1 1',
    }[expected]


def test_status_prints_unknown_count_even_zero():
    source = BB.read_text(encoding="utf-8")
    status = source[source.index('cmd_status() {'):source.index('cmd_status() {') + 18000]
    assert 'printf "could_not_run: %d\\n%s" "$CNR" "$CNR_LIST"' in status


@pytest.mark.parametrize('failure', ['declaration', 'start', 'journal', 'journal_hint'])
def test_clock_queries_preserve_unknown_instead_of_missing(failure):
    import os

    source = BB.read_text(encoding="utf-8")
    helper = source[source.index('clock_lock_evaluate() {'):source.index('# Consultar propiedades')]
    script = r'''
set -uo pipefail
CNR=0; CNR_LIST=''
cannot_run() { CNR=$((CNR+1)); CNR_LIST="$2"; }
systemctl() {
  case "$*" in
    *ExecStart*)
      if [ "$FAILURE" = declaration ]; then echo 'bus denied' >&2; return 1; fi
      echo 'ExecStart=nvidia-smi -lgc 300,2800' ;;
    *)
      if [ "$FAILURE" = start ]; then echo 'bus absent' >&2; return 1; fi
      echo '2026-10-02 12:00:00' ;;
  esac
}
fake_journal() {
  if [ "$FAILURE" = journal_hint ]; then echo 'Hint: not seeing messages'; return 0; fi
  echo 'journal denied' >&2; return 1
}
JOURNALCTL=fake_journal
''' + helper + '\ncmd_status_clock_lock\n'
    run = subprocess.run(['bash', '-c', script], env={**os.environ, 'FAILURE': failure},
                         text=True, capture_output=True, check=False)
    assert run.returncode == 2
    assert 'CIEGO: clock lock' in run.stdout
    assert 'could_not_run: 1' in run.stdout
    assert 'FALTA' not in run.stdout
