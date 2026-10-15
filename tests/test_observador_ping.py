"""tools/observador_ping.py: un ping por ejecucion y la hora de la ultima respuesta (FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01)."""

from __future__ import annotations

import contextlib
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


# --- variante NAS: sync por smbclient ---

T = 1_760_000_000
LOG_NAS = [f"{e} ok" for e in range(T, T + 5)] + [f"{e} fail" for e in range(T + 5, T + 9)] + [f"{e} ok" for e in range(T + 9, T + 12)]


def _cfg(tmp_path: Path, modo: int = 0o600) -> Path:
    cred = tmp_path / "cred"
    cred.write_text("username=u\npassword=SECRETO-NO-IMPRIMIR\n", encoding="utf-8")
    cred.chmod(modo)
    cfg = tmp_path / "externo" / "nas.json"
    cfg.parent.mkdir(exist_ok=True)
    cfg.write_text(json.dumps({"host": "nas.local", "share": "Public", "ruta": "bb/ping-atom.log", "credenciales": str(cred)}), encoding="utf-8")
    return cfg


def _smb(lineas: list[str] | None, rc: int = 0, visto: list[Any] | None = None) -> Any:
    """smbclient de mentira: escribe `lineas` en el destino del `get` (o falla con `rc`)."""

    def correr(args: list[str], **kw: Any) -> Any:
        if visto is not None:
            visto.append(args)
        if lineas is not None:  # con rc != 0 deja igualmente un archivo: el rc es lo que manda
            Path(args[-1].rsplit('" "', 1)[1].rstrip('"')).write_text("\n".join(lineas) + "\n", encoding="utf-8")
        return types.SimpleNamespace(returncode=rc, stdout="", stderr="")

    return correr


def _filas(ruta: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines()]


def test_sync_mezcla_y_es_idempotente(tmp_path: Path) -> None:
    cfg, ruta = _cfg(tmp_path), tmp_path / "externo" / "ping.jsonl"
    r1 = o.sync(cfg, ruta, _smb(LOG_NAS), ahora=T + 20)
    assert (r1["estado"], r1["nuevas"], r1["descartadas"]) == ("OK", 12, 0)
    r2 = o.sync(cfg, ruta, _smb(LOG_NAS), ahora=T + 21)
    assert (r2["estado"], r2["nuevas"]) == ("OK", 0)  # control negativo: repetir no anade filas
    assert len(_filas(ruta)) == 12
    r3 = o.sync(cfg, ruta, _smb([*LOG_NAS, f"{T + 12} ok"]), ahora=T + 22)
    assert r3["nuevas"] == 1 and len(_filas(ruta)) == 13  # control positivo: una linea nueva si entra


def test_sync_descarta_y_cuenta_lineas_rotas(tmp_path: Path) -> None:
    cfg, ruta = _cfg(tmp_path), tmp_path / "externo" / "ping.jsonl"
    sucio = [f"{T} ok", "basura", f"{T + 1} o", "17600000", f"{T + 2} maybe", f"{T + 3} fail", f"{T + 4} fa"]  # la ultima: truncada
    r = o.sync(cfg, ruta, _smb(sucio), ahora=T + 10)
    assert (r["nuevas"], r["descartadas"]) == (2, 5)
    assert [f["epoch"] for f in _filas(ruta)] == [T, T + 3]


def test_sync_nas_caido_es_not_collected_y_no_toca_ping(tmp_path: Path) -> None:
    cfg, ruta = _cfg(tmp_path), tmp_path / "externo" / "ping.jsonl"
    ruta.write_text('{"epoch": 1, "ok": true}\n', encoding="utf-8")
    antes = ruta.read_bytes()
    for correr in (_smb(None, rc=1), _smb(LOG_NAS, rc=1), _smb(None, rc=0), _cae, _smb([]), _smb(["basura"])):
        r = o.sync(cfg, ruta, correr, ahora=T)
        assert r["estado"] == "NOT_COLLECTED" and r["nuevas"] == 0 and "motivo" in r
        assert ruta.read_bytes() == antes
    assert json.loads((ruta.parent / "sync.json").read_text(encoding="utf-8"))["estado"] == "NOT_COLLECTED"
    assert o.sync(tmp_path / "no-existe.json", ruta, _smb(LOG_NAS), ahora=T)["estado"] == "NOT_COLLECTED"  # sin config
    assert ruta.read_bytes() == antes


def test_sync_rehusa_credenciales_abiertas_y_no_las_imprime(tmp_path: Path) -> None:
    ruta = tmp_path / "externo" / "ping.jsonl"
    visto: list[Any] = []
    r = o.sync(_cfg(tmp_path, 0o644), ruta, _smb(LOG_NAS, visto=visto), ahora=T)
    assert r["estado"] == "NOT_COLLECTED" and "600" in r["motivo"] and not visto and not ruta.exists()  # smbclient ni se invoco
    r = o.sync(_cfg(tmp_path), ruta, _smb(LOG_NAS, visto=visto), ahora=T + 12)
    assert r["estado"] == "OK" and "-A" in visto[0]
    assert "SECRETO" not in json.dumps(r) + (ruta.parent / "sync.json").read_text(encoding="utf-8") + ruta.read_text(encoding="utf-8")


def test_sync_log_que_no_avanza_es_obsoleto(tmp_path: Path) -> None:
    cfg, ruta = _cfg(tmp_path), tmp_path / "externo" / "ping.jsonl"
    r = o.sync(cfg, ruta, _smb(LOG_NAS), ahora=T + 11 + 3600)
    assert r["estado"] == "OBSOLETO" and r["nuevas"] == 12  # se guarda lo que hay, pero no se declara OK


def test_hueco_en_el_nas_da_la_ultima_respuesta_anterior_al_corte(tmp_path: Path) -> None:
    """Extremo a extremo: pings hasta T+4, el NAS ve fallos (la ATOM cayo), vuelven en T+9; con el corte en T+7 la ultima respuesta es T+4."""
    cfg, ruta = _cfg(tmp_path), tmp_path / "externo" / "ping.jsonl"
    o.sync(cfg, ruta, _smb(LOG_NAS), ahora=T + 12)
    assert o.ultima_respuesta(ruta, T + 7) == T + 4
    assert o.ultima_respuesta(ruta, T + 11) == T + 11  # control: tras reanudar, la respuesta es la nueva
    # el NAS mismo callo (sin lineas en el hueco): tampoco inventa respuestas
    o2 = tmp_path / "otro.jsonl"
    o.sync(cfg, o2, _smb([f"{e} ok" for e in range(T, T + 5)] + [f"{e} ok" for e in range(T + 9, T + 12)]), ahora=T + 12)
    assert o.ultima_respuesta(o2, T + 7) == T + 4
    assert o.ultima_respuesta(tmp_path / "ausente.jsonl", T + 7) is None  # archivo ausente: sin cobertura, no "sin huecos"


STUB = """#!/bin/sh
[ -n "$SMB_FALLA" ] && exit 1
dest=${5##* }
dest=${dest#\\"}
dest=${dest%\\"}
cp FIXTURE "$dest"
"""


def test_sync_con_smbclient_en_el_path_y_main(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    fix = tmp_path / "fixture.log"
    fix.write_text("\n".join(LOG_NAS) + "\n", encoding="utf-8")
    stub = bin_ / "smbclient"
    stub.write_text(STUB.replace("FIXTURE", str(fix)), encoding="utf-8")
    stub.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_}:/usr/bin:/bin")
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    _cfg(tmp_path)
    assert o.main(["--sync"]) == 0 and json.loads(capsys.readouterr().out)["estado"] == "off"  # interruptor apagado: no trae
    (tmp_path / "interruptores.json").write_text(json.dumps({"modos": {"observador_ping": "observar"}}), encoding="utf-8")
    assert o.main(["--sync"]) == 1  # el log del fixture es viejo: llega, pero OBSOLETO, rc != 0
    assert json.loads(capsys.readouterr().out)["nuevas"] == 12
    monkeypatch.setenv("SMB_FALLA", "1")
    assert o.main(["--sync"]) == 1 and json.loads(capsys.readouterr().out)["estado"] == "NOT_COLLECTED"
    assert len(_filas(tmp_path / "externo" / "ping.jsonl")) == 12


SCRIPT = Path(__file__).resolve().parent.parent / "adopted" / "nas" / "bb-ping-atom.sh"


def _corre_script(log: Path, ip: str, segundos: float, **env: str) -> list[str]:
    e = {"PATH": "/usr/bin:/bin", "BB_ATOM_IP": ip, "BB_LOG": str(log), **env}
    p = subprocess.Popen(["/bin/sh", str(SCRIPT)], env=e, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with contextlib.suppress(subprocess.TimeoutExpired):
        p.wait(timeout=segundos)  # el script no termina solo: se le da el tiempo y se le manda SIGTERM
    p.terminate()
    p.wait(timeout=5)
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def test_script_nas_una_linea_por_segundo_ok_y_fail_con_rotacion(tmp_path: Path) -> None:
    ok = _corre_script(tmp_path / "ok.log", "127.0.0.1", 3.5)
    assert 3 <= len(ok) <= 5 and all(ln.endswith(" ok") and ln.split()[0].isdigit() for ln in ok)
    assert len({ln.split()[0] for ln in ok}) == len(ok)  # a lo sumo una linea por segundo
    mal = _corre_script(tmp_path / "mal.log", "192.0.2.1", 3.5)  # control negativo: destino que no responde
    assert mal and all(ln.endswith(" fail") for ln in mal)
    rot = _corre_script(tmp_path / "rot.log", "127.0.0.1", 5.5, BB_MAX_LINEAS="3", BB_CADA_N="2")
    assert 0 < len(rot) <= 4  # sin rotacion habria 5 o mas lineas
    assert not (tmp_path / "rot.log.lock").exists()  # el trap limpia el bloqueo
