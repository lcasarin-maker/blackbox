"""Portero: ramas que DEBEN actuar y ramas que NO, y una prueba real con scopes desechables propios."""

import json
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import replace
from pathlib import Path

import pytest

from tools import portero as po

G = po.GIB_KB
APP = "/user.slice/user-1000.slice/user@1000.service/app.slice"
CLAUDE = APP + "/app-com.anthropic.Claude-1.scope"


def estado(psi: float | None = 0.0, freno: str | None = "", tope: int | None = 42 * G, uso: int | None = 30 * G, **kw):
    return po.Estado(psi, freno, tope, uso, tuple(kw.get("alternos", ())), kw.get("consumo", 0))


def arbol(raiz, edad, rss=10 * G, cgroup=CLAUDE, **kw):
    return po.Arbol(raiz=raiz, clase="suite", rss_kb=rss, procesos=5, edad_s=edad, cgroup=cgroup, **kw)


def tipos(acciones):
    return {(a.raiz, a.tipo) for a in acciones}


# --- PSI, termico, holgura -----------------------------------------------------------------------------------


@pytest.mark.unit
def test_psi_bajo_admite_el_arbol_pesado():
    assert tipos(po.decide([arbol(1, 60)], estado(psi=0.5))) == {(1, "admitir")}


@pytest.mark.unit
def test_psi_alto_congela_en_vez_de_admitir():
    acc = po.decide([arbol(1, 60)], estado(psi=po.PSI_FULL_MAX))
    assert tipos(acc) == {(1, "congelar")} and "PSI" in acc[0].motivo


@pytest.mark.unit
def test_freno_termico_congela():
    acc = po.decide([arbol(1, 60)], estado(freno="estado termico 'sostenida'"))
    assert tipos(acc) == {(1, "congelar")} and "termico" in acc[0].motivo


@pytest.mark.unit
@pytest.mark.parametrize("campo", ["psi", "freno", "tope", "uso"])
def test_sin_medir_no_actua_y_lo_declara(campo):
    acc = po.decide([arbol(1, 60), arbol(2, 30)], estado(**{campo: None}))
    assert [a.tipo for a in acc] == ["no_actua"] and acc[0].motivo.startswith("NOT_COLLECTED")


@pytest.mark.unit
def test_proc_ilegible_no_actua(tmp_path):
    assert po.observar(proc=tmp_path / "no-existe") is None
    acc = po.decide(None, estado())
    assert [a.tipo for a in acc] == ["no_actua"] and "/proc" in acc[0].motivo


@pytest.mark.unit
def test_holgura_baja_congela_y_con_slice_alterno_mueve():
    poca = 42 * G - po.HOLGURA_MIN_KB + 1
    assert tipos(po.decide([arbol(1, 60)], estado(uso=poca))) == {(1, "congelar")}
    alt = po.SliceAlterno("bb-jobs.slice", 30 * G, 0)
    acc = po.decide([arbol(1, 60)], estado(uso=poca, alternos=[alt]))
    assert tipos(acc) == {(1, "mover")} and acc[0].slice == "bb-jobs.slice"
    lleno = po.SliceAlterno("bb-jobs.slice", 30 * G, 15 * G)  # 15 + 20 > 30: no cabe
    assert tipos(po.decide([arbol(1, 60)], estado(uso=poca, alternos=[lleno]))) == {(1, "congelar")}


# --- Cola FIFO -----------------------------------------------------------------------------------------------


@pytest.mark.unit
def test_cola_con_uno_dos_y_tres_arboles():
    assert tipos(po.decide([arbol(1, 60)], estado())) == {(1, "admitir")}
    assert tipos(po.decide([arbol(1, 30), arbol(2, 60)], estado())) == {(2, "admitir"), (1, "congelar")}
    tres = [arbol(1, 10), arbol(2, 90), arbol(3, 50)]
    assert tipos(po.decide(tres, estado())) == {(2, "admitir"), (3, "congelar"), (1, "congelar")}


@pytest.mark.unit
def test_admitido_no_se_recongela_aunque_suba_la_presion():
    corriendo = arbol(1, 600, unidad="bb-portero-suite-1.scope")
    assert po.decide([corriendo, arbol(2, 900)], estado(psi=50.0)) == [
        po.Accion("congelar", "PSI memory full avg10=50.0 >= 5.0", 2, "suite", topes=po._topes(po.CLASES["suite"]))
    ]


@pytest.mark.unit
def test_turno_ocupado_congela_al_nuevo_y_al_liberarse_descongela_al_mas_antiguo():
    corriendo = arbol(1, 600, unidad="bb-portero-suite-1.scope")
    assert tipos(po.decide([corriendo, arbol(2, 60)], estado())) == {(2, "congelar")}
    c2 = arbol(2, 60, unidad="bb-portero-suite-2.scope", congelado=True)
    c3 = arbol(3, 120, unidad="bb-portero-suite-3.scope", congelado=True)
    assert tipos(po.decide([c2, c3], estado())) == {(3, "descongelar"), (2, "esperar")}


@pytest.mark.unit
def test_arbol_ligero_no_se_toca():
    assert po.decide([arbol(1, 60, rss=po.UMBRAL_RSS_SUITE_KB - 1)], estado()) == []


# --- Excepciones -----------------------------------------------------------------------------------------------


@pytest.mark.unit
def test_pre_commit_no_se_congela_solo_se_le_pone_tope():
    corriendo = arbol(1, 600, unidad="bb-portero-suite-1.scope")
    pc = arbol(2, 60, ancestros=("/bin/sh .git/hooks/pre-commit", "git commit -m x", "bash"))
    acc = po.decide([corriendo, pc], estado())
    assert tipos(acc) == {(2, "admitir")} and "index.lock" in acc[0].motivo


@pytest.mark.unit
def test_control_negativo_pre_push_si_se_congela():
    corriendo = arbol(1, 600, unidad="bb-portero-suite-1.scope")
    pp = arbol(2, 60, ancestros=(
        "python .simplecode/run.py simplecode.verification.gate_runner --hook pre-push -- pre-commit run --hook-stage pre-push",
        "git push origin master",
    ))
    assert tipos(po.decide([corriendo, pp], estado())) == {(2, "congelar")}


@pytest.mark.unit
def test_fuera_de_app_slice_no_actua():
    for cg in ("/system.slice/docker-abc.scope", "/system.slice/x.service", "/user.slice/user-1000.slice/session-2.scope"):
        acc = po.decide([arbol(1, 60, cgroup=cg)], estado())
        assert [a.tipo for a in acc] == ["no_actua"] and "fuera de app.slice" in acc[0].motivo, cg


@pytest.mark.unit
def test_proceso_con_tope_propio_no_se_mueve():
    atlas = arbol(1, 60, tope_propio_kb=8 * G, cgroup=APP + "/run-u5.scope")
    acc = po.decide([atlas], estado())
    assert [a.tipo for a in acc] == ["no_actua"] and "tope propio" in acc[0].motivo


@pytest.mark.unit
def test_control_negativo_tope_propio_mas_holgado_que_la_clase_si_es_candidato():
    assert tipos(po.decide([arbol(1, 60, tope_propio_kb=40 * G)], estado())) == {(1, "admitir")}


@pytest.mark.unit
def test_jobs_de_atlas_docker_y_bb_cap_excluidos_aunque_no_tengan_tope():
    casos = [
        arbol(1, 60, cgroup=APP + "/liberation_job.scope"),
        arbol(2, 60, cgroup=APP + "/liberation_job_test_7.scope"),
        arbol(3, 60, cgroup=APP + "/bb-cap-code-99.scope"),
        arbol(4, 60, ancestros=("pytest -n 8", "python3 liberation_watchdog.py --loop")),
    ]
    acc = po.decide(casos, estado())
    assert {a.tipo for a in acc} == {"no_actua"} and len(acc) == 4
    assert all("excluido" in a.motivo for a in acc)


# --- Presupuesto ------------------------------------------------------------------------------------------------


@pytest.mark.unit
def test_presupuesto_desbordado_no_actua():
    clases = {"suite": po.Clase(20 * G, 18 * G, 100, 3, 1)}  # 3 x 20 > 42
    acc = po.decide([arbol(1, 60)], estado(), clases)
    assert [a.tipo for a in acc] == ["no_actua"] and "desbordado" in acc[0].motivo
    altas = {"suite": po.Clase(20 * G, 21 * G, 100, 1, 1)}  # MemoryHigh > MemoryMax
    assert po.decide([arbol(1, 60)], estado(), altas)[0].tipo == "no_actua"


@pytest.mark.unit
def test_clase_suite_lleva_el_tope_que_cierra_los_colapsos_del_11_oct():
    """DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01: la suite pesada de un scope de sesion sale con 20G/18G, sin swap.

    Los numeros son el contrato del cierre (medicion.txt de la ficha). Control negativo: con 3 turnos de 20G el
    presupuesto de un app.slice de 42G se desborda y el portero no actua.
    """
    c = po.CLASES["suite"]
    esperado = {"MemoryMax": 20 * 1024**3, "MemoryHigh": 18 * 1024**3, "MemorySwapMax": 0, "TasksMax": 1230}
    assert po._topes(c) == esperado and c.turnos == 1
    assert po.presupuesto_desbordado(42 * G, po.CLASES) == ""
    acc = po.decide([arbol(1, 60, rss=c.umbral_rss_kb)], estado())
    assert tipos(acc) == {(1, "admitir")} and acc[0].topes == esperado
    tres = {"suite": replace(c, turnos=3)}
    assert po.presupuesto_desbordado(42 * G, tres) != ""
    assert [a.tipo for a in po.decide([arbol(1, 60, rss=c.umbral_rss_kb)], estado(), tres)] == ["no_actua"]


@pytest.mark.unit
def test_presupuesto_descuenta_lo_que_consumen_los_scopes_con_tope_propio():
    acc = po.decide([arbol(1, 60)], estado(consumo=23 * G))  # 23 + 20 > 42
    assert tipos(acc) == {(1, "congelar")} and "presupuesto" in acc[0].motivo
    assert tipos(po.decide([arbol(1, 60)], estado(consumo=22 * G))) == {(1, "admitir")}  # 22 + 20 = 42 cabe


# --- Clasificacion -----------------------------------------------------------------------------------------------


@pytest.mark.unit
def test_clasifica_por_forma():
    assert po.clasifica(["python3", "-m", "pytest", "-n", "8"]) == "suite"
    assert po.clasifica(["/home/x/.venv/bin/pytest"]) == "suite"
    assert po.clasifica(["/bin/sh", ".git/hooks/pre-push", "origin"]) == "suite"
    assert po.clasifica(["pre-commit", "run", "--hook-stage", "pre-push"]) == "suite"
    assert po.clasifica(["python3", "server.py"]) is None
    assert po.clasifica(["vim", "pytest.ini"]) is None


@pytest.mark.unit
def test_sostiene_index_lock():
    assert po.sostiene_index_lock(["git -C /r commit -m x"])
    assert po.sostiene_index_lock(["git rebase main"])
    assert po.sostiene_index_lock(["python run.py --hook pre-commit"])
    assert not po.sostiene_index_lock(["git push origin master", "bash"])
    assert not po.sostiene_index_lock(["pre-commit run --hook-stage pre-push"])


# --- Medicion de cgroups (arbol falso en disco) -----------------------------------------------------------------


def _cg(base: Path, rel: str, max_: str, cur: str = "0"):
    d = base / rel.lstrip("/")
    d.mkdir(parents=True, exist_ok=True)
    (d / "memory.max").write_text(max_ + "\n", encoding="utf-8")
    (d / "memory.current").write_text(cur + "\n", encoding="utf-8")
    return d


@pytest.mark.unit
def test_tope_propio_y_consumo_con_tope_propio(tmp_path):
    app = _cg(tmp_path, APP, str(42 * G * 1024), str(30 * G * 1024))
    _cg(tmp_path, APP + "/app-com.anthropic.Claude-1.scope", "max", str(20 * G * 1024))
    _cg(tmp_path, APP + "/liberation_job.scope", str(8 * G * 1024), str(5 * G * 1024))
    _cg(tmp_path, APP + "/bb-portero-suite-9.scope", str(20 * G * 1024), str(3 * G * 1024))
    assert po.tope_propio_kb(CLAUDE, tmp_path) is None
    assert po.tope_propio_kb(APP + "/liberation_job.scope", tmp_path) == 8 * G
    assert po.tope_propio_kb("/system.slice/docker-x.scope", tmp_path) is None
    assert po.consumo_con_tope_propio_kb(app) == 5 * G  # sin el scope del portero ni el de Claude
    assert po.consumo_con_tope_propio_kb(tmp_path / "no-existe") is None
    assert po.lee_slice(app) == (42 * G, 30 * G)
    assert po.lee_slice(tmp_path / APP.lstrip("/") / "app-com.anthropic.Claude-1.scope") == (None, None)


@pytest.mark.unit
def test_lee_psi(tmp_path):
    f = tmp_path / "memory"
    f.write_text("some avg10=1.00 avg60=0 avg300=0 total=1\nfull avg10=7.25 avg60=0 avg300=0 total=1\n", encoding="utf-8")
    assert po.lee_psi(f) == 7.25
    assert po.lee_psi(tmp_path / "nada") is None


# --- Cola compartida de `run` -------------------------------------------------------------------------------


@pytest.mark.unit
def test_turno_espera_mientras_la_puerta_esta_cerrada_y_lanza_al_abrirse(tmp_path):
    fx = po.Efectos(log=tmp_path / "p.jsonl", cola=tmp_path / "cola")
    pid = os.getpid()
    lecturas = iter([estado(psi=20.0), estado(psi=20.0), estado(psi=0.0)])

    def fuente():
        e = next(lecturas)
        procs = {pid: object()}
        return e, po._peticiones(procs, time.time(), fx.cola)

    esperas = []
    acc = po.turno(pid, "suite", fuente, lambda: esperas.append(1), fx)
    assert acc.tipo == "admitir" and len(esperas) == 2
    assert json.loads((fx.cola / f"{pid}.json").read_text(encoding="utf-8"))["concedido"] is True
    eventos = [json.loads(x) for x in fx.log.read_text(encoding="utf-8").splitlines()]
    assert [e["accion"] for e in eventos] == ["esperar", "turno"]  # la espera se registra una vez, no en cada vuelta


@pytest.mark.unit
def test_peticion_concedida_ocupa_turno_para_el_demonio(tmp_path):
    cola = tmp_path / "cola"
    cola.mkdir()
    (cola / "7.json").write_text(json.dumps({"pid": 7, "clase": "suite", "ts": time.time(), "concedido": True}), encoding="utf-8")
    (cola / "8.json").write_text(json.dumps({"pid": 8, "clase": "suite", "ts": time.time()}), encoding="utf-8")  # pid muerto
    virtuales = po._peticiones({7: object()}, time.time(), cola)
    assert [(a.raiz, a.nuestro, a.virtual) for a in virtuales] == [(7, True, False)]
    assert tipos(po.decide([*virtuales, arbol(1, 60)], estado())) == {(1, "congelar")}


@pytest.mark.unit
def test_aplica_registra_no_actua_una_vez_con_medicion_no_colectada(tmp_path):
    fx = po.Efectos(log=tmp_path / "p.jsonl", ejecutar=lambda a: pytest.fail("no debe ejecutar nada"))
    e = estado(psi=None)
    ultimo = {}
    for _ in range(3):
        po.aplica(po.decide([arbol(1, 60)], e), [arbol(1, 60)], e, fx, ultimo)
    eventos = [json.loads(x) for x in fx.log.read_text(encoding="utf-8").splitlines()]
    assert len(eventos) == 1 and eventos[0]["medicion"]["psi_full_avg10"] == "NOT_COLLECTED"


@pytest.mark.unit
def test_aplica_lleva_el_origen_de_la_costura(tmp_path):
    fx = po.Efectos(log=tmp_path / "p.jsonl", origen=lambda pid: {"lanzo": f"sesion-{pid}"})
    ev = po.aplica([po.Accion("no_actua", "fuera de app.slice", 5, "suite")], [], estado(), fx)
    assert ev[0]["origen"] == {"lanzo": "sesion-5"}
    assert po.origen_no_integrado(5)["estado"] == "NOT_COLLECTED"


# --- Interruptor del demonio (DEBT-PORTERO-IGNORA-SU-INTERRUPTOR-01) -----------------------------------------


EFECTOS = po.Efectos  # la clase real: los tests de abajo sustituyen `po.Efectos` por una fabrica


def _mundo_congelable(tmp_path, monkeypatch, modo):
    """Un arbol pesado con PSI alto (decide: congelar), /proc y cgroups falsos, un systemd falso y el interruptor."""
    datos = tmp_path / "datos"
    datos.mkdir(parents=True)
    (datos / "interruptores.json").write_text(json.dumps({"esquema": "bb-interruptores/1", "modos": {"portero": modo}}),
                                              encoding="utf-8")
    monkeypatch.setenv("BLACKBOX_DATA", str(datos))
    proc, cg_raiz = tmp_path / "proc", tmp_path / "cg"
    (proc / "77").mkdir(parents=True)
    (proc / "77" / "stat").write_text("77 (pytest) S 1 " + " ".join(["0"] * 17) + " 500 0 0\n", encoding="utf-8")
    (proc / "77" / "cgroup").write_text(f"0::{CLAUDE}\n", encoding="utf-8")
    llamadas = []
    unidad = po.nombre_unidad("suite", 77)

    def ejecutar(args):
        llamadas.append(args)
        if args[0] == "busctl":  # systemd mueve la raiz a su scope
            (cg_raiz / APP.lstrip("/") / unidad).mkdir(parents=True)
            (proc / "77" / "cgroup").write_text(f"0::{APP}/{unidad}\n", encoding="utf-8")
            return 0, 'o "/org/freedesktop/systemd1/job/1"'
        return 0, "ActiveState=active\nResult=success\n"

    fx = EFECTOS(log=tmp_path / "portero.jsonl", cola=tmp_path / "cola", ejecutar=ejecutar, cg_raiz=cg_raiz, proc=proc)
    monkeypatch.setattr(po, "Efectos", lambda: fx)
    lecturas = []
    monkeypatch.setattr(po, "lee_estado", lambda: lecturas.append("estado") or estado(psi=po.PSI_FULL_MAX + 1))
    monkeypatch.setattr(po, "observar", lambda: lecturas.append("proc") or [arbol(77, 60, pids=(77,), inicio=500)])
    freeze = cg_raiz / APP.lstrip("/") / unidad / "cgroup.freeze"
    return fx, llamadas, lecturas, freeze


def _filas(log):
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []


@pytest.mark.unit
def test_demonio_respeta_el_interruptor(tmp_path, monkeypatch):
    import argparse

    una = argparse.Namespace(una_vez=True, contenedores=False)
    # off: ni mide (/proc, PSI, cgroups) ni actua; una sola fila que lo dice.
    fx, llamadas, lecturas, freeze = _mundo_congelable(tmp_path / "off", monkeypatch, "off")
    assert po.cmd_demonio(una) == 0
    assert lecturas == [] and llamadas == [] and not freeze.exists()
    assert [(f["accion"], f["modo"]) for f in _filas(fx.log)] == [("off", "off")]
    # observar: mide y decide lo mismo, registra lo que haria, y el ejecutor no recibe NINGUNA llamada.
    fx, llamadas, lecturas, freeze = _mundo_congelable(tmp_path / "obs", monkeypatch, "observar")
    assert po.cmd_demonio(una) == 0
    assert lecturas == ["estado", "proc"] and llamadas == [] and not freeze.exists()
    fila = _filas(fx.log)[0]
    assert (fila["accion"], fila["modo"], fila["raiz"]) == ("habria_congelar", "observar", 77) and "rc" not in fila
    # actuar (control negativo de los dos anteriores): el mismo mundo adopta en un scope y congela.
    fx, llamadas, lecturas, freeze = _mundo_congelable(tmp_path / "act", monkeypatch, "actuar")
    assert po.cmd_demonio(una) == 0
    assert [a[0] for a in llamadas] == ["busctl", "systemctl"] and freeze.read_text(encoding="utf-8") == "1"
    fila = _filas(fx.log)[0]
    assert (fila["accion"], fila["rc"]) == ("congelar", 0) and "modo" not in fila  # filas de actuar: como antes


@pytest.mark.unit
def test_demonio_relee_el_interruptor_en_cada_vuelta_y_off_no_repite_su_fila(tmp_path, monkeypatch):
    import argparse

    fx, llamadas, lecturas, freeze = _mundo_congelable(tmp_path, monkeypatch, "off")
    vueltas = []

    def dormir(_s):
        vueltas.append(1)
        if len(vueltas) == 2:  # tras dos vueltas en off, Luis pasa el interruptor a observar
            (tmp_path / "datos" / "interruptores.json").write_text(json.dumps({"modos": {"portero": "observar"}}), encoding="utf-8")
        if len(vueltas) == 4:
            raise KeyboardInterrupt

    monkeypatch.setattr(po.time, "sleep", dormir)
    with pytest.raises(KeyboardInterrupt):
        po.cmd_demonio(argparse.Namespace(una_vez=False, contenedores=False))
    # 2 vueltas off (1 fila) + 2 vueltas observar (1 fila: la repeticion del mismo motivo se suprime); nada ejecutado.
    assert [f["accion"] for f in _filas(fx.log)] == ["off", "habria_congelar"]
    assert lecturas == ["estado", "proc", "estado", "proc"] and llamadas == [] and not freeze.exists()


@pytest.mark.unit
@pytest.mark.parametrize("modo", ["off", "observar", "actuar"])
def test_fuera_de_actuar_el_demonio_descongela_solo_lo_que_congelo_el_portero(tmp_path, monkeypatch, modo):
    import argparse

    fx, llamadas, lecturas, freeze = _mundo_congelable(tmp_path, monkeypatch, modo)
    app = po.cgroup_app(raiz=fx.cg_raiz)
    previos = (("bb-portero-suite-5.scope", 1), ("bb-portero-suite-6.scope", 0), ("app-ajeno-1.scope", 1))
    for nombre, frozen in previos:
        (app / nombre).mkdir(parents=True)
        (app / nombre / "cgroup.events").write_text(f"populated 1\nfrozen {frozen}\n", encoding="utf-8")
    assert po.cmd_demonio(argparse.Namespace(una_vez=True, contenedores=False)) == 0
    escritos = [n for n, _ in previos if (app / n / "cgroup.freeze").exists()]
    filas = [f["accion"] for f in _filas(fx.log)]
    if modo == "actuar":  # control negativo: en actuar la congelacion propia es la politica, no se deshace
        assert escritos == [] and "descongelar" not in filas
    else:  # solo el scope propio congelado; ni el propio sin congelar ni el ajeno congelado
        assert escritos == ["bb-portero-suite-5.scope"]
        assert (app / "bb-portero-suite-5.scope" / "cgroup.freeze").read_text(encoding="utf-8") == "0"
        assert filas[0] == "descongelar" and _filas(fx.log)[0]["modo"] == modo and llamadas == []


# --- Prueba real: scopes desechables propios, cgroup v2 delegado ---------------------------------------------


def _delegado() -> bool:
    app = po.cgroup_app()
    return bool(shutil.which("systemd-run") and shutil.which("busctl") and os.access(app / "cgroup.procs", os.W_OK))


def _espera_evento(cg, linea):
    """cgroup.freeze es asincrono: `frozen` cambia cuando el kernel termino con todas las tareas (medido: flaky sin esto)."""
    for _ in range(40):
        if linea in (cg / "cgroup.events").read_text(encoding="utf-8"):
            return True
        time.sleep(0.05)  # blocking-sleep: sondeo acotado (2 s) de cgroup.events tras escribir cgroup.freeze -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01  # sunset-reviewed: 4.4 -- re-revisado 2026-10-16 contra 4.3 (`git log -L431,431:tests/test_portero.py bade99f4..HEAD`: 0 commits, la linea no cambio desde el release 4.3.0; la razon sigue valiendo); re-revisado 2026-10-16 contra 4.2 (`git log -L431,431:tests/test_portero.py e3b13369..HEAD`: 0 commits, la linea no cambio desde el release 4.2.0; la razon sigue valiendo); re-revisado 2026-10-16 contra 4.1 (`git log -L431,431:tests/test_portero.py 4d6d1771..HEAD`: 0 commits, la linea no cambio desde el release 4.1.0; la razon sigue valiendo); re-revisado 2026-10-15 contra 4.0 (`git log -L` c4977a8b..HEAD sobre la linea +-6: 0 commits, linea identica a la revision 4.0 c4977a8b; sigue dentro de `for _ in range(40)` de _espera_evento (techo 2 s)); re-revisado 2026-10-15 contra 3.9 (`git log -L`: ultimo cambio de la linea anterior a la revision 3.9, 9aec733f); re-revisado 2026-10-13 contra 3.5: `git blame` de la linea 304 (7280a6a4) es anterior al bump 3.5.0 (b99560e8), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.4: `git blame` de la linea 304 (095c3a35) es anterior al bump 3.4.1 (eb89c383), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.3: `git blame` de la linea 304 (b008b6ee) es anterior al bump 3.3.0 (3512a16a), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.2: `git blame` de la linea 304 (804713d5) es anterior al bump 3.2.0 (e8e5aa8d), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.1: `git blame` de la linea 304 (93850773) es anterior al bump 3.1.0 (7a5bd48b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 3.0: `git blame` de la linea 304 (92598b79) es anterior al bump 2.9.1 (ab63e2b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 2.9: `git blame` de la linea 304 (7283bfb9) no cambio desde su revision anterior; la razon sigue valiendo: revisado 2026-10-12: la congelacion termina despues de la escritura ; re-revisado 2026-10-13 contra 3.1: la linea no cambio desde 20256295 (git blame de esta linea)
    return False


@pytest.mark.integration
@pytest.mark.skipif(not _delegado(), reason="sin cgroup v2 delegado al usuario (systemd --user)")
def test_real_mover_topar_en_caliente_congelar_y_control_negativo(tmp_path):
    tag = uuid.uuid4().hex[:8]
    p = subprocess.Popen(["systemd-run", "--user", "--scope", "--quiet", f"--unit=bbtest-a-{tag}", "--", "sleep", "60"])
    h = subprocess.Popen(["systemd-run", "--user", "--scope", "--quiet", f"--unit=bbtest-h-{tag}", "--", "sleep", "60"])
    try:
        cg, cg_h = None, None
        for _ in range(50):
            cg, cg_h = po._cg_de(p.pid), po._cg_de(h.pid)
            if cg and cg.endswith(f"bbtest-a-{tag}.scope") and cg_h and cg_h.endswith(f"bbtest-h-{tag}.scope"):
                break
            time.sleep(0.05)  # blocking-sleep: espera a que systemd ponga el pid en su scope -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01  # sunset-reviewed: 4.4 -- re-revisado 2026-10-16 contra 4.3 (`git log -L447,447:tests/test_portero.py bade99f4..HEAD`: 0 commits, la linea no cambio desde el release 4.3.0; la razon sigue valiendo); re-revisado 2026-10-16 contra 4.2 (`git log -L447,447:tests/test_portero.py e3b13369..HEAD`: 0 commits, la linea no cambio desde el release 4.2.0; la razon sigue valiendo); re-revisado 2026-10-16 contra 4.1 (`git log -L447,447:tests/test_portero.py 4d6d1771..HEAD`: 0 commits, la linea no cambio desde el release 4.1.0; la razon sigue valiendo); re-revisado 2026-10-15 contra 4.0 (`git log -L` c4977a8b..HEAD sobre la linea +-6: 0 commits, linea identica a la revision 4.0 c4977a8b; sigue dentro de `for _ in range(50)` que espera ambos scopes); re-revisado 2026-10-15 contra 3.9 (`git log -L`: ultimo cambio de la linea anterior a la revision 3.9, 9aec733f); re-revisado 2026-10-13 contra 3.5: `git blame` de la linea 320 (7280a6a4) es anterior al bump 3.5.0 (b99560e8), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.4: `git blame` de la linea 320 (095c3a35) es anterior al bump 3.4.1 (eb89c383), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.3: `git blame` de la linea 320 (b008b6ee) es anterior al bump 3.3.0 (3512a16a), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.2: `git blame` de la linea 320 (804713d5) es anterior al bump 3.2.0 (e8e5aa8d), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.1: `git blame` de la linea 320 (93850773) es anterior al bump 3.1.0 (7a5bd48b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 3.0: `git blame` de la linea 320 (92598b79) es anterior al bump 2.9.1 (ab63e2b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 2.9: `git blame` de la linea 320 (7283bfb9) no cambio desde su revision anterior; la razon sigue valiendo: revisado 2026-10-12: sondeo acotado a 2.5 s de un scope desechable propio ; re-revisado 2026-10-13 contra 3.1: la linea no cambio desde 20256295 (git blame de esta linea)
        assert cg and cg.endswith(f"bbtest-a-{tag}.scope"), cg
        assert cg_h and cg_h.endswith(f"bbtest-h-{tag}.scope"), cg_h
        a = po.Arbol(raiz=p.pid, clase="suite", rss_kb=1, procesos=1, edad_s=1, cgroup=cg, pids=(p.pid,))
        topes = {"MemoryMax": 64 * 1024 * 1024, "MemoryHigh": 60 * 1024 * 1024, "MemorySwapMax": 0, "TasksMax": 8}
        fx = po.Efectos(log=tmp_path / "p.jsonl", cola=tmp_path / "cola")
        ev = po.aplica([po.Accion("congelar", "prueba", p.pid, "suite", topes=topes)], [a], estado(), fx)
        assert ev[0]["rc"] == 0, ev[0]["salida"]
        nuevo = po._cg_de(p.pid)
        assert nuevo is not None
        destino = po.CGROUP_RAIZ / nuevo.lstrip("/")
        assert Path(nuevo).name == po.nombre_unidad("suite", p.pid)
        assert (destino / "memory.max").read_text(encoding="utf-8").strip() == str(64 * 1024 * 1024)
        assert (destino / "memory.swap.max").read_text(encoding="utf-8").strip() == "0"
        assert (destino / "pids.max").read_text(encoding="utf-8").strip() == "8"
        assert _espera_evento(destino, "frozen 1")
        congelado = replace(a, cgroup=nuevo, unidad=Path(nuevo).name, congelado=True)
        po.aplica([po.Accion("descongelar", "prueba", p.pid, "suite")], [congelado], estado(), fx)
        assert _espera_evento(destino, "frozen 0")
        r = subprocess.run(["systemctl", "--user", "set-property", "--runtime", Path(nuevo).name, "MemoryMax=32M"],
                           capture_output=True, text=True, check=False)
        assert r.returncode == 0 and (destino / "memory.max").read_text(encoding="utf-8").strip() == str(32 * 1024 * 1024)
        # Mover dentro de lo delegado funciona (a otro scope propio); fuera (system.slice, user-1000.slice) se niega.
        assert po.mueve_pid(p.pid, po.CGROUP_RAIZ / cg_h.lstrip("/")) == ""
        assert po._cg_de(p.pid) == cg_h
        for fuera in ("system.slice", "user.slice/user-1000.slice"):
            err = po.mueve_pid(p.pid, po.CGROUP_RAIZ / fuera)
            assert err.startswith("PermissionError"), (fuera, err)
        assert po._cg_de(p.pid) == cg_h
    finally:
        for x in (p, h):
            x.kill()
            x.wait(timeout=10)
        subprocess.run(["systemctl", "--user", "reset-failed", po.nombre_unidad("suite", p.pid), f"bbtest-a-{tag}.scope",
                        f"bbtest-h-{tag}.scope"],
                       capture_output=True, check=False)


# --- Contenedores (docker.slice) -------------------------------------------------------------------------------


def _ct(nombre, tope: int | None = None, pico: int | None = 1 * G):
    return po.Contenedor(nombre, tope, pico)


@pytest.mark.unit
def test_contenedor_sin_tope_se_acota_con_el_reparto_medido():
    conts = [_ct("pg", tope=2 * G, pico=1 * G), _ct("libre", pico=1 * G), _ct("otro", pico=3 * G)]
    acc = {a.objetivo: a for a in po.decide_contenedores(conts, 14 * G)}
    assert acc["libre"].tipo == "acotar" and acc["libre"].topes["MemoryMax"] == (14 - 2 - 3) * G * 1024
    assert acc["libre"].topes["MemorySwapMax"] == 0
    assert acc["pg"].tipo == "no_actua" and "tope propio" in acc["pg"].motivo


@pytest.mark.unit
def test_contenedor_con_tope_propio_o_excluido_no_se_toca():
    conts = [_ct("nemotron-server"), _ct("x", tope=75 * G)]
    assert {a.tipo for a in po.decide_contenedores(conts, 14 * G)} == {"no_actua"}


@pytest.mark.unit
def test_contenedor_cuyo_reparto_no_cubre_su_pico_no_se_acota():
    # Caso medido el 2026-10-12: el pico de un contenedor con tope mayor que el slice (vLLM) ya llena docker.slice.
    conts = [_ct("vllm", tope=75 * G, pico=12 * G), _ct("libre", pico=1 * G)]
    acc = {a.objetivo: a for a in po.decide_contenedores(conts, 14 * G)}
    assert acc["libre"].tipo == "acotar"
    conts = [_ct("vllm", tope=75 * G, pico=13 * G + 512 * 1024), _ct("libre", pico=1 * G)]
    acc = {a.objetivo: a for a in po.decide_contenedores(conts, 14 * G)}
    assert acc["libre"].tipo == "no_actua" and "mataria" in acc["libre"].motivo


@pytest.mark.unit
def test_contenedores_sin_medir_no_actua():
    assert po.decide_contenedores(None, 14 * G)[0].motivo.startswith("NOT_COLLECTED")
    assert po.decide_contenedores([_ct("a")], None)[0].motivo.startswith("NOT_COLLECTED")
    acc = po.decide_contenedores([_ct("a"), _ct("b", pico=None)], 14 * G)
    assert {a.tipo for a in acc} == {"no_actua"}


@pytest.mark.unit
def test_aplica_contenedores_solo_ejecuta_docker_update_con_aplicar(tmp_path):
    llamadas = []

    def ejecutar(args):
        llamadas.append(args)
        return 0, ""

    fx = po.Efectos(log=tmp_path / "p.jsonl", ejecutar=ejecutar)
    acc = po.decide_contenedores([_ct("libre")], 14 * G)
    assert po.aplica_contenedores(acc, fx)[0]["accion"] == "acotaria" and llamadas == []
    po.aplica_contenedores(acc, fx, aplicar=True)
    b = str(14 * G * 1024)  # solo: todo el slice
    assert llamadas == [["docker", "update", "--memory", b, "--memory-swap", b, "libre"]]


@pytest.mark.unit
def test_observar_contenedores_lee_su_cgroup(tmp_path):
    cid = "a" * 64
    _cg(tmp_path, f"docker.slice/docker-{cid}.scope", "max")
    (tmp_path / f"docker.slice/docker-{cid}.scope/memory.peak").write_text("2048\n", encoding="utf-8")
    assert po.observar_contenedores(lambda a: (0, f"{cid} libre\n"), tmp_path) == [po.Contenedor("libre", None, 2)]
    assert po.observar_contenedores(lambda a: (1, "sin docker"), tmp_path) is None
    assert po.observar_contenedores(lambda a: (0, f"{'b' * 64} perdido\n"), tmp_path) is None


# --- Drop-in por prefijo: tope de creacion de los scopes de la app ---------------------------------------------

DROPIN = Path(__file__).resolve().parents[1] / "systemd/app-com.anthropic.Claude-.scope.d/50-bb-portero.conf"


def _scope_desechable(unidad):
    p = subprocess.Popen(["systemd-run", "--user", "--scope", "--quiet", f"--unit={unidad}", "--", "sleep", "60"])
    cg = None
    for _ in range(50):
        cg = po._cg_de(p.pid)
        if cg and cg.endswith(f"{unidad}.scope"):
            break
        time.sleep(0.05)  # blocking-sleep: espera a que systemd ponga el pid en su scope -- DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01  # sunset-reviewed: 4.4 -- re-revisado 2026-10-16 contra 4.3 (`git log -L564,564:tests/test_portero.py bade99f4..HEAD`: 0 commits, la linea no cambio desde el release 4.3.0; la razon sigue valiendo); re-revisado 2026-10-16 contra 4.2 (`git log -L564,564:tests/test_portero.py e3b13369..HEAD`: 0 commits, la linea no cambio desde el release 4.2.0; la razon sigue valiendo); re-revisado 2026-10-16 contra 4.1 (`git log -L564,564:tests/test_portero.py 4d6d1771..HEAD`: 0 commits, la linea no cambio desde el release 4.1.0; la razon sigue valiendo); re-revisado 2026-10-15 contra 4.0 (`git log -L` c4977a8b..HEAD sobre la linea +-6: 0 commits, linea identica a la revision 4.0 c4977a8b; sigue dentro de `for _ in range(50)` de _scope_desechable); re-revisado 2026-10-15 contra 3.9 (`git log -L`: ultimo cambio de la linea anterior a la revision 3.9, 9aec733f); re-revisado 2026-10-13 contra 3.5: `git blame` de la linea 437 (7280a6a4) es anterior al bump 3.5.0 (b99560e8), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.4: `git blame` de la linea 437 (095c3a35) es anterior al bump 3.4.1 (eb89c383), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.3: `git blame` de la linea 437 (b008b6ee) es anterior al bump 3.3.0 (3512a16a), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.2: `git blame` de la linea 437 (804713d5) es anterior al bump 3.2.0 (e8e5aa8d), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-13 contra 3.1: `git blame` de la linea 437 (93850773) es anterior al bump 3.1.0 (7a5bd48b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 3.0: `git blame` de la linea 437 (92598b79) es anterior al bump 2.9.1 (ab63e2b), la linea no cambio desde su revision anterior; la razon sigue valiendo: re-revisado 2026-10-12 contra 2.9: `git blame` de la linea 437 (7283bfb9) no cambio desde su revision anterior; la razon sigue valiendo: revisado 2026-10-12: sondeo acotado a 2.5 s de un scope desechable propio ; re-revisado 2026-10-13 contra 3.1: la linea no cambio desde 20256295 (git blame de esta linea)
    return p, cg


@pytest.mark.integration
@pytest.mark.skipif(not _delegado(), reason="sin cgroup v2 delegado al usuario (systemd --user)")
def test_real_carrera_pid_que_sale_al_adoptar_el_rc_dice_lo_que_systemd_dejo(tmp_path):
    """DEBT-PORTERO-ADOPCION-CHOCA-CON-PIDS-QUE-SALEN-01 con systemd de verdad: un hijo que sale milisegundos despues
    de pedir la adopcion deja a veces la unidad `failed` (Result=resources) con la raiz YA dentro del cgroup (medido
    2026-10-14: 17 de 100 intentos llamando a crea_scope directo). El rc registrado tiene que coincidir con lo que systemd dejo, en los dos sentidos."""
    vistos = {"failed": 0, "active": 0}
    unidades = []
    topes = {"MemoryMax": 64 * 1024 * 1024, "MemoryHigh": 60 * 1024 * 1024, "MemorySwapMax": 0, "TasksMax": 8}
    try:
        for intento in range(60):
            if vistos["failed"] and vistos["active"]:
                break
            vivo = subprocess.Popen(["sleep", "30"])
            corto = subprocess.Popen(["sleep", f"{0.002 * (1 + intento % 8):.3f}"])

            def ejecutar(args, corto=corto):
                r = po._ejecuta(args)
                if args[0] == "busctl":
                    corto.wait(timeout=10)  # el hijo sale Y se recoge entre la llamada y el attach (un zombi no basta)
                return r

            try:
                p = po._lee_proc(Path("/proc") / str(vivo.pid))
                assert p is not None
                a = po.Arbol(raiz=vivo.pid, clase="suite", rss_kb=1, procesos=2, edad_s=1, cgroup=p.cgroup,
                             pids=(vivo.pid, corto.pid), inicio=p.inicio)
                unidades.append(po.nombre_unidad("suite", vivo.pid))
                fx = po.Efectos(log=tmp_path / "p.jsonl", cola=tmp_path / "cola", ejecutar=ejecutar)
                ev = po.aplica([po.Accion("admitir", "prueba", vivo.pid, "suite", topes=topes)], [a], estado(), fx)[0]
                corto.wait(timeout=10)
                real = subprocess.run(["systemctl", "--user", "show", unidades[-1], "-p", "ActiveState", "--value"],
                                      capture_output=True, text=True, check=False).stdout.strip()
                assert (ev.get("rc") == 0) == (real == "active"), (real, ev)  # el rc dice lo que systemd dejo
                if real == "failed":
                    assert ev.get("rc") == 1 and "Result=resources" in ev["salida"], ev
                vistos["active" if real == "active" else "failed"] += 1
            finally:
                vivo.kill()
                vivo.wait(timeout=10)
    finally:
        subprocess.run(["systemctl", "--user", "reset-failed", *unidades], capture_output=True, check=False)
    if not vistos["failed"]:
        pytest.skip(f"COULD_NOT_RUN: la carrera no se reprodujo en 60 intentos ({vistos}); la rama failed quedo sin medir")
    assert vistos["active"], vistos  # control: la misma prueba tambien ve adopciones sanas con rc=0


@pytest.mark.integration
@pytest.mark.skipif(not _delegado(), reason="sin cgroup v2 delegado al usuario (systemd --user)")
def test_real_dropin_por_prefijo_topa_el_scope_al_crearse_y_no_a_otro():
    tag = uuid.uuid4().hex[:8]
    d = Path.home() / f".config/systemd/user/app-bbprobe{tag}-.scope.d"
    d.mkdir(parents=True)
    procs = []
    try:
        (d / "50-bb-portero.conf").write_text(DROPIN.read_text(encoding="utf-8"), encoding="utf-8")
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True, timeout=60)
        leidos = {}
        for unidad in (f"app-bbprobe{tag}-1", f"app-bbotro{tag}-1"):
            p, cg = _scope_desechable(unidad)
            procs.append(p)
            assert cg and cg.endswith(f"{unidad}.scope"), cg
            base = po.CGROUP_RAIZ / cg.lstrip("/")
            leidos[unidad] = tuple((base / f).read_text(encoding="utf-8").strip() for f in ("memory.max", "pids.max"))
        assert leidos[f"app-bbprobe{tag}-1"] == (str(35 * 1024**3), "1230")
        assert leidos[f"app-bbotro{tag}-1"][0] == "max"  # control negativo: sin el prefijo no hay tope
    finally:
        for p in procs:
            p.kill()
            p.wait(timeout=10)
        shutil.rmtree(d, ignore_errors=True)
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False, timeout=60)


def test_portero_como_script_cae_al_import_plano_de_interruptores(monkeypatch):
    """`bb portero` corre el archivo con tools/ en sys.path (no la raiz del repo): `from tools import ...` falla y se usa `import interruptores`."""
    import builtins
    import runpy

    script = Path(po.__file__)
    monkeypatch.syspath_prepend(str(script.parent))
    original_import = builtins.__import__

    def sin_paquete_tools(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "tools" and "interruptores" in (fromlist or ()):
            raise ImportError("fixture: la raiz del repo no esta en sys.path")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", sin_paquete_tools)
    ns = runpy.run_path(str(script), run_name="portero_import_probe")
    assert ns["interruptores"].__name__ == "interruptores"  # el modulo plano, no `tools.interruptores`
    assert ns["interruptores"] is not po.interruptores
    assert callable(ns["observar"]) and ns["NOMBRE"] == "portero"


def test_peticiones_con_la_cola_ilegible_devuelve_vacio_sin_propagar(tmp_path):
    class ColaDenegada(type(tmp_path)):
        def glob(self, _patron):
            raise PermissionError("cola denegada")

    assert po._peticiones({os.getpid(): object()}, time.time(), ColaDenegada(tmp_path)) == []
    # control: la misma llamada con una cola real que contiene una peticion viva SI devuelve un arbol
    (tmp_path / "1.json").write_text(json.dumps({"pid": os.getpid(), "clase": "suite", "ts": 1.0}), encoding="utf-8")
    vivas = po._peticiones({os.getpid(): object()}, time.time(), tmp_path)
    assert len(vivas) == 1
