"""vigilante_memavail: lecturas, origen, detencion, lista de protegidos y bucle principal ejecutados de verdad.
DEBT-COBERTURA-PISO-REBAJADO-01. Los efectos son archivos en tmp_path, un `systemctl` real (script) en el PATH y /proc."""

from __future__ import annotations

import json
import os
import runpy
import stat
import time
from pathlib import Path
from typing import NoReturn

import pytest

from tools import vigilante_memavail as v


def test_lee_meminfo_extrae_memavailable_y_declara_ausencia(tmp_path: Path) -> None:
    ruta = tmp_path / "meminfo"
    ruta.write_text("MemTotal:  1000 kB\nMemAvailable:   123456 kB\n", encoding="utf-8")
    assert v.lee_meminfo(ruta) == 123456
    ruta.write_text("MemTotal:  1000 kB\n", encoding="utf-8")
    assert v.lee_meminfo(ruta) is None
    assert v.lee_meminfo(tmp_path / "no-existe") is None


def test_origen_de_lee_los_pids_del_cgroup_y_describe_el_proceso(tmp_path: Path) -> None:
    (tmp_path / "cgroup.procs").write_text(f"{os.getpid()}\n", encoding="ascii")
    r = v.origen_de(str(tmp_path))
    assert isinstance(r, list) and len(r) == 1
    assert r[0]["pid"] == os.getpid() and r[0]["comm"]


def test_origen_de_limita_a_ORIGEN_MAX_PIDS(tmp_path: Path) -> None:
    (tmp_path / "cgroup.procs").write_text("\n".join([str(os.getpid())] * (v.ORIGEN_MAX_PIDS + 3)), encoding="ascii")
    r = v.origen_de(str(tmp_path))
    assert isinstance(r, list) and len(r) == v.ORIGEN_MAX_PIDS


def test_origen_de_declara_cgroup_ilegible(tmp_path: Path) -> None:
    assert v.origen_de(str(tmp_path / "no-existe")) == "NOT_COLLECTED: cgroup.procs ilegible"
    (tmp_path / "cgroup.procs").write_text("no-es-un-pid\n", encoding="ascii")
    assert v.origen_de(str(tmp_path)) == "NOT_COLLECTED: cgroup.procs ilegible"


def _systemctl(bin_dir: Path, rc: int) -> None:
    ejecutable = bin_dir / "systemctl"
    ejecutable.write_text(f'#!/bin/sh\necho "args:$*"\necho "aviso" >&2\nexit {rc}\n', encoding="utf-8")
    ejecutable.chmod(ejecutable.stat().st_mode | stat.S_IXUSR)


def test_detiene_ejecuta_systemctl_user_stop_y_devuelve_rc_y_salida(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _systemctl(tmp_path, 3)
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")
    r = v.detiene("bb-lab-x.scope")
    assert r["rc"] == 3
    assert r["salida"].splitlines() == ["args:--user stop bb-lab-x.scope", "aviso"]


def test_detiene_declara_COULD_NOT_RUN_si_no_hay_systemctl(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))  # directorio vacio: ningun systemctl
    r = v.detiene("bb-lab-x.scope")
    assert r["rc"] is None and r["salida"].startswith("COULD_NOT_RUN: ")


def test_protegidos_comm_distingue_exactos_y_prefijos() -> None:
    p = v._construye((("dockerd", False, None), ("gnome-", True, None)), (), None)
    assert p.comm("dockerd") and not p.comm("dockerd2")  # exacto: no casa por prefijo
    assert p.comm("gnome-shell") and not p.comm("xgnome-shell")  # prefijo: solo al inicio
    assert not p.comm("bash")


def test_cargar_protegidos_lee_un_fichero_valido_sin_error(tmp_path: Path) -> None:
    ruta = tmp_path / "p.json"
    ruta.write_text(json.dumps({"comm": [{"nombre": "dockerd", "prefijo": False}], "unidades": [{"patron": "^docker"}]}), encoding="utf-8")
    p = v.cargar_protegidos(ruta)
    assert p.error is None and p.comm("dockerd") and p.unidades.search("docker.service")


@pytest.mark.parametrize(
    ("contenido", "error_esperado"),
    [
        ("{ no es json", "JSONDecodeError"),
        (json.dumps({"comm": [], "unidades": []}), "ValueError: lista vacia o entrada mal formada"),
        (json.dumps({"comm": [{"nombre": "x", "prefijo": "si"}], "unidades": []}), "ValueError: lista vacia o entrada mal formada"),
    ],
)
def test_cargar_protegidos_con_fichero_roto_usa_el_respaldo_y_dice_por_que(tmp_path: Path, caplog: pytest.LogCaptureFixture, contenido: str, error_esperado: str) -> None:
    ruta = tmp_path / "p.json"
    ruta.write_text(contenido, encoding="utf-8")
    p = v.cargar_protegidos(ruta)
    assert p.error is not None and p.error.startswith(error_esperado)
    assert p.exactos == frozenset(n for n, pref, _ in v.RESPALDO_COMM if not pref)  # es la copia de respaldo
    assert "se usa la copia de respaldo" in caplog.text
    assert v.cargar_protegidos(tmp_path / "no-existe").error is not None  # fichero ausente: tambien respaldo


class _Alto(Exception):
    """Corta el bucle `while True` tras la primera vuelta."""


def _duerme_una_vez(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    pausas: list[float] = []

    def duerme(s: float) -> NoReturn:
        pausas.append(s)
        raise _Alto

    monkeypatch.setattr(time, "sleep", duerme)
    return pausas


def test_una_vuelta_con_modo_off_no_decide_y_con_observar_registra_el_disparo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    assert v.una_vuelta() is None  # sin interruptores.json el modo es off
    (tmp_path / "interruptores.json").write_text(json.dumps({"modos": {v.NOMBRE: "observar"}}), encoding="utf-8")
    assert v.una_vuelta(linea_gib=1e12, elegibles=("zzz-ninguna-unidad-casa",)) is not None  # MemAvailable real < 1e12 GiB: siempre dispara
    filas = [json.loads(x) for x in (tmp_path / "interruptores" / f"{v.NOMBRE}.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(filas) == 1 and filas[0]["modo"] == "observar" and filas[0]["dispara"] is True and filas[0]["culpable"]["veredicto"] == "NOT_COLLECTED"
    assert v.una_vuelta(linea_gib=0.0, elegibles=("zzz-ninguna-unidad-casa",)) is None  # linea 0: nunca dispara


def test_el_modulo_como_script_hace_una_vuelta_y_duerme_1s(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ejecuta el modulo como `__main__`: la guarda llama a main(), que vuelve una vez y duerme 1 s."""
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    pausas = _duerme_una_vez(monkeypatch)
    with pytest.warns(RuntimeWarning, match="found in sys.modules"), pytest.raises(_Alto):
        runpy.run_module("tools.vigilante_memavail", run_name="__main__")
    assert pausas == [1]
    assert not (tmp_path / "interruptores").exists()  # modo off: la vuelta no escribe
