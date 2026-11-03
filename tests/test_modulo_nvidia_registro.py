"""Registro del modulo nvidia por arranque: solo-lectura por defecto, anexa con --escribe, idempotente por boot_id."""

import hashlib
import json

import pytest

from tools import modulo_nvidia_registro as mn

pytestmark = pytest.mark.unit

BID = "0123456789abcdef0123456789abcdef"


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    ko = tmp_path / "lib/modules/7.0.0-1024-nvidia/updates/nvidia.ko"
    ko.parent.mkdir(parents=True)
    ko.write_bytes(b"modulo")
    sysm = tmp_path / "sys_nvidia"
    sysm.mkdir()
    (sysm / "version").write_text("580.178.04\n")
    (sysm / "srcversion").write_text("SRC123\n")
    (tmp_path / "boot_id").write_text("01234567-89ab-cdef-0123-456789abcdef\n")
    monkeypatch.setattr(mn, "SALIDA", tmp_path / "salida.jsonl")
    monkeypatch.setattr(mn, "SYS_MODULO", sysm)
    monkeypatch.setattr(mn, "BOOT_ID", tmp_path / "boot_id")
    monkeypatch.setattr(mn, "_modinfo", lambda campo: str(ko) if campo == "-n" else "SRC123")
    return ko


def test_sin_escribe_imprime_la_linea_y_no_toca_disco(mundo, capsys):
    assert mn.main([]) == 0
    linea = json.loads(capsys.readouterr().out)
    assert linea["boot_id"] == BID and linea["parchado"] is True and linea["srcversion"] == "SRC123"
    assert linea["sha256"] == hashlib.sha256(b"modulo").hexdigest()
    assert not mn.SALIDA.exists()


def test_escribe_anexa_una_vez_por_boot_id(mundo):
    assert mn.main(["--escribe"]) == 0
    assert mn.main(["--escribe"]) == 0
    assert len(mn.SALIDA.read_text().splitlines()) == 1
    # control negativo: otro boot_id si anexa, y la linea previa se conserva
    mn.BOOT_ID.write_text("ffffffff-89ab-cdef-0123-456789abcdef\n")
    assert mn.main(["--escribe"]) == 0
    assert len(mn.SALIDA.read_text().splitlines()) == 2


def test_ruta_de_fabrica_no_es_parchada(mundo, monkeypatch):
    monkeypatch.setattr(mn, "_modinfo", lambda c: str(mundo.parent.parent / "kernel/nvidia.ko") if c == "-n" else "S")
    assert mn.lee_modulo()["parchado"] is False


def test_modulo_no_cargado_no_escribe_y_modinfo_caido_se_declara(mundo, monkeypatch):
    monkeypatch.setattr(mn, "SYS_MODULO", mundo.parent / "no_cargado")
    assert mn.main(["--escribe"]) == 1 and not mn.SALIDA.exists()
    monkeypatch.setattr(mn, "_modinfo", lambda c: "NOT_COLLECTED: modinfo caido")
    m = mn.lee_modulo()
    assert m["sha256"].startswith("NOT_COLLECTED") and m["parchado"].startswith("NOT_COLLECTED")


def test_sin_boot_id_es_could_not_run(mundo, capsys):
    mn.BOOT_ID.unlink()
    assert mn.main([]) == 2 and "COULD_NOT_RUN" in capsys.readouterr().err
