import copy
import json
from pathlib import Path
from typing import Any

import pytest

from tools import verify_clases_memoria as v

REAL = Path(__file__).resolve().parents[1] / "tasks" / "evidence" / "FEATURE-DMEM-CLASES-DE-MEMORIA-POR-CGROUP-01" / "raw.json"


def fila(rotulo: str, tipo: str, n: int, exit_: int, medidas: tuple[float | None, float | None]) -> dict[str, Any]:
    dmem, memcg = medidas
    return {"rotulo": rotulo, "tipo": tipo, "n_mib": n, "exit": exit_, "dmem_delta_mib": dmem, "memcg_delta_mib": memcg}


def bueno() -> dict[str, Any]:
    f = []
    for r in ("pequena-1", "pequena-2"):
        f += [fila(r, "nada", 256, 0, (0.5, 0.0)), fila(r, "device", 256, 0, (256.0, 0.5)),
              fila(r, "managed", 256, 0, (-0.3, 257.0)), fila(r, "pinned", 256, 0, (0.7, 257.6))]
    f += [fila("sobre-el-tope", "managed", 2048, -9, (None, None)), fila("sobre-el-tope", "pinned", 2048, 137, (None, None)),
          fila("sobre-el-tope", "device", 2048, 0, (2050.0, 4.0)), fila("bajo-el-tope", "managed", 512, 0, (-2.7, 514.0))]
    return {"filas": f}


def cambia(**campos: Any):
    """Devuelve una copia de `bueno()` con los campos de las filas que casan (rotulo, tipo) reemplazados."""
    def aplica(rotulo: str, tipo: str, **nuevos: Any) -> dict[str, Any]:
        d = copy.deepcopy(bueno())
        for f in d["filas"]:
            if f["rotulo"].startswith(rotulo) and f["tipo"] == tipo:
                f.update(nuevos)
        return d
    return aplica


def test_el_caso_bueno_pasa():
    assert v.verifica(bueno()) == ("pass", [])


@pytest.mark.parametrize("rotulo,tipo,nuevos,pista", [
    ("pequena", "nada", {"memcg_delta_mib": 300.0}, "nada: memcg"),          # el instrumento ve ruido: nada vale
    ("pequena", "device", {"dmem_delta_mib": 0.0}, "device: dmem"),           # device sin cobro en dmem
    ("pequena", "device", {"memcg_delta_mib": 256.0}, "device: memcg"),       # device cobrado tambien a memory.current
    ("pequena", "managed", {"dmem_delta_mib": 256.0}, "managed: dmem"),       # managed cobrado a dmem
    ("pequena", "managed", {"memcg_delta_mib": 0.0}, "managed: memcg"),       # managed sin cobro en memory.current
    ("pequena", "pinned", {"memcg_delta_mib": 10.0}, "pinned: memcg"),
    ("sobre-el-tope", "managed", {"exit": 0}, "sobre el tope, managed"),      # managed sobrevive: memory.max no lo frena
    ("sobre-el-tope", "pinned", {"exit": 0}, "sobre el tope, pinned"),
    ("sobre-el-tope", "device", {"exit": -9}, "sobre el tope, device"),       # device muere: el limite no es dmem
    ("sobre-el-tope", "device", {"dmem_delta_mib": 0.0}, "no hay cobro en dmem"),
    ("bajo-el-tope", "managed", {"exit": -9}, "el control no es un control"),
])
def test_cada_regla_tiene_su_control_negativo(rotulo, tipo, nuevos, pista):
    estado, hallazgos = v.verifica(cambia()(rotulo, tipo, **nuevos))
    assert estado == "fail" and any(pista in h for h in hallazgos), hallazgos


def test_corrida_sin_numeros_es_unknown_no_pass():
    estado, hallazgos = v.verifica(cambia()("pequena", "managed", exit=1, dmem_delta_mib=None, memcg_delta_mib=None))
    assert estado == "unknown" and any("no dejo numeros" in h for h in hallazgos)


@pytest.mark.parametrize("quitar", ["nada", "device", "managed", "pinned"])
def test_faltan_filas_pequenas_es_unknown(quitar):
    d = bueno()
    d["filas"] = [f for f in d["filas"] if not (f["rotulo"].startswith("pequena") and f["tipo"] == quitar)]
    estado, hallazgos = v.verifica(d)
    assert estado == "unknown" and any(f"faltan filas pequenas de {quitar}" in h for h in hallazgos)


@pytest.mark.parametrize("rotulo,tipo", [("sobre-el-tope", "managed"), ("sobre-el-tope", "pinned"), ("sobre-el-tope", "device"),
                                         ("bajo-el-tope", "managed")])
def test_faltan_filas_de_tope_es_unknown(rotulo, tipo):
    d = bueno()
    d["filas"] = [f for f in d["filas"] if not (f["rotulo"] == rotulo and f["tipo"] == tipo)]
    estado, hallazgos = v.verifica(d)
    assert estado == "unknown" and any("falta la fila" in h for h in hallazgos)


def test_un_fallo_gana_sobre_lo_que_falta():
    d = cambia()("pequena", "managed", dmem_delta_mib=256.0)
    d["filas"] = [f for f in d["filas"] if f["rotulo"] != "bajo-el-tope"]
    assert v.verifica(d)[0] == "fail"


@pytest.mark.parametrize("malo", [None, [], {}, {"filas": []}, {"filas": "x"}])
def test_entrada_sin_filas_es_unknown(malo):
    assert v.verifica(malo)[0] == "unknown"


def test_main_sobre_la_captura_real_y_sus_negativos(tmp_path, capsys):
    assert v.main([str(REAL)]) == 0
    malo = json.loads(REAL.read_text(encoding="utf-8"))
    for f in malo["filas"]:
        if f["rotulo"] == "sobre-el-tope" and f["tipo"] == "managed":
            f["exit"] = 0  # control negativo sobre datos reales: managed no murio
    ruta = tmp_path / "raw.json"
    ruta.write_text(json.dumps(malo), encoding="utf-8")
    assert v.main([str(ruta)]) == 1
    assert v.main([str(tmp_path / "no-existe.json")]) == 2
    ruta.write_text("no es json", encoding="utf-8")
    assert v.main([str(ruta)]) == 2
    assert v.main([]) == 2
    assert "unknown" in capsys.readouterr().out


def test_se_puede_correr_como_modulo(tmp_path):
    import subprocess
    import sys
    r = subprocess.run([sys.executable, "-m", "tools.verify_clases_memoria", str(REAL)], cwd=REAL.parents[3], capture_output=True,
                       text=True, timeout=60, check=False)
    assert r.returncode == 0 and '"pass"' in r.stdout
