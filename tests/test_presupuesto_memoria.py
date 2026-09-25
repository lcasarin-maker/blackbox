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


def _firma(gib=1000.0, dias=30, owner="lcasarin (prueba)", reason="control de la suite"):
    """Una declaracion de excursion VALIDA. Por defecto autoriza mas que
    cualquier serie de los tests, para que la mitad 2 no contamine a la mitad 1:
    un test que quiere medir la aritmetica tiene que fallar por la aritmetica."""
    import datetime
    return {"excursion_gib": gib, "owner": owner, "reason": reason,
            "expires": str(datetime.date.today() + datetime.timedelta(days=dias))}


def _montar(monkeypatch, tmp_path, **kw):
    monkeypatch.setattr(pm, "CGROUP", _cgroups(tmp_path, **{k: v for k, v in kw.items()
                                                            if k.endswith("_max")}))
    monkeypatch.setattr(pm, "MEMINFO", _meminfo(tmp_path, kw.get("mem_kb", 126980000)))
    monkeypatch.setattr(pm, "DATA_DIR", tmp_path)
    _muestras(tmp_path, kw.get("picos", [1024]))
    monkeypatch.setattr(pm, "RESERVA_GPU_GIB", kw.get("reserva", 86.0))
    # La declaracion se apunta SIEMPRE a tmp_path, tambien cuando no se escribe:
    # si no, el test leeria el fichero real del repo y su veredicto dependeria
    # de si alguien firmo hoy. Un test que depende del estado del repo no mide
    # el codigo.
    decl = tmp_path / "presupuesto_gpu.json"
    if kw.get("firma") is not None:
        decl.write_text(json.dumps(kw["firma"]), encoding="utf-8")
    monkeypatch.setattr(pm, "DECLARACION", decl)


def test_falla_con_el_reparto_real_de_esta_maquina(monkeypatch, tmp_path, capsys):
    """El control negativo que la ficha exigia literalmente: "el gate tiene que
    FALLAR con el reparto de hoy (125G sobre 121.1). Si pasa, no mide".

    Con la reserva de GPU contada son 168.3 sobre 121.1.
    """
    # Serie realista: una meseta de 50 GiB y un pico de 85, que es la forma
    # medida en esta maquina. El suelo comprometido sale de la meseta.
    _montar(monkeypatch, tmp_path, system_max=str(4 * 1024**3),
            picos=[50 * 1024] * 20 + [85 * 1024], firma=_firma())
    assert pm.main(["--check"]) == 1
    err = capsys.readouterr().err
    # Falla por la ARITMETICA, con la excursion ya firmada: 50 + 48 + 32 + 4.
    assert "los compromisos NO componen" in err, err


def test_pasa_cuando_los_techos_SI_caben(monkeypatch, tmp_path):
    """La otra direccion, sin la cual el de arriba no significa nada: un gate
    que no puede salir en verde no mide, solo bloquea."""
    _montar(monkeypatch, tmp_path, app_max=str(8 * 1024**3), docker_max=str(8 * 1024**3),
            system_max=str(4 * 1024**3), reserva=40.0, firma=_firma())
    assert pm.main(["--check"]) == 0


def test_un_slice_SIN_techo_se_cuenta_y_se_DICE(monkeypatch, tmp_path, capsys):
    """Un slice sin techo no se puede presupuestar, solo observar. Meterlo en la
    suma callando que es una observacion seria presentar un numero de hoy como
    un compromiso."""
    _montar(monkeypatch, tmp_path, app_max=str(8 * 1024**3), docker_max=str(8 * 1024**3),
            system_max="max", reserva=40.0, firma=_firma())
    rc = pm.main(["--check"])
    err = capsys.readouterr().err
    assert rc == 1 and "sin techo" in err


def test_una_firma_que_se_quedo_CORTA_se_caza_con_las_propias_muestras(
        monkeypatch, tmp_path, capsys):
    """Heredera directa de `test_la_reserva_VIEJA`: un numero firmado una vez y
    nunca releido es el techo sin calibrar que esta ficha vino a quitar.

    Ahora el numero lo firma una persona, y el control es el mismo: si las
    muestras ya vieron mas de lo que la firma autoriza, el gate lo dice y nombra
    las dos cifras."""
    _montar(monkeypatch, tmp_path, app_max=str(1024**3), docker_max=str(1024**3),
            system_max=str(1024**3), picos=[40 * 1024], firma=_firma(gib=10.0))
    rc = pm.main(["--check"])
    err = capsys.readouterr().err
    assert rc == 1 and "se PASO de lo firmado" in err, err
    assert "40.0" in err and "10.0" in err, err


def test_una_firma_CADUCADA_no_vale(monkeypatch, tmp_path, capsys):
    """Una suspension sin caducidad se vuelve permanente en silencio -- los 59
    hooks de Cerberus, "temporalmente" desactivados el 2026-08-01 y nunca
    restaurados. Aqui la caducidad es obligatoria Y se comprueba: el dia
    siguiente a `expires` el gate vuelve a bloquear, para que se discuta en vez
    de renovarse sola."""
    _montar(monkeypatch, tmp_path, app_max=str(1024**3), docker_max=str(1024**3),
            system_max=str(1024**3), picos=[1024], firma=_firma(gib=1000.0, dias=-1))
    rc = pm.main(["--check"])
    err = capsys.readouterr().err
    assert rc == 1 and "CADUCO" in err, err


def test_control_negativo_la_MISMA_firma_un_dia_antes_SI_vale(monkeypatch, tmp_path):
    """Sin esto, el de arriba tambien pasaria con una firma que no vale nunca.
    Mismo fichero, misma maquina, un dia de diferencia: verde."""
    _montar(monkeypatch, tmp_path, app_max=str(1024**3), docker_max=str(1024**3),
            system_max=str(1024**3), picos=[1024], firma=_firma(gib=1000.0, dias=0))
    assert pm.main(["--check"]) == 0


def test_una_firma_SIN_dueno_no_vale(monkeypatch, tmp_path, capsys):
    """Una declaracion sin dueno no la viene a discutir nadie cuando caduque."""
    f = _firma()
    del f["owner"]
    _montar(monkeypatch, tmp_path, app_max=str(1024**3), docker_max=str(1024**3),
            system_max=str(1024**3), firma=f)
    rc = pm.main(["--check"])
    assert rc == 1 and "owner" in capsys.readouterr().err


def test_sin_firma_es_ROJO_y_lo_DICE(monkeypatch, tmp_path, capsys):
    """El estado por defecto. Un reparto que compone perfectamente sigue en rojo
    mientras nadie firme la excursion, porque la excursion no la acota ningun
    cgroup: solo la acota una persona diciendo que la acepta."""
    _montar(monkeypatch, tmp_path, app_max=str(1024**3), docker_max=str(1024**3),
            system_max=str(1024**3), picos=[1024])   # sin firma
    rc = pm.main(["--check"])
    err = capsys.readouterr().err
    assert rc == 1 and "nadie ha firmado" in err, err


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
            system_max=str(1024**3), reserva=40.0, firma=_firma())
    rc = pm.main(["--check"])
    salida = capsys.readouterr()
    assert "could_not_run" not in salida.out and rc == 0, salida


# =====================================================================
# los caminos que NO son el feliz: cada uno tiene que decir la verdad
# =====================================================================


def test_meminfo_sin_la_linea_MemTotal_devuelve_None(tmp_path, monkeypatch):
    """Un /proc/meminfo que existe pero no trae MemTotal no es un MemTotal de 0:
    es un instrumento que no contesta lo que se le pregunta."""
    f = tmp_path / "meminfo"
    f.write_text("MemFree:  1 kB\nBuffers:  2 kB\n", encoding="utf-8")
    monkeypatch.setattr(pm, "MEMINFO", f)
    assert pm.mem_total_gib() is None


def test_meminfo_con_basura_devuelve_None_y_no_revienta(tmp_path, monkeypatch):
    f = tmp_path / "meminfo"
    f.write_text("MemTotal:       no-soy-un-numero kB\n", encoding="utf-8")
    monkeypatch.setattr(pm, "MEMINFO", f)
    assert pm.mem_total_gib() is None


def test_un_cgroup_que_no_existe_no_tiene_techo_ni_uso(tmp_path):
    """Distinto de tener techo 0: no hay sujeto que leer."""
    d = tmp_path / "no-existe"
    assert pm.techo_gib(d) is None
    assert pm.uso_gib(d) == 0.0


def test_memory_current_ilegible_cuenta_como_cero_y_no_revienta(tmp_path):
    """El uso es informativo; que falte no puede tumbar el presupuesto entero."""
    d = tmp_path / "cg"
    d.mkdir()
    (d / "memory.current").write_text("basura\n", encoding="utf-8")
    assert pm.uso_gib(d) == 0.0


def test_un_directorio_de_muestras_SIN_PERMISO_se_registra(tmp_path):
    """"No se pudo comprobar" no es "no hay picos".

    Este caso existe porque la primera version envolvia el glob en
    `try/except OSError` y eso NO servia: medido, `Path.glob` no lanza sobre un
    directorio sin permisos -- devuelve vacio. La rama era inalcanzable y el
    efecto real era que un directorio ilegible se leia como "no hay muestras".
    Ahora el permiso se comprueba antes, con `os.access`, y eso si puede fallar.
    """
    d = tmp_path / "samples"
    d.mkdir()
    (d / "x.jsonl").write_text('{"gpu":[{"mib":5}]}\n', encoding="utf-8")
    d.chmod(0o000)
    try:
        assert pm.pico_gpu_observado_mib(d) is None
        assert any("sin permiso" in x for x in pm._ILEGIBLES), pm._ILEGIBLES
    finally:
        d.chmod(0o755)


def test_un_directorio_de_muestras_que_NO_ES_un_directorio_se_registra(tmp_path):
    """Si alguien deja un fichero donde deberia estar `samples/`, `Path.glob`
    tambien devuelve vacio en silencio."""
    f = tmp_path / "samples"
    f.write_text("no soy un directorio", encoding="utf-8")
    assert pm.pico_gpu_observado_mib(f) is None
    assert any("no es un directorio" in x for x in pm._ILEGIBLES), pm._ILEGIBLES


def test_lineas_que_no_son_una_muestra_de_GPU_se_saltan_sin_ruido(tmp_path):
    """El jsonl mezcla muestras, rafagas y eventos. Las que no traen `gpu`, las
    que no parsean y las que traen la lista vacia no son errores: son el resto
    del fichero. Lo que NO puede pasar es que una de ellas cuente como un pico.
    """
    d = tmp_path / "samples"
    d.mkdir()
    (d / "x.jsonl").write_text(
        '{"ts":"a","burst":true,"load1":1}\n'          # sin campo gpu
        'esto no es json\n'                            # no parsea, y no dice gpu
        '{"ts":"z","gpu":[{"mib":99999  <-- truncada\n'  # DICE gpu y NO parsea:
        #    una linea a medio escribir, que es lo que deja un corte de energia
        #    en un fichero de solo-anadir. Si contara, el pico seria inventado.
        '{"ts":"b","gpu":[]}\n'                        # gpu vacio
        '{"ts":"c","gpu":[{"pid":1,"mib":700}]}\n',    # el unico real
        encoding="utf-8")
    pico = pm.pico_gpu_observado_mib(d)
    assert pico == (700, "c"), pico


def test_un_slice_AUSENTE_se_dice_y_no_se_cuenta(tmp_path, monkeypatch, capsys):
    """Un cgroup que no esta en esta maquina no puede entrar en la suma como 0:
    eso haria que el presupuesto cuadrara por no encontrar al sujeto."""
    raiz = _cgroups(tmp_path)
    import shutil
    shutil.rmtree(raiz / "docker.slice")
    monkeypatch.setattr(pm, "CGROUP", raiz)
    monkeypatch.setattr(pm, "MEMINFO", _meminfo(tmp_path))
    monkeypatch.setattr(pm, "DATA_DIR", tmp_path)
    _muestras(tmp_path, [1024])
    monkeypatch.setattr(pm, "RESERVA_GPU_GIB", 10.0)
    pm.main([])
    salida = capsys.readouterr().out
    assert "AUSENTE" in salida, salida
    # y los 32 GiB de docker NO estan en la suma
    assert "docker" in salida and "32.0 GiB" not in salida.split("AUSENTE")[0].split("docker")[-1]


def test_sin_muestras_el_informe_dice_COULD_NOT_RUN_y_no_calla(tmp_path, monkeypatch, capsys):
    """Un informe sin la fila del pico es un informe que perdio una fila; uno
    que la imprime vacia miente. Se imprime COULD_NOT_RUN."""
    monkeypatch.setattr(pm, "CGROUP", _cgroups(tmp_path))
    monkeypatch.setattr(pm, "MEMINFO", _meminfo(tmp_path))
    monkeypatch.setattr(pm, "DATA_DIR", tmp_path / "vacio")
    pm.main([])
    assert "COULD_NOT_RUN" in capsys.readouterr().out


def test_sin_check_informa_y_sale_cero_aunque_no_componga(tmp_path, monkeypatch, capsys):
    """Informar y bloquear son cosas distintas: sin `--check` esto es un
    informe, y un informe no decide."""
    _montar(monkeypatch, tmp_path)   # reparto que NO compone
    assert pm.main([]) == 0
    assert "SUMA comprometida" in capsys.readouterr().out


def test_json_saca_la_cuenta_entera_sin_veredicto(tmp_path, monkeypatch, capsys):
    """Para que otro lo consuma sin parsear texto -- y sin que el formato de
    salida decida nada."""
    _montar(monkeypatch, tmp_path, system_max=str(4 * 1024**3),
            picos=[50 * 1024] * 20 + [85 * 1024], firma=_firma())
    assert pm.main(["--json"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["mem_total_gib"] > 0 and d["gasto_gib"] > d["mem_total_gib"]
    assert [f["nombre"] for f in d["slices"]], d
    # Las DOS mitades viajan en el JSON, o quien lo consuma solo ve una.
    assert d["suelo_gpu"]["muestras"] == 21 and d["declaracion"]["owner"], d


# =====================================================================
# el presupuesto de GPU y las excursiones del abanico
# =====================================================================


def test_el_presupuesto_de_GPU_se_RESTA_no_se_elige(monkeypatch, tmp_path):
    """El umbral de la alarma del abanico no es un numero puesto a ojo: es lo
    que le queda a la memoria unificada si todos los techos declarados se
    honran. MemTotal - techos - lo que usan los slices sin techo.

    Esto importa porque el numero decide si la alarma sirve: medido el
    2026-09-25 sobre 18 944 muestras, con docker.slice en 32G el corte cae en
    37.1 GiB y se supera el 75.4 % del tiempo (ruido); con 16G cae en 53.1 y se
    supera el 0.9 % (senal). Mediana observada 49.0, p90 50.1.
    """
    G = 1024 ** 3
    monkeypatch.setattr(pm, "CGROUP", _cgroups(tmp_path, app_max=str(48 * G),
                                               docker_max=str(16 * G),
                                               system_max="max"))
    monkeypatch.setattr(pm, "MEMINFO", _meminfo(tmp_path))   # 121.1 GiB
    monkeypatch.setattr(pm, "DATA_DIR", tmp_path)
    _muestras(tmp_path, [1024])
    p = pm.presupuesto()
    # 121.1 - 48 - 16 - 2 (lo que usa el slice sin techo en el fixture)
    assert 54.0 < p["presupuesto_gpu_gib"] < 56.0, p["presupuesto_gpu_gib"]


def test_un_docker_slice_mas_ancho_ESTRECHA_el_presupuesto_de_GPU(
        monkeypatch, tmp_path):
    """La otra mitad, y es la que justifica haber bajado docker.slice de 32 a
    16: cada GiB que un techo reclama es un GiB que la GPU no puede tomar sin
    romper la suma. Con el techo ancho el umbral cae DENTRO de la operacion
    normal y la alarma deja de discriminar."""
    G = 1024 ** 3
    monkeypatch.setattr(pm, "MEMINFO", _meminfo(tmp_path))
    monkeypatch.setattr(pm, "DATA_DIR", tmp_path)
    _muestras(tmp_path, [1024])
    monkeypatch.setattr(pm, "CGROUP", _cgroups(tmp_path, app_max=str(48 * G),
                                               docker_max=str(32 * G),
                                               system_max="max"))
    estrecho = pm.presupuesto()["presupuesto_gpu_gib"]
    monkeypatch.setattr(pm, "CGROUP", _cgroups(tmp_path, app_max=str(48 * G),
                                               docker_max=str(16 * G),
                                               system_max="max"))
    ancho = pm.presupuesto()["presupuesto_gpu_gib"]
    assert ancho - estrecho == pytest.approx(16.0, abs=0.1), (estrecho, ancho)


def test_las_excursiones_cuentan_lo_que_PASA_del_presupuesto(tmp_path):
    """Lo que agota la maquina es la suma simultanea por encima del umbral, y
    lo que hace util la alarma es que se pueda contar cuantas veces paso."""
    d = tmp_path / "samples"
    d.mkdir()
    filas = [json.dumps({"ts": f"2026-09-2{i}T00:00:00-0600",
                         "gpu": [{"pid": 1, "mib": mib}]})
             for i, mib in enumerate([10 * 1024, 60 * 1024, 20 * 1024, 70 * 1024])]
    (d / "x.jsonl").write_text("\n".join(filas) + "\n", encoding="utf-8")
    pm.pico_gpu_observado_mib(d)          # llena la serie
    ex = pm.excursiones_gpu(50.0)
    assert ex["muestras"] == 4 and ex["por_encima"] == 2, ex
    assert ex["pct"] == pytest.approx(50.0), ex
    assert [m for _, m in ex["ultimas"]] == [60 * 1024, 70 * 1024], ex["ultimas"]


def test_control_negativo_bajo_el_presupuesto_no_hay_excursiones(tmp_path):
    """Si contara igual, la alarma estaria encendida siempre y no diria nada."""
    d = tmp_path / "samples"
    d.mkdir()
    (d / "x.jsonl").write_text(
        json.dumps({"ts": "a", "gpu": [{"mib": 10 * 1024}]}) + "\n", encoding="utf-8")
    pm.pico_gpu_observado_mib(d)
    ex = pm.excursiones_gpu(50.0)
    assert ex["por_encima"] == 0 and ex["muestras"] == 1, ex


def test_control_negativo_serie_vacia_no_es_cero_excursiones(tmp_path):
    """`muestras: 0` dice "no se midio". Reportar "0 excursiones" sobre una
    serie vacia seria afirmar que el abanico se porta, que es justo lo que no
    se sabe."""
    pm.pico_gpu_observado_mib(tmp_path / "no-existe")
    ex = pm.excursiones_gpu(50.0)
    assert ex["muestras"] == 0 and ex["por_encima"] == 0


def test_el_informe_NOMBRA_las_ultimas_excursiones_con_su_fecha(
        monkeypatch, tmp_path, capsys):
    """Un porcentaje sin fechas no sirve para diagnosticar: "el 0.9 % del
    tiempo" no dice si fue anoche o hace tres semanas. El informe imprime las
    tres ultimas con su marca de tiempo y su tamano.
    """
    G = 1024 ** 3
    monkeypatch.setattr(pm, "CGROUP", _cgroups(tmp_path, app_max=str(48 * G),
                                               docker_max=str(16 * G),
                                               system_max="max"))
    monkeypatch.setattr(pm, "MEMINFO", _meminfo(tmp_path))
    monkeypatch.setattr(pm, "DATA_DIR", tmp_path)
    # una por debajo del presupuesto (~55 GiB) y dos por encima
    d = tmp_path / "samples"
    d.mkdir(parents=True, exist_ok=True)
    (d / "x.jsonl").write_text("\n".join(
        json.dumps({"ts": ts, "gpu": [{"pid": 1, "mib": mib}]})
        for ts, mib in (("2026-09-20T01:00:00-0600", 10 * 1024),
                        ("2026-09-21T00:33:00-0600", 85 * 1024),
                        ("2026-09-25T11:32:00-0600", 70 * 1024))) + "\n",
        encoding="utf-8")
    pm.main([])
    salida = capsys.readouterr().out
    assert "excursiones: 2 de 3" in salida, salida
    assert "2026-09-21T00:33:00-0600" in salida and "85.0 GiB" in salida, salida
    assert "2026-09-20" not in salida.split("excursiones")[1], "la que cabe no es una excursion"


# =====================================================================
# el suelo comprometido: que sea la MESETA y no el maximo
# =====================================================================


def test_el_suelo_es_la_MESETA_y_no_el_pico(monkeypatch, tmp_path):
    """Este test existe porque su ausencia se midio.

    El 2026-09-25, mutando `suelo_gpu_gib` para que devolviera `v[-1]` -- o sea
    volviendo al criterio-muro que usaba el maximo observado-- la suite entera
    seguia VERDE: 31 de 31. Nada fijaba la diferencia entre el suelo comprometido
    y el pico, que es justo el cambio que esta ficha vino a hacer.

    Un cambio que nadie caza es un cambio que va a volver en silencio.
    """
    # 20 muestras de meseta a 50 GiB y UNA espiga de 85, que es la forma medida
    # en esta maquina: p50 49.05, p95 50.15, max 85.40.
    _montar(monkeypatch, tmp_path, picos=[50 * 1024] * 20 + [85 * 1024])
    pm.pico_gpu_observado_mib()          # llena la serie
    s = pm.suelo_gpu_gib()
    assert s is not None
    assert s["gib"] == 50.0, s           # la meseta
    assert s["max"] == 85.0, s           # el pico, que viaja aparte y NO se resta
    # Y la distancia entre los dos es exactamente lo que la mitad 2 obliga a
    # firmar. Si el suelo fuera el pico, esto seria 0 y no habria nada que firmar.
    assert s["max"] - s["gib"] == 35.0, s


def test_control_negativo_el_suelo_SIGUE_a_la_serie_y_no_es_una_constante(
        monkeypatch, tmp_path):
    """Sin esto, el de arriba se cumple con un suelo puesto a mano en 50.

    Tambien medido: con `suelo_gpu_gib` devolviendo un `50.0` literal, la suite
    seguia verde con 33 de 33, porque las dos series de los tests daban 50. Asi
    que esta usa OTRA meseta, 30 GiB: un numero constante ya no puede pasar por
    los dos. Y una serie plana no tiene excursion -- suelo y pico coinciden."""
    _montar(monkeypatch, tmp_path, picos=[30 * 1024] * 21)
    pm.pico_gpu_observado_mib()
    s = pm.suelo_gpu_gib()
    assert s["gib"] == 30.0 and s["max"] == 30.0, s
