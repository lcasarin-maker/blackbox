"""Controles de `tools/guardia_integridad.py`: cada defecto sale rojo y el texto legitimo sale verde."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools import guardia_integridad as gi

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("datos,esperado", [
    (b"linea\x00oculta\n", "bytes NUL"),
    (b"\xef\xbb\xbfhola\n", "BOM"),
    (b"uno\r\ndos\r\n", "CRLF"),
    (b"caf\xe9\n", "UTF-8 invalido"),
    ("canci" + "\u00c3\u00b3" + "n\n", "mojibake"),
    ("it" + "\u00e2\u20ac\u2122" + "s\n", "mojibake"),
])
def test_cada_defecto_se_detecta(datos: bytes | str, esperado: str):
    crudo = datos if isinstance(datos, bytes) else datos.encode("utf-8")
    assert any(esperado in p for p in gi.problemas(crudo))


@pytest.mark.parametrize("texto", [
    "canción, ñandú, áéíóú, ÁÉÍÓÚ, ü\n",           # acentos legitimos en UTF-8
    "Ángel López dijo «hola» — con rayas y comillas “curvas”\n",
    "\n",
    "",
])
def test_texto_legitimo_no_se_marca(texto: str):
    assert gi.problemas(texto.encode("utf-8")) == []


def test_main_sale_1_con_un_archivo_danado_y_0_con_uno_sano(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    malo, bueno = tmp_path / "malo.jsonl", tmp_path / "bueno.jsonl"
    malo.write_bytes(b'{"a": 1}\n\x00\x00\n')
    bueno.write_text('{"a": 1}\n', encoding="utf-8")
    assert gi.main([str(malo)]) == 1
    assert "bytes NUL" in capsys.readouterr().err
    assert gi.main([str(bueno)]) == 0


def test_sin_archivos_ni_arbol_no_examina_nada(capsys: pytest.CaptureFixture[str]):
    assert gi.main([]) == 0
    assert "examinados=0" in capsys.readouterr().out


def test_los_binarios_no_se_examinan(tmp_path: Path):
    binario = tmp_path / "datos.bin"
    binario.write_bytes(b"\x00\x01\xff\xfe")
    assert gi.main([str(binario)]) == 0


def test_fuera_de_un_repo_git_es_could_not_run(tmp_path: Path, capsys: pytest.CaptureFixture[str],
                                                 monkeypatch: pytest.MonkeyPatch):
    # dentro de un hook de git (pre-push) el entorno trae GIT_DIR/GIT_INDEX_FILE y `git -C` encontraria el repo real
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_PREFIX", "GIT_COMMON_DIR"):
        monkeypatch.delenv(var, raising=False)
    assert gi.main(["--arbol"], raiz=tmp_path) == 2
    assert "COULD_NOT_RUN" in capsys.readouterr().err


def test_el_arbol_versionado_de_este_repo_esta_integro():
    r = subprocess.run(["python3", "-m", "tools.guardia_integridad", "--arbol"], cwd=ROOT, capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stderr[-1500:]
