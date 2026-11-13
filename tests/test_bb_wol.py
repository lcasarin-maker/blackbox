"""Pruebas de `tools/testigo/bb_wol.py` (archivo autonomo que se copia a la Dell). Se carga por ruta, como se usa copiado.

Cada afirmacion de «el paquete es valido» lleva al lado la de «una MAC invalida se rechaza»: un constructor que acepta todo no pasa.
"""
import importlib.util
import socket
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parents[1] / "tools" / "testigo" / "bb_wol.py"
spec = importlib.util.spec_from_file_location("bb_wol", RUTA)
wol = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wol)


def test_el_paquete_magico_tiene_la_forma_del_estandar():
    p = wol.paquete_magico("02-00-00-00-00-01")
    mac = bytes.fromhex("020000000001")
    assert len(p) == 102 and p[:6] == b"\xff" * 6 and p[6:] == mac * 16


def test_acepta_guiones_y_mayusculas_y_da_el_mismo_paquete():
    assert wol.paquete_magico("02-AB-00-00-00-01") == wol.paquete_magico("02-ab-00-00-00-01")


@pytest.mark.parametrize("mala", ["", "02-00-00-00-00", "02-00-00-00-00-01:00", "zz-00-00-00-00-01", "102-00-00-00-00-01"])
def test_rechaza_macs_invalidas(mala):
    with pytest.raises(ValueError):
        wol.paquete_magico(mala)  # control negativo: ninguna de estas llega a la red


def test_modo_seco_no_toca_la_red(monkeypatch, capsys):
    monkeypatch.setattr(socket, "socket", lambda *a, **k: (_ for _ in ()).throw(AssertionError("abrio un socket")))
    assert wol.main(["--seco", "--mac", "02-00-00-00-00-01", "--broadcast", "192.0.2.255"]) == 0
    assert "102 bytes" in capsys.readouterr().out


def test_una_mac_invalida_sale_con_2_y_no_envia(monkeypatch, capsys):
    monkeypatch.setattr(wol, "envia", lambda *a: (_ for _ in ()).throw(AssertionError("envio")))
    assert wol.main(["--mac", "mala", "--broadcast", "192.0.2.255"]) == 2
    assert "MAC invalida" in capsys.readouterr().err


def test_envia_en_broadcast_con_so_broadcast(monkeypatch):
    visto = {}

    class Falso:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def setsockopt(self, nivel, opcion, valor):
            visto["opt"] = (nivel, opcion, valor)

        def sendto(self, datos, destino):
            visto["envio"] = (len(datos), destino)

    monkeypatch.setattr(socket, "socket", lambda *a, **k: Falso())
    assert wol.main(["--mac", "02-00-00-00-00-01", "--broadcast", "192.0.2.255", "--puerto", "9"]) == 0
    assert visto["opt"] == (socket.SOL_SOCKET, socket.SO_BROADCAST, 1) and visto["envio"] == (102, ("192.0.2.255", 9))
