"""Control: emula lo que el portero vivo hace (tools/portero.py::_decide_clase -> descongelar con 'turno libre') sobre
scopes que casen po.NOMBRE_UNIDAD, pero SOLO sobre scopes cuyo unico proceso sea `sleep 60` (los de la prueba)."""
import threading
import time
from pathlib import Path

from tools import portero as po

hits = []
vistos = {}


def _solo_sleep60(d):
    try:
        pids = (d / "cgroup.procs").read_text().split()
        return len(pids) == 1 and Path(f"/proc/{pids[0]}/cmdline").read_bytes().split(b"\0")[:2] in ([b"sleep", b"60"], [b"/usr/bin/sleep", b"60"])
    except OSError:
        return False


def _bucle(stop):
    app = po.cgroup_app()
    while not stop.is_set():
        vistos["vueltas"] = vistos.get("vueltas", 0) + 1
        try:
            for d in app.iterdir():
                if po.NOMBRE_UNIDAD.match(d.name):
                    vistos["match"] = vistos.get("match", 0) + 1
                    vistos.setdefault("muestra", set()).add(tuple(Path(f"/proc/{x}/cmdline").read_bytes() for x in (d / "cgroup.procs").read_text().split()))
                    vistos["sleep60"] = vistos.get("sleep60", 0) + (1 if _solo_sleep60(d) else 0)
                    vistos["congelado"] = vistos.get("congelado", 0) + (1 if po._congelado(d) else 0)
                if po.NOMBRE_UNIDAD.match(d.name) and _solo_sleep60(d) and po._congelado(d):
                    if not po.congela(d, False):
                        hits.append(d.name)
        except OSError:
            pass
        time.sleep(0.0005)


_real_congela = po.congela


def _congela_con_carga(cg, si):
    """Simula el test descheduleado por la carga (load ~55 en 20 cores): tras congelar, 50 ms antes de seguir."""
    r = _real_congela(cg, si)
    if si:
        time.sleep(0.05)
    return r


po.congela = _congela_con_carga


def pytest_sessionstart(session):
    session._stop = threading.Event()
    session._th = threading.Thread(target=_bucle, args=(session._stop,), daemon=True)
    session._th.start()


def pytest_sessionfinish(session):
    session._stop.set()
    print(f"\nDEMONIO_EMULADO descongelaciones={len(hits)} {hits} vistos={vistos}")
