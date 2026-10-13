"""Pruebas de tools/hid_inventario.py con sysfs sintetico (sin tocar hardware)."""
from __future__ import annotations

import json
from typing import Any
from pathlib import Path

from tools import hid_inventario as hi


def _dev(sysu: Path, nombre: str, vid: str, pid: str, producto: str, ifaces: list[tuple[str, str | None]]) -> None:
    d = sysu / nombre
    d.mkdir(parents=True)
    (d / "idVendor").write_text(vid + "\n", encoding="utf-8")
    (d / "idProduct").write_text(pid + "\n", encoding="utf-8")
    (d / "product").write_text(producto + "\n", encoding="utf-8")
    drivers = sysu.parent / "drivers"
    for i, (clase, drv) in enumerate(ifaces):
        f = sysu / f"{nombre}:1.{i}"
        f.mkdir()
        (f / "bInterfaceClass").write_text(clase + "\n", encoding="utf-8")
        if drv:
            (drivers / drv).mkdir(parents=True, exist_ok=True)
            (f / "driver").symlink_to(drivers / drv)


def _mundo(tmp: Path, kb_driver: str | None = "usbhid", con_kb: bool = True, con_mouse: bool = True,
           input_kb: bool = True) -> tuple[Path, Path]:
    sysu = tmp / "bus" / "devices"
    sysu.mkdir(parents=True)
    _dev(sysu, "3-1.2", "046d", "082d", "Webcam", [("0e", "uvcvideo")])
    if con_kb:
        _dev(sysu, "3-1.3", "258a", "002a", "Gaming KB", [("03", kb_driver), ("03", kb_driver)])
    if con_mouse:
        _dev(sysu, "3-1.1.4", "046d", "c52b", "Receiver", [("03", "usbhid")])
    inp = tmp / "devices"
    txt = "N: Name=x\nP: Phys=ALSA\n"
    if input_kb:
        txt += "N: Name=kb\nP: Phys=usb-NVDA:01-1.3/input0\nN: Name=kb2\nP: Phys=usb-NVDA:01-1.3/input1\n"
    txt += "N: Name=m\nP: Phys=usb-NVDA:01-1.1.4/input2:1\n"
    inp.write_text(txt, encoding="utf-8")
    return sysu, inp


def _corre(tmp: Path, kernel: str, **kw: Any) -> dict[str, Any]:
    d = tmp / f"w{len(list(tmp.glob('w*')))}"
    d.mkdir()
    sysu, inp = _mundo(d, **kw)
    return hi.correr(sysu, inp, tmp / "estado.json", kernel)


def test_inventario_solo_clase_03(tmp_path: Path) -> None:
    sysu, inp = _mundo(tmp_path)
    r = hi.inventario(sysu, inp)
    assert sorted(r["hid"]) == ["046d:c52b", "258a:002a"]  # la webcam (clase 0e) no entra
    assert r["hid"]["258a:002a"]["drivers"] == ["usbhid"]
    assert r["hid"]["258a:002a"]["input"] == 2


def test_primera_corrida_solo_linea_base(tmp_path: Path) -> None:
    assert _corre(tmp_path, "6.1")["veredicto"] == "BASELINE"


def test_igual_sin_hallazgos_y_cambio_de_kernel_sano(tmp_path: Path) -> None:
    _corre(tmp_path, "6.1")
    assert _corre(tmp_path, "6.1")["veredicto"] == "SIN_HALLAZGOS"
    r = _corre(tmp_path, "6.2")
    assert (r["veredicto"], r["hallazgos"]) == ("SIN_HALLAZGOS", [])


def test_control_negativo_dispositivo_desaparecido(tmp_path: Path) -> None:
    _corre(tmp_path, "6.1")
    r = _corre(tmp_path, "6.2", con_kb=False)
    assert r["veredicto"] == "HID_PERDIDO"
    assert [h["dispositivo"] for h in r["hallazgos"]] == ["258a:002a"]
    # persiste en la siguiente corrida del mismo kernel
    assert _corre(tmp_path, "6.2", con_kb=False)["veredicto"] == "HID_PERDIDO"
    # y se limpia al reaparecer
    assert _corre(tmp_path, "6.2")["veredicto"] == "SIN_HALLAZGOS"


def test_control_negativo_sin_driver_y_sin_input(tmp_path: Path) -> None:
    _corre(tmp_path, "6.1")
    r = _corre(tmp_path, "6.1", kb_driver=None)
    assert r["hallazgos"][0]["motivo"] == "sin_driver"
    assert _corre(tmp_path, "6.1", kb_driver=None)["veredicto"] == "HID_PERDIDO"  # persiste aunque vistos se sobrescriba
    r = _corre(tmp_path, "6.2", input_kb=False)
    assert r["veredicto"] == "HID_PERDIDO" and any(h["motivo"] == "sin_nodo_input" for h in r["hallazgos"])


def test_desenchufado_en_mismo_kernel_no_alerta(tmp_path: Path) -> None:
    _corre(tmp_path, "6.1")
    assert _corre(tmp_path, "6.1", con_mouse=False)["veredicto"] == "SIN_HALLAZGOS"


def test_sin_hid_indeterminado(tmp_path: Path) -> None:
    r = _corre(tmp_path, "6.1", con_kb=False, con_mouse=False)
    assert r["veredicto"] == "INDETERMINADO"
    assert not (tmp_path / "estado.json").exists()  # no fija linea base vacia
    _corre(tmp_path, "6.1")
    r = _corre(tmp_path, "6.1", con_kb=False, con_mouse=False)
    assert r["veredicto"] == "INDETERMINADO" and r["hallazgos"][0]["motivo"] == "sin_hid_conectado"
    r = _corre(tmp_path, "6.2", con_kb=False, con_mouse=False)  # kernel nuevo y todo HID ausente
    assert r["veredicto"] == "HID_PERDIDO"


def test_sysfs_ausente_y_estado_corrupto(tmp_path: Path) -> None:
    r = hi.correr(tmp_path / "nada", tmp_path / "nada2", tmp_path / "e.json", "6.1")
    assert r["veredicto"] == "INDETERMINADO" and r["could_not_run"] == 1
    sysu, inp = _mundo(tmp_path)
    (tmp_path / "e.json").write_text("{roto", encoding="utf-8")
    r = hi.correr(sysu, inp, tmp_path / "e.json", "6.1")
    assert r["veredicto"] == "INDETERMINADO" and r["could_not_run"] == 1
    assert (tmp_path / "e.json").read_text(encoding="utf-8") == "{roto"
    (tmp_path / "e.json").write_text("[]", encoding="utf-8")
    assert hi.correr(sysu, inp, tmp_path / "e.json", "6.1")["could_not_run"] == 1


def test_input_ilegible_se_registra(tmp_path: Path) -> None:
    sysu, _ = _mundo(tmp_path)
    r = hi.inventario(sysu, tmp_path / "no-existe")
    assert "input_ilegible:FileNotFoundError" in r["errores"] and r["hid"]


def test_main_rc_y_estado_por_defecto(tmp_path: Path, monkeypatch, capsys) -> None:
    sysu, inp = _mundo(tmp_path)
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path / "datos"))
    assert hi.estado_por_defecto() == tmp_path / "datos" / "hid_inventario.json"
    args = ["--sys-usb", str(sysu), "--input", str(inp), "--kernel", "6.1"]
    assert hi.main(args) == 0
    assert json.loads(capsys.readouterr().out)["veredicto"] == "BASELINE"
    (sysu / "3-1.3" / "idVendor").unlink()  # un HID cambia de identidad: el anterior desaparece
    assert hi.main(args + ["--kernel", "6.2"]) == 1
    assert hi.main(args + ["--no-guardar", "--kernel", "6.3"]) == 1  # la perdida sigue abierta en otro kernel
    assert hi.main(args + ["--kernel", "6.3"]) == 1
    assert hi.main(args + ["--kernel", "6.3"]) == 1
