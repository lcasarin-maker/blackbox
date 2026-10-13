"""Portero, partes con efecto: /proc falso en disco, colas reales, subprocess reales y el CLI de punta a punta.

Cada prueba afirma un efecto observable (fila del log, archivo, codigo de salida, accion devuelta) y las que deciden
un veredicto llevan su control negativo (la misma entrada con un campo roto da el veredicto contrario).
Lo unico que se sustituye son colaboradores de la funcion bajo prueba: rutas globales (`LOG`, `COLA`, `CGROUP_RAIZ`),
el uid (para que /proc y el cgroup de `app.slice` queden fuera y la medicion sea NOT_COLLECTED, determinista),
`Efectos` (log y `ejecutar` desechables) y un `systemd-run` de mentira en el PATH que ejecuta el comando tal cual.
Nada toca cgroups, systemd ni docker reales.
"""

from __future__ import annotations

import argparse
import threading
import json
import os
import runpy
import stat
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from tools import portero as po

G = po.GIB_KB
APP = "/user.slice/user-1000.slice/user@1000.service/app.slice"
CLAUDE = APP + "/app-com.anthropic.Claude-1.scope"
HZ = os.sysconf("SC_CLK_TCK")
PID_INEXISTENTE = 2**31 - 5


def estado(psi: float | None = 0.0, tope: int | None = 42 * G, uso: int | None = 30 * G) -> po.Estado:
    return po.Estado(psi, "", tope, uso)


def arbol(raiz: int, edad: float, **kw: Any) -> po.Arbol:
    return po.Arbol(raiz=raiz, clase="suite", rss_kb=10 * G, procesos=5, edad_s=edad, cgroup=CLAUDE, **kw)


def filas(log: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]


# --- Fixtures: log, cola y ejecutor desechables; medicion NOT_COLLECTED determinista ------------------------------


@dataclass
class Banco:
    fx: po.Efectos
    llamadas: list[list[str]] = field(default_factory=list)


@pytest.fixture
def banco(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Banco:
    """`LOG`, `COLA` y `Efectos()` apuntan a tmp_path; el ejecutor registra y no ejecuta nada."""
    llamadas: list[list[str]] = []

    def ejecutar(args: list[str]) -> tuple[int, str]:
        llamadas.append(args)
        return 0, ""

    fx = po.Efectos(log=tmp_path / "log" / "portero.jsonl", cola=tmp_path / "cola", ejecutar=ejecutar)
    monkeypatch.setattr(po, "LOG", fx.log)
    monkeypatch.setattr(po, "COLA", fx.cola)
    monkeypatch.setattr(po, "Efectos", lambda: fx)
    return Banco(fx, llamadas)


@pytest.fixture
def sin_app_slice(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un uid sin cgroup ni procesos: lee_estado/observar leen solo lo que no existe y decide da NOT_COLLECTED."""
    monkeypatch.setattr(po.os, "getuid", lambda: 4_000_000)


# --- Clasificacion: ramas sin cubrir -------------------------------------------------------------------------


@pytest.mark.unit
def test_subcomando_git_salta_banderas_y_devuelve_none_sin_subcomando():
    assert po._subcomando_git(["git", "--no-pager", "commit"]) == "commit"
    assert po._subcomando_git(["git", "-C", "/r"]) is None  # solo opciones: no hay subcomando
    assert po._subcomando_git(["git", "-C", "/r", "commit"]) == "commit"  # control: con subcomando lo devuelve
    assert po._subcomando_git(["hg", "commit"]) is None


@pytest.mark.unit
def test_marca_hook_acepta_la_forma_con_igual_y_distingue_el_hook():
    assert po._marca_hook(["pre-commit", "--hook-stage=pre-push"], "pre-push")
    assert not po._marca_hook(["pre-commit", "--hook-stage=pre-commit"], "pre-push")  # control: otro hook
    assert po.clasifica(["x", "--hook-type=pre-push"]) == "suite"
    assert po.clasifica(["x", "--hook-type=post-merge"]) is None


@pytest.mark.unit
def test_holgura_none_si_falta_una_medicion_y_numero_si_estan_las_dos():
    assert po.Estado(0.0, "", None, 5).holgura_app_kb is None
    assert po.Estado(0.0, "", 5, None).holgura_app_kb is None
    assert po.Estado(0.0, "", 9, 5).holgura_app_kb == 4  # control


@pytest.mark.unit
def test_clase_con_turnos_cero_no_actua_y_con_un_turno_si():
    rota = {"suite": po.Clase(20 * G, 18 * G, 100, 0, 1)}
    acc = po.decide([arbol(1, 60)], estado(), rota)
    assert [a.tipo for a in acc] == ["no_actua"] and "no positivos" in acc[0].motivo
    sana = {"suite": po.Clase(20 * G, 18 * G, 100, 1, 1)}
    assert [a.tipo for a in po.decide([arbol(1, 60)], estado(), sana)] == ["admitir"]  # control: mismo arbol, turno 1


# --- Medicion de cgroups ---------------------------------------------------------------------------------------


def _cg(base: Path, rel: str, max_: str, cur: str = "0") -> Path:
    d = base / rel.lstrip("/")
    d.mkdir(parents=True, exist_ok=True)
    (d / "memory.max").write_text(max_ + "\n", encoding="utf-8")
    (d / "memory.current").write_text(cur + "\n", encoding="utf-8")
    return d


@pytest.mark.unit
def test_consumo_con_tope_propio_sigue_ante_un_subdirectorio_ilegible(tmp_path: Path):
    app = tmp_path / "app"
    _cg(app, "job.scope", str(8 * G * 1024), str(2 * G * 1024))  # finito: cuenta
    (app / "grupo" / "sellado").mkdir(parents=True)  # sin memory.max: se baja a sus hijos
    (app / "grupo" / "sellado" / "memory.max").write_text("max\n", encoding="utf-8")
    sellado = app / "grupo" / "sellado"
    (sellado / "interno").mkdir()
    sellado.chmod(0)
    try:
        assert po.consumo_con_tope_propio_kb(app) == 2 * G  # el ilegible no tumba la suma
        sellado.chmod(stat.S_IRWXU)
        _cg(sellado, "interno", str(4 * G * 1024), str(G * 1024))
        assert po.consumo_con_tope_propio_kb(app) == 3 * G  # control: legible, su hijo suma
    finally:
        sellado.chmod(stat.S_IRWXU)


@pytest.mark.unit
def test_lee_estado_sin_cgroup_de_app_declara_tope_none(sin_app_slice: None):
    e = po.lee_estado()
    assert isinstance(e, po.Estado)
    assert e.tope_app_kb is None and e.consumo_con_tope_propio_kb == 0
    assert po.consumo_con_tope_propio_kb(po.cgroup_app()) is None


@pytest.mark.unit
def test_lee_estado_real_devuelve_un_estado_medido_o_none_por_campo():
    e = po.lee_estado()
    assert isinstance(e, po.Estado) and isinstance(e.consumo_con_tope_propio_kb, int)
    assert e.psi_full_avg10 is None or e.psi_full_avg10 >= 0.0


# --- Freno termico: el archivo de estado real, en tmp -------------------------------------------------------------


def _termico(ruta: Path, estado_: str, hace_s: float) -> None:
    ts = (datetime.now(timezone.utc) - timedelta(seconds=hace_s)).isoformat()
    ruta.write_text(json.dumps({"estado": estado_, "actualizado": ts}), encoding="utf-8")


@pytest.mark.unit
def test_freno_termico_frena_ante_estado_distinto_de_normal_y_no_sabe_ante_dato_viejo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    agt = pytest.importorskip("tools.atom_gpu_telemetry")
    ruta = tmp_path / "estado_termico.json"
    monkeypatch.setattr(agt, "ESTADO_TERMICO_PATH", ruta)
    _termico(ruta, "sostenida", 1)
    assert po.freno_termico() == "estado termico 'sostenida'"
    _termico(ruta, "sostenida", agt.ESTADO_TERMICO_LATIDO_S + 30)  # control: mismo estado, latido viejo
    assert po.freno_termico() is None
    _termico(ruta, "desconocido", 1)
    assert po.freno_termico() is None
    ruta.write_text("{no es json", encoding="utf-8")
    assert po.freno_termico() is None
    ruta.write_text(json.dumps({"estado": "normal"}), encoding="utf-8")  # falta `actualizado`
    assert po.freno_termico() is None
    ruta.unlink()
    assert po.freno_termico() is None


@pytest.mark.unit
def test_freno_termico_normal_y_fresco_delega_en_el_presupuesto_termico(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    agt = pytest.importorskip("tools.atom_gpu_telemetry")
    ruta = tmp_path / "estado_termico.json"
    monkeypatch.setattr(agt, "ESTADO_TERMICO_PATH", ruta)
    _termico(ruta, "normal", 1)
    r = po.freno_termico()
    assert r is None or isinstance(r, str)  # '' admite, texto frena, None no se sabe: el sensor real decide
    _termico(ruta, "critica", 1)  # control: no normal nunca llega al sensor
    assert po.freno_termico() == "estado termico 'critica'"


@pytest.mark.unit
def test_freno_termico_sin_el_modulo_de_telemetria_no_se_sabe(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(sys.modules, "tools.atom_gpu_telemetry", None)  # import -> ImportError
    monkeypatch.setitem(sys.modules, "atom_gpu_telemetry", None)
    assert po.freno_termico() is None


# --- /proc falso: _lee_proc, _Tabla, observar ----------------------------------------------------------------------


def _proc(base: Path, pid: int, ppid: int, argv: list[str], cg: str, rss_kb: int, inicio_s: float = 100.0) -> None:
    d = base / str(pid)
    d.mkdir(parents=True)
    ticks = int(inicio_s * HZ)
    (d / "stat").write_text(f"{pid} (py (x)) S {ppid} " + " ".join(["0"] * 17) + f" {ticks} 0 0\n", encoding="utf-8")
    (d / "cmdline").write_text("\0".join(argv) + "\0", encoding="utf-8")
    (d / "cgroup").write_text(f"0::{cg}\n", encoding="utf-8")
    (d / "status").write_text(f"Name:\tx\nVmRSS:\t{rss_kb} kB\n", encoding="utf-8")


@pytest.mark.unit
def test_lee_proc_ilegible_o_corrupto_es_none_y_el_sano_se_lee(tmp_path: Path):
    _proc(tmp_path, 10, 1, ["python", "x.py"], CLAUDE, 123)
    p = po._lee_proc(tmp_path / "10")
    assert p is not None and (p.ppid, p.argv, p.cgroup, p.rss_kb) == (1, ["python", "x.py"], CLAUDE, 123)
    (tmp_path / "11").mkdir()
    assert po._lee_proc(tmp_path / "11") is None  # sin stat
    (tmp_path / "11" / "stat").write_text("", encoding="utf-8")
    assert po._lee_proc(tmp_path / "11") is None  # stat vacio
    (tmp_path / "11" / "stat").write_text("11 (x) S", encoding="utf-8")
    assert po._lee_proc(tmp_path / "11") is None  # IndexError: faltan campos
    (tmp_path / "11" / "stat").write_text("11 (x) S abc " + " ".join(["0"] * 20), encoding="utf-8")
    assert po._lee_proc(tmp_path / "11") is None  # ValueError: ppid no numerico


def _mundo(tmp_path: Path) -> tuple[Path, Path, Path]:
    proc, cg, cola = tmp_path / "proc", tmp_path / "cg", tmp_path / "cola"
    proc.mkdir()
    (proc / "uptime").write_text("1000.00 500.00\n", encoding="utf-8")
    nuestro, ocioso = APP + "/bb-portero-suite-200.scope", APP + "/bb-portero-suite-210.scope"
    _proc(proc, 200, 1, ["python", "-m", "pytest"], nuestro, 1000, inicio_s=50)
    _proc(proc, 201, 200, ["python", "worker"], nuestro, 500, inicio_s=60)
    _proc(proc, 210, 1, ["sleep", "9"], ocioso, 7, inicio_s=70)
    (cg / nuestro.lstrip("/")).mkdir(parents=True)
    (cg / nuestro.lstrip("/") / "cgroup.events").write_text("populated 1\nfrozen 1\n", encoding="utf-8")
    (cg / ocioso.lstrip("/")).mkdir(parents=True)
    (cg / ocioso.lstrip("/") / "cgroup.events").write_text("populated 1\nfrozen 0\n", encoding="utf-8")
    _proc(proc, 299, 1, ["git", "push", "origin"], "/user.slice/x", 1)
    _proc(proc, 300, 299, ["python", "-m", "pytest", "-n", "8"], CLAUDE, 4000, inicio_s=100)
    _proc(proc, 301, 300, ["python", "worker"], CLAUDE, 600, inicio_s=101)
    _proc(proc, 302, 300, ["pytest", "sub"], CLAUDE, 50, inicio_s=102)  # misma forma que su padre: no es raiz
    _proc(proc, 400, 1, ["vim", "notas"], CLAUDE, 9)
    _cg(cg, CLAUDE, str(8 * G * 1024))
    cola.mkdir()
    (cola / "300.json").write_text(json.dumps({"pid": 300, "clase": "suite", "ts": time.time() - 30}), encoding="utf-8")
    (cola / "9999.json").write_text(json.dumps({"pid": 9999, "clase": "suite", "ts": time.time()}), encoding="utf-8")
    return proc, cg, cola


@pytest.mark.unit
def test_observar_arma_arboles_nuestros_por_forma_y_peticiones(tmp_path: Path):
    proc, cg, cola = _mundo(tmp_path)
    arboles = po.observar(proc, cg, cola)
    assert arboles is not None
    por = {(a.raiz, a.virtual): a for a in arboles}
    assert sorted(por) == [(200, False), (210, False), (300, False), (300, True)]  # ni 201/302 (no raices), ni 400 (sin forma)
    n = por[(200, False)]
    assert (n.clase, n.rss_kb, n.procesos, n.pids, n.congelado, n.unidad) == (
        "suite", 1500, 2, (200, 201), True, "bb-portero-suite-200.scope")
    assert n.edad_s == pytest.approx(950.0)
    assert por[(210, False)].congelado is False  # control: frozen 0 no es congelado
    f = por[(300, False)]
    assert (f.rss_kb, f.procesos, f.unidad, f.tope_propio_kb) == (4650, 3, None, 8 * G)
    assert f.ancestros == ("python -m pytest -n 8", "git push origin") and f.edad_s == pytest.approx(900.0)
    v = por[(300, True)]
    assert v.unidad is None and v.edad_s >= 30.0  # peticion viva; la del pid 9999 muerto no entra


@pytest.mark.unit
def test_observar_proc_sin_uptime_es_none_y_con_uptime_corrupto_tambien(tmp_path: Path):
    (tmp_path / "1").mkdir()
    assert po.observar(tmp_path, tmp_path, tmp_path / "c") is None  # sin /proc/uptime
    (tmp_path / "uptime").write_text("no-es-numero\n", encoding="utf-8")
    assert po.observar(tmp_path, tmp_path, tmp_path / "c") is None
    (tmp_path / "uptime").write_text("5.0 1.0\n", encoding="utf-8")  # control: con uptime valido hay lista
    assert po.observar(tmp_path, tmp_path, tmp_path / "c") == []


@pytest.mark.unit
def test_observar_control_negativo_un_scope_con_nombre_ajeno_no_es_nuestro(tmp_path: Path):
    proc, cg, cola = _mundo(tmp_path)
    (proc / "200" / "cgroup").write_text(f"0::{APP}/bb-portero-suite-x.scope\n", encoding="utf-8")
    (proc / "201" / "cgroup").write_text(f"0::{APP}/bb-portero-suite-x.scope\n", encoding="utf-8")
    arboles = po.observar(proc, cg, cola)
    assert arboles is not None
    # 200 sigue siendo pytest: ahora aparece por forma, no como scope nuestro, y 210 sigue siendo el unico nuestro
    assert [(a.raiz, a.unidad) for a in arboles if a.unidad and not a.virtual] == [(210, "bb-portero-suite-210.scope")]
    assert 200 in {a.raiz for a in arboles if a.unidad is None}


@pytest.mark.unit
def test_tabla_ancestros_corta_los_ciclos_y_edad_no_es_negativa(tmp_path: Path):
    proc = tmp_path / "proc"
    proc.mkdir()
    (proc / "uptime").write_text("10.0 1.0\n", encoding="utf-8")
    _proc(proc, 5, 6, ["a"], CLAUDE, 1, inicio_s=500)  # arranque "en el futuro" respecto del uptime
    _proc(proc, 6, 5, ["b"], CLAUDE, 1, inicio_s=1)
    t = po._Tabla.lee(proc)
    assert t is not None
    assert t.ancestros(5) == ("a", "b")  # el ciclo 5 -> 6 -> 5 termina
    assert t.edad(t.procs[5]) == 0.0 and t.edad(t.procs[6]) == pytest.approx(9.0)


# --- Cola: peticiones ilegibles --------------------------------------------------------------------------------


@pytest.mark.unit
def test_peticion_ilegible_se_declara_en_stderr_y_no_entra(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    cola = tmp_path / "cola"
    cola.mkdir()
    (cola / "1.json").write_text("{roto", encoding="utf-8")
    (cola / "2.json").write_text(json.dumps({"pid": 2, "clase": "suite"}), encoding="utf-8")  # falta ts
    (cola / "3.json").write_text(json.dumps({"pid": 3, "clase": "suite", "ts": time.time()}), encoding="utf-8")
    out = po._peticiones({1: 0, 2: 0, 3: 0}, time.time(), cola)
    assert [a.raiz for a in out] == [3]  # control: la sana entra
    err = capsys.readouterr().err
    assert "peticion ilegible 1.json" in err and "peticion ilegible 2.json" in err and "3.json" not in err


@pytest.mark.unit
def test_cola_que_es_un_archivo_o_no_existe_no_tumba(tmp_path: Path):
    (tmp_path / "archivo").write_text("x", encoding="utf-8")
    assert po._peticiones({1: 0}, time.time(), tmp_path / "archivo") == []
    assert po._peticiones({1: 0}, time.time(), tmp_path / "no-existe") == []


# --- Ejecutor, cgroup.freeze, adopcion, log ------------------------------------------------------------------------


@pytest.mark.unit
def test_ejecuta_devuelve_rc_y_salida_y_127_si_el_comando_no_existe():
    assert po._ejecuta(["echo", "hola"]) == (0, "hola")
    assert po._ejecuta(["false"])[0] == 1
    rc, txt = po._ejecuta(["/no/existe/cmd-portero"])
    assert rc == 127 and "cmd-portero" in txt


@pytest.mark.unit
def test_congela_escribe_el_archivo_o_devuelve_el_error(tmp_path: Path):
    assert po.congela(tmp_path, True) == "" and (tmp_path / "cgroup.freeze").read_text(encoding="utf-8") == "1"
    assert po.congela(tmp_path, False) == "" and (tmp_path / "cgroup.freeze").read_text(encoding="utf-8") == "0"
    err = po.congela(tmp_path / "no-existe", True)
    assert err.startswith("FileNotFoundError")
    assert po.mueve_pid(7, tmp_path / "no-existe").startswith("FileNotFoundError")


@pytest.mark.unit
def test_adopta_propaga_el_fallo_del_ejecutor_y_la_raiz_que_no_quedo_en_su_scope(tmp_path: Path):
    a = po.Arbol(raiz=PID_INEXISTENTE, clase="suite", rss_kb=1, procesos=1, edad_s=1, cgroup=CLAUDE)
    ac = po.Accion("admitir", "x", a.raiz, "suite", topes=po._topes(po.CLASES["suite"]))
    assert po._adopta(a, ac, lambda args: (3, "busctl cayo"), tmp_path) == (3, "busctl cayo", None)
    rc, salida, destino = po._adopta(a, ac, lambda args: (0, "ok"), tmp_path)  # control: rc 0 pero la raiz no se movio
    assert rc == 1 and destino is None and f"bb-portero-suite-{PID_INEXISTENTE}.scope" in salida


@pytest.mark.unit
def test_registra_escribe_la_fila_y_ante_un_log_imposible_lo_dice_en_stderr(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    ok = tmp_path / "a" / "b" / "p.jsonl"
    po._registra({"accion": "x"}, ok)
    assert filas(ok)[0]["accion"] == "x"
    (tmp_path / "archivo").write_text("x", encoding="utf-8")
    po._registra({"accion": "y"}, tmp_path / "archivo" / "p.jsonl")  # el "directorio" padre es un archivo
    assert "no se pudo escribir" in capsys.readouterr().err
    assert not (tmp_path / "archivo" / "p.jsonl").exists()


@pytest.mark.unit
def test_aplica_registra_el_arbol_no_observado_y_control_con_el_arbol_presente(tmp_path: Path):
    fx = po.Efectos(log=tmp_path / "p.jsonl", ejecutar=lambda a: (1, "busctl cayo"))
    ac = po.Accion("admitir", "turno", 99, "suite", topes=po._topes(po.CLASES["suite"]))
    ev = po.aplica([ac], [], estado(), fx)
    assert ev[0]["rc"] == 1 and ev[0]["salida"] == "arbol no observado" and "unidad" not in ev[0]
    ev = po.aplica([ac], [arbol(99, 5)], estado(), fx)  # control: observado, se intenta y el fallo es el del ejecutor
    assert ev[0]["salida"] == "busctl cayo" and ev[0]["unidad"] == "bb-portero-suite-99.scope"
    assert [f["accion"] for f in filas(fx.log)] == ["admitir", "admitir"]


# --- Contenedores ----------------------------------------------------------------------------------------------


@pytest.mark.unit
def test_observar_contenedores_salta_lineas_mal_formadas(tmp_path: Path):
    cid = "c" * 64
    _cg(tmp_path, f"docker.slice/docker-{cid}.scope", "max")
    salida = f"corta\n{cid} dos palabras\n{'z' * 64} idnohex\n{cid} libre\n"
    assert po.observar_contenedores(lambda a: (0, salida), tmp_path) == [po.Contenedor("libre", None, None)]
    assert po.observar_contenedores(lambda a: (0, "corta\n"), tmp_path) == []  # control: sin lineas validas, lista vacia


# --- Turno: espera real y fallo cerrado ---------------------------------------------------------------------------


def _fuente_de(estados: list[po.Estado | None], pid: int, cola: Path):
    it = iter(estados)

    def fuente() -> tuple[po.Estado, list[po.Arbol] | None]:
        e = next(it)
        assert e is not None
        return e, po._peticiones({pid: object()}, time.time(), cola)

    return fuente


@pytest.mark.unit
def test_turno_sin_funcion_de_espera_duerme_el_intervalo_y_luego_lanza(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(po, "INTERVALO_S", 0.0)
    fx = po.Efectos(log=tmp_path / "p.jsonl", cola=tmp_path / "cola")
    pid = os.getpid()
    acc = po.turno(pid, "suite", _fuente_de([estado(psi=20.0), estado(psi=0.0)], pid, fx.cola), None, fx)
    assert acc.tipo == "admitir"
    assert [f["accion"] for f in filas(fx.log)] == ["esperar", "turno"]


@pytest.mark.unit
def test_turno_con_medicion_no_colectada_lanza_como_antes_y_con_medicion_sana_decide(tmp_path: Path):
    pid = os.getpid()
    fx = po.Efectos(log=tmp_path / "p.jsonl", cola=tmp_path / "cola")
    ciego = po.turno(pid, "suite", lambda: (estado(psi=None), []), lambda: pytest.fail("no debe esperar"), fx)
    assert ciego.tipo == "no_actua" and ciego.motivo.startswith("NOT_COLLECTED")
    assert json.loads((fx.cola / f"{pid}.json").read_text(encoding="utf-8"))["concedido"] is True
    assert filas(fx.log)[0]["concedido"] == "no_actua"
    fx2 = po.Efectos(log=tmp_path / "q.jsonl", cola=tmp_path / "cola2")
    sano = po.turno(pid, "suite", _fuente_de([estado()], pid, fx2.cola), lambda: pytest.fail("no debe esperar"), fx2)
    assert sano.tipo == "admitir"  # control: el mismo estado con PSI medido da el veredicto contrario
    assert filas(fx2.log)[0]["concedido"] == "admitir"


# --- cmd_run: el comando de verdad bajo un systemd-run de mentira ---------------------------------------------------


@pytest.fixture
def falso_systemd_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Un `systemd-run` en el PATH que anota sus argumentos y ejecuta el comando tras `--`. No toca systemd."""
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    args_ = tmp_path / "args.txt"
    script = bin_ / "systemd-run"
    script.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" > '{args_}'\nwhile [ \"$1\" != \"--\" ]; do shift; done\nshift\nexec \"$@\"\n",
                      encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_}{os.pathsep}{os.environ['PATH']}")
    return args_


@pytest.mark.unit
@pytest.mark.parametrize(("cmd", "rc"), [(["--", "true"], 0), (["--", "false"], 1), (["true"], 0)])
def test_cmd_run_devuelve_el_codigo_del_comando_y_deja_la_cola_limpia(
    banco: Banco, falso_systemd_run: Path, sin_app_slice: None, capsys: pytest.CaptureFixture[str], cmd: list[str], rc: int
):
    pid = os.getpid()
    assert po.cmd_run(argparse.Namespace(cmd=cmd, clase="suite")) == rc
    pasados = falso_systemd_run.read_text(encoding="utf-8").splitlines()
    assert f"--unit=bb-portero-suite-{pid}.scope" in pasados and f"MemoryMax={20 * G * 1024}" in pasados
    assert pasados[-1] == cmd[-1] and "--slice=app.slice" in pasados
    assert not (banco.fx.cola / f"{pid}.json").exists()  # la peticion se retira al terminar
    ultima = filas(banco.fx.log)[-1]
    assert ultima["accion"] == "fin" and ultima["rc"] == rc and ultima["unidad"] == f"bb-portero-suite-{pid}.scope"
    assert "MemoryMax=20G" in capsys.readouterr().err


@pytest.mark.unit
def test_cmd_run_tolera_que_la_peticion_ya_no_exista_al_terminar(banco: Banco, falso_systemd_run: Path, sin_app_slice: None):
    pid = os.getpid()
    borra = ["--", "sh", "-c", f"rm -f '{banco.fx.cola / f'{pid}.json'}'"]
    assert po.cmd_run(argparse.Namespace(cmd=borra, clase="suite")) == 0
    assert filas(banco.fx.log)[-1]["accion"] == "fin"


@pytest.mark.unit
def test_cmd_run_sin_comando_da_2_y_no_toca_la_cola(banco: Banco, capsys: pytest.CaptureFixture[str]):
    assert po.cmd_run(argparse.Namespace(cmd=["--"], clase="suite")) == 2
    assert po.cmd_run(argparse.Namespace(cmd=[], clase="suite")) == 2
    assert "uso: bb portero run" in capsys.readouterr().err
    assert not banco.fx.cola.exists() and not banco.fx.log.exists()


# --- _ciclo, demonio, estado, contenedores --------------------------------------------------------------------------


@pytest.mark.unit
def test_ciclo_registra_la_decision_no_actua_una_sola_vez(banco: Banco, sin_app_slice: None):
    ultimo: dict[Any, str] = {}
    ev: list[dict[str, Any]] = [{}]
    for _ in range(3):
        ev = po._ciclo(ultimo)
    assert ev == [] and len(filas(banco.fx.log)) == 1  # la repeticion se suprime
    fila = filas(banco.fx.log)[0]
    assert fila["accion"] == "no_actua" and fila["motivo"].startswith("NOT_COLLECTED")
    assert fila["medicion"]["tope_app_kb"] == "NOT_COLLECTED" and banco.llamadas == []


@pytest.fixture
def docker_falso(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """docker.slice de 14 GiB en tmp y un contenedor sin tope; `docker` no se invoca (observar se sustituye)."""
    raiz = tmp_path / "cgroot"
    _cg(raiz, "docker.slice", str(14 * G * 1024), "0")
    monkeypatch.setattr(po, "CGROUP_RAIZ", raiz)
    monkeypatch.setattr(po, "observar_contenedores", lambda: [po.Contenedor("libre", None, 1 * G)])


@pytest.mark.unit
@pytest.mark.parametrize("aplicar", [True, False])
def test_cmd_contenedores_imprime_cada_decision_y_solo_aplica_con_la_bandera(
    banco: Banco, docker_falso: None, capsys: pytest.CaptureFixture[str], aplicar: bool
):
    assert po.cmd_contenedores(argparse.Namespace(aplicar=aplicar)) == 0
    impreso = [json.loads(x) for x in capsys.readouterr().out.splitlines()]
    assert [(e["accion"], e["contenedor"]) for e in impreso] == [("acotar" if aplicar else "acotaria", "libre")]
    b = str(14 * G * 1024)
    esperadas = [["docker", "update", "--memory", b, "--memory-swap", b, "libre"]] if aplicar else []
    assert banco.llamadas == esperadas  # control negativo: sin --aplicar no se llama a docker
    assert [f["accion"] for f in filas(banco.fx.log)] == [impreso[0]["accion"]]


@pytest.mark.unit
def test_cmd_demonio_una_vez_corre_un_ciclo_y_con_contenedores_aplica(
    banco: Banco, docker_falso: None, sin_app_slice: None, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(po.time, "sleep", lambda s: pytest.fail("una vez no duerme"))
    assert po.cmd_demonio(argparse.Namespace(una_vez=True, contenedores=True)) == 0
    assert [f["accion"] for f in filas(banco.fx.log)] == ["no_actua", "acotar"]
    assert len(banco.llamadas) == 1 and banco.llamadas[0][:2] == ["docker", "update"]


@pytest.mark.unit
def test_cmd_demonio_sin_contenedores_no_llama_a_docker_y_duerme_entre_ciclos(
    banco: Banco, docker_falso: None, sin_app_slice: None, monkeypatch: pytest.MonkeyPatch
):
    class Parar(Exception):
        pass

    dormidos: list[float] = []
    del_test = threading.current_thread()
    real = po.time.sleep

    def dormir(s: float) -> None:
        # `po.time` es el modulo `time` ENTERO: este parche tambien lo ve cualquier hilo filtrado por otro test
        # (p.ej. el de muestreo de gpuoom_bb, que duerme 0.01 s). Solo cuenta lo que duerme el hilo del test.
        if threading.current_thread() is not del_test:
            real(0)
            return
        dormidos.append(s)
        raise Parar

    monkeypatch.setattr(po.time, "sleep", dormir)
    intruso = threading.Thread(target=lambda: po.time.sleep(0.01))  # control: un hilo ajeno duerme mientras el parche esta puesto
    intruso.start()
    intruso.join()
    with pytest.raises(Parar):
        po.cmd_demonio(argparse.Namespace(una_vez=False, contenedores=False))
    assert dormidos == [po.INTERVALO_S]  # tras un ciclo, antes del siguiente; el hilo ajeno no cuenta
    assert [f["accion"] for f in filas(banco.fx.log)] == ["no_actua"] and banco.llamadas == []


@pytest.mark.unit
def test_cmd_estado_imprime_medicion_decision_y_los_ultimos_diez_eventos(
    banco: Banco, sin_app_slice: None, capsys: pytest.CaptureFixture[str]
):
    assert po.cmd_estado(argparse.Namespace()) == 0
    vacio = json.loads(capsys.readouterr().out)
    assert vacio["ultimos_eventos"] == [] and vacio["arboles"] == []  # control: sin log no hay eventos
    assert vacio["medicion"]["tope_app_kb"] == "NOT_COLLECTED"
    assert vacio["decidiria"][0]["accion"] == "no_actua"
    banco.fx.log.parent.mkdir(parents=True)
    banco.fx.log.write_text("".join(f'{{"n": {i}}}\n' for i in range(12)) + "linea suelta\n", encoding="utf-8")
    assert po.cmd_estado(argparse.Namespace()) == 0
    lleno = json.loads(capsys.readouterr().out)
    assert [e["n"] for e in lleno["ultimos_eventos"]] == list(range(3, 12))  # 10 ultimas lineas, la suelta se descarta


@pytest.mark.unit
def test_fuente_real_devuelve_estado_y_arboles_leidos():
    e, arboles = po._fuente_real()
    assert isinstance(e, po.Estado) and (arboles is None or isinstance(arboles, list))


# --- main y `python tools/portero.py` ----------------------------------------------------------------------------


@pytest.mark.unit
def test_main_despacha_estado_contenedores_demonio_y_run(
    banco: Banco, docker_falso: None, sin_app_slice: None, falso_systemd_run: Path, capsys: pytest.CaptureFixture[str]
):
    assert po.main(["estado"]) == 0
    assert json.loads(capsys.readouterr().out)["decidiria"][0]["accion"] == "no_actua"
    assert po.main(["contenedores"]) == 0
    assert json.loads(capsys.readouterr().out.splitlines()[0])["accion"] == "acotaria"
    assert po.main(["contenedores", "--aplicar"]) == 0
    assert banco.llamadas and banco.llamadas[0][:2] == ["docker", "update"]
    assert po.main(["demonio", "--una-vez"]) == 0
    assert po.main(["run", "--", "false"]) == 1  # el codigo del comando llega hasta main
    assert po.main(["run", "--clase", "suite", "--", "true"]) == 0
    with pytest.raises(SystemExit) as e:
        po.main(["no-existe"])  # control negativo: un subcomando desconocido no despacha nada
    assert e.value.code == 2


@pytest.mark.unit
def test_ejecutado_como_script_sale_con_el_codigo_de_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sin_app_slice: None, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path / "datos"))
    monkeypatch.setattr(sys, "argv", ["portero.py", "estado"])
    with pytest.raises(SystemExit) as e:
        runpy.run_path(po.__file__, run_name="__main__")
    assert e.value.code == 0
    assert json.loads(capsys.readouterr().out)["decidiria"][0]["accion"] == "no_actua"
    monkeypatch.setattr(sys, "argv", ["portero.py"])  # control: sin subcomando argparse sale con 2
    with pytest.raises(SystemExit) as e2:
        runpy.run_path(po.__file__, run_name="__main__")
    assert e2.value.code == 2
