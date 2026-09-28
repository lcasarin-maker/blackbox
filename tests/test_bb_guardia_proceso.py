"""Cobertura de bin/bb-guardia-proceso -- el vigilante que frena a UN proceso
individual antes de que tumbe la maquina entera.

## Por que existe

Nace de DEBT-PROCESO-SIN-TECHO-TUMBO-LA-MAQUINA-DOS-VECES: dos reinicios
forzados el 2026-09-28 (03:39:21 y 04:27:29), los dos por un solo `python3`
creciendo sin freno hasta 30+ GiB bajo un scope de Claude Desktop. Ninguna
capa existente (app.slice, earlyoom, memory.low) esta disenada para frenar un
proceso individual -- solo `bb cap`, que es opt-in.

## Por que hay una escalada, y no un SIGKILL directo

Decision de Luis, 2026-09-28: matar sin avisar era demasiado brusco. La
escalada de tres pasos (AVISO -> SIGTERM -> SIGKILL) le da al proceso, y a
quien lo lanzo, dos oportunidades de pararse solo antes del ultimo recurso.
SIGTERM es la parte "no destructiva": un proceso bien portado la atrapa y
sale limpio. Este demonio NO puede mandarle un mensaje a la SESION de Claude
que lo lanzo -- corre fuera del framework de agentes, sin ese canal -- y eso
se dice en el docstring de bin/bb-guardia-proceso en vez de fingir que existe.

## Lo que estos tests prueban, y lo que NO pueden probar

`procesar_muestra()` es pura funcion de datos -> estado -> veredicto, sin
tocar `/proc` ni matar nada: por eso se puede REPRODUCIR el timeline exacto
de los dos incidentes reales (los numeros de `top_rss` que `bb` ya grabo esa
madrugada) y verificar que el guardian los habria cazado, sin necesidad de
provocar un colapso de verdad. Mismo principio que bb-usable ya declara para
su propio camino de accion: se ejercita de verdad, no se argumenta.

Lo que NO prueban: si 4 GiB/muestra y 16 GiB son los numeros correctos para
CUALQUIER carga futura, ni si la escalada habria alcanzado SIGKILL en el
incidente real -- los datos del colapso 1 se cortan en la cuarta muestra
(el reinicio se llevo la telemetria posterior), asi que el replay de abajo
solo puede probar hasta donde el propio incidente dejo evidencia: AVISO y
SIGTERM, no el paso final. Calibrado contra DOS incidentes, no contra un
corpus de miles de muestras sanas como el PSI de bb-usable.
"""

from __future__ import annotations

import importlib.machinery as machinery
import importlib.util as util
import json
import os
import signal
import sys
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parent.parent / "bin" / "bb-guardia-proceso"


def _cargar():
    """`@dataclass` en el modulo cargado necesita encontrarse a si mismo en
    `sys.modules` (resuelve KW_ONLY via `sys.modules.get(cls.__module__)`),
    asi que hay que registrarlo ANTES de ejecutarlo -- sin esto, exec_module
    revienta con AttributeError sobre None. Se retira al salir para no dejar
    un modulo fantasma entre tests."""
    loader = machinery.SourceFileLoader("bb_guardia_proceso", str(RUTA))
    spec = util.spec_from_loader("bb_guardia_proceso", loader)
    assert spec is not None, f"no se pudo construir el spec de {RUTA}"
    mod = util.module_from_spec(spec)
    sys.modules["bb_guardia_proceso"] = mod
    try:
        loader.exec_module(mod)
    finally:
        del sys.modules["bb_guardia_proceso"]
    return mod


@pytest.fixture
def g(tmp_path, monkeypatch):
    """Carga el modulo con DRY_RUN forzado y su evidencia en tmp_path, para
    que ningun test real mande una senal ni escriba en $HOME."""
    monkeypatch.setenv("BB_GUARDIA_DRY_RUN", "1")
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    mod = _cargar()
    monkeypatch.setattr(mod, "EVIDENCIA", tmp_path / "guardia_proceso.jsonl")
    return mod


def _muestra(pid, rss_gib, comm="python3"):
    return {"pid": pid, "rss_kb": int(rss_gib * 1024 * 1024), "comm": comm}


def _eventos(g):
    if not g.EVIDENCIA.exists():
        return []
    return [json.loads(l) for l in g.EVIDENCIA.read_text(encoding="utf-8").splitlines()
            if l.strip()]


# ------------------------------------------------------- la escalada, en abstracto


def test_una_sola_crecida_no_dispara_nada(g):
    """UMBRAL_AVISO=2: una muestra sola nunca es una racha."""
    estado = g.procesar_muestra(_muestra(100, 4.0), {})
    estado = g.procesar_muestra(_muestra(100, 9.0), estado)  # +5 GiB, UNA vez
    assert estado["racha"] == 1
    assert _eventos(g) == []


def test_dos_crecidas_seguidas_disparan_SOLO_el_aviso(g):
    """Paso 1: se registra, no se manda ninguna senal."""
    estado = {}
    for rss in (4.0, 9.0, 14.0):  # +5, +5 -- dos crecidas seguidas
        estado = g.procesar_muestra(_muestra(100, rss), estado)
    eventos = _eventos(g)
    assert len(eventos) == 1
    assert eventos[0]["etapa"] == "aviso"
    assert eventos[0]["accion"] == "ninguna"


def test_tres_crecidas_seguidas_escalan_a_SIGTERM(g):
    """Paso 2: sigue disparando despues del aviso -> SIGTERM, no SIGKILL."""
    estado = {}
    for rss in (4.0, 9.0, 14.0, 19.0):  # tres crecidas de +5 GiB seguidas
        estado = g.procesar_muestra(_muestra(100, rss), estado)
    eventos = _eventos(g)
    assert [e["etapa"] for e in eventos] == ["aviso", "term"]
    assert "SIGTERM" in eventos[1]["accion"]
    assert "SIGKILL" not in eventos[1]["accion"]


def test_cuatro_crecidas_seguidas_escalan_a_SIGKILL(g):
    """Paso 3: solo si SIGTERM no lo paro y sigue disparando."""
    estado = {}
    for rss in (4.0, 9.0, 14.0, 19.0, 24.0):
        estado = g.procesar_muestra(_muestra(100, rss), estado)
    eventos = _eventos(g)
    assert [e["etapa"] for e in eventos] == ["aviso", "term", "kill"]
    assert "SIGKILL" in eventos[2]["accion"]


def test_si_se_para_despues_del_aviso_no_llega_a_SIGTERM(g):
    """Control negativo de la escalada: si el crecimiento se detiene tras el
    aviso, el guardian no sigue escalando solo porque si."""
    estado = {}
    for rss in (4.0, 9.0, 14.0, 14.1, 14.2):  # crece, crece, luego se calma
        estado = g.procesar_muestra(_muestra(100, rss), estado)
    eventos = _eventos(g)
    assert len(eventos) == 1 and eventos[0]["etapa"] == "aviso"


def test_crecer_por_DEBAJO_del_umbral_no_acumula_racha(g):
    estado = g.procesar_muestra(_muestra(100, 4.0), {})
    estado = g.procesar_muestra(_muestra(100, 5.5), estado)  # +1.5 GiB < 4
    assert estado["racha"] == 0
    assert _eventos(g) == []


def test_si_cambia_el_pid_mas_grande_la_racha_se_corta(g):
    """Sin esto, dos procesos DISTINTOS que crecen un poco cada uno se
    sumarian como si fueran el mismo culpable."""
    estado = g.procesar_muestra(_muestra(100, 4.0), {})
    estado = g.procesar_muestra(_muestra(200, 9.0), estado)  # otro pid, sin racha previa
    assert estado["racha"] in (0, 1)  # nunca hereda la racha del pid 100
    assert _eventos(g) == []


# ------------------------------------------------------- los dos incidentes reales


def test_reproduce_el_colapso_1_medido_el_2026_09_28(g):
    """Los numeros literales de tasks/backlog/DEBT-PROCESO-SIN-TECHO...md:
    pid 1410728, 4.8 -> 13.7 -> 21.4 -> 31.0 GiB entre las 03:25:09 y las
    03:28:09. La telemetria se corta ahi (el reinicio se llevo el resto), asi
    que esto solo puede probar hasta AVISO+SIGTERM, no el paso final."""
    estado = {}
    for rss in (4.8, 13.7, 21.4, 31.0):
        estado = g.procesar_muestra(_muestra(1410728, rss), estado)
    eventos = _eventos(g)
    assert [e["etapa"] for e in eventos] == ["aviso", "term"], (
        "el guardian NO habria actuado a tiempo sobre el colapso real que motivo su creacion")
    assert eventos[0]["rss_kb"] == int(21.4 * 1024 * 1024)
    assert eventos[1]["rss_kb"] == int(31.0 * 1024 * 1024)


def test_reproduce_el_colapso_2_via_el_techo_absoluto(g):
    """El colapso 2: el proceso ya estaba en 30-36 GiB ESTABLE cuando
    aparecio en la telemetria -- la tasa no lo habria cazado (no crecia entre
    muestras), el techo absoluto si."""
    estado = {}
    for rss in (30.4, 30.5, 30.6):  # estable, sin crecer, pero sobre el techo
        estado = g.procesar_muestra(_muestra(320489, rss), estado)
    eventos = _eventos(g)
    assert [e["etapa"] for e in eventos] == ["aviso", "term"]
    assert all("techo" in e["motivo"] for e in eventos)


def test_control_negativo_una_sola_muestra_sobre_el_techo_no_dispara(g):
    estado = g.procesar_muestra(_muestra(320489, 30.4), {})
    assert estado["racha"] == 1
    assert _eventos(g) == []


def test_procesos_legitimos_del_mismo_dataset_nunca_disparan(g):
    """Control negativo del que motiva esta ficha entera: los procesos
    REALES vistos en los mismos dos incidentes (VLLM::EngineCor, 3.3-5.9
    GiB) no pueden disparar el guardian. Si esto falla, el umbral es
    demasiado bajo."""
    estado = {}
    for rss in (3.3, 4.1, 4.9, 5.9, 5.2, 4.8):
        estado = g.procesar_muestra(_muestra(29049, rss, "VLLM::EngineCor"), estado)
    assert _eventos(g) == []


# ------------------------------------------------------- seguridad al actuar


def test_nunca_toca_pid_1(g):
    assert g._es_intocable(1, "systemd") == "PID 1 o el propio guardian"


def test_nunca_se_toca_a_si_mismo(g):
    assert g._es_intocable(os.getpid(), "python3") == "PID 1 o el propio guardian"


def test_nunca_toca_un_comm_intocable(g):
    razon = g._es_intocable(999999, "sshd")
    assert razon is not None and "intocables" in razon


def test_nunca_toca_root(g, monkeypatch):
    monkeypatch.setattr(g, "_uid_de", lambda pid: 0)
    razon = g._es_intocable(999999, "algo")
    assert razon is not None and "root" in razon


def test_control_negativo_un_pid_normal_de_usuario_SI_es_tocable(g, monkeypatch):
    """Sin esto, `_es_intocable` podria estar bloqueando TODO por error y los
    tests de arriba pasarian sin que el guardian pudiera actuar nunca."""
    monkeypatch.setattr(g, "_uid_de", lambda pid: 1000)
    assert g._es_intocable(999999, "python3") is None


def test_uid_ilegible_por_precaucion_no_se_toca(g, monkeypatch):
    monkeypatch.setattr(g, "_uid_de", lambda pid: None)
    razon = g._es_intocable(999999, "python3")
    assert razon is not None and "Uid" in razon


# ------------------------------------------------------- dry-run vs real


def test_dry_run_no_llama_a_kill_ni_a_os_kill_en_ninguna_etapa(g, monkeypatch):
    llamado = []
    monkeypatch.setattr(os, "kill", lambda *a: llamado.append(a))
    estado = {}
    for rss in (4.0, 9.0, 14.0, 19.0, 24.0):  # llega hasta SIGKILL
        estado = g.procesar_muestra(_muestra(100, rss), estado)
    assert not llamado, "con DRY_RUN=1 nunca se puede llamar a os.kill"
    eventos = _eventos(g)
    assert all(e["dry_run"] is True for e in eventos)
    assert eventos[-1]["etapa"] == "kill"
    assert "[dry-run]" in eventos[-1]["accion"]


def test_sin_dry_run_intocable_no_llama_a_kill(tmp_path, monkeypatch):
    """El otro lado: SIN dry-run, un intocable sigue sin tocarse."""
    monkeypatch.delenv("BB_GUARDIA_DRY_RUN", raising=False)
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    mod = _cargar()
    monkeypatch.setattr(mod, "EVIDENCIA", tmp_path / "guardia_proceso.jsonl")
    llamado = []
    monkeypatch.setattr(os, "kill", lambda *a: llamado.append(a))
    mod._enviar_senal(mod.Proceso(1, "systemd", 1024), "prueba", "term", mod.signal.SIGTERM)
    assert not llamado


def test_sin_dry_run_un_pid_tocable_SI_recibe_la_senal(tmp_path, monkeypatch):
    """Control negativo del de arriba: sin esto, el test de intocable
    pasaria aunque `_enviar_senal` nunca llamara a `os.kill` para nadie."""
    monkeypatch.delenv("BB_GUARDIA_DRY_RUN", raising=False)
    monkeypatch.setenv("BLACKBOX_DATA", str(tmp_path))
    mod = _cargar()
    monkeypatch.setattr(mod, "EVIDENCIA", tmp_path / "guardia_proceso.jsonl")
    monkeypatch.setattr(mod, "_uid_de", lambda pid: 1000)
    llamado = []
    monkeypatch.setattr(os, "kill", lambda pid, sig: llamado.append((pid, sig)))
    mod._enviar_senal(mod.Proceso(999999, "python3", 20 * 1024 * 1024), "prueba", "term", signal.SIGTERM)
    assert llamado == [(999999, signal.SIGTERM)]
