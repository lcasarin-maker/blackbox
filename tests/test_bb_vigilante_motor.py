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
        '  *metrics*) [ -n "$FAKE_RUN" ] && printf "vllm:num_requests_running{e=\\"0\\"} %s\\nvllm:generation_tokens_total{e=\\"0\\"} %s\\nvllm:prompt_tokens_total{e=\\"0\\"} %s\\n" "$FAKE_RUN" "${FAKE_GEN:-100}" "${FAKE_PRO:-500}" ;;\n'
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


# --- atasco por metricas: peticiones corriendo y ni un token avanza ----------


def _atasco(env, n, **extra):
    _vig({**env, **extra}, n)


def test_atasco_por_metricas_reinicia_a_la_segunda_corrida_plana(falso):
    tmp, env = falso
    _atasco(env, 3, FAKE_RUN="30")           # 1a fija la base, 2a y 3a son planas
    assert len(_reinicios(tmp)) == 1
    log = (tmp / "d" / "vigilante_motor.log").read_text(encoding="utf-8")
    assert "REINICIA" in log and "atasco por metricas" in log


def test_control_negativo_una_sola_corrida_plana_no_reinicia(falso):
    tmp, env = falso
    _atasco(env, 2, FAKE_RUN="30")
    assert _reinicios(tmp) == []


def test_control_negativo_motor_que_avanza_no_reinicia(falso):
    tmp, env = falso
    for i in range(5):
        _atasco(env, 1, FAKE_RUN="30", FAKE_GEN=str(100 + i * 50), FAKE_PRO=str(500 + i * 90))
    assert _reinicios(tmp) == []


def test_control_negativo_motor_ocioso_run_cero_no_reinicia(falso):
    tmp, env = falso
    _atasco(env, 6, FAKE_RUN="0")
    assert _reinicios(tmp) == []


def test_control_negativo_prefill_que_avanza_sin_generar_no_reinicia(falso):
    tmp, env = falso
    for i in range(5):
        _atasco(env, 1, FAKE_RUN="30", FAKE_GEN="100", FAKE_PRO=str(500 + i * 900))
    assert _reinicios(tmp) == []


def test_control_negativo_sin_metricas_legibles_no_cuenta_atasco(falso):
    tmp, env = falso
    _atasco(env, 6)                           # FAKE_RUN ausente: curl no devuelve metricas
    assert _reinicios(tmp) == []


def test_un_avance_entre_corridas_planas_reinicia_la_cuenta(falso):
    tmp, env = falso
    _atasco(env, 2, FAKE_RUN="30")
    _atasco(env, 1, FAKE_RUN="30", FAKE_GEN="999")   # avanza: la cuenta vuelve a 0
    _atasco(env, 1, FAKE_RUN="30", FAKE_GEN="999")   # una plana: cuenta 1, no alcanza
    assert _reinicios(tmp) == []


def test_control_negativo_durante_la_gracia_el_atasco_no_actua(falso):
    tmp, env = falso
    from datetime import datetime
    ahora = datetime.now().strftime("%a %Y-%m-%d %H:%M:%S")
    _atasco({**env, "FAKE_START": ahora, "VIGILANTE_GRACIA_S": "600"}, 5, FAKE_RUN="30")
    assert _reinicios(tmp) == []


def test_simulacro_del_atasco_registra_y_no_reinicia(falso):
    tmp, env = falso
    _atasco(env, 3, FAKE_RUN="30", VIGILANTE_SIMULA="1")
    assert _reinicios(tmp) == []
    assert "SIMULACRO" in (tmp / "d" / "vigilante_motor.log").read_text(encoding="utf-8")


# --- tope de reinicios: 3 por hora, luego alerta en vez de reiniciar ---------


@pytest.fixture
def con_alertas(falso):
    tmp, env = falso
    snap = tmp / "snap.sh"
    snap.write_text('#!/bin/bash\necho "$*" >> "%s/snapshots.txt"\n' % tmp, encoding="utf-8")
    snap.chmod(0o755)
    ns = tmp / "bin" / "notify-send"
    ns.write_text('#!/bin/bash\necho "$*" >> "%s/avisos.txt"\n' % tmp, encoding="utf-8")
    ns.chmod(0o755)
    return tmp, {**env, "VIGILANTE_SNAPSHOT_CMD": str(snap), "FAKE_CHAT_CODE": "000"}


def _lineas(tmp, nombre):
    p = tmp / nombre
    return p.read_text(encoding="utf-8").splitlines() if p.exists() else []


def test_presupuesto_agotado_cuarto_reinicio_no_reinicia_y_avisa(con_alertas):
    tmp, env = con_alertas
    _vig(env, 12)                                  # 4 ciclos de 3 fallos
    assert len(_reinicios(tmp)) == 3
    assert (tmp / "d" / "motor_alerta.json").exists()
    assert "TOPE" in (tmp / "d" / "vigilante_motor.log").read_text(encoding="utf-8")
    assert len(_lineas(tmp, "snapshots.txt")) == 1
    assert len(_lineas(tmp, "avisos.txt")) == 1


def test_control_negativo_presupuesto_tres_reinicios_caben_sin_alerta(con_alertas):
    tmp, env = con_alertas
    _vig(env, 9)
    assert len(_reinicios(tmp)) == 3
    assert not (tmp / "d" / "motor_alerta.json").exists()
    assert _lineas(tmp, "snapshots.txt") == [] and _lineas(tmp, "avisos.txt") == []


def test_la_alerta_no_repite_snapshot_ni_aviso_aunque_siga_fallando(con_alertas):
    tmp, env = con_alertas
    _vig(env, 24)                                  # 8 ciclos
    assert len(_reinicios(tmp)) == 3
    assert len(_lineas(tmp, "snapshots.txt")) == 1 and len(_lineas(tmp, "avisos.txt")) == 1


def test_el_simulacro_no_consume_presupuesto(con_alertas):
    tmp, env = con_alertas
    _vig({**env, "VIGILANTE_SIMULA": "1"}, 18)     # 6 ciclos simulados
    _vig(env, 9)                                   # 3 reales
    assert len(_reinicios(tmp)) == 3
    assert not (tmp / "d" / "motor_alerta.json").exists()


def test_la_alerta_se_resuelve_cuando_el_chat_vuelve(con_alertas):
    tmp, env = con_alertas
    _vig(env, 12)
    assert (tmp / "d" / "motor_alerta.json").exists()
    _vig({**env, "FAKE_CHAT_CODE": "200"}, 1)
    assert not (tmp / "d" / "motor_alerta.json").exists()
    assert list((tmp / "d").glob("motor_alerta.resuelta.*.json"))


def test_control_negativo_la_alerta_no_se_resuelve_mientras_siga_mudo(con_alertas):
    tmp, env = con_alertas
    _vig(env, 14)
    assert (tmp / "d" / "motor_alerta.json").exists()


def test_presupuesto_ilegible_reinicia_igual_y_lo_registra(con_alertas):
    tmp, env = con_alertas
    (tmp / "d").mkdir(exist_ok=True)
    (tmp / "d" / "vigilante_motor.presupuesto").write_text("no es json", encoding="utf-8")
    _vig(env, 3)
    assert len(_reinicios(tmp)) == 1
    assert "ilegible" in (tmp / "d" / "vigilante_motor.log").read_text(encoding="utf-8")


def test_status_con_alerta_es_FALTA_y_sin_alerta_ARMADO(con_alertas):
    tmp, env = con_alertas
    assert "ARMADO" in _fila(_status(tmp, {**env, "FAKE_CHAT_CODE": "200"}), "sin alerta de tope")
    (tmp / "d").mkdir(exist_ok=True)
    (tmp / "d" / "motor_alerta.json").write_text("{}", encoding="utf-8")
    assert "FALTA" in _fila(_status(tmp, {**env, "FAKE_CHAT_CODE": "200"}), "sin alerta de tope")
