"""`bb techo` (tools/techo_memoria.py): techo de memoria del cgroup de un proceso, salida estable para el consumidor de conocimiento.

Todo sobre un arbol /proc y /sys/fs/cgroup falso en tmp: ninguna prueba toca un cgroup real. Cada veredicto tiene su
caso y su contrario, y lo ilegible es NOT_COLLECTED (rc 2), nunca NO_ACOTADO ni ACOTADO: un instrumento que no pudo leer
no dice que el sujeto este roto ni sano.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools import techo_memoria as tm

GIB = 1024**3
RUTA = "/user.slice/app-trabajo.scope"


def arbol(tmp_path: Path, memory_max: str | None, swap_max: str | None, pid: int = 4242, linea: str | None = None) -> tuple[Path, Path]:
    proc, raiz = tmp_path / "proc", tmp_path / "cg"
    (proc / str(pid)).mkdir(parents=True)
    (proc / str(pid) / "cgroup").write_text(linea if linea is not None else f"0::{RUTA}\n", encoding="utf-8")
    d = raiz / RUTA.lstrip("/")
    d.mkdir(parents=True)
    if memory_max is not None:
        (d / "memory.max").write_text(memory_max + "\n", encoding="utf-8")
    if swap_max is not None:
        (d / "memory.swap.max").write_text(swap_max + "\n", encoding="utf-8")
    return proc, raiz


def corre(tmp_path: Path, capsys, memory_max, swap_max, *args, **kw) -> tuple[int, dict]:
    proc, raiz = arbol(tmp_path, memory_max, swap_max, **kw)
    rc = tm.main(["--pid", "4242", *args], proc, raiz)
    return rc, json.loads(capsys.readouterr().out)


def test_acotado_con_tope_de_2gib_y_swap_cero(tmp_path, capsys):
    rc, f = corre(tmp_path, capsys, str(2 * GIB), "0", "--max-gib", "2", "--sin-swap")
    assert rc == 0 and f["veredicto"] == "ACOTADO"
    assert f["formato"] == "bb-techo-memoria/1" and f["cgroup"] == RUTA
    assert f["memory_max_bytes"] == 2 * GIB and f["memory_swap_max_bytes"] == 0


@pytest.mark.parametrize("memory_max,swap_max,motivo", [
    pytest.param("max", "0", "sin tope", id="memory.max-es-max"),
    pytest.param(str(3 * GIB), "0", "tope mayor que el exigido", id="tope-mayor"),
    pytest.param(str(2 * GIB), "max", "swap permitido", id="swap-max"),
    pytest.param(str(2 * GIB), str(2 * GIB), "swap con tope pero no cero", id="swap-finito"),
])
def test_control_negativo_lo_que_no_cumple_sale_NO_ACOTADO_rc_1(tmp_path, capsys, memory_max, swap_max, motivo):
    rc, f = corre(tmp_path, capsys, memory_max, swap_max, "--max-gib", "2", "--sin-swap")
    assert (rc, f["veredicto"]) == (1, "NO_ACOTADO"), motivo


@pytest.mark.parametrize("memory_max,swap_max", [
    pytest.param(None, "0", id="memory.max-ausente"),
    pytest.param("basura", "0", id="memory.max-ilegible"),
    pytest.param(str(2 * GIB), None, id="swap.max-ausente"),
])
def test_control_negativo_lo_ilegible_es_NOT_COLLECTED_rc_2_no_NO_ACOTADO(tmp_path, capsys, memory_max, swap_max):
    rc, f = corre(tmp_path, capsys, memory_max, swap_max, "--max-gib", "2", "--sin-swap")
    assert (rc, f["veredicto"]) == (2, "NOT_COLLECTED")
    assert any(str(v).startswith("NOT_COLLECTED") for v in (f["memory_max_bytes"], f["memory_swap_max_bytes"]))


def test_swap_ilegible_no_importa_si_no_se_exige_sin_swap(tmp_path, capsys):
    """La exigencia manda: pedir solo --max-gib no depende de memory.swap.max."""
    rc, f = corre(tmp_path, capsys, str(GIB), None, "--max-gib", "2")
    assert (rc, f["veredicto"]) == (0, "ACOTADO")


def test_pid_sin_cgroup_v2_legible_es_NOT_COLLECTED(tmp_path, capsys):
    rc, f = corre(tmp_path, capsys, str(GIB), "0", "--max-gib", "2", linea="1:name=systemd:/x\n")
    assert (rc, f["veredicto"], f["cgroup"]) == (2, "NOT_COLLECTED", None)


def test_pid_inexistente_es_NOT_COLLECTED_no_un_falso_acotado(tmp_path, capsys):
    proc, raiz = arbol(tmp_path, str(GIB), "0")
    assert tm.main(["--pid", "999999", "--max-gib", "2", "--sin-swap"], proc, raiz) == 2
    assert json.loads(capsys.readouterr().out)["veredicto"] == "NOT_COLLECTED"


def test_sin_exigencia_solo_informa(tmp_path, capsys):
    rc, f = corre(tmp_path, capsys, "max", "max")
    assert rc == 0 and "veredicto" not in f and f["memory_max_bytes"] == "max"


def test_el_tope_de_un_ancestro_no_acota_la_hoja(tmp_path, capsys):
    """Criterio del consumidor: se lee la hoja. Un padre con 1 GiB no da por acotada una hoja en `max`."""
    proc, raiz = arbol(tmp_path, "max", "0")
    (raiz / "user.slice" / "memory.max").write_text(str(GIB) + "\n", encoding="utf-8")
    assert tm.main(["--pid", "4242", "--max-gib", "2", "--sin-swap"], proc, raiz) == 1


def test_el_veredicto_de_bb_equivale_a_la_guarda_del_consumidor(tmp_path):
    """Equivalencia con `_bounded` de tools/idle_skill_candidates.py (consumidor), reproducida aqui, en las 6 combinaciones."""
    def guarda_consumidor(maximum: str, swap: str) -> bool:
        return not (maximum == "max" or int(maximum) > 2 * 1024**3 or swap != "0")

    for mem in ("max", str(GIB), str(2 * GIB), str(3 * GIB)):
        for swap in ("0", "max", str(GIB)):
            d = tmp_path / f"{mem}-{swap}"
            d.mkdir()
            proc, raiz = arbol(d, mem, swap)
            rc = tm.main(["--pid", "4242", "--max-gib", "2", "--sin-swap"], proc, raiz)
            assert (rc == 0) == guarda_consumidor(mem, swap), (mem, swap)


def test_bb_techo_esta_cableado_y_sale_con_el_rc_del_veredicto():
    """Sobre el cgroup REAL de este proceso: sin techo exigido solo informa; el rc 0/1/2 es el del veredicto. No se
    asume en que cgroup corre la suite: se comprueba que el rc concuerda con lo que el propio JSON dice."""
    repo = Path(__file__).resolve().parents[1]
    r = subprocess.run([sys.executable, "-m", "tools.techo_memoria", "--pid", str(__import__("os").getpid()),
                        "--max-gib", "2", "--sin-swap"], cwd=repo, capture_output=True, text=True, timeout=20)
    f = json.loads(r.stdout)
    assert f["formato"] == "bb-techo-memoria/1"
    assert r.returncode == {"ACOTADO": 0, "NO_ACOTADO": 1, "NOT_COLLECTED": 2}[f["veredicto"]]
