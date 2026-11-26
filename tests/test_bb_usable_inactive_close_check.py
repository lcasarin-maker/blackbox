"""El cierre distingue sujeto sano, fallo de status y bus inaccesible."""
import json
import os
from pathlib import Path
import subprocess

import pytest


CARD = Path(__file__).resolve().parents[1] / 'tasks/archive/DEBT-BB-USABLE-INACTIVO-DEJA-CIEGO-EL-WATCHDOG-01.md'


@pytest.mark.parametrize(('output', 'status', 'expected'), [
    ('  ARMADO    bb-usable (latido)\ncould_not_run: 0\n', 0, 0),
    ('  ARMADO    bb-usable (latido)\ncould_not_run: 0\n', 1, 1),
    ('  ARMADO    bb-usable (latido)\ncould_not_run: 1\n', 0, 1),
    ('  CIEGO     bb-usable (bus inaccesible)\ncould_not_run: 1\n', 0, 1),
    ('  FALTA     bb-usable (inactivo)\ncould_not_run: 0\n', 0, 1),
    ('  FALTA     bb-usable (activa pero sin latido)\ncould_not_run: 0\n', 0, 1),
    ('  ARMADO    bb-usable (latido)\n  CIEGO     configuracion del watchdog de hardware\ncould_not_run: 1\n', 0, 1),
    ('  ARMADO    bb-usable (latido)\ncould_not_run: 0\n  CIEGO     watchdog de hardware\n', 0, 1),
    ('', 0, 1),
])
def test_close_check(tmp_path, output, status, expected):
    line = next(line for line in CARD.read_text().splitlines() if line.startswith('close_check: '))
    command = json.loads(line.removeprefix('close_check: '))['cmd']
    (tmp_path / 'bin').mkdir()
    bb = tmp_path / 'bin/bb'
    bb.write_text('#!/bin/sh\ncat <<\'END\'\n' + output + 'END\nexit ' + str(status) + '\n')
    bb.chmod(0o755)
    result = subprocess.run(['bash', '-c', command], cwd=tmp_path, capture_output=True)
    assert (result.returncode == 0) == (expected == 0)


def test_last_grep_failure_cannot_pass(tmp_path):
    line = next(line for line in CARD.read_text().splitlines() if line.startswith('close_check: '))
    command = json.loads(line.removeprefix('close_check: '))['cmd']
    (tmp_path / 'bin').mkdir()
    bb = tmp_path / 'bin/bb'
    bb.write_text("#!/bin/sh\nprintf '  ARMADO    bb-usable (latido)\\ncould_not_run: 0\\n'\n")
    bb.chmod(0o755)
    grep = tmp_path / 'bin/grep'
    grep.write_text('#!/bin/sh\ncase "$*" in *"FALTA +bb-usable"*) exit 2;; esac\nexec /usr/bin/grep "$@"\n')
    grep.chmod(0o755)
    env = {**os.environ, 'PATH': str(tmp_path / 'bin') + ':' + os.environ['PATH']}
    result = subprocess.run(['bash', '-c', command], cwd=tmp_path, env=env, capture_output=True)
    assert result.returncode != 0
