"""Suite de `tools/reclaim_ventana.py`: deltas por minuto de los contadores de reclamo.

Los contadores de `memory.stat` son acumulados desde el arranque. Lo que esta
suite guarda es que el lector convierta dos muestras en una tasa sin inventar:
un contador que BAJA es un reinicio (nunca una tasa negativa), un campo
`NOT_COLLECTED` no se vuelve 0, y la parte de reclamo directo sale del par
`pgscan_direct`/`pgscan_kswapd`, no de uno solo.
"""

from __future__ import annotations

import json

from tools import reclaim_ventana as rv


def _fila(ts, refault, direct, kswapd, boot="b1", slice_="app"):
    reclaim = {"refault_file": refault, "pgscan_direct": direct, "pgscan_kswapd": kswapd,
               "pgsteal_direct": 0, "inactive_file_kb": 1, "anon_kb": 1, "file_kb": 1}
    return json.dumps({"ts": ts, "boot_id": boot,
                       "slices": [{"slice": slice_, "cur_kb": 1, "reclaim": reclaim}]})


def _samples(tmp_path, filas):
    d = tmp_path / "samples"
    d.mkdir()
    (d / "2026-10-17.jsonl").write_text("\n".join(filas) + "\n", encoding="utf-8")
    return d


def test_deltas_por_minuto_y_parte_de_reclamo_directo(tmp_path):
    d = _samples(tmp_path, [
        _fila("2026-10-17T18:00:00-0600", 1000, 5000, 100),
        _fila("2026-10-17T18:01:00-0600", 1600, 5990, 110),
        _fila("2026-10-17T18:02:00-0600", 1600, 5990, 110),
    ])
    filas = rv.deltas(rv.serie(d, "app"))
    assert [(f["refault_file"], f["pgscan_direct"], f["pgscan_kswapd"]) for f in filas] == [
        (600, 990, 10), (0, 0, 0)]
    assert filas[0]["parte_directo"] == 0.99
    assert filas[0]["minutos"] == 1.0
    assert filas[1]["parte_directo"] is None  # sin escaneo no hay parte: no es 0 %
    assert not any(f["reinicio"] for f in filas)


def test_un_contador_que_BAJA_es_un_reinicio_y_no_una_tasa_negativa(tmp_path):
    d = _samples(tmp_path, [
        _fila("2026-10-17T16:59:00-0600", 900000, 800000, 1000, boot="viejo"),
        _fila("2026-10-17T17:08:00-0600", 50, 30, 10, boot="nuevo"),
        _fila("2026-10-17T17:09:00-0600", 80, 60, 20, boot="nuevo"),
    ])
    filas = rv.deltas(rv.serie(d, "app"))
    assert filas[0]["reinicio"] is True
    # Tras el reinicio el contador partio de 0: lo acumulado ES el delta.
    assert (filas[0]["refault_file"], filas[0]["pgscan_direct"]) == (50, 30)
    assert all(isinstance(f[k], int) and f[k] >= 0 for f in filas
               for k in ("refault_file", "pgscan_direct", "pgscan_kswapd"))
    assert (filas[1]["pgscan_direct"], filas[1]["reinicio"]) == (30, False)


def test_un_contador_que_baja_SIN_cambiar_de_boot_tambien_es_reinicio(tmp_path):
    d = _samples(tmp_path, [
        _fila("2026-10-17T18:00:00-0600", 500, 500, 500),
        _fila("2026-10-17T18:01:00-0600", 20, 600, 600),
    ])
    (f,) = rv.deltas(rv.serie(d, "app"))
    assert f["reinicio"] is True and f["refault_file"] == 20


def test_NOT_COLLECTED_en_cualquiera_de_las_dos_muestras_no_se_vuelve_cero(tmp_path):
    d = _samples(tmp_path, [
        _fila("2026-10-17T18:00:00-0600", "NOT_COLLECTED", 10, 10),
        _fila("2026-10-17T18:01:00-0600", 100, 20, 10),
    ])
    (f,) = rv.deltas(rv.serie(d, "app"))
    assert f["refault_file"] == "NOT_COLLECTED"
    assert f["pgscan_direct"] == 10 and f["parte_directo"] == 1.0


def test_la_ventana_recorta_por_hora_y_el_resumen_suma_la_ventana(tmp_path, capsys):
    d = _samples(tmp_path, [
        _fila("2026-10-17T17:00:00-0600", 0, 0, 0),
        _fila("2026-10-17T18:00:00-0600", 100, 100, 0),
        _fila("2026-10-17T18:01:00-0600", 400, 1090, 10),
        _fila("2026-10-17T18:02:00-0600", 700, 2080, 20),
        _fila("2026-10-17T19:00:00-0600", 9999, 99999, 99999),
    ])
    rc = rv.main(["--samples", str(d), "--desde", "2026-10-17T18:00",
                  "--hasta", "2026-10-17T18:02"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "18:01" in out and "18:02" in out and "19:00" not in out
    assert "refault_file 600" in out and "pgscan_direct 1980" in out
    assert "directo 99.0 %" in out


def test_sin_muestras_con_reclaim_en_la_ventana_sale_2_COULD_NOT_RUN(tmp_path, capsys):
    d = _samples(tmp_path, [json.dumps({"ts": "2026-10-17T18:00:00-0600",
                                        "slices": [{"slice": "app", "cur_kb": 1}]})])
    assert rv.main(["--samples", str(d)]) == 2
    assert "COULD_NOT_RUN" in capsys.readouterr().err


def test_lee_memory_stat_vivo_o_NOT_COLLECTED(tmp_path):
    f = tmp_path / "memory.stat"
    f.write_text("pgscan_direct 99\npgscan_kswapd 1\nfile x\n", encoding="utf-8")
    r = rv.lee_memory_stat(f)
    assert (r["pgscan_direct"], r["pgscan_kswapd"], r["file_kb"]) == (99, 1, "NOT_COLLECTED")
    assert rv.parte_directo(r) == 0.99
    assert set(rv.lee_memory_stat(tmp_path / "no_existe").values()) == {"NOT_COLLECTED"}
