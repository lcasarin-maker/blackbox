"""tools/monitor_distros.py: compara fuentes de distros alternas y publica un hallazgo solo cuando hay cambio (FEATURE-MONITOR-DISTROS-ALTERNAS-GB10-01)."""

from __future__ import annotations

import json
import subprocess
import types
from pathlib import Path
from typing import Any

import pytest

from tools import hallazgo, interruptores
from tools import monitor_distros as m

SHA_A, SHA_B = "a" * 40, "b" * 40
REPO = {"id": "graham33-nixos", "tipo": "repo", "url": "https://github.com/graham33/nixos-dgx-spark"}
HILO = {"id": "foro-349124", "tipo": "hilo", "url": "https://forums.developer.nvidia.com/t/has-anyone-tried-an-alternative-linux-distro/349124"}
GUIA = {"id": "kairos", "tipo": "guia", "url": "https://kairos.io/docs/installation/nvidia_dgx_spark/"}


def _git(sha: str, rc: int = 0) -> Any:
    def f(args: list[str], **kw: Any) -> Any:
        return types.SimpleNamespace(returncode=rc, stdout=f"{sha}\tHEAD\n" if sha else "")
    return f


def _cae(args: list[str], **kw: Any) -> Any:
    raise subprocess.TimeoutExpired(args, 30)


def _abre(posts: int) -> Any:
    return lambda url: json.dumps({"posts_count": posts}).encode()


def _abre_roto(url: str) -> bytes:
    raise OSError("sin red")


def test_lee_repo_hilo_y_lo_que_no_se_pudo() -> None:
    assert m.lee(REPO, _git(SHA_A)) == SHA_A
    assert m.lee(HILO, abre=_abre(42)) == "posts=42"
    assert m.lee(REPO, _git("")).startswith("NOT_COLLECTED")  # rc 0 sin cabeza
    assert m.lee(REPO, _git(SHA_A, rc=128)).startswith("NOT_COLLECTED")  # el sha de un rc distinto de 0 no vale
    assert m.lee(REPO, _cae).startswith("NOT_COLLECTED")
    assert m.lee(HILO, abre=_abre_roto).startswith("NOT_COLLECTED")
    assert m.lee(HILO, abre=lambda u: b"no es json").startswith("NOT_COLLECTED")
    assert m.lee({**HILO, "url": "https://otro.example/t/1"}, abre=_abre(1)).startswith("NOT_COLLECTED")  # el hilo debe ser del foro de NVIDIA
    assert "sin comparador" in m.lee(GUIA)


def test_compara_nunca_confunde_no_recogido_con_sin_cambio() -> None:
    assert m.compara(None, SHA_A) == "primera_lectura"
    assert m.compara(SHA_A, SHA_A) == "sin_cambio"
    assert m.compara(SHA_A, SHA_B) == "cambio"
    assert m.compara(SHA_A, "NOT_COLLECTED: x") == "no_recogido"
    assert m.compara("NOT_COLLECTED: x", SHA_A) == "primera_lectura"


def _paso(tmp_path: Path, modo: str, correr: Any, fuentes: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    return m.paso(modo, fuentes or [REPO, GUIA], tmp_path / "estado.json", m.Entorno(correr, _abre(1), tmp_path / "bandeja", tmp_path / "reg", "2026-10-13"))


def test_off_no_lee_ni_escribe(tmp_path: Path) -> None:
    assert _paso(tmp_path, "off", _cae) is None
    assert not (tmp_path / "estado.json").exists()


def test_primera_pasada_sin_cambio_y_cambio_con_control_negativo(tmp_path: Path) -> None:
    ev = _paso(tmp_path, "observar", _git(SHA_A))
    assert ev is not None and ev["veredictos"] == {"graham33-nixos": "primera_lectura", "kairos": "no_recogido"} and ev["habria_actuado"] is False
    assert ev["no_recogidas"] == ["kairos"] and not (tmp_path / "bandeja").exists()  # una fuente sin actividad no genera hallazgo
    ev = _paso(tmp_path, "observar", _git(SHA_A))
    assert ev is not None and ev["veredictos"]["graham33-nixos"] == "sin_cambio" and not (tmp_path / "bandeja").exists()
    ev = _paso(tmp_path, "observar", _git(SHA_B))
    assert ev is not None and ev["veredictos"]["graham33-nixos"] == "cambio" and ev["habria_actuado"] is True
    publicados = list((tmp_path / "bandeja").glob("*.md"))
    assert len(publicados) == 1 and hallazgo.valida(publicados[0].read_text(encoding="utf-8")) == []
    assert SHA_A in publicados[0].read_text(encoding="utf-8") and SHA_B in publicados[0].read_text(encoding="utf-8")


def test_una_lectura_fallida_no_pisa_la_marca_guardada(tmp_path: Path) -> None:
    _paso(tmp_path, "actuar", _git(SHA_A), [REPO])
    ev = _paso(tmp_path, "actuar", _cae, [REPO])
    assert ev is not None and ev["veredictos"] == {"graham33-nixos": "no_recogido"}
    assert json.loads((tmp_path / "estado.json").read_text(encoding="utf-8")) == {"graham33-nixos": SHA_A}


def test_estado_ilegible_arranca_de_cero(tmp_path: Path) -> None:
    (tmp_path / "estado.json").write_text("{roto", encoding="utf-8")
    ev = _paso(tmp_path, "observar", _git(SHA_A), [REPO])
    assert ev is not None and ev["veredictos"]["graham33-nixos"] == "primera_lectura"


def test_la_lista_versionada_es_valida_y_main_forzado(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    fuentes = json.loads(m.FUENTES.read_text(encoding="utf-8"))
    assert fuentes["esquema"] == "bb-fuentes/1" and len(fuentes["fuentes"]) == 15 and {f["tipo"] for f in fuentes["fuentes"]} <= {"repo", "hilo", "guia", "articulo"}
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    monkeypatch.setattr(m, "lee", lambda f, correr=subprocess.run, abre=m._abre: "NOT_COLLECTED: prueba")
    assert m.main(["--forzar"]) == 0
    assert json.loads(capsys.readouterr().out)["modo"] == "observar"
    assert interruptores.modo(m.NOMBRE) == "off"  # --forzar no cambia el interruptor
    assert m.main(["--paso"]) == 0 and capsys.readouterr().out.strip() == "null"


def test_abre_real_lee_una_url_local(tmp_path: Path) -> None:
    (tmp_path / "x.json").write_text("{}", encoding="utf-8")
    assert m._abre((tmp_path / "x.json").as_uri()) == b"{}"
