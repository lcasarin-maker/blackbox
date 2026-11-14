"""Aceptacion roja de pendientes; solo se invoca por sus close_checks explicitos."""
import os
import re
import subprocess
import sys

import pytest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
GUARDA = RAIZ / 'tests/test_sin_datos_privados.py'


def medir_copia(tmp_path, *, base='{}', dato_en_guarda=False, sin_git=False, dato_ordinario=False):
    tmp_path.mkdir(parents=True, exist_ok=True)
    tests = tmp_path / 'tests'
    (tests / 'fixtures').mkdir(parents=True)
    src = GUARDA.read_text()
    if dato_en_guarda:
        src += '\n# Control sintetico: ' + '10.' + '194.' + '62.85\n'
    (tests / GUARDA.name).write_text(src)
    (tests / 'fixtures/datos_privados_baseline.json').write_text(base)
    archivos = ['tests/test_sin_datos_privados.py', 'tests/fixtures/datos_privados_baseline.json']
    if dato_ordinario:
        (tmp_path / 'dato.txt').write_text('10.' + '194.' + '62.85')
        archivos.append('dato.txt')
    for args in [('init', '-q'), ('add', '--', *archivos),
                 ('-c', 'user.name=Prueba', '-c', 'user.email=prueba@example.org', 'commit', '-qm', 'fixture')]:
        subprocess.run(['git', *args], cwd=tmp_path, check=True, capture_output=True)
    if sin_git:
        (tmp_path / '.git').rename(tmp_path / 'git-inactivo')
    return subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                           'tests/test_sin_datos_privados.py::test_el_repo_no_gana_datos_privados'],
                          cwd=tmp_path, capture_output=True, text=True,
                          env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})


@pytest.mark.parametrize('fallo', ['base', 'git'])
def test_error_lector_es_could_not_run(tmp_path, fallo):
    resultado = medir_copia(tmp_path / 'roto', base='JSON roto' if fallo == 'base' else '{}', sin_git=fallo == 'git')
    assert resultado.returncode == 2, resultado.stdout + resultado.stderr
    limpio = medir_copia(tmp_path / 'limpio')
    assert limpio.returncode == 0, limpio.stdout + limpio.stderr
    privado = medir_copia(tmp_path / 'privado', dato_ordinario=True)
    assert privado.returncode == 1, privado.stdout + privado.stderr


def test_dato_nuevo_en_guarda_no_queda_exento(tmp_path):
    resultado = medir_copia(tmp_path, dato_en_guarda=True)
    assert resultado.returncode == 1, resultado.stdout + resultado.stderr


def test_spec_usa_una_notacion_gateway():
    nombres = set(re.findall(r'/srv/([^/`]+)/gateway/', (RAIZ / 'SPEC.md').read_text()))
    assert nombres == {'@BB_GATEWAY@'}, nombres
