"""Suite de `tools/atribucion_enjambre.py` (solo lectura, datos sinteticos).

Cada afirmacion tiene su control negativo: la serie que SI separa y la que no,
la ventana con datos y la vacia, la linea legible y la corrupta.
"""

from __future__ import annotations

import json

from tools import atribucion_enjambre as ae

G = 1024 * 1024  # KiB por GiB


def reg(ts, psi=0.0, app=None, scopes=None, pidio=None):
    r = {"ts": f"2026-10-05T00:{ts}-0600", "psi": {"mem_full": psi}}
    if app is not None:
        r["slices"] = [{"slice": "app", "cur_kb": int(app * G)}]
    if scopes is not None:
        r["claude_scopes"] = scopes
    if pidio is not None:
        r["pidio"] = pidio
    return r


def sc(gib, unit="app-com.anthropic.Claude-100.scope", state="ok"):
    return {"unit": unit, "memory_current_kb": int(gib * G), "state": state}


def escribe(tmp_path, lineas, nombre="2026-10-05.jsonl"):
    p = tmp_path / nombre
    p.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return p


def test_cargar_cuenta_lo_ilegible(tmp_path):
    p = escribe(tmp_path, [json.dumps(reg("00:00")), "{roto", "", "[1]"])
    regs, mal = ae.cargar([p])
    assert len(regs) == 1 and mal == 2  # control negativo: no se traga lo roto


def test_ventana_filtra_y_ordena():
    regs = [reg("05:00"), reg("01:00"), reg("30:00")]
    out = ae.ventana(regs, "2026-10-05T00:00:00-06:00", "2026-10-05T00:10:00-06:00")
    assert [r["ts"][14:16] for r in out] == ["01", "05"]


def test_quien_crecio_cuenta_pids_y_ordena():
    regs = [reg("01:00", pidio=[{"pid": 1, "comm": "java", "crecio_kb": 5},
                                {"pid": 2, "comm": "java", "crecio_kb": 9}]),
            reg("02:00", pidio=[{"pid": 3, "comm": "x", "crecio_kb": 99}]),
            reg("03:00")]
    out = ae.quien_crecio(regs)
    assert out[0]["comm"] == "x"
    java = next(c for c in out if c["comm"] == "java")
    assert java["pids"] == 2 and java["max_crecio_kb"] == 9


def test_atribucion_a_scope_solo_por_pid_coincidente():
    regs = [reg("01:00", scopes=[sc(1, unit="app-com.anthropic.Claude-100.scope")],
                pidio=[{"pid": 100, "comm": "claude-desktop", "crecio_kb": 1},
                       {"pid": 7, "comm": "java", "crecio_kb": 2}])]
    out = ae.analizar(regs, "2026-10-05T00:00:00-06:00", "2026-10-05T01:00:00-06:00")
    por = {c["comm"]: c["scope"] for c in out["quien_crecio"]}
    assert por["claude-desktop"].endswith("Claude-100.scope")
    assert por["java"] == "sin_scope"  # control negativo: no se inventa scope


def test_series_ignora_scope_no_ok_y_sin_slices():
    regs = [reg("01:00", scopes=[sc(1, state="unavailable")]), reg("02:00")]
    assert ae.series(regs) == {}
    assert "app.slice" in ae.series([reg("01:00", app=3)])


def test_techo_separable_y_adelanto():
    sano = [reg(f"0{i}:00", psi=0.0, app=20) for i in range(3)]
    inc = [reg("10:00", psi=None, app=33), reg("12:00", psi=50.0, app=38)]
    s = ae.series(sano + inc)["app.slice"]
    t = ae.techo(s, s, [30.0, 36.0, 39.0])
    assert t["separable"] is True and t["margen_gib"] == 18.0
    por = {c["techo_gib"]: c for c in t["candidatos"]}
    assert por[30.0]["adelanto_s"] == 120 and por[30.0]["mataria_carga_sana"] is False
    assert por[39.0]["cruza"] is False and por[39.0]["adelanto_s"] is None


def test_techo_no_separable_cuando_lo_sano_llega_al_pico():
    pts = [reg("01:00", psi=0.0, app=40), reg("02:00", psi=60.0, app=39)]
    s = ae.series(pts)["app.slice"]
    t = ae.techo(s, s, [39.5])
    assert t["separable"] is False  # control negativo del caso anterior
    assert t["candidatos"][0]["mataria_carga_sana"] is True


def test_techo_sin_psi_alto_no_inventa_adelanto():
    s = ae.series([reg("01:00", psi=0.0, app=40)])["app.slice"]
    t = ae.techo(s, s, [30.0])
    assert t["primer_psi_alto"] is None and t["candidatos"][0]["adelanto_s"] is None


def test_analizar_sin_muestras_es_could_not_run():
    out = ae.analizar([reg("01:00")], "2026-09-01T00:00:00-06:00", "2026-09-01T01:00:00-06:00", 3)
    assert out["veredicto"] == "could_not_run" and out["lineas_ilegibles_corpus"] == 3


def test_analizar_cuenta_registros_sin_psi_y_series_vacias():
    r = {"ts": "2026-10-05T00:01:00-0600"}
    out = ae.analizar([r], "2026-10-05T00:00:00-06:00", "2026-10-05T01:00:00-06:00")
    assert out["registros_sin_psi"] == 1 and out["psi_max"] is None
    assert out["series_sin_datos"] and out["techos"] == {}


def test_cli_ok_y_could_not_run(tmp_path, capsys):
    escribe(tmp_path, [json.dumps(reg("01:00", psi=1.0, app=2))])
    base = ["--samples", str(tmp_path), "--desde", "2026-10-05T00:00:00-06:00"]
    assert ae.main(base + ["--hasta", "2026-10-05T01:00:00-06:00", "--techo-gib", "1"]) == 0
    assert json.loads(capsys.readouterr().out)["veredicto"] == "ok"
    assert ae.main(base + ["--hasta", "2026-10-05T00:00:30-06:00"]) == 2
    vacio = tmp_path / "vacio"
    vacio.mkdir()
    assert ae.main(["--samples", str(vacio), "--desde", "2026-10-05T00:00:00-06:00",
                    "--hasta", "2026-10-05T01:00:00-06:00"]) == 2
