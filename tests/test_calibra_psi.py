"""Cobertura de tools/calibra_psi.py -- el instrumento que sostiene los cortes
de PSI de `bb scan` (DEBT-PSI-UMBRALES-SIN-CALIBRAR).

El test que mas importa aqui no es `test_corte_bueno_no_dispara_en_sanas`: es
`test_control_negativo_*`. Un calibrador que siempre dice CALIBRADO no calibra
nada, y esta misma funcion `clasifica` ya salio CALIBRADO con `--sostenido 0`
antes de invertir el orden de sus dos comprobaciones. Cada corte se prueba
tambien MOVIDO, para que el rojo este demostrado y no supuesto.
"""

import datetime as dt
import json
import sys

import pytest

from tools.calibra_psi import (
    calibra,
    carga,
    clasifica,
    duracion_min,
    excursiones,
    informe,
    main,
    solapa,
    ventanas,
)

pytestmark = pytest.mark.unit

T0 = dt.datetime(2026, 9, 22, 5, 40)


def serie(*pares):
    """(minuto_relativo, mem_full) -> [(datetime, float)]"""
    return [(T0 + dt.timedelta(minutes=m), v) for m, v in pares]


def _linea(ts, **psi):
    return json.dumps({"ts": ts, "psi": psi})


# --- carga -----------------------------------------------------------------

def test_carga_ordena_y_filtra_basura(tmp_path):
    (tmp_path / "b.jsonl").write_text(
        _linea("2026-09-22T05:42:00-0600", mem_full=7.5) + "\n", encoding="utf-8")
    (tmp_path / "a.jsonl").write_text(
        "{no es json\n"                                        # ValueError
        + json.dumps({"ts": "2026-09-22T05:41:00-0600"}) + "\n"        # sin psi
        + json.dumps({"ts": "x", "psi": {"mem_full": 1}}) + "\n"       # ts ilegible
        + json.dumps({"ts": "2026-09-22T05:40:00-0600", "psi": []}) + "\n"  # psi no dict
        + _linea("2026-09-22T05:39:00-0600", mem_full=0) + "\n",
        encoding="utf-8")
    s = carga(tmp_path)
    assert [v for _, v in s] == [0.0, 7.5]
    assert s[0][0] < s[1][0]
    assert s[0][0].tzinfo is None


def test_carga_mem_full_ausente_vale_cero(tmp_path):
    (tmp_path / "a.jsonl").write_text(
        _linea("2026-09-22T05:40:00-0600", io_some=3) + "\n", encoding="utf-8")
    assert carga(tmp_path) == [(T0, 0.0)]


# --- excursiones / duracion / clasificacion --------------------------------

def test_excursiones_cierra_la_racha_al_bajar_y_al_acabar():
    s = serie((0, 0), (1, 40), (2, 40), (3, 0), (4, 90), (5, 90))
    excs = excursiones(s, umbral=10)
    assert [len(e) for e in excs] == [2, 2]
    assert duracion_min(excs[0]) == 1.0


def test_excursiones_sin_ninguna():
    assert excursiones(serie((0, 0), (1, 4)), umbral=10) == []


@pytest.mark.parametrize("dur,esperado", [
    (0.0, "PICO"), (3.0, "PICO"), (4.0, "SIN OBSERVAR"), (5.0, "COLAPSO"), (999.0, "COLAPSO"),
])
def test_clasifica_las_tres_bandas(dur, esperado):
    assert clasifica(dur) == esperado


def test_clasifica_colapso_gana_cuando_las_bandas_se_solapan():
    # El bug real: con la banda de PICO delante, esto devolvia PICO y el
    # control negativo del fichero no podia salir en rojo.
    assert clasifica(0.0, pico_max=3.0, sostenido=0.0) == "COLAPSO"


# --- ventanas / solapa -----------------------------------------------------

def test_ventanas_por_defecto_son_los_congelamientos_reales():
    """Tres desde el 2026-09-24. Este test existe para que anadir un incidente
    sea un cambio DELIBERADO y no algo que se cuela: la lista es la verdad de
    referencia contra la que se mide el corte, y una lista rancia hace que el
    calibrador llame falso positivo a un colapso real -- que es exactamente lo
    que paso al aparecer el tercero."""
    vs = ventanas()
    assert len(vs) == 3
    assert vs[0][0] == dt.datetime(2026, 9, 22, 5, 45)
    assert vs[-1][0] == dt.datetime(2026, 9, 24, 0, 2)


def test_solapa_en_los_dos_bordes_y_fuera():
    v = (T0, T0 + dt.timedelta(minutes=10))
    assert solapa(serie((5, 90)), v) is True
    assert solapa(serie((-5, 90), (0, 90)), v) is True          # toca por la izquierda
    assert solapa(serie((-20, 90), (-10, 90)), v) is False      # acaba antes
    assert solapa(serie((20, 90), (30, 90)), v) is False        # empieza despues


# --- calibra ---------------------------------------------------------------

VENTANA = [("2026-09-22 05:45", "2026-09-22 06:30")]


def test_calibra_detecta_el_incidente_y_no_dispara_en_el_pico_sano():
    s = serie((0, 0), (1, 95), (2, 0),                    # pico sano: 0 min
              (5, 60), (11, 98), (20, 99), (40, 99))      # incidente: 35 min
    r = calibra(s, incidentes=VENTANA)
    assert len(r["colapsos"]) == 1
    assert len(r["picos"]) == 1
    assert r["falsos_positivos"] == []
    assert r["no_detectados"] == []
    assert r["cero"] == 2
    assert r["rango"][0] == "2026-09-22 05:40"


def test_calibra_cuenta_falso_positivo_fuera_de_ventana():
    s = serie((100, 90), (110, 90))          # sostenido pero fuera del incidente
    r = calibra(s, incidentes=VENTANA)
    assert len(r["falsos_positivos"]) == 1
    assert len(r["no_detectados"]) == 1      # y ademas no cubre el incidente


def test_calibra_marca_la_banda_sin_observar():
    r = calibra(serie((5, 90), (9, 90)), incidentes=VENTANA)
    assert len(r["sin_observar"]) == 1
    assert r["colapsos"] == []
    assert len(r["no_detectados"]) == 1


def test_calibra_serie_vacia_no_lanza():
    r = calibra([], incidentes=VENTANA)
    assert r["rango"] == ("", "")
    assert r["muestras"] == 0


# --- informe ---------------------------------------------------------------

def test_informe_imprime_los_ceros_y_el_detalle():
    texto = "\n".join(informe(calibra(serie((5, 60), (40, 99)), incidentes=VENTANA)))
    assert "falsos positivos:          0" in texto
    assert "incidentes no detectados:  0" in texto
    assert "SIN OBSERVAR               0" in texto      # el cero se imprime
    assert "09-22 05:45 (35 min, max 99.00 %)" in texto


# --- main ------------------------------------------------------------------

# `main` califica contra INCIDENTES, la verdad etiquetada real del modulo, y eso
# es deliberado: si las ventanas fueran un flag, cualquiera podria ablandar el
# gate moviendolas. Asi que el corpus sintetico se coloca SOBRE esas dos
# ventanas reales en vez de inventarse las suyas.
CORPUS_BUENO = [
    # pico sano, fuera de todo incidente: sube a 95 y baja en un minuto
    ("2026-09-21 10:00", 0), ("2026-09-21 10:01", 95), ("2026-09-21 10:02", 0),
    # congelamiento 1 (05:45 -> 23:30): sostenido 1035 min
    ("2026-09-22 05:45", 60), ("2026-09-22 06:00", 98), ("2026-09-22 23:00", 99),
    ("2026-09-22 23:35", 0),
    # congelamiento 2 (23:49 -> 05:44): sostenido 311 min
    ("2026-09-22 23:49", 98), ("2026-09-23 05:00", 99),
    ("2026-09-23 05:50", 0),
    # congelamiento 3 (2026-09-24 00:02 -> 05:56): sostenido 354 min.
    # Anadido el 2026-09-24 al declararse el tercer incidente real. El corpus
    # sintetico se coloca SOBRE las ventanas reales, asi que al crecer
    # INCIDENTES tiene que crecer con el: si no, el tercero sale como
    # "incidente no detectado" y el control negativo de este fichero se pone
    # rojo por una laguna del corpus y no por un defecto del corte.
    ("2026-09-24 00:02", 98), ("2026-09-24 05:00", 99),
    ("2026-09-24 06:00", 0),
]


def _corpus(tmp_path, pares):
    d = tmp_path / "samples"
    d.mkdir()
    d.joinpath("x.jsonl").write_text("\n".join(
        _linea(dt.datetime.strptime(t, "%Y-%m-%d %H:%M").strftime("%Y-%m-%dT%H:%M:%S-0600"),
               mem_full=v)
        for t, v in pares) + "\n", encoding="utf-8")
    return d


def test_main_directorio_ausente_es_could_not_run(tmp_path, capsys):
    assert main(["--muestras", str(tmp_path / "no-existe")]) == 2
    assert "COULD_NOT_RUN" in capsys.readouterr().out


def test_main_corpus_sin_psi_es_could_not_run(tmp_path, capsys):
    d = tmp_path / "samples"
    d.mkdir()
    d.joinpath("x.jsonl").write_text("{}\n", encoding="utf-8")
    assert main(["--muestras", str(d)]) == 2
    assert "0 muestras con PSI" in capsys.readouterr().out


def test_main_corte_bueno_sale_cero(tmp_path, capsys):
    assert main(["--muestras", str(_corpus(tmp_path, CORPUS_BUENO))]) == 0
    salida = capsys.readouterr().out
    assert "VEREDICTO: CALIBRADO" in salida
    assert "falsos positivos:          0" in salida
    assert "incidentes no detectados:  0" in salida


def test_control_negativo_sin_corte_de_duracion_sale_uno(tmp_path, capsys):
    """Con --sostenido 0 el pico sano de 0 min pasa a COLAPSO: falso positivo."""
    d = _corpus(tmp_path, CORPUS_BUENO)
    assert main(["--muestras", str(d), "--sostenido", "0"]) == 1
    salida = capsys.readouterr().out
    assert "VEREDICTO: CORTE INVALIDO" in salida
    assert "falsos positivos:          1" in salida


def test_control_negativo_corte_demasiado_largo_deja_pasar_el_incidente(tmp_path, capsys):
    """Con el corte a 500 min se escapan DOS de los tres: el de 311 min y el de
    354. El primero dura 1035 y se sigue detectando, que es lo que hace de
    este un control y no un apagon -- si no detectara ninguno tampoco sabriamos
    si el corte discrimina o si el corpus esta vacio."""
    d = _corpus(tmp_path, CORPUS_BUENO)
    assert main(["--muestras", str(d), "--sostenido", "500"]) == 1
    assert "incidentes no detectados:  2" in capsys.readouterr().out


def test_main_usa_argv_cuando_no_se_le_pasa_nada(tmp_path, monkeypatch, capsys):
    d = _corpus(tmp_path, CORPUS_BUENO)
    monkeypatch.setattr(sys, "argv", ["calibra_psi.py", "--muestras", str(d)])
    assert main() == 0
    assert "VEREDICTO" in capsys.readouterr().out
