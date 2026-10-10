"""bin/bb-vigilante-motor y los chequeos de `bb status` sobre el motor local.

curl y systemctl son falsos: la prueba no toca el motor real ni lo reinicia.
Control negativo de cada rama que actua: la misma entrada sana NO actua.
"""
import os
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
VIG = RAIZ / "bin" / "bb-vigilante-motor"
BB = RAIZ / "bin" / "bb"


@pytest.fixture
def falso(tmp_path):
    b = tmp_path / "bin"; b.mkdir()
    (b / "curl").write_text(
        '#!/bin/bash\n'
        'case "$*" in\n'
        '  *chat/completions*) printf "%s" "${FAKE_CHAT_CODE:-200}" ;;\n'
        '  *) echo \'{"id":"nemotron-local"}\' ;;\nesac\n', encoding="utf-8")
    (b / "systemctl").write_text(
        '#!/bin/bash\n'
        'case "$*" in\n'
        '  *"show"*ActiveState*) echo "${FAKE_ACTIVE:-active}" ;;\n'
        '  *"show"*ExecMainStartTimestamp*) echo "${FAKE_START-Mon 2020-01-01 00:00:00 UTC}" ;;\n'
        '  *restart*) echo "$*" >> "$FAKE_LOG" ;;\n'
        '  *is-active*) exit "${FAKE_TIMER_RC:-0}" ;;\n'
        'esac\n', encoding="utf-8")
    for f in b.iterdir():
        f.chmod(0o755)
    return tmp_path, {"PATH": f"{b}:{os.environ['PATH']}", "FAKE_LOG": str(tmp_path / "reinicios"),
                      "BLACKBOX_DATA": str(tmp_path / "d"), "VIGILANTE_GRACIA_S": "10",
                      "VIGILANTE_UMBRAL": "3", "VIGILANTE_ESPERA_CHAT_S": "2"}


def _vig(env, n=1):
    for _ in range(n):
        subprocess.run([str(VIG)], env={**os.environ, **env}, check=True, timeout=30)


def _reinicios(tmp):
    p = tmp / "reinicios"
    return p.read_text(encoding="utf-8").splitlines() if p.exists() else []


def test_tres_fallos_seguidos_reinician_la_unidad(falso):
    tmp, env = falso
    _vig({**env, "FAKE_CHAT_CODE": "000"}, 3)
    assert len(_reinicios(tmp)) == 1
    assert "REINICIA" in (tmp / "d" / "vigilante_motor.log").read_text(encoding="utf-8")


def test_control_negativo_dos_fallos_no_reinician(falso):
    tmp, env = falso
    _vig({**env, "FAKE_CHAT_CODE": "000"}, 2)
    assert _reinicios(tmp) == []


def test_control_negativo_chat_sano_nunca_reinicia(falso):
    tmp, env = falso
    _vig(env, 5)
    assert _reinicios(tmp) == []


def test_un_exito_entre_fallos_reinicia_la_cuenta(falso):
    tmp, env = falso
    _vig({**env, "FAKE_CHAT_CODE": "000"}, 2)
    _vig(env)
    _vig({**env, "FAKE_CHAT_CODE": "000"}, 2)
    assert _reinicios(tmp) == []


def test_control_negativo_durante_la_gracia_no_actua(falso):
    tmp, env = falso
    from datetime import datetime
    ahora = datetime.now().strftime("%a %Y-%m-%d %H:%M:%S")
    _vig({**env, "FAKE_CHAT_CODE": "000", "FAKE_START": ahora, "VIGILANTE_GRACIA_S": "600"}, 4)
    assert _reinicios(tmp) == []


def test_control_negativo_unidad_inactiva_no_la_toca_systemd_la_recupera(falso):
    tmp, env = falso
    _vig({**env, "FAKE_CHAT_CODE": "000", "FAKE_ACTIVE": "inactive"}, 4)
    assert _reinicios(tmp) == []


def test_simulacro_registra_pero_no_reinicia(falso):
    tmp, env = falso
    _vig({**env, "FAKE_CHAT_CODE": "000", "VIGILANTE_SIMULA": "1"}, 3)
    assert _reinicios(tmp) == []
    assert "SIMULACRO" in (tmp / "d" / "vigilante_motor.log").read_text(encoding="utf-8")


def _status(tmp, env):
    cfg = tmp / "active_engine.json"
    cfg.write_text(env.pop("CFG", '{"env":{"CUDA_ENABLE_COREDUMP_ON_EXCEPTION": "1"}}'), encoding="utf-8")
    vol = tmp / "vol"; vol.mkdir(exist_ok=True)
    r = subprocess.run([str(BB), "status"], capture_output=True, text=True, timeout=120,
                       env={**os.environ, **env, "BLACKBOX_MOTOR_CONFIG": str(cfg),
                            "BLACKBOX_MOTOR_VOLCADOS": str(vol)})
    return r.stdout


def _fila(salida, nombre):
    return next(ln for ln in salida.splitlines() if nombre in ln)


def test_status_chat_vivo_con_modelos_vivo_esta_ARMADO(falso):
    tmp, env = falso
    assert "ARMADO" in _fila(_status(tmp, env), "contesta una llamada de chat")


def test_control_negativo_status_modelos_200_pero_chat_mudo_es_FALTA(falso):
    tmp, env = falso
    s = _status(tmp, {**env, "FAKE_CHAT_CODE": "000"})
    assert "ARMADO    motor de inferencia sirviendo" in s
    assert "FALTA" in _fila(s, "contesta una llamada de chat")


def test_control_negativo_status_sin_timer_del_vigilante_es_FALTA(falso):
    tmp, env = falso
    assert "FALTA" in _fila(_status(tmp, {**env, "FAKE_TIMER_RC": "3"}), "vigilante del motor")


def test_status_volcado_cuda_armado_y_su_control_negativo(falso):
    tmp, env = falso
    assert "ARMADO" in _fila(_status(tmp, dict(env)), "volcado CUDA")
    assert "FALTA" in _fila(_status(tmp, {**env, "CFG": '{"env":{}}'}), "volcado CUDA")
