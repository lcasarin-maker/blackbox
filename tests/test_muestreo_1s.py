"""Pruebas de tools/muestreo_1s.py: formato de linea, fsync por segundo y rotacion por arranque."""
import importlib.util
import json
import os
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
# ponytail: la variable solo existe para correr el control negativo contra una copia sin fsync, techo = esta prueba; disparador = otra prueba que necesite sustituir el modulo
MODULO = pathlib.Path(os.environ.get("MUESTREO_1S_PATH", RAIZ / "tools" / "muestreo_1s.py"))

spec = importlib.util.spec_from_file_location("muestreo_1s", MODULO)
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

CLAVES = ["ts", "cpu_pct", "load1", "top", "freq_khz_cpu0", "temp_mc", "gpu", "psi_cpu", "psi_mem"]


def muestra():
    pp = {1: ("a", 10), 2: ("b", 10), 3: ("c", 10), 4: ("d", 10)}
    cp = {1: ("a", 110), 2: ("b", 50), 3: ("c", 40), 4: ("d", 11)}
    return m.registro(1.5, 200, 90, 100, 50, cp, pp, "1, 2", 100)


def test_formato_de_linea():
    rec = muestra()
    assert list(rec) == CLAVES
    assert rec["cpu_pct"] == 60.0  # dt=100, ocioso 40 -> 60 %
    assert [t["pid"] for t in rec["top"]] == [1, 2, 3]  # top 3 por delta de CPU
    assert rec["top"][0] == {"pid": 1, "cmd": "a", "cpu_pct_de_un_nucleo": 100.0}
    assert rec["gpu"] == "1, 2"


def test_linea_con_datos_vivos():
    r = m.registro(1.0, 2, 1, 1, 1, m.procs(), {}, None, 100)
    assert list(r) == CLAVES
    assert json.loads(json.dumps(r)) == r


def test_fsync_por_linea(tmp_path, monkeypatch):
    llamadas = []
    monkeypatch.setattr(m.os, "fsync", lambda fd: llamadas.append(fd))
    with open(tmp_path / "s.jsonl", "a", buffering=1) as f:
        for _ in range(3):
            m.escribir(f, muestra())
        assert llamadas == [f.fileno()] * 3


def test_linea_visible_sin_cerrar(tmp_path):
    with open(tmp_path / "s.jsonl", "a", buffering=1) as f:
        m.escribir(f, muestra())
        lineas = (tmp_path / "s.jsonl").read_text().splitlines()
    assert len(lineas) == 1 and list(json.loads(lineas[0])) == CLAVES


def test_rotacion_un_archivo_por_arranque(tmp_path):
    a = m.ruta_salida("7cd0848b-aaaa-bbbb", str(tmp_path))
    b = m.ruta_salida("11111111-aaaa-bbbb", str(tmp_path))
    assert a != b
    assert os.path.basename(a) == "muestreo-7cd0848b.jsonl"
    assert os.path.dirname(a) == str(tmp_path)
    assert m.ruta_salida("7cd0848b-zzzz", str(tmp_path)) == a
