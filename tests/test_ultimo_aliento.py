"""Ultimo aliento: anillo de tamano fijo, fdatasync en hilo con plazo y snapshot atomico, cada propiedad con su control.

Todo corre contra una raiz falsa de /proc y /sys (costura `raiz`): este contenedor no es la ATOM y no tiene zonas
termicas de la GB10. Las mutaciones del tope de tamano (`seq % ranuras`) y del `rename` atomico de `escribir_estado`
las caza `test_el_anillo_nunca_crece_*` y `test_estado_maquina_*` respectivamente.
"""

import ast
import configparser
import io
import json
import os
import socket
import threading
import time
import zlib
from pathlib import Path

import pytest

from tools import ultimo_aliento as ua

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[1]
BOOT = "0123456789abcdef0123456789abcdef"


def raiz_falsa(base: Path, zonas: int = 0, hwmon: bool = False, psi: bool = True) -> str:
    """Arbol minimo de proc/ y sys/ con el formato real del kernel."""
    (base / "proc/sys/kernel/random").mkdir(parents=True)
    (base / "proc/sys/kernel/random/boot_id").write_text("01234567-89ab-cdef-0123-456789abcdef\n")
    if psi:
        (base / "proc/pressure").mkdir()
        for recurso in ("cpu", "memory", "io"):
            (base / f"proc/pressure/{recurso}").write_text(
                "some avg10=1.50 avg60=0.75 avg300=0.10 total=123456\n"
                "full avg10=0.00 avg60=0.00 avg300=0.00 total=0\n")
    (base / "proc/meminfo").write_text(
        "MemTotal:       131072000 kB\nMemFree:         1696136 kB\nMemAvailable:   60115000 kB\n"
        "SwapTotal:       16777212 kB\nSwapFree:        16000000 kB\nDirty:               168 kB\n")
    (base / "proc/loadavg").write_text("3.10 2.05 1.00 4/812 99999\n")
    (base / "sys/class/thermal").mkdir(parents=True)
    for n in range(zonas):
        d = base / f"sys/class/thermal/thermal_zone{n}"
        d.mkdir()
        (d / "type").write_text(f"soc_zone{n}\n")
        (d / "temp").write_text(f"{93000 + n * 500}\n")
        for i, (temp, tipo) in enumerate(((104800, "critical"), (99800, "hot"), (89800, "passive"))):
            (d / f"trip_point_{i}_temp").write_text(f"{temp}\n")
            (d / f"trip_point_{i}_type").write_text(f"{tipo}\n")
    (base / "sys/class/hwmon").mkdir(parents=True)
    if hwmon:
        d = base / "sys/class/hwmon/hwmon0"
        d.mkdir()
        (d / "name").write_text("pmic_falso\n")
        (d / "power1_input").write_text("82400000\n")
        (d / "in0_input").write_text("19500\n")
        (d / "curr1_input").write_text("4200\n")
        (d / "temp1_input").write_text("50000\n")  # control: temperatura de hwmon NO es potencia/voltaje/corriente
        (d / "device").mkdir()
        (d / "device/power2_input").write_text("1500000\n")  # driver viejo: atributo bajo device/
    return str(base)


def demonio(tmp_path: Path, raiz: str, **kw) -> ua.UltimoAliento:
    anillo = ua.Anillo(str(tmp_path / "anillo.bin"))
    anillo.abrir()
    kw.setdefault("intervalo", 0.02)
    kw.setdefault("sync_cada", 0.05)
    kw.setdefault("estado_cada", 0.05)
    kw.setdefault("bloquear", lambda: "omitido: prueba")  # mlockall de verdad bloquearia la memoria de pytest
    return ua.UltimoAliento(anillo, raiz=raiz, estado_ruta=str(tmp_path / "estado_maquina.json"), **kw)


def correr_mientras(d: ua.UltimoAliento, hasta, tope_s: float = 5.0) -> None:
    """Corre el bucle en un hilo hasta que `hasta()` sea cierto (o el tope), y lo para."""
    hilo = threading.Thread(target=d.correr, daemon=True)
    hilo.start()
    limite = time.monotonic() + tope_s
    while not hasta() and time.monotonic() < limite:
        time.sleep(0.01)
    d.parar.set()
    hilo.join(timeout=5.0)
    assert not hilo.is_alive(), "el bucle no se detuvo al poner parar"


def registros(tmp_path: Path) -> list:
    return ua.leer_anillo(str(tmp_path / "anillo.bin"))["registros"]


def muestras(tmp_path: Path) -> list:
    return [r for r in registros(tmp_path) if r["tipo"] == "muestra"]


# --- fdatasync lento ---------------------------------------------------------------------------------------------

def test_un_fsync_lento_se_anota_mientras_cuelga_y_el_muestreo_no_se_detiene(tmp_path):
    raiz = raiz_falsa(tmp_path / "raiz", zonas=1)
    d = demonio(tmp_path, raiz, plazo_fsync=0.2)
    ventana = {}

    def fsync_lento(fd):
        if ventana:  # solo el primero cuelga
            return
        ventana["inicio"], seq0 = time.time(), d.anillo.seq
        limite = time.monotonic() + 3.0
        # Cuelga hasta pasar el plazo Y hasta que el bucle haya escrito 20 registros mas. Si el bucle esperara al
        # fsync, eso nunca pasa y el fsync "termina" por el limite de 3 s: el assert de abajo lo caza.
        while time.monotonic() < limite and not (time.time() - ventana["inicio"] > 0.4 and d.anillo.seq - seq0 >= 20):
            time.sleep(0.005)
        ventana["fin"], ventana["por_limite"] = time.time(), time.monotonic() >= limite

    d.fsync = fsync_lento
    correr_mientras(d, lambda: "fin" in ventana and d.anillo.seq > 0 and d.fsync_info["lentos"] >= 1)
    assert ventana["por_limite"] is False, "el muestreo se detuvo mientras el fsync colgaba"
    durante = [m for m in muestras(tmp_path) if ventana["inicio"] < m["ts"] < ventana["fin"]]
    assert len(durante) >= 15
    eventos = [r for r in registros(tmp_path) if r.get("evento") == "fsync_lento"]
    en_curso = [e for e in eventos if e["en_curso"]]
    terminado = [e for e in eventos if not e["en_curso"]]
    assert len(en_curso) == 1 and en_curso[0]["lleva_s"] > 0.2  # anotado UNA vez mientras colgaba
    assert ventana["inicio"] < en_curso[0]["ts"] < ventana["fin"]
    assert len(terminado) == 1 and terminado[0]["duracion_s"] >= 0.4
    assert d.fsync_info["max_s"] >= 0.4


def test_control_un_fsync_rapido_no_anota_retraso(tmp_path):
    raiz = raiz_falsa(tmp_path / "raiz", zonas=1)
    llamadas = []
    d = demonio(tmp_path, raiz, plazo_fsync=0.2, fsync=lambda fd: llamadas.append(fd))
    correr_mientras(d, lambda: len(llamadas) >= 5)
    assert not [r for r in registros(tmp_path) if r.get("evento") == "fsync_lento"]
    assert d.fsync_info["lentos"] == 0 and len(llamadas) >= 5
    assert registros(tmp_path)[-1]["evento"] == "parada"  # el ultimo fdatasync se llevo el evento de parada


def test_un_fsync_que_falla_se_anota_y_el_muestreo_sigue(tmp_path):
    raiz = raiz_falsa(tmp_path / "raiz")

    def fsync_roto(fd):
        raise OSError(5, "Input/output error")

    d = demonio(tmp_path, raiz, fsync=fsync_roto)
    correr_mientras(d, lambda: d.fsync_info["errores"] >= 2 and d.anillo.seq > 10)
    assert [r for r in registros(tmp_path) if r.get("evento") == "fsync_error"]
    assert len(muestras(tmp_path)) > 5


# --- anillo de tamano fijo ---------------------------------------------------------------------------------------

def test_el_anillo_nunca_crece_tras_varias_vueltas_tamano_exacto(tmp_path):
    ruta = tmp_path / "anillo.bin"
    anillo = ua.Anillo(str(ruta))
    assert anillo.abrir() == ["anillo nuevo"]
    assert ruta.stat().st_size == ua.TAMANO_ANILLO == 4 * 1024 * 1024
    bloques = ruta.stat().st_blocks
    assert bloques * 512 >= ua.TAMANO_ANILLO  # preasignado de verdad, no un archivo disperso
    for i in range(3 * anillo.ranuras + 17):
        anillo.escribir({"tipo": "muestra", "i": i})
    assert ruta.stat().st_size == ua.TAMANO_ANILLO
    assert ruta.stat().st_blocks == bloques
    # Un registro que no cabe se recorta en su ranura: ni crece el archivo ni pisa la ranura vecina.
    enorme = {"tipo": "muestra", "temp_c": {"0": 93.1}, "hwmon": {f"hwmon0/power{i}_input": 10**9 for i in range(500)}}
    seq = anillo.escribir(enorme)
    assert ruta.stat().st_size == ua.TAMANO_ANILLO
    anillo.cerrar()
    leidos = ua.leer_anillo(str(ruta))
    assert leidos["ilegibles"] == 0 and len(leidos["registros"]) == anillo.ranuras
    ultimo = leidos["registros"][-1]
    assert ultimo["seq"] == seq and ultimo["recortado"] == ["hwmon"] and ultimo["temp_c"] == {"0": 93.1}


def test_serializar_da_siempre_la_longitud_exacta_de_la_ranura():
    for registro in ({"seq": 1}, {"seq": 2, "hwmon": {str(i): i for i in range(2000)}},
                     {"seq": 3, "tipo": "evento", "notas": ["x" * 5000]}):
        linea = ua.serializar(registro)
        assert len(linea) == ua.REGISTRO_BYTES and linea.endswith(b"\n")
        assert json.loads(linea)["seq"] == registro["seq"]
    assert json.loads(ua.serializar({"seq": 3, "notas": ["x" * 5000]}))["recortado"] == "todo"


def test_volcar_devuelve_las_muestras_en_orden_aunque_el_anillo_haya_dado_la_vuelta(tmp_path):
    ruta = str(tmp_path / "anillo.bin")
    anillo = ua.Anillo(ruta)
    anillo.abrir()
    total = anillo.ranuras + anillo.ranuras // 2
    for i in range(total):
        anillo.escribir({"tipo": "muestra", "ts": 1000.0 + i * 0.25, "i": i})
    anillo.cerrar()
    # Control: en disco NO estan en orden (la ranura 0 tiene un registro mas nuevo que la ultima).
    with open(ruta, "rb") as f:
        f.seek(ua.ENCABEZADO_BYTES)
        primera = json.loads(f.read(ua.REGISTRO_BYTES))
        f.seek(ua.TAMANO_ANILLO - ua.REGISTRO_BYTES)
        ultima_ranura = json.loads(f.read(ua.REGISTRO_BYTES))
    assert primera["seq"] > ultima_ranura["seq"]
    salida = io.StringIO()
    assert ua.volcar(ruta, salida) == 0
    lineas = [json.loads(linea) for linea in salida.getvalue().splitlines()]
    seqs = [r["seq"] for r in lineas]
    assert seqs == list(range(total - anillo.ranuras, total))
    assert [r["ts"] for r in lineas] == sorted(r["ts"] for r in lineas)
    # Un reinicio continua el cursor desde el mayor seq: el orden se conserva a traves de la vuelta y del reinicio.
    otro = ua.Anillo(ruta)
    otro.abrir()
    assert otro.seq == total
    otro.escribir({"tipo": "muestra", "i": "tras_reinicio"})
    otro.cerrar()
    salida = io.StringIO()
    ua.volcar(ruta, salida)
    lineas = [json.loads(linea) for linea in salida.getvalue().splitlines()]
    assert lineas[-1]["i"] == "tras_reinicio" and [r["seq"] for r in lineas] == sorted(r["seq"] for r in lineas)


def test_una_ranura_rota_por_un_corte_se_salta_y_se_cuenta(tmp_path):
    ruta = str(tmp_path / "anillo.bin")
    anillo = ua.Anillo(ruta)
    anillo.abrir()
    for i in range(10):
        anillo.escribir({"tipo": "muestra", "i": i})
    # Corte a media escritura en la frontera de un sector de 512 bytes: la mitad nueva de un registro largo sobre la
    # cola (relleno) de uno viejo corto. El JSON queda truncado: debe salir como ilegible, nunca como dato.
    nuevo = ua.serializar({"seq": 4 + anillo.ranuras, "tipo": "muestra", "hwmon": {str(i): i for i in range(80)}})
    os.pwrite(anillo.fd, nuevo[:512], ua.ENCABEZADO_BYTES + 4 * ua.REGISTRO_BYTES)
    anillo.cerrar()
    leidos = ua.leer_anillo(ruta)
    assert leidos["ilegibles"] == 1 and [r["seq"] for r in leidos["registros"]] == [0, 1, 2, 3, 5, 6, 7, 8, 9]


def test_una_sola_instancia_por_anillo(tmp_path):
    primero = ua.Anillo(str(tmp_path / "anillo.bin"))
    primero.abrir()
    with pytest.raises(ua.AnilloOcupado):
        ua.Anillo(str(tmp_path / "anillo.bin")).abrir()
    primero.cerrar()
    segundo = ua.Anillo(str(tmp_path / "anillo.bin"))  # control: liberado el flock, abre
    assert segundo.abrir() == []
    segundo.cerrar()


def test_un_archivo_con_otra_geometria_no_se_pisa_se_renombra(tmp_path):
    ruta = tmp_path / "anillo.bin"
    ruta.write_bytes(b"datos forenses de otra version\n")
    anillo = ua.Anillo(str(ruta))
    assert anillo.abrir() == [f"anillo invalido renombrado a {ruta}.previo", "anillo nuevo"]
    anillo.cerrar()
    assert (tmp_path / "anillo.bin.previo").read_bytes() == b"datos forenses de otra version\n"
    assert ruta.stat().st_size == ua.TAMANO_ANILLO


# --- estado_maquina.json -----------------------------------------------------------------------------------------

def _carrera_de_lecturas(ruta: Path, escribir, vueltas: int = 600, lectores: int = 3) -> tuple[int, int]:
    """Un escritor reescribe `ruta` `vueltas` veces mientras `lectores` hilos la leen y la parsean sin parar.
    Devuelve (lecturas, lecturas que no eran JSON valido)."""
    dato = {"formato": ua.FORMATO_ESTADO, "ts": 0.0, "relleno": ["x" * 64] * 300}  # ~20 KB: varias paginas
    escribir(str(ruta), dato)
    listo = threading.Event()
    cuenta = {"lecturas": 0, "rotas": 0}
    candado = threading.Lock()

    def leer():
        while not listo.is_set():
            try:
                with open(ruta, "rb") as f:
                    json.loads(f.read())
                rota = 0
            except ValueError:
                rota = 1
            with candado:
                cuenta["lecturas"] += 1
                cuenta["rotas"] += rota

    hilos = [threading.Thread(target=leer) for _ in range(lectores)]
    for h in hilos:
        h.start()
    for i in range(vueltas):
        dato["ts"] = float(i)
        escribir(str(ruta), dato)
    listo.set()
    for h in hilos:
        h.join()
    return cuenta["lecturas"], cuenta["rotas"]


def test_estado_maquina_siempre_es_json_valido_con_lecturas_concurrentes(tmp_path):
    lecturas, rotas = _carrera_de_lecturas(tmp_path / "estado_maquina.json", ua.escribir_estado)
    assert lecturas > 300 and rotas == 0
    assert not list(tmp_path.glob(".estado_maquina.json.*.tmp"))  # el temporal no queda tirado


def test_control_un_escritor_sin_rename_si_deja_lecturas_rotas(tmp_path):
    """El control negativo del arnes: escribir en el sitio (truncar y escribir) SI se lee a medias. Si este test
    dejara de ver lecturas rotas, el de arriba ya no probaria nada."""
    def en_el_sitio(ruta, dato):
        cuerpo = json.dumps(dato).encode()
        with open(ruta, "wb") as f:
            f.write(cuerpo[: len(cuerpo) // 2])
            f.flush()
            f.write(cuerpo[len(cuerpo) // 2:])

    _, rotas = _carrera_de_lecturas(tmp_path / "estado_maquina.json", en_el_sitio)
    assert rotas > 0


def test_el_demonio_publica_el_estado_con_sello_y_formato(tmp_path):
    raiz = raiz_falsa(tmp_path / "raiz", zonas=2, hwmon=True)
    d = demonio(tmp_path, raiz)
    ruta = str(tmp_path / "estado_maquina.json")
    correr_mientras(d, lambda: os.path.exists(ruta) and (ua.leer_estado(ruta)[0] or {}).get("ultima") is not None)
    dato, motivo = ua.leer_estado(ruta)
    assert dato is not None
    assert motivo is None and dato["formato"] == "bb-estado-maquina/1" and dato["boot"] == BOOT
    assert dato["ultima"]["tipo"] == "muestra" and dato["ultima"]["temp_c"] == {"0": 93.0, "1": 93.5}
    assert dato["zonas"]["0"]["trips"][0] == {"n": 0, "temp_c": 104.8, "tipo": "critical"}
    assert dato["hwmon_nombres"] == {"hwmon0": "pmic_falso"}
    assert dato["mlock"] == "omitido: prueba"


def test_leer_estado_rechaza_un_sello_viejo_o_del_futuro(tmp_path):
    ruta = str(tmp_path / "estado_maquina.json")
    ua.escribir_estado(ruta, {"formato": ua.FORMATO_ESTADO, "ts": 1000.0})
    assert ua.leer_estado(ruta, ahora=1002.0)[1] is None
    assert (ua.leer_estado(ruta, ahora=1006.0)[1] or "").startswith("sello viejo")  # control: 6 s > 5 s
    assert (ua.leer_estado(ruta, ahora=990.0)[1] or "").startswith("sello en el futuro")
    ua.escribir_estado(ruta, {"formato": "otro/1", "ts": 1000.0})
    assert ua.leer_estado(ruta, ahora=1000.0) == (None, "formato distinto de bb-estado-maquina/1")
    assert ua.leer_estado(str(tmp_path / "no_existe.json"))[0] is None


def test_estado_cli_da_rc_1_si_el_demonio_no_corre(tmp_path, capsys):
    ruta = str(tmp_path / "estado_maquina.json")
    ua.escribir_estado(ruta, {"formato": ua.FORMATO_ESTADO, "ts": time.time() - 60})
    assert ua.main(["--estado", "--estado-ruta", ruta, "--anillo", str(tmp_path / "no_hay.bin")]) == 1
    informe = json.loads(capsys.readouterr().out)
    assert informe["fresco"] is False and informe["motivo"].startswith("sello viejo") and "error" in informe["anillo"]
    ua.escribir_estado(ruta, {"formato": ua.FORMATO_ESTADO, "ts": time.time()})
    assert ua.main(["--estado", "--estado-ruta", ruta, "--anillo", str(tmp_path / "no_hay.bin")]) == 0



# --- raiz falsa: fuentes presentes y ausentes --------------------------------------------------------------------

def test_sin_zonas_termicas_sigue_muestreando_y_declara_la_fuente_ausente(tmp_path):
    raiz = raiz_falsa(tmp_path / "raiz")  # thermal/ y hwmon/ existen pero vacios, como en este contenedor
    d = demonio(tmp_path, raiz)
    correr_mientras(d, lambda: len(muestras(tmp_path)) >= 5)
    ultimas = muestras(tmp_path)
    assert len(ultimas) >= 5
    for m in ultimas:
        assert "temp_c" not in m and m["ausente"]["termica"].startswith("sin thermal_zone*")
        assert m["ausente"]["hwmon"].startswith("sin power/in/curr*_input")
        assert m["psi"]["memory"]["some"] == [1.5, 0.75, 0.1, 123456]
        assert m["mem_kb"]["MemAvailable"] == 60115000 and m["loadavg"] == [3.1, 2.05, 1.0]
    inventario = [r for r in registros(tmp_path) if r["tipo"] == "inventario"]
    assert inventario and inventario[0]["ausente"]["termica"].startswith("sin thermal_zone*")


def test_control_con_zonas_y_hwmon_lee_temperaturas_trips_y_potencia(tmp_path):
    raiz = raiz_falsa(tmp_path / "raiz", zonas=7, hwmon=True)  # 7 zonas, como la GB10
    inventario = ua.descubrir(raiz)
    muestra = ua.muestrear(raiz, inventario)
    assert "ausente" not in muestra
    assert muestra["temp_c"] == {str(n): 93.0 + n * 0.5 for n in range(7)}
    assert muestra["hwmon"] == {"hwmon0/power1_input": 82400000, "hwmon0/device/power2_input": 1500000,
                                "hwmon0/in0_input": 19500, "hwmon0/curr1_input": 4200}  # temp1_input no entra
    assert [t["tipo"] for t in inventario["zonas"]["0"]["trips"]] == ["critical", "hot", "passive"]
    zona0 = tmp_path / "raiz/sys/class/thermal/thermal_zone0"
    (zona0 / "trip_point_10_temp").write_text("50000\n")
    (zona0 / "trip_point_10_type").write_text("active\n")
    assert [t["n"] for t in ua.descubrir(raiz)["zonas"]["0"]["trips"]] == [0, 1, 2, 10]  # numerico, no 0,1,10,2
    # Una muestra real de la GB10 cabe entera en su ranura (sin recortes).
    linea = ua.serializar({"seq": 10**6, "ts": time.time(), "boot": BOOT, "tipo": "muestra", **muestra})
    assert "recortado" not in json.loads(linea)
    # Cada zona va en su propio registro de inventario y cabe sin recortes.
    for registro in ua.registros_inventario(inventario):
        assert "recortado" not in json.loads(ua.serializar({"seq": 1, "ts": 1.0, "boot": BOOT, **registro}))
    (tmp_path / "raiz/sys/class/thermal/thermal_zone3/temp").write_text("garbage\n")
    rota = ua.muestrear(raiz, inventario)
    assert rota["temp_c"]["3"] is None and rota["ausente"]["tz3"].startswith("ValueError")


def test_sin_psi_ni_meminfo_la_muestra_lo_declara_y_no_lanza(tmp_path):
    raiz = raiz_falsa(tmp_path / "raiz", zonas=1, psi=False)
    (tmp_path / "raiz/proc/meminfo").write_text("MemTotal: 1 kB\n")
    muestra = ua.muestrear(raiz, ua.descubrir(raiz))
    assert set(muestra["ausente"]) == {"psi_cpu", "psi_memory", "psi_io", "meminfo", "hwmon"}
    assert muestra["ausente"]["meminfo"].startswith("ValueError: faltan MemAvailable")
    assert muestra["temp_c"] == {"0": 93.0} and muestra["loadavg"] == [3.1, 2.05, 1.0]


def test_el_inventario_se_refresca_y_ve_una_zona_que_aparece(tmp_path):
    raiz = raiz_falsa(tmp_path / "raiz", zonas=1)
    d = demonio(tmp_path, raiz, inventario_cada=0.05)
    hilo = threading.Thread(target=d.correr, daemon=True)
    hilo.start()
    time.sleep(0.1)
    nueva = tmp_path / "raiz/sys/class/thermal/thermal_zone1"
    nueva.mkdir()
    (nueva / "type").write_text("nueva\n")
    (nueva / "temp").write_text("70000\n")
    limite = time.monotonic() + 3.0
    while time.monotonic() < limite and not [m for m in muestras(tmp_path) if "1" in m.get("temp_c", {})]:
        time.sleep(0.02)
    d.parar.set()
    hilo.join(timeout=5.0)
    assert [m for m in muestras(tmp_path) if m.get("temp_c", {}).get("1") == 70.0]


# --- mlockall, UDP, unidad y prohibiciones -----------------------------------------------------------------------

def test_mlockall_se_omite_sin_root_y_un_fallo_se_anota_sin_lanzar():
    class LibcQueFalla:
        def mlockall(self, flags):
            assert flags == ua.MCL_CURRENT | ua.MCL_FUTURE
            return -1

    class LibcQueFunciona:
        def mlockall(self, flags):
            return 0

    assert ua.bloquear_memoria(euid=1000) == "omitido: no es root"
    assert ua.bloquear_memoria(euid=0, libc=LibcQueFalla()).startswith("fallo: errno")
    assert ua.bloquear_memoria(euid=0, libc=LibcQueFunciona()) == "ok"


def test_udp_envia_cada_muestra_comprimida_al_testigo(tmp_path):
    receptor = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receptor.bind(("127.0.0.1", 0))
    receptor.settimeout(3.0)
    raiz = raiz_falsa(tmp_path / "raiz", zonas=7, hwmon=True)
    d = demonio(tmp_path, raiz, udp=f"127.0.0.1:{receptor.getsockname()[1]}")
    correr_mientras(d, lambda: d.udp["enviados"] >= 3)
    datagrama = receptor.recv(65535)
    receptor.close()
    assert len(datagrama) <= ua.UDP_DATAGRAM_MAX_BYTES
    dato = json.loads(zlib.decompress(datagrama))
    assert dato["evento"] == "ultimo_aliento" and dato["boot_id"] == BOOT and isinstance(dato["seq"], int)
    assert dato["mem_avail_mb"] == 60115000 // 1024 and dato["psi_mem_some_avg10"] == 1.5
    assert dato["zonas"][0] == {"zona": "thermal_zone0", "temp_c": 93.0} and len(dato["zonas"]) == 7
    assert d.udp["errores"] == 0


def test_control_un_destino_udp_invalido_no_frena_el_muestreo(tmp_path):
    raiz = raiz_falsa(tmp_path / "raiz")
    d = demonio(tmp_path, raiz, udp="testigo.lan:5140")  # nombre, no IP literal: se rechaza (sin DNS)
    correr_mientras(d, lambda: len(muestras(tmp_path)) >= 3)
    assert d.udp["ultimo_error"].startswith("destino invalido") and d.udp["enviados"] == 0
    assert len(muestras(tmp_path)) >= 3


def test_la_unidad_declara_los_topes_y_la_prioridad():
    unidad = configparser.ConfigParser(strict=False, interpolation=None)
    setattr(unidad, "optionxform", str)
    unidad.read(ROOT / "systemd/bb-ultimo-aliento.service", encoding="utf-8")
    servicio = unidad["Service"]
    assert servicio["OOMScoreAdjust"] == "-1000" and servicio["Restart"] == "always"
    assert servicio["MemoryMin"] and servicio["MemoryMax"] and servicio["CPUQuota"].endswith("%")
    assert int(servicio["Nice"]) != 0
    assert servicio["ExecStart"] == "/usr/bin/python3 -I /usr/local/lib/blackbox/ultimo_aliento.py"
    assert unidad["Install"]["WantedBy"] == "multi-user.target"


def test_el_demonio_no_lanza_subprocesos_ni_nombra_nvidia_smi():
    fuente = (ROOT / "tools/ultimo_aliento.py").read_text(encoding="utf-8")
    arbol = ast.parse(fuente)
    importados = {a.name.split(".")[0] for n in ast.walk(arbol) if isinstance(n, ast.Import) for a in n.names}
    importados |= {n.module.split(".")[0] for n in ast.walk(arbol) if isinstance(n, ast.ImportFrom) and n.module}
    assert not importados & {"subprocess", "multiprocessing", "pty"}
    assert fuente.count("nvidia-smi") == (ast.get_docstring(arbol) or "").count("nvidia-smi")  # solo la prohibicion escrita
    assert "os.system" not in fuente and "os.popen" not in fuente and "os.exec" not in fuente
    # Solo biblioteca estandar: el demonio root no arrastra dependencias del repo.
    assert not [m for m in importados if m == "tools"]


def test_un_mlockall_que_falla_se_anota_en_el_arranque_y_el_muestreo_sigue(tmp_path):
    raiz = raiz_falsa(tmp_path / "raiz")
    d = demonio(tmp_path, raiz, bloquear=lambda: "fallo: errno 12 (Cannot allocate memory)")
    correr_mientras(d, lambda: len(muestras(tmp_path)) >= 3)
    arranque = registros(tmp_path)[0]
    assert arranque["evento"] == "arranque" and arranque["mlock"].startswith("fallo: errno 12")
    assert len(muestras(tmp_path)) >= 3


def test_extremo_a_extremo_el_cli_muestrea_para_con_sigterm_y_vuelca(tmp_path):
    """El proceso real: main(), mlockall de verdad (o su omision sin root), SIGTERM y `--volcar` por CLI."""
    import signal
    import subprocess
    import sys

    raiz = raiz_falsa(tmp_path / "raiz", zonas=2)
    rutas = ["--anillo", str(tmp_path / "anillo.bin"), "--estado-ruta", str(tmp_path / "run/estado_maquina.json")]
    proceso = subprocess.Popen([sys.executable, "-I", str(ROOT / "tools/ultimo_aliento.py"), "--raiz", raiz,
                                "--intervalo", "0.05", *rutas], stderr=subprocess.PIPE, text=True)
    limite = time.monotonic() + 5.0
    while time.monotonic() < limite and not (tmp_path / "run/estado_maquina.json").exists():
        time.sleep(0.05)
    time.sleep(0.5)
    proceso.send_signal(signal.SIGTERM)
    assert proceso.wait(timeout=5) == 0
    assert proceso.stderr is not None
    proceso.stderr.close()
    volcado = subprocess.run([sys.executable, "-I", str(ROOT / "tools/ultimo_aliento.py"), "--volcar", *rutas],
                             capture_output=True, text=True, timeout=30)
    assert volcado.returncode == 0
    lineas = [json.loads(linea) for linea in volcado.stdout.splitlines()]
    assert lineas[0]["evento"] == "arranque" and lineas[-1]["evento"] == "parada"
    esperado = "ok" if os.geteuid() == 0 else "omitido: no es root"
    assert lineas[0]["mlock"] == esperado or lineas[0]["mlock"].startswith("fallo:")
    assert len([r for r in lineas if r["tipo"] == "muestra"]) >= 5
    assert "registros de 4092 ranuras; 0 ilegibles" in volcado.stderr
