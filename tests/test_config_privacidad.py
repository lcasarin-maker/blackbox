"""Configuracion operativa externa: nunca enviar a un destino implicito."""
import json

import pytest

from tools import boton_rojo
from tools.testigo import bb_wol


def test_wol_lee_config_local(tmp_path, monkeypatch, capsys):
    cfg = tmp_path / 'wol.json'
    cfg.write_text(json.dumps({'mac': '02-00-00-00-00-01', 'broadcast': '192.0.2.255'}))
    monkeypatch.setenv('BB_WOL_CONFIG', str(cfg))
    assert bb_wol.main(['--seco']) == 0
    assert '192.0.2.255:9' in capsys.readouterr().out


def test_wol_sin_destino_bloquea(monkeypatch):
    monkeypatch.delenv('BB_WOL_CONFIG', raising=False)
    with pytest.raises(SystemExit) as exc:
        bb_wol.main(['--seco'])
    assert exc.value.code == 2


def test_rojo_lee_usuario_local(tmp_path, monkeypatch):
    cfg = tmp_path / 'rojo.json'
    cfg.write_text(json.dumps({'usuario': 'operador'}))
    monkeypatch.delenv('BB_ROJO_USUARIO', raising=False)
    monkeypatch.setenv('BB_ROJO_CONFIG', str(cfg))
    assert boton_rojo.Ctx().usuario == 'operador'


def test_rojo_sin_usuario_bloquea(tmp_path, monkeypatch):
    monkeypatch.delenv('BB_ROJO_USUARIO', raising=False)
    monkeypatch.setenv('BB_ROJO_CONFIG', str(tmp_path / 'ausente.json'))
    with pytest.raises((OSError, ValueError)):
        boton_rojo.Ctx()


def test_rojo_json_sin_usuario_da_error_de_configuracion(tmp_path, monkeypatch):
    cfg = tmp_path / 'rojo.json'
    cfg.write_text('{}')
    monkeypatch.delenv('BB_ROJO_USUARIO', raising=False)
    monkeypatch.setenv('BB_ROJO_CONFIG', str(cfg))
    with pytest.raises(ValueError, match='rojo.json'):
        boton_rojo.Ctx()


@pytest.mark.parametrize('entrada', ['panic', 'crea', 'arranque-ok'])
def test_emergencia_sin_config_falla_con_mensaje(tmp_path, monkeypatch, capsys, entrada):
    from tools import panic, punto_restauracion
    monkeypatch.delenv('BB_ROJO_USUARIO', raising=False)
    monkeypatch.setenv('BB_ROJO_RAIZ', str(tmp_path))
    monkeypatch.setenv('BB_ROJO_CONFIG', str(tmp_path / 'ausente.json'))
    rc = panic.main([]) if entrada == 'panic' else punto_restauracion.main([entrada])
    assert rc == 2
    mensaje = capsys.readouterr().out
    assert 'COULD_NOT_RUN' in mensaje and 'ausente.json' in mensaje and 'usuario' in mensaje


def test_wol_config_lista_se_rechaza(tmp_path, monkeypatch):
    cfg = tmp_path / 'wol.json'
    cfg.write_text('[]')
    monkeypatch.setenv('BB_WOL_CONFIG', str(cfg))
    with pytest.raises(SystemExit) as exc:
        bb_wol.main(['--seco'])
    assert exc.value.code == 2
