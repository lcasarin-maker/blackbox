"""Suite de bin/bb -- el ejecutable bash que es el grueso de este repo.

## Por que existe

`bin/bb` es bash y queda FUERA de `coverage_targets` (la autodeteccion busca
paquetes Python). Durante meses eso se declaro como hueco y se dejo asi, y el
precio de esa costumbre esta medido: `bin/bb-usable` tampoco tenia pruebas, su
premisa fundacional era falsa, y dejo pasar TRES congelamientos antes de que
un cuarto la falsificara.

Un hueco declarado sigue siendo un hueco. Esto lo cierra para los caminos que
deciden algo: el techo de memoria por aplicacion, la atribucion de quien pidio
memoria, el disparador de la rafaga y el veredicto de "instrumento armado".

## Lo que esta suite NO compra, dicho antes de que alguien lo suponga

La cobertura SI esta medida desde el 2026-09-24 -- `tools/cobertura_bash.sh`
traza el ejecutable con BASH_XTRACEFD -- y da **17.6 %**, 146 de 829 lineas.
Ese numero es el hallazgo, no la solucion: lo que hay son pruebas de
comportamiento sobre los caminos que DECIDEN algo, cada una con su control
negativo. `tools/piso_cobertura.sh` impide que baje sin que nadie se entere.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

BB = Path(__file__).resolve().parent.parent / "bin" / "bb"


def correr(args, datos=None, extra_env=None, timeout=120):
    env = dict(os.environ)
    if datos is not None:
        env["BLACKBOX_DATA"] = str(datos)
    env.update(extra_env or {})
    return subprocess.run([str(BB), *args], capture_output=True, text=True,
                          env=env, timeout=timeout)


@pytest.fixture
def datos(tmp_path):
    d = tmp_path / "blackbox"
    (d / "samples").mkdir(parents=True)
    return d


def _cpu_segundos(pid):
    """Segundos de CPU acumulados de un pid, como los lee bb (`ps -o times=`)."""
    r = subprocess.run(["ps", "-o", "times=", "-p", str(pid)],
                       capture_output=True, text=True)
    return int(r.stdout.strip() or 0)


def _no_esta_pero_los_cinco_queman_mas(lista, campo, mio, sujeto):
    """El invariante REAL de una lista `sort -rn | head -5`.

    `pidio` y `cpu_top` prometen EL TOP 5, no "tu proceso". Que el proceso de un
    test no salga no es un fallo del sujeto si habia cinco mas calientes: es la
    maquina ocupada. Lo que si seria un fallo es que la lista soltara al mio
    mientras nombra a alguien MAS FRIO, y eso es lo que se comprueba aqui.

    Medido el 2026-09-25: `test_cpu_top_NOMBRA_a_quien_quema_cpu` fallo dentro
    del `pre-push` -- con la suite entera corriendo-- y paso 3 de 3 con la
    maquina en reposo. La asercion de pertenencia era la que estaba mal, no bb.
    Es tambien la explicacion que le faltaba al fallo de
    `test_pidio_NOMBRA_a_quien_pide_memoria` que quedo sin reproducir, y que se
    commiteo como inexplicado: misma forma, mismo `head -5`.
    """
    assert len(lista) == 5, (
        f"{sujeto} no nombro al mio y la lista NO esta llena ({len(lista)} de 5): "
        f"habia sitio y no lo uso. {lista}")
    frios = [x for x in lista if x[campo] < mio]
    assert not frios, (
        f"{sujeto} solto al mio ({mio}) y nombro a estos, que son MAS FRIOS: {frios}")


def muestras(datos):
    """Las muestras COMPLETAS. Las de rafaga se filtran, y no es cosmetica.

    El muestreo adaptativo escribe un registro REDUCIDO -- sin `cpu_top`, sin
    `top_rss`, sin `swap`-- cuando la maquina se mueve rapido. Un test que lee
    `muestras(datos)[-1]["cpu_top"]` revienta con `KeyError` si justo la ultima
    linea fue una rafaga, y eso depende de la carga de la maquina, no del sujeto.

    Medido el 2026-09-25: corriendo la suite entera,
    `test_control_negativo_un_proceso_dormido_no_sale_como_que_quema` fallo con
    `KeyError: 'cpu_top'`. Tercera instancia del mismo modo de fallo en esta
    misma pasada -- las otras dos fueron las aserciones de pertenencia a las
    listas `head -5`. Los cuatro tests que SI quieren ver rafagas leen el
    fichero por su cuenta con `_leer`, asi que este filtro no les quita nada.
    """
    f = next((datos / "samples").glob("*.jsonl"), None)
    if f is None:
        return []
    todas = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [m for m in todas if not m.get("burst")]


# =====================================================================
# bb cap -- el techo de memoria por aplicacion
# =====================================================================


def test_cap_rechaza_argumentos_invalidos(datos):
    """Un techo mal escrito no puede arrancar el programa SIN techo: eso seria
    peor que fallar, porque el usuario creeria estar protegido."""
    for args in (["cap"], ["cap", "abc", "true"], ["cap", "16"]):
        r = correr(args, datos)
        assert r.returncode == 2, f"{args} deberia rechazarse, dio rc={r.returncode}"
        assert "uso:" in r.stderr or "falta el comando" in r.stderr


def test_cap_MATA_lo_que_se_pasa_del_techo(datos):
    """El caso que motiva todo: un programa que pide mas de lo permitido muere
    DENTRO de su cgroup, sin tocar al resto de la maquina."""
    r = correr(["cap", "1", sys.executable, "-c",
                "import mmap; m=mmap.mmap(-1, 3*1024**3); m.write(b'x'*(3*1024**3))"],
               datos, timeout=180)
    assert r.returncode != 0, "pedir 3 GiB con techo de 1G tiene que morir"
    assert "bajo techo de 1G" in r.stderr


def test_control_negativo_cap_deja_pasar_lo_que_cabe(datos):
    """Sin esto, el test de arriba no distingue "el techo mata" de "bb cap
    siempre falla"."""
    r = correr(["cap", "6", sys.executable, "-c",
                "import mmap; m=mmap.mmap(-1, 2*1024**3); m.write(b'x'*(2*1024**3)); print('ok')"],
               datos, timeout=180)
    assert r.returncode == 0, f"2 GiB bajo techo de 6G deberia caber: {r.stderr[-400:]}"
    assert "ok" in r.stdout


def test_cap_anuncia_el_techo_que_aplica(datos):
    """El usuario tiene que poder ver en el log con que numero se lanzo algo;
    si no, un techo mal puesto es indistinguible de ninguno."""
    r = correr(["cap", "2", "true"], datos)
    assert "bajo techo de 2G" in r.stderr


# =====================================================================
# bb sample -- la muestra y sus campos nuevos
# =====================================================================


def test_sample_escribe_json_valido_con_los_campos_que_decide(datos):
    correr(["sample"], datos)
    m = muestras(datos)
    assert len(m) == 1
    d = m[0]
    for campo in ("ts", "mem_free_kb", "mem_avail_kb", "commit_pct",
                  "residuo_mb", "pidio", "psi", "top_rss", "gpu"):
        assert campo in d, f"falta {campo}"
    assert isinstance(d["pidio"], list)
    assert 0 <= float(d["commit_pct"]) <= 1000


def test_commit_pct_es_un_porcentaje_real_no_un_cero_de_adorno(datos):
    """Fue el indicador ADELANTADO del cuarto congelamiento (33.64 -> 87.81 en
    un minuto). Un campo que siempre valiera 0 se leeria como maquina sana."""
    correr(["sample"], datos)
    v = float(muestras(datos)[0]["commit_pct"])
    assert v > 0, "una maquina con procesos siempre tiene algo comprometido"


@pytest.mark.sleeps_aceptados
def test_pidio_NOMBRA_a_quien_pide_memoria(datos):
    """El hueco que Committed_AS no cerraba: decia cuanto, no quien."""
    correr(["sample"], datos)                      # muestra 1: linea base
    # El hijo AVISA cuando ya reservo, en vez de que aqui se adivine cuanto
    # tarda. La exencion de sunset decia "no hay evento que compartir con un
    # hijo que reserva memoria" y era falso: su stdout es el evento. Sustituido
    # en la revision de 1.4, que es para lo que existe el sunset.
    hijo = subprocess.Popen(
        [sys.executable, "-c",
         "import mmap,sys,time; m=mmap.mmap(-1, 5*1024**3); "
         "print('listo', flush=True); time.sleep(20)"],
        stdout=subprocess.PIPE, text=True)
    try:
        assert hijo.stdout is not None
        assert hijo.stdout.readline().strip() == "listo", "el hijo no llego a reservar"
        correr(["sample"], datos)                  # muestra 2: ya crecio
        d = muestras(datos)[-1]
        crecidos = {x["pid"]: x for x in d["pidio"]}
        if hijo.pid not in crecidos:
            # Mismo `head -5` que `cpu_top`, y el mismo modo de fallo bajo carga.
            _no_esta_pero_los_cinco_queman_mas(
                d["pidio"], "crecio_kb", 5 * 1024 ** 2, "pidio")
            return
        gb = crecidos[hijo.pid]["crecio_kb"] / 1048576
        assert 4.5 < gb < 5.5, f"deberia ver ~5 GiB, vio {gb:.2f}"
    finally:
        hijo.kill(); hijo.wait()


@pytest.mark.sleeps_aceptados
def test_control_negativo_un_proceso_que_NO_pide_no_sale_nombrado(datos):
    """Sin esto, el test de arriba no distingue "atribuye" de "lista a todo el
    mundo".

    NO se asierta que `pidio` este vacio: esta maquina tiene ~500 procesos
    propios y cualquiera puede crecer durante el test -- la primera version de
    este control fallaba de forma intermitente porque soffice.bin crecio 534 MB
    por su cuenta. Un test que depende de que la maquina este quieta no es un
    control, es una moneda al aire. Lo que SI se controla es un proceso propio
    que existe en las dos muestras y no pide nada: ese no puede salir.
    """
    # Igual que arriba: el hijo avisa de que ya existe. La exencion decia que
    # sondear /proc/<pid> "seria cambiar un sleep por otro", y tenia razon en
    # eso -- pero leer su stdout no es un sondeo, es esperar un evento.
    quieto = subprocess.Popen(
        [sys.executable, "-c", "import time; print('listo', flush=True); time.sleep(20)"],
        stdout=subprocess.PIPE, text=True)
    try:
        assert quieto.stdout is not None and quieto.stdout.readline().strip() == "listo"
        correr(["sample"], datos)
        # Sin sleep desde el 2026-09-28: DEBT-ACCEPTED-SLEEP-TESTS-BB cerro aqui.
        # Leido bin/bb (topvsz, `prev_vsz`): la deteccion de crecimiento diffea
        # dos snapshots de `ps -eo vsz` SIN ninguna puerta de tiempo -- a
        # diferencia de cputop/swap (mas abajo), que SI dependen de `dt` con
        # resolucion de segundo entero (ver L342). No habia nada que la espera
        # sostuviera: 10/10 corridas con sleep(0) dieron el mismo resultado
        # (pidio vacio, la asercion pasa) que con sleep(2). La debilidad que la
        # exencion 1.9 declaraba ("pasa VACIO, no falla") sigue existiendo --
        # es un limite del propio mecanismo de pidio en esta ventana, no algo
        # que el sleep tapara. Evidencia: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/sin-sleep-2026-09-28.txt
        correr(["sample"], datos)
        nombrados = {x["pid"] for x in muestras(datos)[-1]["pidio"]}
        assert quieto.pid not in nombrados, \
            "un proceso que no pidio memoria no puede aparecer como que crecio"
    finally:
        quieto.kill(); quieto.wait()


# =====================================================================
# latencia_x -- cuanto tarda el escritorio en contestar
# =====================================================================


def _con_xset_falso(tmp_path, cuerpo):
    """Antepone al PATH un `xset` de mentira con el cuerpo que se le pase."""
    shim = tmp_path / "shim_x"
    shim.mkdir(exist_ok=True)
    x = shim / "xset"
    x.write_text("#!/usr/bin/env bash\n" + cuerpo, encoding="utf-8")
    x.chmod(0o755)
    return {"PATH": f"{shim}:{os.environ['PATH']}", "DISPLAY": ":1"}


def _x_de_la_ultima_muestra(datos):
    f = sorted((datos / "samples").glob("*.jsonl"))[-1]
    return json.loads(f.read_text(encoding="utf-8").strip().splitlines()[-1])["x"]


def test_latencia_x_dice_OK_cuando_el_escritorio_contesta(datos, tmp_path):
    """La pregunta que bb no supo contestar el 2026-09-25: "casi no se podia
    escribir, por que". Todos sus instrumentos leian sano porque todos miden la
    MAQUINA, y una tecla no pasa por la maquina: pasa por el servidor X."""
    correr(["sample"], datos, _con_xset_falso(tmp_path, "exit 0\n"))
    x = _x_de_la_ultima_muestra(datos)
    assert x["estado"] == "OK", x
    assert x["ms"] >= 0, x


def test_control_negativo_latencia_x_dice_TIMEOUT_si_el_escritorio_no_contesta(
        datos, tmp_path):
    """El caso que importa: el servidor X vivo pero sin atender. Es el estado
    en el que se teclea y no aparece nada, y el que ningun total de maquina
    puede distinguir de una maquina en reposo."""
    env = _con_xset_falso(tmp_path, "sleep 30\n")
    env["BB_X_TIMEOUT_S"] = "1"
    correr(["sample"], datos, env)
    x = _x_de_la_ultima_muestra(datos)
    assert x["estado"] == "TIMEOUT", x
    assert x["ms"] >= 900, f"si no espero el timeout, no midio nada: {x}"


def test_control_negativo_latencia_x_dice_ERROR_si_el_servidor_rechaza(datos, tmp_path):
    correr(["sample"], datos, _con_xset_falso(tmp_path, "exit 1\n"))
    assert _x_de_la_ultima_muestra(datos)["estado"] == "ERROR"


def test_control_negativo_sin_DISPLAY_dice_AUSENTE_y_no_OK(datos, tmp_path):
    """Un instrumento que no puede correr no deja el sujeto limpio: deja el
    informe sin esa fila. AUSENTE y OK no son lo mismo."""
    env = _con_xset_falso(tmp_path, "exit 0\n")
    env["DISPLAY"] = ""
    correr(["sample"], datos, env)
    assert _x_de_la_ultima_muestra(datos)["estado"] == "AUSENTE"


# =====================================================================
# swap -- el nivel y el RITMO
# =====================================================================


def _vmstat(tmp_path, pin, pout):
    f = tmp_path / f"vmstat_{pin}_{pout}"
    f.write_text(f"pswpin {pin}\npswpout {pout}\n", encoding="utf-8")
    return str(f)


@pytest.mark.sleeps_aceptados
def test_swap_mide_el_RITMO_no_solo_el_nivel(datos, tmp_path):
    """La noche del 2026-09-24 al 25 el swap fue la unica magnitud que se movio
    en una sola direccion -- 4.3 GB expulsados entre las 20:51 y las 03:28, con
    el 53 % de la RAM libre -- y bb no la registraba: el numero hubo que sacarlo
    del log de earlyoom.

    Lo que se paga no es tener paginas fuera, es traerlas de vuelta, y eso es
    `pswpin`, un contador acumulado desde el arranque. Como nivel no dice nada;
    lo que informa es el delta por segundo.
    """
    correr(["sample"], datos, {"BB_VMSTAT": _vmstat(tmp_path, 1000, 2000)})
    time.sleep(4)  # blocking-sleep: el ritmo es un delta y necesita dos instantes separados -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 2.0 -- sin cambios desde la revision de 1.9 horas antes, mismo dia, mismas evidencias -- SE QUEDA, y AHORA CON PRUEBA PROPIA: sin la espera su test FALLA (1 failed in 1.64s), asi que no necesita el argumento de pareja. Evidencia: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/sunset-1.9-sleeps.txt
    correr(["sample"], datos, {"BB_VMSTAT": _vmstat(tmp_path, 5000, 2400)})
    s = muestras(datos)[-1]["swap"]
    # 4000 paginas en ~4-6 s; el intervalo exacto lo pone el reloj, asi que se
    # asierta el orden de magnitud y el signo, no una cifra al decimal.
    assert 500 < s["in_pag_s"] < 1200, s
    assert 50 < s["out_pag_s"] < 120, s
    assert s["total_kb"] > 0, "SwapTotal real de la maquina"


@pytest.mark.sleeps_aceptados
def test_control_negativo_sin_trafico_de_swap_el_ritmo_es_cero(datos, tmp_path):
    """Sin esto, el test de arriba no distingue "mide el ritmo" de "escupe un
    numero grande". Los mismos contadores en las dos muestras tienen que dar
    cero, no un residuo."""
    v = _vmstat(tmp_path, 1000, 2000)
    correr(["sample"], datos, {"BB_VMSTAT": v})
    time.sleep(2)  # blocking-sleep: dos muestras separadas, mismos contadores -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 2.0 -- sin cambios desde la revision de 1.9 horas antes, mismo dia, mismas evidencias -- SE QUEDA: CONTROL NEGATIVO cuya prueba es que su POSITIVO emparejado falle sin la suya -- y la linea 312 FALLA. Sostenida por pareja, medido 2026-09-28. Evidencia: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/sunset-1.9-sleeps.txt
    correr(["sample"], datos, {"BB_VMSTAT": v})
    s = muestras(datos)[-1]["swap"]
    assert float(s["in_pag_s"]) == 0.0, s
    assert float(s["out_pag_s"]) == 0.0, s


@pytest.mark.sleeps_aceptados
def test_un_contador_que_RETROCEDE_no_produce_un_ritmo_negativo(datos, tmp_path):
    """`pswpin` se reinicia con la maquina. Si bb restara sin mas, la primera
    muestra despues de un arranque emitiria un ritmo negativo -- un numero que
    no significa nada y que cualquier grafica leeria como dato."""
    correr(["sample"], datos, {"BB_VMSTAT": _vmstat(tmp_path, 900000, 900000)})
    time.sleep(2)  # blocking-sleep: dt de bin/bb tiene resolucion de SEGUNDO ENTERO (`date +%s`) -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 2.0 -- sin cambios desde la revision de 1.9 horas antes, mismo dia, mismas evidencias -- SE QUEDA, y con razon MAS FUERTE que antes: instrumentado bin/bb directamente el 2026-09-28 (`dt=$(( ahora_s - antes_s ))` en la seccion de swap/cputop), sleep(0) dio dt=0 en 3 de 6 corridas -- exactamente esos 3 saltan el bloque `[ "$dt" -gt 0 ]` entero y dejan swpin_s/swpout_s en su default 0 SIN pasar por el clamp `(v>0?v:0)` que el test dice verificar. O sea que sin la espera, la mitad de las corridas pasarian por el camino EQUIVOCADO -- vacuamente, no por el mecanismo. Ya no es "argumento estructural solo": es una puerta de tiempo medida y su fallo reproducido. Evidencia: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/dt-resolucion-entera-2026-09-28.txt
    correr(["sample"], datos, {"BB_VMSTAT": _vmstat(tmp_path, 12, 34)})
    s = muestras(datos)[-1]["swap"]
    assert float(s["in_pag_s"]) == 0.0, s
    assert float(s["out_pag_s"]) == 0.0, s


# =====================================================================
# bb status -- el veredicto sobre la propia instrumentacion
# =====================================================================


def _proc_falso(tmp_path, procesos):
    """Un /proc de mentira. En esta maquina el swap esta al 100 % libre casi
    siempre, asi que un campo que sale vacio no demuestra que sepa nombrar a
    nadie, y forzar swap de verdad sobre 60 GB libres arriesga la maquina que
    se vigila."""
    r = tmp_path / f"proc_{len(procesos)}"
    for pid, kb, nombre in procesos:
        d = r / str(pid)
        d.mkdir(parents=True, exist_ok=True)
        (d / "status").write_text(f"Name:\t{nombre}\nVmSwap:\t{kb} kB\n", encoding="utf-8")
        (d / "cgroup").write_text(f"0::/user.slice/prueba-{nombre}.scope\n", encoding="utf-8")
    return {"BB_PROC": str(r)}


def test_swap_por_proceso_NOMBRA_a_quien_tiene_memoria_fuera(datos, tmp_path):
    """`swap.in_pag_s` dice cuantas paginas vuelven del disco y no de quien --
    el mismo defecto que tenia Committed_AS antes de `pidio` y `cpu_some` antes
    de `cpu_top`.

    La ficha que pedia esto daba el COSTE como motivo para no hacerlo. Medido
    antes de escribirlo: un awk por proceso sobre 533 procesos cuesta 0.72-0.78 s
    y la muestra entera dura 0.31 s -- la habria triplicado. Una sola pasada de
    awk sobre el glob cuesta 0.00-0.01 s. El coste era el de la implementacion
    ingenua, no el del dato.
    """
    env = _proc_falso(tmp_path, [(111, 9000000, "gordo"), (222, 512, "chico"),
                                 (444, 4000000, "mediano")])
    correr(["sample"], datos, env)
    top = muestras(datos)[-1]["swap"]["top"]
    assert [x["pid"] for x in top] == [111, 444, 222], top
    assert top[0]["swap_kb"] == 9000000 and top[0]["comm"] == "gordo", top[0]
    assert top[0]["unit"] == "prueba-gordo.scope", "sin la unit no se sabe quien lo lanzo"


def test_sample_escapa_backslash_de_la_unit_en_json(datos, tmp_path):
    """DEBT-SAMPLE-JSON-ESCAPE-SYSTEMD-UNIT: cgroup escaping stays valid JSONL."""
    env = _proc_falso(tmp_path, [(555, 1024, "proceso")])
    proc = Path(env["BB_PROC"])
    (proc / "555" / "cgroup").write_text(
        r"0::/user.slice/app-gnome-google\x2dchrome.scope" + "\n",
        encoding="utf-8",
    )
    correr(["sample"], datos, env)
    swap_top = muestras(datos)[-1]["swap"]["top"]
    assert swap_top[0]["unit"] == r"app-gnome-google\x2dchrome.scope"


def test_control_negativo_un_proceso_SIN_swap_no_sale_nombrado(datos, tmp_path):
    """Sin esto el test de arriba no distingue "atribuye" de "lista a todo el
    mundo". Un proceso con VmSwap 0 existe, se lee, y no puede aparecer."""
    env = _proc_falso(tmp_path, [(111, 4096, "tiene"), (333, 0, "no_tiene")])
    correr(["sample"], datos, env)
    pids = {x["pid"] for x in muestras(datos)[-1]["swap"]["top"]}
    assert 111 in pids and 333 not in pids, muestras(datos)[-1]["swap"]["top"]


def test_control_negativo_sin_nadie_en_swap_la_lista_va_vacia(datos, tmp_path):
    """Y no con una fila de relleno: una lista vacia dice 'nadie', que es un
    hecho; una fila con ceros diria 'este', que seria falso."""
    env = _proc_falso(tmp_path, [(333, 0, "limpio"), (334, 0, "limpio2")])
    correr(["sample"], datos, env)
    assert muestras(datos)[-1]["swap"]["top"] == []


def _journal_falso(tmp_path, nombre, cuerpo):
    """Un `journalctl` de mentira. Sin esto, los chequeos que leen lo que un
    proceso DIJO al arrancar no tendrian caso negativo montable, y un chequeo
    cuyo caso negativo no se puede montar no esta verificado."""
    f = tmp_path / f"journalctl_{nombre}"
    f.write_text("#!/usr/bin/env bash\n" + cuerpo, encoding="utf-8")
    f.chmod(0o755)
    return {"BB_JOURNALCTL": str(f)}


def _fila(r, texto):
    filas = [l for l in r.stdout.splitlines() if texto in l]
    assert filas, r.stdout
    return filas[0]


# --- muestreo: por el DATO, no por el timer -------------------------------


def test_status_ve_el_muestreo_por_su_dato(datos):
    """Un timer `active` cuyo `bb sample` falla en cada disparo se ve igual que
    uno sano si solo se mira `systemctl is-active`."""
    correr(["sample"], datos)
    assert "ARMADO" in _fila(correr(["status"], datos), "muestreo de apps/zombis")


def test_control_negativo_sin_muestra_fresca_el_muestreo_esta_FALTA(datos):
    """El directorio existe y esta vacio: es exactamente el estado de un timer
    activo que no escribe."""
    assert "FALTA" in _fila(correr(["status"], datos), "muestreo de apps/zombis")


# --- clock lock: lo que el DRIVER confirmo --------------------------------


CLOCK_OK = """case "$*" in
  *atom-clock-lock*) echo 'GPU clocks set to "(gpuClkMin 300, gpuClkMax 2800)" for GPU 0' ;;
  *earlyoom*) echo "Preferring to kill process names that match regex '(pytest)'"
              echo "Will avoid killing process names that match regex '(Xorg)'" ;;
esac
"""


def test_control_negativo_clock_lock_con_OTRO_rango_que_el_declarado(datos, tmp_path):
    """El driver NO expone el rango bloqueado -- medido sobre el driver
    580.178.04: `nvidia-smi -q -d CLOCK` da el maximo del hardware (3003 MHz) y
    ningun campo dice 2800. Lo unico que queda del hecho es la linea que
    nvidia-smi imprimio al aplicarlo, y por eso se compara contra los
    argumentos que la unit declara: no basta con que alguna vez se aplicara
    ALGUN rango.
    """
    env = _journal_falso(tmp_path, "rango_distinto", CLOCK_OK.replace("2800", "2600"))
    assert "FALTA" in _fila(correr(["status"], datos, env), "clock lock")


def test_control_negativo_clock_lock_sin_confirmacion_del_driver(datos, tmp_path):
    """La unit puede quedar `active` habiendo fallado en aplicar el limite."""
    env = _journal_falso(tmp_path, "mudo", "exit 0\n")
    assert "FALTA" in _fila(correr(["status"], datos, env), "clock lock")


# --- earlyoom: su PUNTERIA, dicha por el mismo ----------------------------


def test_control_negativo_earlyoom_de_serie_no_cuenta_como_armado(datos, tmp_path):
    """Un earlyoom sin los argumentos de punteria tambien esta `active` y mata
    lo que le parece. El ajuste vive en /etc/default/earlyoom, que un paquete
    puede reescribir dejando la unit igual de activa; lo unico que prueba que
    esos argumentos LE LLEGARON es lo que el proceso imprimio al arrancar.
    """
    env = _journal_falso(tmp_path, "serie",
                         'echo "earlyoom v1.7"\necho "mem total: 123967 MiB"\n')
    assert "FALTA" in _fila(correr(["status"], datos, env), "earlyoom con la punteria")


def test_earlyoom_con_las_dos_regex_SI_cuenta(datos, tmp_path):
    """La otra mitad: con las dos lineas puestas tiene que salir ARMADO, o el
    chequeo seria uno que no puede salir positivo."""
    env = _journal_falso(tmp_path, "con_punteria", CLOCK_OK)
    assert "ARMADO" in _fila(correr(["status"], datos, env), "earlyoom con la punteria")


def test_control_negativo_earlyoom_con_UNA_sola_regex_no_basta(datos, tmp_path):
    """Preferir a quien matar sin proteger a quien no tocar deja el escritorio
    expuesto: son dos propiedades y hacen falta las dos."""
    solo_una = """case "$*" in
  *earlyoom*) echo "Preferring to kill process names that match regex '(pytest)'" ;;
esac
"""
    env = _journal_falso(tmp_path, "media_punteria", solo_una)
    assert "FALTA" in _fila(correr(["status"], datos, env), "earlyoom con la punteria")


# --- bb-usable: su LATIDO, no su `is-active` ------------------------------


LATIDO = ("[bb-usable] latencia del escritorio: 6 ms "
          "(observacion, no actua -- DEBT-BB-USABLE-CIEGO-A-LA-LATENCIA)")
ARRANQUE = ("[bb-usable] sonda sana de referencia: 12 ms para 64 MiB "
            "-- plazo 300s (25000x ese valor)")


def _bb_usable(tmp_path, edad_s, linea=LATIDO):
    """Un journal con UNA linea de bb-usable escrita hace `edad_s` segundos, que
    honra `-S` como el de verdad. Si bb no pasara la ventana, la linea vieja
    saldria igual y el caso rancio daria ARMADO: por eso el stub filtra y no
    decide el veredicto por su cuenta.

    `is-active` se fija con un `systemctl` delante en el PATH, para que los casos
    negativos no pasen por la razon equivocada (una unit inactiva en la maquina
    que corre la suite) y el positivo no dependa de ella. Todo lo demas va al
    systemctl real."""
    cuerpo = f"""case "$*" in *bb-usable*) ;; *) exit 0 ;; esac
desde=""
while [ $# -gt 0 ]; do case "$1" in -S|--since) desde=$2; shift ;; esac; shift; done
escrita=$(( $(date +%s) - {edad_s} ))
if [ -z "$desde" ] || [ "$escrita" -ge "$(date -d "$desde" +%s)" ]; then
  echo '{linea}'
fi
"""
    env = _journal_falso(tmp_path, f"bb_usable_{edad_s}", cuerpo)
    real = subprocess.run(["bash", "-c", "command -v systemctl"],
                          capture_output=True, text=True).stdout.strip()
    bin_falso = tmp_path / "bin_falso"
    bin_falso.mkdir(exist_ok=True)
    s = bin_falso / "systemctl"
    s.write_text('#!/usr/bin/env bash\n'
                 'case "$*" in "is-active bb-usable.service") exit 0 ;; esac\n'
                 f'exec {real or "/bin/false"} "$@"\n', encoding="utf-8")
    s.chmod(0o755)
    env["PATH"] = f"{bin_falso}:{os.environ['PATH']}"
    return env


def test_bb_usable_con_latido_fresco_SI_cuenta(datos, tmp_path):
    """El caso positivo: activa y con una vuelta del bucle hace 10 s."""
    r = correr(["status"], datos, _bb_usable(tmp_path, 10))
    assert "ARMADO" in _fila(r, "bb-usable (vigilante"), r.stdout


def test_control_negativo_bb_usable_activa_con_latido_RANCIO(datos, tmp_path):
    """El caso que motiva el chequeo: la unit sigue `active` pero el bucle dejo
    de dar vueltas hace 10 minutos. `is-active` solo decia ARMADO aqui."""
    r = correr(["status"], datos, _bb_usable(tmp_path, 600))
    assert "FALTA" in _fila(r, "bb-usable (vigilante"), r.stdout
    assert "sin latido" in _fila(r, "bb-usable (vigilante"), r.stdout


@pytest.mark.parametrize("linea", ["", ARRANQUE], ids=["journal_vacio", "solo_arranque"])
def test_control_negativo_bb_usable_activa_sin_latido(datos, tmp_path, linea):
    """Sin latido no hay ARMADO, ni con el journal vacio ni con una linea FRESCA
    de bb-usable que no es el latido -- la de arranque, que sale una sola vez:
    lo que se lee es la marca que se repite."""
    r = correr(["status"], datos, _bb_usable(tmp_path, 10, linea))
    assert "FALTA" in _fila(r, "bb-usable (vigilante"), r.stdout


def _arbol_cgroup(tmp_path, low=2 * 1024**3, con_scope=True, con_ventana=True, roto=None):
    """Monta un arbol de cgroups de mentira con la cadena de 7 eslabones.

    Los dos ultimos llevan un identificador variable en el nombre -- el numero
    de sesion y el pid -- y por eso se montan con nombres concretos: lo que se
    prueba es que el chequeo los ENCUENTRA por patron, no que adivine el nombre.
    """
    u = os.getuid()
    r = tmp_path / f"cg_{low}_{con_scope}_{con_ventana}_{roto}"
    base = r / "user.slice" / f"user-{u}.slice"
    app = base / f"user@{u}.service" / "app.slice"
    rutas = {
        "user.slice": r / "user.slice",
        "user-uid.slice": base,
        "user@.service": base / f"user@{u}.service",
        "session.slice": base / f"user@{u}.service" / "session.slice",
        "app.slice": app,
    }
    if con_scope:
        rutas["session-N.scope"] = base / "session-7.scope"
    if con_ventana:
        rutas["app-gnome-N.scope"] = app / "app-gnome-com.ejemplo.App-4242.scope"
    for nombre, d in rutas.items():
        d.mkdir(parents=True, exist_ok=True)
        (d / "memory.low").write_text("0" if nombre == roto else str(low), encoding="utf-8")
    return {"BB_CGROUP_ROOT": str(r)}


def _fila_escritorio(r):
    filas = [l for l in r.stdout.splitlines() if "escritorio" in l]
    assert filas, r.stdout
    return filas[0]


def test_status_ve_la_proteccion_de_memoria_del_escritorio(datos, tmp_path):
    """Por el DATO y no por el fichero: un drop-in copiado que systemd no
    aplico -- por no recargar, por un nombre mal puesto, o porque la sesion
    grafica nacio antes -- deja los ficheros en su sitio y memory.low en 0, y
    eso es indistinguible de no haberlo hecho salvo leyendo el cgroup."""
    r = correr(["status"], datos, _arbol_cgroup(tmp_path))
    assert "ARMADO" in _fila_escritorio(r), _fila_escritorio(r)


@pytest.mark.parametrize("eslabon", [
    "user.slice", "user-uid.slice", "user@.service", "session.slice", "app.slice",
    "session-N.scope", "app-gnome-N.scope"])
def test_control_negativo_UN_eslabon_en_cero_rompe_la_cadena(datos, tmp_path, eslabon):
    """En cgroup v2 la proteccion efectiva de un hijo esta acotada por la del
    padre, asi que un 0 en cualquier nivel anula los de abajo. Un chequeo que
    mirase solo el ultimo diria ARMADO sobre una cadena rota -- que es la forma
    exacta en que un instrumento da falsa confianza."""
    r = correr(["status"], datos, _arbol_cgroup(tmp_path, roto=eslabon))
    assert "FALTA" in _fila_escritorio(r), _fila_escritorio(r)


def test_control_negativo_sin_scope_grafico_NO_dice_armado(datos, tmp_path):
    """Ahi vive Xorg. Medido el 2026-09-25 leyendo /proc/<pid>/cgroup: Xorg NO
    esta en session.slice sino en session-<N>.scope, hermano de
    user@<uid>.service. Si no hay ninguno, no hay nada que proteger y el
    chequeo no puede decir que si."""
    r = correr(["status"], datos, _arbol_cgroup(tmp_path, con_scope=False))
    assert "FALTA" in _fila_escritorio(r), _fila_escritorio(r)


def test_control_negativo_sin_proteccion_ninguna_cuenta_los_siete(datos, tmp_path):
    r = correr(["status"], datos, _arbol_cgroup(tmp_path, low=0))
    fila = _fila_escritorio(r)
    assert "FALTA" in fila and "7 eslabon" in fila, fila


def test_ventana_de_la_aplicacion_protegida_y_el_arnes_NO(datos, tmp_path):
    """El P1: la ventana donde se escribe y el arnes que la ahoga eran hermanos
    en app.slice sin ninguna prioridad relativa.

    La ficha decia que el scope de una ventana "lleva el pid en el nombre, asi
    que no admite un drop-in estable", y eso era FALSO: systemd resuelve los
    drop-ins tambien por prefijo truncado en cada guion. Comprobado sobre la
    unit viva el 2026-09-25 con `app-gnome-.scope.d/`:

        app-gnome-com.anthropic.Claude-38380.scope   memory.low = 3221225472
        app-com.anthropic.Claude-38380.scope         memory.low = 0

    El arnes queda reclamable sin tener que nombrarlo: no pide proteccion, y
    por eso no la recibe. Aqui se comprueba la otra mitad -- que el chequeo
    encuentra el scope de ventana por patron, con el pid que sea.
    """
    env = _arbol_cgroup(tmp_path)
    r = correr(["status"], datos, env)
    assert "ARMADO" in _fila_escritorio(r), _fila_escritorio(r)
    # Y el control que da sentido al de arriba: un arnes SIN proteccion, al
    # lado de la ventana protegida, no rompe la cadena. Si lo rompiera, el
    # chequeo estaria exigiendo proteger justo lo que se quiere reclamar.
    u = os.getuid()
    app = (Path(env["BB_CGROUP_ROOT"]) / "user.slice" / f"user-{u}.slice"
           / f"user@{u}.service" / "app.slice")
    arnes = app / "app-com.ejemplo.Arnes-9999.scope"
    arnes.mkdir(parents=True, exist_ok=True)
    (arnes / "memory.low").write_text("0", encoding="utf-8")
    r2 = correr(["status"], datos, env)
    assert "ARMADO" in _fila_escritorio(r2), _fila_escritorio(r2)


def test_control_negativo_sin_ninguna_ventana_NO_dice_armado(datos, tmp_path):
    """Una cadena que no llega a ningun sujeto no protege nada, por mucho que
    sus niveles altos esten puestos."""
    r = correr(["status"], datos, _arbol_cgroup(tmp_path, con_ventana=False))
    assert "FALTA" in _fila_escritorio(r), _fila_escritorio(r)


def test_status_ve_la_telemetria_termica_EN_ESTE_REPO(datos):
    """DGX-585 movio el productor de la telemetria termica a blackbox y borro
    la copia de Atlas. El consumidor dentro de `bin/bb` se quedo apuntando a
    la ruta borrada, y el resultado medido el 2026-09-25 fue que `bb status`
    decia

        FALTA  termica de Atlas (atom_gpu_telemetry, <2 min)
               -- systemctl --user start atom-gpu-telemetry

    mientras la unit llevaba horas activa escribiendo 711 muestras por hora.
    El informe de instrumentacion mintiendo sobre su propio instrumento: manda
    a rearmar lo que ya esta armado, y quien lo lee deja de creerle al resto
    de las filas.
    """
    (datos / "atom_gpu_telemetry.jsonl").write_text(
        '{"ts": "2026-09-25T00:00:00+00:00", "evento": "muestra"}\n', encoding="utf-8")
    r = correr(["status"], datos)
    fila = [l for l in r.stdout.splitlines() if "atom_gpu_telemetry" in l]
    assert fila, r.stdout
    assert "ARMADO" in fila[0], fila[0]


def test_control_negativo_status_DICE_falta_si_la_telemetria_no_esta(datos):
    """Un chequeo que no puede salir negativo no es un chequeo. Este es el
    unico motivo por el que el de arriba significa algo."""
    r = correr(["status"], datos)
    fila = [l for l in r.stdout.splitlines() if "atom_gpu_telemetry" in l]
    assert fila, r.stdout
    assert "FALTA" in fila[0], fila[0]


def test_control_negativo_status_DICE_falta_si_la_telemetria_esta_rancia(datos):
    """Por sus DATOS, no por la unit: el chequeo exige escritura de hace menos
    de 2 minutos, porque una unit `active` cuyo proceso dejo de escribir es
    exactamente el fallo silencioso que se busca."""
    f = datos / "atom_gpu_telemetry.jsonl"
    f.write_text('{"evento": "muestra"}\n', encoding="utf-8")
    viejo = time.time() - 3600
    os.utime(f, (viejo, viejo))
    r = correr(["status"], datos)
    fila = [l for l in r.stdout.splitlines() if "atom_gpu_telemetry" in l]
    assert fila, r.stdout
    assert "FALTA" in fila[0], fila[0]


# =====================================================================
# cpu_top -- quien quema CPU
# =====================================================================


@pytest.mark.sleeps_aceptados
def test_cpu_top_NOMBRA_a_quien_quema_cpu(datos):
    """El hueco que `psi.cpu_some` y `load1` no cierran: dicen cuanto sufre la
    maquina, no quien la hace sufrir.

    Medido la noche del 2026-09-24 al 25: ocho muestras con `cpu_some` entre
    50.38 y 85.43 y load1 hasta 47.65 sobre 20 nucleos, y ninguna nombra a un
    responsable -- `top_rss` ordena por memoria residente y `pidio` por
    crecimiento de VmSize, asi que un proceso que solo quema CPU no sale.
    """
    # El hijo AVISA de que existe antes de ponerse a quemar, en vez de que aqui
    # se adivine cuanto tarda en arrancar. Convertido en la revision de sunset
    # de 1.5, con la misma tecnica que en 1.4 saco a otros dos de esta suite:
    # su stdout es el evento.
    quemador = subprocess.Popen(
        ["bash", "-c", "echo listo; while :; do :; done"],
        stdout=subprocess.PIPE, text=True)
    try:
        assert quemador.stdout is not None
        assert quemador.stdout.readline().strip() == "listo"
        cpu_antes = _cpu_segundos(quemador.pid)
        correr(["sample"], datos)                  # muestra 1: linea base
        time.sleep(4)  # blocking-sleep: `ps -o times=` da segundos ENTEROS; hacen falta varios para que el delta sea legible -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 2.0 -- sin cambios desde la revision de 1.9 horas antes, mismo dia, mismas evidencias -- SE QUEDA, y su justificacion MEJORO desde 1.8. Entonces se anoto que el test PASABA sin este sleep y que por eso la afirmacion de 1.7 era falsa; en 1.9 FALLA (1 failed in 1.59s). El disparador que 1.8 dejo escrito -- que `bb sample` bajara de 0.5 s -- se midio y NO se cumple: mediana 1.21 s en 6 corridas frente a 0.75 en 1.8, o sea que se ALEJO. Evidencia: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/sunset-1.9-sleeps.txt
        correr(["sample"], datos)                  # muestra 2: ya quemo
        mio = _cpu_segundos(quemador.pid) - cpu_antes
        d = muestras(datos)[-1]
        por_pid = {x["pid"]: x for x in d["cpu_top"]}
        if quemador.pid not in por_pid:
            # La maquina tenia cinco procesos mas calientes. `cpu_top` promete el
            # top 5, no el mio: se comprueba ESA promesa.
            _no_esta_pero_los_cinco_queman_mas(d["cpu_top"], "cpu_s", mio, "cpu_top")
            return
        fila = por_pid[quemador.pid]
        # Un bucle vacio de bash satura UN nucleo: por debajo del 50 % de uno
        # el campo estaria midiendo otra cosa que lo que dice medir.
        assert fila["pct_nucleo"] >= 50, fila
        assert fila["unit"], "sin la unit de cgroup no se sabe quien lo lanzo"
    finally:
        quemador.kill(); quemador.wait()


@pytest.mark.sleeps_aceptados
def test_control_negativo_un_proceso_dormido_no_sale_como_que_quema(datos):
    """Sin esto, el test de arriba no distingue "atribuye" de "lista a todo el
    mundo".

    Igual que el control de `pidio`, NO se asierta que `cpu_top` este vacio:
    esta maquina tiene ~500 procesos y siempre hay alguno trabajando. Lo que
    se controla es un proceso propio, vivo en las dos muestras, que no quema
    nada: ese no puede aparecer.
    """
    dormido = subprocess.Popen(
        [sys.executable, "-c", "import time; print('listo', flush=True); time.sleep(20)"],
        stdout=subprocess.PIPE, text=True)
    try:
        assert dormido.stdout is not None
        assert dormido.stdout.readline().strip() == "listo"
        correr(["sample"], datos)
        time.sleep(4)  # blocking-sleep: mismo intervalo que el caso positivo, para que la comparacion valga -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 2.0 -- sin cambios desde la revision de 1.9 horas antes, mismo dia, mismas evidencias -- SE QUEDA, y su base MEJORO: es CONTROL NEGATIVO y su prueba es que su positivo emparejado (linea 679) falle sin la suya. En 1.8 ese positivo NO fallaba y esta exencion heredaba su debilidad; en 1.9 SI falla. Evidencia: tasks/evidence/DEBT-ACCEPTED-SLEEP-TESTS-BB/sunset-1.9-sleeps.txt
        correr(["sample"], datos)
        nombrados = {x["pid"] for x in muestras(datos)[-1]["cpu_top"]}
        assert dormido.pid not in nombrados, \
            "un proceso dormido no puede aparecer como que quemo CPU"
    finally:
        dormido.kill(); dormido.wait()


def test_cpu_top_va_vacio_en_la_primera_muestra_y_no_inventa(datos):
    """Sin muestra anterior no hay delta, y un delta inventado seria peor que
    la ausencia: la primera muestra tras arrancar reportaria como "quemado
    ahora" todo el CPU acumulado desde el arranque de cada proceso."""
    correr(["sample"], datos)
    d = muestras(datos)[-1]
    assert d["cpu_top"] == [], d["cpu_top"]


def test_residuo_es_un_numero_y_CABE_en_la_maquina(datos):
    """El sleep de este test se RETIRO en la revision de sunset de 1.7, y con el
    la mitad de la asercion que era falsa.

    Antes afirmaba que `residuo_mb` "no se mueve solo" entre dos muestras, con un
    tope de 2048 MiB. La primera medida que lo refuto fueron ocho repeticiones
    por lado con la maquina en reposo (mediana 306 y 801 MiB, max 2305), y una de
    las ocho paso de 2048.

    ESA MEDIDA QUEDO SUPERADA el 2026-09-27 por la caracterizacion completa, y
    los numeros nuevos son peores: 3308 pares contiguos del corpus, separados por
    estado de carga, |delta| en MiB --

        estado                   n     mediana   p95    p99     max
        reposo (load1 < 4)     2690        47    825   1825    4007
        media  (4-20)           535       849   4576   7193    8035
        carga  (load1 >= 20)     83      1370   7096   8053    8053

    El ruido ESCALA CON LA CARGA por un factor de 29 en la mediana, y el tope de
    2048 lo superan 142 de 3308 pares: 1 de cada 23, no 1 de 8. Subir el tope a
    4096 habria quitado el flake sin medir nada mejor, y CUALQUIER tope fijo
    sobre este campo depende de lo ocupada que este la caja.

    Asi que se queda lo que se puede afirmar: que es un entero y que cabe en la
    maquina. Un `residuo_mb` mayor que `MemTotal` seria una resta mal hecha, y
    eso si es un defecto y no ruido.

    Y el campo SIRVE, que es la otra mitad de la caracterizacion: rechaza el
    92.9 % de la memoria con dueno (6 GiB tocados pagina por pagina lo mueven 437
    MiB, que caben dentro de su propio ruido en reposo), y separa su senal -- los
    21 GB que desaparecieron sin dueno -- del ruido por 25x en reposo y 3.0x con
    carga. Lo que sobraba era la palabra "no se mueve", no el campo.
    Ficha cerrada: [[DEBT-RESIDUO-MAS-RUIDOSO-QUE-SU-PROPIA-SENAL]].
    """
    correr(["sample"], datos)
    residuo = int(muestras(datos)[-1]["residuo_mb"])
    total_mb = next(int(l.split()[1]) for l in
                    Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
                    if l.startswith("MemTotal:")) // 1024
    assert abs(residuo) < total_mb, (
        f"residuo {residuo} MiB sobre una maquina de {total_mb} MiB: eso no es "
        "ruido, es una resta mal hecha")


# =====================================================================
# la rafaga -- muestreo adaptativo
# =====================================================================


def _sembrar_anterior(datos, **campos):
    """Escribe una muestra 'anterior' a medida para provocar (o no) la rafaga."""
    f = datos / "samples" / (time.strftime("%Y-%m-%d") + ".jsonl")
    base = {"ts": "sembrada", "mem_free_kb": 1, "mem_avail_kb": 1,
            "commit_pct": 1, "psi": {"mem_full": 0.0}}
    base.update(campos)
    # separators sin espacios: bb escribe su JSON con printf, sin espacio tras
    # los dos puntos, y parsea su PROPIO formato. Sembrar `"k": 1` en vez de
    # `"k":1` prueba un formato que bb nunca produce -- fallo de este fichero
    # en su primer intento, no del ejecutable.
    f.write_text(json.dumps(base, separators=(",", ":")) + "\n", encoding="utf-8")


def _leer(f):
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_la_rafaga_dispara_con_la_caida_real_del_incidente(datos):
    """21 GB de MemAvailable en un minuto: la caida medida el 2026-09-24."""
    av = int(next(l.split()[1] for l in open("/proc/meminfo", encoding="ascii")
                  if l.startswith("MemAvailable:")))
    cp = float(subprocess.run(
        ["awk", "/^MemTotal:/{mt=$2} /^SwapTotal:/{st=$2} /^Committed_AS:/{c=$2}"
         " END{printf \"%.2f\", c*100/(mt+st)}", "/proc/meminfo"],
        capture_output=True, text=True).stdout)
    _sembrar_anterior(datos, mem_avail_kb=av + 21 * 1048576, commit_pct=cp)
    correr(["sample"], datos, {"BLACKBOX_RAFAGA_SEGS": "3", "BLACKBOX_RAFAGA_PASO": "1"})
    lineas = _leer(datos / "samples" / (time.strftime("%Y-%m-%d") + ".jsonl"))
    inicios = [l for l in lineas if l.get("burst_inicio")]
    assert inicios, "una caida de 21 GB tiene que disparar la rafaga"
    assert "mem_avail" in inicios[0]["motivo"]
    assert [l for l in lineas if l.get("burst")], "la rafaga no escribio muestras"


def test_control_negativo_la_rafaga_NO_dispara_en_reposo(datos):
    """El mismo camino, con un 'anterior' igual al ahora."""
    av = int(next(l.split()[1] for l in open("/proc/meminfo", encoding="ascii")
                  if l.startswith("MemAvailable:")))
    _sembrar_anterior(datos, mem_avail_kb=av, commit_pct=999)
    correr(["sample"], datos)
    lineas = _leer(datos / "samples" / (time.strftime("%Y-%m-%d") + ".jsonl"))
    assert not [l for l in lineas if l.get("burst_inicio")], \
        "sin caida ni salto de commit no puede haber rafaga"


def test_la_rafaga_dispara_con_el_salto_de_commit_del_incidente(datos):
    """+54 puntos en un minuto: el salto medido el 2026-09-24."""
    av = int(next(l.split()[1] for l in open("/proc/meminfo", encoding="ascii")
                  if l.startswith("MemAvailable:")))
    _sembrar_anterior(datos, mem_avail_kb=av, commit_pct=-54.0)
    correr(["sample"], datos, {"BLACKBOX_RAFAGA_SEGS": "3", "BLACKBOX_RAFAGA_PASO": "1"})
    lineas = _leer(datos / "samples" / (time.strftime("%Y-%m-%d") + ".jsonl"))
    inicios = [l for l in lineas if l.get("burst_inicio")]
    assert inicios and "commit" in inicios[0]["motivo"]


def test_la_rafaga_no_pisa_el_estado_de_la_muestra_completa(datos):
    """Defecto real del 2026-09-24: la rafaga sobrescribia vsz_prev cada 2 s y
    la muestra completa pasaba a comparar contra un mapa de hace segundos."""
    av = int(next(l.split()[1] for l in open("/proc/meminfo", encoding="ascii")
                  if l.startswith("MemAvailable:")))
    _sembrar_anterior(datos, mem_avail_kb=av + 21 * 1048576, commit_pct=1)
    correr(["sample"], datos, {"BLACKBOX_RAFAGA_SEGS": "3", "BLACKBOX_RAFAGA_PASO": "1"})
    assert (datos / "vsz_prev").exists()
    assert (datos / "vsz_prev_rafaga").exists(), "la rafaga tiene que tener estado propio"


# =====================================================================
# bb sigterm -- "no ha pasado" frente a "no estabamos mirando"
# =====================================================================


def test_sigterm_distingue_armado_de_no_armado(datos, tmp_path):
    """El medio valor del subcomando: cero filas significa lo contrario segun
    si la regla esta puesta, y las dos salidas se leen igual."""
    aud = tmp_path / "audit"; aud.mkdir()
    ts = int(time.time())

    # El anillo se ANCLA atras a proposito, y la razon es del 2026-09-27: desde
    # ese dia `bb sigterm` declara cuanto cubre el registro y levanta su propio
    # could_not_run cuando se le pide mas. Sin el ancla, este test pedia 5 min
    # contra un anillo de 0 y salia `could_not_run: 2` -- las dos razones
    # ciertas, pero la segunda no es lo que este test mide. El ancla lo deja
    # midiendo una cosa: si la regla esta puesta.
    ancla = (f'type=SYSCALL msg=audit({ts - 3600}.1:7): arch=c00000b7 auid=1000 '
             f'comm="ancla" exe="/usr/bin/true" key="otra_cosa"\n')

    # Ruido de rustdesk LLEGANDO ahora: la regla no esta cargada.
    (aud / "audit.log").write_text(
        ancla +
        f'type=SYSCALL msg=audit({ts}.1:1): arch=c00000b7 auid=4294967295 '
        f'comm="loginctl" exe="/usr/bin/loginctl" key="reboot_cmd"\n',
        encoding="utf-8")
    r = correr(["sigterm", "5 minutes ago"], datos, {"BLACKBOX_AUDIT_DIR": str(aud)})
    assert "NO ARMADO" in r.stdout
    assert "could_not_run: 1" in r.stdout, (
        f"solo la regla puede faltar aqui; el anillo cubre una hora:\n{r.stdout}")

    # El mismo ruido, pero viejo: la regla ya esta puesta.
    (aud / "audit.log").write_text(
        ancla +
        f'type=SYSCALL msg=audit({ts - 600}.1:1): arch=c00000b7 auid=4294967295 '
        f'comm="loginctl" exe="/usr/bin/loginctl" key="reboot_cmd"\n',
        encoding="utf-8")
    r = correr(["sigterm", "30 minutes ago"], datos, {"BLACKBOX_AUDIT_DIR": str(aud)})
    assert "regla de auditoria: armado" in r.stdout
    assert "could_not_run: 0" in r.stdout


def test_sigterm_empareja_emisor_con_victima(datos, tmp_path):
    aud = tmp_path / "audit"; aud.mkdir()
    ts = int(time.time()) - 60
    (aud / "audit.log").write_text(
        f'type=SYSCALL msg=audit({ts}.1:9001): arch=c00000b7 syscall=129 a0=4d2 a1=f '
        f'ppid=1 pid=3011 auid=4294967295 uid=0 comm="earlyoom" '
        f'exe="/usr/bin/earlyoom" key="blackbox_sigterm"\n'
        f'type=OBJ_PID msg=audit({ts}.1:9001): opid=1234 ocomm="python3"\n',
        encoding="utf-8")
    r = correr(["sigterm", "10 minutes ago"], datos, {"BLACKBOX_AUDIT_DIR": str(aud)})
    assert "earlyoom[3011]" in r.stdout
    assert "python3[1234]" in r.stdout
    assert "demonio" in r.stdout, "auid unset tiene que leerse como demonio"


def test_sigterm_sin_registro_legible_lo_DICE(datos, tmp_path):
    """Un registro ilegible no puede leerse como 'no hubo senales'."""
    r = correr(["sigterm"], datos, {"BLACKBOX_AUDIT_DIR": str(tmp_path / "no-existe")})
    assert "ILEGIBLE" in r.stdout
    assert "could_not_run: 1" in r.stdout


# =====================================================================
# lo basico que nadie mira hasta que se rompe
# =====================================================================


def test_sin_subcomando_imprime_la_ayuda_y_falla(datos):
    r = correr(["subcomando-que-no-existe"], datos)
    assert r.returncode == 2
    assert "bb cap" in r.stderr, "la ayuda tiene que listar los subcomandos nuevos"


def test_la_ayuda_documenta_los_subcomandos_que_deciden(datos):
    r = correr([], datos)
    for sub in ("bb cap", "bb sigterm", "bb sample", "bb scan"):
        assert sub in r.stdout, f"{sub} no aparece en la ayuda"


# --------------------------------------------------------------- smi_salud
# Que `nvidia-smi` deje de responder es EL sintoma del cuelgue -- da titulo al
# hilo del foro de NVIDIA #358951 -- y hasta el 2026-09-24 no lo registraba
# nadie: el `gpu_sampler.sh` retirado el 2026-09-07 tenia una columna `status`
# con TIMEOUT/ERROR, `atom_gpu_telemetry.py` no la absorbio (su campo `evento`
# vale "muestra" en 2000 de 2000 muestras medidas), y el resto de `bin/bb`
# llamaba a nvidia-smi con `2>/dev/null || return 1`, tragandose el cuelgue.
#
# Estos tres tests son el control negativo de esa recuperacion: el campo tiene
# que saber decir OK, TIMEOUT y ERROR. Uno que solo supiera decir OK no
# distinguiria una maquina sana de una colgada, que es justo su unico trabajo.


def _con_smi_falso(tmp_path, cuerpo):
    """Antepone al PATH un nvidia-smi de mentira con el cuerpo que se le pase."""
    shim = tmp_path / "shim"
    shim.mkdir(exist_ok=True)
    smi = shim / "nvidia-smi"
    smi.write_text("#!/usr/bin/env bash\n" + cuerpo, encoding="utf-8")
    smi.chmod(0o755)
    return {"PATH": f"{shim}:{os.environ['PATH']}"}


def _smi_de_la_ultima_muestra(datos):
    f = sorted((datos / "samples").glob("*.jsonl"))[-1]
    return json.loads(f.read_text(encoding="utf-8").strip().splitlines()[-1])["smi"]


def test_sample_ignora_fila_gpu_sin_pid_y_conserva_json_valido(datos, tmp_path):
    env = _con_smi_falso(
        tmp_path,
        'if [[ "$*" == *query-compute-apps* ]]; then printf ",N/A,0\\n"; fi\n'
        'exit 0\n',
    )
    r = correr(["sample"], datos=datos, extra_env=env)
    assert r.returncode == 0, r.stderr
    muestra = muestras(datos)[-1]
    assert muestra["gpu"] == [], muestra["gpu"]


def test_smi_dice_OK_cuando_el_driver_responde(datos, tmp_path):
    env = _con_smi_falso(tmp_path, "exit 0\n")
    correr(["sample"], datos=datos, extra_env=env)
    smi = _smi_de_la_ultima_muestra(datos)
    assert smi["estado"] == "OK", smi
    assert isinstance(smi["ms"], int) and smi["ms"] >= 0, smi


def test_control_negativo_smi_dice_TIMEOUT_cuando_el_driver_se_cuelga(datos, tmp_path):
    """El caso que importa: nvidia-smi vivo pero sin contestar."""
    env = _con_smi_falso(tmp_path, "sleep 30\n")
    env["BB_SMI_TIMEOUT_S"] = "1"
    correr(["sample"], datos=datos, extra_env=env)
    smi = _smi_de_la_ultima_muestra(datos)
    assert smi["estado"] == "TIMEOUT", smi
    assert smi["ms"] >= 900, f"debe haber esperado ~1 s de verdad: {smi}"


def test_control_negativo_smi_dice_ERROR_cuando_el_driver_falla(datos, tmp_path):
    env = _con_smi_falso(tmp_path, "exit 9\n")
    correr(["sample"], datos=datos, extra_env=env)
    smi = _smi_de_la_ultima_muestra(datos)
    assert smi["estado"] == "ERROR", smi


# =====================================================================
# memoria por slice en la muestra: sin serie no hay techo que calibrar
# =====================================================================


def _cg_slices(tmp_path, cur="1048576", peak="2097152", sin_peak=False, roto=None):
    """Un arbol de cgroups con los tres slices que el presupuesto mira."""
    u = os.getuid()
    r = tmp_path / f"cgs_{cur}_{peak}_{sin_peak}_{roto}"
    rutas = {
        "app": r / "user.slice" / f"user-{u}.slice" / f"user@{u}.service" / "app.slice",
        "docker": r / "docker.slice",
        "system": r / "system.slice",
    }
    for nombre, d in rutas.items():
        d.mkdir(parents=True, exist_ok=True)
        if nombre != roto:
            (d / "memory.current").write_text(cur + "\n", encoding="utf-8")
        if not sin_peak:
            (d / "memory.peak").write_text(peak + "\n", encoding="utf-8")
    return {"BB_CGROUP_ROOT": str(r)}


def _slices_de_la_muestra(datos):
    f = next((datos / "samples").glob("*.jsonl"))
    return json.loads(f.read_text(encoding="utf-8").splitlines()[-1])["slices"]


def test_la_muestra_guarda_la_memoria_de_CADA_slice(datos, tmp_path):
    """`DEBT-TECHOS-SIN-CALIBRAR` se quedo trabada por falta de esta serie.

    `system.slice` es el ultimo slice sin techo; ponerle uno hace que el
    presupuesto componga, y el 2026-09-25 no habia con que elegir el numero --
    solo su `memory.peak` de un arranque. El techo de `docker.slice` salio de
    18 944 muestras, y ese es el liston. Sin esto, dentro de un mes seguiria sin
    haberlo.
    """
    correr(["sample"], datos, _cg_slices(tmp_path))
    s = _slices_de_la_muestra(datos)
    assert sorted(x["slice"] for x in s) == ["app", "docker", "system"], s
    assert all(x["cur_kb"] == 1024 and x["peak_kb"] == 2048 for x in s), s


def test_un_slice_que_NO_se_puede_leer_se_OMITE_y_no_entra_como_cero(datos, tmp_path):
    """Un 0 se promediaria como si fuera una medida, y un techo calibrado sobre
    ceros inventados saldria mas bajo de lo que el slice necesita -- o sea, un
    techo que mata procesos por un dato que nadie tomo."""
    correr(["sample"], datos, _cg_slices(tmp_path, roto="system"))
    s = _slices_de_la_muestra(datos)
    assert [x["slice"] for x in s] == ["app", "docker"], s


def test_sin_memory_peak_en_el_kernel_se_escribe_null_y_no_cero(datos, tmp_path):
    """`memory.peak` no existe en todos los kernels. "no lo da este kernel" y
    "el pico fue cero" son cosas distintas, y solo una de las dos se puede
    promediar."""
    correr(["sample"], datos, _cg_slices(tmp_path, sin_peak=True))
    s = _slices_de_la_muestra(datos)
    assert all(x["peak_kb"] is None and x["cur_kb"] == 1024 for x in s), s


# =====================================================================
# el invariante de las listas `head -5`, que es lo unico que prometen
# =====================================================================


def test_la_lista_que_SUELTA_al_mio_y_nombra_a_uno_MAS_FRIO_si_es_un_fallo():
    """El camino nuevo no puede ser una amnistia.

    Si `cpu_top` deja fuera a mi proceso mientras nombra a alguien que quemo
    MENOS, eso no es la maquina ocupada: es la lista mal ordenada, y tiene que
    seguir siendo rojo."""
    lista = [{"pid": i, "cpu_s": s} for i, s in enumerate([9, 8, 7, 6, 1])]
    with pytest.raises(AssertionError, match="MAS FRIOS"):
        _no_esta_pero_los_cinco_queman_mas(lista, "cpu_s", 4, "cpu_top")


def test_una_lista_con_SITIO_LIBRE_que_no_me_nombra_si_es_un_fallo():
    """Si la lista no llego a cinco, no hubo competencia que me sacara: habia
    hueco y bb no lo uso. Eso es el defecto original, no contencion."""
    lista = [{"pid": i, "cpu_s": 9} for i in range(3)]
    with pytest.raises(AssertionError, match="NO esta llena"):
        _no_esta_pero_los_cinco_queman_mas(lista, "cpu_s", 4, "cpu_top")


def test_control_negativo_cinco_MAS_CALIENTES_que_el_mio_NO_son_un_fallo():
    """La otra direccion, sin la cual las dos de arriba solo dirian que el
    helper sabe levantar excepciones. Con la maquina llena de procesos mas
    calientes, que el mio no salga es lo correcto."""
    lista = [{"pid": i, "cpu_s": s} for i, s in enumerate([9, 8, 7, 6, 5])]
    _no_esta_pero_los_cinco_queman_mas(lista, "cpu_s", 4, "cpu_top")   # no levanta
    # Y el BORDE, que es lo que convierte esto en un oraculo y no en un "no
    # reviento": con el mio en 6 el de 5 pasa a ser mas frio, y tiene que
    # levantar. Lo pidio zero-debt con `test_without_assert`, y tenia razon --
    # sin esta mitad, el test seguiria verde si el helper fuera un `pass`.
    with pytest.raises(AssertionError, match="MAS FRIOS"):
        _no_esta_pero_los_cinco_queman_mas(lista, "cpu_s", 6, "cpu_top")


def test_muestras_FILTRA_las_de_rafaga_y_no_las_da_por_completas(datos):
    """Una muestra de rafaga no trae `cpu_top`. Devolverla como "la ultima
    muestra" hace que el test de al lado reviente por la carga de la maquina y
    no por el sujeto, que es la peor clase de rojo: el que no dice nada."""
    f = datos / "samples" / "2026-09-25.jsonl"
    f.write_text("\n".join([
        json.dumps({"ts": "2026-09-25T00:00:00-0600", "cpu_top": [{"pid": 1}]}),
        json.dumps({"ts": "2026-09-25T00:00:01-0600", "burst": True, "pidio": []}),
    ]) + "\n", encoding="utf-8")
    ms = muestras(datos)
    assert len(ms) == 1 and "cpu_top" in ms[-1], ms


def test_control_negativo_sin_rafagas_NO_se_filtra_nada(datos):
    """Sin esto, `muestras` podria devolver la lista vacia y los dos tests de
    arriba seguirian verdes."""
    f = datos / "samples" / "2026-09-25.jsonl"
    f.write_text("\n".join(
        json.dumps({"ts": f"2026-09-25T00:00:0{i}-0600", "cpu_top": []}) for i in range(3)
    ) + "\n", encoding="utf-8")
    assert len(muestras(datos)) == 3


# =====================================================================
# bb sigterm, los cuatro defectos medidos el 2026-09-27 (DEBT-DGX-438)
#
# La ficha planeaba dejar el instrumento un mes acumulando evidencia. Medido
# ese dia: llevaba 76 HORAS armado y podia contestar sobre 10 MINUTOS, porque
# leia solo audit.log e ignoraba las cuatro rotaciones del anillo. Y cuando
# contestaba, su columna de victima salia "?" en las 53 capturas, porque el
# anillo tiene 0 registros type=OBJ_PID contra 307 SYSCALL con la clave.
# =====================================================================


def _syscall(ts, serial, *, pid, comm='"x"', exe='"/usr/bin/x"', a0="4d2",
             auid="4294967295", key="blackbox_sigterm"):
    """Una linea SYSCALL de auditd. `a0` es la VICTIMA, en hexadecimal."""
    c = f"comm={comm} " if comm else ""
    e = f"exe={exe} " if exe else ""
    return (f'type=SYSCALL msg=audit({ts}.1:{serial}): arch=c00000b7 syscall=129 '
            f'a0={a0} a1=f ppid=1 pid={pid} auid={auid} uid=0 {c}{e}key="{key}"\n')


def test_sigterm_lee_las_ROTACIONES_y_no_solo_el_fichero_actual(datos, tmp_path):
    """El defecto que hacia inejecutable el plan de DEBT-DGX-438.

    El anillo rota por tamano: 5 ficheros, 33.6 MB, 136 min en esta caja. Leer
    solo `audit.log` veia 10 de esos 136 minutos, y una pregunta por cuatro
    dias recibia una respuesta sobre diez minutos.
    """
    aud = tmp_path / "audit"; aud.mkdir()
    ts = int(time.time())
    # El viejo vive en una rotacion; el nuevo en el fichero actual.
    (aud / "audit.log.1").write_text(
        _syscall(ts - 300, 9001, pid=1111, comm='"viejo"'), encoding="utf-8")
    (aud / "audit.log").write_text(
        _syscall(ts - 30, 9002, pid=2222, comm='"nuevo"'), encoding="utf-8")
    r = correr(["sigterm", "10 minutes ago"], datos,
               {"BLACKBOX_AUDIT_DIR": str(aud)})
    assert "nuevo[2222]" in r.stdout
    assert "viejo[1111]" in r.stdout, (
        "la captura de la ROTACION no aparece: se volvio a leer solo audit.log, "
        "que es el defecto que dejaba a DGX-438 mirando 10 min de 136")


def test_sigterm_DECLARA_la_ventana_que_el_anillo_cubre(datos, tmp_path):
    """Y avisa cuando se le pide mas de lo que puede mirar.

    Sin esto un cero es ambiguo entre "no hubo senales en lo que pediste" y
    "el anillo no llega hasta ahi", y solo una de las dos habla del sujeto.
    """
    aud = tmp_path / "audit"; aud.mkdir()
    ts = int(time.time())
    (aud / "audit.log").write_text(
        _syscall(ts - 120, 9001, pid=3333), encoding="utf-8")
    r = correr(["sigterm", "2 hours ago"], datos, {"BLACKBOX_AUDIT_DIR": str(aud)})
    assert "el registro cubre:" in r.stdout
    assert "no se miraron" in r.stdout
    assert "could_not_run: 1" in r.stdout, (
        "pedir 120 min contra un anillo de 2 no puede salir con could_not_run 0")


def test_control_negativo_un_hueco_de_SEGUNDOS_no_levanta_el_aviso(datos, tmp_path):
    """El par del de arriba, y sin el ese aviso no vale nada.

    Medido el 2026-09-27: la primera version comparaba dos cuentas de minutos
    redondeadas por su lado, asi que un hueco de CUATRO SEGUNDOS salia como
    "1 min" (137 - 136) y levantaba could_not_run. Un aviso que salta por un
    artefacto de redondeo ensena a ignorar los avisos.
    """
    aud = tmp_path / "audit"; aud.mkdir()
    ts = int(time.time())
    # El anillo empieza 4 s DESPUES del corte que se va a pedir.
    (aud / "audit.log").write_text(
        _syscall(ts - 296, 9001, pid=4444) + _syscall(ts - 10, 9002, pid=4445),
        encoding="utf-8")
    r = correr(["sigterm", "5 minutes ago"], datos, {"BLACKBOX_AUDIT_DIR": str(aud)})
    assert "no se miraron" not in r.stdout, (
        "un hueco de segundos no es un tramo sin mirar")
    assert "could_not_run: 0" in r.stdout


def test_sigterm_NOMBRA_a_la_victima_desde_a0_cuando_no_hay_OBJ_PID(datos, tmp_path):
    """La mitad que DGX-438 pregunta, y que estaba estructuralmente vacia.

    El anillo de esta caja tiene 0 registros type=OBJ_PID contra 307 SYSCALL
    con la clave de blackbox, asi que la rama que los une no corre nunca. Pero
    la victima ya estaba en el SYSCALL: `a0`, en hexadecimal. 0x4d2 = 1234.
    """
    aud = tmp_path / "audit"; aud.mkdir()
    (aud / "audit.log").write_text(
        _syscall(int(time.time()) - 60, 9001, pid=5555, a0="4d2"), encoding="utf-8")
    r = correr(["sigterm", "10 minutes ago"], datos, {"BLACKBOX_AUDIT_DIR": str(aud)})
    assert "1234" in r.stdout, (
        "la victima sigue sin nombre: a0 es hexadecimal y hay que convertirlo")


def test_un_a0_NEGATIVO_es_un_GRUPO_y_conserva_su_signo(datos, tmp_path):
    """`kill(-pgid, sig)` senala a un GRUPO, y a0 llega sin signo.

    Encontrado el 2026-09-27 leyendo la salida, no el codigo: la columna de
    victima traia `4294965974`, que no es ningun pid -- `pid_max` en Linux llega
    a 2^22 -- sino -1322, el grupo 1322 de postgres. 44 de 314 capturas
    acumuladas (14.0 %) venian asi, y `nombra_victimas` no podia nombrarlas
    jamas porque buscaba en el indice un numero de diez cifras.

    0xfffffad6 = 4294965974 sin signo = -1322 con signo.
    """
    aud = tmp_path / "audit"; aud.mkdir()
    (aud / "audit.log").write_text(
        _syscall(int(time.time()) - 60, 9001, pid=5555, a0="fffffad6"),
        encoding="utf-8")
    r = correr(["sigterm", "10 minutes ago"], datos, {"BLACKBOX_AUDIT_DIR": str(aud)})
    assert "-1322" in r.stdout, (
        "el signo se perdio: la victima sale como 4294965974, que no es un pid")
    assert "4294965974" not in r.stdout, (
        "y no puede salir la forma sin signo: quien la lea buscara un pid que "
        "no existe y contara la captura como misterio")


def test_un_campo_vacio_NO_desplaza_las_columnas(datos, tmp_path):
    """`IFS=$'\\t' read` COLAPSA tabuladores consecutivos, porque el tabulador
    es espacio en blanco para IFS. Un campo vacio corria todos los de su
    derecha.

    Medido: con `comm` ausente la fila salia
    `python3.12[1841782] humano auid=? -> [?]` y debajo `exe: 1000` -- el auid
    aterrizando en la columna de exe. El emisor mostraba la ruta del ejecutable
    como si fuera su nombre.
    """
    aud = tmp_path / "audit"; aud.mkdir()
    (aud / "audit.log").write_text(
        _syscall(int(time.time()) - 60, 9001, pid=6666, comm="", auid="1000"),
        encoding="utf-8")
    r = correr(["sigterm", "10 minutes ago"], datos, {"BLACKBOX_AUDIT_DIR": str(aud)})
    assert "exe: /usr/bin/x" in r.stdout, (
        f"la columna de exe no trae el exe; se desplazo:\n{r.stdout}")
    assert "auid=1000" in r.stdout


def test_sigterm_ACUMULA_fuera_del_anillo_y_no_duplica(datos, tmp_path):
    """El anillo retiene 136 min; la ficha esperaba un mes de acumulacion.

    `bb sample` barre y escribe lo nuevo en sigterm.jsonl. El control que
    importa es el segundo: una segunda pasada sobre el mismo anillo no puede
    volver a escribir lo mismo, o el fichero crece por muestra en vez de por
    evento.
    """
    aud = tmp_path / "audit"; aud.mkdir()
    ts = int(time.time())
    (aud / "audit.log").write_text(
        _syscall(ts - 60, 9001, pid=7777, comm='"asesino"', auid="4294967295"),
        encoding="utf-8")
    env = {"BLACKBOX_AUDIT_DIR": str(aud)}
    assert correr(["sample"], datos, env).returncode == 0
    acum = Path(datos) / "sigterm.jsonl"
    assert acum.is_file(), "no se acumulo nada"
    filas = [json.loads(l) for l in acum.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(filas) == 1, filas
    assert filas[0]["emisor"]["comm"] == "asesino"
    assert filas[0]["emisor"]["clase"] == "demonio"
    assert str(filas[0]["victima"]["pid"]) == "1234"

    # El control negativo: otra pasada, mismo anillo, ni una fila mas.
    assert correr(["sample"], datos, env).returncode == 0
    filas2 = [l for l in acum.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(filas2) == 1, (
        f"la segunda pasada duplico: {len(filas2)} filas. La marca de agua no "
        "esta cortando, asi que el fichero crece por muestra y no por evento")


# `cmd_drift` en `bin/bb` derivaba `root` de `$0` sin forma de apuntarlo a otro
# sitio, asi que la unica manera de probar una divergencia REAL era escribir
# sobre los 39 sujetos adoptados de la maquina de verdad -- inaceptable para
# un test. BLACKBOX_DRIFT_ROOT (anadido junto con el arreglo del exit code,
# 2026-09-28) sigue el mismo patron que BLACKBOX_DATA: un repo de mentira,
# y HOME tambien de mentira para el lado desplegado, sin tocar la maquina.

@pytest.fixture
def raiz_drift(tmp_path):
    raiz = tmp_path / "repo"
    (raiz / "adopted" / "systemd-user").mkdir(parents=True)
    home = tmp_path / "home"
    (home / ".config" / "systemd" / "user").mkdir(parents=True)
    return raiz, home


def _correr_drift(raiz, home):
    return correr(["drift"], extra_env={
        "BLACKBOX_DRIFT_ROOT": str(raiz), "HOME": str(home)})


def test_drift_SALE_0_cuando_el_repo_describe_la_maquina(raiz_drift):
    raiz, home = raiz_drift
    contenido = "[Unit]\nDescription=fake\n"
    (raiz / "adopted" / "systemd-user" / "fake.timer").write_text(contenido, encoding="utf-8")
    (home / ".config" / "systemd" / "user" / "fake.timer").write_text(contenido, encoding="utf-8")
    r = _correr_drift(raiz, home)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "revisados: 1   divergentes: 0   ausentes: 0" in r.stdout


def test_drift_SALE_DISTINTO_DE_0_cuando_diverge(raiz_drift):
    """El control negativo del arreglo: antes del 2026-09-28 `cmd_drift`
    terminaba con `return 0` sin condicion, asi que este mismo fixture --
    una divergencia real, a proposito -- habria dado exit 0 igual. Si esta
    asercion pasa contra el codigo VIEJO, el arreglo no esta probando nada;
    contra `git stash` del cambio de `bin/bb` falla, que es la prueba de que
    el control negativo puede salir negativo."""
    raiz, home = raiz_drift
    (raiz / "adopted" / "systemd-user" / "fake.timer").write_text(
        "[Unit]\nDescription=repo\n", encoding="utf-8")
    (home / ".config" / "systemd" / "user" / "fake.timer").write_text(
        "[Unit]\nDescription=maquina\n", encoding="utf-8")
    r = _correr_drift(raiz, home)
    assert r.returncode != 0, f"diverge en el fixture y el exit code sigue en 0:\n{r.stdout}"
    assert "DIVERGE" in r.stdout
    assert "divergentes: 1" in r.stdout


def test_drift_SALE_DISTINTO_DE_0_cuando_esta_ausente(raiz_drift):
    raiz, home = raiz_drift
    (raiz / "adopted" / "systemd-user" / "fake.timer").write_text("[Unit]\n", encoding="utf-8")
    # no se crea el lado desplegado: ausente
    r = _correr_drift(raiz, home)
    assert r.returncode != 0, r.stdout
    assert "AUSENTE" in r.stdout
    assert "ausentes: 1" in r.stdout


def test_drift_suspendido_VIGENTE_no_cuenta_como_fallo(raiz_drift):
    """Suspendido es un estado documentado y esperado (ADR 0004, `suspended/
    MANIFIESTO.md`): no puede tumbar el exit code o cada suspension legitima
    rompe el chequeo diario contra su propio proposito."""
    raiz, home = raiz_drift
    destino = home / ".config" / "systemd" / "user" / "fake.timer"
    (raiz / "adopted" / "systemd-user" / "fake.timer").write_text("[Unit]\n", encoding="utf-8")
    manifest = raiz / "suspended" / "MANIFIESTO.md"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        "## fake.timer -- suspendido de mentira\n\n"
        "| | |\n|---|---|\n"
        f"| **Ruta original** | `{destino}` |\n"
        "| **Caduca** | **2099-01-01** -- nunca en este test |\n",
        encoding="utf-8")
    r = _correr_drift(raiz, home)
    assert r.returncode == 0, f"suspendido vigente y el exit code no es 0:\n{r.stdout}"
    assert "SUSPENDIDO" in r.stdout


def test_drift_suspension_VENCIDA_SI_cuenta_como_fallo(raiz_drift):
    """El control negativo del anterior: la MISMA suspension, con `Caduca` en
    el pasado, tiene que volver a contar -- si no, una suspension vieja se
    vuelve invisible para siempre en vez de pedir revision."""
    raiz, home = raiz_drift
    destino = home / ".config" / "systemd" / "user" / "fake.timer"
    (raiz / "adopted" / "systemd-user" / "fake.timer").write_text("[Unit]\n", encoding="utf-8")
    manifest = raiz / "suspended" / "MANIFIESTO.md"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        "## fake.timer -- suspendido de mentira\n\n"
        "| | |\n|---|---|\n"
        f"| **Ruta original** | `{destino}` |\n"
        "| **Caduca** | **2020-01-01** -- vencida a proposito |\n",
        encoding="utf-8")
    r = _correr_drift(raiz, home)
    assert r.returncode != 0, f"suspension vencida y el exit code sigue en 0:\n{r.stdout}"
    assert "VENCIDA" in r.stdout


# =====================================================================
# bb scan -- "apps Electron sin renderer" (proceso vivo, UI muerta)
# =====================================================================
#
# DEBT-EL-GATE-DE-RENDERERS-EXIGE-CERO-NO-UI-MUERTA: el 2026-09-28 el OOM
# killer mato el renderer de UNA ventana de claude-desktop y la UI paso 59
# minutos sin pintar, pero el proceso "main" tenia un renderer HERMANO vivo
# (de otra ventana) bajo el mismo zygote, y el gate cuenta renderers por
# proceso main, no por ventana -- asi que "bb scan" reporto "apps sin
# renderer: 0" sobre un incidente real. Ese limite NO se arregla aqui (arreglarlo
# de verdad exige correlacionar con la ventana X, que la ficha deja declarado
# como trabajo futuro sin coste medido); lo que hace falta primero, y lo que
# faltaba antes de esta suite, es que el bloque tenga ALGUNA cobertura: ni
# siquiera su caso positivo (cero renderers -> SOSPECHOSO) se habia probado
# nunca. Los dos tests de abajo cierran eso.
#
# `cmd_scan` es un comando forense grande (journal, GPU, coredumps...) y
# lanzarlo entero por `bin/bb scan` seria lento y ruidoso para un test que solo
# quiere UNA de sus filas. En vez de eso, el bloque exacto de bin/bb:1100-1120
# se copia LITERAL (no se reinterpreta) a un script bash temporal, envuelto en
# una funcion para poder usar `local`. Si el bloque real cambia de forma en
# bin/bb, esta copia puede desincronizarse -- quien toque bin/bb:1100-1120
# deberia revisar esta constante tambien.

_BLOQUE_ELECTRON_BASH = r'''#!/usr/bin/env bash
# Copia LITERAL de bin/bb:1100-1120 (bloque "apps Electron sin renderer"
# dentro de cmd_scan), citada el 2026-09-28 -- ver
# tests/test_bb_bash.py::_BLOQUE_ELECTRON_BASH para el porque de la copia.
set -u

chequeo_electron() {
  # --- 5. apps Electron: viva pero sin renderer ----------------------------
  # La firma exacta del cuelgue del 2026-09-07: proceso principal vivo,
  # ventana mapeada, cero procesos --type=renderer.
  echo "-- apps Electron sin renderer (proceso vivo, UI muerta) --"
  local found=0
  for main in $(pgrep -f 'type=zygote' 2>/dev/null | while read -r p; do
        ps -o ppid= -p "$p" 2>/dev/null; done | sort -u); do
    [ -z "$main" ] && continue
    local exe name nrend
    exe=$(readlink -f "/proc/$main/exe" 2>/dev/null) || continue
    [ -z "$exe" ] && continue
    name=$(basename "$exe")
    nrend=$(pgrep -P "$main" -f 'type=renderer' 2>/dev/null | wc -l)
    # los renderers pueden colgar del zygote, no solo del main
    [ "$nrend" -eq 0 ] && nrend=$(ps -eo args= 2>/dev/null | grep -c "^$exe.*--type=renderer")
    if [ "$nrend" -eq 0 ]; then
      echo "  SOSPECHOSO  $name (pid $main): 0 renderers"
      found=$((found + 1))
    fi
  done
  echo "  apps sin renderer:           $found"
}

chequeo_electron
'''


def _correr_chequeo_electron(tmp_path):
    script = tmp_path / "chequeo_electron.sh"
    script.write_text(_BLOQUE_ELECTRON_BASH, encoding="utf-8")
    script.chmod(0o755)
    return subprocess.run(["bash", str(script)], capture_output=True, text=True,
                          timeout=30)


def _esperar_proceso(patron, timeout=15.0):
    """Espera a que pgrep -f encuentre `patron` y devuelve su primer pid.

    Sincroniza contra el fork+exec real en vez de confiar en un sleep fijo:
    el hijo backgrounded existe tras el fork, pero su cmdline no lleva el
    marcador hasta que su propio exec -a termina.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = subprocess.run(["pgrep", "-f", patron], capture_output=True, text=True)
        pids = r.stdout.split()
        if pids:
            return pids[0]
        time.sleep(0.05)  # blocking-sleep: intervalo de sondeo DENTRO de un bucle con deadline explicito (arriba), no una espera fija -- sin el, el bucle quema un nucleo entero re-consultando pgrep sin ceder CPU -- DEBT-EL-GATE-DE-RENDERERS-EXIGE-CERO-NO-UI-MUERTA  # sunset-reviewed: 2.0 -- nuevo el 2026-09-28, mismo commit que lo introduce
    raise AssertionError(f"ningun proceso con {patron!r} aparecio en {timeout}s")


def _lanzar_electron_falso(con_renderer):
    """Lanza un 'main' REAL (bash) con un hijo 'zygote' REAL marcado
    --type=zygote y, si con_renderer, un hijo HERMANO (no del zygote: del
    main, igual que en el incidente real) marcado --type=renderer.

    No son mocks de funciones de shell: son procesos de verdad que pgrep/ps/
    /proc pueden encontrar, porque el bloque bajo prueba llama a esos
    comandos directamente sobre el sistema real.
    """
    # los marcadores llevan la subcadena LITERAL que busca el bloque bajo
    # prueba ('type=zygote' / 'type=renderer', via pgrep -f) mas un sufijo
    # unico para poder esperarlos/matarlos sin tocar procesos reales del
    # sistema (p.ej. un claude-desktop real corriendo en la misma maquina).
    zyg_marca = "type=zygote-DEBT-EL-GATE-FALSO"
    rend_marca = "type=renderer-DEBT-EL-GATE-FALSO"
    lanzar_zyg = f'exec -a "{zyg_marca}" sleep 300 &\n'
    lanzar_rend = f'exec -a "{rend_marca}" sleep 300 &\n' if con_renderer else ""
    script = f'{lanzar_zyg}{lanzar_rend}wait\n'
    # start_new_session=True: el bash principal y sus hijos backgrounded
    # quedan en un pgid propio = proc.pid, para poder matarlos a los tres de
    # un solo killpg sin arrastrar a ningun otro proceso del sistema.
    proc = subprocess.Popen(["bash", "-c", script], start_new_session=True)
    zyg_pid = _esperar_proceso(zyg_marca)
    rend_pid = _esperar_proceso(rend_marca) if con_renderer else None
    marcadores = [zyg_marca] + ([rend_marca] if con_renderer else [])
    return proc, marcadores, zyg_pid, rend_pid


def _matar_electron_falso(proc, marcadores, timeout=15.0):
    """Mata el arbol completo y prueba, no argumenta, que no queda huerfano:
    negativo real sobre pgrep, no solo `proc.wait()` del padre inmediato."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=timeout)
    deadline = time.time() + timeout
    for patron in marcadores:
        while True:
            r = subprocess.run(["pgrep", "-f", patron], capture_output=True, text=True)
            if not r.stdout.strip():
                break
            assert time.time() < deadline, (
                f"proceso huerfano con {patron!r} sigue vivo tras matar el arbol")
            time.sleep(0.05)  # blocking-sleep: intervalo de sondeo DENTRO de un bucle con deadline explicito (arriba), no una espera fija -- confirma que un huerfano de verdad muere, no solo lo asume -- DEBT-EL-GATE-DE-RENDERERS-EXIGE-CERO-NO-UI-MUERTA  # sunset-reviewed: 2.0 -- nuevo el 2026-09-28, mismo commit que lo introduce


def test_electron_ui_muerta_con_hermano_vivo_pasa_limpio(tmp_path):
    """El caso de HOY (2026-09-28): documenta el LIMITE, no lo arregla.

    Un 'main' con un renderer HERMANO vivo (de otra ventana) no se marca
    SOSPECHOSO, aunque conceptualmente la ventana de ESTE renderer muerto
    podria seguir sin pintar -- porque el chequeo cuenta renderers por
    proceso zygote/main, no por ventana individual. Esto es una LIMITACION
    CONOCIDA y documentada en DEBT-EL-GATE-DE-RENDERERS-EXIGE-CERO-NO-UI-MUERTA,
    no un comportamiento que este test valide como correcto: pasar limpio es
    justo lo que dejo pasar el incidente real sin avisar.
    """
    # el "main" real es el propio proceso bash lanzado: pgrep -P lo
    # encuentra por ppid, exactamente como lo hace el bloque bajo prueba.
    proc, marcadores, _zyg_pid, _rend_pid = _lanzar_electron_falso(con_renderer=True)
    try:
        r = _correr_chequeo_electron(tmp_path)
        assert r.returncode == 0, r.stderr
        linea_sospechosa = f"(pid {proc.pid}):"
        assert linea_sospechosa not in r.stdout, (
            "el gate SI marco SOSPECHOSO a un main con un renderer hermano "
            f"vivo -- eso contradice el limite documentado:\n{r.stdout}")
    finally:
        _matar_electron_falso(proc, marcadores)


def test_electron_ui_muerta_CERO_renderers_SI_dispara_SOSPECHOSO(tmp_path):
    """El control negativo real que la ficha dice que NUNCA se corrio: el
    mismo 'main', pero sin ningun renderer vivo (ni propio ni hermano).

    Sin este test, el de arriba (pasa limpio con un hermano vivo) no prueba
    nada: podria estar pasando limpio porque la rama `-eq 0` esta rota, no
    porque el hermano la evite. Este es el caso que la ficha describe como
    "nunca antes probado" -- un gate con cero capturas tras muchas corridas
    es un defecto del instrumento, no evidencia de que el sujeto este limpio.
    """
    proc, marcadores, _zyg_pid, _rend_pid = _lanzar_electron_falso(con_renderer=False)
    try:
        r = _correr_chequeo_electron(tmp_path)
        assert r.returncode == 0, r.stderr
        linea_sospechosa = f"(pid {proc.pid}): 0 renderers"
        assert linea_sospechosa in r.stdout, (
            f"el gate NO marco SOSPECHOSO a un main sin ningun renderer "
            f"vivo -- la rama '-eq 0' nunca se habia probado y esta es "
            f"la prueba de que SI dispara:\n{r.stdout}")
        assert "apps sin renderer:" in r.stdout
        conteo = int(r.stdout.split("apps sin renderer:")[1].split()[0])
        assert conteo >= 1, (
            f"SOSPECHOSO salio en el detalle pero el conteo no lo reflejo: {r.stdout}")
    finally:
        _matar_electron_falso(proc, marcadores)
