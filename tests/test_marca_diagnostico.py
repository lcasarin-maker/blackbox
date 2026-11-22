import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def consumidor(ruta, ahora, testigo):
    from tools import marca_diagnostico as marca
    if not marca.activa(ruta, ahora):
        testigo()


def test_consumidor_no_llama_activa_y_llama_ausente_o_caducada(tmp_path):
    from tools import marca_diagnostico as marca
    ruta = tmp_path / 'marca.json'
    llamadas = []
    testigo = lambda: llamadas.append('llamada')
    consumidor(ruta, 100, testigo)
    assert llamadas == ['llamada']
    llamadas.clear()
    marca.activar(ruta, 10, 100)
    consumidor(ruta, 109, testigo)
    assert llamadas == []
    consumidor(ruta, 110, testigo)
    assert llamadas == ['llamada']
    llamadas.clear()
    marca.desactivar(ruta)
    consumidor(ruta, 101, testigo)
    assert llamadas == ['llamada']


def test_cli_y_validacion(tmp_path):
    env = {**os.environ, 'BLACKBOX_DATA': str(tmp_path)}
    def bb(*args):
        return subprocess.run([str(ROOT / 'bin/bb'), 'marca-diagnostico', *args], env=env, capture_output=True, text=True)
    assert bb('activar', '60').returncode == 0
    ruta = tmp_path / 'marca-diagnostico.json'
    from tools import marca_diagnostico as marca
    contenido = json.loads(ruta.read_text())
    assert marca.activa(ruta, contenido['vence'] - 1)
    assert not marca.activa(ruta, contenido['vence'])
    assert bb('activar', '0').returncode != 0
    assert bb('desactivar').returncode == 0
    assert not ruta.exists()
    assert bb('desactivar').returncode == 0


@pytest.mark.parametrize('texto', ['{}', 'null', '{', '{"esquema":"otro","vence":999}', '{"esquema":"bb-marca-diagnostico/1","vence":true}', '{"esquema":"bb-marca-diagnostico/1","vence":999,"vence":0}', '{"esquema":"bb-marca-diagnostico/1","vence":' + '9' * 400 + '}', ' ' * 4097])
def test_marca_invalida_no_autoriza_llamada(tmp_path, texto):
    ruta = tmp_path / 'marca.json'
    ruta.write_text(texto)
    llamadas = []
    with pytest.raises(ValueError, match='marca'):
        consumidor(ruta, 100, lambda: llamadas.append(1))
    assert llamadas == []


def test_enlace_colgante_no_autoriza_llamada(tmp_path):
    ruta = tmp_path / 'marca.json'
    ruta.symlink_to(tmp_path / 'ausente')
    llamadas = []
    with pytest.raises(ValueError, match='marca'):
        consumidor(ruta, 100, lambda: llamadas.append(1))
    assert llamadas == []


def test_fifo_no_bloquea_ni_autoriza_llamada(tmp_path):
    ruta = tmp_path / 'marca.json'
    os.mkfifo(ruta)
    codigo = "from pathlib import Path; from tools.marca_diagnostico import activa; activa(Path(__import__('sys').argv[1]), 100); print('LLAMADA')"
    resultado = subprocess.run([sys.executable, '-c', codigo, str(ruta)], cwd=ROOT, capture_output=True, text=True, timeout=3)
    assert resultado.returncode != 0
    assert 'marca ilegible' in resultado.stderr
    assert 'LLAMADA' not in resultado.stdout


@pytest.mark.parametrize('valor,destino', [('', '.local/share/blackbox'), ('rel', 'rel')])
def test_cli_ruta_desde_cwd_original_o_home(tmp_path, valor, destino):
    home = tmp_path / 'home'
    home.mkdir()
    env = {**os.environ, 'HOME': str(home), 'BLACKBOX_DATA': valor}
    resultado = subprocess.run([str(ROOT / 'bin/bb'), 'marca-diagnostico', 'activar', '60'], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
    base = home if not valor else tmp_path
    assert (base / destino / 'marca-diagnostico.json').is_file()


@pytest.mark.parametrize('tipo', ['padre', 'enlace'])
@pytest.mark.parametrize('accion', ['activar', 'desactivar'])
@pytest.mark.parametrize('existente', [False, True])
def test_cli_rechaza_ruta_invalida_sin_tocar_destino(tmp_path, tipo, accion, existente):
    from tools import marca_diagnostico as marca
    home = tmp_path / 'home'
    home.mkdir()
    cwd = tmp_path / 'cwd'
    cwd.mkdir()
    destino = tmp_path / 'real'
    destino.mkdir(mode=0o755)
    archivo = destino / 'marca-diagnostico.json'
    if existente:
        archivo.write_text('testigo')
    if tipo == 'padre':
        valor = '../real'
    else:
        (cwd / 'enlace').symlink_to(destino, target_is_directory=True)
        valor = 'enlace'
    env = {**os.environ, 'HOME': str(home), 'BLACKBOX_DATA': valor, 'TMPDIR': str(tmp_path)}
    args = [str(ROOT / 'bin/bb'), 'marca-diagnostico', accion]
    if accion == 'activar':
        args.append('60')
    resultado = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    assert resultado.returncode != 0
    assert resultado.stderr
    assert (destino.stat().st_mode & 0o777) == 0o755
    assert sorted(p.name for p in destino.iterdir()) == (['marca-diagnostico.json'] if existente else [])
    if existente:
        assert archivo.read_text() == 'testigo'
    with pytest.raises(ValueError):
        marca.activa(cwd / valor / 'marca-diagnostico.json', 100)


def test_cli_relativa_activa_lee_y_retira(tmp_path):
    from tools import marca_diagnostico as marca
    home = tmp_path / 'home'
    home.mkdir()
    env = {**os.environ, 'HOME': str(home), 'BLACKBOX_DATA': 'datos', 'TMPDIR': str(tmp_path)}
    def bb(*args):
        return subprocess.run([str(ROOT / 'bin/bb'), 'marca-diagnostico', *args], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert bb('activar', '60').returncode == 0
    ruta = tmp_path / 'datos' / 'marca-diagnostico.json'
    assert (ruta.parent.stat().st_mode & 0o777) == 0o700
    assert marca.activa(ruta, 0)
    assert bb('desactivar').returncode == 0
    assert not marca.activa(ruta, 0)


@pytest.mark.parametrize('accion', ['activar', 'desactivar'])
def test_cli_rechaza_enlace_de_archivo_sin_alterarlo(tmp_path, accion):
    home = tmp_path / 'home'
    home.mkdir()
    datos = tmp_path / 'datos'
    datos.mkdir(mode=0o755)
    destino = tmp_path / 'destino'
    destino.write_text('testigo')
    enlace = datos / 'marca-diagnostico.json'
    enlace.symlink_to(destino)
    env = {**os.environ, 'HOME': str(home), 'BLACKBOX_DATA': str(datos), 'TMPDIR': str(tmp_path)}
    args = [str(ROOT / 'bin/bb'), 'marca-diagnostico', accion]
    if accion == 'activar':
        args.append('60')
    resultado = subprocess.run(args, env=env, cwd=tmp_path, capture_output=True, text=True)
    assert resultado.returncode != 0
    assert enlace.is_symlink()
    assert destino.read_text() == 'testigo'
    assert (datos.stat().st_mode & 0o777) == 0o755
