"""huella_host: sondas con arboles falsos, diferencias sin ocultar perdidas de lectura, y el interruptor."""

from __future__ import annotations

import json
import subprocess
import types
from pathlib import Path
from typing import Any

import pytest

from tools import huella_host as h


def _w(raiz: Path, rel: str, txt: str) -> None:
    p = raiz / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")


def _correr(salidas: dict[str, tuple[int, str]]) -> Any:
    def f(args: list[str], **kw: Any) -> Any:
        clave = next((k for k in salidas if k in " ".join(args)), None)
        if clave is None:
            raise FileNotFoundError(args[0])
        rc, out = salidas[clave]
        return types.SimpleNamespace(returncode=rc, stdout=out)
    return f


def _cae(args: list[str], **kw: Any) -> Any:
    raise subprocess.TimeoutExpired(args, 10)


# 1 os_release
def test_os_release_sano(tmp_path: Path) -> None:
    _w(tmp_path, "etc/os-release", 'NAME="Ubuntu"\nPRETTY_NAME="Ubuntu 24.04.3 LTS"\n')
    _w(tmp_path, "etc/dgx-release", "DGX_OTA_VERSION=7.2\nDGX_SERIAL_NUMBER=SN-PRIVADO\n")
    assert h.sonda_os_release(tmp_path, subprocess.run) == {"pretty_name": "Ubuntu 24.04.3 LTS", "dgx_release": "DGX_OTA_VERSION=7.2"}  # el serie no entra (control negativo: seria 'SN-PRIVADO' si entrara)


def test_os_release_sin_pretty_ni_dgx(tmp_path: Path) -> None:
    _w(tmp_path, "etc/os-release", "NAME=x\n")
    assert h.sonda_os_release(tmp_path, subprocess.run) == {"pretty_name": "NOT_COLLECTED: sin PRETTY_NAME"}


def test_os_release_ausente(tmp_path: Path) -> None:
    assert h.es_nc(h.sonda_os_release(tmp_path, subprocess.run))


# 2 kernel
def test_kernel(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(h.platform, "release", lambda: "6.17.0-x")
    assert h.sonda_kernel(tmp_path, subprocess.run) == "6.17.0-x"
    monkeypatch.setattr(h.platform, "release", lambda: "")
    assert h.es_nc(h.sonda_kernel(tmp_path, subprocess.run))


# 3 driver nvidia
def test_driver_nvidia(tmp_path: Path) -> None:
    assert h.es_nc(h.sonda_driver_nvidia(tmp_path, subprocess.run))
    _w(tmp_path, "proc/driver/nvidia/version", "NVRM version: 580.95\nGCC x\n")
    assert h.sonda_driver_nvidia(tmp_path, subprocess.run) == "NVRM version: 580.95"


# 4 ota
def test_ota_sano_y_ausente(tmp_path: Path) -> None:
    ok = h.sonda_ota(tmp_path, _correr({"dgx-spark-ota-update-meta": (0, "1.2"), "nvidia-spark-ota-check": (1, "")}))
    assert ok["dgx-spark-ota-update-meta"] == "1.2" and h.es_nc(ok["nvidia-spark-ota-check"])
    assert all(h.es_nc(v) for v in h.sonda_ota(tmp_path, _cae).values())
    assert all(h.es_nc(v) for v in h.sonda_ota(tmp_path, _correr({})).values())


# 5 firmware CX7
def test_firmware_cx7(tmp_path: Path) -> None:
    assert h.es_nc(h.sonda_firmware_cx7(tmp_path, subprocess.run))
    _w(tmp_path, "sys/class/infiniband/rocep1s0f0/fw_ver", "28.45.1200\n")
    _w(tmp_path, "sys/class/infiniband/rocep1s0f0/board_id", "NVD0000000033\n")
    _w(tmp_path, "sys/class/infiniband/rocep1s0f1/fw_ver", "\n")
    r = h.sonda_firmware_cx7(tmp_path, subprocess.run)
    assert r["rocep1s0f0"] == {"fw_ver": "28.45.1200", "psid": "NVD0000000033"}
    assert h.es_nc(r["rocep1s0f1"]["fw_ver"]) and h.es_nc(r["rocep1s0f1"]["psid"])


# 6 driver por interfaz
def test_driver_red(tmp_path: Path) -> None:
    assert h.es_nc(h.sonda_driver_red(tmp_path, subprocess.run))
    d = tmp_path / "sys/class/net/enP7s7/device"
    d.mkdir(parents=True)
    (d / "driver").symlink_to("../../../../bus/pci/drivers/r8127")
    (tmp_path / "sys/class/net/lo").mkdir()
    assert h.sonda_driver_red(tmp_path, subprocess.run) == {"enP7s7": "r8127"}


# 7 USB
def test_usb(tmp_path: Path) -> None:
    assert h.es_nc(h.sonda_usb(tmp_path, subprocess.run))
    _w(tmp_path, "sys/bus/usb/devices/2-1/speed", "480\n")
    _w(tmp_path, "sys/bus/usb/devices/2-1/product", "SSD\n")
    _w(tmp_path, "sys/bus/usb/devices/2-2/speed", "\n")
    r = h.sonda_usb(tmp_path, subprocess.run)
    assert r["2-1"] == {"speed_mbps": "480", "product": "SSD"}
    assert h.es_nc(r["2-2"]["speed_mbps"]) and h.es_nc(r["2-2"]["product"])


# 8 apt
def test_apt_mezcla_detectada(tmp_path: Path) -> None:
    _w(tmp_path, "etc/apt/sources.list", "deb http://archive.ubuntu.com/ubuntu noble main\n")
    _w(tmp_path, "etc/apt/sources.list.d/a.sources", "URIs: http://ports.ubuntu.com/ubuntu-ports\n")
    r = h.sonda_apt(tmp_path, subprocess.run)
    assert r["mezcla_archive_y_ports"] is True


def test_apt_mezcla_no_detectada(tmp_path: Path) -> None:
    _w(tmp_path, "etc/apt/sources.list.d/a.list", "deb http://ports.ubuntu.com/ubuntu-ports noble main\n")
    _w(tmp_path, "etc/apt/sources.list.d/b.list", "# deb http://archive.ubuntu.com/ubuntu noble main\n")
    r = h.sonda_apt(tmp_path, subprocess.run)
    assert r == {"archive": False, "ports": True, "mezcla_archive_y_ports": False}


def test_apt_sin_fuentes(tmp_path: Path) -> None:
    assert h.es_nc(h.sonda_apt(tmp_path, subprocess.run))


# 9 watchdog
def test_watchdog(tmp_path: Path) -> None:
    assert h.es_nc(h.sonda_watchdog(tmp_path, subprocess.run))
    _w(tmp_path, "sys/class/watchdog/watchdog0/identity", "SBSA\n")
    (tmp_path / "dev").mkdir()
    (tmp_path / "dev/watchdog0").write_text("", encoding="utf-8")
    r = h.sonda_watchdog(tmp_path, subprocess.run)
    assert r["dev"] == ["watchdog0"] and r["sysfs"]["watchdog0"]["identity"] == "SBSA"
    assert h.es_nc(r["sysfs"]["watchdog0"]["state"])


# 10 GPU
def test_gpu(tmp_path: Path) -> None:
    _w(tmp_path, "sys/bus/pci/devices/0000:01:00.0/vendor", "0x10de\n")
    _w(tmp_path, "sys/bus/pci/devices/0000:01:00.0/class", "0x030200\n")
    _w(tmp_path, "sys/bus/pci/devices/0000:00:00.0/vendor", "0x10de\n")  # puerto raiz del SoC: mismo vendor, no es la GPU
    _w(tmp_path, "sys/bus/pci/devices/0000:00:00.0/class", "0x060400\n")
    _w(tmp_path, "sys/bus/pci/devices/0000:02:00.0/vendor", "0x8086\n")
    ok = h.sonda_gpu(tmp_path, _correr({"nvidia-smi": (0, "GB10, 580.95, 97.1")}))
    assert ok == {"smi": "GB10, 580.95, 97.1", "pci_nvidia": ["0000:01:00.0"]}
    mal = h.sonda_gpu(tmp_path, _correr({"nvidia-smi": (9, "")}))
    assert h.es_nc(mal["smi"]) and mal["pci_nvidia"] == ["0000:01:00.0"]


# 11 pstore
def test_pstore(tmp_path: Path) -> None:
    (tmp_path / "sys/fs/pstore").mkdir(parents=True)
    (tmp_path / "sys/fs/pstore/dmesg-1").write_text("", encoding="utf-8")
    r = h.sonda_pstore(tmp_path, subprocess.run)
    assert r["sys/fs/pstore"] == 1 and h.es_nc(r["var/lib/systemd/pstore"])


# 12 clock lock
def test_clock_lock(tmp_path: Path) -> None:
    assert h.sonda_clock_lock(tmp_path, _correr({"clocks.max.sm": (0, "2411")})) == "2411"
    assert h.es_nc(h.sonda_clock_lock(tmp_path, _cae))


# recoge / diferencias
def _huella(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kernel: str = "6.17.0-a") -> dict[str, Any]:
    monkeypatch.setattr(h.platform, "release", lambda: kernel)
    return h.recoge(tmp_path, _correr({}))


def test_recoge_cubre_todas_las_sondas_sin_inventar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    r = _huella(tmp_path, monkeypatch)
    assert set(r) == set(h.SONDAS) and len(r) == 12 and h.es_nc(r["os_release"])


def test_recoge_sonda_que_lanza_es_nc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def rota(raiz: Path, correr: Any) -> Any:
        raise ValueError("boom")
    monkeypatch.setitem(h.SONDAS, "kernel", rota)
    assert h.recoge(tmp_path, _correr({}))["kernel"] == "NOT_COLLECTED: ValueError: boom"


def test_dos_huellas_iguales_sin_diferencias(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    a, b = _huella(tmp_path, monkeypatch), _huella(tmp_path, monkeypatch)
    assert h.diferencias(a, b) == []


def test_cambiar_solo_el_kernel_da_una_diferencia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    a, b = _huella(tmp_path, monkeypatch), _huella(tmp_path, monkeypatch, "6.17.0-b")
    assert h.diferencias(a, b) == [{"sonda": "kernel", "antes": "6.17.0-a", "despues": "6.17.0-b"}]


def test_perdida_y_recuperacion_de_lectura() -> None:
    perdida = h.diferencias({"x": "1"}, {"x": "NOT_COLLECTED: z"})
    assert perdida[0]["etiqueta"] == "perdida_de_lectura"
    rec = h.diferencias({"x": "NOT_COLLECTED: z"}, {"x": "1"})
    assert rec[0]["etiqueta"] == "lectura_recuperada"
    nc_nc = h.diferencias({"x": "NOT_COLLECTED: a"}, {"x": "NOT_COLLECTED: b"})
    assert "etiqueta" not in nc_nc[0]


def test_sonda_ausente_en_una_huella_se_cuenta() -> None:
    assert h.diferencias({}, {"x": "1"})[0]["etiqueta"] == "lectura_recuperada"
    assert h.diferencias({"x": "1"}, {})[0]["etiqueta"] == "perdida_de_lectura"


# paso
def _lineas(d: Path) -> list[dict[str, Any]]:
    f = d / "huella_host.jsonl"
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []


def test_off_no_escribe_nada(tmp_path: Path) -> None:
    assert h.paso("off", {"a": 1}, tmp_path / "e.json", tmp_path / "d") is None
    assert list(tmp_path.iterdir()) == []


def test_primera_huella_no_dispara(tmp_path: Path) -> None:
    ev = h.paso("observar", {"a": 1}, tmp_path / "e.json", tmp_path / "d")
    assert ev is not None and ev["primera"] is True and ev["habria_actuado"] is False
    assert (tmp_path / "e.json").exists() and _lineas(tmp_path / "d")[0]["primera"] is True


def test_segunda_igual_no_registra_y_cambio_si(tmp_path: Path) -> None:
    e, d = tmp_path / "e.json", tmp_path / "d"
    h.paso("observar", {"a": 1}, e, d)
    assert h.paso("observar", {"a": 1}, e, d) is None
    ev = h.paso("observar", {"a": 2}, e, d)
    assert ev is not None and ev["habria_actuado"] is True and ev["primera"] is False
    assert ev["diferencias"] == [{"sonda": "a", "antes": 1, "despues": 2}]
    assert json.loads(e.read_text(encoding="utf-8")) == {"a": 2} and len(_lineas(d)) == 2


def test_estado_corrupto_cuenta_como_primera(tmp_path: Path) -> None:
    e = tmp_path / "e.json"
    e.write_text("{no json", encoding="utf-8")
    ev = h.paso("observar", {"a": 1}, e, tmp_path / "d")
    assert ev is not None and ev["primera"] is True


def test_actuar_declara_unsupported(tmp_path: Path) -> None:
    e, d = tmp_path / "e.json", tmp_path / "d"
    h.paso("actuar", {"a": 1}, e, d)
    ev = h.paso("actuar", {"a": 2}, e, d)
    assert ev is not None and ev["accion"].startswith("UNSUPPORTED")


def test_paso_usa_recoge_y_ruta_por_defecto(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    monkeypatch.setattr(h, "recoge", lambda: {"k": "v"})
    ev = h.paso("observar", directorio=tmp_path / "d")
    assert ev is not None and json.loads((tmp_path / "huella_host.json").read_text(encoding="utf-8")) == {"k": "v"}


# CLI
def test_main_imprime_huella(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(h, "recoge", lambda: {"k": "v"})
    assert h.main([]) == 0
    assert json.loads(capsys.readouterr().out) == {"k": "v"}


def test_main_paso(monkeypatch: pytest.MonkeyPatch) -> None:
    visto: list[str] = []
    monkeypatch.setattr(h.interruptores, "modo", lambda n: "observar")
    monkeypatch.setattr(h, "paso", lambda m: visto.append(m))
    assert h.main(["--paso"]) == 0 and visto == ["observar"]
