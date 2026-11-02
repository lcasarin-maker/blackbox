"""tools/motor_solicitudes.py: el contrato `bb-motor-solicitud/1` y su manejador.

systemctl es un doble: ningun test toca la unidad real. Cada rama que actua lleva su
control negativo (la misma entrada que NO debe actuar, no actua).
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tools import motor_caidas as mc
from tools import motor_solicitudes as ms

DORADOS = Path(__file__).parent / "fixtures" / "contrato"
SHA_SOLICITUD = "2716e2de414dd8ee730704ffb2dfe9b248c01ffcd83fee93527dd8fdce0ecc6f"
SHA_MANEJADOR = "944541e29e82cc29495d4354720dd35851a48fde737f7f4e9a7c6335c3625dd4"
UNIDAD = "ai-nemotron.service"
T0 = datetime(2026, 11, 1, 15, 30, tzinfo=timezone.utc)


@pytest.fixture
def motor(tmp_path, monkeypatch):
    """El directorio del contrato y un systemctl que solo anota."""
    llamadas: list[str] = []
    estado = {"result": "success", "rc": 0}

    def systemctl(verbo, unidad):
        assert unidad == UNIDAD
        llamadas.append(verbo)
        return estado["rc"] if verbo != "reset-failed" else 0

    monkeypatch.setattr(ms, "systemctl", systemctl)
    monkeypatch.setattr(ms, "_resultado", lambda unidad: estado["result"])
    monkeypatch.setenv("BLACKBOX_MOTOR_CONFIG", str(tmp_path / "gw" / "active_engine.json"))
    d = tmp_path / "motor"
    return d, llamadas, estado


def pide(d: Path, sol_id: str, accion: str, creada: datetime = T0, **extra) -> Path:
    sol = {"esquema": ms.ESQUEMA, "id": sol_id, "accion": accion, "origen": "consumidor",
           "creada": creada.isoformat(), "plazo_s": 900, **extra}
    ruta = d / "solicitudes" / f"{sol_id}.json"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(sol), encoding="utf-8")
    return ruta


def respuesta(d: Path, sol_id: str) -> dict:
    return json.loads((d / "respuestas" / f"{sol_id}.json").read_text(encoding="utf-8"))


def vuelta(d: Path, ahora: datetime = T0) -> list[str]:
    return ms.atender(d, UNIDAD, reloj=lambda: ahora)


def ventana(duracion_s: int, compensacion: dict | None = None) -> dict:
    return {"ventana": {"duracion_s": duracion_s, "motivo": "experimento sobre el motor",
                        "compensacion": compensacion or {"accion": "arrancar"}}}


# --- el contrato fijado por los dorados, copiados (no importados) en el consumidor --------


def test_los_dorados_son_los_mismos_que_fija_el_consumidor():
    assert hashlib.sha256((DORADOS / "bb_motor_solicitud_1.json").read_bytes()).hexdigest() == SHA_SOLICITUD
    assert hashlib.sha256((DORADOS / "bb_motor_manejador_1.json").read_bytes()).hexdigest() == SHA_MANEJADOR


def test_el_dorado_de_la_solicitud_se_acepta_y_caduca_con_su_propio_plazo(motor):
    sol = json.loads((DORADOS / "bb_motor_solicitud_1.json").read_text(encoding="utf-8"))
    creada = datetime.fromisoformat(sol["creada"])
    assert ms.valida(sol, sol["id"], creada) == ""
    tarde = creada + timedelta(seconds=sol["plazo_s"] + 1)
    assert ms.valida(sol, sol["id"], tarde).startswith("caducada")


def test_el_latido_se_escribe_byte_a_byte_como_el_dorado(motor):
    d, _ll, _e = motor
    dorado = (DORADOS / "bb_motor_manejador_1.json").read_text(encoding="utf-8")
    v = json.loads(dorado)["ventana"]
    d.mkdir(parents=True)
    (d / "ventana.json").write_text(json.dumps({**v, "desde": T0.isoformat(),
                                                "compensacion": {"accion": "arrancar"}}), encoding="utf-8")
    ms.latido(d, UNIDAD, T0)
    assert (d / "manejador.json").read_text(encoding="utf-8") == dorado


# --- orden, una sola accion por accion pedida, rechazos ----------------------------------


def test_dos_solicitudes_simultaneas_se_atienden_en_orden_sin_reinicio_doble(motor):
    d, llamadas, _e = motor
    pide(d, "b", "reiniciar", T0 + timedelta(seconds=1))
    pide(d, "a", "reiniciar", T0)
    lineas = vuelta(d, T0 + timedelta(seconds=5))
    assert llamadas == ["restart"]
    assert respuesta(d, "a")["estado"] == respuesta(d, "b")["estado"] == "hecha"
    assert "atendida por la de a" in respuesta(d, "b")["detalle"]
    assert [ln.split()[1] for ln in lineas] == ["a", "b"]
    assert not list((d / "solicitudes").iterdir())


def test_control_negativo_una_accion_distinta_en_medio_no_se_fusiona(motor):
    d, llamadas, _e = motor
    for i, accion in enumerate(("reiniciar", "parar", "reiniciar")):
        pide(d, f"s{i}", accion, T0 + timedelta(seconds=i))
    vuelta(d, T0 + timedelta(seconds=5))
    assert llamadas == ["restart", "stop", "restart"]


def test_el_orden_es_el_de_creada_no_el_del_nombre(motor):
    d, llamadas, _e = motor
    pide(d, "a-tarde", "parar", T0 + timedelta(seconds=9))
    pide(d, "z-pronto", "arrancar", T0)
    vuelta(d, T0 + timedelta(seconds=10))
    assert llamadas == ["start", "stop"]


@pytest.mark.parametrize("cambio, motivo", [
    ({"esquema": "bb-motor-solicitud/2"}, "no es bb-motor-solicitud/1"),
    ({"accion": "borrar"}, "accion desconocida"),
    ({"id": "otro"}, "id invalido"),
    ({"origen": " "}, "sin origen"),
    ({"plazo_s": 0}, "plazo_s"),
    ({"creada": "2026-11-01T15:30:00"}, "creada"),
])
def test_una_solicitud_invalida_se_rechaza_con_motivo_y_no_actua(motor, cambio, motivo):
    d, llamadas, _e = motor
    ruta = pide(d, "x", "reiniciar")
    sol = {**json.loads(ruta.read_text(encoding="utf-8")), **cambio}
    ruta.write_text(json.dumps(sol), encoding="utf-8")
    vuelta(d)
    r = respuesta(d, "x")
    assert r["estado"] == "rechazada" and motivo in r["motivo"]
    assert llamadas == []


def test_una_solicitud_caducada_no_actua_tarde(motor):
    d, llamadas, _e = motor
    pide(d, "x", "reiniciar")
    vuelta(d, T0 + timedelta(seconds=901))
    assert respuesta(d, "x")["estado"] == "rechazada" and llamadas == []


def test_control_negativo_la_misma_dentro_de_plazo_si_actua(motor):
    d, llamadas, _e = motor
    pide(d, "x", "reiniciar")
    vuelta(d, T0 + timedelta(seconds=899))
    assert respuesta(d, "x") | {"actualizado": None} == {
        "esquema": ms.ESQUEMA_RESPUESTA, "id": "x", "accion": "reiniciar", "estado": "hecha",
        "rc": 0, "actualizado": None}
    assert llamadas == ["restart"]


def test_el_rc_distinto_de_cero_es_fallida_con_su_rc(motor):
    d, _ll, estado = motor
    estado["rc"] = 1
    pide(d, "x", "arrancar")
    vuelta(d)
    assert (respuesta(d, "x")["estado"], respuesta(d, "x")["rc"]) == ("fallida", 1)


def test_el_limite_de_arranques_se_limpia_antes_de_arrancar(motor):
    d, llamadas, estado = motor
    estado["result"] = "start-limit-hit"
    pide(d, "x", "arrancar")
    vuelta(d)
    assert llamadas == ["reset-failed", "start"]


def test_control_negativo_sin_limite_no_se_limpia_nada(motor):
    d, llamadas, _e = motor
    pide(d, "x", "arrancar")
    vuelta(d)
    assert llamadas == ["start"]


def test_una_solicitud_retirada_por_su_autor_no_se_atiende(motor):
    d, llamadas, _e = motor
    ruta = pide(d, "x", "reiniciar")
    ruta.unlink()                      # el consumidor se rindio antes de que bb la tomara
    linea, _ = ms._atiende(d, ruta, UNIDAD, T0, None)
    assert "retirada" in linea and llamadas == []


def test_una_tomada_huerfana_se_declara_fallida_y_no_se_reintenta(motor):
    d, llamadas, _e = motor
    (d / "solicitudes").mkdir(parents=True)
    (d / "solicitudes" / "x.tomada").write_text("{}", encoding="utf-8")
    vuelta(d)
    assert respuesta(d, "x")["estado"] == "fallida" and llamadas == []
    assert not (d / "solicitudes" / "x.tomada").exists()


def test_un_segundo_manejador_a_la_vez_no_atiende(motor):
    d, llamadas, _e = motor
    import fcntl
    pide(d, "x", "reiniciar")
    with open(d / "manejador.lock", "w", encoding="utf-8") as otro:
        fcntl.flock(otro, fcntl.LOCK_EX)
        assert vuelta(d) == ["otro manejador atiende las solicitudes: esta vuelta no"]
    assert llamadas == [] and (d / "solicitudes" / "x.json").exists()


def test_las_lineas_de_solicitud_no_cuentan_como_cuelgue(motor):
    d, _ll, _e = motor
    pide(d, "x", "reiniciar")
    lineas = [f"[2026-11-01 15:30:00] {ln}" for ln in vuelta(d)]
    assert mc.cuelgues(lineas) == []
    assert mc.cuelgues(["[2026-11-01 15:30:00] REINICIA ai-nemotron.service (chat) origen=vigilante"])


# --- la ventana: vigente, cerrada, vencida, y su compensacion ----------------------------


def test_abrir_una_ventana_la_deja_vigente_y_en_el_latido(motor):
    d, llamadas, _e = motor
    pide(d, "v", "ventana", **ventana(600))
    vuelta(d)
    assert respuesta(d, "v")["estado"] == "hecha" and llamadas == []
    assert ms.ventana_vigente(d, T0 + timedelta(seconds=599))["id"] == "v"
    assert ms.ventana_vigente(d, T0 + timedelta(seconds=600)) is None
    lat = json.loads((d / "manejador.json").read_text(encoding="utf-8"))
    assert lat["ventana"]["id"] == "v" and lat["latido_s"] == ms.LATIDO_S


def test_una_segunda_ventana_se_rechaza_mientras_la_primera_viva(motor):
    d, _ll, _e = motor
    pide(d, "v1", "ventana", **ventana(600))
    pide(d, "v2", "ventana", T0 + timedelta(seconds=1), **ventana(600))
    vuelta(d, T0 + timedelta(seconds=2))
    assert respuesta(d, "v2")["estado"] == "rechazada" and "v1" in respuesta(d, "v2")["motivo"]


def test_las_solicitudes_del_consumidor_se_atienden_dentro_de_su_ventana(motor):
    d, llamadas, _e = motor
    pide(d, "v", "ventana", **ventana(600))
    pide(d, "r", "reiniciar", T0 + timedelta(seconds=1))
    vuelta(d, T0 + timedelta(seconds=2))
    assert llamadas == ["restart"] and ms.ventana_vigente(d, T0 + timedelta(seconds=3))


def test_al_vencer_la_ventana_se_aplica_la_compensacion_y_se_registra(motor):
    d, llamadas, _e = motor
    pide(d, "v", "ventana", **ventana(600))
    vuelta(d)
    lineas = vuelta(d, T0 + timedelta(seconds=601))
    assert llamadas == ["start"]
    assert any(ln.startswith("VENTANA v vencida") for ln in lineas)
    assert not (d / "ventana.json").exists()
    assert "compensacion: arrancar rc=0" in respuesta(d, "v")["detalle"]


def test_control_negativo_antes_de_vencer_no_se_compensa(motor):
    d, llamadas, _e = motor
    pide(d, "v", "ventana", **ventana(600))
    vuelta(d)
    vuelta(d, T0 + timedelta(seconds=599))
    assert llamadas == [] and (d / "ventana.json").exists()


def test_cerrarla_con_duracion_cero_compensa_ya(motor):
    d, llamadas, _e = motor
    pide(d, "v", "ventana", **ventana(600))
    pide(d, "c", "ventana", T0 + timedelta(seconds=1), ventana={"duracion_s": 0, "motivo": "fin"})
    vuelta(d, T0 + timedelta(seconds=2))
    assert llamadas == ["start"] and respuesta(d, "c")["estado"] == "hecha"
    assert ms.ventana_vigente(d, T0 + timedelta(seconds=3)) is None


def test_cerrar_sin_ventana_no_hace_nada(motor):
    d, llamadas, _e = motor
    pide(d, "c", "ventana", ventana={"duracion_s": 0, "motivo": "fin"})
    vuelta(d)
    assert llamadas == [] and respuesta(d, "c")["detalle"] == "no habia ventana que cerrar"


def test_una_ventana_ilegible_se_descarta_arrancando(motor):
    d, llamadas, _e = motor
    d.mkdir(parents=True)
    (d / "ventana.json").write_text("{roto", encoding="utf-8")
    assert ms.ventana_vigente(d, T0) is None
    lineas = vuelta(d)
    assert llamadas == ["start"] and "ilegible" in lineas[0]


def test_compensacion_restaurar_devuelve_la_copia_y_reinicia(motor, tmp_path):
    d, llamadas, _e = motor
    cfg = ms.config_motor()
    cfg.parent.mkdir(parents=True)
    copia = cfg.parent / "active_engine.json.copia"
    copia.write_text('{"image": "produccion"}\n', encoding="utf-8")
    cfg.write_text('{"image": "experimento"}\n', encoding="utf-8")
    pide(d, "v", "ventana", **ventana(600, {"accion": "restaurar", "copia": str(copia)}))
    vuelta(d)
    vuelta(d, T0 + timedelta(seconds=601))
    assert cfg.read_text(encoding="utf-8") == '{"image": "produccion"}\n'
    assert llamadas == ["restart"]


def test_control_negativo_restaurar_ya_restaurado_solo_arranca(motor):
    d, llamadas, _e = motor
    cfg = ms.config_motor()
    cfg.parent.mkdir(parents=True)
    copia = cfg.parent / "active_engine.json.copia"
    copia.write_text('{"image": "produccion"}\n', encoding="utf-8")
    cfg.write_text('{"image": "produccion"}\n', encoding="utf-8")
    pide(d, "v", "ventana", **ventana(600, {"accion": "restaurar", "copia": str(copia)}))
    vuelta(d)
    vuelta(d, T0 + timedelta(seconds=601))
    assert llamadas == ["start"], "la config ya era la copia: reiniciar seria el reinicio doble"


def test_una_copia_fuera_del_directorio_de_la_config_se_rechaza(motor, tmp_path):
    d, llamadas, _e = motor
    ms.config_motor().parent.mkdir(parents=True)
    ajena = tmp_path / "ajena.json"
    ajena.write_text("{}", encoding="utf-8")
    pide(d, "v", "ventana", **ventana(600, {"accion": "restaurar", "copia": str(ajena)}))
    vuelta(d)
    assert respuesta(d, "v")["estado"] == "rechazada" and "junto a" in respuesta(d, "v")["motivo"]
    assert not (d / "ventana.json").exists() and llamadas == []


def test_una_ventana_mas_larga_que_el_tope_se_rechaza(motor):
    d, _ll, _e = motor
    pide(d, "v", "ventana", **ventana(ms.TOPE_VENTANA_S + 1))
    vuelta(d)
    assert respuesta(d, "v")["estado"] == "rechazada"


def test_la_cli_ventana_sale_0_con_una_vigente_y_1_sin_ella(motor, capsys):
    d, _ll, _e = motor
    assert ms.main(["--dir", str(d), "ventana"]) == 1
    d.mkdir(parents=True)
    hasta = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
    (d / "ventana.json").write_text(json.dumps({"id": "v", "origen": "consumidor", "motivo": "m",
                                                "hasta": hasta}), encoding="utf-8")
    assert ms.main(["--dir", str(d), "ventana"]) == 0
    assert capsys.readouterr().out.startswith("v de consumidor hasta")
