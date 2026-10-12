"""El escalon de bin/bb-usable: matar UN trabajo desbocado antes de reiniciar la maquina.

DEBT-COLAPSOS-11-OCT-SUITES-PYTEST-SIN-TECHO-01. Este es el unico camino de bb-usable que manda una
senal a un proceso, y su fallo es silencioso en las dos direcciones: si mata de mas, se lleva el trabajo
de alguien sin que la maquina lo necesitara; si no mata, la maquina reinicia como antes y nadie nota que
el escalon no hizo nada. Por eso cada rama tiene un caso que DEBE matar y otro que NO.

La decision (`decidir_escalon`, `matar_en_grupo`) es pura y se prueba con muestras construidas. La
lectura de cgroup y /proc se prueba contra arboles falsos. Y UN control real: un acaparador de 300 MB en
un scope `systemd-run --user --scope -p MemoryMax=1G -p MemorySwapMax=0` que el escalon elige y mata
de verdad, junto a un senuelo protegido de 350 MB que NO toca. Nada aqui pasa de 1 GB.
"""

from __future__ import annotations

import importlib.machinery as machinery
import importlib.util as util
import json
import os
import shutil
import signal
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parent.parent / "bin" / "bb-usable"


def _cargar():
    loader = machinery.SourceFileLoader("bb_usable_escalon", str(RUTA))
    spec = util.spec_from_loader("bb_usable_escalon", loader)
    assert spec is not None
    mod = util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture
def bbu(tmp_path, monkeypatch):
    mod = _cargar()
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path / "datos"))
    (tmp_path / "sin-proc").mkdir()
    monkeypatch.setattr(mod, "CGROUP_ROOT", tmp_path / "sin-cgroup")
    monkeypatch.setattr(mod, "PROC_ROOT", tmp_path / "sin-proc")
    return mod


SLICE = "/cg/user.slice/user-1000.slice/user@1000.service/app.slice"
GIB = 1024 ** 3


def _slice(bbu, fraccion, ruta=SLICE):
    return bbu.SliceApp(ruta, int(fraccion * 42 * GIB), 42 * GIB)


def _proc(bbu, pid, comm, rss_gib, **kw):
    """uid, pgid, scope y slice_ruta por palabra clave; por defecto, un proceso de usuario en un scope."""
    return bbu.Proc(pid, kw.get("pgid") or pid, comm, kw.get("uid", 1000), int(rss_gib * 1048576),
                    1000 + pid, kw.get("scope", "app-com.anthropic.Claude-9.scope"),
                    kw.get("slice_ruta", SLICE))


def _muestra(bbu, **kw):
    """psi, fraccion, candidatos y slices por palabra clave; por defecto el colapso de las 22:44."""
    slices = kw.get("slices") or (_slice(bbu, kw.get("fraccion", 0.93)),)
    candidatos = kw.get("candidatos") or (_proc(bbu, 10, "claude", 6), _proc(bbu, 20, "python3", 26),
                                          _proc(bbu, 30, "pytest", 2))
    return bbu.MuestraEscalon(1000.0, kw.get("psi", 50.0), slices, candidatos, 99999, 99999)


def _sostenido(bbu, segundos=60.0, ultima_muerte=None):
    return bbu.EstadoEscalon(alto_desde=1000.0 - segundos, ultima_muerte=ultima_muerte)


# ============================================================ casos que DEBEN matar


def test_DEBE_matar_al_mayor_no_protegido_con_psi_sostenido_y_slice_lleno(bbu):
    """El colapso de las 22:44 del 2026-10-11: un python3 de 26 GB junto a varios `claude` de 6 GB."""
    d = bbu.decidir_escalon(_muestra(bbu), _sostenido(bbu))
    assert d.accion == "matar" and d.condicion
    assert d.objetivo.pid == 20 and d.objetivo.comm == "python3"
    assert d.estado.ultima_muerte == 1000.0, "la muerte arranca el enfriamiento"


def test_DEBE_matar_justo_en_el_borde_de_60s_y_del_90(bbu):
    # 90 de 100 exacto: int(0.90 * 42 GiB) trunca por debajo del 90 % y el borde no se mediria.
    exacto = (bbu.SliceApp(SLICE, 90, 100),)
    d = bbu.decidir_escalon(_muestra(bbu, slices=exacto), _sostenido(bbu, 60.0))
    assert d.accion == "matar"


def test_DEBE_matar_al_terminar_el_enfriamiento(bbu):
    d = bbu.decidir_escalon(_muestra(bbu), _sostenido(bbu, ultima_muerte=1000.0 - 300.0))
    assert d.accion == "matar"


# ============================================================ casos que NO


def test_NO_mata_con_psi_alta_y_slice_bajo(bbu):
    """27 de las 37 muestras con PSI >= 10 desde el 09-28 tenian app.slice por debajo del 90 %."""
    d = bbu.decidir_escalon(_muestra(bbu, fraccion=0.75), _sostenido(bbu))
    assert d.accion == "nada" and not d.condicion
    assert "por debajo de 90%" in d.motivo


def test_NO_mata_con_slice_alto_y_psi_baja(bbu):
    """1483 muestras con app.slice >= 90 % y PSI < 10; el 2026-10-12 estaba al 90.9 % con PSI 0.00."""
    d = bbu.decidir_escalon(_muestra(bbu, psi=5.0, fraccion=0.95), _sostenido(bbu))
    assert d.accion == "nada" and not d.condicion
    assert d.estado.alto_desde is None, "una lectura baja reinicia el reloj del escalon"


def test_NO_mata_antes_de_60s_sostenidos(bbu):
    d = bbu.decidir_escalon(_muestra(bbu), _sostenido(bbu, 59.0))
    assert d.accion == "nada" and "< 60s" in d.motivo


def test_la_primera_lectura_alta_arranca_el_reloj_y_no_mata(bbu):
    d = bbu.decidir_escalon(_muestra(bbu), bbu.EstadoEscalon())
    assert d.accion == "nada" and d.estado.alto_desde == 1000.0


def test_NO_mata_si_solo_hay_protegidos(bbu):
    cands = (_proc(bbu, 10, "claude", 6), _proc(bbu, 11, "node", 9), _proc(bbu, 12, "claude-desktop", 3),
             _proc(bbu, 13, "python3", 20, uid=0), _proc(bbu, 1, "python3", 30),
             _proc(bbu, 99999, "python3", 30), _proc(bbu, 14, "python3", 30, scope=None))
    d = bbu.decidir_escalon(_muestra(bbu, candidatos=cands), _sostenido(bbu))
    assert d.accion == "nada" and d.condicion
    assert "solo procesos protegidos" in d.motivo


def test_NO_mata_dentro_del_enfriamiento(bbu):
    d = bbu.decidir_escalon(_muestra(bbu), _sostenido(bbu, ultima_muerte=1000.0 - 299.0))
    assert d.accion == "nada" and d.condicion and "enfriamiento" in d.motivo
    assert d.estado.ultima_muerte == 1000.0 - 299.0


def test_NO_mata_con_cgroup_ilegible_falla_cerrado(bbu):
    m = bbu.MuestraEscalon(1000.0, 50.0, None, (), 99999, 99999)
    d = bbu.decidir_escalon(m, _sostenido(bbu))
    assert d.accion == "nada" and "ilegible" in d.motivo


def test_NO_mata_con_proc_ilegible_falla_cerrado(bbu):
    m = bbu.MuestraEscalon(1000.0, 50.0, (_slice(bbu, 0.95),), None, 99999, 99999)
    d = bbu.decidir_escalon(m, _sostenido(bbu))
    assert d.accion == "nada" and d.condicion and "ilegible" in d.motivo


def test_NO_mata_con_psi_ilegible_y_reinicia_el_reloj(bbu):
    d = bbu.decidir_escalon(_muestra(bbu, psi=None), _sostenido(bbu))
    assert d.accion == "nada" and d.estado.alto_desde is None


def test_NO_mata_un_slice_sin_techo(bbu):
    sin_techo = (bbu.SliceApp(SLICE, 41 * GIB, None),)
    d = bbu.decidir_escalon(_muestra(bbu, slices=sin_techo), _sostenido(bbu))
    assert d.accion == "nada" and "sin techo" in d.motivo


def test_NO_elige_procesos_de_un_slice_que_no_esta_lleno(bbu):
    otro = "/cg/user.slice/user-1001.slice/user@1001.service/app.slice"
    slices = (_slice(bbu, 0.95), bbu.SliceApp(otro, 10 * GIB, 42 * GIB))
    cands = (_proc(bbu, 20, "python3", 2), _proc(bbu, 21, "python3", 30, slice_ruta=otro))
    d = bbu.decidir_escalon(_muestra(bbu, slices=slices, candidatos=cands), _sostenido(bbu))
    assert d.objetivo.pid == 20, "el de 30 GB vive en un slice al 24 %: no es el problema"


# ============================================================ el grupo


def test_grupo_entero_cuando_todo_el_grupo_es_matable(bbu):
    obj = _proc(bbu, 20, "python3", 26, pgid=20)
    miembros = (obj, _proc(bbu, 21, "bash", 0.01, pgid=20), _proc(bbu, 22, "python3", 3, pgid=20))
    en_grupo, motivo = bbu.matar_en_grupo(obj, miembros, 99999, 99999)
    assert en_grupo, motivo


def test_solo_el_pid_si_el_grupo_incluye_un_protegido(bbu):
    obj = _proc(bbu, 20, "python3", 26, pgid=20)
    miembros = (obj, _proc(bbu, 10, "claude", 6, pgid=20))
    en_grupo, motivo = bbu.matar_en_grupo(obj, miembros, 99999, 99999)
    assert not en_grupo and "claude" in motivo


def test_solo_el_pid_si_el_grupo_incluye_algo_fuera_del_scope(bbu):
    obj = _proc(bbu, 20, "python3", 26, pgid=20)
    miembros = (obj, _proc(bbu, 23, "python3", 1, pgid=20, scope=None))
    assert not bbu.matar_en_grupo(obj, miembros, 99999, 99999)[0]


def test_solo_el_pid_si_el_grupo_es_el_propio_o_ilegible(bbu):
    obj = _proc(bbu, 20, "python3", 26, pgid=777)
    assert not bbu.matar_en_grupo(obj, (obj,), 99999, 777)[0]
    assert not bbu.matar_en_grupo(obj, None, 99999, 99999)[0]


# ============================================================ el escalon no toca el latido


def _correr(bbu, monkeypatch, serie, paso):
    caricias = []
    monkeypatch.setattr(bbu, "notify", caricias.append)
    monkeypatch.setattr(bbu, "probe", lambda: 0.001)
    monkeypatch.setattr(bbu, "latencia_x_ms", lambda: None)
    monkeypatch.setattr(bbu.time, "sleep", lambda s: None)
    monkeypatch.setattr(bbu, "paso_escalon", paso)
    monkeypatch.setattr(bbu, "origen_al_declarar_colapso", lambda s: None)
    it = iter(serie)

    def leer():
        try:
            return next(it)
        except StopIteration:
            raise SystemExit from None

    monkeypatch.setattr(bbu, "psi_memory_full_avg10", leer)
    monkeypatch.setattr(bbu.sys, "stderr", type("F", (), {
        "write": lambda _s, m: None, "flush": lambda _s: None})())
    with pytest.raises(SystemExit):
        bbu.main()
    return caricias.count("WATCHDOG=1") - 1


def test_el_escalon_corre_en_cada_vuelta_y_el_COLAPSO_sigue_igual(bbu, monkeypatch):
    """Respaldo intacto: aunque el escalon 'mate' en cada vuelta, el latido es el de siempre."""
    llamadas = []

    def paso(psi, estado, ahora=None):
        llamadas.append(psi)
        return bbu.EstadoEscalon(alto_desde=0.0, ultima_muerte=1.0)

    caricias = _correr(bbu, monkeypatch, [99.0] * 15, paso)
    assert len(llamadas) == 15, "el escalon tiene que evaluarse en CADA vuelta"
    assert caricias == bbu.PSI_ACT_SONDAS - 1, "el COLAPSO cobra igual: el escalon no lo relaja"


def test_el_COLAPSO_registra_el_origen_UNA_vez_por_declaracion(bbu, monkeypatch):
    capturas = []
    monkeypatch.setattr(bbu, "capturar_origen", lambda motivo, pids: capturas.append(motivo) or {})
    caricias = []
    monkeypatch.setattr(bbu, "notify", caricias.append)
    monkeypatch.setattr(bbu, "probe", lambda: 0.001)
    monkeypatch.setattr(bbu, "latencia_x_ms", lambda: None)
    monkeypatch.setattr(bbu.time, "sleep", lambda s: None)
    monkeypatch.setattr(bbu, "paso_escalon", lambda psi, e, ahora=None: e)
    it = iter([99.0] * 14)

    def leer():
        try:
            return next(it)
        except StopIteration:
            raise SystemExit from None

    monkeypatch.setattr(bbu, "psi_memory_full_avg10", leer)
    monkeypatch.setattr(bbu, "log", lambda m: None)
    with pytest.raises(SystemExit):
        bbu.main()
    assert capturas == ["colapso"], "una captura al declarar, no una por cada vuelta del colapso"
    assert caricias.count("WATCHDOG=1") - 1 == bbu.PSI_ACT_SONDAS - 1, "capturar no cambia el latido"


def test_un_escalon_que_revienta_no_tumba_al_vigilante(bbu, monkeypatch):
    """Una excepcion que escapara mataria bb-usable y FailureAction reiniciaria la maquina."""
    monkeypatch.setattr(bbu, "leer_slices_app", lambda: 1 / 0)
    lineas = []
    monkeypatch.setattr(bbu, "log", lineas.append)
    estado = bbu.EstadoEscalon(alto_desde=5.0)
    assert bbu.paso_escalon(50.0, estado, ahora=100.0) == estado
    assert any("ESCALON FALLO" in linea for linea in lineas)


def test_un_fallo_tras_decidir_matar_conserva_el_enfriamiento(bbu, monkeypatch):
    """Si algo revienta DESPUES de decidir, el enfriamiento no se pierde: si se perdiera, la vuelta
    siguiente volveria a matar y el escalon mataria en cascada."""
    obj = _proc(bbu, 20, "python3", 26)
    monkeypatch.setattr(bbu, "leer_slices_app", lambda: (_slice(bbu, 0.95),))
    monkeypatch.setattr(bbu, "leer_candidatos", lambda s: (obj,))
    monkeypatch.setattr(bbu, "capturar_origen", lambda motivo, pids: {"procesos": []})
    monkeypatch.setattr(bbu, "leer_grupo", lambda pgid: 1 / 0)
    monkeypatch.setattr(bbu, "log", lambda m: None)
    nuevo = bbu.paso_escalon(50.0, bbu.EstadoEscalon(alto_desde=0.0), ahora=100.0)
    assert nuevo.ultima_muerte == 100.0


# ============================================================ lectura y registro


def _arbol_cgroup(raiz: Path, actual="45000000000", techo="45097156608"):
    app = raiz / "user.slice" / "user-1000.slice" / "user@1000.service" / "app.slice"
    app.mkdir(parents=True)
    (app / "memory.current").write_text(actual + "\n", encoding="ascii")
    (app / "memory.max").write_text(techo + "\n", encoding="ascii")
    return app


def test_lee_el_slice_y_su_techo(bbu, tmp_path, monkeypatch):
    monkeypatch.setattr(bbu, "CGROUP_ROOT", tmp_path / "cg")
    _arbol_cgroup(tmp_path / "cg")
    (s,) = bbu.leer_slices_app()
    assert s.techo == 45097156608 and s.fraccion() == pytest.approx(0.9978, abs=1e-3)


def test_techo_max_es_None_y_sin_slice_es_ilegible(bbu, tmp_path, monkeypatch):
    monkeypatch.setattr(bbu, "CGROUP_ROOT", tmp_path / "cg")
    assert bbu.leer_slices_app() is None, "sin app.slice no hay lectura: None, no una lista vacia"
    app = _arbol_cgroup(tmp_path / "cg", techo="max")
    assert bbu.leer_slices_app()[0].techo is None
    (app / "memory.current").unlink()
    assert bbu.leer_slices_app() is None


def _proc_falso(raiz: Path, pid: int, comm: str, rss_paginas: int, uid: int = 1000):
    d = raiz / str(pid)
    d.mkdir(parents=True)
    campos = ["S", "1", str(pid), *(["0"] * 16), "4242", "0", str(rss_paginas)]
    (d / "stat").write_text(f"{pid} ({comm}) {' '.join(campos)}\n", encoding="ascii")
    (d / "status").write_text(f"Name:\t{comm}\nUid:\t{uid}\t{uid}\t{uid}\t{uid}\n", encoding="ascii")


def test_lee_candidatos_de_los_scopes_claude_y_declara_proc_ciego(bbu, tmp_path, monkeypatch):
    monkeypatch.setattr(bbu, "CGROUP_ROOT", tmp_path / "cg")
    monkeypatch.setattr(bbu, "PROC_ROOT", tmp_path / "proc")
    app = _arbol_cgroup(tmp_path / "cg")
    scope = app / "app-com.anthropic.Claude-1.scope"
    scope.mkdir()
    (scope / "cgroup.procs").write_text("10\n20\n", encoding="ascii")
    otro = app / "app-gnome-org.gnome.Terminal.scope"
    otro.mkdir()
    (otro / "cgroup.procs").write_text("30\n", encoding="ascii")
    _proc_falso(tmp_path / "proc", 10, "claude", 1000)
    _proc_falso(tmp_path / "proc", 20, "python3", 5000)
    _proc_falso(tmp_path / "proc", 30, "python3", 9000)
    cands = bbu.leer_candidatos(bbu.leer_slices_app())
    assert sorted(p.pid for p in cands) == [10, 20], "el terminal no es un scope Claude"
    assert all(p.scope == "app-com.anthropic.Claude-1.scope" for p in cands)
    shutil.rmtree(tmp_path / "proc")
    assert bbu.leer_candidatos(bbu.leer_slices_app()) is None, "pids sin /proc legible es ceguera, no vacio"


def test_cada_decision_se_registra_tambien_no_actuo(bbu, tmp_path):
    bbu.paso_escalon(3.0, bbu.EstadoEscalon(), ahora=1.0)
    bbu.paso_escalon(None, bbu.EstadoEscalon(), ahora=2.0)
    (f,) = (tmp_path / "datos" / "escalon").glob("*.jsonl")
    eventos = [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines()]
    assert [e["accion"] for e in eventos] == ["nada", "nada"]
    assert "PSI 3.0 < 10" in eventos[0]["motivo"] and "ilegible" in eventos[1]["motivo"]
    assert eventos[0]["slices"] is None, "cgroup ilegible queda como null, no como lista vacia"


def test_al_matar_el_evento_cita_el_origen_del_objetivo(bbu, monkeypatch):
    obj = _proc(bbu, 20, "python3", 26)
    monkeypatch.setattr(bbu, "leer_slices_app", lambda: (_slice(bbu, 0.95),))
    monkeypatch.setattr(bbu, "leer_candidatos", lambda s: (obj,))
    origen = {"pid": 20, "lanzador": {"tipo": "git_hook"}}
    monkeypatch.setattr(bbu, "capturar_origen",
                        lambda motivo, pids: {"ts": "T", "procesos": [{"pid": 1}, origen]})
    monkeypatch.setattr(bbu, "leer_grupo", lambda pgid: (obj,))
    muertes = []
    monkeypatch.setattr(bbu, "ejecutar_muerte", lambda o, g: muertes.append((o.pid, g)) or "SIGKILL")
    monkeypatch.setattr(bbu, "log", lambda m: None)
    bbu.paso_escalon(50.0, bbu.EstadoEscalon(alto_desde=0.0), ahora=100.0)
    (f,) = (Path(os.environ["BLACKBOX_DATA"]) / "escalon").glob("*.jsonl")
    ev = json.loads(f.read_text(encoding="utf-8").splitlines()[-1])
    assert muertes == [(20, True)]
    assert ev["origen_objetivo"] == origen and ev["efecto"] == "SIGKILL"


# ============================================================ control REAL, pequeno


ACAPARADOR = ("import signal\n"
              "b = bytearray({mb} * 1024 * 1024)\n"
              "for i in range(0, len(b), 4096):\n"
              "    b[i] = 1\n"
              "print('listo', flush=True)\n"
              "signal.pause()\n")


def _lanzar(nombre_scope: str, exe: str, mb: int) -> subprocess.Popen:
    p = subprocess.Popen(
        ["systemd-run", "--user", "--scope", "--quiet", f"--unit={nombre_scope}",
         "-p", "MemoryMax=1G", "-p", "MemorySwapMax=0", exe, "-c", ACAPARADOR.format(mb=mb)],
        stdout=subprocess.PIPE, text=True, start_new_session=True)
    assert p.stdout.readline().strip() == "listo"
    return p


def _psi_full_avg10() -> float:
    linea = Path("/proc/pressure/memory").read_text(encoding="ascii").splitlines()[1]
    return float(linea.split()[1].split("=")[1])


@pytest.mark.skipif(shutil.which("systemd-run") is None, reason="sin systemd-run")
def test_control_real_elige_y_mata_al_acaparador_y_no_al_senuelo_protegido(bbu, tmp_path, monkeypatch):
    """Selecciona sobre el cgroup REAL y mata de verdad, sin estresar la maquina.

    La condicion de slice lleno es sintetica (no se puede llenar app.slice sin el riesgo que esto viene a
    quitar); todo lo demas es real: los scopes se leen de /sys/fs/cgroup, los procesos de /proc, el
    grupo se reune del sistema entero y la senal es SIGKILL al grupo. Un senuelo llamado `claude`, MAS
    grande que el acaparador, prueba la lista protegida. Solo se decide sobre los dos scopes de este test:
    nunca sobre los procesos reales de la sesion.
    """
    if _psi_full_avg10() >= 5:
        pytest.skip("PSI full avg10 >= 5: no se lanza ni un acaparador pequeno con la maquina presionada")
    monkeypatch.setattr(bbu, "CGROUP_ROOT", Path("/sys/fs/cgroup"))
    monkeypatch.setattr(bbu, "PROC_ROOT", Path("/proc"))
    sufijo = uuid.uuid4().hex[:8]
    s_hog, s_senuelo = f"app-com.anthropic.Claude-bbtest{sufijo}a.scope", f"app-com.anthropic.Claude-bbtest{sufijo}b.scope"
    senuelo_exe = tmp_path / "claude"
    senuelo_exe.symlink_to(sys.executable)
    hog = _lanzar(s_hog, sys.executable, 300)
    senuelo = _lanzar(s_senuelo, str(senuelo_exe), 350)
    try:
        uid = os.getuid()
        app = f"/sys/fs/cgroup/user.slice/user-{uid}.slice/user@{uid}.service/app.slice"
        lleno = (bbu.SliceApp(app, 95, 100),)
        todos = bbu.leer_candidatos(lleno)
        assert todos is not None
        mios = tuple(p for p in todos if p.scope in (s_hog, s_senuelo))
        assert {p.pid for p in mios} == {hog.pid, senuelo.pid}, mios
        assert next(p for p in mios if p.pid == senuelo.pid).comm == "claude"

        m = bbu.MuestraEscalon(1000.0, 50.0, lleno, mios, os.getpid(), os.getpgrp())
        d = bbu.decidir_escalon(m, bbu.EstadoEscalon(alto_desde=900.0))
        assert d.accion == "matar" and d.objetivo.pid == hog.pid, d
        miembros = bbu.leer_grupo(d.objetivo.pgid)
        assert {p.pid for p in miembros} == {hog.pid}, miembros
        en_grupo, motivo = bbu.matar_en_grupo(d.objetivo, miembros, os.getpid(), os.getpgrp())
        assert en_grupo, motivo
        assert bbu.ejecutar_muerte(d.objetivo, en_grupo) == f"SIGKILL al grupo {hog.pid}"
        assert hog.wait(timeout=10) == -signal.SIGKILL
        assert senuelo.poll() is None, "el senuelo protegido tiene que seguir vivo"

        # Control negativo sobre el mismo cgroup real: sin el acaparador solo queda el protegido.
        restantes = tuple(p for p in bbu.leer_candidatos(lleno) if p.scope in (s_hog, s_senuelo))
        d2 = bbu.decidir_escalon(bbu.MuestraEscalon(1000.0, 50.0, lleno, restantes, os.getpid(),
                                                    os.getpgrp()), bbu.EstadoEscalon(alto_desde=900.0))
        assert d2.accion == "nada" and "protegidos" in d2.motivo, d2
    finally:
        for p in (hog, senuelo):
            if p.poll() is None:
                p.kill()
            p.wait(timeout=10)


def test_ejecutar_muerte_no_mata_un_pid_que_cambio_de_identidad(bbu, tmp_path, monkeypatch):
    """Entre leer y matar, el pid pudo morir y reciclarse: se comprueba el starttime antes de la senal."""
    p = subprocess.Popen([sys.executable, "-c", "import signal; signal.pause()"])
    try:
        monkeypatch.setattr(bbu, "PROC_ROOT", Path("/proc"))
        real = bbu._leer_proc(p.pid, "s", "x")
        impostor = bbu.Proc(real.pid, real.pgid, real.comm, real.uid, real.rss_kb, real.inicio + 1, "s", "x")
        assert "cambio de identidad" in bbu.ejecutar_muerte(impostor, False)
        with pytest.raises(subprocess.TimeoutExpired):
            p.wait(timeout=0.5)  # una senal mal enviada lo habria terminado: wait volveria
    finally:
        p.kill()
        p.wait(timeout=10)
