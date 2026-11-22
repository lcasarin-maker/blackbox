"""Alarma de GPU en Reset Required: deteccion con control negativo, idempotencia por boot_id, reintento sin sesion."""

import json

import pytest

from tools import aviso_gpu_reset as ag

pytestmark = pytest.mark.unit

CON = [
    "[   24.390647] host kernel: NVRM: _issueRpcAndWait: rpcRecvPoll timedout",
    "[   38.100000] host kernel: NVRM: Xid (PCI:000f:01:00): 154, GPU recovery action changed from 0x0 (None) to 0x1 (GPU Reset Required)",
]
SIN = [
    "[    1.000000] host kernel: NVRM: loading NVIDIA UNIX Open Kernel Module",
    "[   30.0] host kernel: NVRM: Xid (PCI:000f:01:00): 13, graphics exception",
]


def test_detecta_la_secuencia_y_no_otros_xid():
    assert ag.hechos(CON)["detectado"] is True
    assert ag.hechos(CON[:1])["detectado"] is True  # solo el timeout
    assert ag.hechos(CON[1:])["detectado"] is True  # solo el Xid 154
    assert ag.hechos(SIN)["detectado"] is False  # el control: Xid 13 no es 154
    assert ag.hechos([])["detectado"] is False


def _corre(monkeypatch, tmp_path, lineas, envia=True):
    monkeypatch.setattr(ag, "RUTA", tmp_path / "a.jsonl")
    boot_file = tmp_path / "boot_id"
    boot_file.write_text("boot-sintetico\n")
    monkeypatch.setattr(ag.reboot_verdict, "BOOT_ID_ACTUAL", boot_file)
    monkeypatch.setattr(ag, "lee_journal", lambda b: lineas)
    enviados = []
    monkeypatch.setattr(
        ag.aviso_termico, "enviar", lambda av: enviados.append(av) or envia
    )
    return ag.main([]), enviados


def test_una_vez_por_arranque(monkeypatch, tmp_path):
    assert _corre(monkeypatch, tmp_path, CON)[1] != []
    rc, enviados = _corre(monkeypatch, tmp_path, CON)
    assert rc == 0 and enviados == []  # segunda corrida: ya anotado
    filas = [json.loads(ln) for ln in (tmp_path / "a.jsonl").read_text().splitlines()]
    assert len(filas) == 1 and filas[0]["xid154"] is True


def test_sin_secuencia_no_avisa_ni_anota(monkeypatch, tmp_path):
    rc, enviados = _corre(monkeypatch, tmp_path, SIN)
    assert rc == 0 and enviados == [] and not (tmp_path / "a.jsonl").exists()


def test_aviso_fallido_no_anota_y_reintenta(monkeypatch, tmp_path):
    rc, _ = _corre(monkeypatch, tmp_path, CON, envia=False)
    assert rc == 1 and not (tmp_path / "a.jsonl").exists()
    assert (
        _corre(monkeypatch, tmp_path, CON)[0] == 0 and (tmp_path / "a.jsonl").exists()
    )


def test_journal_caido_es_could_not_run_no_limpio(monkeypatch, tmp_path):
    rc, enviados = _corre(monkeypatch, tmp_path, None)
    assert rc == 2 and enviados == []


def test_calidad_no_activa_aviso_sin_receptor_explicito():
    assert ag.aviso_calidad({}, receptor=None) is False


def test_aviso_calidad_sintetico_deduplica_reintenta_y_requiere_ack():
    estado = set()
    enviados = []
    receptor = lambda evento: enviados.append(evento) or True
    falla = lambda evento: False
    assert not ag.aviso_calidad({}, receptor=falla, clave="boot:calidad", estado=estado)
    assert not enviados
    assert ag.aviso_calidad({}, receptor=receptor, clave="boot:calidad", estado=estado)
    assert not ag.aviso_calidad({}, receptor=receptor, clave="boot:calidad", estado=estado)
    assert len(enviados) == 1


def test_aviso_sintetico_exige_parser_intervalo_calidad_boot_y_receptor():
    observaciones = [
        {"boot_id": "boot-a", "monotonic_s": 24.5, "estado": "reciente",
         "comparacion": "igual", "edad_contenido_s": 3.0},
        {"boot_id": "boot-a", "monotonic_s": 25.5, "estado": "reciente",
         "comparacion": "igual", "edad_contenido_s": 4.0},
    ]
    evento = {"tipo": "gpu_calidad", **observaciones[-1]}
    recibido = []
    kwargs = dict(boot_id="boot-a",
                  evidencia_boot_id="boot-a", lineas=CON[:1],
                  intervalo_sospecha=(24.0, 26.0), observaciones_calidad=observaciones,
                  ahora_monotonic=30.0, journal_legible=True, incertidumbre_s=0.1,
                  receptor=lambda e: recibido.append(e) or True,
                  clave="boot-a:calidad", estado=set())
    assert not ag.aviso_calidad_corrobora(evento, **{**kwargs, "receptor": None})
    assert not ag.aviso_calidad_corrobora(evento, **{**kwargs, "evidencia_boot_id": "boot-b"})
    assert ag.aviso_calidad_corrobora(evento, **kwargs)
    assert recibido == [evento]
    assert not ag.aviso_calidad_corrobora(evento, **{**kwargs, "lineas": SIN})
    assert not ag.aviso_calidad_corrobora(evento, **{**kwargs, "intervalo_sospecha": (1.0, 2.0)})
    assert not ag.aviso_calidad_corrobora(evento, **{**kwargs, "observaciones_calidad": []})
    assert not ag.aviso_calidad_corrobora(evento, **{**kwargs, "intervalo_sospecha": ()})
    futuras = [dict(o, monotonic_s=35.0, edad_contenido_s=8.0) for o in observaciones]
    assert not ag.aviso_calidad_corrobora(evento, **{**kwargs, "observaciones_calidad": futuras})
    assert recibido == [evento]


def test_corrobora_solo_firma_del_parser_en_intervalo_mismo_boot():
    assert ag.corroborar_gsp(boot_id="a", evidencia_boot_id="a", lineas=CON[:1],
        intervalo_sospecha=(24.0, 25.0), ahora_monotonic=30.0,
        journal_legible=True, incertidumbre_s=0.2)["estado"] == "confirmado"
    for cambios in (
        {"lineas": SIN}, {"evidencia_boot_id": "b"},
        {"intervalo_sospecha": (1.0, 2.0)}, {"journal_legible": False},
        {"incertidumbre_s": None},
    ):
        base = dict(boot_id="a", evidencia_boot_id="a", lineas=CON[:1],
            intervalo_sospecha=(24.0, 25.0), ahora_monotonic=30.0,
            journal_legible=True, incertidumbre_s=0.2)
        assert ag.corroborar_gsp(**{**base, **cambios})["estado"] == "desconocido"


def test_firma_antigua_no_oculta_timeout_valido_en_ventana():
    lineas = ["[    1.000000] host kernel: NVRM: _issueRpcAndWait: rpcRecvPoll timedout",
              CON[0]]
    resultado = ag.corroborar_gsp(
        boot_id="boot-a", evidencia_boot_id="boot-a", lineas=lineas,
        intervalo_sospecha=(24.0, 25.0), ahora_monotonic=30.0,
        journal_legible=True, incertidumbre_s=0.1)
    assert resultado["estado"] == "confirmado"
    assert resultado["evidencia_monotonic"] == 24.390647
