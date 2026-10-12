import json
from pathlib import Path

from tools import interruptores, limita_cuda as lc

LIB = Path("/x/libvgpu.so")


def test_parsea_limite():
    assert lc.parsea_limite("512m") == 512 << 20
    assert lc.parsea_limite("2G") == 2 << 30
    for malo in ("", "0m", "512", "m", "-1m", "5x"):
        assert lc.parsea_limite(malo) is None


def test_decide_off_lanza_sin_limitador():
    assert lc.decide("off", None, LIB, False, False, None)[0] == "lanza_sin_limitador"


def test_decide_fallo_cerrado_en_cada_causa():
    base = dict(modo="actuar", limite=512 << 20, lib=LIB, existe_lib=True, simbolos=True, centinela_rc=lc.CUDA_OOM)
    assert lc.decide(**base)[0] == "lanza"
    for cambio in ({"limite": None}, {"existe_lib": False}, {"simbolos": False}, {"centinela_rc": 0}, {"centinela_rc": None}, {"centinela_rc": -1}):
        accion, motivo = lc.decide(**{**base, **cambio})
        assert accion == "rechaza", (cambio, motivo)


def test_decide_observar_no_limita():
    assert lc.decide("observar", 512 << 20, LIB, True, True, lc.CUDA_OOM)[0] == "lanza_sin_limitador"


def _corre(tmp_path, monkeypatch, modo, rc_centinela, lib_ok=True):
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    (tmp_path / "interruptores.json").write_text(json.dumps({"modos": {"limitador": modo}}), encoding="utf-8")
    monkeypatch.setattr(interruptores, "_datos", lambda: tmp_path)
    lib = tmp_path / "libvgpu.so"
    if lib_ok:
        lib.write_text("x", encoding="utf-8")
    monkeypatch.setattr(lc, "exporta_cu", lambda _p: lib_ok)
    lanzados = []
    rc = lc.principal(["--limite", "512m", "--lib", str(lib), "--cache", str(tmp_path / "c"), "--", "echo", "hola"],
                      sondeo=lambda n, e: rc_centinela, ejecuta=lambda f, a, e: lanzados.append(e))
    return rc, lanzados


def test_actuar_con_centinela_rechazada_lanza_con_limitador(tmp_path, monkeypatch):
    rc, lanzados = _corre(tmp_path, monkeypatch, "actuar", lc.CUDA_OOM)
    assert rc == 0 and "libvgpu.so" in lanzados[0]["LD_PRELOAD"] and lanzados[0]["CUDA_DEVICE_MEMORY_LIMIT"] == "512m"


def test_actuar_con_centinela_que_pasa_NO_lanza(tmp_path, monkeypatch):
    rc, lanzados = _corre(tmp_path, monkeypatch, "actuar", 0)
    assert rc == 3 and lanzados == []


def test_actuar_sin_biblioteca_no_lanza(tmp_path, monkeypatch):
    rc, lanzados = _corre(tmp_path, monkeypatch, "actuar", lc.CUDA_OOM, lib_ok=False)
    assert rc == 3 and lanzados == []


def test_observar_lanza_sin_preload_y_registra(tmp_path, monkeypatch):
    rc, lanzados = _corre(tmp_path, monkeypatch, "observar", lc.CUDA_OOM)
    assert rc == 0 and "libvgpu" not in lanzados[0].get("LD_PRELOAD", "")
    assert (tmp_path / "interruptores" / "limitador.jsonl").exists()


def test_falta_comando(tmp_path, monkeypatch):
    monkeypatch.setattr(interruptores, "_datos", lambda: tmp_path)
    assert lc.principal(["--lib", "/x", "--limite", "1m"]) == 2
