#!/usr/bin/env python3
"""Ultimo aliento: muestreo de 250 ms con fdatasync cada segundo, para que un corte duro deje escritos sus ultimos
segundos (DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01).

Por que existe: los cortes de la ATOM no dejan rastro de sus ultimos segundos. `blackbox-sample` corre cada minuto y
no hace fsync; la telemetria GPU muestrea cada 5 s; antes de los cortes la zona mas caliente marcaba 93.0-96.3 C y no
habia registro del trip point. Este demonio de sistema lee cada 250 ms, solo de archivos y sin subprocesos (NUNCA
`nvidia-smi`: se cuelga, y ya lo cubre `tools/atom_gpu_telemetry.py`):

  /proc/pressure/{cpu,memory,io}                 some/full: [avg10, avg60, avg300, total]
  /proc/meminfo                                  MemAvailable, MemFree, SwapTotal, SwapFree, Dirty (kB)
  /sys/class/thermal/thermal_zone*/temp          C; tipo y trip points (`trip_point_*_temp` y `_type`) al inicio y
                                                 cada minuto, en un registro `inventario`
  /sys/class/hwmon/hwmon*/{power,in,curr}*_input crudo segun la ABI de sysfs: uW, mV y mA
  /proc/loadavg                                  [1 min, 5 min, 15 min]

Toda fuente que no se puede leer se declara en `ausente` de la muestra; ninguna se omite en silencio.

Formatos:

  Anillo (`/var/lib/bb-ultimo-aliento/anillo.bin`, esquema `bb-ultimo-aliento-anillo/1`): archivo de EXACTAMENTE
  4 MiB, preasignado con posix_fallocate, que nunca crece. Los primeros 4096 bytes son un encabezado JSON relleno de
  espacios (formato, tamano, encabezado, registro, ranuras, creado). Siguen 4092 ranuras de 1024 bytes: una linea JSON
  rellena de espacios y terminada en `\\n`, o ceros si nunca se uso. El cursor es `seq`, entero global que cada
  registro lleva dentro: la ranura es `seq % ranuras`, y al arrancar se continua desde el mayor `seq` presente, asi que
  no hay un cursor en el encabezado que se pueda desincronizar con un corte. 4092 ranuras a 4 muestras/s son ~17 min:
  el veredicto de reinicio corre a los 3 min del arranque y todavia encuentra ~14 min del boot anterior. Tipos de
  registro: `muestra`, `inventario` (zonas, tipos, trips y nombres de hwmon) y `evento` (arranque, mlockall,
  fsync_lento, parada). Un registro que no cabe pierde primero `hwmon`, luego `temp_c`, y lo declara en `recortado`.

  Volcado (`--volcar`): JSONL en stdout, un registro por linea en orden de `seq` (orden de escritura) aunque el anillo
  haya dado la vuelta; cada linea lleva `boot` (boot_id sin guiones) para separar el boot anterior. Un registro roto
  por un corte a media escritura se salta y se cuenta en stderr.

  `estado_maquina.json` (`/run/bb-ultimo-aliento/`, esquema `bb-estado-maquina/1`): la ultima lectura, el inventario,
  el estado del fsync y del mlockall, con `ts` (epoch) y `ts_iso`. Se reescribe cada segundo a un temporal y `rename`:
  quien lo lee ve el archivo viejo o el nuevo, nunca uno a medias. Es la fuente de "hechos por archivo" (voto de Luis
  #18): el consumidor lee el archivo y valida la frescura del sello (`leer_estado`, `--estado`); un sello viejo es un
  demonio muerto, no una maquina tranquila. Vive en /run porque describe ESTE boot.

  UDP (opcional, `--udp IP:PUERTO` o `BB_ULTIMO_ALIENTO_UDP`): cada muestra comprimida con zlib, con las claves de
  `_udp_payload` de `tools/atom_gpu_telemetry.py` (ts, evento, boot_id, mem_free_mb, mem_avail_mb, psi_mem_*, zonas
  [{zona, temp_c}] hasta 8) mas psi_cpu_*, psi_io_*, swap_free_mb, dirty_mb, loadavg_1 y seq. No se importa ese modulo:
  el demonio solo usa la biblioteca estandar. Tope de 1200 bytes por datagrama, IP literal (sin DNS), socket no
  bloqueante; un envio que falla se cuenta en el estado y no frena el muestreo.

Durabilidad: el bucle escribe con pwrite (cache de paginas) y NUNCA espera al disco. Un hilo propio hace fdatasync cada
segundo; si uno lleva mas de 2 s, el bucle lo anota en el anillo mientras sigue colgado (`en_curso`) y otra vez al
terminar (`duracion_s`), y sigue muestreando. Siendo root se llama a mlockall(MCL_CURRENT|MCL_FUTURE) para que el
demonio no espere a que le devuelvan paginas en el peor momento; si falla, se anota y sigue. Una sola instancia por
anillo (flock). LIMITE DECLARADO: el pwrite a la cache puede bloquear si el kernel estrangula a los escritores sucios;
eso se veria como un hueco en los `ts`, no como un error.

Instalacion (con sudo de Luis; nada se activa solo). El script se COPIA a /usr/local/lib: un demonio root no debe
ejecutar codigo de un directorio que un usuario puede escribir.

  sudo install -D -m 0644 tools/ultimo_aliento.py /usr/local/lib/blackbox/ultimo_aliento.py
  sudo install -m 0644 systemd/bb-ultimo-aliento.service /etc/systemd/system/bb-ultimo-aliento.service
  sudo systemd-analyze verify /etc/systemd/system/bb-ultimo-aliento.service
  sudo systemctl daemon-reload
  sudo systemctl enable --now bb-ultimo-aliento.service
  python3 tools/ultimo_aliento.py --estado          # rc=0 si el sello tiene menos de 5 s
  python3 tools/ultimo_aliento.py --volcar > /tmp/ultimo_aliento.jsonl

Testigo UDP: `sudo systemctl edit bb-ultimo-aliento.service` y anadir `[Service]` +
`Environment=BB_ULTIMO_ALIENTO_UDP=<ip-del-testigo>:<puerto>`. Actualizar: repetir el primer `install` y
`sudo systemctl restart bb-ultimo-aliento.service`. Retirar: `sudo systemctl disable --now bb-ultimo-aliento.service`,
`sudo rm -f /etc/systemd/system/bb-ultimo-aliento.service /usr/local/lib/blackbox/ultimo_aliento.py` y
`sudo systemctl daemon-reload` (el anillo queda en /var/lib/bb-ultimo-aliento hasta borrarlo a mano).
"""

from __future__ import annotations

import argparse
import collections
import ctypes
import fcntl
import glob
import ipaddress
import json
import os
import signal
import socket
import sys
import threading
import time
import zlib
from datetime import datetime, timezone

FORMATO_ANILLO = "bb-ultimo-aliento-anillo/1"
FORMATO_ESTADO = "bb-estado-maquina/1"
TAMANO_ANILLO = 4 * 1024 * 1024
ENCABEZADO_BYTES = 4096
REGISTRO_BYTES = 1024
INTERVALO_S = 0.25
SYNC_CADA_S = 1.0
FSYNC_PLAZO_S = 2.0
INVENTARIO_CADA_S = 60.0
ESTADO_CADA_S = 1.0
ESTADO_MAX_EDAD_S = 5.0  # cinco veces la cadencia del snapshot: mas viejo que esto es un demonio muerto
UDP_DATAGRAM_MAX_BYTES = 1200  # el mismo tope que tools/atom_gpu_telemetry.py
MENSAJE_MAX = 96

ANILLO_RUTA = os.environ.get("BB_ULTIMO_ALIENTO_ANILLO", "/var/lib/bb-ultimo-aliento/anillo.bin")
ESTADO_RUTA = os.environ.get("BB_ULTIMO_ALIENTO_ESTADO", "/run/bb-ultimo-aliento/estado_maquina.json")
MEMINFO_CLAVES = ("MemAvailable", "MemFree", "SwapTotal", "SwapFree", "Dirty")
PSI_RECURSOS = ("cpu", "memory", "io")
HWMON_PATRONES = ("power*_input", "in*_input", "curr*_input")
MCL_CURRENT, MCL_FUTURE = 1, 2


def _log(mensaje: str) -> None:
    print(f"ultimo_aliento: {mensaje}", file=sys.stderr, flush=True)


def _corto(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"[:MENSAJE_MAX]


def _leer(ruta: str) -> str:
    """Lectura barata: os.open/os.read/os.close, sin objetos de archivo ni subprocesos."""
    fd = os.open(ruta, os.O_RDONLY)
    try:
        return os.read(fd, 65536).decode("ascii", "replace")
    finally:
        os.close(fd)


def _en(raiz: str, relativa: str) -> str:
    return os.path.join(raiz, relativa)


def leer_psi(raiz: str, recurso: str) -> dict:
    """`some avg10=0.34 avg60=0.22 avg300=0.13 total=15094739` -> {"some": [0.34, 0.22, 0.13, 15094739]}."""
    resultado = {}
    for linea in _leer(_en(raiz, f"proc/pressure/{recurso}")).splitlines():
        partes = linea.split()
        if not partes or partes[0] not in ("some", "full"):
            continue
        campos = dict(p.split("=", 1) for p in partes[1:] if "=" in p)
        resultado[partes[0]] = [float(campos["avg10"]), float(campos["avg60"]), float(campos["avg300"]),
                                int(campos["total"])]
    if "some" not in resultado:
        raise ValueError("sin linea some")
    return resultado


def leer_meminfo(raiz: str) -> dict:
    valores = {}
    for linea in _leer(_en(raiz, "proc/meminfo")).splitlines():
        clave, _, resto = linea.partition(":")
        if clave in MEMINFO_CLAVES:
            valores[clave] = int(resto.split()[0])
    faltan = [c for c in MEMINFO_CLAVES if c not in valores]
    if faltan:
        raise ValueError(f"faltan {','.join(faltan)}")
    return valores


def leer_loadavg(raiz: str) -> list:
    partes = _leer(_en(raiz, "proc/loadavg")).split()
    return [float(partes[0]), float(partes[1]), float(partes[2])]


def leer_boot_id(raiz: str) -> str:
    try:
        return _leer(_en(raiz, "proc/sys/kernel/random/boot_id")).strip().replace("-", "")
    except OSError:
        return "desconocido"


def _numero(nombre: str, prefijo: str) -> str:
    return nombre[len(prefijo):]


def descubrir(raiz: str) -> dict:
    """Inventario que cambia poco: zonas con su tipo y trip points, y los archivos hwmon de potencia, voltaje y
    corriente. Se llama al inicio y cada INVENTARIO_CADA_S; el bucle de 250 ms solo lee los `temp`/`*_input` ya
    descubiertos (un glob cada 250 ms seria el costo dominante)."""
    zonas, rutas_temp, ausente = {}, {}, {}
    def orden(d: str) -> tuple:
        n = _numero(os.path.basename(d), "thermal_zone")
        return (not n.isdigit(), int(n) if n.isdigit() else 0, n)

    dirs = sorted(glob.glob(_en(raiz, "sys/class/thermal/thermal_zone*")), key=orden)
    for d in dirs:
        n = _numero(os.path.basename(d), "thermal_zone")
        zona = {"trips": []}
        try:
            zona["tipo"] = _leer(os.path.join(d, "type")).strip()
        except OSError as exc:
            zona["tipo"] = None
            zona["error"] = _corto(exc)
        indices = [os.path.basename(r)[len("trip_point_"):-len("_temp")]
                   for r in glob.glob(os.path.join(d, "trip_point_*_temp"))]
        for i in sorted(indices, key=lambda i: (not i.isdigit(), int(i) if i.isdigit() else 0, i)):
            ruta = os.path.join(d, f"trip_point_{i}_temp")
            trip = {"n": int(i) if i.isdigit() else i}
            try:
                trip["temp_c"] = int(_leer(ruta).strip()) / 1000
                trip["tipo"] = _leer(os.path.join(d, f"trip_point_{i}_type")).strip()
            except (OSError, ValueError) as exc:
                trip["error"] = _corto(exc)
            zona["trips"].append(trip)
        zonas[n] = zona
        rutas_temp[n] = os.path.join(d, "temp")
    if not zonas:
        ausente["termica"] = f"sin thermal_zone* en {_en(raiz, 'sys/class/thermal')}"
    nombres, rutas_hwmon = {}, {}
    for d in sorted(glob.glob(_en(raiz, "sys/class/hwmon/hwmon*"))):
        base = os.path.basename(d)
        try:
            nombres[base] = _leer(os.path.join(d, "name")).strip()
        except OSError:
            nombres[base] = None
        # Los drivers viejos dejan los atributos en hwmonN/device/ en vez de hwmonN/.
        for patron in HWMON_PATRONES:
            for ruta in sorted(glob.glob(os.path.join(d, patron)) + glob.glob(os.path.join(d, "device", patron))):
                rutas_hwmon[f"{base}/{os.path.relpath(ruta, d)}"] = ruta
    if not rutas_hwmon:
        ausente["hwmon"] = f"sin power/in/curr*_input en {_en(raiz, 'sys/class/hwmon')}"
    return {"zonas": zonas, "hwmon_nombres": nombres, "rutas_temp": rutas_temp, "rutas_hwmon": rutas_hwmon,
            "ausente": ausente}


def muestrear(raiz: str, inventario: dict) -> dict:
    """Una lectura completa. Nunca lanza: cada fuente que falla queda en `ausente` con su motivo."""
    muestra: dict = {"psi": {}}
    ausente = dict(inventario["ausente"])
    for recurso in PSI_RECURSOS:
        try:
            muestra["psi"][recurso] = leer_psi(raiz, recurso)
        except (OSError, ValueError, KeyError) as exc:
            ausente[f"psi_{recurso}"] = _corto(exc)
    try:
        muestra["mem_kb"] = leer_meminfo(raiz)
    except (OSError, ValueError, IndexError) as exc:
        ausente["meminfo"] = _corto(exc)
    temps = {}
    for n, ruta in inventario["rutas_temp"].items():
        try:
            temps[n] = int(_leer(ruta).strip()) / 1000
        except (OSError, ValueError) as exc:
            temps[n] = None
            ausente[f"tz{n}"] = _corto(exc)
    if temps:
        muestra["temp_c"] = temps
    valores = {}
    for clave, ruta in inventario["rutas_hwmon"].items():
        try:
            valores[clave] = int(_leer(ruta).strip())
        except (OSError, ValueError) as exc:
            valores[clave] = None
            ausente[clave] = _corto(exc)
    if valores:
        muestra["hwmon"] = valores
    try:
        muestra["loadavg"] = leer_loadavg(raiz)
    except (OSError, ValueError, IndexError) as exc:
        ausente["loadavg"] = _corto(exc)
    if ausente:
        muestra["ausente"] = ausente
    return muestra


def serializar(registro: dict, tamano: int = REGISTRO_BYTES) -> bytes:
    """Linea JSON rellena de espacios hasta `tamano` exacto. Lo que no cabe se recorta y se declara en `recortado`:
    primero hwmon, luego temp_c, luego ausente; si ni asi cabe, queda la cabecera del registro."""
    dato = dict(registro)
    recortado = []
    for clave in ("hwmon", "temp_c", "ausente", "psi", "trips", "nombres"):
        linea = json.dumps(dato, ensure_ascii=True, separators=(",", ":")).encode("ascii")
        if len(linea) < tamano:
            break
        if clave in dato:
            dato.pop(clave)
            recortado.append(clave)
            dato["recortado"] = recortado
    linea = json.dumps(dato, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    if len(linea) >= tamano:
        dato = {k: registro[k] for k in ("seq", "ts", "boot", "tipo") if k in registro}
        dato["recortado"] = "todo"
        linea = json.dumps(dato, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    return linea + b" " * (tamano - 1 - len(linea)) + b"\n"


def registros_inventario(inventario: dict) -> list:
    """Un registro por zona (tipo y trips) y uno con los nombres de hwmon: el inventario completo de la GB10 (7
    zonas con varios trips cada una) no cabe en una ranura de 1024 bytes, cada zona por separado si."""
    registros = [{"tipo": "inventario", "zona": n, "zona_tipo": z.get("tipo"), "trips": z["trips"],
                  **({"error": z["error"]} if "error" in z else {})}
                 for n, z in inventario["zonas"].items()]
    registros.append({"tipo": "inventario", "nombres": inventario["hwmon_nombres"],
                      "ausente": inventario["ausente"]})
    return registros


def _encabezado(tamano: int, encabezado: int, registro: int) -> dict:
    return {"formato": FORMATO_ANILLO, "tamano": tamano, "encabezado": encabezado, "registro": registro,
            "ranuras": (tamano - encabezado) // registro}


def _parsear_ranuras(datos: bytes, registro: int) -> tuple[list, int]:
    """(registros validos, ilegibles). Una ranura de ceros nunca se uso; una que no parsea es una escritura rota."""
    registros, ilegibles = [], 0
    for inicio in range(0, len(datos) - registro + 1, registro):
        ranura = datos[inicio:inicio + registro]
        if ranura[0] == 0:
            continue
        try:
            dato = json.loads(ranura)
            if isinstance(dato, dict) and isinstance(dato.get("seq"), int):
                registros.append(dato)
                continue
        except ValueError:
            pass
        ilegibles += 1
    return registros, ilegibles


class AnilloOcupado(RuntimeError):
    """Otra instancia tiene el flock del anillo."""


class Anillo:
    """Archivo de tamano fijo con ranuras de longitud fija. La ranura de un registro es `seq % ranuras`: ese modulo
    es el tope de tamano, y `tests/test_ultimo_aliento.py` lo controla por mutacion."""

    def __init__(self, ruta: str, tamano: int = TAMANO_ANILLO, encabezado: int = ENCABEZADO_BYTES,
                 registro: int = REGISTRO_BYTES):
        self.ruta, self.tamano, self.encabezado, self.registro = ruta, tamano, encabezado, registro
        self.ranuras = (tamano - encabezado) // registro
        self.fd = -1
        self.seq = 0
        self._lock = threading.Lock()

    def _valido(self, fd: int) -> bool:
        if os.fstat(fd).st_size != self.tamano:
            return False
        try:
            cabecera = json.loads(os.pread(fd, self.encabezado, 0))
        except ValueError:
            return False
        esperado = _encabezado(self.tamano, self.encabezado, self.registro)
        return all(cabecera.get(k) == v for k, v in esperado.items())

    def _bloquear(self, fd: int) -> None:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            raise AnilloOcupado(f"otra instancia escribe {self.ruta}") from None

    def abrir(self) -> list:
        """Abre o crea el anillo y devuelve notas para el evento de arranque. Un archivo con otra geometria o un
        encabezado roto NO se pisa: se renombra a `.previo` (uno solo, acotado) y se crea uno nuevo."""
        notas = []
        os.makedirs(os.path.dirname(self.ruta) or ".", exist_ok=True)
        fd = os.open(self.ruta, os.O_RDWR | os.O_CREAT, 0o644)
        self._bloquear(fd)
        if os.fstat(fd).st_size and not self._valido(fd):
            os.replace(self.ruta, self.ruta + ".previo")
            notas.append(f"anillo invalido renombrado a {self.ruta}.previo")
            viejo, fd = fd, os.open(self.ruta, os.O_RDWR | os.O_CREAT, 0o644)
            self._bloquear(fd)
            os.close(viejo)
        if os.fstat(fd).st_size == 0:
            os.posix_fallocate(fd, 0, self.tamano)
            cabecera = dict(_encabezado(self.tamano, self.encabezado, self.registro), creado=round(time.time(), 3))
            os.pwrite(fd, serializar(cabecera, self.encabezado), 0)
            os.fdatasync(fd)
            notas.append("anillo nuevo")
        registros, ilegibles = _parsear_ranuras(os.pread(fd, self.tamano - self.encabezado, self.encabezado),
                                                self.registro)
        self.seq = max((r["seq"] for r in registros), default=-1) + 1
        if ilegibles:
            notas.append(f"{ilegibles} ranuras ilegibles (escritura cortada)")
        self.fd = fd
        return notas

    def escribir(self, registro: dict) -> int:
        with self._lock:
            seq = self.seq
            self.seq += 1
            linea = serializar({"seq": seq, **registro}, self.registro)
            os.pwrite(self.fd, linea, self.encabezado + (seq % self.ranuras) * self.registro)
        return seq

    def cerrar(self) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1


def leer_anillo(ruta: str) -> dict:
    """Lectura sin lock (la usa un usuario sin privilegios mientras el demonio escribe): registros ordenados por
    `seq`, ilegibles y la cabecera. Una ranura reescrita a media lectura sale como ilegible, nunca como dato."""
    fd = os.open(ruta, os.O_RDONLY)
    try:
        primeros = os.pread(fd, ENCABEZADO_BYTES, 0)
        cabecera = json.loads(primeros[:primeros.index(b"\n")] if b"\n" in primeros else primeros)
        if cabecera.get("formato") != FORMATO_ANILLO:
            raise ValueError(f"formato desconocido: {cabecera.get('formato')!r}")
        datos = os.pread(fd, cabecera["tamano"] - cabecera["encabezado"], cabecera["encabezado"])
    finally:
        os.close(fd)
    registros, ilegibles = _parsear_ranuras(datos, cabecera["registro"])
    registros.sort(key=lambda r: r["seq"])
    return {"cabecera": cabecera, "registros": registros, "ilegibles": ilegibles}


def escribir_estado(ruta: str, dato: dict) -> None:
    """Temporal en el mismo directorio + rename: el lector ve el archivo viejo o el nuevo, nunca uno a medias."""
    cuerpo = json.dumps(dato, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    tmp = os.path.join(os.path.dirname(ruta) or ".", f".{os.path.basename(ruta)}.{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        vista = memoryview(cuerpo)
        while vista:
            vista = vista[os.write(fd, vista):]
    finally:
        os.close(fd)
    os.replace(tmp, ruta)


def leer_estado(ruta: str = ESTADO_RUTA, max_edad_s: float = ESTADO_MAX_EDAD_S,
                ahora: float | None = None) -> tuple[dict | None, str | None]:
    """Para consumidores: (dato, None) si el snapshot es valido y fresco; si no, (dato o None, motivo). Un sello
    viejo o en el futuro NO es un dato del presente."""
    try:
        with open(ruta, encoding="utf-8") as f:
            dato = json.load(f)
    except (OSError, ValueError) as exc:
        return None, _corto(exc)
    if not isinstance(dato, dict) or dato.get("formato") != FORMATO_ESTADO:
        return None, f"formato distinto de {FORMATO_ESTADO}"
    ts = dato.get("ts")
    if not isinstance(ts, (int, float)):
        return dato, "sin sello ts"
    edad = (time.time() if ahora is None else ahora) - ts
    if edad > max_edad_s:
        return dato, f"sello viejo: {edad:.1f} s (max {max_edad_s} s)"
    if edad < -max_edad_s:
        return dato, f"sello en el futuro: {-edad:.1f} s"
    return dato, None


def bloquear_memoria(euid: int | None = None, libc=None) -> str:
    """mlockall(MCL_CURRENT|MCL_FUTURE) si es root. Devuelve "ok" o el motivo; nunca lanza."""
    if (os.geteuid() if euid is None else euid) != 0:
        return "omitido: no es root"
    try:
        libc = libc or ctypes.CDLL(None, use_errno=True)
        rc = libc.mlockall(MCL_CURRENT | MCL_FUTURE)
    except (OSError, AttributeError) as exc:
        return f"fallo: {_corto(exc)}"
    if rc != 0:
        err = ctypes.get_errno()
        return f"fallo: errno {err} ({os.strerror(err)})"
    return "ok"


def parsear_destino(destino: str) -> tuple[int, tuple[str, int]]:
    """`IP:PUERTO` o `[IPv6]:PUERTO`, IP literal: resolver DNS cada 250 ms podria colgar el muestreo."""
    if destino.startswith("["):
        host, puerto_txt = destino[1:].split("]:", 1)
    else:
        host, puerto_txt = destino.rsplit(":", 1)
    ip = ipaddress.ip_address(host)
    puerto = int(puerto_txt)
    if not 1 <= puerto <= 65535:
        raise ValueError("puerto fuera de 1..65535")
    return (socket.AF_INET6 if ip.version == 6 else socket.AF_INET), (host, puerto)


def udp_payload(registro: dict) -> bytes:
    """Claves de `_udp_payload` (tools/atom_gpu_telemetry.py) para las senales comunes, mas las propias; zlib."""
    psi, mem = registro.get("psi", {}), registro.get("mem_kb", {})
    dato = {"ts": registro.get("ts"), "evento": "ultimo_aliento", "boot_id": registro.get("boot"),
            "seq": registro.get("seq")}
    if "MemFree" in mem:
        dato["mem_free_mb"] = mem["MemFree"] // 1024
        dato["mem_avail_mb"] = mem["MemAvailable"] // 1024
        dato["swap_free_mb"] = mem["SwapFree"] // 1024
        dato["dirty_mb"] = mem["Dirty"] // 1024
    for recurso, prefijo in (("memory", "psi_mem"), ("cpu", "psi_cpu"), ("io", "psi_io")):
        for grupo, valores in psi.get(recurso, {}).items():
            for campo, valor in zip(("avg10", "avg60", "avg300", "total"), valores):
                dato[f"{prefijo}_{grupo}_{campo}"] = valor
    if registro.get("loadavg"):
        dato["loadavg_1"] = registro["loadavg"][0]
    dato["zonas"] = [{"zona": f"thermal_zone{n}", "temp_c": t}
                     for n, t in list(registro.get("temp_c", {}).items())[:8]]
    comprimido = zlib.compress(json.dumps(dato, separators=(",", ":")).encode("utf-8"))
    if len(comprimido) > UDP_DATAGRAM_MAX_BYTES:
        dato.pop("zonas")
        comprimido = zlib.compress(json.dumps(dato, separators=(",", ":")).encode("utf-8"))
    if len(comprimido) > UDP_DATAGRAM_MAX_BYTES:
        raise ValueError(f"payload supera {UDP_DATAGRAM_MAX_BYTES} bytes")
    return comprimido


class UltimoAliento:
    """El bucle de 250 ms. Nada en `correr` espera al disco: el fdatasync vive en `_hilo_sync` y el bucle solo
    consulta, sin bloquear, si el que esta en curso ya paso el plazo."""

    def __init__(self, anillo: Anillo, raiz: str = "/", estado_ruta: str = ESTADO_RUTA,
                 intervalo: float = INTERVALO_S, sync_cada: float = SYNC_CADA_S, plazo_fsync: float = FSYNC_PLAZO_S,
                 inventario_cada: float = INVENTARIO_CADA_S, estado_cada: float = ESTADO_CADA_S,
                 udp: str | None = None, fsync=os.fdatasync, bloquear=bloquear_memoria):
        self.anillo, self.raiz, self.estado_ruta = anillo, raiz, estado_ruta
        self.intervalo, self.sync_cada, self.plazo_fsync = intervalo, sync_cada, plazo_fsync
        self.inventario_cada, self.estado_cada, self.fsync = inventario_cada, estado_cada, fsync
        self._bloquear = bloquear
        self.parar = threading.Event()
        self._parada_escrita = threading.Event()
        self.boot = leer_boot_id(raiz)
        self.inventario: dict = {}
        self.ultima: dict | None = None
        self.mlock = "sin intentar"
        self.fsync_info = {"ultimo_s": None, "max_s": 0.0, "lentos": 0, "errores": 0, "en_curso_s": None}
        self.errores = {"anillo": 0, "estado": 0}
        self.atrasos = 0
        self._sync_inicio: float | None = None
        self._avisado_inicio: float | None = None
        self._avisos: collections.deque = collections.deque()
        self.udp = {"destino": udp, "enviados": 0, "errores": 0, "ultimo_error": None}
        self._sock, self._udp_dir = None, None
        if udp:
            try:
                familia, self._udp_dir = parsear_destino(udp)
                self._sock = socket.socket(familia, socket.SOCK_DGRAM)
                self._sock.setblocking(False)
            except (OSError, ValueError) as exc:
                self.udp["ultimo_error"] = f"destino invalido: {_corto(exc)}"
                _log(f"UDP desactivado: {self.udp['ultimo_error']}")

    def _registro(self, cuerpo: dict) -> dict:
        return {"ts": round(time.time(), 3), "boot": self.boot, **cuerpo}

    def _escribir(self, cuerpo: dict) -> dict:
        registro = self._registro(cuerpo)
        try:
            registro["seq"] = self.anillo.escribir(registro)
        except OSError as exc:
            self.errores["anillo"] += 1
            if self.errores["anillo"] == 1:
                _log(f"escritura al anillo fallo (se sigue con estado y UDP): {_corto(exc)}")
        return registro

    def _evento(self, evento: str, **campos) -> None:
        self._escribir({"tipo": "evento", "evento": evento, **campos})

    def _sync_una(self) -> None:
        inicio = time.monotonic()
        self._sync_inicio = inicio
        try:
            self.fsync(self.anillo.fd)
        except OSError as exc:
            self.fsync_info["errores"] += 1
            self._avisos.append({"evento": "fsync_error", "error": _corto(exc)})
        duracion = time.monotonic() - inicio
        self._sync_inicio = None
        self.fsync_info["ultimo_s"] = round(duracion, 4)
        self.fsync_info["max_s"] = max(self.fsync_info["max_s"], round(duracion, 4))
        if duracion > self.plazo_fsync:
            self._avisos.append({"evento": "fsync_lento", "duracion_s": round(duracion, 3), "en_curso": False})
            self.fsync_info["lentos"] += 1
            _log(f"fdatasync tardo {duracion:.3f} s (plazo {self.plazo_fsync} s)")

    def _hilo_sync(self) -> None:
        while not self.parar.wait(self.sync_cada):
            self._sync_una()
        self._parada_escrita.wait(timeout=5.0)  # el ultimo fdatasync debe llevarse el evento de parada
        self._sync_una()

    def _vigilar_fsync(self) -> None:
        """Sin bloquear: si el fdatasync en curso ya paso el plazo, se anota UNA vez mientras sigue colgado."""
        inicio = self._sync_inicio
        if inicio is not None:
            lleva = time.monotonic() - inicio
            self.fsync_info["en_curso_s"] = round(lleva, 3)
            if lleva > self.plazo_fsync and self._avisado_inicio != inicio:
                self._avisado_inicio = inicio
                self._evento("fsync_lento", en_curso=True, lleva_s=round(lleva, 3))
                _log(f"fdatasync lleva {lleva:.3f} s colgado; el muestreo sigue")
        else:
            self.fsync_info["en_curso_s"] = None
        while self._avisos:
            self._evento(**self._avisos.popleft())

    def _inventariar(self) -> None:
        self.inventario = descubrir(self.raiz)
        for registro in registros_inventario(self.inventario):
            self._escribir(registro)

    def _enviar_udp(self, registro: dict) -> None:
        if self._sock is None:
            return
        try:
            self._sock.sendto(udp_payload(registro), self._udp_dir)
            self.udp["enviados"] += 1
        except (OSError, ValueError) as exc:
            self.udp["errores"] += 1
            self.udp["ultimo_error"] = _corto(exc)
            if self.udp["errores"] == 1:
                _log(f"envio UDP fallo (se cuenta en el estado, no se repite aqui): {self.udp['ultimo_error']}")

    def estado(self) -> dict:
        ahora = time.time()
        inventario = {n: {"tipo": z.get("tipo"), "trips": z["trips"]} for n, z in self.inventario["zonas"].items()}
        return {"formato": FORMATO_ESTADO, "ts": round(ahora, 3),
                "ts_iso": datetime.fromtimestamp(ahora, timezone.utc).isoformat(timespec="milliseconds"),
                "boot": self.boot, "pid": os.getpid(), "intervalo_s": self.intervalo, "ultima": self.ultima,
                "zonas": inventario, "hwmon_nombres": self.inventario["hwmon_nombres"],
                "fsync": dict(self.fsync_info), "mlock": self.mlock, "udp": dict(self.udp),
                "errores": dict(self.errores), "atrasos": self.atrasos, "anillo": self.anillo.ruta}

    def _publicar_estado(self) -> None:
        try:
            escribir_estado(self.estado_ruta, self.estado())
        except OSError as exc:
            self.errores["estado"] += 1
            if self.errores["estado"] == 1:
                _log(f"no se pudo escribir {self.estado_ruta}: {_corto(exc)}")

    def correr(self, notas: list | None = None) -> None:
        """El anillo ya viene abierto (y con su flock). Vuelve cuando alguien pone `parar`."""
        self.mlock = self._bloquear()
        if self.mlock != "ok":
            _log(f"mlockall: {self.mlock}")
        self._evento("arranque", pid=os.getpid(), notas=notas or [], mlock=self.mlock, raiz=self.raiz,
                     intervalo_s=self.intervalo)
        self._inventariar()
        hilo = threading.Thread(target=self._hilo_sync, name="fdatasync", daemon=True)
        hilo.start()
        ultimo_inventario = ultimo_estado = siguiente = time.monotonic()
        ultimo_estado -= self.estado_cada
        while not self.parar.is_set():
            if time.monotonic() - ultimo_inventario >= self.inventario_cada:
                ultimo_inventario = time.monotonic()
                self._inventariar()
            self.ultima = self._escribir({"tipo": "muestra", **muestrear(self.raiz, self.inventario)})
            self._enviar_udp(self.ultima)
            self._vigilar_fsync()
            if time.monotonic() - ultimo_estado >= self.estado_cada:
                ultimo_estado = time.monotonic()
                self._publicar_estado()
            siguiente += self.intervalo
            espera = siguiente - time.monotonic()
            if espera < -self.intervalo:  # el bucle se atraso mas de una vuelta: se re-ancla, no se recupera a rafagas
                self.atrasos += 1
                siguiente, espera = time.monotonic(), 0.0
            self.parar.wait(max(0.0, espera))
        self._vigilar_fsync()
        self._evento("parada", atrasos=self.atrasos)
        self._parada_escrita.set()
        hilo.join(timeout=self.plazo_fsync)  # el ultimo fdatasync; si el disco esta colgado no se espera para siempre
        self._publicar_estado()


def volcar(ruta: str, salida=None) -> int:
    salida = salida or sys.stdout
    try:
        anillo = leer_anillo(ruta)
    except (OSError, ValueError, KeyError) as exc:
        _log(f"no se pudo leer el anillo {ruta}: {_corto(exc)}")
        return 1
    try:
        for registro in anillo["registros"]:
            salida.write(json.dumps(registro, ensure_ascii=False, separators=(",", ":")) + "\n")
        salida.flush()
    except BrokenPipeError:  # `--volcar | head`: el lector ya tiene lo que queria
        os.dup2(os.open(os.devnull, os.O_WRONLY), salida.fileno())
        return 0
    _log(f"{len(anillo['registros'])} registros de {anillo['cabecera']['ranuras']} ranuras; "
         f"{anillo['ilegibles']} ilegibles")
    return 0


def informe_estado(estado_ruta: str, anillo_ruta: str) -> tuple[dict, int]:
    """`--estado`: el snapshot con su frescura y un resumen del anillo. rc=0 solo si el sello esta fresco."""
    dato, motivo = leer_estado(estado_ruta)
    informe: dict = {"estado_ruta": estado_ruta, "fresco": motivo is None, "motivo": motivo, "estado": dato}
    if dato and isinstance(dato.get("ts"), (int, float)):
        informe["edad_s"] = round(time.time() - dato["ts"], 3)
    try:
        anillo = leer_anillo(anillo_ruta)
        registros = anillo["registros"]
        informe["anillo"] = {"ruta": anillo_ruta, "tamano": os.stat(anillo_ruta).st_size,
                             "ranuras": anillo["cabecera"]["ranuras"], "validos": len(registros),
                             "ilegibles": anillo["ilegibles"],
                             "seq_min": registros[0]["seq"] if registros else None,
                             "seq_max": registros[-1]["seq"] if registros else None,
                             "ts_ultimo": registros[-1].get("ts") if registros else None}
    except (OSError, ValueError, KeyError) as exc:
        informe["anillo"] = {"ruta": anillo_ruta, "error": _corto(exc)}
    return informe, 0 if motivo is None else 1


def main(argv: list | None = None) -> int:
    p = argparse.ArgumentParser(description="Muestreo de 250 ms con fdatasync cada segundo (ultimo aliento).")
    p.add_argument("--raiz", default=os.environ.get("BB_ULTIMO_ALIENTO_RAIZ", "/"),
                   help="raiz donde buscar proc/ y sys/ (costura para pruebas)")
    p.add_argument("--anillo", default=ANILLO_RUTA)
    p.add_argument("--estado-ruta", default=ESTADO_RUTA)
    p.add_argument("--udp", default=os.environ.get("BB_ULTIMO_ALIENTO_UDP") or None, help="IP:PUERTO del testigo")
    p.add_argument("--intervalo", type=float, default=INTERVALO_S)
    modo = p.add_mutually_exclusive_group()
    modo.add_argument("--volcar", action="store_true", help="exporta el anillo a JSONL en orden de seq")
    modo.add_argument("--estado", action="store_true", help="muestra el snapshot y su frescura")
    args = p.parse_args(argv)
    if args.volcar:
        return volcar(args.anillo)
    if args.estado:
        informe, rc = informe_estado(args.estado_ruta, args.anillo)
        print(json.dumps(informe, ensure_ascii=False, indent=2))
        return rc
    if args.intervalo <= 0:
        p.error("--intervalo debe ser positivo")
    anillo = Anillo(args.anillo)
    try:
        notas = anillo.abrir()
    except AnilloOcupado as exc:
        _log(str(exc))
        return 2
    os.makedirs(os.path.dirname(args.estado_ruta) or ".", exist_ok=True)
    threading.stack_size(256 * 1024)  # con MCL_FUTURE la pila del hilo de fdatasync queda bloqueada entera
    demonio = UltimoAliento(anillo, raiz=args.raiz, estado_ruta=args.estado_ruta, intervalo=args.intervalo,
                            udp=args.udp)
    for senal in (signal.SIGTERM, signal.SIGINT):
        signal.signal(senal, lambda *_: demonio.parar.set())
    demonio.correr(notas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
