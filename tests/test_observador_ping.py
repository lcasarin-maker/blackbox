"""tools/observador_ping.py: un ping por ejecucion y la hora de la ultima respuesta (FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01)."""

from __future__ import annotations

import json
import subprocess
import types
from pathlib import Path
from typing import Any

import pytest

from tools import observador_ping as o


def _rc(rc: int) -> Any:
    return lambda args, **kw: types.SimpleNamespace(returncode=rc, stdout="")


def _cae(args: list[str], **kw: Any) -> Any:
    raise subprocess.TimeoutExpired(args, 5)


def test_sondea_distingue_respuesta_de_silencio_y_de_fallo_del_comando() -> None:
    assert o.sondea("10.0.0.1", _rc(0)) == {"ok": True}
    assert o.sondea("10.0.0.1", _rc(1)) == {"ok": False}
    assert o.sondea("10.0.0.1", _cae) == {"ok": False, "error": "TimeoutExpired"}
    assert o.sondea("10.0.0.1", lambda a, **k: (_ for _ in ()).throw(FileNotFoundError("ping")))["error"] == "FileNotFoundError"


def test_paso_off_no_sondea_y_on_anade_filas(tmp_path: Path) -> None:
    ruta = tmp_path / "externo" / "ping.jsonl"
    assert o.paso("off", "x", ruta, _cae) is None and not ruta.exists()
    o.paso("observar", "x", ruta, _rc(0), ahora=100.0)
    o.paso("observar", "x", ruta, _rc(1), ahora=101.0)
    assert [json.loads(x)["ok"] for x in ruta.read_text(encoding="utf-8").splitlines()] == [True, False]


def test_ultima_respuesta_es_la_ultima_ok_antes_del_corte(tmp_path: Path) -> None:
    ruta = tmp_path / "p.jsonl"
    assert o.ultima_respuesta(ruta, 1000) is None  # sin archivo
    filas = [{"epoch": 998, "ok": True}, {"epoch": 999, "ok": True}, {"epoch": 1000.5, "ok": False}, {"epoch": 1001, "ok": True}]
    ruta.write_text("{roto\n" + "\n".join(json.dumps(f) for f in filas) + "\n", encoding="utf-8")
    assert o.ultima_respuesta(ruta, 1000) == 999  # ignora la linea rota, la fila fallida y la posterior al corte
    assert o.ultima_respuesta(ruta, 997) is None  # nada anterior: sin cobertura
    ruta.write_text(json.dumps({"epoch": 5, "ok": False}) + "\n", encoding="utf-8")
    assert o.ultima_respuesta(ruta, 1000) is None  # solo silencios: no hay respuesta que reportar


def test_main_sin_argumentos_sin_config_y_con_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    assert o.main([]) == 2
    assert o.main(["--paso"]) == 1 and "observador.json" in capsys.readouterr().err
    (tmp_path / "externo").mkdir()
    (tmp_path / "externo" / "observador.json").write_text(json.dumps({"destino": "10.0.0.1"}), encoding="utf-8")
    monkeypatch.setattr(o, "paso", lambda modo, destino, ruta, correr=subprocess.run, ahora=None: {"modo": modo, "destino": destino})
    assert o.main(["--paso"]) == 0 and json.loads(capsys.readouterr().out.strip().splitlines()[-1])["destino"] == "10.0.0.1"
