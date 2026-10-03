"""Suite de `tools/calibra_techo_slice.py` -- que sepa decir TODAVIA NO.

## Por que existe

`DEBT-TECHOS-SIN-CALIBRAR` se quedo trabada en su ultimo eslabon: `system.slice`
sin techo, 5.3 GiB de holgura para ponerselo, y nada con que elegir el numero
salvo su `memory.peak` de un arranque. El unico que impedia que ese numero se
eligiera a ojo el dia que hubiera serie era la buena voluntad de quien lo
hiciera.

Lo que esta suite guarda NO es la multiplicacion -- eso es `max * 1.4`-- sino
que el modulo se NIEGUE cuando la serie no lo sostiene. Un calibrador que
siempre emite un numero no es un calibrador: es una multiplicacion con un
informe bonito.

Los tres frenos, cada uno con su control en la direccion contraria:

  pocas muestras           -> se niega   |  suficientes -> emite
  el maximo TODAVIA crece  -> se niega   |  estabilizado -> emite
  el slice no aparece      -> se niega   |  y no dice que el maximo es 0
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import calibra_techo_slice as ct


def _muestras(tmp_path, filas, nombre="system"):
    """Escribe una serie de muestras con bloque `slices`.

    `filas` son (cur_gib, peak_gib). `peak_gib` a None escribe `null`, que es lo
    que hace bb en un kernel sin `memory.peak`.
    """
    d = tmp_path / "samples"
    d.mkdir(parents=True, exist_ok=True)
    lineas = []
    for i, (cur, pk) in enumerate(filas):
        lineas.append(json.dumps({
            "ts": f"2026-09-25T{i // 3600:02d}:{i // 60 % 60:02d}:{i % 60:02d}-0600",
            "slices": [{"slice": nombre,
                        "cur_kb": int(cur * 1024 ** 2),
                        "peak_kb": None if pk is None else int(pk * 1024 ** 2)}],
        }))
    (d / "2026-09-25.jsonl").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return d


def _plana(n, cur: float = 2.0, pk: float | None = 2.8):
    """Una serie estable: el maximo no se mueve en toda la ventana."""
    return [(cur, pk)] * n


# =====================================================================
# freno 1: el minimo de muestras
# =====================================================================


def test_con_el_pico_de_UN_arranque_se_NIEGA(tmp_path, capsys):
    """El caso literal que dejo la ficha abierta: 8 h 19 min de un arranque son
    unas 500 muestras a una por minuto, y de ahi no sale un techo."""
    d = _muestras(tmp_path, _plana(499))
    r = ct.calibra("system", d)
    assert r["propuesto_gib"] is None, r
    assert any("minimo declarado" in x for x in r["faltas"]), r["faltas"]


def test_control_negativo_con_la_serie_COMPLETA_si_propone(tmp_path):
    """La otra direccion, sin la cual el de arriba solo dice que el modulo sabe
    negarse. Con el minimo cumplido y el maximo quieto, emite."""
    d = _muestras(tmp_path, _plana(ct.MINIMO_MUESTRAS))
    r = ct.calibra("system", d)
    assert r["faltas"] == [], r["faltas"]
    assert r["propuesto_gib"] == round(2.8 * ct.FACTOR, 1), r


def test_una_muestra_MENOS_del_minimo_ya_se_niega(tmp_path):
    """El borde, y es el que convierte el minimo en un umbral y no en una
    decoracion."""
    d = _muestras(tmp_path, _plana(ct.MINIMO_MUESTRAS - 1))
    assert ct.calibra("system", d)["propuesto_gib"] is None


# =====================================================================
# freno 2: el maximo todavia crece -- el que de verdad protege
# =====================================================================


def test_si_el_maximo_TODAVIA_CRECE_se_niega_aunque_haya_muestras_de_sobra(tmp_path):
    """Este es el freno que vale, y por eso tiene su propio test.

    Una serie que aun sube no ha visto el peor caso. Un techo puesto sobre ella
    se queda corto POR CONSTRUCCION: mata procesos la primera vez que el slice
    haga lo que siempre iba a hacer.
    """
    n = ct.MINIMO_MUESTRAS
    # Dos tercios quietos en 2.8 y una cola que llega a 9.0: maximo nuevo.
    filas = _plana(int(n * 0.7)) + [(8.0, 9.0)] * (n - int(n * 0.7))
    r = ct.calibra("system", _muestras(tmp_path, filas))
    assert r["propuesto_gib"] is None, r
    assert any("TODAVIA CRECE" in x for x in r["faltas"]), r["faltas"]
    # Y nombra las dos cifras: un "todavia no" sin numeros no se puede discutir.
    # `approx` porque los GiB pasan por KiB enteros al escribir la muestra, igual
    # que en la maquina real: 2.8 GiB vuelve como 2.799999237.
    assert r["estabilidad"]["cola"] == pytest.approx(9.0), r
    assert r["estabilidad"]["cabeza"] == pytest.approx(2.8, abs=1e-5), r


def test_control_negativo_un_pico_en_la_CABEZA_no_bloquea(tmp_path):
    """La direccion contraria del mismo freno, y no es simetrica: un maximo
    alto al PRINCIPIO que la cola no vuelve a alcanzar es justo la senal de que
    la serie ya vio el peor caso. Si esto bloqueara, el calibrador no podria
    emitir nunca sobre una maquina que tuvo su pico y se calmo."""
    n = ct.MINIMO_MUESTRAS
    filas = [(8.0, 9.0)] * 10 + _plana(n - 10)
    r = ct.calibra("system", _muestras(tmp_path, filas))
    assert r["faltas"] == [], r["faltas"]
    assert r["propuesto_gib"] == round(9.0 * ct.FACTOR, 1), r


def test_una_serie_demasiado_CORTA_para_comparar_dos_tramos_lo_dice(tmp_path):
    """Con tres muestras no hay dos tramos que comparar, y declarar "estable"
    sobre eso seria inventar la estabilidad."""
    r = ct.calibra("system", _muestras(tmp_path, _plana(3)))
    assert r["estable"] is False
    assert "demasiado corta" in r["estabilidad"]["porque"], r


# =====================================================================
# freno 3: el slice que no esta
# =====================================================================


def test_un_slice_que_NO_APARECE_no_tiene_un_maximo_de_cero(tmp_path, capsys):
    """Un 0 se multiplicaria por 1.4 y daria un techo de 0, que mata el slice
    entero. "No hay serie" y "el maximo es 0" no son lo mismo."""
    d = _muestras(tmp_path, _plana(ct.MINIMO_MUESTRAS), nombre="docker")
    r = ct.calibra("system", d)
    assert r["observado_gib"] is None and r["propuesto_gib"] is None, r
    assert any("no aparece en ninguna muestra" in x for x in r["faltas"]), r["faltas"]


def test_un_directorio_de_muestras_que_no_existe_se_registra(tmp_path):
    """No se pudo leer no es esta vacio."""
    r = ct.calibra("system", tmp_path / "no-existe")
    assert r["propuesto_gib"] is None
    assert any("no es un directorio" in x for x in r["ilegibles"]), r


def test_una_muestra_ILEGIBLE_no_se_traga_en_silencio(tmp_path, monkeypatch):
    """Un maximo calculado sobre un conjunto incompleto sale MAS BAJO de lo
    real, y un techo bajo mata procesos. Lo mismo que `silent_io_loop_swallow`
    cazo en presupuesto_memoria."""
    d = _muestras(tmp_path, _plana(ct.MINIMO_MUESTRAS))
    roto = d / "ilegible.jsonl"
    roto.write_text("{}\n", encoding="utf-8")
    read_text = Path.read_text

    def read_with_permission_error(path, *args, **kwargs):
        if path == roto:
            raise PermissionError(f"fixture: {path}")
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_with_permission_error)
    r = ct.calibra("system", d)
    assert roto.name in " ".join(r["ilegibles"]), r["ilegibles"]
    assert r["propuesto_gib"] is None, r
    assert any("ilegibles" in x for x in r["faltas"]), r["faltas"]


# =====================================================================
# el numero SIGUE a la serie, y no es una constante
# =====================================================================


@pytest.mark.parametrize("pico,espera", [(2.8, 3.9), (5.0, 7.0), (11.2, 15.7)])
def test_el_techo_propuesto_SIGUE_al_maximo_observado(tmp_path, pico, espera):
    """Sin esto, todo lo de arriba pasaria con un `return 3.9` fijo.

    El tercer caso es el de `docker.slice`: pico 11.2 GiB -> 15.7, y el techo
    que se le puso a mano fue 16G. Que el calibrador reproduzca por si solo la
    unica decision de este tipo que el repo ya tomo es lo que hace creible el
    factor."""
    d = _muestras(tmp_path, _plana(ct.MINIMO_MUESTRAS, cur=pico / 2, pk=pico))
    assert ct.calibra("system", d)["propuesto_gib"] == espera


def test_el_maximo_sale_del_mayor_de_current_y_peak(tmp_path):
    """`memory.peak` sabe de picos que ocurrieron ENTRE dos muestras y no
    dejaron rastro en `current`. Tomar solo `current` propondria un techo por
    debajo de algo que ya paso."""
    n = ct.MINIMO_MUESTRAS
    d = _muestras(tmp_path, _plana(n, cur=1.0, pk=7.0))
    assert ct.calibra("system", d)["observado_gib"] == 7.0


def test_sin_memory_peak_en_el_kernel_se_calibra_con_current(tmp_path):
    """Un kernel sin `memory.peak` escribe null. El modulo no se cae: usa lo que
    hay y el techo sale de `current`, que es peor pero no inventado."""
    d = _muestras(tmp_path, _plana(ct.MINIMO_MUESTRAS, cur=3.0, pk=None))
    r = ct.calibra("system", d)
    assert r["observado_gib"] == 3.0 and r["propuesto_gib"] == round(3.0 * ct.FACTOR, 1), r


# =====================================================================
# el informe: negarse tiene que DECIR que falta
# =====================================================================


def test_el_informe_dice_QUE_FALTA_y_sale_1(tmp_path, monkeypatch, capsys):
    """Un "no" sin motivo obliga a adivinar. Y sale 1, para que un guion lo
    pueda usar como puerta."""
    monkeypatch.setattr(ct, "DATA_DIR", tmp_path)
    _muestras(tmp_path, _plana(10))
    assert ct.main([]) == 1
    err = capsys.readouterr().err
    assert "SIN TECHO QUE PROPONER" in err and "minimo declarado" in err, err


def test_el_informe_del_caso_bueno_trae_la_DERIVACION_no_solo_el_numero(
        tmp_path, monkeypatch, capsys):
    """Un techo sin su derivacion al lado vuelve a ser un numero con una unidad
    detras, que es lo que la ficha vino a quitar."""
    monkeypatch.setattr(ct, "DATA_DIR", tmp_path)
    _muestras(tmp_path, _plana(ct.MINIMO_MUESTRAS))
    assert ct.main([]) == 0
    out = capsys.readouterr().out
    assert "PROPUESTO" in out and f"x {ct.FACTOR}" in out, out
    assert ct.FACTOR_VIENE_DE in out, out
    # Y dice que NO toca la maquina, porque proponer y aplicar son cosas
    # distintas y la segunda pide sudo.
    assert "NO toca la maquina" in out, out


def test_el_json_sale_1_cuando_no_hay_techo_y_0_cuando_si(tmp_path, monkeypatch, capsys):
    """El codigo de salida no depende del formato de salida. Un `--json` que
    saliera siempre 0 haria que un guion leyera "hay techo" sobre una negativa."""
    monkeypatch.setattr(ct, "DATA_DIR", tmp_path)
    _muestras(tmp_path, _plana(10))
    assert ct.main(["--json"]) == 1
    assert json.loads(capsys.readouterr().out)["propuesto_gib"] is None
    _muestras(tmp_path, _plana(ct.MINIMO_MUESTRAS))
    assert ct.main(["--json"]) == 0
    assert json.loads(capsys.readouterr().out)["propuesto_gib"] is not None


# =====================================================================
# los caminos que no son el feliz: cada uno tiene que decir la verdad
# =====================================================================


def test_un_directorio_SIN_PERMISO_se_registra_y_no_pasa_por_vacio(tmp_path, monkeypatch):
    """Un directorio ilegible que se leyera como "no hay muestras" haria que el
    calibrador dijera "el slice no aparece" -- una afirmacion sobre la maquina
    que nadie comprobo. Mismo fallo que `Path.glob` provoco en
    presupuesto_memoria: no lanza, devuelve vacio."""
    d = tmp_path / "samples"
    d.mkdir()
    access = ct.os.access

    def access_without_directory_permission(path, mode):
        if Path(path) == d:
            return False
        return access(path, mode)

    monkeypatch.setattr(ct.os, "access", access_without_directory_permission)
    r = ct.calibra("system", d)
    assert any("sin permiso" in x for x in r["ilegibles"]), r
    assert r["propuesto_gib"] is None


def test_lineas_que_no_son_una_muestra_se_saltan_sin_ruido(tmp_path):
    """El fichero de muestras es JSONL escrito por un proceso de vida larga:
    puede traer una linea a medias de un corte de energia. Una linea rota no
    puede tirar el calibrador ni contarse como muestra."""
    d = _muestras(tmp_path, _plana(ct.MINIMO_MUESTRAS))
    f = next(d.glob("*.jsonl"))
    f.write_text(f.read_text(encoding="utf-8")
                 + '{"ts": "2026-09-25T23:59:59-0600", "slices": [{"slice": "sys\n'
                 + '{"ts": "2026-09-26T00:00:00-0600", "slices": "no es una lista"}\n'
                 + '{"ts": "2026-09-26T00:00:01-0600", "slices": [{"slice": "system"}]}\n'
                 # Y una muestra de RAFAGA, que es un registro reducido y NO trae
                 # bloque `slices`. No es un caso inventado: bb las escribe cuando
                 # la maquina se mueve rapido, asi que el fichero real las tiene.
                 + '{"ts": "2026-09-26T00:00:02-0600", "burst": true, "pidio": []}\n',
                 encoding="utf-8")
    r = ct.calibra("system", d)
    # Las cuatro se saltan: la truncada no parsea, la segunda no trae lista de
    # dicts, la tercera no trae `cur_kb`, y la rafaga no trae `slices`. El
    # recuento no se mueve.
    assert r["muestras"] == ct.MINIMO_MUESTRAS, r["muestras"]
    assert r["propuesto_gib"] == round(2.8 * ct.FACTOR, 1), r


def test_el_informe_dice_COULD_NOT_RUN_cuando_no_hay_serie_que_leer(
        tmp_path, monkeypatch, capsys):
    """Y no imprime un maximo de 0.00 GiB, que se leeria como una medida."""
    monkeypatch.setattr(ct, "DATA_DIR", tmp_path)
    _muestras(tmp_path, _plana(5), nombre="docker")
    assert ct.main([]) == 1
    salida = capsys.readouterr()
    assert "COULD_NOT_RUN" in salida.out, salida.out
    assert "0.00 GiB" not in salida.out, salida.out


def test_el_informe_NOMBRA_los_ficheros_ilegibles(tmp_path, monkeypatch, capsys):
    """Un recuento sin nombres no sirve para ir a arreglarlo."""
    monkeypatch.setattr(ct, "DATA_DIR", tmp_path)
    d = _muestras(tmp_path, _plana(ct.MINIMO_MUESTRAS))
    roto = d / "ilegible.jsonl"
    roto.write_text("{}\n", encoding="utf-8")
    read_text = Path.read_text

    def read_with_permission_error(path, *args, **kwargs):
        if path == roto:
            raise PermissionError(f"fixture: {path}")
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_with_permission_error)
    rc = ct.main([])
    salida = capsys.readouterr()
    assert rc == 1 and "ilegible.jsonl" in salida.out, salida.out
