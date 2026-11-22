"""Caracterizacion del lazo de `bin/bb-usable` (DEBT-RUFF-BB-USABLE-01).

`main()` se partio en funciones para pasar C901/PLR0915. Este demonio reinicia la maquina (WatchdogSec=360,
FailureAction=reboot-immediate): un cambio de comportamiento silencioso es el peor fallo posible. Por eso la
secuencia ORDENADA de efectos -- cada `notify`, cada linea de `log`, cada declaracion de origen de COLAPSO y cada
paso del criterio confinado con su contador -- se grabo contra el `main()` SIN modificar (commit b71ef875) y queda
fijada en `fixtures/bb_usable_caracterizacion.json`. El refactor tiene que reproducirla byte a byte.

Se anulan solo las fuentes externas (sleep, sonda, PSI, latencia X, escalon, criterio confinado, origen); la
logica que decide si se acaricia el watchdog es la real. Regrabar: BB_USABLE_CARACTERIZA_GRABAR=1, y solo contra
un `main()` cuyo comportamiento se haya revisado a mano."""

from __future__ import annotations

import importlib.machinery as machinery
import importlib.util as util
import itertools
import json
import os
from pathlib import Path
from typing import Any

import pytest

RUTA = Path(__file__).resolve().parent.parent / "bin" / "bb-usable"
GOLDEN = Path(__file__).parent / "fixtures" / "bb_usable_caracterizacion.json"

ALTO, BAJO, PLAZO = 50.0, 0.5, 301.0
# Paso: (psi, segundos de la sonda, accion del criterio confinado si se le consulta)
Paso = tuple[float | None, float, str]
_corrida = itertools.count()


def _p(psi: float | None, took: float = 0.001, accion: str = "retiene") -> Paso:
    return (psi, took, accion)


ESCENARIOS: dict[str, list[Paso]] = {
    "bajo_el_umbral": [_p(BAJO)] * 3,
    "racha_hasta_colapso": [_p(ALTO)] * 11,
    "ilegible_en_mitad_de_racha": [_p(ALTO)] * 3 + [_p(None)] + [_p(ALTO)],
    "ilegible_con_colapso_declarado": [_p(ALTO)] * 10 + [_p(None)] + [_p(ALTO)],
    "ilegible_sin_racha": [_p(None), _p(BAJO)],
    "sonda_fuera_de_plazo": [_p(BAJO, PLAZO), _p(ALTO, PLAZO), _p(BAJO)],
    "confinado_acaricia": [_p(ALTO, accion="acaricia")] * 12,
    "confinado_habria_acariciado": [_p(ALTO, accion="habria_acariciado")] * 11,
    "recuperacion_tras_bajas": [_p(ALTO)] * 10 + [_p(BAJO)] * 3 + [_p(ALTO)],
    "una_baja_no_absuelve_colapso": [_p(ALTO)] * 10 + [_p(BAJO)] + [_p(ALTO)],
    "una_baja_no_absuelve_racha": [_p(ALTO)] * 3 + [_p(BAJO)] + [_p(ALTO), _p(BAJO), _p(ALTO)],
}


def _cargar():
    loader = machinery.SourceFileLoader("bb_usable_caracterizacion", str(RUTA))
    spec = util.spec_from_loader("bb_usable_caracterizacion", loader)
    assert spec is not None
    mod = util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class _Fin(Exception):
    pass


def correr(monkeypatch, pasos: list[Paso], tmp_path: Path) -> list[list[Any]]:
    """Corre el `main()` real sobre `pasos` y devuelve la lista ordenada de efectos."""
    tmp_path = tmp_path / f"run-{next(_corrida)}"
    tmp_path.mkdir()
    bbu = _cargar()
    datos = tmp_path / "datos"
    cgroup = tmp_path / "cgroup"
    proc = tmp_path / "proc"
    app = cgroup / "user.slice/user-77.slice/user@77.service/app.slice"
    unidad = app / "synthetic.scope"
    unidad.mkdir(parents=True)
    proc.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("BLACKBOX_DATA", str(datos))
    monkeypatch.setenv("TMPDIR", str(tmp_path / "tmp"))
    monkeypatch.setattr(bbu, "CGROUP_ROOT", cgroup)
    monkeypatch.setattr(bbu, "PROC_ROOT", proc)
    monkeypatch.setattr(bbu._MAPA, "lee_clases", lambda: ())
    eventos: list[list[Any]] = []
    i = -1  # paso en curso; -1 = antes del bucle

    def dormir(_s: float) -> None:
        nonlocal i
        i += 1
        if i >= len(pasos):
            raise _Fin

    def sonda() -> float:
        return 0.002 if i < 0 else pasos[i][1]

    def confinado(confinadas: int) -> tuple[str, int]:
        eventos.append(["confinado", confinadas])
        return pasos[i][2], confinadas + 1

    monkeypatch.setattr(bbu.time, "sleep", dormir)
    monkeypatch.setattr(bbu, "probe", sonda)
    monkeypatch.setattr(bbu, "psi_memory_full_avg10", lambda: pasos[i][0])
    monkeypatch.setattr(bbu, "notify", lambda s: eventos.append(["notify", s]))
    monkeypatch.setattr(bbu, "log", lambda m: eventos.append(["log", m]))
    monkeypatch.setattr(bbu, "latencia_x_ms", lambda: None)
    monkeypatch.setattr(bbu, "paso_escalon", lambda psi, est, ahora=None: (eventos.append(["escalon", psi]), est)[1])
    monkeypatch.setattr(bbu, "paso_confinado", confinado)
    monkeypatch.setattr(bbu, "origen_al_declarar_colapso", lambda s: eventos.append(["origen", s]))
    monkeypatch.setattr(bbu, "avisar_origen_no_cargado", lambda: eventos.append(["aviso_origen"]))
    monkeypatch.setattr(bbu, "protegidos_origen", lambda: "protegidos: fijo")
    with pytest.raises(_Fin):
        bbu.main()
    return eventos


def _caricias(eventos: list[list[Any]]) -> int:
    """Caricias del bucle, sin la de arranque."""
    return sum(1 for e in eventos if e == ["notify", "WATCHDOG=1"]) - 1


@pytest.mark.parametrize("nombre", sorted(ESCENARIOS))
def test_main_reproduce_la_secuencia_grabada(nombre, monkeypatch, tmp_path):
    eventos = correr(monkeypatch, ESCENARIOS[nombre], tmp_path)
    if os.environ.get("BB_USABLE_CARACTERIZA_GRABAR") == "1":
        datos = json.loads(GOLDEN.read_text(encoding="utf-8")) if GOLDEN.exists() else {}
        datos[nombre] = eventos
        GOLDEN.write_text(json.dumps(datos, indent=1, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    grabado = json.loads(GOLDEN.read_text(encoding="utf-8"))[nombre]
    assert eventos == grabado


# Lo que dice la secuencia grabada, en claro: si alguien la regraba con un comportamiento distinto, esto cae.

def test_semantica_bajo_el_umbral_acaricia_cada_sonda(monkeypatch, tmp_path):
    assert _caricias(correr(monkeypatch, ESCENARIOS["bajo_el_umbral"], tmp_path)) == 3


def test_semantica_colapso_deja_de_acariciar(monkeypatch, tmp_path):
    ev = correr(monkeypatch, ESCENARIOS["racha_hasta_colapso"], tmp_path)
    assert _caricias(ev) == 9
    assert ["origen", 10] in ev and ["origen", 11] in ev
    assert sum(1 for e in ev if e[0] == "log" and "COLAPSO:" in e[1]) == 2


def test_semantica_ilegible(monkeypatch, tmp_path):
    assert _caricias(correr(monkeypatch, ESCENARIOS["ilegible_sin_racha"], tmp_path)) == 2
    ev = correr(monkeypatch, ESCENARIOS["ilegible_en_mitad_de_racha"], tmp_path)
    assert _caricias(ev) == 5
    assert any(e[0] == "log" and "racha 4/10" in e[1] for e in ev), "la lectura perdida no absuelve"
    ev = correr(monkeypatch, ESCENARIOS["ilegible_con_colapso_declarado"], tmp_path)
    assert _caricias(ev) == 9


def test_semantica_fuera_de_plazo_no_acaricia(monkeypatch, tmp_path):
    assert _caricias(correr(monkeypatch, ESCENARIOS["sonda_fuera_de_plazo"], tmp_path)) == 1


def test_semantica_confinado(monkeypatch, tmp_path):
    assert _caricias(correr(monkeypatch, ESCENARIOS["confinado_acaricia"], tmp_path)) == 12
    assert _caricias(correr(monkeypatch, ESCENARIOS["confinado_habria_acariciado"], tmp_path)) == 9


def test_semantica_bajas(monkeypatch, tmp_path):
    # 9 de la racha + la segunda y tercera baja (la racha se corto) + la nueva racha 1/10
    assert _caricias(correr(monkeypatch, ESCENARIOS["recuperacion_tras_bajas"], tmp_path)) == 12
    assert _caricias(correr(monkeypatch, ESCENARIOS["una_baja_no_absuelve_colapso"], tmp_path)) == 9
    ev = correr(monkeypatch, ESCENARIOS["una_baja_no_absuelve_racha"], tmp_path)
    assert any(e[0] == "log" and "racha 5/10" in e[1] for e in ev)
