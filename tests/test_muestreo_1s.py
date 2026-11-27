"""Pruebas de tools/muestreo_1s.py: formato de linea, fsync por segundo y rotacion por arranque."""
import builtins
import importlib.util
import json
import os
import pathlib
import threading

RAIZ = pathlib.Path(__file__).resolve().parent.parent
# ponytail: la variable solo existe para correr el control negativo contra una copia sin fsync, techo = esta prueba; disparador = otra prueba que necesite sustituir el modulo
MODULO = pathlib.Path(os.environ.get("MUESTREO_1S_PATH", RAIZ / "tools" / "muestreo_1s.py"))

spec = importlib.util.spec_from_file_location("muestreo_1s", MODULO)
assert spec is not None and spec.loader is not None
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

CLAVES = ["ts", "cpu_pct", "load1", "top", "freq_khz_cpu0", "temp_mc", "gpu", "psi_cpu", "psi_mem", "gpu_calidad"]


def muestra():
    pp = {1: ("a", 10), 2: ("b", 10), 3: ("c", 10), 4: ("d", 10)}
    cp = {1: ("a", 110), 2: ("b", 50), 3: ("c", 40), 4: ("d", 11)}
    return m.registro(1.5, 200, 90, 100, 50, cp, pp, "1, 2", 100)


def test_formato_de_linea():
    rec = muestra()
    assert list(rec) == CLAVES
    assert rec["cpu_pct"] == 60.0  # dt=100, ocioso 40 -> 60 %
    assert [t["pid"] for t in rec["top"]] == [1, 2, 3]  # top 3 por delta de CPU
    assert rec["top"][0] == {"pid": 1, "cmd": "a", "cpu_pct_de_un_nucleo": 100.0}
    assert rec["gpu"] == "1, 2"


def test_linea_con_datos_vivos():
    r = m.registro(1.0, 2, 1, 1, 1, m.procs(), {}, None, 100)
    assert list(r) == CLAVES
    assert json.loads(json.dumps(r)) == r


def test_calidad_distingue_entrega_de_contenido():
    calidad = m.CalidadGPU(reloj=lambda: 0.0)
    assert calidad.observar("x", estado="reciente") == {"estado": "reciente", "edad_entrega_s": 0.0, "edad_contenido_s": 0.0, "entregas_racha": 1, "comparacion": "inicio"}
    calidad.reloj = lambda: 5.0
    assert calidad.observar("x", estado="reciente")["edad_entrega_s"] == 0.0
    assert calidad.observar("x", estado="reciente")["edad_contenido_s"] == 5.0
    assert calidad.observar(None, estado="eof")["estado"] == "eof"
    calidad.reloj = lambda: 6.0
    parcial = calidad.observar(None, estado="no_comparable", entrega=True)
    assert parcial["edad_entrega_s"] == 0.0 and parcial["edad_contenido_s"] == 6.0


def test_reloj_invalido_no_reancla_aunque_haya_entrega():
    reloj = [3.0]
    calidad = m.CalidadGPU(lambda: reloj[0])
    calidad.observar("x")
    reloj[0] = 2.0
    invalida = calidad.observar("y", entrega=True)
    assert invalida["estado"] == "reloj_invalido"
    assert invalida["edad_entrega_s"] is None
    assert invalida["edad_contenido_s"] is None
    reloj[0] = float("nan")
    invalida = calidad.observar("z", entrega=True)
    assert invalida["estado"] == "reloj_invalido"
    assert invalida["edad_entrega_s"] is None


def test_fsync_por_linea(tmp_path, monkeypatch):
    llamadas = []
    lecturas = []
    globulos = []
    abrir = builtins.open
    def abrir_guardado(ruta, *args, **kwargs):
        ruta = str(ruta)
        if ruta.startswith(("/proc/", "/sys/")):
            raise AssertionError(f"lectura viva bloqueada: {ruta}")
        return abrir(ruta, *args, **kwargs)
    def rd_sintetico(ruta):
        lecturas.append(ruta)
        return "0.1 0 0" if ruta == "/proc/loadavg" else "1200000"
    def glob_sintetico(patron):
        globulos.append(patron)
        return []
    monkeypatch.setattr(builtins, "open", abrir_guardado)
    monkeypatch.setattr(m, "rd", rd_sintetico)
    monkeypatch.setattr(m.glob, "glob", glob_sintetico)
    monkeypatch.setattr(m.os, "fsync", lambda fd: llamadas.append(fd))
    try:
        open("/proc/close-check-guard", "r")
    except AssertionError as exc:
        assert "lectura viva bloqueada" in str(exc)
    else:
        raise AssertionError("la guarda permitió abrir /proc")
    with open(tmp_path / "s.jsonl", "a", buffering=1) as f:
        for _ in range(3):
            m.escribir(f, muestra())
        assert llamadas == [f.fileno()] * 3
    rutas_lectura = ["/proc/loadavg", "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq",
                     "/proc/pressure/cpu", "/proc/pressure/memory"]
    assert lecturas == rutas_lectura * 3
    assert globulos == ["/sys/class/thermal/thermal_zone*/temp"] * 3


def test_linea_visible_sin_cerrar(tmp_path):
    with open(tmp_path / "s.jsonl", "a", buffering=1) as f:
        m.escribir(f, muestra())
        lineas = (tmp_path / "s.jsonl").read_text().splitlines()
    assert len(lineas) == 1 and list(json.loads(lineas[0])) == CLAVES


def test_rotacion_un_archivo_por_arranque(tmp_path):
    a = m.ruta_salida("7cd0848b-aaaa-bbbb", str(tmp_path))
    b = m.ruta_salida("11111111-aaaa-bbbb", str(tmp_path))
    assert a != b
    assert os.path.basename(a) == "muestreo-7cd0848b.jsonl"
    assert os.path.dirname(a) == str(tmp_path)
    assert m.ruta_salida("7cd0848b-zzzz", str(tmp_path)) == a


def _main_sintetico(monkeypatch, tmp_path, lecturas, ticks, *, stdout=None,
                    dormir=None, set_blocking=None):
    calidad_gpu = m.CalidadGPU
    reloj = [0.0]
    monkeypatch.setattr(m, "CalidadGPU", lambda: calidad_gpu(reloj=lambda: reloj[0]))

    class Pipe:
        def __init__(self):
            self.ticks = iter(lecturas)
            self.lecturas = iter(())
            self.cargar_tick = True
        def fileno(self): return 10
        def readline(self):
            if self.cargar_tick:
                try: self.lecturas = iter(next(self.ticks))
                except StopIteration: return ""
                self.cargar_tick = False
            try:
                return next(self.lecturas)
            except StopIteration:
                self.cargar_tick = True
                return ""
    class Proceso:
        def __init__(self): self.stdout = stdout or Pipe()
        def poll(self): return None
    monkeypatch.setattr(m.subprocess, "Popen", lambda *a, **k: Proceso())
    monkeypatch.setattr(m.os, "set_blocking", set_blocking or (lambda *a: None))
    def dormir_tick(*args):
        if threading.current_thread() is not threading.main_thread():
            threading.Event().wait()
        reloj[0] += 1.0
        if dormir is not None:
            dormir(*args)
    monkeypatch.setattr(m.time, "sleep", dormir_tick)
    monkeypatch.setattr(m, "stat", lambda: (100, 20))
    monkeypatch.setattr(m, "procs", lambda: {})
    monkeypatch.setattr(m.glob, "glob", lambda *_: [])
    monkeypatch.setattr(m.os, "sysconf", lambda *_: 100)
    monkeypatch.setattr(m, "rd", lambda p: "11111111-aaaa" if "boot_id" in p else "0.1 0 0")
    monkeypatch.setattr(m, "ruta_salida", lambda *_: str(tmp_path / "out.jsonl"))
    m.main(max_iteraciones=ticks)
    return [json.loads(x) for x in (tmp_path / "out.jsonl").read_text().splitlines()]


def test_main_dos_filas_acumuladas_mismo_indice_actualiza_ultima_legacy(tmp_path, monkeypatch):
    filas = _main_sintetico(monkeypatch, tmp_path,
        [["0, 1, 2, 3, 4, 5\n", "0, 6, 7, 8, 9, 10\n"]], 1)
    assert filas[0]["gpu"] == "6, 7, 8, 9, 10"
    assert filas[0]["gpu_calidad"]["estado"] == "reciente"


def test_main_no_mezcla_dos_identidades_y_conserva_fragmento(tmp_path, monkeypatch):
    filas = _main_sintetico(monkeypatch, tmp_path,
        [["0, 1, 2, 3, 4, 5\n", "1, 6, 7, 8, 9, 10\n"]], 1)
    assert filas[0]["gpu"] is None
    assert filas[0]["gpu_calidad"]["estado"] == "ambiguo"


def test_main_recompone_fila_fragmentada_entre_ticks(tmp_path, monkeypatch):
    filas = _main_sintetico(monkeypatch, tmp_path,
        [["0, 1, 2"], [", 3, 4, 5\n"]], 2)
    assert filas[0]["gpu"] is None
    assert filas[0]["gpu_calidad"]["estado"] == "parcial"
    assert filas[1]["gpu"] == "1, 2, 3, 4, 5"
    assert filas[1]["gpu_calidad"]["estado"] == "reciente"
    assert filas[1]["gpu_calidad"]["edad_entrega_s"] == 0.0
    assert filas[1]["gpu_calidad"]["edad_contenido_s"] == 0.0


def test_main_n_a_en_memoria_opcional_conserva_comparacion(tmp_path, monkeypatch):
    filas = _main_sintetico(monkeypatch, tmp_path,
        [["0, 1, 2, 3, 4, [N/A]\n"], ["0, 1, 2, 3, 4, [N/A]\n"]], 2)
    assert filas[0]["gpu"] == "1, 2, 3, 4, [N/A]"
    assert filas[1]["gpu_calidad"]["estado"] == "reciente"
    assert filas[1]["gpu_calidad"]["comparacion"] == "igual"
    assert filas[0]["gpu_calidad"]["edad_entrega_s"] == 0.0
    assert filas[1]["gpu_calidad"]["edad_entrega_s"] == 0.0
    assert filas[1]["gpu_calidad"]["edad_contenido_s"] == 1.0


def test_main_n_a_en_metrica_requerida_es_no_comparable(tmp_path, monkeypatch):
    filas = _main_sintetico(monkeypatch, tmp_path,
        [["0, [N/A], 2, 3, 4, 5\n"]], 1)
    assert filas[0]["gpu_calidad"]["estado"] == "no_comparable"
    assert filas[0]["gpu_calidad"]["edad_entrega_s"] == 0.0
    assert filas[0]["gpu_calidad"]["edad_contenido_s"] is None


def test_main_entrega_igual_refresca_solo_edad_de_entrega(tmp_path, monkeypatch):
    filas = _main_sintetico(monkeypatch, tmp_path,
        [["0, 1, 2, 3, 4, 5\n"], ["0, 1, 2, 3, 4, 5\n"], []], 3)
    assert filas[1]["gpu_calidad"]["comparacion"] == "igual"
    assert filas[1]["gpu_calidad"]["edad_entrega_s"] == 0.0
    assert filas[1]["gpu_calidad"]["edad_contenido_s"] == 1.0
    assert filas[2]["gpu_calidad"]["estado"] == "ausencia"
    assert filas[2]["gpu_calidad"]["edad_entrega_s"] == 1.0
    assert filas[2]["gpu_calidad"]["edad_contenido_s"] == 2.0


def test_main_cambio_de_identidad_cuenta_como_cambio_de_contenido(tmp_path, monkeypatch):
    filas = _main_sintetico(monkeypatch, tmp_path,
        [["0, 1, 2, 3, 4, 5\n"], ["1, 1, 2, 3, 4, 5\n"]], 2)
    assert filas[1]["gpu"] == "1, 2, 3, 4, 5"
    assert filas[1]["gpu_calidad"]["comparacion"] == "cambio"
    assert filas[1]["gpu_calidad"]["edad_contenido_s"] == 0.0
    assert filas[1]["gpu_calidad"]["edad_entrega_s"] == 0.0


def test_main_recompone_con_pipe_os_real(tmp_path, monkeypatch):
    read_fd, write_fd = os.pipe()
    stdout = os.fdopen(read_fd, "r", buffering=1)
    original_set_blocking = os.set_blocking
    tick = [0]
    def dormir(_):
        tick[0] += 1
        if tick[0] == 1:
            os.write(write_fd, b"0, 1, 2")
        else:
            os.write(write_fd, b", 3, 4, 5\n")
            os.close(write_fd)
    try:
        filas = _main_sintetico(monkeypatch, tmp_path, [], 2, stdout=stdout,
                                dormir=dormir,
                                set_blocking=lambda fd, value: original_set_blocking(fd, value))
    finally:
        stdout.close()
        try: os.close(write_fd)
        except OSError: pass
    assert filas[0]["gpu_calidad"]["estado"] == "parcial"
    assert filas[1]["gpu"] == "1, 2, 3, 4, 5"
    assert filas[1]["gpu_calidad"]["estado"] == "reciente"
    assert filas[1]["gpu_calidad"]["edad_entrega_s"] == 0.0
    assert filas[1]["gpu_calidad"]["edad_contenido_s"] == 0.0


def test_main_pipe_cambio_intermedio_aba_marca_cambio_y_preserva_ultima(tmp_path, monkeypatch):
    read_fd, write_fd = os.pipe()
    stdout = os.fdopen(read_fd, "r", buffering=1)
    original_set_blocking = os.set_blocking
    tick = [0]
    def dormir(_):
        tick[0] += 1
        if tick[0] == 1:
            os.write(write_fd, b"0, 1, 2, 3, 4, 5\n")
        else:
            os.write(write_fd, b"0, 6, 7, 8, 9, 10\n0, 1, 2, 3, 4, 5\n")
            os.close(write_fd)
    try:
        filas = _main_sintetico(monkeypatch, tmp_path, [], 2, stdout=stdout,
                                dormir=dormir,
                                set_blocking=lambda fd, value: original_set_blocking(fd, value))
    finally:
        stdout.close()
        try: os.close(write_fd)
        except OSError: pass
    assert filas[1]["gpu"] == "1, 2, 3, 4, 5"
    assert filas[1]["gpu_calidad"]["comparacion"] == "cambio"
    assert filas[1]["gpu_calidad"]["edad_contenido_s"] == 0.0
    assert filas[1]["gpu_calidad"]["edad_entrega_s"] == 0.0
    assert filas[1]["gpu_calidad"]["entregas_racha"] == 1
