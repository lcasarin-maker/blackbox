import json
import re
from pathlib import Path

RUTA = Path(__file__).resolve().parent.parent / "data" / "distros_alternas.json"
TIPOS = {"repo", "hilo", "guia", "articulo"}


def _carga():
    return json.loads(RUTA.read_text(encoding="utf-8"))


def test_esquema_y_campos():
    d = _carga()
    assert d["esquema"] == "bb-fuentes/1" and d["busca"] and d["fuentes"]
    for f in d["fuentes"]:
        assert set(f) == {"id", "tipo", "url", "nota"}, f
        assert f["tipo"] in TIPOS and f["nota"].strip(), f


def test_ids_unicos_y_urls_https():
    fs = _carga()["fuentes"]
    assert len({f["id"] for f in fs}) == len(fs)
    for f in fs:
        assert re.fullmatch(r"https://[\w.-]+/\S+", f["url"]), f["url"]


def test_la_cosecha_citada_existe():
    assert (RUTA.parent.parent / _carga()["origen"]).is_file()
