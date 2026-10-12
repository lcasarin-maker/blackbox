"""Vigilante de avisos termicos: la maquina de estados es una funcion pura, cada transicion con su control."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from tools import aviso_termico as av

pytestmark = pytest.mark.unit

AHORA = datetime(2026, 10, 11, 18, 0, 0, tzinfo=timezone.utc)


def dato(estado, *, hace_s=5, t=96.0, zona="thermal_zone0"):
    return {
        "esquema": "bb-estado-termico/1",
        "estado": estado,
        "desde": (AHORA - timedelta(minutes=3)).isoformat(),
        "zona_mas_caliente": zona,
        "temp_c": t,
        "actualizado": (AHORA - timedelta(seconds=hace_s)).isoformat(),
    }


def test_etiqueta_trata_un_latido_viejo_o_un_dato_roto_como_desconocido_nunca_como_normal():
    assert av.etiqueta(dato("normal"), AHORA) == "normal"
    assert (
        av.etiqueta(dato("normal", hace_s=61), AHORA) == "desconocido"
    )  # el control: 61 s es viejo
    assert av.etiqueta(None, AHORA) == "desconocido"
    assert av.etiqueta({"estado": "normal"}, AHORA) == "desconocido"  # sin latido
    assert av.etiqueta(dato("raro"), AHORA) == "desconocido"


def test_el_primer_arranque_no_avisa_de_normal_ni_de_desconocido_pero_si_de_calor():
    assert av.decide(None, dato("normal"), AHORA)[0] == []
    assert av.decide(None, None, AHORA)[0] == []
    avisos, nuevo, _ = av.decide(None, dato("sostenida"), AHORA)
    assert nuevo == "sostenida" and [a.titulo for a in avisos] == [
        "ATOM: calor sostenido"
    ]


def test_entrar_en_calor_sostenido_avisa_una_vez_y_dice_que_hacer():
    avisos, nuevo, _ = av.decide("normal", dato("sostenida"), AHORA)
    assert (
        len(avisos) == 1
        and avisos[0].urgencia == "normal"
        and "bb who" in avisos[0].cuerpo
    )
    assert (
        av.decide(nuevo, dato("sostenida"), AHORA)[0] == []
    )  # control: seguir igual no repite el aviso


def test_pasar_de_100_es_critico_y_calcula_el_margen_al_trip():
    avisos, _, rec = av.decide(
        "sostenida", dato("sobre_100", t=100.8), AHORA, None, 1000.0
    )
    assert (
        avisos[0].urgencia == "critical"
        and "4.0 C del apagado" in avisos[0].cuerpo
        and rec == 1000.0
    )


def test_mientras_siga_sobre_100_recuerda_cada_10_min_y_no_antes():
    _, _, rec = av.decide("normal", dato("sobre_100", t=101.0), AHORA, None, 0.0)
    assert (
        av.decide("sobre_100", dato("sobre_100"), AHORA, rec, 599.0)[0] == []
    )  # control: 9 min 59 s
    avisos, _, rec2 = av.decide("sobre_100", dato("sobre_100"), AHORA, rec, 600.0)
    assert avisos and avisos[0].titulo == "ATOM: sigue sobre 100 C" and rec2 == 600.0


def test_normalizarse_avisa_en_baja_urgencia_solo_si_antes_hubo_calor():
    avisos, _, _ = av.decide("sostenida", dato("normal"), AHORA)
    assert [a.urgencia for a in avisos] == ["low"]
    assert (
        av.decide("normal", dato("normal"), AHORA)[0] == []
    )  # control: normal a normal no avisa


def test_perder_los_datos_se_avisa_una_vez_y_recuperarlos_tambien():
    avisos, nuevo, _ = av.decide("normal", dato("normal", hace_s=300), AHORA)
    assert nuevo == "desconocido" and avisos[0].titulo == "ATOM: sin datos térmicos"
    assert av.decide(nuevo, dato("normal", hace_s=400), AHORA)[0] == []  # no insiste
    avisos, nuevo, _ = av.decide("desconocido", dato("normal"), AHORA)
    assert nuevo == "normal" and avisos[0].urgencia == "low"


def test_enviar_arma_notify_send_y_declara_el_fallo_sin_lanzar(monkeypatch, capsys):
    llamadas = []

    class R:
        returncode, stderr = 0, ""

    monkeypatch.setattr(
        av.subprocess, "run", lambda cmd, **kw: llamadas.append(cmd) or R()
    )
    assert av.enviar(av.Aviso("critical", "T", "C")) is True
    assert llamadas[0] == ["notify-send", "-u", "critical", "-a", "blackbox", "T", "C"]

    class Mala:
        returncode, stderr = 1, "sin bus"

    monkeypatch.setattr(av.subprocess, "run", lambda cmd, **kw: Mala())
    assert av.enviar(av.Aviso("low", "T", "C")) is False
    assert "COULD_NOT_NOTIFY" in capsys.readouterr().err  # un fallo no se calla

    def revienta(cmd, **kw):
        raise FileNotFoundError("notify-send")

    monkeypatch.setattr(av.subprocess, "run", revienta)
    assert av.enviar(av.Aviso("low", "T", "C")) is False


def test_lee_distingue_archivo_ausente_de_ilegible(tmp_path):
    f = tmp_path / "e.json"
    assert av.lee(f) is None
    f.write_text("no es json", encoding="utf-8")
    assert av.lee(f) is None
    f.write_text(json.dumps(dato("normal")), encoding="utf-8")
    assert av.lee(f)["estado"] == "normal"
