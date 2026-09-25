"""Suite de `tools/presupuesto_memoria.py` -- que los techos COMPONGAN.

## Por que existe

`DEBT-TECHOS-SIN-CALIBRAR` decia que los techos declarados sumaban mas que la
maquina, y no se podia cerrar porque faltaba un numero: cuanta memoria unificada
reserva la GPU, que **ningun cgroup ve**. Medido en esta caja: 7 GiB de CUDA se
contabilizan como 15 MiB.

Lo que esta suite guarda no es la aritmetica -- eso es una suma-- sino que el
gate pueda salir en las DOS direcciones. Un presupuesto que siempre cuadra no
es un presupuesto.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import presupuesto_memoria as pm


def _cgroups(tmp_path, app_max="51539607552", docker_max="34359738368",
             system_max="max", uid=None):
    import os
    uid = uid if uid is not None else os.getuid()
    raiz = tmp_path / "cg"
    rutas = {
        raiz / "user.slice" / f"user-{uid}.slice" / f"user@{uid}.service" / "app.slice": app_max,
        raiz / "docker.slice": docker_max,
        raiz / "system.slice": system_max,
    }
    for d, mx in rutas.items():
        d.mkdir(parents=True, exist_ok=True)
        (d / "memory.max").write_text(mx + "\n", encoding="utf-8")
        (d / "memory.current").write_text("2147483648\n", encoding="utf-8")
    return raiz


def _meminfo(tmp_path, kb=126980000):
    f = tmp_path / "meminfo"
    f.write_text(f"MemTotal:       {kb} kB\nMemFree:  1 kB\n", encoding="utf-8")
    return f


def _muestras(tmp_path, picos_mib):
    d = tmp_path / "samples"
    d.mkdir(parents=True, exist_ok=True)
    filas = []
    for i, mib in enumerate(picos_mib):
        filas.append(json.dumps({"ts": f"2026-09-2{i%9}T00:00:00-0600",
                                 "gpu": [{"pid": 1, "mib": mib, "unit": "x"}]}))
    (d / "2026-09-21.jsonl").write_text("\n".join(filas) + "\n", encoding="utf-8")
    return d


def _montar(monkeypatch, tmp_path, **kw):
    monkeypatch.setattr(pm, "CGROUP", _cgroups(tmp_path, **{k: v for k, v in kw.items()
                                                            if k.endswith("_max")}))
    monkeypatch.setattr(pm, "MEMINFO", _meminfo(tmp_path, kw.get("mem_kb", 126980000)))
    monkeypatch.setattr(pm, "DATA_DIR", tmp_path)
    _muestras(tmp_path, kw.get("picos", [1024]))
    monkeypatch.setattr(pm, "RESERVA_GPU_GIB", kw.get("reserva", 86.0))


def test_falla_con_el_reparto_real_de_esta_maquina(monkeypatch, tmp_path, capsys):
    """El control negativo que la ficha exigia literalmente: "el gate tiene que
    FALLAR con el reparto de hoy (125G sobre 121.1). Si pasa, no mide".

    Con la reserva de GPU contada son 168.3 sobre 121.1.
    """
    _montar(monkeypatch, tmp_path)   # 48 + 32 + 2 de system + 86 de GPU
    assert pm.main(["--check"]) == 1
    err = capsys.readouterr().err
    assert "NO componen" in err


def test_pasa_cuando_los_techos_SI_caben(monkeypatch, tmp_path):
    """La otra direccion, sin la cual el de arriba no significa nada: un gate
    que no puede salir en verde no mide, solo bloquea."""
    _montar(monkeypatch, tmp_path, app_max=str(8 * 1024**3), docker_max=str(8 * 1024**3),
            system_max=str(4 * 1024**3), reserva=40.0)
    assert pm.main(["--check"]) == 0


def test_un_slice_SIN_techo_se_cuenta_y_se_DICE(monkeypatch, tmp_path, capsys):
    """Un slice sin techo no se puede presupuestar, solo observar. Meterlo en la
    suma callando que es una observacion seria presentar un numero de hoy como
    un compromiso."""
    _montar(monkeypatch, tmp_path, app_max=str(8 * 1024**3), docker_max=str(8 * 1024**3),
            system_max="max", reserva=40.0)
    rc = pm.main(["--check"])
    err = capsys.readouterr().err
    assert rc == 1 and "sin techo" in err


def test_la_reserva_VIEJA_se_caza_con_las_propias_muestras(monkeypatch, tmp_path, capsys):
    """Una reserva fijada una vez y nunca releida es el techo sin calibrar que
    esta ficha vino a quitar. Si las muestras ya vieron mas que lo declarado,
    el numero esta viejo y el gate lo dice."""
    _montar(monkeypatch, tmp_path, app_max=str(1024**3), docker_max=str(1024**3),
            system_max=str(1024**3), reserva=10.0, picos=[40 * 1024])
    rc = pm.main(["--check"])
    err = capsys.readouterr().err
    assert rc == 1 and "VIEJA" in err


def test_sin_MemTotal_es_COULD_NOT_RUN_y_no_un_aprobado(monkeypatch, tmp_path, capsys):
    """No se midio y esta bien no son lo mismo. Devuelve 2, que no es ni 0 ni 1."""
    _montar(monkeypatch, tmp_path)
    monkeypatch.setattr(pm, "MEMINFO", tmp_path / "no-existe")
    assert pm.main(["--check"]) == 2
    assert "COULD_NOT_RUN" in capsys.readouterr().err


def test_sin_muestras_el_pico_es_None_y_no_cero(monkeypatch, tmp_path):
    """`None` dice "no se pudo comprobar"; un 0 diria "no hay GPU en uso", que
    es una afirmacion sobre la maquina que nadie hizo."""
    monkeypatch.setattr(pm, "DATA_DIR", tmp_path / "vacio")
    assert pm.pico_gpu_observado_mib() is None


def test_el_pico_es_el_AGREGADO_de_la_muestra_no_el_mayor_proceso(tmp_path):
    """Lo que agota la maquina es la suma simultanea, no el mayor de los
    sumandos. El pico real del 2026-09-21 fueron 33.6 GiB del vLLM MAS ocho
    procesos de un abanico que sumaban 48: quedarse con el mayor habria
    reportado 33.6 y perdido el hallazgo entero."""
    d = tmp_path / "samples"
    d.mkdir(parents=True)
    (d / "x.jsonl").write_text(json.dumps({
        "ts": "2026-09-21T00:33:00-0600",
        "gpu": [{"pid": 1, "mib": 30000}, {"pid": 2, "mib": 9000},
                {"pid": 3, "mib": 9000}, {"pid": 4, "mib": 9000}]}) + "\n",
        encoding="utf-8")
    pico = pm.pico_gpu_observado_mib(d)
    assert pico is not None and pico[0] == 57000, pico


def test_un_techo_ilegible_no_se_lee_como_infinito(tmp_path):
    """Si `memory.max` trae basura, devolver None (sin techo) es lo honesto;
    devolver 0 haria que el presupuesto cuadrara por no saber leer."""
    d = tmp_path / "roto"
    d.mkdir()
    (d / "memory.max").write_text("no-soy-un-numero\n", encoding="utf-8")
    assert pm.techo_gib(d) is None


def test_una_muestra_ILEGIBLE_no_se_traga_en_silencio(monkeypatch, tmp_path, capsys):
    """Lo cazo `zero-debt` con `silent_io_loop_swallow` sobre la primera version
    de este modulo, que hacia `except OSError: continue` dentro del bucle.

    El gate tenia razon: un pico calculado sobre un conjunto incompleto puede
    salir MAS BAJO de lo real, y presentarlo como el maximo seria afirmar algo
    que la lectura no respalda. Ahora se cuentan y bloquean.
    """
    _montar(monkeypatch, tmp_path, app_max=str(1024**3), docker_max=str(1024**3),
            system_max=str(1024**3), reserva=10.0)
    roto = tmp_path / "samples" / "2026-09-22.jsonl"
    roto.write_text('{"gpu": [{"mib": 1}]}\n', encoding="utf-8")
    roto.chmod(0o000)
    try:
        rc = pm.main(["--check"])
        salida = capsys.readouterr()
        assert "could_not_run" in salida.out, salida.out
        assert rc == 1 and "incompleto" in salida.err, salida.err
    finally:
        roto.chmod(0o644)


def test_control_negativo_sin_ilegibles_no_se_inventa_el_aviso(monkeypatch, tmp_path, capsys):
    """Si el aviso saliera siempre, no distinguiria un conjunto completo de uno
    roto y seria ruido en vez de senal."""
    _montar(monkeypatch, tmp_path, app_max=str(1024**3), docker_max=str(1024**3),
            system_max=str(1024**3), reserva=40.0)
    rc = pm.main(["--check"])
    salida = capsys.readouterr()
    assert "could_not_run" not in salida.out and rc == 0, salida
