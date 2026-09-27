"""Cobertura de bin/bb-usable -- el vigilante que decide reiniciar la maquina.

## Por que existe este fichero

Hasta el 2026-09-24 `bb-usable` no tenia una sola prueba. Ese dia se descubrio
que su premisa fundacional era falsa: afirmaba que durante un colapso "una
asignacion de 64 MiB no habria vuelto", y medida en el tercer congelamiento la
sonda volvio en 18-21 ms mientras la maquina llevaba cinco horas inservible.

SE DICE CON PRECISION, porque la tentacion es venderlo al reves: **ninguna
suite habria cazado esa premisa falsa.** Era una afirmacion sobre el
comportamiento del kernel bajo un colapso real, y lo unico que puede
falsificarla es un colapso real -- que es exactamente lo que paso. Lo que
estos tests SI compran es que el camino de accion nuevo no se degrade en
silencio: la aritmetica del umbral, que una lectura ilegible no reinicie la
caja, y que un pico sano no la reinicie tampoco.

El arnes con el que se verifico el arreglo el mismo dia vivia en /tmp y se
habria perdido. Esto es ese arnes, convertido en suite.

## Como se carga un ejecutable sin extension .py

`bin/bb-usable` es un ejecutable Python sin `.py`, asi que ni el import normal
ni la autodeteccion de `coverage_target` lo alcanzan (ver la exencion de
.gitignore y corpus_exempt.yaml, que lo declaran FUERA de `coverage_targets`).
`SourceFileLoader` si lo carga, y su guarda `if __name__ == "__main__"` impide
que cargarlo arranque el demonio.
"""

from __future__ import annotations

import importlib.machinery as machinery
import importlib.util as util
from pathlib import Path

import pytest

RUTA = Path(__file__).resolve().parent.parent / "bin" / "bb-usable"


def _cargar():
    """Carga bin/bb-usable como modulo, sin ejecutar main()."""
    loader = machinery.SourceFileLoader("bb_usable", str(RUTA))
    spec = util.spec_from_loader("bb_usable", loader)
    assert spec is not None, f"no se pudo construir el spec de {RUTA}"
    mod = util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.fixture
def bbu():
    return _cargar()


# ----------------------------------------------------- lectura de la senal


def test_lee_el_full_avg10(bbu, tmp_path, monkeypatch):
    p = tmp_path / "pressure"
    p.write_text("some avg10=1.00 avg60=0 avg300=0 total=1\n"
                 "full avg10=98.70 avg60=0 avg300=0 total=1\n", encoding="ascii")
    monkeypatch.setattr(bbu, "PSI_PATH", str(p))
    assert bbu.psi_memory_full_avg10() == pytest.approx(98.70)


def test_control_negativo_lee_tambien_un_valor_sano(bbu, tmp_path, monkeypatch):
    """Sin esto, el test de arriba no distingue "lee" de "devuelve siempre alto"."""
    p = tmp_path / "pressure"
    p.write_text("some avg10=0.00 avg60=0 avg300=0 total=1\n"
                 "full avg10=0.00 avg60=0 avg300=0 total=1\n", encoding="ascii")
    monkeypatch.setattr(bbu, "PSI_PATH", str(p))
    assert bbu.psi_memory_full_avg10() == 0.0


def test_sin_fichero_devuelve_None_no_cero(bbu, tmp_path, monkeypatch):
    """None es "no se midio". Devolver 0.0 convertiria un instrumento ausente
    en un veredicto de "todo bien", que es la forma exacta de mentir que este
    repo persigue."""
    monkeypatch.setattr(bbu, "PSI_PATH", str(tmp_path / "no-existe"))
    assert bbu.psi_memory_full_avg10() is None


def test_fichero_ilegible_devuelve_None(bbu, tmp_path, monkeypatch):
    p = tmp_path / "pressure"
    p.write_text("full avg10=no-es-un-numero\n", encoding="ascii")
    monkeypatch.setattr(bbu, "PSI_PATH", str(p))
    assert bbu.psi_memory_full_avg10() is None
    p.write_text("some avg10=1.0 total=1\n", encoding="ascii")
    assert bbu.psi_memory_full_avg10() is None, "sin linea 'full' no hay dato"


# ------------------------------------------------------------- los cortes


def test_el_corte_es_el_calibrado_y_no_otro(bbu):
    """Fijar los numeros aqui hace que cambiarlos sea deliberado. Salen de
    tools/calibra_psi.py, validado contra los TRES congelamientos reales con
    falsos positivos 0 e incidentes no detectados 0."""
    assert bbu.PSI_ACT_FULL_AVG10 == 10.0
    assert bbu.PSI_ACT_SOSTENIDO_S == 300.0


def test_las_sondas_cubren_el_plazo_exacto(bbu):
    """La aritmetica que decide cuando se reinicia la maquina."""
    assert bbu.PSI_ACT_SONDAS * bbu.PROBE_INTERVAL == bbu.PSI_ACT_SOSTENIDO_S
    assert bbu.PSI_ACT_SONDAS == 10


# ------------------------------------ el bucle: cuando acaricia y cuando no


def _correr(bbu, monkeypatch, serie):
    """Corre el bucle real contra una serie de lecturas de PSI.

    Devuelve (caricias, lineas). Se anula el sleep y la sonda -- NO la logica
    que se esta probando -- y se corta por StopIteration cuando la serie se
    agota, que es lo que saca del `while True`.
    """
    caricias, lineas = [], []
    monkeypatch.setattr(bbu, "notify", lambda s: caricias.append(s))
    monkeypatch.setattr(bbu, "probe", lambda: 0.001)
    monkeypatch.setattr(bbu.time, "sleep", lambda s: None)
    it = iter(serie)

    def leer():
        try:
            return next(it)
        except StopIteration:
            raise SystemExit

    monkeypatch.setattr(bbu, "psi_memory_full_avg10", leer)
    monkeypatch.setattr(bbu.sys, "stderr", type("F", (), {
        "write": lambda _self, m: lineas.append(m), "flush": lambda _self: None})())
    with pytest.raises(SystemExit):
        bbu.main()
    # La primera caricia es la de arranque, tras la sonda de referencia.
    return sum(1 for c in caricias if c == "WATCHDOG=1") - 1, "".join(lineas)


def test_con_la_maquina_sana_acaricia_siempre(bbu, monkeypatch):
    caricias, _ = _correr(bbu, monkeypatch, [0.0] * 12)
    assert caricias == 12, "una maquina sana no puede quedarse sin caricias"


def test_con_el_colapso_del_2026_09_24_deja_de_acariciar(bbu, monkeypatch):
    """El caso real: PSI 99 sostenida. Acaricia 9 veces y corta en la 10a,
    que son los 300 s del corte. systemd cobra dentro de WatchdogSec."""
    caricias, salida = _correr(bbu, monkeypatch, [99.0] * 15)
    assert caricias == bbu.PSI_ACT_SONDAS - 1 == 9
    assert "COLAPSO" in salida
    assert "NO se acaricia el watchdog" in salida


def test_control_negativo_un_pico_sano_no_reinicia(bbu, monkeypatch):
    """Entre los 7 picos sanos del corpus hay dos que llegaron a 90.69 % y
    98.53 % durante 2 minutos. Un corte por NIVEL los habria reiniciado; el
    de DURACION no. Este test es ese control."""
    caricias, salida = _correr(bbu, monkeypatch, [99.0] * 4 + [0.0] * 8)
    assert caricias == 12, "un pico de 2 min no puede reiniciar la maquina"
    assert "COLAPSO" not in salida
    assert "Era un pico, no un colapso" in salida


def test_justo_por_debajo_del_plazo_todavia_acaricia(bbu, monkeypatch):
    """El borde: 9 sondas son 270 s, uno menos que el corte."""
    caricias, salida = _correr(bbu, monkeypatch, [99.0] * (bbu.PSI_ACT_SONDAS - 1))
    assert caricias == bbu.PSI_ACT_SONDAS - 1
    assert "COLAPSO" not in salida


def test_psi_ilegible_no_reinicia_pero_tampoco_absuelve(bbu, monkeypatch):
    """Reiniciar por ceguera seria peor que el fallo que se vigila. Pero una
    lectura perdida EN MEDIO de un colapso no puede borrar la racha."""
    caricias, salida = _correr(bbu, monkeypatch, [None] * 15)
    assert caricias == 15, "no se reinicia por no poder medir"
    assert "PSI ILEGIBLE" in salida

    caricias, salida = _correr(
        bbu, monkeypatch, [99.0] * 5 + [None] + [99.0] * 5)
    assert "COLAPSO" in salida, "la racha sobrevive a una lectura perdida"


def test_una_sonda_fuera_de_plazo_corta_aunque_PSI_este_sana(bbu, monkeypatch):
    """El camino viejo sigue vivo: cubre un fallo distinto -- una caja que de
    verdad no sirve memoria -- aunque no cubriera ninguno de los tres casos."""
    caricias, lineas = [], []
    monkeypatch.setattr(bbu, "notify", lambda s: caricias.append(s))
    monkeypatch.setattr(bbu, "probe", lambda: bbu.PROBE_DEADLINE + 1)
    monkeypatch.setattr(bbu.time, "sleep", lambda s: None)
    it = iter([0.0, 0.0])

    def leer():
        try:
            return next(it)
        except StopIteration:
            raise SystemExit

    monkeypatch.setattr(bbu, "psi_memory_full_avg10", leer)
    monkeypatch.setattr(bbu.sys, "stderr", type("F", (), {
        "write": lambda _self, m: lineas.append(m), "flush": lambda _self: None})())
    with pytest.raises(SystemExit):
        bbu.main()
    assert sum(1 for c in caricias if c == "WATCHDOG=1") - 1 == 0
    assert "SONDA FUERA DE PLAZO" in "".join(lineas)


# --------------------------------------------------------------- la sonda


def test_la_sonda_pide_y_TOCA_la_memoria(bbu):
    """Pedirla sin tocarla no prueba nada: Linux no asigna paginas hasta el
    primer acceso. La sonda devuelve un tiempo real y positivo."""
    t = bbu.probe()
    assert t > 0
    assert t < 60, "en una maquina sana la sonda es de milisegundos"


def test_notify_manda_de_verdad_por_el_socket(bbu, tmp_path, monkeypatch):
    """La caricia es lo unico que separa "todo bien" de "reinicia la maquina",
    asi que se comprueba que SALE, no solo que no revienta."""
    import socket

    ruta = tmp_path / "notify.sock"
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    srv.bind(str(ruta))
    srv.settimeout(2)
    monkeypatch.setenv("NOTIFY_SOCKET", str(ruta))
    try:
        bbu.notify("WATCHDOG=1")
        assert srv.recv(64) == b"WATCHDOG=1"
    finally:
        srv.close()


def test_notify_sin_socket_no_manda_nada_y_no_revienta(bbu, tmp_path, monkeypatch):
    """Control negativo del de arriba: fuera de systemd no hay NOTIFY_SOCKET,
    el demonio tiene que poder cargarse igual (o estos tests no existirian) y
    ahi NO puede llegar nada al socket."""
    import socket

    ruta = tmp_path / "notify2.sock"
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    srv.bind(str(ruta))
    srv.settimeout(0.2)
    monkeypatch.delenv("NOTIFY_SOCKET", raising=False)
    try:
        bbu.notify("WATCHDOG=1")  # no debe lanzar
        # Se afirma SOBRE la excepcion, no solo que haya una: sin esto,
        # cualquier fallo del socket (permisos, ruta mala) se leeria como
        # "no llego nada", que es la conclusion que este test vende.
        with pytest.raises(socket.timeout) as exc:
            srv.recv(64)
        assert exc.type is socket.timeout
        assert "timed out" in str(exc.value).lower()
    finally:
        srv.close()


def test_la_racha_se_REINICIA_tras_un_pico_no_se_acumula(bbu, monkeypatch):
    """Altas, una RECUPERACION, y altas otra vez: la racha no se acumula.

    ESTE TEST CAMBIO DE PREMISA EL 2026-09-26, y el cambio esta medido.

    Decia "nueve lecturas altas, UNA sana, y una alta mas" y exigia que no
    hubiera colapso, llamando a esa unica lectura baja "una recuperacion real".
    Esa premisa era falsa y nadie la habia medido. El kernel panic de las
    15:38:26 la midio: dentro de un colapso de 16 minutos hubo TRES bajadas de
    una sola sonda (2.4, 3.7 y 9.8) y cada una absolvio el colapso entero. La
    maquina murio con el vigilante armado. Ver
    DEBT-UNA-BAJADA-MOMENTANEA-ABSUELVE-UN-COLAPSO.

    Lo que el test mide sigue siendo lo mismo -- que la racha se REINICIA y no
    se acumula-- y su razon de existir tambien: el mutante que cambia
    `sostenido = 0` por `pass` SE ESCAPABA de la suite, porque el caso
    [alto x4, sano x8] no lo distingue (ahi la racha ya no vuelve a crecer).
    Hace falta alto -> recuperacion -> alto. Lo unico que cambio es que una
    recuperacion son `BAJAS_PARA_CORTAR` sondas, no una.
    """
    serie = ([99.0] * (bbu.PSI_ACT_SONDAS - 1)
             + [0.0] * bbu.BAJAS_PARA_CORTAR + [99.0])
    caricias, salida = _correr(bbu, monkeypatch, serie)
    assert "COLAPSO" not in salida, (
        "la recuperacion de en medio tiene que borrar la racha; si no, dos "
        "episodios sanos separados reinician la maquina"
    )
    assert caricias == len(serie)


# =====================================================================
# latencia del escritorio -- se OBSERVA, no se actua sobre ella
# =====================================================================


def _xset_falso(tmp_path, cuerpo):
    f = tmp_path / "xset_falso"
    f.write_text("#!/usr/bin/env bash\n" + cuerpo, encoding="utf-8")
    f.chmod(0o755)
    return str(f)


def test_observa_la_latencia_del_servidor_grafico(bbu, tmp_path, monkeypatch):
    """El 2026-09-25 la maquina fue inusable para teclear con `mem_full` en 0.00
    casi todo el rato. Este demonio vio una caja sana y tenia razon por su
    definicion: pregunta si sirve MEMORIA. Esto anade la otra pregunta.
    """
    monkeypatch.setenv("DISPLAY", ":1")
    monkeypatch.setenv("BB_USABLE_XSET", _xset_falso(tmp_path, "exit 0\n"))
    v = bbu.latencia_x_ms()
    assert v is not None and v >= 0


def test_control_negativo_un_servidor_que_se_cuelga_devuelve_el_PLAZO(
        bbu, tmp_path, monkeypatch):
    """El caso que importa: el servidor X vivo pero sin atender. Tiene que
    devolver el plazo entero, no un numero pequeno -- si devolviera algo bajo,
    una grafica leeria 'rapido' justo durante el incidente."""
    monkeypatch.setenv("DISPLAY", ":1")
    monkeypatch.setenv("BB_USABLE_XSET", _xset_falso(tmp_path, "sleep 30\n"))
    monkeypatch.setenv("BB_USABLE_X_TIMEOUT_S", "1")
    assert bbu.latencia_x_ms() >= 900


def test_control_negativo_sin_DISPLAY_devuelve_None_y_no_cero(bbu, monkeypatch):
    """`None` y `0 ms` no son lo mismo: uno dice 'no se midio' y el otro
    'instantaneo'. Reportar el segundo por el primero es como reiniciar por
    ceguera, que es el error que este fichero ya documenta haber cometido."""
    monkeypatch.delenv("DISPLAY", raising=False)
    assert bbu.latencia_x_ms() is None


@pytest.mark.parametrize("cuerpo", ["exit 1\n", "exit 127\n"])
def test_control_negativo_un_servidor_que_rechaza_devuelve_None(
        bbu, tmp_path, monkeypatch, cuerpo):
    monkeypatch.setenv("DISPLAY", ":1")
    monkeypatch.setenv("BB_USABLE_XSET", _xset_falso(tmp_path, cuerpo))
    assert bbu.latencia_x_ms() is None


def test_el_comando_se_lee_del_entorno_EN_CADA_llamada(bbu, tmp_path, monkeypatch):
    """Ligarlo al importar dejaba los casos negativos sin poder montarse: al
    cambiar la variable despues, la funcion seguia llamando al `xset` real y
    devolvia un numero donde debia devolver `None`. Lo encontro el control
    negativo, no leer el codigo.
    """
    monkeypatch.setenv("DISPLAY", ":1")
    monkeypatch.setenv("BB_USABLE_XSET", _xset_falso(tmp_path, "exit 0\n"))
    assert bbu.latencia_x_ms() is not None
    monkeypatch.setenv("BB_USABLE_XSET", "/no/existe/xset")
    assert bbu.latencia_x_ms() is None


def test_la_latencia_NO_entra_en_ninguna_decision(bbu):
    """La propiedad mas importante de este cambio, y por eso tiene test: este
    proceso no informa, ACTUA -- su unit lleva FailureAction=reboot-immediate.
    Con UNA medida sana y CERO episodios malos no hay calibracion posible, y un
    vigilante que actua sobre un numero sin calibrar reinicia la maquina y
    ademas afirma haber tenido razon.

    Se comprueba sobre el texto porque lo que se guarda es una AUSENCIA: que
    ninguna rama de decision consulte la latencia.
    """
    import ast
    fuente = Path(bbu.__file__).read_text(encoding="utf-8") if getattr(bbu, "__file__", None) \
        else (Path(__file__).resolve().parent.parent / "bin" / "bb-usable").read_text(encoding="utf-8")
    arbol = ast.parse(fuente)
    principal = next(n for n in ast.walk(arbol)
                     if isinstance(n, ast.FunctionDef) and n.name == "main")
    for nodo in ast.walk(principal):
        if isinstance(nodo, (ast.If, ast.While)):
            usados = {n.id for n in ast.walk(nodo.test) if isinstance(n, ast.Name)}
            assert "xms" not in usados, (
                "la latencia entro en una decision de bb-usable: eso es darle "
                "permiso para reiniciar la maquina por un umbral sin calibrar")


# ------------------------------------ DEBT-UNA-BAJADA-MOMENTANEA-ABSUELVE-UN-COLAPSO
#
# El 2026-09-26 a las 15:38:26 esta maquina murio de un kernel panic
# (`hung_task: blocked tasks`) con este demonio armado, corriendo, y viendo el
# colapso entero. Su journal lo cuenta:
#
#   15:33:02  racha  9/10 (270s)  avg10=83.2   <- ultima caricia
#   15:33:32  COLAPSO sostenido 300s -- NO se acaricia
#   15:34:32  COLAPSO sostenido 360s -- NO se acaricia
#   15:35:02  PSI bajo a 9.8: la racha de 360s SE CORTA
#   15:35:32  racha  1/10  avg10=80.2
#   15:38:02  racha  6/10  avg10=92.2          <- ultima caricia real
#   15:38:26  KERNEL PANIC
#
# Una bajada de UNA sonda a 9.8 -- dentro de un colapso de 16 minutos, con dos
# decimas por debajo del umbral-- puso la racha a cero y volvio a acariciar el
# watchdog. Hubo tres de esas (2.4, 3.7, 9.8) en la misma ventana.


def test_una_bajada_suelta_NO_absuelve_un_colapso(bbu, monkeypatch):
    """El sujeto es la traza real: 10 sondas altas, una baja, y sigue alto.

    Con el defecto, la baja reseteaba la racha Y acariciaba, asi que el
    watchdog volvia a tener sus 6 minutos enteros y el colapso no cobraba
    nunca. Con el arreglo la racha sobrevive y el demonio deja de acariciar.
    """
    serie = [99.0] * bbu.PSI_ACT_SONDAS + [9.8] + [99.0] * 5
    caricias, salida = _correr(bbu, monkeypatch, serie)
    assert "COLAPSO" in salida
    assert "UNA sonda no" in salida, (
        "la bajada suelta tiene que quedar registrada como no-absolucion")
    assert "se corta" not in salida, (
        "una sola bajada NO puede cortar la racha: es el defecto que mato la "
        "maquina el 2026-09-26")
    # Y lo que de verdad importa: la baja tampoco acaricia, porque la racha
    # sigue cumpliendo el criterio de accion.
    assert caricias == bbu.PSI_ACT_SONDAS - 1, (
        f"acaricio {caricias} veces; solo las {bbu.PSI_ACT_SONDAS - 1} de antes "
        "de que la racha llegara al corte pueden acariciar")


def test_control_negativo_DOS_bajadas_seguidas_SI_absuelven(bbu, monkeypatch):
    """Sin esto, el de arriba se 'arregla' no cortando nunca la racha.

    Un vigilante que no admite una recuperacion reinicia una maquina que ya
    esta bien, y eso es peor que el fallo que vigila: los siete picos sanos del
    corpus se recuperaron solos. La recuperacion tiene que reconocerse.
    """
    serie = [99.0] * 5 + [0.0] * bbu.BAJAS_PARA_CORTAR + [99.0] * 5
    caricias, salida = _correr(bbu, monkeypatch, serie)
    assert "se corta" in salida, (
        f"{bbu.BAJAS_PARA_CORTAR} bajadas seguidas son una recuperacion y "
        "tienen que cortar la racha")
    assert "COLAPSO" not in salida, (
        "cortada la racha, 5 sondas altas no llegan al corte de 300 s")
    assert caricias == len(serie), "una maquina recuperada recibe sus caricias"


def test_el_numero_de_bajadas_sale_del_control_de_falsos_positivos(bbu):
    """`BAJAS_PARA_CORTAR` no es un numero redondo elegido a ojo.

    Medido el 2026-09-26 sobre las 21 636 muestras del corpus
    (2026-09-11 -> 2026-09-26): el maximo tiempo sostenido que la regla
    acumula FUERA de una ventana de incidente es 180 s con 1 baja y los MISMOS
    180 s con 2, 3 o 6 -- en quince dias no hay una sola excursion sana con una
    bajada suelta dentro, asi que la superficie nueva de falso positivo es 0.
    Contra el corte de 300 s el margen es 1.67x.

    Este test fija el 2. Si alguien lo sube, el control hay que re-correrlo:
    la evidencia esta en
    tasks/evidence/DEBT-UNA-BAJADA-MOMENTANEA-ABSUELVE-UN-COLAPSO/.
    """
    assert bbu.BAJAS_PARA_CORTAR == 2
    assert bbu.BAJAS_PARA_CORTAR > 1, (
        "1 es el defecto: cualquier muestra suelta pone la duracion a cero, y "
        "una duracion asi no es una duracion")
    # Dos bajas son 60 s. El corte son 300 s: la ventana de absolucion tiene
    # que ser mucho menor que el criterio de accion, o absuelve colapsos.
    assert bbu.BAJAS_PARA_CORTAR * bbu.PROBE_INTERVAL < bbu.PSI_ACT_SOSTENIDO_S


def test_la_racha_alta_limpia_el_contador_de_bajadas(bbu, monkeypatch):
    """Bajadas SEGUIDAS, no acumuladas. Sin este reset, dos bajadas separadas
    por veinte sondas altas cortarian la racha igual que dos consecutivas, y el
    defecto volveria por la puerta de atras con un contador distinto."""
    serie = ([99.0] * 3 + [0.0]) * 3 + [99.0] * 3
    caricias, salida = _correr(bbu, monkeypatch, serie)
    assert "se corta" not in salida, (
        "tres bajadas AISLADAS no son una recuperacion sostenida")
