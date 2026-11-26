"""Tests para FEATURE-TRAE-TESTIGO-INCREMENTAL-01."""
from __future__ import annotations

import hashlib
import json

from tools.observador_ping import trae_testigo_incremental


def test_trae_testigo_incremental_solo_bytes_nuevos_y_no_recopia_rotados(tmp_path):
    cfg = tmp_path / "testigo.json"
    cfg.write_text(json.dumps({"origen": "user@192.0.2.10", "ruta": "/bb"}), encoding="utf-8")
    dest = tmp_path / "testigo"

    remoto = {
        "ping.jsonl": b'{"epoch":1}\n{"epoch":2}\n',
        "alarma.jsonl": b'{"ok":true}\n',
        "ping.jsonl.1": b'{"epoch":0}\n',
    }
    sha_rotado = hashlib.sha256(remoto["ping.jsonl.1"]).hexdigest()
    llamadas_rango: list[tuple[str, int]] = []

    def listar(_cfg):
        return [
            {"nombre": k, "tamano": len(v), "sha256": hashlib.sha256(v).hexdigest()}
            for k, v in remoto.items()
        ]

    def leer(_cfg, nombre: str, offset: int) -> bytes:
        llamadas_rango.append((nombre, offset))
        return remoto[nombre][offset:]

    r1 = trae_testigo_incremental(cfg, dest, listar_remoto=listar, leer_rango=leer, ahora=100.0)
    assert r1["estado"] == "OK"
    assert r1["bytes_transferidos"] == sum(len(v) for v in remoto.values())
    assert "alarma.jsonl" in r1["archivos"]

    # Segunda corrida sin cambios: 0 bytes transferidos y rotado no se vuelve a pedir
    llamadas_rango.clear()
    r2 = trae_testigo_incremental(cfg, dest, listar_remoto=listar, leer_rango=leer, ahora=110.0)
    assert r2["estado"] == "OK"
    assert r2["bytes_transferidos"] == 0
    assert llamadas_rango == []

    # Llega una nueva linea a ping.jsonl: solo transfiere el delta
    nueva_linea = b'{"epoch":3}\n'
    remoto["ping.jsonl"] += nueva_linea
    llamadas_rango.clear()
    r3 = trae_testigo_incremental(cfg, dest, listar_remoto=listar, leer_rango=leer, ahora=120.0)
    assert r3["estado"] == "OK"
    assert r3["bytes_transferidos"] == len(nueva_linea)
    assert (dest / "ping.jsonl").read_bytes() == remoto["ping.jsonl"]
    assert ("ping.jsonl.1", 0) not in llamadas_rango
    assert hashlib.sha256((dest / "ping.jsonl.1").read_bytes()).hexdigest() == sha_rotado


def test_control_negativo_fallo_transporte_conserva_archivo_previo(tmp_path):
    cfg = tmp_path / "testigo.json"
    cfg.write_text(json.dumps({"origen": "user@192.0.2.10", "ruta": "/bb"}), encoding="utf-8")
    dest = tmp_path / "testigo"
    dest.mkdir()
    (dest / "ping.jsonl").write_bytes(b"previo\n")

    def listar(_cfg):
        return [{"nombre": "ping.jsonl", "tamano": 20}]

    def leer_fail(_cfg, _nombre: str, _offset: int) -> bytes:
        raise RuntimeError("scp cortado")

    r = trae_testigo_incremental(cfg, dest, listar_remoto=listar, leer_rango=leer_fail, ahora=200.0)
    assert r["estado"] == "NOT_COLLECTED"
    assert "scp cortado" in r["motivo"]
    assert (dest / "ping.jsonl").read_bytes() == b"previo\n"
