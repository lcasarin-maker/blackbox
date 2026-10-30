"""Mapa de memoria por unidad duena al ACTUAR una guardia (FEATURE-MAPA-DE-MEMORIA-FORENSE-AL-ACTUAR-01).

Tres guardias, una funcion (`tools/mapa_memoria.captura`): el escalon de `bin/bb-usable` al matar,
`tools/vigilante_memavail.py` en cada fila que registra (observar y actuar) y `tools/portero.py` al congelar o al
negar. Todo sobre arboles cgroup falsos en tmp: ninguna prueba toca una unidad real ni manda una senal.

(a) cada accion deja el mapa con sus campos; (b) control negativo: sin accion no hay mapa; (c) lo ilegible es
NOT_COLLECTED, nunca 0 (y un 0 medido sigue siendo 0); (d) una excepcion del mapa no cambia la decision ni la accion;
(e) tope por fila; (f) control del control: el codigo de antes (sacado de git) NO deja el mapa, asi (a) puede salir rojo.
"""

from __future__ import annotations

import importlib.machinery as machinery
import importlib.util as util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tools import mapa_memoria as mm
from tools import portero as po
from tools import vigilante_memavail as v

RAIZ = Path(__file__).resolve().parent.parent
GIB = 1 << 30
G = po.GIB_KB
UID = os.getuid()
APP_REL = f"user.slice/user-{UID}.slice/user@{UID}.service/app.slice"
# Ultimo commit sin el mapa (master antes de esta ficha): las tres guardias tal como estaban.
COMMIT_VIEJO = "fe42e66670107f3f13d5cd447438af0ea41e907a"
CAMPOS = ("unidad", "cgroup", "clase", "rango", "memory.current", "anon", "file", "shmem", "memory.swap.current",
          "gpu_dmem")
STAT = "anon 100\nfile 200\nkernel 9\nshmem 30\n"


def _cg(d: Path, current: int | None, stat: str | None = STAT, swap: int | None = 40, dmem: str | None = None) -> Path:
    d.mkdir(parents=True, exist_ok=True)
    for nombre, valor in (("memory.current", current), ("memory.stat", stat), ("memory.swap.current", swap),
                          ("dmem.current", dmem)):
        if valor is not None:
            (d / nombre).write_text(f"{valor}\n" if isinstance(valor, int) else valor, encoding="ascii")
    return d


def _filas(ruta: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in ruta.read_text(encoding="utf-8").splitlines()] if ruta.exists() else []


def faltas(fila: dict[str, Any] | None, unidad: str, esperado: dict[str, Any]) -> list[str]:
    """Lo que le falta a la fila de una accion para cumplir (a). Lista vacia = cumple."""
    if fila is None:
        return ["la guardia no escribio fila"]
    m = fila.get("mapa_memoria")
    if not isinstance(m, dict):
        return ["la fila no lleva mapa_memoria"]
    if m.get("esquema") != mm.ESQUEMA or not isinstance(m.get("unidades"), list):
        return [f"mapa sin esquema o sin unidades: {m}"]
    out = [f"{u.get('unidad')}: falta {c}" for u in m["unidades"] for c in CAMPOS if c not in u]
    por_nombre = {u["unidad"]: u for u in m["unidades"]}
    if unidad not in por_nombre:
        return [*out, f"{unidad} no esta en el mapa"]
    out += [f"{unidad}.{k}={por_nombre[unidad].get(k)!r}, se esperaba {val!r}"
            for k, val in esperado.items() if por_nombre[unidad].get(k) != val]
    return out


ESPERADO_LAB = {"memory.current": 3 * GIB, "anon": 100, "file": 200, "shmem": 30, "memory.swap.current": 40,
                "gpu_dmem": {"drm": 50}, "clase": "laboratorio", "rango": 0}
ESPERADO_SUITE = {"memory.current": 6 * GIB, "anon": 100, "file": 200, "shmem": 30, "memory.swap.current": 40,
                  "clase": "suites", "rango": 1}
ESPERADO_CLAUDE = {"memory.current": 30 * GIB, "anon": 100, "file": 200, "shmem": 30, "memory.swap.current": 40,
                   "clase": "sesion", "rango": 3}


# ------------------------------------------------------------------ escenarios (cada guardia, codigo nuevo o viejo)


def escenario_memavail(mod: Any, tmp: Path, modo: str = "actuar", mem_kb: int = 1 * 1048576,
                       stat_lab: str | None = STAT) -> tuple[dict[str, Any] | None, list[str], Path]:
    raiz = tmp / "user@1000.service" / "app.slice"
    lab = _cg(raiz / "bb-lab-acaparador-1.scope", 3 * GIB, stat=stat_lab, dmem="drm 50\n")
    otra = _cg(raiz / "app-firefox-9.scope", 5 * GIB)
    unidades = [mod.Unidad(lab.name, str(lab), 3 * GIB), mod.Unidad(otra.name, str(otra), 5 * GIB)]
    detenidas: list[str] = []
    ctx = mod.Contexto(mod.LINEA_GIB, mod.ELEGIBLES, lambda: unidades, lambda cg: [{"pid": 7}],
                       lambda n: (detenidas.append(n), {"rc": 0, "salida": ""})[1])
    reg = tmp / "reg"
    mod.paso(modo, mem_kb, 0.0, reg, ctx)
    filas = _filas(reg / "memavail.jsonl")
    return (filas[-1] if filas else None), detenidas, reg


def _arbol_portero(mod: Any) -> Any:
    return mod.Arbol(raiz=77, clase="suite", rss_kb=5 * G, procesos=3, edad_s=60.0,
                     cgroup=f"/{APP_REL}/app-com.anthropic.Claude-1.scope")


def escenario_portero(mod: Any, tmp: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, Any], list[int]]:
    """Congelar ejecutado (la adopcion por systemd se sustituye: devuelve rc 0 y la unidad creada)."""
    app = tmp / "cg" / APP_REL
    _cg(app / "bb-portero-suite-77.scope", 6 * GIB)
    _cg(app / "app-com.anthropic.Claude-1.scope", 9 * GIB)
    llamadas: list[int] = []

    def adopta(a: Any, ac: Any, fx: Any) -> dict[str, Any]:
        llamadas.append(a.raiz)
        return {"rc": 0, "salida": "", "unidad": "bb-portero-suite-77.scope", "slice": ac.slice, "topes": ac.topes}

    monkeypatch.setattr(mod, "_adopta_y_congela", adopta)
    fx = mod.Efectos(log=tmp / "portero.jsonl", cola=tmp / "cola", ejecutar=_prohibido, cg_raiz=tmp / "cg",
                     proc=tmp / "proc", modo="actuar")
    mod.aplica([mod.Accion("congelar", "turno ocupado", 77, "suite")], [_arbol_portero(mod)],
               mod.Estado(0.0, "", 42 * G, 30 * G), fx, {})
    return _filas(fx.log)[-1], llamadas


def escenario_portero_niega(mod: Any, tmp: Path) -> list[dict[str, Any]]:
    """`portero_admision` en observar: la suite no cabe en lo que app.slice tiene fuera de anon+shmem."""
    app = tmp / "cg" / APP_REL
    _cg(app / "app-com.anthropic.Claude-1.scope", 9 * GIB)
    estado = mod.Estado(0.97, "", 44040192, 35743284, (), 4965588, admision="observar", no_recuperable_app_kb=27267340)
    arbol = _arbol_portero(mod)
    acciones = mod.decide([arbol], estado)
    fx = mod.Efectos(log=tmp / "portero.jsonl", cola=tmp / "cola", ejecutar=_prohibido, cg_raiz=tmp / "cg",
                     proc=tmp / "proc", modo="actuar")
    mod.aplica(acciones, [], estado, fx, {})
    return _filas(fx.log)


def _prohibido(args: list[str]) -> tuple[int, str]:
    raise AssertionError(f"no debe ejecutar nada: {args}")


def _cargar_bbu(ruta: Path) -> Any:
    loader = machinery.SourceFileLoader(f"bb_usable_mapa_{abs(hash(str(ruta)))}", str(ruta))
    spec = util.spec_from_loader(loader.name, loader)
    assert spec is not None
    mod = util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def escenario_bbu(bbu: Any, tmp: Path, monkeypatch: pytest.MonkeyPatch, psi: float = 50.0
                  ) -> tuple[dict[str, Any], list[tuple[int, bool]], Any]:
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp / "datos"))
    app = tmp / "cg" / APP_REL
    scope = _cg(app / "app-com.anthropic.Claude-1.scope", 30 * GIB)
    _cg(app / "app-gnome-org.gnome.Terminal-2.scope", 1 * GIB)
    obj = bbu.Proc(20, 20, "python3", UID, 26 * 1048576, 123, scope.name, str(app))
    monkeypatch.setattr(bbu, "CGROUP_ROOT", tmp / "cg")
    monkeypatch.setattr(bbu, "leer_slices_app", lambda: (bbu.SliceApp(str(app), 95, 100),))
    monkeypatch.setattr(bbu, "leer_candidatos", lambda s: (obj,))
    monkeypatch.setattr(bbu, "capturar_origen", lambda motivo, pids: {"ts": "T", "procesos": []})
    monkeypatch.setattr(bbu, "leer_grupo", lambda pgid: (obj,))
    muertes: list[tuple[int, bool]] = []
    monkeypatch.setattr(bbu, "ejecutar_muerte", lambda o, g: muertes.append((o.pid, g)) or "SIGKILL")
    monkeypatch.setattr(bbu, "log", lambda m: None)
    estado = bbu.paso_escalon(psi, bbu.EstadoEscalon(alto_desde=0.0), ahora=100.0)
    (f,) = (tmp / "datos" / "escalon").glob("*.jsonl")
    return _filas(f)[-1], muertes, estado


@pytest.fixture
def bbu() -> Any:
    return _cargar_bbu(RAIZ / "bin" / "bb-usable")


# ------------------------------------------------------------------ (a) la accion deja el mapa con sus campos


def test_a_memavail_al_detener_deja_el_mapa_en_su_fila(tmp_path):
    fila, detenidas, _ = escenario_memavail(v, tmp_path)
    assert detenidas == ["bb-lab-acaparador-1.scope"]
    assert fila is not None and fila["accion"]["detenida"] == "bb-lab-acaparador-1.scope"
    assert faltas(fila, "bb-lab-acaparador-1.scope", ESPERADO_LAB) == []
    assert {u["unidad"] for u in fila["mapa_memoria"]["unidades"]} == {"bb-lab-acaparador-1.scope", "app-firefox-9.scope"}


def test_a_memavail_en_observar_deja_el_mapa_y_no_detiene(tmp_path):
    fila, detenidas, _ = escenario_memavail(v, tmp_path, modo="observar")
    assert detenidas == [] and fila is not None and "accion" not in fila
    assert faltas(fila, "bb-lab-acaparador-1.scope", ESPERADO_LAB) == []


def test_a_portero_al_congelar_deja_el_mapa_con_la_unidad_congelada(tmp_path, monkeypatch):
    fila, llamadas = escenario_portero(po, tmp_path, monkeypatch)
    assert llamadas == [77] and (fila["accion"], fila["rc"]) == ("congelar", 0)
    assert faltas(fila, "bb-portero-suite-77.scope", ESPERADO_SUITE) == []


def test_a_portero_al_negar_en_observar_deja_el_mapa(tmp_path):
    filas = escenario_portero_niega(po, tmp_path)
    neg = [f for f in filas if f["accion"] == "habria_negado"]
    assert len(neg) == 1 and neg[0]["necesario_kb"] == po.CLASES["suite"].memory_max_kb
    assert faltas(neg[0], "app-com.anthropic.Claude-1.scope", {"memory.current": 9 * GIB, "clase": "sesion"}) == []


def test_a_bb_usable_al_matar_deja_el_mapa_con_el_scope_del_objetivo(bbu, tmp_path, monkeypatch):
    evento, muertes, _ = escenario_bbu(bbu, tmp_path, monkeypatch)
    assert muertes == [(20, True)] and evento["efecto"] == "SIGKILL"
    assert faltas(evento, "app-com.anthropic.Claude-1.scope", ESPERADO_CLAUDE) == []
    assert mm.NOT_COLLECTED == evento["mapa_memoria"]["unidades"][0]["gpu_dmem"]  # sin dmem.current: no un cero


# ------------------------------------------------------------------ (b) control negativo: sin accion no hay mapa


def test_b_memavail_sin_disparo_no_escribe_nada(tmp_path):
    fila, detenidas, reg = escenario_memavail(v, tmp_path, mem_kb=100 * 1048576)  # 100 GiB libres: no dispara
    assert fila is None and detenidas == [] and not (reg / "memavail.jsonl").exists()
    fila, _, _ = escenario_memavail(v, tmp_path / "off", modo="off")
    assert fila is None


def test_b_portero_sin_congelar_ni_negar_no_lleva_mapa(tmp_path, monkeypatch):
    monkeypatch.setattr(po, "_adopta_y_congela", lambda a, ac, fx: {"rc": 0, "salida": "", "unidad": "u.scope"})
    fx = po.Efectos(log=tmp_path / "portero.jsonl", cola=tmp_path / "cola", ejecutar=_prohibido,
                    cg_raiz=tmp_path / "cg", proc=tmp_path / "proc", modo="actuar")
    a = _arbol_portero(po)
    po.aplica([po.Accion("admitir", "hay turno", 77, "suite"), po.Accion("esperar", "x", None)], [a],
              po.Estado(0.0, "", 42 * G, 30 * G), fx, {})
    # observar: `habria_congelar` no es una congelacion
    fx_obs = po.Efectos(log=tmp_path / "obs.jsonl", cola=tmp_path / "cola", ejecutar=_prohibido,
                        cg_raiz=tmp_path / "cg", proc=tmp_path / "proc", modo="observar")
    po.aplica([po.Accion("congelar", "turno ocupado", 77, "suite")], [a], po.Estado(0.0, "", 42 * G, 30 * G), fx_obs, {})
    filas = _filas(fx.log) + _filas(fx_obs.log)
    assert [f["accion"] for f in filas] == ["admitir", "esperar", "habria_congelar"]
    assert all("mapa_memoria" not in f for f in filas)


def test_b_portero_negativa_sin_medicion_no_es_accion_y_no_lleva_mapa(tmp_path):
    estado = po.Estado(0.97, "", None, None, (), 0, admision="observar", no_recuperable_app_kb=None)
    fx = po.Efectos(log=tmp_path / "portero.jsonl", cola=tmp_path / "cola", ejecutar=_prohibido,
                    cg_raiz=tmp_path / "cg", proc=tmp_path / "proc", modo="actuar")
    po.aplica([po.Accion("admitir", "x", 77, "suite")], [], estado, fx, {})
    neg = [f for f in _filas(fx.log) if f["accion"] == "habria_negado"]
    assert len(neg) == 1 and neg[0]["motivo"].startswith("NOT_COLLECTED") and "mapa_memoria" not in neg[0]


def test_b_bb_usable_sin_muerte_no_lleva_mapa(bbu, tmp_path, monkeypatch):
    evento, muertes, _ = escenario_bbu(bbu, tmp_path, monkeypatch, psi=3.0)  # PSI bajo: no actua
    assert muertes == [] and evento["accion"] == "nada" and "mapa_memoria" not in evento


def test_b_bb_usable_con_condicion_pero_solo_protegidos_no_lleva_mapa(bbu, tmp_path, monkeypatch):
    protegido = bbu.Proc(21, 21, "claude", UID, 30 * 1048576, 1, "app-com.anthropic.Claude-1.scope", "x")
    monkeypatch.setattr(bbu, "leer_slices_app", lambda: (bbu.SliceApp("x", 95, 100),))
    monkeypatch.setattr(bbu, "leer_candidatos", lambda s: (protegido,))
    monkeypatch.setattr(bbu, "capturar_origen", lambda motivo, pids: {"ts": "T", "procesos": []})
    monkeypatch.setattr(bbu, "ejecutar_muerte", lambda o, g: pytest.fail("no debe matar"))
    monkeypatch.setattr(bbu, "log", lambda m: None)
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path / "datos"))
    bbu.paso_escalon(50.0, bbu.EstadoEscalon(alto_desde=0.0), ahora=100.0)
    (f,) = (tmp_path / "datos" / "escalon").glob("*.jsonl")
    (evento,) = _filas(f)
    assert evento["condicion"] is True and evento["accion"] == "nada" and "mapa_memoria" not in evento


# ------------------------------------------------------------------ (c) ilegible es NOT_COLLECTED, nunca 0


def test_c_memory_stat_ilegible_es_not_collected_campo_a_campo(tmp_path):
    sin_stat = _cg(tmp_path / "sin-stat.scope", 5, stat=None, swap=None)
    stat_dir = _cg(tmp_path / "stat-dir.scope", 4, stat=None)
    (stat_dir / "memory.stat").mkdir()  # leerlo da IsADirectoryError
    parcial = _cg(tmp_path / "parcial.scope", 3, stat="anon 7\n")
    vacio_dmem = _cg(tmp_path / "dmem-vacio.scope", 2, dmem="")
    sin_current = _cg(tmp_path / "sin-current.scope", None)
    m = mm.captura([sin_stat, stat_dir, parcial, vacio_dmem, sin_current])
    u = {x["unidad"]: x for x in m["unidades"]}
    for nombre in ("sin-stat.scope", "stat-dir.scope"):
        assert [u[nombre][k] for k in ("anon", "file", "shmem")] == [mm.NOT_COLLECTED] * 3
    assert u["sin-stat.scope"]["memory.swap.current"] == mm.NOT_COLLECTED
    assert (u["parcial.scope"]["anon"], u["parcial.scope"]["file"], u["parcial.scope"]["shmem"]) == (
        7, mm.NOT_COLLECTED, mm.NOT_COLLECTED)
    assert u["dmem-vacio.scope"]["gpu_dmem"] == mm.SIN_REGION and u["sin-stat.scope"]["gpu_dmem"] == mm.NOT_COLLECTED
    assert u["sin-current.scope"]["memory.current"] == mm.NOT_COLLECTED
    assert m["unidades"][-1]["unidad"] == "sin-current.scope"  # lo ilegible va al final, no como si fuera 0
    ceros = [(x["unidad"], k) for x in m["unidades"] for k in CAMPOS if x[k] == 0]
    assert ceros == [], "ningun campo ilegible puede salir como cero"


def test_c_control_un_cero_medido_sigue_siendo_cero(tmp_path):
    """El instrumento SI puede decir 0 cuando el kernel lo dice: NOT_COLLECTED no es un valor por defecto."""
    u = mm.captura([_cg(tmp_path / "cero.scope", 0, stat="anon 0\nfile 0\nshmem 0\n", swap=0, dmem="drm 0\n")])
    (x,) = u["unidades"]
    assert [x[k] for k in ("memory.current", "anon", "file", "shmem", "memory.swap.current")] == [0] * 5
    assert x["gpu_dmem"] == {"drm": 0}


def test_c_memavail_con_memory_stat_ilegible_lo_dice_en_su_fila(tmp_path):
    (tmp_path / "user@1000.service" / "app.slice" / "bb-lab-acaparador-1.scope").mkdir(parents=True)
    (tmp_path / "user@1000.service" / "app.slice" / "bb-lab-acaparador-1.scope" / "memory.stat").mkdir()
    fila, detenidas, _ = escenario_memavail(v, tmp_path, stat_lab=None)
    assert detenidas == ["bb-lab-acaparador-1.scope"]
    assert faltas(fila, "bb-lab-acaparador-1.scope", {"anon": mm.NOT_COLLECTED, "file": mm.NOT_COLLECTED,
                                                       "shmem": mm.NOT_COLLECTED, "memory.current": 3 * GIB}) == []


def test_c_lista_de_unidades_ilegible_es_not_collected_no_un_mapa_vacio(tmp_path):
    assert mm.captura(None)["estado"] == mm.NOT_COLLECTED
    assert mm.unidades_de(tmp_path / "no-existe") is None
    m = mm.captura([tmp_path / "x.scope"], clases=None)
    assert (m["unidades"][0]["clase"], m["unidades"][0]["rango"]) == (mm.NOT_COLLECTED, mm.NOT_COLLECTED)


# ------------------------------------------------------------------ (d) una excepcion del mapa no cambia nada


def _revienta(*_a: Any, **_k: Any) -> Any:
    raise RuntimeError("mapa roto a proposito")


def test_d_memavail_con_el_mapa_roto_decide_y_detiene_igual(tmp_path, monkeypatch):
    # el mismo arbol en las dos corridas: las rutas de cgroup van en el evento
    bien, det_bien, _ = escenario_memavail(v, tmp_path)
    monkeypatch.setattr(v.mapa_memoria, "captura", _revienta)
    mal, det_mal, _ = escenario_memavail(v, tmp_path)
    assert det_bien == det_mal == ["bb-lab-acaparador-1.scope"] and bien is not None and mal is not None
    quita = ("ts", "mapa_memoria")
    assert {k: x for k, x in bien.items() if k not in quita} == {k: x for k, x in mal.items() if k not in quita}
    assert mal["mapa_memoria"]["estado"] == mm.NOT_COLLECTED and "RuntimeError" in mal["mapa_memoria"]["motivo"]


def test_d_captura_nunca_lanza_aunque_reviente_por_dentro(tmp_path, monkeypatch):
    monkeypatch.setattr(mm, "_unidad", _revienta)
    m = mm.captura([_cg(tmp_path / "a.scope", 1)])
    assert m["estado"] == mm.NOT_COLLECTED and "mapa roto" in m["motivo"]


def test_d_portero_con_el_mapa_roto_congela_igual(tmp_path, monkeypatch):
    bien, ll_bien = escenario_portero(po, tmp_path, monkeypatch)
    monkeypatch.setattr(po.mapa_memoria, "captura", _revienta)
    mal, ll_mal = escenario_portero(po, tmp_path, monkeypatch)
    assert ll_bien == ll_mal == [77]
    quita = ("ts", "mapa_memoria")
    assert {k: x for k, x in bien.items() if k not in quita} == {k: x for k, x in mal.items() if k not in quita}
    assert mal["mapa_memoria"]["estado"] == mm.NOT_COLLECTED


class _MapaRoto:
    captura = staticmethod(_revienta)
    unidades_de = staticmethod(_revienta)
    lee_clases = staticmethod(_revienta)


@pytest.mark.parametrize("modulo", [_MapaRoto, None], ids=["revienta", "no_cargado"])
def test_d_bb_usable_con_el_mapa_roto_mata_igual_y_guarda_el_enfriamiento(bbu, tmp_path, monkeypatch, modulo):
    bien, m_bien, e_bien = escenario_bbu(bbu, tmp_path, monkeypatch)
    monkeypatch.setattr(bbu, "_MAPA", modulo)
    mal, m_mal, e_mal = escenario_bbu(bbu, tmp_path, monkeypatch)
    assert m_bien == m_mal == [(20, True)] and e_bien == e_mal and e_mal.ultima_muerte == 100.0
    quita = ("ts", "mapa_memoria")
    assert {k: x for k, x in bien.items() if k not in quita} == {k: x for k, x in mal.items() if k not in quita}
    assert mal["mapa_memoria"]["estado"] == mm.NOT_COLLECTED and mal["efecto"] == "SIGKILL"


# ------------------------------------------------------------------ (e) tope de tamano por fila


def test_e_tope_las_mayores_mas_la_obligatoria_y_el_resto_contado(tmp_path):
    rutas = [_cg(tmp_path / f"u{i:02d}.scope", (i + 1) * 1000) for i in range(25)]  # u24 la mayor, u00 la menor
    m = mm.captura(rutas, obligatorias=[rutas[0]])
    nombres = [u["unidad"] for u in m["unidades"]]
    assert len(nombres) == mm.TOPE_UNIDADES + 1 == 11
    assert nombres[:10] == [f"u{i:02d}.scope" for i in range(24, 14, -1)] and nombres[10] == "u00.scope"
    assert (m["vistas"], m["omitidas"], m["omitidas_ilegibles"]) == (25, 14, 0)
    assert m["omitidas_bytes_legibles"] == sum((i + 1) * 1000 for i in range(1, 15))
    # control: sin tope efectivo entran todas; el que corta es el tope, no la lectura
    assert len(mm.captura(rutas, tope=100)["unidades"]) == 25


def test_e_tope_se_respeta_en_la_fila_del_portero(tmp_path, monkeypatch):
    app = tmp_path / "cg" / APP_REL
    for i in range(30):
        _cg(app / f"app-relleno-{i}.scope", (i + 1) * GIB)
    fila, _ = escenario_portero(po, tmp_path, monkeypatch)
    m = fila["mapa_memoria"]
    assert len(m["unidades"]) <= mm.TOPE_UNIDADES + 1 and m["vistas"] == 32 and m["omitidas"] == 32 - 11
    assert "bb-portero-suite-77.scope" in {u["unidad"] for u in m["unidades"]}  # la congelada, aunque no sea mayor


# ------------------------------------------------------------------ coherencia del rango con el arbitro


@pytest.mark.parametrize("nombre", ["bb-lab-x.scope", "bb-portero-suite-1.scope", "app-firefox-1.scope",
                                    "session-2.scope", "docker-abc.scope", "vllm.service", "dbus.service",
                                    "BB-LAB-MAYUS.SCOPE"])
def test_el_rango_del_mapa_es_el_del_arbitro(nombre):
    clase, rango = mm.clase_de(nombre, mm.lee_clases())
    assert rango == v.RANGOS.rango(nombre)
    assert mm.lee_clases() == v.RANGOS.clases  # el mismo fichero, leido por los dos


# ------------------------------------------------------------------ (f) control del control: el codigo viejo no deja mapa


def _viejo(tmp: Path, ruta: str) -> Path:
    fuente = subprocess.run(["git", "-C", str(RAIZ), "show", f"{COMMIT_VIEJO}:{ruta}"],
                            capture_output=True, text=True, timeout=30, check=True).stdout
    assert "mapa_memoria" not in fuente  # de verdad es el codigo de antes
    destino = tmp / "viejo" / ruta
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(fuente, encoding="utf-8")
    return destino


def _carga_py(ruta: Path, nombre: str, monkeypatch: pytest.MonkeyPatch) -> Any:
    spec = util.spec_from_file_location(nombre, ruta)
    assert spec is not None and spec.loader is not None
    mod = util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, nombre, mod)  # @dataclass busca su modulo en sys.modules
    spec.loader.exec_module(mod)
    return mod


def test_f_control_del_control_el_codigo_viejo_no_deja_mapa(tmp_path, monkeypatch):
    (tmp_path / "viejo" / "data").mkdir(parents=True)
    for f in ("procesos_protegidos.json", "rangos_memoria.json"):
        shutil.copy2(RAIZ / "data" / f, tmp_path / "viejo" / "data" / f)
    (tmp_path / "viejo" / "tools").mkdir()
    shutil.copy2(RAIZ / "tools" / "origen_proceso.py", tmp_path / "viejo" / "tools" / "origen_proceso.py")

    v_viejo = _carga_py(_viejo(tmp_path, "tools/vigilante_memavail.py"), "vigilante_memavail_viejo_mapa", monkeypatch)
    fila, detenidas, _ = escenario_memavail(v_viejo, tmp_path / "mv")
    assert detenidas == ["bb-lab-acaparador-1.scope"]  # el viejo actua igual...
    assert faltas(fila, "bb-lab-acaparador-1.scope", ESPERADO_LAB) == ["la fila no lleva mapa_memoria"]  # ...sin mapa

    po_viejo = _carga_py(_viejo(tmp_path, "tools/portero.py"), "portero_viejo_mapa", monkeypatch)
    fila, llamadas = escenario_portero(po_viejo, tmp_path / "po", monkeypatch)
    assert llamadas == [77]
    assert faltas(fila, "bb-portero-suite-77.scope", ESPERADO_SUITE) == ["la fila no lleva mapa_memoria"]
    neg = [f for f in escenario_portero_niega(po_viejo, tmp_path / "pn") if f["accion"] == "habria_negado"]
    assert len(neg) == 1 and faltas(neg[0], "app-com.anthropic.Claude-1.scope", {}) == ["la fila no lleva mapa_memoria"]

    bbu_viejo = _cargar_bbu(_viejo(tmp_path, "bin/bb-usable"))
    evento, muertes, _ = escenario_bbu(bbu_viejo, tmp_path / "bb", monkeypatch)
    assert muertes == [(20, True)]
    assert faltas(evento, "app-com.anthropic.Claude-1.scope", ESPERADO_CLAUDE) == ["la fila no lleva mapa_memoria"]
