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


def muestras(datos):
    f = datos / "samples" / time.strftime("%Y-%m-%d") + ".jsonl" if False else \
        next((datos / "samples").glob("*.jsonl"), None)
    if f is None:
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


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
    hijo = subprocess.Popen(
        [sys.executable, "-c",
         "import mmap,time; m=mmap.mmap(-1, 5*1024**3); time.sleep(20)"])
    try:
        time.sleep(3)  # blocking-sleep: se espera a que el hijo reserve -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 1.3 -- relido 2026-09-25: relido 2026-09-24: nace en 1.0: espera a un SUBPROCESO, no a estado propio; no hay evento que compartir con un hijo que reserva memoria
        correr(["sample"], datos)                  # muestra 2: ya crecio
        d = muestras(datos)[-1]
        crecidos = {x["pid"]: x for x in d["pidio"]}
        assert hijo.pid in crecidos, f"no nombro al pid {hijo.pid}: {d['pidio']}"
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
    quieto = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"])
    try:
        time.sleep(1)  # blocking-sleep: el hijo tiene que existir ya -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 1.3 -- relido 2026-09-25: relido 2026-09-24: nace en 1.0: sondear /proc/<pid> seria cambiar un sleep por otro con mas codigo
        correr(["sample"], datos)
        time.sleep(2)  # blocking-sleep: separa las dos muestras -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 1.3 -- relido 2026-09-25: relido 2026-09-24: nace en 1.0: bb marca las muestras con resolucion de segundo; sin la espera caen en el mismo
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
    time.sleep(4)  # blocking-sleep: el ritmo es un delta y necesita dos instantes separados -- DEBT-ACCEPTED-SLEEP-TESTS-BB
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
    time.sleep(2)  # blocking-sleep: dos muestras separadas, mismos contadores -- DEBT-ACCEPTED-SLEEP-TESTS-BB
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
    time.sleep(2)  # blocking-sleep: dos muestras separadas -- DEBT-ACCEPTED-SLEEP-TESTS-BB
    correr(["sample"], datos, {"BB_VMSTAT": _vmstat(tmp_path, 12, 34)})
    s = muestras(datos)[-1]["swap"]
    assert float(s["in_pag_s"]) == 0.0, s
    assert float(s["out_pag_s"]) == 0.0, s


# =====================================================================
# bb status -- el veredicto sobre la propia instrumentacion
# =====================================================================


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
    quemador = subprocess.Popen(["bash", "-c", "while :; do :; done"])
    try:
        time.sleep(1)  # blocking-sleep: el hijo tiene que existir en la muestra 1 -- DEBT-ACCEPTED-SLEEP-TESTS-BB
        correr(["sample"], datos)                  # muestra 1: linea base
        time.sleep(4)  # blocking-sleep: `ps -o times=` da segundos ENTEROS; hacen falta varios para que el delta sea legible -- DEBT-ACCEPTED-SLEEP-TESTS-BB
        correr(["sample"], datos)                  # muestra 2: ya quemo
        d = muestras(datos)[-1]
        por_pid = {x["pid"]: x for x in d["cpu_top"]}
        assert quemador.pid in por_pid, \
            f"no nombro al pid {quemador.pid} que quemaba un nucleo entero: {d['cpu_top']}"
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
    dormido = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"])
    try:
        time.sleep(1)  # blocking-sleep: el hijo tiene que existir ya -- DEBT-ACCEPTED-SLEEP-TESTS-BB
        correr(["sample"], datos)
        time.sleep(4)  # blocking-sleep: mismo intervalo que el caso positivo, para que la comparacion valga -- DEBT-ACCEPTED-SLEEP-TESTS-BB
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


@pytest.mark.sleeps_aceptados
def test_residuo_es_un_numero_y_no_se_mueve_solo(datos):
    """Mide memoria que nadie reclama. Entre dos muestras en reposo tiene que
    quedarse practicamente igual, o su delta no significaria nada."""
    correr(["sample"], datos)
    time.sleep(1)  # blocking-sleep: dos muestras distintas -- DEBT-ACCEPTED-SLEEP-TESTS-BB  # sunset-reviewed: 1.3 -- relido 2026-09-25: relido 2026-09-24: nace en 1.0: misma razon, resolucion de segundo del sello de bb
    correr(["sample"], datos)
    a, b = (int(x["residuo_mb"]) for x in muestras(datos)[:2])
    assert abs(b - a) < 2048, f"el residuo se movio {b-a} MiB sin que nadie pidiera"


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
    # Ruido de rustdesk LLEGANDO ahora: la regla no esta cargada.
    (aud / "audit.log").write_text(
        f'type=SYSCALL msg=audit({ts}.1:1): arch=c00000b7 auid=4294967295 '
        f'comm="loginctl" exe="/usr/bin/loginctl" key="reboot_cmd"\n',
        encoding="utf-8")
    r = correr(["sigterm", "5 minutes ago"], datos, {"BLACKBOX_AUDIT_DIR": str(aud)})
    assert "NO ARMADO" in r.stdout
    assert "could_not_run: 1" in r.stdout

    # El mismo ruido, pero viejo: la regla ya esta puesta.
    (aud / "audit.log").write_text(
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
