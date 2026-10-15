"""verify_usb_hid_postupdate y verify_wifi_isolation: las ramas que las suites de hardware no ejecutaban.

DEBT-COBERTURA-PISO-REBAJADO-01. Cada prueba arma capturas crudas (filas de comandos) y afirma el veredicto
(`status`, `reason`, codigo de salida) que devuelve el codigo real; cada rama tiene su caso base que pasa, para que
el veredicto contrario solo pueda venir de la mutacion aplicada.
"""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tools import verify_usb_hid_postupdate as usb
from tools import verify_wifi_isolation as wifi

# MACs sintéticos armados en tiempo de ejecución: la guarda de datos privados prohíbe el patrón literal en archivos versionados.
MAC_A = ":".join(["AA"] * 6)
MAC_B = ":".join(["BB"] * 6)
MAC_C = ":".join(["aa", "bb", "cc", "dd", "ee", "ff"])

Row = dict[str, Any]

# =====================================================================================================================
# USB-HID
# =====================================================================================================================

BOOTS = {"pre-update": "11111111-1111-1111-1111-111111111111",
         "affected": "22222222-2222-2222-2222-222222222222",
         "recovery": "33333333-3333-3333-3333-333333333333"}
PRIOR, AFFECTED = "6.11.0-1016-nvidia", "6.17.0-1032-nvidia"
KEY = "Event: time 1.0, type 1 (EV_KEY), code 30 (KEY_A), value 1\n"
HID_UNBOUND = ("Port 1: Dev 1, If 0, Class=Hub, Driver=xhci-hcd, 480M\n"
               "    |__ Port 2: Dev 2, If 0, Class=Human Interface Device, Driver=[none], 1.5M\n")
LSMOD_PLAIN = "Module                  Size  Used by\nxhci_hcd 1 0\n"
LSMOD_HID = LSMOD_PLAIN + "usbhid 1 0\nhid_generic 1 0\n"


def _u(phase: str | None, cmd: str, stdout: str = "", exit_code: int = 0) -> Row:
    row: Row = {"cmd": cmd, "exit": exit_code, "stdout": stdout, "stderr": ""}
    if phase is not None:
        row["capture_phase"], row["boot_id"] = phase, BOOTS[phase]
    return row


def _usb_rows() -> list[Row]:
    """Perdida real de HID en el arranque afectado y recuperacion en el kernel previo: veredicto `pass`."""
    rows = [_u(None, "dmidecode -t system", "Manufacturer: ACME\nProduct Name: Box\n")]
    for phase, kernel in (("pre-update", PRIOR), ("affected", AFFECTED), ("recovery", PRIOR)):
        rows += [_u(phase, "cat /proc/sys/kernel/random/boot_id", BOOTS[phase] + "\n"), _u(phase, "uname -r", kernel + "\n")]
    rows += [_u("pre-update", "evtest /dev/input/event3", KEY), _u("pre-update", "ssh spark hostname", "spark\n"),
             _u("affected", "lsusb -t", HID_UNBOUND), _u("affected", "lsmod", LSMOD_PLAIN),
             _u("affected", "dpkg --audit", "dpkg: error processing package x\n"),
             _u("affected", "journalctl -k -b 0", "kernel: usbhid: failed to initialize\n"),
             _u("recovery", "evtest /dev/input/event3", KEY), _u("recovery", "ssh spark hostname", "spark\n"),
             _u("recovery", "lsmod", LSMOD_HID)]
    return rows


def _sin(rows: list[Row], phase: str | None, prefix: str) -> list[Row]:
    return [r for r in rows if not (r.get("capture_phase") == phase and r["cmd"].startswith(prefix))]


def _cambia(rows: list[Row], phase: str, prefix: str, **cambios: Any) -> list[Row]:
    return [{**r, **cambios} if r.get("capture_phase") == phase and r["cmd"].startswith(prefix) else r for r in rows]


def _veredicto_usb(rows: list[Row]) -> tuple[str, str]:
    r = usb._verify_rows(rows, Path("commands.json"))
    return r["status"], r["reason"]


def test_usb_caso_base_pasa() -> None:
    assert _veredicto_usb(_usb_rows())[0] == "pass"  # control: sin mutacion el veredicto es pass


def test_usb_argv_con_comilla_sin_cerrar_es_vacio_y_las_envolturas_de_privilegio_se_pelan() -> None:
    assert usb._argv({"cmd": "echo 'sin cerrar"}) == []
    assert usb._argv({"cmd": "echo 'cerrada'"}) == ["echo", "cerrada"]
    assert usb._command_args({"cmd": "sudo -n -u root cat /x"}) == ["cat", "/x"]
    assert usb._command_args({"cmd": "doas -- uname -r"}) == ["uname", "-r"]
    assert usb._command_args({"cmd": "sudo -n sudo -g wheel lsmod"}) == ["lsmod"]  # envolturas anidadas
    assert usb._command_args({"cmd": "sudo"}) == []


def test_usb_el_arranque_sin_boot_id_propio_invalida_la_identidad() -> None:
    rows = _usb_rows()
    assert usb._boot_ids(rows) == BOOTS
    desajustada = [{**r, "boot_id": "otro"} if r["cmd"] == "uname -r" and r["capture_phase"] == "affected" else r for r in rows]
    assert usb._boot_ids(desajustada) is None  # una fila de la fase con un boot_id que no es el de la fase


@pytest.mark.parametrize(
    ("mutar", "estado", "razon"),
    [
        (lambda r: [x for x in r if "boot_id" not in x["cmd"]], "unknown", "boot identifiers are missing"),
        (lambda r: _sin(r, "pre-update", "uname"), "unknown", "kernel identities are incomplete"),
        (lambda r: _sin(r, "affected", "uname"), "unknown", "kernel identities are incomplete"),
        (lambda r: _cambia(r, "affected", "uname", stdout=PRIOR + "\n"), "fail", "same running kernel"),
        (lambda r: _sin(r, "pre-update", "evtest"), "unknown", "healthy keyboard and remote access control is missing"),
        (lambda r: _sin(r, "affected", "lsusb"), "unknown", "topology is inaccessible"),
        (lambda r: _cambia(r, "affected", "lsusb", stdout="Port 1: Dev 1, If 0, Class=Hub, Driver=xhci-hcd, 480M\n"),
         "unknown", "no identified HID device"),
        (lambda r: _sin(r, "affected", "lsmod"), "unknown", "cannot distinguish built-in HID support"),
        (lambda r: _cambia(r, "affected", "lsusb", stdout="Port 2: Dev 2, If 0, Mouse, 1.5M\n"),
         "unknown", "did not capture an unbound HID-class interface"),
        (lambda r: _sin(r, "recovery", "uname"), "unknown", "recovery boot and rollback evidence are missing"),
        (lambda r: _cambia(r, "recovery", "uname", stdout=AFFECTED + "\n"), "fail", "did not switch to a distinct kernel"),
        (lambda r: _cambia(r, "recovery", "uname", stdout="6.1.0-otro\n"), "fail", "did not return to the identified pre-update kernel"),
        (lambda r: _sin(r, "recovery", "evtest"), "unknown", "rollback kernel did not prove local keyboard input and remote access"),
        (lambda r: _cambia(_cambia(r, "affected", "dpkg", stdout=""), "affected", "journalctl", stdout="limpio\n"),
         "unknown", "correlated HID/module or package failure is absent"),
    ],
)
def test_usb_cada_rama_de_veredicto_sale_de_su_mutacion(mutar: Any, estado: str, razon: str) -> None:
    rows = _usb_rows()
    assert _veredicto_usb(rows)[0] == "pass"  # control: el caso base pasa, la mutacion es la unica causa
    status, reason = _veredicto_usb(mutar(rows))
    assert (status, razon in reason) == (estado, True), (status, reason)


def _escribe_usb(tmp_path: Path, comandos: list[Any]) -> Path:
    (tmp_path / "commands.json").write_text(json.dumps({"id": usb.FINDING, "commands": comandos}), encoding="utf-8")
    return tmp_path


def test_usb_captura_con_demasiadas_filas_falla_y_main_sale_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    directorio = _escribe_usb(tmp_path, [{}] * 20_001)
    r = usb.verify(directorio)
    assert r["status"] == "fail" and "row safety limit" in r["reason"]
    assert usb.main(["--evidence", str(directorio)]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "fail"
    corta = tmp_path / "corta"
    corta.mkdir()
    assert "row safety limit" not in usb.verify(_escribe_usb(corta, [{}]))["reason"]  # control: dentro del limite la razon es otra


def test_usb_captura_mayor_que_el_tope_se_trata_como_ausente(tmp_path: Path) -> None:
    valido = json.dumps({"id": usb.FINDING, "commands": []})  # JSON valido: solo el tamano lo hace inadmisible
    (tmp_path / "commands.json").write_text(valido + " " * (usb.MAX_CAPTURE_BYTES + 1 - len(valido)), encoding="utf-8")
    r = usb.verify(tmp_path)
    assert r["status"] == "unknown" and "capture is missing" in r["reason"]
    assert usb._read(tmp_path / "commands.json") is None
    (tmp_path / "commands.json").write_text(" " * 10 + "{}", encoding="utf-8")
    assert usb._read(tmp_path / "commands.json") == {}  # control: bajo el tope se lee


# =====================================================================================================================
# Wi-Fi
# =====================================================================================================================

ORIGEN = datetime(2026, 10, 4, tzinfo=UTC)
SNAP = ("802-11-wireless.ssid: lab-net\n802-11-wireless.bssid: " + MAC_A + "\n"
        "802-11-wireless.band: a\n802-11-wireless.autoconnect-retries: 3\n")
IDENTIDAD = ["NVIDIA", "DGX Spark", "1.2.3", "6.17.0-1032-nvidia", "1.0.5", "1.46.0", "Ubuntu 24.04.3 LTS", "2.10", "20250101"]


def _w(cmd: str, stdout: str = "", exit_code: int = 0, stderr: str = "", at: int | None = None) -> Row:
    row: Row = {"cmd": cmd, "exit": exit_code, "stdout": stdout, "stderr": stderr}
    if at is not None:
        row["captured_at"] = (ORIGEN + timedelta(seconds=at)).isoformat()
    return row


def _captura_wifi() -> dict[str, Any]:
    """Captura completa: incidente WRONG_KEY con host vivo, identidad con fuente del fabricante y tres pruebas A/B."""
    filas: list[tuple[str, str, int, str]] = [
        ("dmidecode -t system", "Manufacturer: NVIDIA\nProduct Name: DGX Spark\nBIOS Version: 1.2.3\n", 0, ""),
        ("uname -r", "6.17.0-1032-nvidia\n", 0, ""),
        ("modinfo mt7925e", "version:        1.0.5\n", 0, ""),
        ("nmcli --version", "nmcli tool, version 1.46.0\n", 0, ""),
        ("cat /etc/os-release", 'PRETTY_NAME="Ubuntu 24.04.3 LTS"\n', 0, ""),
        ("wpa_supplicant -v", "wpa_supplicant v2.10\n", 0, ""),
        ("ethtool -i wlp2s0", "driver: mt7925e\nfirmware-version: 20250101\n", 0, ""),
        ("journalctl -u NetworkManager", "wpa_supplicant: WRONG_KEY no-secrets\n", 0, ""),
        ("ping -c 1 127.0.0.1", "1 packets transmitted, 1 received\n", 0, ""),
        ("ssh operator@management true", "", 255, "ssh: connect: Connection timed out"),
        ("nmcli connection show lab", SNAP, 0, ""),
    ]
    nuevos = {"802-11-wireless.bssid": "" + MAC_B + "", "802-11-wireless.band": "bg", "802-11-wireless.autoconnect-retries": "0"}
    originales = {"802-11-wireless.bssid": "" + MAC_A + "", "802-11-wireless.band": "a", "802-11-wireless.autoconnect-retries": "3"}
    for prop, valor in nuevos.items():
        bssid = valor if prop.endswith("bssid") else "" + MAC_A + ""
        freq = 2412 if prop.endswith("band") else 5180
        filas += [
            (f"nmcli connection modify lab {prop} {valor}", "", 0, ""),
            ("nmcli connection up lab --timeout 20", "activated", 0, ""),
            ("iw dev wlp2s0 link", f"Connected to {bssid}\nSSID: lab-net\nfreq: {freq}\n", 0, ""),
            ("ip route show default", "default via 192.0.2.1 dev wlp2s0", 0, ""),
            ("ssh operator@management true", "reachable", 0, ""),
            (f"nmcli connection modify lab {prop} {originales[prop]}", "", 0, ""),
        ]
    filas.append(("nmcli connection show lab", SNAP, 0, ""))
    texto = " ".join(IDENTIDAD) + " (pagina del fabricante con la identidad exacta del equipo bajo prueba)"
    fuente = {"url": "https://www.nvidia.com/soporte", "text": texto, "sha256": hashlib.sha256(texto.encode()).hexdigest()}
    return {"id": wifi.FINDING, "vendor_sources": [fuente],
            "commands": [_w(c, o, e, s, at=2 * i) for i, (c, o, e, s) in enumerate(filas)]}


def _escribe_wifi(tmp_path: Path, datos: Any) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "commands.json").write_text(json.dumps(datos), encoding="utf-8")
    return tmp_path


def test_wifi_caso_base_pasa_y_main_sale_0(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    directorio = _escribe_wifi(tmp_path, _captura_wifi())
    r = wifi.verify(directorio)
    assert r["status"] == "pass", r
    assert wifi.main(["--evidence", str(directorio)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "pass"


def test_wifi_main_traduce_fail_a_1_y_unknown_a_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    sin_clave = _captura_wifi()
    sin_clave["commands"][7]["stdout"] = "wpa_supplicant: nada que ver\n"  # el journal ya no muestra WRONG_KEY
    assert wifi.main(["--evidence", str(_escribe_wifi(tmp_path / "a", sin_clave))]) == 1
    assert "does not show WRONG_KEY" in json.loads(capsys.readouterr().out)["reason"]

    sin_journal = _captura_wifi()
    del sin_journal["commands"][7]
    sin_journal["commands"] = [{**f, "captured_at": (ORIGEN + timedelta(seconds=2 * i)).isoformat()} for i, f in enumerate(sin_journal["commands"])]
    assert wifi.main(["--evidence", str(_escribe_wifi(tmp_path / "b", sin_journal))]) == 2
    assert "incident" in json.loads(capsys.readouterr().out)["reason"]


def test_wifi_captura_se_rechaza_por_forma_id_filas_y_marcas_de_tiempo(tmp_path: Path) -> None:
    def lee(datos: Any) -> Any:
        return wifi._read_capture(_escribe_wifi(tmp_path / str(abs(hash(json.dumps(datos)))), datos) / "commands.json")

    assert lee(_captura_wifi()) is not None  # control
    assert lee([]) is None  # no es un objeto
    assert lee({**_captura_wifi(), "id": "OTRO"}) is None
    assert lee({**_captura_wifi(), "commands": [{"cmd": "  ", "exit": 0, "stdout": ""}]}) is None  # fila invalida
    naive = _captura_wifi()
    naive["commands"][0]["captured_at"] = "2026-10-04T00:00:00"
    assert lee(naive) is None  # marca sin zona horaria


def test_wifi_marca_de_tiempo_que_no_es_texto_invalida_la_captura() -> None:
    assert wifi._valid_timestamps([{"captured_at": "2026-10-04T00:00:00+00:00"}])
    assert not wifi._valid_timestamps([{"captured_at": 5}])


def test_wifi_comilla_sin_cerrar_y_envolturas_de_privilegio() -> None:
    assert wifi._tokens({"cmd": "echo 'sin cerrar"}) == []
    assert wifi._command_args({"cmd": "sudo -n -u root iw dev wlan0 link"}) == ["iw", "dev", "wlan0", "link"]
    assert wifi._command_args({"cmd": "doas -- ssh host"}) == ["ssh", "host"]


@pytest.mark.parametrize(
    ("cmd", "esperado"),
    [
        ("ssh -- host", "host"),
        ("ssh --", None),
        ("ssh -Z host", None),  # opcion corta desconocida
        ("ssh --opcion-larga host", None),
        ("ssh -4", None),  # sin destino
        ("ssh -V", None),
        ("ssh -p 22 host", "host"),
        ("ssh -4q host", "host"),
        ("ping host", None),
    ],
)
def test_wifi_ssh_target_en_cada_forma(cmd: str, esperado: str | None) -> None:
    assert wifi._ssh_target({"cmd": cmd}) == esperado


def test_wifi_sondas_de_loopback_y_sus_fallos_explicitos() -> None:
    assert wifi._loopback_probe(_w("true")) is False  # ni ping ni ssh
    assert wifi._explicit_loopback_failure(_w("ping -c 1 vecino", exit_code=1)) is False  # no es loopback
    assert wifi._explicit_loopback_failure(_w("ping -c 1 127.0.0.1", exit_code=1)) is True  # ping local sin respuesta
    assert wifi._explicit_loopback_failure(_w("ping -c 1 127.0.0.1", exit_code=2)) is False  # no corrio
    ssh_caido = _w("ssh localhost true", exit_code=255, stderr="Connection refused")
    assert wifi._explicit_loopback_failure(ssh_caido) is True
    assert wifi._explicit_loopback_failure(_w("ssh localhost true", exit_code=255, stderr="otra cosa")) is False


def test_wifi_conexion_por_nmcli_y_interfaz_iw_solo_con_exito() -> None:
    conectado = _w("nmcli device show wlp2s0", "GENERAL.STATE:                         100 (connected)\n")
    assert wifi._wifi_connected(conectado)
    assert not wifi._wifi_connected(_w("nmcli device show wlp2s0", "GENERAL.STATE: 30 (disconnected)\n"))
    assert wifi._iw_interface(_w("iw dev wlp2s0 link", "Connected to " + MAC_C + "")) == "wlp2s0"
    assert wifi._iw_interface(_w("iw dev wlp2s0 link", "", exit_code=1)) is None
    assert wifi._iw_interface(_w("ip dev wlp2s0 link", "")) is None


def _trial(ruta_extra: dict[int, Any] | None = None) -> list[Row]:
    """Una sola prueba de BSSID: modify, up con timeout, iw, ruta y acceso remoto (indices 0..4)."""
    rows = [
        _w("nmcli connection modify lab 802-11-wireless.bssid " + MAC_B + ""),
        _w("nmcli connection up lab --timeout 20", "activated", at=0),
        _w("iw dev wlp2s0 link", "Connected to " + MAC_B + "\nSSID: lab-net\nfreq: 5180\n"),
        _w("ip route show default", "default via 192.0.2.1 dev wlp2s0"),
        _w("ssh operator@management true", "reachable", at=30),
    ]
    for i, fila in (ruta_extra or {}).items():
        rows[i] = fila
    return rows


def _recupera(rows: list[Row]) -> bool | None:
    return wifi._recovered_trial(rows, 0, "802-11-wireless.bssid", "" + MAC_B + "", "lab-net")


def test_wifi_prueba_de_bssid_base_recupera() -> None:
    assert _recupera(_trial()) is True  # control


def test_wifi_prueba_sin_up_con_timeout_no_tiene_ventana() -> None:
    rows = _trial()
    del rows[1]
    assert wifi._trial_window(rows, 0) is None
    assert _recupera(rows) is None


def test_wifi_el_up_fallido_distingue_activacion_rechazada_de_error_ajeno() -> None:
    rechazado = _trial({1: _w("nmcli connection up lab --timeout 20", "", 4, "Error: Connection activation failed: x", at=0)})
    assert _recupera(rechazado) is False
    ajeno = _trial({1: _w("nmcli connection up lab --timeout 20", "", 4, "Error: otra cosa", at=0)})
    assert _recupera(ajeno) is None


def test_wifi_sin_enlace_conectado_distingue_desconectado_de_ausente() -> None:
    desconectado = _trial({2: _w("iw dev wlp2s0 link", "Not connected.\n")})
    assert wifi._trial_link(list(enumerate(desconectado[2:], 2))) == (None, "disconnected")
    assert _recupera(desconectado) is False
    nmcli_desconectado = _trial({2: _w("nmcli device show wlp2s0", "GENERAL.STATE: 30 (disconnected)\n")})
    assert _recupera(nmcli_desconectado) is False
    ausente = _trial()
    del ausente[2]
    assert wifi._trial_link(list(enumerate(ausente[2:], 2))) == (None, "missing")
    assert _recupera(ausente) is None
    assert wifi._trial_link([(7, _w("iw dev wlp2s0 link", "Connected to " + MAC_C + "\n"))]) == (7, "connected")


def test_wifi_interfaz_ilegible_remoto_ausente_o_caido_y_detalles_incompletos() -> None:
    mala_interfaz = _trial({2: _w("iw dev mala/interfaz link", "Connected to " + MAC_B + "\nSSID: lab-net\nfreq: 5180\n")})
    assert _recupera(mala_interfaz) is None

    sin_remoto = _trial()
    del sin_remoto[4]
    assert wifi._trial_remote_index(list(enumerate(sin_remoto[2:], 2))) == (None, "missing")
    assert _recupera(sin_remoto) is None

    remoto_caido = _trial({4: _w("ssh operator@management true", "", 255, "Connection timed out", at=30)})
    assert _recupera(remoto_caido) is False
    remoto_mudo = _trial({4: _w("ssh operator@management true", "", 1, "", at=30)})
    assert _recupera(remoto_mudo) is None  # fallo sin diagnostico nativo: no se afirma nada

    sin_detalles = _trial({2: _w("iw dev wlp2s0 link", "Connected to " + MAC_B + "\n")})
    assert _recupera(sin_detalles) is None


def test_wifi_temporizacion_de_la_recuperacion() -> None:
    sobre_tiempo = _trial({4: _w("ssh operator@management true", "reachable", at=61)})
    assert _recupera(sobre_tiempo) is False  # >60 s
    assert wifi._trial_timing_ok(_trial(), 1, 4) is True
    assert wifi._trial_timing_ok([_w("a"), _w("b", at=1)], 0, 1) is None  # sin marca
    assert wifi._trial_timing_ok([{**_w("a"), "captured_at": "no-es-fecha"}, _w("b", at=1)], 0, 1) is None
    ingenua = {**_w("a"), "captured_at": "2026-10-04T00:00:00"}
    assert wifi._trial_timing_ok([ingenua, _w("b", at=1)], 0, 1) is None  # sin zona horaria


def test_wifi_identidad_exige_el_driver_mt7925e_y_las_fuentes_se_verifican_por_hash() -> None:
    rows = _captura_wifi()["commands"]
    assert wifi._observed_identity(rows) == IDENTIDAD  # control
    otro_driver = [{**r, "stdout": r["stdout"].replace("mt7925e", "ath11k")} if r["cmd"].startswith("ethtool") else r for r in rows]
    assert wifi._observed_identity(otro_driver) is None

    texto = " ".join(IDENTIDAD) + " (pagina del fabricante con la identidad exacta del equipo bajo prueba)"
    buena = {"url": "https://www.nvidia.com/x", "text": texto, "sha256": hashlib.sha256(texto.encode()).hexdigest()}
    assert wifi._vendor_cites_identity([buena], IDENTIDAD) is True
    assert wifi._vendor_cites_identity(["no-es-dict", {"text": 5}, buena], IDENTIDAD) is True  # las ajenas se saltan
    assert wifi._vendor_cites_identity([{**buena, "sha256": "0" * 64}], IDENTIDAD) is False  # hash que no cuadra
    assert wifi._vendor_cites_identity([{**buena, "url": "https://ejemplo.com/x"}], IDENTIDAD) is False
    assert wifi._vendor_cites_identity([], IDENTIDAD) is False


def test_wifi_veredicto_de_pruebas_distingue_exito_falla_y_dato_ausente() -> None:
    ruta = Path("commands.json")
    prop = "802-11-wireless.band"
    assert wifi._trial_verdict([False, True], prop, ruta) is None
    unknown = wifi._trial_verdict([None], prop, ruta)
    assert unknown is not None and unknown["status"] == "unknown" and prop in unknown["reason"]
    fail = wifi._trial_verdict([False], prop, ruta)
    assert fail is not None and fail["status"] == "fail" and "within 60 seconds" in fail["reason"]
