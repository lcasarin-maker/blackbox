"""Rotacion por tamano de portero.jsonl (DEBT-PORTERO-LOG-SIN-ROTACION-CON-OBSERVAR-DE-LIBREOFFICE-01).

`_registra` pasa el log vivo a `portero.jsonl.1` (una sola generacion) cuando supera `LOG_TOPE_BYTES`, y sigue sin
lanzar nunca hacia el demonio, tambien cuando la rotacion falla.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import threading
import types
from pathlib import Path

import pytest

from tools import portero as po

TOPE = 4_000  # bytes: unas 60 filas de las de abajo, para rotar varias veces en un test corto


def _filas(p: Path) -> list[dict[str, object]]:
    if not p.exists():
        return []
    return [json.loads(linea) for linea in p.read_text(encoding="utf-8").splitlines()]


@pytest.mark.unit
def test_rota_a_una_sola_generacion_y_lo_que_cae_es_lo_mas_viejo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(po, "LOG_TOPE_BYTES", TOPE)
    log = tmp_path / "portero.jsonl"
    for i in range(500):
        po._registra({"accion": "x", "n": i}, log)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["portero.jsonl", "portero.jsonl.1"]
    assert log.stat().st_size <= TOPE + 200 and (tmp_path / "portero.jsonl.1").stat().st_size <= TOPE + 200
    ns = [int(str(f["n"])) for f in _filas(tmp_path / "portero.jsonl.1") + _filas(log)]
    assert ns == list(range(ns[0], 500)), "lo que sobrevive es un sufijo contiguo que termina en la ultima fila"
    assert ns[0] > 0, "la primera fila (la mas vieja) es la que se descarta"


@pytest.mark.unit
def test_control_negativo_bajo_el_tope_no_rota_y_no_pierde_nada(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(po, "LOG_TOPE_BYTES", 10 * TOPE)
    log = tmp_path / "portero.jsonl"
    for i in range(30):
        po._registra({"accion": "x", "n": i}, log)
    assert not (tmp_path / "portero.jsonl.1").exists()
    assert [f["n"] for f in _filas(log)] == list(range(30))


@pytest.mark.unit
def test_si_la_rotacion_falla_no_lanza_y_la_fila_queda_escrita(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                               capsys: pytest.CaptureFixture[str]):
    monkeypatch.setattr(po, "LOG_TOPE_BYTES", TOPE)
    d = tmp_path / "ro"
    d.mkdir()
    log = d / "portero.jsonl"
    log.write_text(json.dumps({"accion": "viejo", "relleno": "x" * TOPE}) + "\n", encoding="utf-8")
    d.chmod(0o555)  # el archivo se puede anexar, pero el directorio no deja renombrar
    try:
        po._registra({"accion": "nueva"}, log)
        assert [f["accion"] for f in _filas(log)] == ["viejo", "nueva"]
        assert not (d / "portero.jsonl.1").exists()
    finally:
        d.chmod(0o755)
    assert "no se pudo rotar" in capsys.readouterr().err


@pytest.mark.unit
def test_dos_escritores_a_la_vez_no_cortan_filas_ni_pierden_una_generacion(tmp_path: Path,
                                                                           monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(po, "LOG_TOPE_BYTES", TOPE)
    log = tmp_path / "portero.jsonl"
    hilos, n = 4, 400

    def escribe(h: int) -> None:
        for i in range(n):
            po._registra({"accion": "x", "h": h, "n": i, "relleno": "y" * 20}, log)

    ts = [threading.Thread(target=escribe, args=(h,)) for h in range(hilos)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["portero.jsonl", "portero.jsonl.1"]
    filas = _filas(tmp_path / "portero.jsonl.1") + _filas(log)  # json.loads revienta ante una fila cortada
    for h in range(hilos):
        ns = [int(str(f["n"])) for f in filas if f["h"] == h]
        # Lo que sobrevive es un sufijo del orden global, asi que por hilo es un sufijo contiguo: un hueco seria una
        # generacion `.1` pisada por una rotacion concurrente.
        assert ns == list(range(n - len(ns), n)), f"hilo {h}: hueco en {ns[:5]}..{ns[-5:]}"


@pytest.mark.unit
def test_estado_muestra_los_ultimos_eventos_aunque_el_log_vivo_acabe_de_rotar(tmp_path: Path,
                                                                              monkeypatch: pytest.MonkeyPatch,
                                                                              capsys: pytest.CaptureFixture[str]):
    log = tmp_path / "portero.jsonl"
    (tmp_path / "portero.jsonl.1").write_text(
        "".join(json.dumps({"accion": "x", "n": i}) + "\n" for i in range(20)), encoding="utf-8")
    log.write_text(json.dumps({"accion": "x", "n": 20}) + "\n", encoding="utf-8")
    monkeypatch.setattr(po, "LOG", log)
    monkeypatch.setattr(po, "lee_estado", lambda: po.Estado(None, None, None, None))
    monkeypatch.setattr(po, "observar", lambda: None)
    monkeypatch.setattr(po.interruptores, "modo", lambda _n: "observar")
    po.cmd_estado(argparse.Namespace())
    salida = json.loads(capsys.readouterr().out)
    assert [e["n"] for e in salida["ultimos_eventos"]] == list(range(11, 21))


@pytest.mark.unit
def test_si_otro_escritor_rota_mientras_se_espera_el_candado_la_fila_va_al_log_nuevo(tmp_path: Path,
                                                                                    monkeypatch: pytest.MonkeyPatch):
    """La carrera de dos procesos (demonio y `bb portero run`), hecha determinista: mientras este escritor espera el
    candado, otro rota el log y anexa una fila al nuevo. Sin el chequeo de inodo la fila caeria en el archivo ya
    rotado y la rotacion siguiente pisaria `.1` con el log nuevo: se perderia una generacion entera."""
    monkeypatch.setattr(po, "LOG_TOPE_BYTES", TOPE)
    log = tmp_path / "portero.jsonl"
    anterior = tmp_path / "portero.jsonl.1"
    log.write_text(json.dumps({"accion": "generacion_vieja", "relleno": "x" * TOPE}) + "\n", encoding="utf-8")
    llamadas: list[int] = []

    def flock_con_carrera(fh: object, op: int) -> None:
        if not llamadas:  # la primera espera: el otro escritor rota y anexa
            os.replace(log, anterior)
            log.write_text(json.dumps({"accion": "del_otro"}) + "\n", encoding="utf-8")
        llamadas.append(op)

    monkeypatch.setattr(po, "fcntl", types.SimpleNamespace(flock=flock_con_carrera, LOCK_EX=fcntl.LOCK_EX))
    po._registra({"accion": "mia"}, log)
    assert [f["accion"] for f in _filas(anterior)] == ["generacion_vieja"]
    assert [f["accion"] for f in _filas(log)] == ["del_otro", "mia"]


@pytest.mark.unit
def test_otro_proceso_espera_el_candado_y_anexa_al_log_que_quedo_tras_rotar(tmp_path: Path):
    """La misma carrera con dos PROCESOS reales: este test sostiene el flock como lo haria el demonio a mitad de una
    rotacion; un `_registra` en otro proceso debe esperar y, al soltarse, anexar al log nuevo, no al rotado."""
    log = tmp_path / "portero.jsonl"
    anterior = tmp_path / "portero.jsonl.1"
    log.write_text(json.dumps({"accion": "generacion_vieja"}) + "\n", encoding="utf-8")
    raiz = Path(__file__).resolve().parent.parent
    codigo = f"from pathlib import Path; from tools import portero as po; po._registra({{'accion': 'mia'}}, Path({str(log)!r}))"
    with log.open("a", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        hijo = subprocess.Popen([sys.executable, "-c", codigo], cwd=raiz)
        try:
            with pytest.raises(subprocess.TimeoutExpired):
                hijo.wait(timeout=1.5)  # sin candado el hijo ya habria escrito y salido
            os.replace(log, anterior)
            log.write_text(json.dumps({"accion": "del_otro"}) + "\n", encoding="utf-8")
        except BaseException:
            hijo.kill()
            raise
    assert hijo.wait(timeout=30) == 0
    assert [f["accion"] for f in _filas(anterior)] == ["generacion_vieja"]
    assert [f["accion"] for f in _filas(log)] == ["del_otro", "mia"]
