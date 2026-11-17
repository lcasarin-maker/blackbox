"""Controles de DEBT-GUARDA-PUBLICA-ARCHIVOS-EXENTOS-01: la guarda escanea su archivo y su linea base enteros y solo
exenta las lineas firmadas (sha256) en su ruta exacta. Cada caso corre la guarda real en una copia git aislada."""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import test_sin_datos_privados as guarda

RAIZ = Path(__file__).resolve().parent.parent
GUARDA = "tests/test_sin_datos_privados.py"
BASE = "tests/fixtures/datos_privados_baseline.json"
DATO = "10." + "194." + "62.85"


def _linea_firmada(texto: str, rel: str) -> str:
    firmas = guarda.LINEAS_FIRMADAS[rel]
    hallada = [l for l in texto.split("\n") if hashlib.sha256(l.encode("utf-8")).hexdigest() in firmas]
    assert len(hallada) == 1, rel
    return hallada[0]


def _corre(tmp: Path, *, guarda_src: str | None = None, base: str = "{}", extra: dict[str, str] | None = None):
    archivos = {GUARDA: guarda_src if guarda_src is not None else (RAIZ / GUARDA).read_text(), BASE: base,
                **(extra or {})}
    for rel, txt in archivos.items():
        (tmp / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp / rel).write_text(txt)
    for args in [("init", "-q"), ("add", "--", *archivos),
                 ("-c", "user.name=Prueba", "-c", "user.email=prueba@example.org", "commit", "-qm", "fixture")]:
        subprocess.run(["git", *args], cwd=tmp, check=True, capture_output=True)
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                           f"{GUARDA}::test_el_repo_no_gana_datos_privados"],
                          cwd=tmp, capture_output=True, text=True, timeout=120,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


def test_c_guarda_sin_cambios_pasa(tmp_path):
    r = _corre(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_a_dato_nuevo_en_la_guarda_bloquea(tmp_path):
    r = _corre(tmp_path, guarda_src=(RAIZ / GUARDA).read_text() + "\n# dato: " + DATO + "\n")
    assert r.returncode == 1, r.stdout + r.stderr
    assert GUARDA + ": archivo nuevo con 1 dato" in r.stdout


def test_b_editar_una_linea_firmada_bloquea(tmp_path):
    src = (RAIZ / GUARDA).read_text()
    linea = _linea_firmada(src, GUARDA)
    editada = linea[:-1] + ("3" if linea[-1] != "3" else "4")
    assert guarda.cuenta(editada) == guarda.cuenta(linea) > 0, "el control debe conservar el dato de la linea"
    r = _corre(tmp_path, guarda_src=src.replace(linea, editada))
    assert r.returncode == 1, r.stdout + r.stderr


def test_d_linea_base_firmada_pasa_y_sin_firma_bloquea(tmp_path):
    base = (RAIZ / BASE).read_text()
    firmada = _linea_firmada(base, BASE)
    assert guarda.cuenta(firmada) > 0
    ok = _corre(tmp_path / "firmada", base=base)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    sin_firma = base.replace("{\n", '{\n  "x/' + DATO + '": 0,\n', 1)
    r = _corre(tmp_path / "sin_firma", base=sin_firma)
    assert r.returncode == 1, r.stdout + r.stderr
    assert BASE + ": archivo nuevo con 1 dato" in r.stdout


def test_d_la_firma_no_viaja_a_otra_ruta(tmp_path):
    firmada = _linea_firmada((RAIZ / BASE).read_text(), BASE)
    r = _corre(tmp_path, extra={"tests/fixtures/otro.json": firmada + "\n"})
    assert r.returncode == 1, r.stdout + r.stderr
    assert "tests/fixtures/otro.json: archivo nuevo" in r.stdout


def test_cuenta_blob_solo_descuenta_lineas_firmadas():
    linea = _linea_firmada((RAIZ / GUARDA).read_text(), GUARDA).encode("utf-8")
    assert guarda.cuenta_blob(GUARDA, linea + b"\n") == 0
    assert guarda.cuenta_blob(GUARDA, linea + b" \n") == 1
    assert guarda.cuenta_blob("tests/otro.py", linea + b"\n") == 1
    assert guarda.cuenta_blob(GUARDA, linea + b"\n" + DATO.encode() + b"\n") == 1
