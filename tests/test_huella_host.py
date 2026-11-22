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


def _correr_sesion(salidas: dict[str, tuple[int, str]], fallas: dict[str, type[BaseException]] | None = None) -> Any:
    def f(args: list[str], **kw: Any) -> Any:
        clave = " ".join(args)
        if clave not in salidas:
            if clave in (fallas or {}):
                raise (fallas or {})[clave](args[0])
            if args[0] in {"loginctl", "systemctl"}:
                raise AssertionError(f"argv inesperado: {args!r}")
            raise FileNotFoundError(args[0])
        rc, out = salidas[clave]
        return types.SimpleNamespace(returncode=rc, stdout=out, stderr="")
    return f


def _huella_sesion(tmp_path: Path, runner: Any, monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setattr(h.platform, "release", lambda: "6.17.0-synthetic")
    return h.recoge(tmp_path, runner).get("sesion_grafica")


def _fila_sesion(session_id: str, uid: str = "1000", user: str = "synthetic",
                 seat: str = "seat0", tty: str = "tty2") -> str:
    return f"{session_id} {uid} {user} {seat} {tty} active no Fri-Nov-21\n"


def _fila_sesion_corta(session_id: str) -> str:
    return f"{session_id} 1000 synthetic seat0 tty2\n"


def _cmd_default() -> str:
    return "systemctl get-default"


def _cmd_gdm() -> str:
    return "systemctl is-active gdm.service"


def _cmd_sessions() -> str:
    return "loginctl list-sessions --no-pager --no-legend"


def _cmd_show(session_id: str) -> str:
    return (f"loginctl show-session {session_id} --all -p Active -p Remote -p Type "
            "-p Class -p Seat -p Display")


def _propiedades_sesion(*, active: str = "yes", remote: str = "no", kind: str = "wayland",
                        session_class: str = "user", seat: str = "seat0", display: str = ":0") -> str:
    return (f"Active={active}\nRemote={remote}\nType={kind}\nClass={session_class}\n"
            f"Seat={seat}\nDisplay={display}\n")


def test_recoge_sesion_headless_declarada_por_target(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _correr_sesion({
        _cmd_default(): (0, "multi-user.target\n"),
        _cmd_gdm(): (3, "inactive\n"),
        _cmd_sessions(): (0, ""),
    })
    r = _huella_sesion(tmp_path, runner, monkeypatch)
    assert r == {"estado": "headless_declarado", "target": "multi-user.target",
                 "gdm": "inactive", "sesiones_graficas_locales": 0, "greeters": 0}


def test_recoge_sesion_gdm_activo_sin_usuario_grafico_local(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _correr_sesion({
        _cmd_default(): (0, "graphical.target\n"),
        _cmd_gdm(): (0, "active\n"),
        _cmd_sessions(): (0, _fila_sesion("21", user="gdm")),
        _cmd_show("21"): (0, _propiedades_sesion(session_class="greeter")),
    })
    r = _huella_sesion(tmp_path, runner, monkeypatch)
    assert isinstance(r, dict), r
    assert r["estado"] == "gdm_activo_sin_sesion_grafica_local"
    assert r["sesiones_graficas_locales"] == 0 and r["greeters"] == 1
    assert "synthetic" not in json.dumps(r)


@pytest.mark.parametrize("kind", ["x11", "wayland"])
def test_recoge_sesion_grafica_local_observada_excluye_ssh(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str) -> None:
    runner = _correr_sesion({
        _cmd_default(): (0, "graphical.target\n"),
        _cmd_gdm(): (0, "active\n"),
        _cmd_sessions(): (0, _fila_sesion("31", user="remoteuser", seat="-", tty="-") +
                          _fila_sesion("c21", user="privateuser")),
        _cmd_show("31"): (0, _propiedades_sesion(remote="yes", seat="", display=":10")),
        _cmd_show("c21"): (0, _propiedades_sesion(kind=kind, display="")),
    })
    r = _huella_sesion(tmp_path, runner, monkeypatch)
    assert isinstance(r, dict), r
    assert r["estado"] == "sesion_grafica_local_observada"
    assert r["sesiones_graficas_locales"] == 1 and r["greeters"] == 0
    assert "privateuser" not in json.dumps(r) and "remoteuser" not in json.dumps(r)
    assert "c21" not in json.dumps(r)


def test_recoge_acepta_fila_tabular_de_cinco_columnas(tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _correr_sesion({
        _cmd_default(): (0, "graphical.target\n"),
        _cmd_gdm(): (0, "active\n"),
        _cmd_sessions(): (0, _fila_sesion_corta("c21")),
        _cmd_show("c21"): (0, _propiedades_sesion(display="")),
    })
    r = _huella_sesion(tmp_path, runner, monkeypatch)
    assert isinstance(r, dict), r
    assert r["estado"] == "sesion_grafica_local_observada"


def test_recoge_rechaza_fila_incompleta_antes_de_consultar_detalle(tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def runner(args: list[str], **kw: Any) -> Any:
        calls.append(" ".join(args))
        if args[:2] == ["systemctl", "get-default"]:
            return types.SimpleNamespace(returncode=0, stdout="graphical.target\n", stderr="")
        if args[:2] == ["systemctl", "is-active"]:
            return types.SimpleNamespace(returncode=0, stdout="active\n", stderr="")
        if args[:2] == ["loginctl", "list-sessions"]:
            return types.SimpleNamespace(returncode=0, stdout="1 x\n", stderr="")
        if args[:2] == ["loginctl", "show-session"]:
            return types.SimpleNamespace(returncode=0, stdout=_propiedades_sesion(), stderr="")
        raise AssertionError(f"argv inesperado: {args!r}")

    r = h.sonda_sesion_grafica(tmp_path, runner)
    assert h.es_nc(r), r
    assert not any(call.startswith("loginctl show-session") for call in calls), calls


@pytest.mark.parametrize("prefijo", [14.0, 51.0, 56.0])
def test_recoge_sesion_grafica_respeta_presupuesto_completo(tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch, prefijo: float) -> None:
    reloj = [0.0]
    llamadas_graficas: list[list[str]] = []
    timeouts_graficas: list[float] = []
    monkeypatch.setattr(h.time, "monotonic", lambda: reloj[0])
    monkeypatch.setattr(h.platform, "release", lambda: "synthetic")

    def runner(args: list[str], **kw: Any) -> Any:
        joined = " ".join(args)
        if args[0] in {"systemctl", "loginctl"}:
            llamadas_graficas.append(args)
            timeouts_graficas.append(kw.get("timeout", 4.0))
            data = {
                _cmd_default(): (0, "graphical.target\n"),
                _cmd_gdm(): (0, "active\n"),
                _cmd_sessions(): (0, _fila_sesion_corta("c21")),
                _cmd_show("c21"): (0, _propiedades_sesion(display="")),
            }
            rc, out = data[joined]
            elapsed = min(1.0, kw.get("timeout", 4.0))
            reloj[0] += elapsed
            return subprocess.CompletedProcess(args, rc, out, "")
        if reloj[0] == 0.0:
            reloj[0] += prefijo
        return subprocess.CompletedProcess(args, 1, "", "")

    result = h.recoge(tmp_path, runner)
    if prefijo >= 52.0:
        assert h.es_nc(result["sesion_grafica"]), result["sesion_grafica"]
        assert llamadas_graficas == [], llamadas_graficas
        assert reloj[0] == prefijo
    elif prefijo >= 48.0:
        assert h.es_nc(result["sesion_grafica"]), result["sesion_grafica"]
        assert len(llamadas_graficas) == 1, llamadas_graficas
        assert timeouts_graficas == [1.0], timeouts_graficas
    else:
        assert result["sesion_grafica"]["estado"] == "sesion_grafica_local_observada"
        assert llamadas_graficas
    if prefijo < 52.0:
        assert reloj[0] <= 52.0
    else:
        assert reloj[0] == prefijo


def test_recoge_sesion_greeter_y_tty_no_prueban_escritorio_local(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _correr_sesion({
        _cmd_default(): (0, "graphical.target\n"),
        _cmd_gdm(): (0, "active\n"),
        _cmd_sessions(): (0, _fila_sesion("41", user="gdm") +
                           _fila_sesion("42", user="tty", tty="tty1")),
        _cmd_show("41"): (0, _propiedades_sesion(session_class="greeter")),
        _cmd_show("42"): (0, _propiedades_sesion(kind="tty", display="")),
    })
    r = _huella_sesion(tmp_path, runner, monkeypatch)
    assert isinstance(r, dict), r
    assert r["estado"] == "gdm_activo_sin_sesion_grafica_local"
    assert r["sesiones_graficas_locales"] == 0 and r["greeters"] == 1


@pytest.mark.parametrize("salidas,fallas", [
    ({_cmd_default(): (0, "multi-user.target\n"), _cmd_gdm(): (3, "inactive\n"),
      _cmd_sessions(): (0, "fila ambigua\n")}, None),
    ({_cmd_default(): (0, "multi-user.target\n"), _cmd_gdm(): (3, "inactive\n"),
      _cmd_sessions(): (0, "--all 1000 synthetic seat0 tty2 active no Fri-Nov-21\n")}, None),
    ({_cmd_default(): (0, "graphical.target\n"), _cmd_gdm(): (0, "active\n"),
      _cmd_sessions(): (0, _fila_sesion("51")),
      _cmd_show("51"): (0, "Active=yes\nActive=no\nRemote=no\nType=wayland\nClass=user\nSeat=seat0\nDisplay=:0\n")}, None),
    ({_cmd_default(): (0, "multi-user.target\n"), _cmd_gdm(): (3, "inactive\n")},
     {_cmd_sessions(): PermissionError}),
    ({_cmd_default(): (0, "multi-user.target\n"), _cmd_gdm(): (3, "inactive\n"),
      _cmd_sessions(): (0, _fila_sesion("52"))}, {_cmd_show("52"): PermissionError}),
    ({_cmd_gdm(): (0, "active\n"), _cmd_sessions(): (0, "")},
     {_cmd_default(): PermissionError}),
    ({_cmd_default(): (0, "multi-user.target\n"), _cmd_gdm(): (4, "unknown\n"),
      _cmd_sessions(): (0, "")}, None),
    ({_cmd_default(): (0, "rescue.target\n"), _cmd_gdm(): (3, "inactive\n"),
      _cmd_sessions(): (0, "")}, None),
    ({_cmd_default(): (0, "graphical.target\n"), _cmd_gdm(): (3, "inactive\n"),
      _cmd_sessions(): (0, "")}, None),
    ({_cmd_default(): (0, "multi-user.target\n"), _cmd_gdm(): (3, "inactive\n"),
      _cmd_sessions(): (0, "1 " + "x" * 17000)}, None),
])
def test_recoge_sesion_lectura_fallida_o_ambigua_es_nc(
        tmp_path: Path, salidas: dict[str, tuple[int, str]],
        fallas: dict[str, type[BaseException]] | None,
        monkeypatch: pytest.MonkeyPatch) -> None:
    r = _huella_sesion(tmp_path, _correr_sesion(salidas, fallas), monkeypatch)
    assert h.es_nc(r), r


@pytest.mark.parametrize("duracion_consulta", [4.0, 3.9])
def test_sonda_sesion_presupuesto_global_detiene_lecturas_seriales(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, duracion_consulta: float) -> None:
    reloj = [0.0]
    llamadas: list[list[str]] = []
    sesiones = "".join(_fila_sesion(str(i)) for i in range(1, 11))
    monkeypatch.setattr(h.time, "monotonic", lambda: reloj[0])

    def runner(args: list[str], **kw: Any) -> Any:
        llamadas.append(args)
        joined = " ".join(args)
        if joined == _cmd_default():
            rc, out = 0, "graphical.target\n"
        elif joined == _cmd_gdm():
            rc, out = 0, "active\n"
        elif joined == _cmd_sessions():
            rc, out = 0, sesiones
        elif args[0:2] == ["loginctl", "show-session"]:
            assert joined == _cmd_show(args[2])
            rc, out = 0, _propiedades_sesion(display="")
        else:
            raise AssertionError(f"argv inesperado: {args!r}")
        reloj[0] += duracion_consulta
        return types.SimpleNamespace(returncode=rc, stdout=out, stderr="")

    r = h.sonda_sesion_grafica(tmp_path, runner)
    assert h.es_nc(r) and "presupuesto" in r
    assert h.PRESUPUESTO_SESION_GRAFICA_S <= reloj[0] <= (
        h.PRESUPUESTO_SESION_GRAFICA_S + h.host_diagnostics.TIMEOUT_S)
    assert len(llamadas) == (12 if duracion_consulta == 4.0 else 13)


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


# 10b GPU/GSP
def _pci_gpu(raiz: Path) -> None:
    _w(raiz, "sys/bus/pci/devices/0000:01:00.0/vendor", "0x10de\n")
    _w(raiz, "sys/bus/pci/devices/0000:01:00.0/class", "0x030000\n")


_SMI_OK = (0, "NVIDIA GB10, 580.178.04")
_KERNEL_SANO = (0, "oct 12 host kernel: NVRM: loaded\noct 12 host kernel: nvidia: GSP firmware 580.178.04 ok")


def test_gpu_gsp_disponible(tmp_path: Path) -> None:
    _pci_gpu(tmp_path)
    r = h.sonda_gpu_gsp(tmp_path, _correr({"nvidia-smi": _SMI_OK, "journalctl": _KERNEL_SANO}))
    assert r["veredicto"] == "disponible" and r["smi"] == "NVIDIA GB10, 580.178.04"
    assert r["kernel_gsp"] == {"lineas": 1, "errores": 0, "ultima": "nvidia: GSP firmware 580.178.04 ok"}  # sin hostname
    r = h.sonda_gpu_gsp(tmp_path, _correr({"nvidia-smi": _SMI_OK, "journalctl": (0, "")}))
    assert r["veredicto"] == "disponible" and r["kernel_gsp"]["ultima"] is None


def test_gpu_gsp_control_negativo_pci_sin_smi(tmp_path: Path) -> None:
    _pci_gpu(tmp_path)
    assert h.sonda_gpu_gsp(tmp_path, _correr({"nvidia-smi": (9, ""), "journalctl": _KERNEL_SANO}))["veredicto"] == "PCI_SIN_GSP"
    assert h.sonda_gpu_gsp(tmp_path, _cae)["veredicto"] == "PCI_SIN_GSP"  # nvidia-smi excede el timeout


def test_gpu_gsp_control_negativo_errores_con_smi_ok(tmp_path: Path) -> None:
    _pci_gpu(tmp_path)
    for linea in ("NVRM: GSP RPC timeout", "NVRM: rpc failed", "nvidia: GSP init error"):
        r = h.sonda_gpu_gsp(tmp_path, _correr({"nvidia-smi": _SMI_OK, "journalctl": (0, f"oct 12 host kernel: {linea}")}))
        assert r["veredicto"] == "PCI_SIN_GSP" and r["kernel_gsp"]["errores"] == 1, linea


def test_gpu_gsp_pci_ausente_es_indeterminado(tmp_path: Path) -> None:
    _w(tmp_path, "sys/bus/pci/devices/0000:00:00.0/vendor", "0x10de\n")
    _w(tmp_path, "sys/bus/pci/devices/0000:00:00.0/class", "0x060400\n")  # puente, no display
    r = h.sonda_gpu_gsp(tmp_path, _correr({"nvidia-smi": _SMI_OK, "journalctl": _KERNEL_SANO}))
    assert r["veredicto"] == "INDETERMINADO" and r["pci_display_nvidia"] == []


def test_gpu_gsp_sin_journal_nunca_disponible(tmp_path: Path) -> None:
    _pci_gpu(tmp_path)
    r = h.sonda_gpu_gsp(tmp_path, _correr({"nvidia-smi": _SMI_OK, "journalctl": (1, "")}))
    assert r["veredicto"] == "INDETERMINADO" and h.es_nc(r["kernel_gsp"])


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
    assert set(r) == set(h.SONDAS) and len(r) == 18 and h.es_nc(r["os_release"])


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


# drm_modeset
def _modprobe(raiz: Path, etc: dict[str, str], usr: dict[str, str] | None = None, cmdline: str | None = None) -> None:
    for n, t in etc.items():
        _w(raiz, f"etc/modprobe.d/{n}", t)
    for n, t in (usr or {}).items():
        _w(raiz, f"usr/lib/modprobe.d/{n}", t)
    if cmdline is not None:
        _w(raiz, "proc/cmdline", cmdline)


def test_drm_solo_paquete_no_es_override(tmp_path: Path) -> None:
    _modprobe(tmp_path, {"nvidia-graphics-drivers-kms.conf": "options nvidia_drm modeset=1\n", "zz-nvidia-drm-override.conf": "options nvidia-drm modeset=0\n"}, cmdline="BOOT_IMAGE=/x ro\n")
    r = h.sonda_drm_modeset(tmp_path, subprocess.run)
    assert r["modeset"]["efectivo"] == "0" and r["modeset"]["fuente"] == "zz-nvidia-drm-override.conf"  # gana el ultimo por nombre
    assert r["override_no_soportado"] is False
    assert r["fbdev"] == {"efectivo": None, "fuente": None, "declaraciones": []}
    assert h.es_nc(r["sysfs_modeset"])


def test_drm_archivo_propio_es_override_y_etc_tapa_usr(tmp_path: Path) -> None:
    _modprobe(tmp_path, {"50-mio.conf": "# c\noptions nvidia-drm modeset=1 fbdev=1\n", "x.conf": "options otro modeset=7\n"}, usr={"50-mio.conf": "options nvidia-drm modeset=0\n"})
    _w(tmp_path, "sys/module/nvidia_drm/parameters/modeset", "Y\n")
    r = h.sonda_drm_modeset(tmp_path, subprocess.run)
    assert r["override_no_soportado"] is True
    assert r["modeset"]["declaraciones"] == [{"param": "modeset", "valor": "1", "archivo": "50-mio.conf"}]  # control: el de /usr/lib (0) quedo tapado; otro modulo no cuenta
    assert r["fbdev"]["efectivo"] == "1" and r["sysfs_modeset"] == "Y"


def test_drm_cmdline_es_override_y_pesa_mas(tmp_path: Path) -> None:
    _modprobe(tmp_path, {"zz-nvidia-drm-override.conf": "options nvidia-drm modeset=0\n"}, cmdline="ro nvidia_drm.modeset=1 quiet\n")
    r = h.sonda_drm_modeset(tmp_path, subprocess.run)
    assert r["modeset"]["efectivo"] == "1" and r["modeset"]["fuente"] == "/proc/cmdline" and r["override_no_soportado"] is True


def test_drm_nada_legible_es_nc(tmp_path: Path) -> None:
    assert h.es_nc(h.sonda_drm_modeset(tmp_path, subprocess.run))


def test_drm_sin_declaracion_no_es_override(tmp_path: Path) -> None:
    _modprobe(tmp_path, {"a.conf": "blacklist x\n"})
    r = h.sonda_drm_modeset(tmp_path, subprocess.run)
    assert r["modeset"]["efectivo"] is None and r["override_no_soportado"] is False


# arranque_tras_actualizacion
def _kernel(raiz: Path, v: str, initrd: str | None = "x", modulos: bool = True, vmlinuz: bool = True) -> None:
    _w(raiz, f"lib/modules/{v}/modules.dep", "")
    if modulos:
        _w(raiz, f"lib/modules/{v}/kernel/nvidia-580-open/nvidia.ko", "m")
    if initrd is not None:
        _w(raiz, f"boot/initrd.img-{v}", initrd)
    if vmlinuz:
        _w(raiz, f"boot/vmlinuz-{v}", "k")


@pytest.fixture
def en_uso(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(h.platform, "release", lambda: "6.17.0-1032-nvidia")


def test_arranque_sano(tmp_path: Path, en_uso: None) -> None:
    _kernel(tmp_path, "6.17.0-1032-nvidia")
    _kernel(tmp_path, "7.0.0-1019-nvidia")
    _w(tmp_path, "lib/modules/kernel/x", "")  # directorio 'kernel' no es una version
    _w(tmp_path, "sys/firmware/efi/efivars/SecureBoot-8be4", "\x06\x00\x00\x00\x01")
    r = h.sonda_arranque_tras_actualizacion(tmp_path, _cae)
    assert r["kernel_nuevo"] == "7.0.0-1019-nvidia" and r["secure_boot"] is True and r["listo_para_reiniciar"] is True
    assert r["kernels"]["6.17.0-1032-nvidia"] == {"initrd": True, "modulos_nvidia": True, "dkms_sin_firmar": False, "kernel_en_uso": True}
    assert r["kernels"]["7.0.0-1019-nvidia"]["kernel_en_uso"] is False
    assert list(r["kernels"]) == ["6.17.0-1032-nvidia", "7.0.0-1019-nvidia"]


def test_control_negativo_kernel_nuevo_sin_initrd(tmp_path: Path, en_uso: None) -> None:
    _kernel(tmp_path, "6.17.0-1032-nvidia")
    _kernel(tmp_path, "7.0.0-1019-nvidia", initrd=None)
    r = h.sonda_arranque_tras_actualizacion(tmp_path, _cae)
    assert r["kernels"]["7.0.0-1019-nvidia"]["initrd"] is False and r["listo_para_reiniciar"] is False
    assert r["kernels"]["6.17.0-1032-nvidia"]["initrd"] is True  # el viejo sano no salva al nuevo


def test_initrd_vacio_y_sin_modulos(tmp_path: Path, en_uso: None) -> None:
    _kernel(tmp_path, "7.0.0-1019-nvidia", initrd="")
    assert h.sonda_arranque_tras_actualizacion(tmp_path, _cae)["listo_para_reiniciar"] is False
    _w(tmp_path, "boot/initrd.img-7.0.0-1019-nvidia", "x")
    assert h.sonda_arranque_tras_actualizacion(tmp_path, _cae)["listo_para_reiniciar"] is not False  # control: con initrd y modulos ya no bloquea
    (tmp_path / "lib/modules/7.0.0-1019-nvidia/kernel/nvidia-580-open/nvidia.ko").unlink()
    r = h.sonda_arranque_tras_actualizacion(tmp_path, _cae)
    assert r["kernels"]["7.0.0-1019-nvidia"]["modulos_nvidia"] is False and r["listo_para_reiniciar"] is False


def test_modulos_en_updates_y_kernel_solo_en_boot(tmp_path: Path, en_uso: None) -> None:
    _kernel(tmp_path, "7.0.0-1019-nvidia", modulos=False, vmlinuz=False)
    _w(tmp_path, "lib/modules/7.0.0-1019-nvidia/updates/nvidia.ko.zst", "m")
    _w(tmp_path, "boot/vmlinuz-8.0.0-1-nvidia", "k")  # sin /lib/modules ni initrd
    r = h.sonda_arranque_tras_actualizacion(tmp_path, _cae)
    assert r["kernel_nuevo"] == "8.0.0-1-nvidia" and r["listo_para_reiniciar"] is False
    assert r["kernels"]["7.0.0-1019-nvidia"]["modulos_nvidia"] is True


def test_dpkg_a_medio_configurar_baja_listo_y_limpio_no_lo_sube(tmp_path: Path, en_uso: None) -> None:
    _kernel(tmp_path, "7.0.0-1019-nvidia")
    _w(tmp_path, "sys/firmware/efi/efivars/SecureBoot-8be4", "\x06\x00\x00\x00\x00")
    limpio = h.sonda_arranque_tras_actualizacion(tmp_path, _correr({"dpkg --audit": (0, "")}))
    assert limpio["dpkg_consistente"] is True and limpio["listo_para_reiniciar"] is True
    roto = h.sonda_arranque_tras_actualizacion(tmp_path, _correr({"dpkg --audit": (0, "The following packages are only half configured:\n nvidia-dkms-580-open")}))
    assert roto["dpkg_consistente"] is False and roto["listo_para_reiniciar"] is False  # control negativo: el mismo arbol con dpkg limpio da True
    sin_leer = h.sonda_arranque_tras_actualizacion(tmp_path, _cae)
    assert h.es_nc(sin_leer["dpkg_consistente"]) and sin_leer["listo_para_reiniciar"] is True  # no leer no baja ni sube


def test_cx7_hotplug_marcador_y_bandera(tmp_path: Path) -> None:
    ruta = "sys/devices/platform/MTKP0001:00/pcie_hotplug/hotplug_enabled"
    _w(tmp_path, ruta, "1\n")
    _w(tmp_path, "etc/nvidia/cx7-hotplug-enabled", "")
    assert h.sonda_cx7_hotplug(tmp_path, _cae) == {"marcador": True, "hotplug_enabled": "1"}
    (tmp_path / "etc/nvidia/cx7-hotplug-enabled").unlink()
    _w(tmp_path, ruta, "0")
    assert h.sonda_cx7_hotplug(tmp_path, _cae) == {"marcador": False, "hotplug_enabled": "0"}  # control negativo: sin marcador y bandera 0 no se informa como activo
    (tmp_path / ruta).unlink()
    r = h.sonda_cx7_hotplug(tmp_path, _cae)
    assert r["marcador"] is False and h.es_nc(r["hotplug_enabled"])  # sin bandera legible: NOT_COLLECTED, nunca 0 ni 1


def test_el_kernel_a_evaluar_es_el_que_grub_arrancara_no_el_mas_alto(tmp_path: Path, en_uso: None) -> None:
    _kernel(tmp_path, "6.17.0-1032-nvidia")
    _kernel(tmp_path, "7.0.0-1019-nvidia", initrd=None)  # el mas alto esta roto, pero GRUB no lo arranca
    sin_fijar = h.sonda_arranque_tras_actualizacion(tmp_path, _cae)
    assert sin_fijar["kernel_nuevo"] == "7.0.0-1019-nvidia" and sin_fijar["kernel_grub"] is None and sin_fijar["listo_para_reiniciar"] is False
    _w(tmp_path, "etc/default/grub", 'GRUB_TIMEOUT=5\nGRUB_DEFAULT="Advanced options for DGX OS GNU/Linux>DGX OS GNU/Linux, with Linux 6.17.0-1032-nvidia"\n')
    fijado = h.sonda_arranque_tras_actualizacion(tmp_path, _cae)
    assert fijado["kernel_grub"] == "6.17.0-1032-nvidia" and fijado["kernel_nuevo"] == "6.17.0-1032-nvidia"  # control negativo: sin la linea de GRUB manda el mas alto
    _w(tmp_path, "etc/default/grub", "GRUB_DEFAULT=0\n")
    assert h.sonda_arranque_tras_actualizacion(tmp_path, _cae)["kernel_grub"] is None  # un indice numerico no nombra ningun kernel
    _w(tmp_path, "etc/default/grub", 'GRUB_DEFAULT="with Linux 9.9.9-fantasma"\n')
    assert h.sonda_arranque_tras_actualizacion(tmp_path, _cae)["kernel_nuevo"] == "7.0.0-1019-nvidia"  # un kernel fijado que no existe no se evalua


def test_arranque_sin_kernels_es_nc(tmp_path: Path) -> None:
    assert h.es_nc(h.sonda_arranque_tras_actualizacion(tmp_path, _cae))


def test_initrd_ilegible_es_nc_nunca_true(tmp_path: Path, en_uso: None, monkeypatch: pytest.MonkeyPatch) -> None:
    _kernel(tmp_path, "7.0.0-1019-nvidia")
    monkeypatch.setattr(h, "_initrd_ok", lambda p: h._nc("permiso"))
    r = h.sonda_arranque_tras_actualizacion(tmp_path, _cae)
    assert h.es_nc(r["listo_para_reiniciar"]) and h.es_nc(r["kernels"]["7.0.0-1019-nvidia"]["initrd"])


def test_initrd_ok_oserror_real(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(self: Path, *a: Any, **k: Any) -> Any:
        raise PermissionError("no")
    monkeypatch.setattr(Path, "stat", boom)
    assert h.es_nc(h._initrd_ok(tmp_path / "i"))


def test_secure_boot_por_mokutil_y_fallo(tmp_path: Path) -> None:
    assert h._secure_boot(tmp_path, _correr({"mokutil": (0, "SecureBoot enabled")})) is True
    assert h._secure_boot(tmp_path, _correr({"mokutil": (0, "SecureBoot disabled")})) is False
    assert h.es_nc(h._secure_boot(tmp_path, _cae))
    assert h.es_nc(h._secure_boot(tmp_path, _correr({"mokutil": (0, "???")})))


def test_secure_boot_efivar_truncado_o_ilegible_cae_a_mokutil(tmp_path: Path) -> None:
    _w(tmp_path, "sys/firmware/efi/efivars/SecureBoot-a", "\x06\x00")
    (tmp_path / "sys/firmware/efi/efivars/SecureBoot-b").mkdir()  # read_bytes sobre un directorio: OSError
    assert h._secure_boot(tmp_path, _correr({"mokutil": (0, "SecureBoot disabled")})) is False
    _w(tmp_path, "sys/firmware/efi/efivars/SecureBoot-c", "\x06\x00\x00\x00\x00")
    assert h._secure_boot(tmp_path, _cae) is False  # efivar valor 0


def _dkms(raiz: Path, ko: str, contenido: bytes, v: str = "7.0.0-1019-nvidia") -> None:
    _kernel(raiz, v)
    p = raiz / f"lib/modules/{v}/updates/{ko}"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(contenido)
    _w(raiz, "usr/sbin/dkms", "")
    _w(raiz, "sys/firmware/efi/efivars/SecureBoot-a", "\x06\x00\x00\x00\x01")


_ESTADO = _correr({"dkms": (0, f"nvidia/580, 7.0.0-1019-nvidia, aarch64: installed\n")})
_FIRMA = b"mod\n~Module signature appended~\n"


def test_dkms_sin_firmar_bajo_secure_boot_bloquea(tmp_path: Path, en_uso: None) -> None:
    _dkms(tmp_path, "nvidia.ko", b"sin firma")
    r = h.sonda_arranque_tras_actualizacion(tmp_path, _ESTADO)
    assert r["kernels"]["7.0.0-1019-nvidia"]["dkms_sin_firmar"] is True and r["listo_para_reiniciar"] is False


def test_dkms_firmado_no_bloquea(tmp_path: Path, en_uso: None) -> None:
    _dkms(tmp_path, "nvidia.ko", _FIRMA)
    r = h.sonda_arranque_tras_actualizacion(tmp_path, _ESTADO)
    assert r["kernels"]["7.0.0-1019-nvidia"]["dkms_sin_firmar"] is False and r["listo_para_reiniciar"] is True


def test_dkms_casos_limite(tmp_path: Path, en_uso: None) -> None:
    _dkms(tmp_path, "nvidia.ko.zst", b"z")
    d = tmp_path / "lib/modules/7.0.0-1019-nvidia"
    assert h.es_nc(h._dkms_sin_firmar(tmp_path, _ESTADO, "7.0.0-1019-nvidia", d, True))  # comprimido: no se puede leer la firma
    assert h.es_nc(h.sonda_arranque_tras_actualizacion(tmp_path, _ESTADO)["listo_para_reiniciar"])
    assert h.es_nc(h._dkms_sin_firmar(tmp_path, _cae, "7.0.0-1019-nvidia", d, True))  # dkms presente pero no corre
    assert h._dkms_sin_firmar(tmp_path, _correr({"dkms": (0, "otro/1, 7.0.0-1019-nvidia: installed")}), "7.0.0-1019-nvidia", d, True) is False  # dkms sin nvidia
    assert h._dkms_sin_firmar(tmp_path, _ESTADO, "7.0.0-1019-nvidia", d, False) is False  # sin Secure Boot
    assert h.es_nc(h._dkms_sin_firmar(tmp_path, _ESTADO, "7.0.0-1019-nvidia", d, h._nc("sb")))  # estado SB desconocido
    assert h._dkms_sin_firmar(tmp_path / "otro", _ESTADO, "7.0.0-1019-nvidia", d, True) is False  # sin dkms instalado


def test_dkms_ko_ilegible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _dkms(tmp_path, "nvidia.ko", b"x")
    def boom(self: Path) -> bytes:
        raise PermissionError("no")
    monkeypatch.setattr(Path, "read_bytes", boom)
    d = tmp_path / "lib/modules/7.0.0-1019-nvidia"
    assert h.es_nc(h._dkms_sin_firmar(tmp_path, _ESTADO, "7.0.0-1019-nvidia", d, True))


def test_dkms_status_sin_modulos_updates_es_false(tmp_path: Path) -> None:
    _kernel(tmp_path, "7.0.0-1019-nvidia")
    _w(tmp_path, "usr/sbin/dkms", "")
    assert h._dkms_sin_firmar(tmp_path, _ESTADO, "7.0.0-1019-nvidia", tmp_path / "lib/modules/7.0.0-1019-nvidia", True) is False


def test_recoge_incluye_las_dos_sondas(tmp_path: Path) -> None:
    r = h.recoge(tmp_path, _cae)
    assert "drm_modeset" in r and "arranque_tras_actualizacion" in r


def test_drm_conf_ilegible_se_omite(tmp_path: Path) -> None:
    (tmp_path / "etc/modprobe.d/roto.conf").mkdir(parents=True)  # leer un directorio: OSError
    _modprobe(tmp_path, {}, cmdline="ro\n")
    assert h.sonda_drm_modeset(tmp_path, subprocess.run)["override_no_soportado"] is False


def test_secure_boot_variable_ilegible_se_nombra_en_el_nc(tmp_path: Path) -> None:
    """Una variable EFI que no se puede leer no se salta en silencio: el NOT_COLLECTED la nombra (control negativo: con el estado legible no hay NC)."""
    (tmp_path / "sys/firmware/efi/efivars/SecureBoot-8be4").mkdir(parents=True)  # un directorio no se lee como archivo
    r = h._secure_boot(tmp_path, _cae)
    assert isinstance(r, str) and h.es_nc(r) and "SecureBoot-8be4" in r and "ilegibles" in r
    _w(tmp_path, "sys/firmware/efi/efivars/SecureBoot-aaaa", "\x06\x00\x00\x00\x01")
    assert h._secure_boot(tmp_path, _cae) is True


# recomendaciones_personal
def _rp(tmp_path: Path, correr: Any = None) -> dict[str, Any]:
    r = h.sonda_recomendaciones_personal(tmp_path, correr or _correr({}))
    assert isinstance(r, dict)
    return r


def test_recomendaciones_cumple(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISPLAY", ":1")
    _w(tmp_path, "proc/cmdline", "ro iommu.passthrough=1 quiet")
    _w(tmp_path, "proc/sys/vm/overcommit_memory", "2\n")
    _w(tmp_path, "proc/sys/vm/overcommit_ratio", "90\n")
    _w(tmp_path, "sys/module/sbsa_gwdt/parameters/action", "1\n")
    r = _rp(tmp_path, _correr({"xset": (0, "DPMS (Display Power Management Signaling):\n  DPMS is Disabled\n")}))
    assert [v["cumple"] for v in r.values()] == [True, True, True, True]
    assert r["overcommit"]["hilo"] == 368536 and r["overcommit"]["post"] == 23 and "CUDA" in r["overcommit"]["nota"]


def test_recomendaciones_no_cumple(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISPLAY", ":1")
    _w(tmp_path, "proc/cmdline", "ro iommu.passthrough=0")
    _w(tmp_path, "proc/sys/vm/overcommit_memory", "0\n")
    _w(tmp_path, "proc/sys/vm/overcommit_ratio", "50\n")
    _w(tmp_path, "etc/modprobe.d/x.conf", "options sbsa_gwdt action=0\n")
    _w(tmp_path, "usr/lib/modprobe.d/ignora.conf", "options otro action=1\n")
    r = _rp(tmp_path, _correr({"xset": (0, "  DPMS is Enabled\n")}))
    assert [v["cumple"] for v in r.values()] == [False, False, False, False]
    assert r["iommu_passthrough"]["actual"] == "iommu.passthrough=0" and "declarado" in r["sbsa_gwdt_action"]["actual"]


def test_recomendaciones_sbsa_declarado_cumple(tmp_path: Path) -> None:
    _w(tmp_path, "etc/modprobe.d/sbsa_gwdt.conf", "options sbsa_gwdt action=1\n")
    assert _rp(tmp_path)["sbsa_gwdt_action"]["cumple"] is True


def test_recomendaciones_no_legible_es_none_nunca_true(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISPLAY", raising=False)
    r = _rp(tmp_path)  # arbol vacio: control negativo, ninguna lectura posible
    assert [v["cumple"] for v in r.values()] == [None, None, None, None]
    assert h.es_nc(r["iommu_passthrough"]["actual"]) and h.es_nc(r["sbsa_gwdt_action"]["actual"]) and h.es_nc(r["dpms"]["actual"])
    assert all(h.es_nc(v) for v in r["overcommit"]["actual"].values())


def test_recomendaciones_lecturas_parciales(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _w(tmp_path, "proc/cmdline", "ro quiet")  # sin iommu.passthrough: None, no False ni True
    _w(tmp_path, "proc/sys/vm/overcommit_memory", "2")  # coincide, ratio ilegible: None
    _w(tmp_path, "etc/modprobe.d/otro.conf", "options otro x=1\n")  # modprobe legible sin declaracion
    monkeypatch.setenv("DISPLAY", ":1")
    r = _rp(tmp_path, _correr({"xset": (0, "sin linea dpms")}))
    assert [v["cumple"] for v in r.values()] == [None, None, None, None]
    assert "ausente" in r["iommu_passthrough"]["actual"] and "no expuesto" in r["sbsa_gwdt_action"]["actual"] and "sin linea" in r["dpms"]["actual"]
    _w(tmp_path, "proc/sys/vm/overcommit_ratio", "10")  # una diferencia leida decide aunque falte otra
    assert _rp(tmp_path)["overcommit"]["cumple"] is False


def test_recomendaciones_xset_cae(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISPLAY", ":1")
    r = _rp(tmp_path, _cae)
    assert r["dpms"]["cumple"] is None and h.es_nc(r["dpms"]["actual"])


def test_recomendaciones_conf_ilegible_se_omite(tmp_path: Path) -> None:
    (tmp_path / "etc/modprobe.d/roto.conf").mkdir(parents=True)  # directorio con nombre .conf: read_text lanza OSError
    r = _rp(tmp_path)["sbsa_gwdt_action"]
    assert r["cumple"] is None and "sin modprobe.d legible" in r["actual"]
