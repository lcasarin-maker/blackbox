"""apt_arm64_evidence: cada rama de verify_capture sobre capturas falsas, con el camino 'pass' como control negativo."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from tools.apt_arm64_evidence import verify_capture

ID = "DELTA-FORUM-APT-ARM64-SOURCE-VALIDATION-01"
SUMMARY = "5 upgraded, 0 newly installed, 0 to remove and 0 not upgraded."


def _row(argv: list[str], out: str = "", err: str = "", rc: int = 0) -> dict[str, Any]:
    return {"argv": argv, "exit_code": rc, "stdout": out, "stderr": err}


def _buenas() -> list[dict[str, Any]]:
    return [
        _row(["dpkg", "--print-architecture"], "arm64\n"),
        _row(["cat", "/etc/apt/sources.list.d/ubuntu.sources"], "URIs: http://ports.ubuntu.com/ubuntu-ports\n"),
        _row(["apt-get", "indextargets"], "x|http://ports.ubuntu.com/ubuntu-ports|arm64|Packages\n"),
        _row(["gpgv", "noble-updates_InRelease"], err="Good signature from x"),
        _row(["apt-get", "-s", "-o", "k=v", "upgrade"], SUMMARY),
        _row(["gpgv", "/tmp/bad_InRelease"], err="BAD signature", rc=1),
    ]


def _escribe(tmp_path: Path, rows: Any, ident: str = ID) -> Path:
    p = tmp_path / "cap.json"
    p.write_text(json.dumps({"id": ident, "commands": rows}), encoding="utf-8")
    return p


def _con(tmp_path: Path, i: int, **cambios: Any) -> dict[str, Any]:
    rows = copy.deepcopy(_buenas())
    rows[i].update(cambios)
    return verify_capture(_escribe(tmp_path, rows))


def test_captura_buena_deja_el_hueco_del_negativo_de_fuente_sin_correr(tmp_path: Path) -> None:
    out = verify_capture(_escribe(tmp_path, _buenas()))
    assert out["status"] == "unknown" and out["could_not_run"] == 1 and out["fail"] == 0
    assert out["checks"]["bad_signature_negative"] == "pass" and out["checks"]["bad_source_negative"] == "unknown"


def test_captura_ilegible_o_malformada_es_unknown(tmp_path: Path) -> None:
    assert verify_capture(tmp_path / "no_existe.json")["status"] == "unknown"
    malo = tmp_path / "m.json"
    malo.write_text("{no json", encoding="utf-8")
    assert verify_capture(malo)["reason"].startswith("raw command capture unavailable")


def test_identidad_filas_faltantes_o_invalidas(tmp_path: Path) -> None:
    assert verify_capture(_escribe(tmp_path, _buenas(), ident="otro"))["status"] == "fail"
    assert verify_capture(_escribe(tmp_path, "no lista"))["reason"] == "raw command rows missing"
    invalida = verify_capture(_escribe(tmp_path, [{"argv": "x"}]))
    assert invalida["status"] == "fail" and "invalid raw argv" in invalida["reason"]


def test_arquitectura(tmp_path: Path) -> None:
    assert _con(tmp_path, 0, exit_code=1)["status"] == "unknown"
    amd = _con(tmp_path, 0, stdout="amd64\n")
    assert amd["status"] == "fail" and amd["checks"]["architecture"] == "fail"


def test_fuente_ubuntu(tmp_path: Path) -> None:
    assert _con(tmp_path, 1, exit_code=1)["status"] == "unknown"
    assert _con(tmp_path, 1, stdout="URIs: http://archive.ubuntu.com/ubuntu\n")["checks"]["ubuntu_source"] == "fail"
    sin_pruebas = _con(tmp_path, 1, stdout="URIs: otra\n")
    assert sin_pruebas["status"] == "unknown" and sin_pruebas["reason"] == "compatible Ubuntu ports source not proven"


def test_indice_y_firma(tmp_path: Path) -> None:
    assert _con(tmp_path, 2, exit_code=1)["reason"].startswith("effective APT index")
    sin_tupla = _con(tmp_path, 2, stdout="x|http://ports.ubuntu.com/ubuntu-ports|amd64|Packages\n")
    assert sin_tupla["status"] == "fail" and sin_tupla["checks"]["effective_index"] == "fail"
    assert _con(tmp_path, 3, stderr="nada")["reason"].startswith("successful signature")
    assert _con(tmp_path, 3, exit_code=2)["status"] == "unknown"


def test_simulacion(tmp_path: Path) -> None:
    assert _con(tmp_path, 4, exit_code=1)["reason"] == "read-only upgrade simulation unavailable"
    assert _con(tmp_path, 4, stdout="sin resumen")["reason"].endswith("unparseable")
    quita = _con(tmp_path, 4, stdout="5 upgraded, 0 newly installed, 3 to remove and 0 not upgraded.")
    assert quita["status"] == "fail" and "removing 3 packages" in quita["reason"]


def test_negativo_de_firma(tmp_path: Path) -> None:
    rows = _buenas()[:-1]
    assert verify_capture(_escribe(tmp_path, rows))["reason"] == "signature-negative capture absent"
    aceptada = _con(tmp_path, 5, exit_code=0, stderr="Good signature")
    assert aceptada["status"] == "fail" and aceptada["checks"]["bad_signature_negative"] == "fail"


def _fuente_mala(**cambios: Any) -> dict[str, Any]:
    fila = _row(["apt-get", "update", "-o", "Dir::Etc::sourcelist=/tmp/bad.list"],
                err="E: Failed to fetch http://x/ 404  Not Found", rc=100)
    fila["control"] = "bad_source"
    fila.update(cambios)
    return fila


def test_pass_alcanzable_con_fila_bad_source(tmp_path: Path) -> None:
    out = verify_capture(_escribe(tmp_path, [*_buenas(), _fuente_mala()]))
    assert out["status"] == "pass" and out["fail"] == 0 and out["could_not_run"] == 0
    assert out["checks"]["bad_source_negative"] == "pass"
    assert all(v == "pass" for v in out["checks"].values())


def test_pass_alcanzable_control_que_acepta_la_fuente_mala_es_fail(tmp_path: Path) -> None:
    out = verify_capture(_escribe(tmp_path, [*_buenas(), _fuente_mala(exit_code=0)]))
    assert out["status"] == "fail" and out["checks"]["bad_source_negative"] == "fail"
    assert out["reason"] == "el control negativo no rechazo la fuente mala"


def test_pass_alcanzable_stderr_irrelevante_es_fail(tmp_path: Path) -> None:
    out = verify_capture(_escribe(tmp_path, [*_buenas(), _fuente_mala(stderr="disco lleno")]))
    assert out["status"] == "fail" and out["checks"]["bad_source_negative"] == "fail"
    vacio = verify_capture(_escribe(tmp_path, [*_buenas(), _fuente_mala(argv=[])]))
    assert vacio["status"] == "fail"


def test_pass_alcanzable_sin_fila_sigue_unknown(tmp_path: Path) -> None:
    out = verify_capture(_escribe(tmp_path, _buenas()))
    assert out["status"] == "unknown" and out["checks"]["bad_source_negative"] == "unknown"
    assert "wrong-source negative remains unrun" in out["reason"]


def test_comando_ausente_en_filas_validas_es_unknown_sin_arquitectura(tmp_path: Path) -> None:
    sin_dpkg = [r for r in _buenas() if r["argv"][:1] != ["dpkg"]]
    out = verify_capture(_escribe(tmp_path, sin_dpkg))
    assert out["status"] == "unknown" and out["could_not_run"] == 1
    assert "dpkg architecture query missing" in out["reason"]
    assert out["checks"]["architecture"] == "unknown"
