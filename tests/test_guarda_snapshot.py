"""La privacidad se mide en los blobs publicados, aun con disco e indice distintos."""
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


def carga():
    ruta = Path(__file__).with_name('test_sin_datos_privados.py')
    spec = importlib.util.spec_from_file_location('guarda_snapshot', ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize('disco', ['limpio', 'borrado', 'indice_limpio'])
def test_head_contaminado_bloquea_aunque_disco_limpio(tmp_path, monkeypatch, disco):
    m = carga()
    def git(*args):
        return subprocess.run(['git', *args], cwd=tmp_path, check=True, capture_output=True)
    git('init', '-q')
    f = tmp_path / 'dato.txt'
    f.write_text('10.' + '194.' + '62.85')
    baseline = tmp_path / 'tests/fixtures/datos_privados_baseline.json'
    baseline.parent.mkdir(parents=True)
    baseline.write_text('{}')
    git('add', '--', 'dato.txt', 'tests/fixtures/datos_privados_baseline.json')
    git('-c', 'user.name=Prueba', '-c', 'user.email=prueba@example.org', 'commit', '-qm', 'fixture')
    f.write_text('texto limpio')
    if disco == 'borrado':
        f.unlink()
    elif disco == 'indice_limpio':
        git('add', '--', 'dato.txt')
    # Tambien intentar blanquear el dato mediante la base del disco debe fallar.
    baseline.write_text(json.dumps({'dato.txt': 1}))
    monkeypatch.setattr(m, 'RAIZ', tmp_path)
    monkeypatch.setattr(m, '__file__', str(tmp_path / 'tests/test_sin_datos_privados.py'))
    monkeypatch.setattr(m, 'BASE', baseline)
    assert m.medir()['dato.txt'] == 1
    with pytest.raises(AssertionError):
        m.test_el_repo_no_gana_datos_privados()
    f.write_text('texto limpio')
    git('add', '--', 'dato.txt')
    git('-c', 'user.name=Prueba', '-c', 'user.email=prueba@example.org', 'commit', '-qm', 'fixture limpio')
    assert m.medir() == {}
    m.test_el_repo_no_gana_datos_privados()
