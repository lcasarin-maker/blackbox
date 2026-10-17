"""El portero clasifica por la FORMA del comando. Las tandas `soffice --headless` de otros proyectos quedan sin clase.

Cierre de DEBT-PORTERO-NO-CLASIFICA-TANDAS-DE-LIBREOFFICE-DE-OTROS-PROYECTOS-01. Mientras la ficha siga abierta
`tests/conftest.py` marca el test xfail (tests/known_failures.json).
"""
from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

import pytest

from tools import portero


def test_una_conversion_de_libreoffice_headless_tiene_clase():
    argv = ["/usr/lib/libreoffice/program/soffice.bin", "-env:UserInstallation=file:///tmp/perfil", "--headless",
            "--convert-to", "pdf", "--outdir", "/tmp/salida", "/tmp/entrada.docx"]
    assert portero.clasifica(argv) is not None


def test_control_negativo_un_proceso_cualquiera_no_tiene_clase():
    """El instrumento puede decir 'sin clase': un editor o un shell no son trabajo pesado por forma."""
    assert portero.clasifica(["/usr/bin/bash", "-lc", "echo hola"]) is None


# --- Clase `libreoffice`: forma, decision y `observar` como techo de la clase -------------------------------------

po = portero
G = po.GIB_KB
CLAUDE = "/user.slice/user-1000.slice/user@1000.service/app.slice/app-com.anthropic.Claude-1.scope"
CONVERSION = ["--headless", "--convert-to", "pdf", "--outdir", "/tmp/s", "/tmp/e.docx"]


@pytest.mark.unit
@pytest.mark.parametrize("argv", [
    ["/usr/lib/libreoffice/program/oosplash", "-env:UserInstallation=file:///tmp/p", *CONVERSION],
    ["/usr/lib/libreoffice/program/soffice.bin", *CONVERSION],
    ["/usr/bin/soffice", *CONVERSION],
    ["/bin/sh", "/usr/bin/soffice", *CONVERSION],  # el lanzador de la distro es un script de shell
])
def test_conversion_headless_es_libreoffice_por_forma(argv: list[str]):
    assert po.clasifica(argv) == "libreoffice"


@pytest.mark.unit
@pytest.mark.parametrize("argv", [
    ["/usr/bin/bash", "-lc", "soffice --headless --convert-to pdf x.docx"],  # un shell que lo NOMBRA no lo es
    ["/usr/lib/libreoffice/program/soffice.bin", "/home/u/notas.odt"],  # GUI: sin --headless
    ["/usr/lib/libreoffice/program/soffice.bin", "--convert-to", "pdf", "x.docx"],  # sin --headless
    ["/usr/lib/libreoffice/program/soffice.bin", "--headless", "--accept=socket,port=2002;urp;"],  # servidor, no conversion
    ["python3", "lote.py", "soffice", "--headless", "--convert-to", "pdf"],  # el driver del lote no tiene la forma
])
def test_control_negativo_sin_forma_de_conversion_no_es_libreoffice(argv: list[str]):
    assert po.clasifica(argv) is None


@pytest.mark.unit
def test_pytest_que_menciona_soffice_sigue_siendo_suite():
    assert po.clasifica(["python", "-m", "pytest", "soffice.bin", "--headless", "--convert-to"]) == "suite"


def _conv(raiz: int, edad: float, **kw: Any) -> po.Arbol:
    return po.Arbol(raiz=raiz, clase="libreoffice", rss_kb=200_000, procesos=2, edad_s=edad, cgroup=CLAUDE, **kw)


def _suite(raiz: int, edad: float) -> po.Arbol:
    return po.Arbol(raiz=raiz, clase="suite", rss_kb=10 * G, procesos=5, edad_s=edad, cgroup=CLAUDE)


def _estado() -> po.Estado:
    return po.Estado(0.0, "", 42 * G, 30 * G)


@pytest.mark.unit
def test_la_cola_admite_las_conversiones_de_una_en_una():
    acc = po.decide([_conv(10, 1.0), _conv(11, 2.0), _conv(12, 0.5)], _estado())
    assert {(a.raiz, a.tipo) for a in acc} == {(11, "admitir"), (10, "congelar"), (12, "congelar")}
    assert acc[0].topes == {"MemoryMax": G * 1024, "MemoryHigh": G * 9 // 10 * 1024, "MemorySwapMax": 0, "TasksMax": 64}
    assert po.presupuesto_desbordado(42 * G, po.CLASES) == ""  # 20 GiB de suite + 1 GiB de libreoffice caben


@pytest.mark.unit
def test_las_conversiones_no_cambian_lo_que_se_decide_para_las_suites():
    suites = [_suite(1, 30), _suite(2, 60)]
    solo = po.decide(suites, _estado())
    mezcla = po.decide([*suites, _conv(10, 1.0), _conv(11, 2.0)], _estado())
    assert [a for a in mezcla if a.clase == "suite"] == solo
    assert {a.clase for a in mezcla} == {"suite", "libreoffice"}  # control: las conversiones si entran a su cola


@pytest.mark.unit
@pytest.mark.parametrize(("global_", "clase", "efectivo"), [
    ("actuar", "libreoffice", "observar"),
    ("observar", "libreoffice", "observar"),
    ("off", "libreoffice", "off"),  # el interruptor global en off gana
    ("actuar", "suite", "actuar"),  # control: suite obedece solo al interruptor, como antes
    ("observar", "suite", "observar"),
    ("off", "suite", "off"),
    ("actuar", None, "actuar"),
])
def test_modo_efectivo_es_el_mas_restrictivo(global_: str, clase: str | None, efectivo: str):
    assert po.modo_efectivo(global_, clase) == efectivo


def _filas(log: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]


def _proc_vivo(proc: Path, pid: int) -> None:
    d = proc / str(pid)
    d.mkdir(parents=True)
    (d / "stat").write_text(f"{pid} (x) S 1 " + " ".join(["0"] * 17) + " 100 0 0\n", encoding="utf-8")
    (d / "cmdline").write_text("soffice.bin\0--headless\0--convert-to\0pdf\0", encoding="utf-8")
    (d / "cgroup").write_text(f"0::{CLAUDE}\n", encoding="utf-8")
    (d / "status").write_text("Name:\tsoffice.bin\nVmRSS:\t1 kB\n", encoding="utf-8")


def _aplica_conversiones(tmp_path: Path, modo_global: str) -> tuple[list[dict[str, Any]], list[list[str]], Path]:
    """Dos conversiones VIVAS en un /proc falso: sin el techo de la clase, aplica llamaria a systemd por cada una."""
    llamadas: list[list[str]] = []

    def ejecutar(args: list[str]) -> tuple[int, str]:
        llamadas.append(args)
        return 1, "ejecutor de prueba: no hace nada"

    proc, cg = tmp_path / "proc", tmp_path / "cg"
    arboles = [_conv(10, 1.0, pids=(10,), inicio=100), _conv(11, 2.0, pids=(11,), inicio=100)]
    for a in arboles:
        _proc_vivo(proc, a.raiz)
    fx = po.Efectos(log=tmp_path / "p.jsonl", cola=tmp_path / "cola", ejecutar=ejecutar, cg_raiz=cg, proc=proc,
                    modo=modo_global)
    po.aplica(po.decide(arboles, _estado()), arboles, _estado(), fx, {})
    return _filas(fx.log), llamadas, cg


@pytest.mark.unit
def test_con_el_interruptor_en_actuar_la_clase_solo_registra_habria_y_no_llama_a_nada(tmp_path: Path):
    filas, llamadas, cg = _aplica_conversiones(tmp_path, "actuar")
    assert sorted((f["raiz"], f["accion"], f["modo"]) for f in filas) == [
        (10, "habria_congelar", "observar"), (11, "habria_admitir", "observar")]
    assert all("rc" not in f for f in filas)
    assert llamadas == [] and not cg.exists()  # ni busctl/systemctl ni cgroup.freeze


@pytest.mark.unit
def test_control_negativo_con_techo_actuar_la_misma_clase_si_llamaria_a_systemd(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Mutacion del techo: con la clase en `actuar`, aplica adopta (llama a busctl) y el test de arriba saldria rojo."""
    monkeypatch.setitem(po.CLASES, "libreoffice", replace(po.CLASES["libreoffice"], modo="actuar"))
    filas, llamadas, _cg = _aplica_conversiones(tmp_path, "actuar")
    assert {f["accion"] for f in filas} == {"admitir", "congelar"} and all("modo" not in f for f in filas)
    assert [x[0] for x in llamadas] == ["busctl", "busctl"]


@pytest.mark.unit
def test_con_el_interruptor_en_off_la_clase_registra_off_y_no_llama_a_nada(tmp_path: Path):
    filas, llamadas, cg = _aplica_conversiones(tmp_path, "off")
    assert {f["modo"] for f in filas} == {"off"} and llamadas == [] and not cg.exists()


class _Espera(Exception):
    pass


def _espera() -> None:
    raise _Espera


def _cola_ocupada(clase: str, pid: int) -> Callable[[], tuple[po.Estado, list[po.Arbol]]]:
    """Un trabajo de `clase` ya admitido (su turno ocupado) y la peticion de `pid` esperando."""
    otro = po.Arbol(raiz=1, clase=clase, rss_kb=0, procesos=0, edad_s=99.0, cgroup="", unidad=f"bb-portero-{clase}-1.scope")
    yo = po.Arbol(raiz=pid, clase=clase, rss_kb=0, procesos=0, edad_s=0.0, cgroup="", virtual=True)
    return lambda: (_estado(), [otro, yo])


@pytest.mark.unit
def test_turno_de_libreoffice_no_espera_aunque_el_interruptor_diga_actuar(tmp_path: Path):
    pid = os.getpid()
    fx = po.Efectos(log=tmp_path / "p.jsonl", cola=tmp_path / "cola", modo="actuar")
    acc = po.turno(pid, "libreoffice", _cola_ocupada("libreoffice", pid), _espera, fx)
    assert acc.tipo == "no_actua" and "habria esperado" in acc.motivo
    assert [(f["accion"], f["modo"]) for f in _filas(fx.log)] == [("habria_esperar", "observar")]
    fx2 = po.Efectos(log=tmp_path / "q.jsonl", cola=tmp_path / "cola2", modo="actuar")
    with pytest.raises(_Espera):  # control negativo: la suite, en el mismo mundo, si espera su turno
        po.turno(pid, "suite", _cola_ocupada("suite", pid), _espera, fx2)
