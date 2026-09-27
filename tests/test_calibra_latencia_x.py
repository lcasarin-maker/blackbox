"""Suite de `tools/calibra_latencia_x.py`, el calibrador del corte de latencia
del escritorio (DEBT-SLUGGISH-SIN-CAUSA-PROBADA y
DEBT-BB-USABLE-CIEGO-A-LA-LATENCIA, que comparten el mismo numero).

Lo que mas importa aqui son las TRES salidas, y sobre todo la de negarse.
`bb-usable` actua con `FailureAction=reboot-immediate`: un calibrador que
devolviera un corte plausible sin lado positivo contra el que medirlo le daria
permiso para reiniciar la maquina por un numero inventado.

  rc=0  CALIBRADO
  rc=1  ninguna combinacion separa (hay etiqueta, no hay corte)
  rc=2  COULD_NOT_RUN: no hay episodio etiquetado con muestras
"""

from __future__ import annotations

import datetime as dt
import json

import pytest

from tools import calibra_latencia_x as cal


def _serie(pares, base=dt.datetime(2026, 9, 26, 3, 0)):
    """[(minuto, x_ms, smi_ms)] -> la forma que devuelve carga()."""
    return [(base + dt.timedelta(minutes=m), float(x), float(s))
            for m, x, s in pares]


def _muestras(tmp_path, pares, base=dt.datetime(2026, 9, 26, 3, 0)):
    """Escribe un corpus jsonl con la forma real de bin/bb."""
    d = tmp_path / "samples"; d.mkdir(parents=True, exist_ok=True)
    lineas = []
    for m, x, s in pares:
        t = (base + dt.timedelta(minutes=m)).strftime("%Y-%m-%dT%H:%M:%S-0600")
        lineas.append(json.dumps({"ts": t,
                                  "x": {"estado": "OK", "ms": x},
                                  "smi": {"estado": "OK", "ms": s}}))
    (d / "2026-09-26.jsonl").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return d


def _snaps(tmp_path, cuando, razon):
    d = tmp_path / "snapshots" / f"{cuando:%Y-%m-%dT%H%M%S}_x"
    d.mkdir(parents=True, exist_ok=True)
    (d / "reason.txt").write_text(razon, encoding="utf-8")
    (d / "when.txt").write_text(cuando.isoformat(), encoding="utf-8")
    return tmp_path / "snapshots"


# ------------------------------------ la regla de tres partes


def test_el_muestreador_desalojado_NO_cuenta_como_escritorio_lento():
    """La mitad que evita leer el instrumento en vez del sujeto.

    Medido sobre 2234 muestras con los dos canales OK: r = 0.631 entre x.ms y
    smi.ms. Cuando bb es desalojado los dos se inflan juntos, asi que una x.ms
    alta con smi.ms alta no dice nada del escritorio.
    """
    # Una sola muestra lentisima, pero con el muestreador tambien lentisimo.
    serie = _serie([(0, 5, 20), (1, 2000, 3000), (2, 5, 20)])
    etiq = [(serie[1][0] - dt.timedelta(minutes=1),
             serie[1][0] + dt.timedelta(minutes=1), "prueba")]
    fp, nd = cal.evalua(serie, etiq, corte_ms=100, sostenido=1)
    assert len(nd) == 1, "una x.ms alta con smi.ms alta no puede cubrir la etiqueta"
    assert fp == []


def test_control_negativo_la_MISMA_lentitud_con_muestreador_sano_SI_cuenta():
    """El par del de arriba. Sin el, la regla se 'arregla' no disparando nunca."""
    serie = _serie([(0, 5, 20), (1, 2000, 25), (2, 5, 20)])
    etiq = [(serie[1][0] - dt.timedelta(minutes=1),
             serie[1][0] + dt.timedelta(minutes=1), "prueba")]
    fp, nd = cal.evalua(serie, etiq, corte_ms=100, sostenido=1)
    assert nd == [], "con el muestreador sano, esa muestra SI es del escritorio"
    assert fp == []


def test_la_duracion_exige_muestras_SEGUIDAS_no_acumuladas():
    """Tres picos aislados no son un episodio sostenido. Sin este reset, la
    duracion se cumpliria sumando picos de dias distintos."""
    serie = _serie([(0, 500, 20), (1, 5, 20), (2, 500, 20), (3, 5, 20),
                    (4, 500, 20)])
    fp, nd = cal.evalua(serie, [], corte_ms=100, sostenido=2)
    assert fp == [], "tres picos aislados no cumplen una racha de 2"
    # y dos seguidas SI
    serie2 = _serie([(0, 500, 20), (1, 500, 20)])
    fp2, _ = cal.evalua(serie2, [], corte_ms=100, sostenido=2)
    assert len(fp2) == 1, "dos muestras seguidas son una racha de 2"


# ------------------------------------ las tres salidas


def test_sin_etiqueta_es_COULD_NOT_RUN_y_no_un_corte(tmp_path, capsys):
    """rc=2, y es la salida que de verdad protege. Un calibrador que devolviera
    un numero plausible sin lado positivo le daria a bb-usable permiso para
    reiniciar la maquina por una intuicion."""
    m = _muestras(tmp_path, [(i, 5, 20) for i in range(30)])
    rc = cal.main(["--muestras", str(m), "--snapshots", str(tmp_path / "no-hay")])
    assert rc == 2
    salida = capsys.readouterr()
    assert "COULD_NOT_RUN" in salida.err
    assert "bb snapshot" in salida.out, (
        "negarse sin decir como se consigue una etiqueta obliga a quien lo lea "
        "a ir a buscarlo")


def test_con_etiqueta_y_senal_separable_sale_CALIBRADO(tmp_path, capsys):
    """rc=0. Sin este test, los dos de abajo pasarian con un modulo que se
    negara siempre -- y negarse siempre es indistinguible de estar roto."""
    # 40 muestras sanas y DOS seguidas lentas, con el muestreador sano.
    pares = [(i, 5, 20) for i in range(40)]
    pares[20] = (20, 900, 25); pares[21] = (21, 900, 25)
    m = _muestras(tmp_path, pares)
    cuando = dt.datetime(2026, 9, 26, 3, 21)
    sn = _snaps(tmp_path, cuando, "el escritorio no responde, no se puede teclear")
    rc = cal.main(["--muestras", str(m), "--snapshots", str(sn)])
    salida = capsys.readouterr().out
    assert rc == 0, salida
    assert "CALIBRADO" in salida


def test_con_etiqueta_pero_sin_corte_que_separe_sale_1(tmp_path, capsys):
    """rc=1, que es distinto de rc=2: aqui SI habia contra que medir y ninguna
    combinacion separo. Es el estado real del corpus de esta maquina."""
    # La etiqueta cae sobre una muestra lenta, pero hay otras igual de lentas
    # FUERA de la etiqueta: ningun nivel las distingue.
    pares = [(i, 5, 20) for i in range(40)]
    for i in (10, 20, 30):
        pares[i] = (i, 900, 25)
    m = _muestras(tmp_path, pares)
    sn = _snaps(tmp_path, dt.datetime(2026, 9, 26, 3, 20), "inusable para teclear")
    rc = cal.main(["--muestras", str(m), "--snapshots", str(sn)])
    salida = capsys.readouterr().out
    assert rc == 1, salida
    assert "NINGUN CORTE SEPARA" in salida


def test_sin_muestras_es_COULD_NOT_RUN(tmp_path, capsys):
    rc = cal.main(["--muestras", str(tmp_path / "vacio")])
    assert rc == 2
    assert "COULD_NOT_RUN" in capsys.readouterr().err


# ------------------------------------ que cuenta como etiqueta


def test_un_snapshot_con_motivo_cualquiera_NO_es_una_etiqueta(tmp_path):
    """`bb snapshot` se toma por muchas razones y su motivo por defecto es
    "manual". Tratar cualquiera como etiqueta de inusabilidad meteria ruido en
    el lado POSITIVO, que es el lado caro: un falso positivo ahi afloja el
    corte y termina reiniciando la maquina de mas."""
    sn = _snaps(tmp_path, dt.datetime(2026, 9, 26, 3, 20), "manual")
    assert cal.etiquetas(sn) == cal.etiquetas(tmp_path / "no-existe"), (
        "un snapshot 'manual' no puede contar como episodio de inusabilidad")


@pytest.mark.parametrize("razon", [
    "el escritorio no responde", "sumamente sluggish", "inusable para teclear",
    "todo muy lento", "se congelo la GUI"])
def test_los_motivos_que_SI_etiquetan(tmp_path, razon):
    sn = _snaps(tmp_path, dt.datetime(2026, 9, 26, 3, 20), razon)
    assert len(cal.etiquetas(sn)) == len(cal.EPISODIOS_DECLARADOS) + 1, (
        f"{razon!r} describe un escritorio inusable y tiene que etiquetar")


def test_el_episodio_declarado_del_2026_09_25_esta_y_NO_tiene_muestras(tmp_path):
    """El unico episodio que una persona declaro, y la razon de que este modulo
    se niegue hoy: la sonda de x empezo a grabar a las 05:40 y el reinicio a
    mano fue a las 05:08. 32 minutos tarde."""
    vs = cal.etiquetas(tmp_path / "no-existe")
    assert len(vs) == 1
    assert vs[0][0] == dt.datetime(2026, 9, 25, 4, 8)
    # Y sobre una serie que empieza despues, no es utilizable.
    serie = _serie([(i, 5, 20) for i in range(10)],
                   base=dt.datetime(2026, 9, 25, 5, 40))
    assert cal.con_muestras(vs, serie) == [], (
        "el episodio etiquetado no tiene muestras y no puede ser el positivo")


# ------------------------------------ entrada malformada: se ignora, no tumba
#
# El corpus es de produccion. Una linea truncada por un corte de luz, o una
# muestra de rafaga sin el campo x, no pueden tumbar la calibracion -- pero
# tampoco pueden colarse como datos.


@pytest.mark.parametrize("linea, porque", [
    ('{roto', "JSON invalido"),
    ('{"ts":"2026-09-26T03:00:00-0600"}', "sin x ni smi"),
    ('{"ts":"2026-09-26T03:00:00-0600","x":5,"smi":{"estado":"OK","ms":20}}',
     "x no es un dict"),
    ('{"ts":"2026-09-26T03:00:00-0600","x":{"estado":"AUSENTE"},'
     '"smi":{"estado":"OK","ms":20}}', "x sin DISPLAY"),
    ('{"ts":"2026-09-26T03:00:00-0600","x":{"estado":"OK","ms":"mucho"},'
     '"smi":{"estado":"OK","ms":20}}', "ms no es un numero"),
    ('{"ts":"ayer","x":{"estado":"OK","ms":5},"smi":{"estado":"OK","ms":20}}',
     "ts no parseable"),
])
def test_una_linea_mala_se_ignora_y_no_tumba_la_carga(tmp_path, linea, porque):
    d = tmp_path / "samples"; d.mkdir(parents=True)
    buena = ('{"ts":"2026-09-26T03:05:00-0600","x":{"estado":"OK","ms":7},'
             '"smi":{"estado":"OK","ms":21}}')
    (d / "a.jsonl").write_text(linea + "\n" + buena + "\n", encoding="utf-8")
    serie = cal.carga(d)
    assert len(serie) == 1, f"la linea mala ({porque}) se colo o tumbo la carga"
    assert serie[0][1] == 7.0


def test_un_snapshot_incompleto_o_con_fecha_mala_no_etiqueta(tmp_path):
    """Dos formas de snapshot que no sirven, y ninguna puede lanzar."""
    base = tmp_path / "snapshots"
    # sin when.txt
    a = base / "sin_when"; a.mkdir(parents=True)
    (a / "reason.txt").write_text("inusable", encoding="utf-8")
    # con when.txt ilegible como fecha
    b = base / "fecha_mala"; b.mkdir(parents=True)
    (b / "reason.txt").write_text("inusable", encoding="utf-8")
    (b / "when.txt").write_text("el martes", encoding="utf-8")
    assert cal.etiquetas(base) == cal.etiquetas(tmp_path / "no-existe")


def test_el_control_negativo_pone_la_etiqueta_donde_el_muestreador_ESTA_sano(
        tmp_path, capsys):
    """`--etiqueta-de-prueba` existe para comprobar que este modulo PUEDE dar un
    veredicto, y por eso la etiqueta va sobre la peor muestra CON EL MUESTREADOR
    SANO y no sobre la peor del corpus.

    Medido el 2026-09-27: la peor de todas (1234 ms) tenia smi = 1818, o sea el
    muestreador desalojado, y la regla conjunta se niega -- correctamente -- a
    llamarla lentitud del escritorio. Poniendo la etiqueta ahi, el control solo
    podia llegar a rc=1, y un control que no alcanza el camino del exito no
    prueba que ese camino exista.
    """
    pares = [(i, 5, 20) for i in range(30)]
    pares[10] = (10, 5000, 4000)   # lentisima, pero muestreador desalojado
    pares[20] = (20, 400, 25)      # menos lenta, muestreador SANO
    m = _muestras(tmp_path, pares)
    rc = cal.main(["--muestras", str(m), "--snapshots", str(tmp_path / "no-hay"),
                   "--etiqueta-de-prueba"])
    salida = capsys.readouterr().out
    assert "SINTETICA sobre la peor muestra con muestreador sano" in salida
    assert "x=400 ms" in salida, (
        f"la etiqueta cayo sobre la muestra con el muestreador desalojado:\n{salida}")
    assert rc in (0, 1), salida


def test_el_control_negativo_sin_muestras_sanas_es_COULD_NOT_RUN(tmp_path, capsys):
    """Si TODAS las muestras tienen el muestreador desalojado, el control no
    tiene donde poner su etiqueta y lo dice en vez de elegir una mala."""
    m = _muestras(tmp_path, [(i, 100, 5000) for i in range(10)])
    rc = cal.main(["--muestras", str(m), "--snapshots", str(tmp_path / "no-hay"),
                   "--etiqueta-de-prueba"])
    assert rc == 2
    assert "ni una muestra con el muestreador sano" in capsys.readouterr().err


def test_las_lineas_descartadas_se_CUENTAN_por_motivo(tmp_path):
    """"0 muestras utiles" tiene que poder distinguirse de "20 000 lineas
    descartadas por una razon que nadie miro".

    Medido en la maquina el 2026-09-27, la primera vez que se imprimio: 18 109
    de ~20 800 lineas descartadas por no traer x ni smi -- el 87 % del corpus --
    y 4 por JSON invalido, que es corrupcion real en la serie. Nada de eso se
    veia antes.
    """
    d = tmp_path / "samples"; d.mkdir(parents=True)
    (d / "a.jsonl").write_text(
        "{roto\n"
        '{"ts":"2026-09-26T03:00:00-0600"}\n'
        '{"ts":"2026-09-26T03:01:00-0600","x":{"estado":"AUSENTE"},'
        '"smi":{"estado":"OK","ms":20}}\n'
        '{"ts":"2026-09-26T03:02:00-0600","x":{"estado":"OK","ms":"x"},'
        '"smi":{"estado":"OK","ms":20}}\n'
        '{"ts":"manana","x":{"estado":"OK","ms":5},"smi":{"estado":"OK","ms":20}}\n'
        '{"ts":"2026-09-26T03:03:00-0600","x":{"estado":"OK","ms":5},'
        '"smi":{"estado":"OK","ms":20}}\n',
        encoding="utf-8")
    c: dict = {}
    serie = carga_con = cal.carga(d, c)
    assert len(serie) == 1
    assert c == {"json invalido": 1, "sin x o sin smi": 1, "un canal no OK": 1,
                 "ms no numerico": 1, "ts no parseable": 1}, c


def test_una_linea_en_blanco_no_cuenta_como_descartada(tmp_path):
    """El fichero lo escribe bash: lineas vacias son normales y no son un
    descarte que reportar."""
    d = tmp_path / "samples"; d.mkdir(parents=True)
    (d / "a.jsonl").write_text(
        "\n   \n"
        '{"ts":"2026-09-26T03:00:00-0600","x":{"estado":"OK","ms":5},'
        '"smi":{"estado":"OK","ms":20}}\n', encoding="utf-8")
    c: dict = {}
    assert len(cal.carga(d, c)) == 1
    assert c == {}


def test_el_informe_IMPRIME_las_descartadas(tmp_path, capsys):
    d = tmp_path / "samples"; d.mkdir(parents=True)
    (d / "a.jsonl").write_text("{roto\n", encoding="utf-8")
    cal.main(["--muestras", str(d), "--snapshots", str(tmp_path / "no-hay")])
    assert "lineas descartadas: 1 por json invalido" in capsys.readouterr().out
