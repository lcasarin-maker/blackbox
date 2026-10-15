"""Suite de `tools/atribucion_enjambre.py` (solo lectura, datos sinteticos).

Cada afirmacion tiene su control negativo: la serie que SI separa y la que no,
la ventana con datos y la vacia, la linea legible y la corrupta.
"""

from __future__ import annotations

import json

import pytest

from tools import atribucion_enjambre as ae

G = 1024 * 1024  # KiB por GiB


def reg(ts, psi: float | None = 0.0, app=None, scopes=None, pidio=None):
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


def sn(n, unit="app-com.anthropic.Claude-100.scope", state="ok"):
    return {"unit": unit, "memory_current_kb": 1, "process_count": n, "state": state}


def test_conteo_no_separa_si_un_scope_sano_llego_mas_alto():
    sano = [reg("00:00", 1.0, scopes=[sn(224, "app-com.anthropic.Claude-1.scope")]), reg("01:00", 1.0, scopes=[sn(100, "app-com.anthropic.Claude-1.scope")])]
    inc = [reg("10:00", 0.0, scopes=[sn(50)]), reg("11:00", 40.0, scopes=[sn(136)])]
    r = ae.analizar(sano + inc, "2026-10-05T00:10:00-06:00", "2026-10-05T00:12:00-06:00")
    c = r["conteo"]["app-com.anthropic.Claude-100.scope"]
    assert c["pico_incidente"] == 136 and c["maximo_sano"] == 224
    assert c["separable_por_nivel"] is False and c["margen_nivel_pct"] == -39.3


def test_conteo_separa_cuando_el_incidente_supera_lo_sano_control_negativo_del_anterior():
    sano = [reg("00:00", 1.0, scopes=[sn(60, "app-com.anthropic.Claude-1.scope")])]
    inc = [reg("10:00", 0.0, scopes=[sn(50)]), reg("11:00", 40.0, scopes=[sn(136)])]
    c = ae.analizar(sano + inc, "2026-10-05T00:10:00-06:00", "2026-10-05T00:12:00-06:00")["conteo"]["app-com.anthropic.Claude-100.scope"]
    assert c["separable_por_nivel"] is True and c["margen_nivel_pct"] == 126.7
    assert c["separable_por_tasa"] is True and c["tasa_incidente_proc_min"] == 86.0


def test_tasa_max_ignora_pares_fuera_de_30_a_180_s_y_scopes_sin_conteo():
    base = ae._t(reg("00:00"))
    from datetime import timedelta
    s = [(base, 10, 0.0), (base + timedelta(seconds=10), 500, 0.0), (base + timedelta(seconds=70), 40, 0.0), (base + timedelta(seconds=400), 900, 0.0)]
    assert ae.tasa_max(s) == 0.0  # el unico par de 30-180 s es una caida (500 -> 40): no es crecimiento
    s += [(base + timedelta(seconds=460), 930, 0.0)]
    assert ae.tasa_max(s) == 30.0  # 900 -> 930 en 60 s
    assert ae.tasa_max([]) == 0.0
    assert ae.series_conteo([reg("00:00", 0.0, scopes=[sn(5, state="down"), {"unit": "x", "state": "ok"}])]) == {}


def test_script_entrypoint_sale_con_el_codigo_de_main(tmp_path, monkeypatch, capsys):
    import runpy
    from pathlib import Path

    monkeypatch.setattr("sys.argv", ["atribucion_enjambre.py", "--samples", str(tmp_path),
                                     "--desde", "2026-10-05T00:00:00-06:00", "--hasta", "2026-10-05T01:00:00-06:00"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(Path(ae.__file__)), run_name="__main__")
    assert exc.value.code == 2
    assert json.loads(capsys.readouterr().out)["veredicto"] == "could_not_run"
