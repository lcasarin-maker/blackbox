"""Suite de `tools/nombra_victimas.py` (DEBT-DGX-438-SIN-CAUSA-RAIZ).

El modulo existe porque `auditd` no emite `type=OBJ_PID` para las reglas de
senal de este repo, asi que la victima solo se conoce por su pid. Lo que se
prueba aqui, sobre todo, es que NO atribuye de mas: su primera version reporto
12 capturas como "sujeto de DGX-438" cuando eran `rustdesk` limpiando sus hijos
a traves de `pkill`, y eso manda a buscar un culpable llamado `kill`.
"""

from __future__ import annotations

import json

import pytest

from tools import nombra_victimas as nv


def _cap(**kw):
    base = {"ts": 1790500000, "id": "1790500000.1", "senal": "SIGTERM",
            "emisor": {"pid": 100, "ppid": 50, "comm": "algo",
                       "exe": "/usr/bin/algo", "auid": "4294967295",
                       "clase": "demonio"},
            "victima": {"pid": "200", "comm": "?"}}
    for k, v in kw.items():
        if k in ("emisor", "victima"):
            base[k] = {**base[k], **v}
        else:
            base[k] = v
    return base


def _escribe(tmp_path, caps, muestra_pids=()):
    c = tmp_path / "sigterm.jsonl"
    c.write_text("\n".join(json.dumps(x) for x in caps) + "\n", encoding="utf-8")
    m = tmp_path / "samples"; m.mkdir(parents=True, exist_ok=True)
    top = [{"pid": p, "comm": n, "unit": f"{n}.service"} for p, n in muestra_pids]
    (m / "a.jsonl").write_text(
        json.dumps({"ts": "2026-09-27T02:00:00-0600", "top_rss": top}) + "\n",
        encoding="utf-8")
    return c, m


# ------------------------------------ atribucion: el ppid, no el nombre


def test_la_victima_que_ES_el_padre_del_emisor_es_autolimpieza():
    """El caso literal de esta caja: `pkill` invocado por el proceso al que mata.
    Se reconoce por el dato (`victima.pid == emisor.ppid`), no por el nombre."""
    c = _cap(emisor={"comm": "pkill", "ppid": 777}, victima={"pid": "777"})
    assert nv.es_autolimpieza(c) is True


def test_un_ENVOLTORIO_no_atribuye_por_su_nombre():
    """`kill` matando a `rustdesk` NO es "un demonio mata cosas": es que alguien
    uso kill. Sin el padre no se sabe quien, y eso es atribucion incompleta --
    ni sujeto ni descarte."""
    c = _cap(emisor={"comm": "/usr/bin/kill", "ppid": 999},
             victima={"pid": "200", "comm": "rustdesk"})
    assert nv.es_autolimpieza(c) is False
    assert nv.atribucion_incompleta(c) is True


def test_control_negativo_un_emisor_REAL_con_victima_ajena_SI_es_el_sujeto():
    """Sin este test los dos de arriba pasarian con un modulo que clasificara
    todo como incompleto y nunca encontrara nada."""
    c = _cap(emisor={"comm": "earlyoom", "ppid": 1},
             victima={"pid": "200", "comm": "python3"})
    assert nv.es_autolimpieza(c) is False
    assert nv.atribucion_incompleta(c) is False


def test_mismo_nombre_sin_envoltorio_sigue_siendo_autolimpieza():
    c = _cap(emisor={"comm": "rustdesk", "ppid": 1},
             victima={"pid": "200", "comm": "rustdesk"})
    assert nv.es_autolimpieza(c) is True


@pytest.mark.parametrize("ppid", [None, 0, "", "x"])
def test_un_ppid_ausente_o_ilegible_no_lanza(ppid):
    c = _cap(emisor={"comm": "kill", "ppid": ppid}, victima={"pid": "200"})
    assert nv.es_autolimpieza(c) is False


# ------------------------------------ el nombrado


def test_nombra_desde_las_muestras_y_DICE_cuando_no_puede(tmp_path):
    caps = [_cap(victima={"pid": "4242"}), _cap(victima={"pid": "9999"})]
    c, m = _escribe(tmp_path, caps, muestra_pids=[(4242, "vllm")])
    ns = nv.nombra(nv.capturas(c), nv.indice_pids(m))
    assert ns[0]["victima"]["comm"] == "vllm"
    assert ns[0]["victima"]["nombrada"] is True
    assert ns[1]["victima"]["nombrada"] is False
    assert "ninguna muestra" in ns[1]["victima"]["comm"], (
        "una victima sin nombre tiene que DECIRLO, no quedarse con un '?' que se "
        "lee como un nombre raro")


def test_una_linea_mala_en_las_capturas_se_ignora(tmp_path):
    c = tmp_path / "s.jsonl"
    c.write_text("{roto\n" + json.dumps(_cap()) + "\n", encoding="utf-8")
    assert len(nv.capturas(c)) == 1


# ------------------------------------ las salidas


def test_sin_capturas_es_COULD_NOT_RUN(tmp_path, capsys):
    rc = nv.main(["--capturas", str(tmp_path / "no-hay"),
                  "--muestras", str(tmp_path)])
    assert rc == 2
    assert "COULD_NOT_RUN" in capsys.readouterr().err


def test_sin_muestras_es_COULD_NOT_RUN(tmp_path, capsys):
    c, _ = _escribe(tmp_path, [_cap()])
    rc = nv.main(["--capturas", str(c), "--muestras", str(tmp_path / "vacio")])
    assert rc == 2
    assert "no hay con que nombrar" in capsys.readouterr().err


def test_el_informe_separa_sujeto_de_autolimpieza_y_de_incompleta(tmp_path, capsys):
    caps = [
        _cap(emisor={"comm": "pkill", "ppid": 777}, victima={"pid": "777"}),
        _cap(emisor={"comm": "kill", "ppid": 888}, victima={"pid": "200"}),
        _cap(emisor={"comm": "earlyoom", "ppid": 1}, victima={"pid": "300"}),
    ]
    c, m = _escribe(tmp_path, caps, muestra_pids=[(777, "rustdesk"), (200, "rustdesk"),
                                                 (300, "python3")])
    rc = nv.main(["--capturas", str(c), "--muestras", str(m)])
    salida = capsys.readouterr().out
    assert rc == 0
    assert "autolimpieza" in salida
    assert "ATRIBUCION INCOMPLETA" in salida
    assert "SUJETO DE DGX-438 (emisor demonio, victima ajena y nombrada): 1" in salida, salida


def test_la_marca_del_grupo_cuenta_cuantas_no_dice_alguna(tmp_path, capsys):
    """Marcar un grupo entero porque UNA fila coincide hace que dos filas
    distintas se lean como la misma. Se vio en la salida real: `3 pkill ->
    (sin nombre) [autolimpieza]` con 1 de 3."""
    caps = [_cap(emisor={"comm": "pkill", "ppid": 777}, victima={"pid": "777", "comm": "x"}),
            _cap(emisor={"comm": "pkill", "ppid": 777}, victima={"pid": "777", "comm": "x"})]
    # una tercera del MISMO grupo que no es autolimpieza
    caps.append(_cap(emisor={"comm": "pkill", "ppid": 555}, victima={"pid": "777", "comm": "x"}))
    c, m = _escribe(tmp_path, caps, muestra_pids=[(777, "x")])
    nv.main(["--capturas", str(c), "--muestras", str(m)])
    salida = capsys.readouterr().out
    assert "[2 de 3 autolimpieza]" in salida, salida


# ------------------------------------ entrada malformada en las MUESTRAS
#
# El corpus es de produccion: una linea truncada o una lista con formas raras no
# puede tumbar el nombrado, y tampoco colarse como un pid.


@pytest.mark.parametrize("muestra, porque", [
    ("{roto", "JSON invalido"),
    ('{"ts":"x","top_rss":"no soy una lista"}', "la lista no es una lista"),
    ('{"ts":"x","top_rss":["no soy un dict"]}', "el elemento no es un dict"),
    ('{"ts":"x","top_rss":[{"comm":"sin_pid"}]}', "sin pid"),
    ('{"ts":"x","top_rss":[{"pid":"4242","comm":"pid de texto"}]}', "pid no es int"),
])
def test_una_muestra_mala_no_tumba_el_indice(tmp_path, muestra, porque):
    m = tmp_path / "samples"; m.mkdir(parents=True)
    buena = '{"ts":"y","cpu_top":[{"pid":7,"comm":"bueno","unit":"u.service"}]}'
    (m / "a.jsonl").write_text(muestra + "\n" + buena + "\n", encoding="utf-8")
    idx = nv.indice_pids(m)
    assert idx == {7: ("bueno", "u.service")}, f"({porque}) -> {idx}"


def test_la_primera_vista_de_un_pid_es_la_que_manda(tmp_path):
    """Declarado en el docstring del modulo: se queda con la primera. Este test
    lo fija para que cambiarlo sea deliberado."""
    m = tmp_path / "samples"; m.mkdir(parents=True)
    (m / "a.jsonl").write_text(
        '{"ts":"1","top_rss":[{"pid":9,"comm":"primero","unit":"a"}]}\n'
        '{"ts":"2","top_rss":[{"pid":9,"comm":"segundo","unit":"b"}]}\n',
        encoding="utf-8")
    assert nv.indice_pids(m)[9] == ("primero", "a")


def test_una_victima_con_pid_ilegible_no_lanza_y_se_marca(tmp_path):
    caps = [_cap(victima={"pid": "no-soy-un-pid"})]
    c, m = _escribe(tmp_path, caps, muestra_pids=[(1, "x")])
    ns = nv.nombra(nv.capturas(c), nv.indice_pids(m))
    assert ns[0]["victima"]["nombrada"] is False


def test_solo_demonios_filtra_los_humanos(tmp_path, capsys):
    caps = [_cap(emisor={"clase": "demonio", "comm": "earlyoom", "ppid": 1}),
            _cap(emisor={"clase": "humano", "comm": "yo", "ppid": 1})]
    c, m = _escribe(tmp_path, caps, muestra_pids=[(200, "python3")])
    nv.main(["--capturas", str(c), "--muestras", str(m), "--solo-demonios"])
    assert "capturas: 1" in capsys.readouterr().out


def test_una_captura_sin_bloque_emisor_no_lanza(tmp_path, capsys):
    c = tmp_path / "s.jsonl"
    c.write_text(json.dumps({"ts": 1, "senal": "SIGTERM"}) + "\n", encoding="utf-8")
    m = tmp_path / "samples"; m.mkdir()
    (m / "a.jsonl").write_text(
        '{"ts":"1","top_rss":[{"pid":1,"comm":"x","unit":"u"}]}\n', encoding="utf-8")
    assert nv.main(["--capturas", str(c), "--muestras", str(m)]) == 0


def test_una_linea_en_blanco_no_cuenta_como_captura(tmp_path):
    """El fichero lo escribe un `printf` en bucle desde bash: una linea vacia al
    final es normal y no puede contarse como una captura sin campos."""
    c = tmp_path / "s.jsonl"
    c.write_text("\n" + json.dumps(_cap()) + "\n\n   \n", encoding="utf-8")
    assert len(nv.capturas(c)) == 1


# --- El signo de `a0`: un pid negativo es un GRUPO de procesos -------------
#
# Encontrado el 2026-09-27 leyendo la salida del propio modulo, no el codigo:
# la columna de victima traia `4294965290`, que no es un pid sino -2006 leido
# sin signo. 44 de 314 capturas (14.0 %) venian asi y eran innombrables por
# construccion; otras 28 traian `0`, que es `kill(0, sig)` -- el propio grupo
# del emisor-- y se contaban como misterio.


@pytest.mark.parametrize("crudo,esperado,porque", [
    (4294965974, -1322, "la forma SIN signo que traen las capturas ya acumuladas"),
    (-1322, -1322, "la forma con signo que `bin/bb` escribe desde el arreglo"),
    (0, 0, "kill(0, sig): el propio grupo del emisor, y 0 es un valor legitimo"),
    ("200", 200, "un pid normal en texto, que es como llega del jsonl"),
    ("no-un-numero", None, "ilegible se dice, no se adivina"),
    (None, None, "ausente se dice, no se adivina"),
])
def test_normaliza_pid_lee_las_dos_formas(crudo, esperado, porque):
    assert nv.normaliza_pid(crudo) == esperado, porque


def test_un_grupo_se_nombra_por_su_LIDER_y_lo_dice(tmp_path):
    """El caso que el defecto hacia imposible: `a0` sin signo de un grupo.

    Control negativo del arreglo: con el codigo previo esta captura salia
    `nombrada=False` porque buscaba el pid 4294965974 en el indice. Si alguien
    quita `normaliza_pid` de `nombra`, este test vuelve a rojo.
    """
    caps = [_cap(victima={"pid": 4294965974})]
    idx = {1322: ("postgres", "postgresql.service")}
    v = nv.nombra(caps, idx)[0]["victima"]
    assert v["grupo"] is True
    assert v["nombrada"] is True
    assert v["comm"] == "postgres (y su grupo)", (
        "nombrar al lider no afirma que muriera el lider: murio el grupo, y la "
        "etiqueta tiene que decirlo o el informe afirma mas de lo que sabe")


def test_kill_cero_es_autolimpieza_por_POSIX(tmp_path):
    """`kill(0, sig)` va contra el propio grupo del emisor, sin cruzar nada.

    Control negativo: con el codigo previo daba False -- `0` no casaba con
    ningun ppid-- y las 28 capturas de `timeout` entraban en el misterio.
    """
    c = _cap(victima={"pid": 0}, emisor={"comm": "timeout", "ppid": 50})
    assert nv.es_autolimpieza(c) is True
    assert nv.es_autolimpieza(_cap(victima={"pid": 999})) is False, (
        "y no absuelve a cualquiera: un pid ajeno sigue sin ser autolimpieza")


def test_un_grupo_cuyo_LIDER_es_el_padre_del_emisor_es_su_arbol():
    """`pkill -g` desde un hijo contra el grupo del padre.

    El signo distingue el caso: -50 es el grupo 50, y 50 es el ppid del emisor.
    """
    assert nv.es_autolimpieza(_cap(victima={"pid": -50},
                                   emisor={"ppid": 50, "comm": "pkill"})) is True
    assert nv.es_autolimpieza(_cap(victima={"pid": -77},
                                   emisor={"ppid": 50, "comm": "pkill"})) is False, (
        "el grupo de OTRO no es el arbol del emisor")
