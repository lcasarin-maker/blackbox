#!/usr/bin/env python3
"""bb-testigo: testigo EXTERNO de la ATOM. Un solo archivo de Python stdlib (3.8+) que corre en OTRO equipo.

Todo lo que observa la ATOM corre dentro de ella y muere con ella: seis cortes duros quedaron sin causa. Este testigo vive en
otro equipo (Linux, macOS o Windows) y deja evidencia que sobrevive al corte, en su directorio de datos:

  netconsole.jsonl  cada datagrama UDP recibido en `udp_puerto` (6666): netconsole del kernel, journal-udp-forward y la exportacion
                    UDP de atom_gpu_telemetry; con la hora de RECEPCION y la IP y el puerto de origen.
  ping.jsonl        un sondeo TCP a `atom_host:atom_puerto` (22) cada `sondeo_s`, sin root e igual en los tres sistemas, y otro
                    ICMP si hay `ping`. Esquema de `externo/ping.jsonl` (ts, epoch, ok) mas fuente y estado.
  energia.jsonl     (opcional) la lectura del enchufe con medidor: Shelly Gen1 `/status`, Gen2 `/rpc/Switch.GetStatus` o Tasmota
                    `Status 10`. Esquema de `energia.jsonl` (ok, voltaje_v, potencia_w, corriente_a).
  latido.jsonl      el latido propio cada `latido_s`: separa «testigo caido» de «ATOM callada».

Cada linea se escribe con fsync (lo que el testigo vio queda en disco aunque a el tambien lo corten) y cada archivo rota por
tamano. Subcomandos: install (servicio de usuario por plataforma; --dry-run imprime sin escribir nada), run, status (lo ultimo
recibido y el veredicto de ventana) y uninstall (deshace el servicio; los datos se conservan salvo --borrar-datos).

Semantica de `ok` en ping.jsonl, la misma que leen observador_ping.ultima_respuesta/primera_falla y reboot_verdict: «la ATOM
contesto». En TCP eso es aceptar la conexion (`estado` abierto) o rechazarla con RST (`rechazado`: el kernel vive aunque sshd
no); en ICMP, hubo eco. Un fallo puede ser la red del propio testigo: `sin_red` no cuenta como silencio de la ATOM, y sin latido
fresco `status` no concluye nada sobre ella.
"""

from __future__ import annotations

import argparse
import base64
import errno
import json
import math
import os
import plistlib
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple
from xml.sax.saxutils import escape

APP = "bb-testigo"
VERSION = "1"
ETIQUETA_LAUNCHD = "local.bb-testigo"
TAREA_WINDOWS = "bb-testigo"
UNIDAD_SYSTEMD = "bb-testigo.service"
ARCHIVOS = ("netconsole", "ping", "energia", "latido")
TIPOS_ENCHUFE = ("shelly1", "shelly2", "tasmota")
RUTAS_ENCHUFE = {"shelly1": "/status", "shelly2": "/rpc/Switch.GetStatus?id=0", "tasmota": "/cm?cmnd=Status%2010"}
DEFECTOS: Dict[str, Any] = {
    "atom_host": "",
    "atom_puerto": 22,
    "tcp_timeout_s": 2.0,  # Windows reintenta el SYN ante un RST (~1 s): con 1 s un puerto cerrado se leeria como timeout
    "sondeo_s": 1.0,
    "icmp": "auto",  # "auto": solo si hay `ping` en el PATH
    "udp_bind": "0.0.0.0",
    "udp_puerto": 6666,
    "enchufe_tipo": "",
    "enchufe_url": "",
    "enchufe_s": 1.0,
    "latido_s": 10.0,
    "rota_mb": 50.0,
    "rota_copias": 5,
}
# Umbrales de energia: los mismos de tools/medidor_energia.py (red de 120 V; la ATOM encendida consume 22-45 W).
VOLTAJE_CAIDO_V = 90.0
VOLTAJE_NORMAL_V = 100.0
CARGA_W = 20.0
APAGADA_W = 5.0
MARGEN_ENERGIA_S = 60.0
FALLOS_MIN = 3  # un silencio es >= 3 sondeos seguidos sin respuesta y >= 3 s: un paquete perdido no es un corte
SILENCIO_MIN_S = 3.0
COLA_BYTES = 16 * 1024 * 1024  # status lee a lo sumo esto de cada serie (~11 h de ping.jsonl con TCP+ICMP a 1 Hz)
SIN_RED = {e for e in (errno.ENETUNREACH, errno.ENETDOWN, getattr(errno, "WSAENETUNREACH", None), getattr(errno, "WSAENETDOWN", None)) if e}
Correr = Callable[..., Any]
Abre = Callable[[str], bytes]


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).isoformat()


def _local(t: float) -> str:
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")


def _es_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def sistema_actual() -> str:
    """"linux", "darwin" o "win32"; cualquier otro sistema se devuelve tal cual (sin ICMP ni instalador)."""
    return "linux" if sys.platform.startswith("linux") else sys.platform


def _home(env: Mapping[str, str]) -> Path:
    return Path(env.get("HOME") or env.get("USERPROFILE") or str(Path.home()))


def dir_datos(sistema: Optional[str] = None, env: Optional[Mapping[str, str]] = None) -> Path:
    """Directorio de datos por plataforma; `BB_TESTIGO_DATA` lo sustituye (pruebas, o un disco elegido por el usuario)."""
    env = os.environ if env is None else env
    if env.get("BB_TESTIGO_DATA"):
        return Path(env["BB_TESTIGO_DATA"])
    s, h = sistema or sistema_actual(), _home(env)
    if s == "darwin":
        return h / "Library" / "Application Support" / APP
    if s == "win32":
        return Path(env["LOCALAPPDATA"]) / APP if env.get("LOCALAPPDATA") else h / "AppData" / "Local" / APP
    return (Path(env["XDG_DATA_HOME"]) if env.get("XDG_DATA_HOME") else h / ".local" / "share") / APP


def valida_config(crudo: Mapping[str, Any]) -> Dict[str, Any]:
    """Mezcla con DEFECTOS y valida; ValueError con un motivo legible para quien no programa."""
    desconocidas = sorted(set(crudo) - set(DEFECTOS))
    if desconocidas:
        raise ValueError(f"claves desconocidas en testigo.json: {', '.join(desconocidas)}")
    c = dict(DEFECTOS)
    c.update(crudo)
    host = c["atom_host"]
    if not isinstance(host, str) or not host.strip() or any(ch.isspace() for ch in host):
        raise ValueError("atom_host: falta la IP (o el nombre) de la ATOM")
    for k, lo, hi in (("atom_puerto", 1, 65535), ("udp_puerto", 0, 65535), ("rota_copias", 1, 100)):
        if not isinstance(c[k], int) or isinstance(c[k], bool) or not lo <= c[k] <= hi:
            raise ValueError(f"{k}: debe ser un entero entre {lo} y {hi}")
    for k, lo in (("tcp_timeout_s", 0.1), ("sondeo_s", 0.2), ("enchufe_s", 0.2), ("latido_s", 0.2), ("rota_mb", 0.001)):
        if not _es_num(c[k]) or c[k] < lo:
            raise ValueError(f"{k}: debe ser un numero >= {lo}")
        c[k] = float(c[k])
    if c["icmp"] not in ("auto", True, False):
        raise ValueError('icmp: debe ser "auto", true o false')
    if not isinstance(c["udp_bind"], str) or not c["udp_bind"]:
        raise ValueError("udp_bind: debe ser una direccion local, p. ej. 0.0.0.0")
    if c["enchufe_tipo"] not in TIPOS_ENCHUFE + ("",):
        raise ValueError(f"enchufe_tipo: uno de {', '.join(TIPOS_ENCHUFE)} (o vacio si no hay enchufe)")
    if c["enchufe_tipo"] and not (isinstance(c["enchufe_url"], str) and re.fullmatch(r"https?://[^\s/]+/?", c["enchufe_url"])):
        raise ValueError("enchufe_url: debe ser http://<ip-del-enchufe>")
    return c


def carga_config(ruta: Path) -> Dict[str, Any]:
    try:
        crudo = json.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"falta {ruta}: corre primero `install`") from None
    except (OSError, ValueError) as e:
        raise ValueError(f"{ruta} ilegible: {e}") from None
    if not isinstance(crudo, dict):
        raise ValueError(f"{ruta}: debe ser un objeto JSON")
    return valida_config(crudo)


class Diario:
    """Una serie JSONL: una fila por linea, fsync por linea, rotacion por tamano (x.jsonl.1 ... x.jsonl.N). Segura entre hilos.

    Se abre y se cierra en cada fila: a 1 Hz cuesta nada, sobrevive a que alguien mueva el archivo y en Windows deja rotar
    (os.replace falla sobre un archivo abierto)."""

    def __init__(self, ruta: Path, rota_bytes: int, copias: int):
        self.ruta, self.rota_bytes, self.copias = ruta, max(int(rota_bytes), 1), copias
        self._lock = threading.Lock()

    def _rotada(self, i: int) -> Path:
        return self.ruta if i == 0 else self.ruta.with_name(f"{self.ruta.name}.{i}")

    def _rota(self, entrante: int) -> None:
        try:
            tam = self.ruta.stat().st_size
        except FileNotFoundError:
            return
        if tam == 0 or tam + entrante <= self.rota_bytes:
            return
        for i in range(self.copias, 0, -1):  # la copia mas vieja se pisa: quedan exactamente `copias`
            if self._rotada(i - 1).exists():
                os.replace(self._rotada(i - 1), self._rotada(i))

    def escribe(self, fila: Mapping[str, Any]) -> None:
        datos = (json.dumps(fila, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        with self._lock:
            self.ruta.parent.mkdir(parents=True, exist_ok=True)
            self._rota(len(datos))
            with open(self.ruta, "ab") as fh:
                fh.write(datos)
                fh.flush()
                os.fsync(fh.fileno())


def lee_filas(ruta: Path, max_bytes: int = COLA_BYTES) -> List[Dict[str, Any]]:
    """Filas validas (objeto con `epoch` numerico) de la cola de `ruta` y sus rotaciones, de la mas vieja a la mas nueva."""
    trozos: List[bytes] = []
    resto, i = max_bytes, 0
    while resto > 0 and i <= 100:
        p = ruta if i == 0 else ruta.with_name(f"{ruta.name}.{i}")
        try:
            with open(p, "rb") as fh:
                tam = fh.seek(0, 2)
                n = min(tam, resto)
                fh.seek(tam - n)
                b = fh.read(n)
        except OSError:
            break
        if n < tam:  # la primera linea quedo cortada por la ventana: se descarta, no se lee a medias
            b = b[b.index(b"\n") + 1:] if b"\n" in b else b""
        trozos.append(b)
        resto, i = resto - n, i + 1
    filas: List[Dict[str, Any]] = []
    for b in reversed(trozos):
        for ln in b.decode("utf-8", errors="replace").splitlines():
            try:
                f = json.loads(ln)
            except ValueError:
                continue
            if isinstance(f, dict) and _es_num(f.get("epoch")):
                filas.append(f)
    return filas


# --- Sondeos -------------------------------------------------------------------------------------------------------------


def sondea_tcp(host: str, puerto: int, timeout: float) -> Dict[str, Any]:
    """Un intento de conexion TCP. `ok` si la ATOM contesto: acepto (abierto) o rechazo con RST (rechazado, el kernel vive)."""
    t0 = time.monotonic()
    err: Optional[str] = None
    try:
        with socket.create_connection((host, puerto), timeout=timeout):
            estado = "abierto"
    except ConnectionRefusedError:
        estado, err = "rechazado", "ECONNREFUSED"
    except socket.timeout:
        estado, err = "timeout", "timeout"
    except socket.gaierror as e:  # con mDNS (atom.local) el nombre deja de resolver cuando la ATOM calla: usa la IP
        estado, err = "sin_nombre", f"gaierror {e.errno}"
    except OSError as e:
        estado = "sin_red" if e.errno in SIN_RED else "inalcanzable"
        err = errno.errorcode.get(e.errno or 0, type(e).__name__)
    fila: Dict[str, Any] = {"fuente": "tcp", "destino": host, "puerto": puerto, "ok": estado in ("abierto", "rechazado"),
                            "estado": estado, "rtt_ms": round((time.monotonic() - t0) * 1000.0, 1)}
    if err:
        fila["error"] = err
    return fila


def comando_ping(host: str, sistema: str, timeout_s: float) -> Optional[List[str]]:
    """Un eco con la espera en la unidad de cada sistema: Linux `-W` en segundos, macOS `-W` en ms, Windows `-n 1 -w` en ms."""
    if sistema == "linux":
        return ["ping", "-c", "1", "-W", str(max(1, math.ceil(timeout_s))), host]
    if sistema == "darwin":
        return ["ping", "-c", "1", "-W", str(max(1, int(timeout_s * 1000))), host]
    if sistema == "win32":
        return ["ping", "-n", "1", "-w", str(max(1, int(timeout_s * 1000))), host]
    return None


def sondea_icmp(host: str, sistema: str, timeout_s: float, correr: Correr = subprocess.run) -> Dict[str, Any]:
    base: Dict[str, Any] = {"fuente": "icmp", "destino": host}
    cmd = comando_ping(host, sistema, timeout_s)
    if cmd is None:
        return {**base, "ok": False, "estado": "error", "error": f"sin ping para {sistema}"}
    extra = {"creationflags": 0x08000000} if sys.platform == "win32" else {}  # CREATE_NO_WINDOW: sin ventana por segundo
    try:
        r = correr(cmd, capture_output=True, check=False, timeout=timeout_s + 3.0, **extra)
    except (OSError, subprocess.SubprocessError) as e:
        return {**base, "ok": False, "estado": "error", "error": type(e).__name__}
    ok = r.returncode == 0
    if sistema == "win32":  # Windows sale 0 tambien con «host de destino inaccesible» de un router: solo un eco trae TTL=
        salida = r.stdout if isinstance(r.stdout, bytes) else str(r.stdout or "").encode()
        ok = ok and b"TTL=" in salida.upper()
    return {**base, "ok": ok, "estado": "eco" if ok else "sin_eco"}


def _abre(url: str) -> bytes:
    # Sin proxy: un HTTP_PROXY del usuario mandaria la lectura de un enchufe de la LAN a internet.
    abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with abridor.open(url, timeout=2) as r:
        return bytes(r.read())


def _num(d: Any, *claves: Any) -> Optional[float]:
    for c in claves:
        if isinstance(c, int):
            d = d[c] if isinstance(d, list) and len(d) > c else None
        else:
            d = d.get(c) if isinstance(d, dict) else None
    return float(d) if _es_num(d) else None


def _primero(*valores: Optional[float]) -> Optional[float]:
    return next((v for v in valores if v is not None), None)


def lee_enchufe(tipo: str, url: str, abre: Abre = _abre) -> Dict[str, Any]:
    """Una lectura: ok, voltaje_v, potencia_w, corriente_a. Sin potencia no hay fila `ok`; un campo ausente es None, nunca 0.

    A diferencia de medidor_energia.lee, el voltaje es opcional: los Shelly Gen1 Plug y 1PM no lo miden (solo `meters[].power`);
    el EM lo trae en `emeters[]` y el 2.5 arriba en `voltage`. Los campos son los de la documentacion de cada fabricante, NO
    verificados contra un dispositivo real."""
    if tipo not in RUTAS_ENCHUFE:
        return {"ok": False, "error": f"NOT_COLLECTED: tipo '{tipo}' sin lector"}
    try:
        j = json.loads(abre(url.rstrip("/") + RUTAS_ENCHUFE[tipo]))
    except (OSError, ValueError) as e:  # Wi-Fi del enchufe, enchufe sin corriente o respuesta ilegible: no es voltaje perdido
        return {"ok": False, "error": type(e).__name__}
    if tipo == "shelly1":
        w = _primero(_num(j, "meters", 0, "power"), _num(j, "emeters", 0, "power"))
        v = _primero(_num(j, "emeters", 0, "voltage"), _num(j, "voltage"))
        a = _num(j, "emeters", 0, "current")
    elif tipo == "shelly2":
        w, v, a = _num(j, "apower"), _num(j, "voltage"), _num(j, "current")
    else:
        w, v, a = (_num(j, "StatusSNS", "ENERGY", k) for k in ("Power", "Voltage", "Current"))
    if w is None:
        return {"ok": False, "error": "NOT_COLLECTED: respuesta sin potencia"}
    return {"ok": True, "voltaje_v": v, "potencia_w": w, "corriente_a": a}


def abre_udp(bind: str, puerto: int) -> socket.socket:
    s = socket.socket(socket.AF_INET6 if ":" in bind else socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind((bind, puerto))
    except OSError:
        s.close()
        raise
    s.settimeout(0.5)
    return s


def fila_udp(datos: bytes, origen: Tuple[Any, ...], t: float) -> Dict[str, Any]:
    """El texto tal cual llego (netconsole, journal, JSON de telemetria); lo que no es UTF-8 va en base64, no se pierde."""
    fila: Dict[str, Any] = {"ts": _iso(t), "epoch": t, "origen": origen[0], "puerto_origen": origen[1], "bytes": len(datos)}
    try:
        fila["texto"] = datos.decode("utf-8").rstrip("\r\n")
    except UnicodeDecodeError:
        fila["b64"] = base64.b64encode(datos).decode("ascii")
    return fila


def toma_bloqueo(ruta: Path) -> Optional[Any]:
    """Instancia unica: flock en POSIX, msvcrt.locking en Windows. None si otra instancia ya lo tiene."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fh = open(ruta, "a+b")
    try:
        if os.name == "nt":
            import msvcrt
            fh.seek(0)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    return fh


# --- run -----------------------------------------------------------------------------------------------------------------


class Testigo:
    """Los cuatro observadores en hilos (UDP, TCP, ICMP opcional, enchufe opcional) mas el latido propio."""

    def __init__(self, cfg: Mapping[str, Any], datos: Path, sistema: Optional[str] = None,
                 correr: Correr = subprocess.run, abre: Abre = _abre):
        self.cfg, self.datos, self.sistema = dict(cfg), datos, sistema or sistema_actual()
        self.correr, self.abre = correr, abre
        rota = int(self.cfg["rota_mb"] * 1024 * 1024)
        self.diarios = {n: Diario(datos / f"{n}.jsonl", rota, self.cfg["rota_copias"]) for n in ARCHIVOS}
        self.parar = threading.Event()
        self.cuentas = {"udp": 0, "tcp": 0, "icmp": 0, "enchufe": 0, "latido": 0}
        self.errores: Dict[str, str] = {}
        self.arranque = time.time()
        icmp = self.cfg["icmp"]
        self.con_icmp = bool(comando_ping("x", self.sistema, 1.0)) and (icmp is True or (icmp == "auto" and shutil.which("ping") is not None))

    def _cada(self, nombre: str, intervalo: float, fn: Callable[[], None]) -> None:
        sig = time.monotonic()
        while not self.parar.is_set():
            try:
                fn()
            except Exception as e:  # un hilo no muere en silencio: el error viaja en el siguiente latido
                self.errores[nombre] = f"{type(e).__name__}: {e}"[:200]
            sig += intervalo
            espera = sig - time.monotonic()
            if espera < 0:  # un sondeo mas largo que el intervalo (timeout): se sigue sin rafaga de recuperacion
                sig, espera = time.monotonic(), 0.0
            self.parar.wait(espera)

    def _tcp(self) -> None:
        t = time.time()
        f = sondea_tcp(self.cfg["atom_host"], self.cfg["atom_puerto"], self.cfg["tcp_timeout_s"])
        self.diarios["ping"].escribe({"ts": _iso(t), "epoch": t, **f})
        self.cuentas["tcp"] += 1

    def _icmp(self) -> None:
        t = time.time()
        f = sondea_icmp(self.cfg["atom_host"], self.sistema, self.cfg["tcp_timeout_s"], self.correr)
        self.diarios["ping"].escribe({"ts": _iso(t), "epoch": t, **f})
        self.cuentas["icmp"] += 1

    def _enchufe(self) -> None:
        t = time.time()
        f = lee_enchufe(self.cfg["enchufe_tipo"], self.cfg["enchufe_url"], self.abre)
        self.diarios["energia"].escribe({"ts": _iso(t), "epoch": t, "tipo": self.cfg["enchufe_tipo"], **f})
        self.cuentas["enchufe"] += 1

    def _late(self) -> None:
        t = time.time()
        fila_latido = {"ts": _iso(t), "epoch": t, "evento": "latido", "pid": os.getpid(), "version": VERSION,
                       "arranque_epoch": self.arranque, "intervalo_s": self.cfg["latido_s"],
                       "cuentas": dict(self.cuentas), "errores": dict(self.errores)}
        self.diarios["latido"].escribe(fila_latido)
        self.cuentas["latido"] += 1

    def _escucha(self, sock: socket.socket) -> None:
        while not self.parar.is_set():
            try:
                datos, origen = sock.recvfrom(65535)
            except socket.timeout:
                continue
            except ConnectionResetError:  # Windows: un ICMP «puerto inalcanzable» previo aborta un recvfrom UDP; no es fatal
                continue
            except OSError as e:
                if not self.parar.is_set():
                    self.errores["udp"] = f"{type(e).__name__}: {e}"[:200]
                return
            self.diarios["netconsole"].escribe(fila_udp(datos, origen, time.time()))
            self.cuentas["udp"] += 1

    def corre(self, duracion: Optional[float] = None) -> None:
        """Bloquea hasta `parar` (SIGTERM, Ctrl+C) o `duracion`. Un puerto UDP ocupado sale como OSError ANTES de sondear."""
        sock = abre_udp(self.cfg["udp_bind"], self.cfg["udp_puerto"])
        trabajos: List[Tuple[str, Callable[[], None]]] = [
            ("udp", lambda: self._escucha(sock)),
            ("tcp", lambda: self._cada("tcp", self.cfg["sondeo_s"], self._tcp)),
            ("latido", lambda: self._cada("latido", self.cfg["latido_s"], self._late)),
        ]
        if self.con_icmp:
            trabajos.append(("icmp", lambda: self._cada("icmp", self.cfg["sondeo_s"], self._icmp)))
        if self.cfg["enchufe_tipo"]:
            trabajos.append(("enchufe", lambda: self._cada("enchufe", self.cfg["enchufe_s"], self._enchufe)))
        hilos = [threading.Thread(target=fn, name=f"{APP}-{n}", daemon=True) for n, fn in trabajos]
        for h in hilos:
            h.start()
        fin = None if duracion is None else time.monotonic() + duracion
        try:
            while not self.parar.is_set() and (fin is None or time.monotonic() < fin):
                self.parar.wait(0.2 if fin is None else max(0.0, min(0.2, fin - time.monotonic())))
        except KeyboardInterrupt:
            pass
        finally:
            self.parar.set()
            for h in hilos:
                h.join(timeout=self.cfg["tcp_timeout_s"] + 5.0)
            sock.close()
            t = time.time()  # parada limpia: distingue «lo pararon» de «murio» (sin esta fila)
            self.diarios["latido"].escribe({"ts": _iso(t), "epoch": t, "evento": "parada", "pid": os.getpid(),
                                            "cuentas": dict(self.cuentas), "errores": dict(self.errores)})


# --- status: veredicto de ventana ----------------------------------------------------------------------------------------


def _responde(f: Mapping[str, Any]) -> bool:
    # `ok` significa lo mismo aqui que en las filas de observador_ping y del NAS: la ATOM contesto.
    return f.get("ok") is True


def episodios(ping: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Silencios: tramos de sondeos seguidos sin respuesta (>= FALLOS_MIN y >= SILENCIO_MIN_S) entre dos respuestas.

    Un hueco SIN filas (el testigo apagado) no es silencio de la ATOM: solo cuentan filas de fallo reales. `sin_red` (la red
    del propio testigo) no cuenta ni como respuesta ni como fallo. Un episodio sin `hasta` sigue abierto."""
    eps: List[Dict[str, Any]] = []
    actual: Optional[Dict[str, Any]] = None
    ultima: Optional[float] = None
    for f in sorted(ping, key=lambda x: x["epoch"]):
        if f.get("estado") == "sin_red":
            continue
        if _responde(f):
            if actual is not None:
                actual["hasta"] = f["epoch"]
                eps.append(actual)
                actual = None
            ultima = f["epoch"]
            continue
        if actual is None:
            actual = {"desde": f["epoch"], "ultima_respuesta": ultima, "hasta": None, "fallos": 0, "ultimo_fallo": f["epoch"]}
        actual["fallos"] += 1
        actual["ultimo_fallo"] = f["epoch"]
    if actual is not None:
        eps.append(actual)
    return [e for e in eps if e["fallos"] >= FALLOS_MIN and e["ultimo_fallo"] - e["desde"] >= SILENCIO_MIN_S]


def causa_ventana(ep: Mapping[str, Any], energia: List[Dict[str, Any]], cfg: Mapping[str, Any]) -> Dict[str, Any]:
    """Cruza un silencio con el enchufe. Solo concluye con potencia MEDIDA a ambos lados del instante en que la ATOM callo.

    corte_energia          la potencia cayo a ~0 W (o el voltaje bajo de VOLTAJE_CAIDO_V) antes o a la vez que el silencio.
    cuelgue                la ATOM dejo de responder y siguio consumiendo >= CARGA_W despues.
    apagado_tras_silencio  dejo de responder consumiendo y la potencia cayo DESPUES (cuelgue y luego apagado o reinicio).
    enchufe_mudo           el enchufe dejo de contestar a la vez que la ATOM: lo probable es la pared (el enchufe vive de ella),
                           pero su Wi-Fi tambien explica el silencio; no concluye.
    sin_enchufe / no_concluyente  lo demas: no se distingue corte de cuelgue."""
    desde = float(ep["desde"])
    ref = ep["ultima_respuesta"] if ep.get("ultima_respuesta") is not None else desde
    fin = ep["hasta"] if ep.get("hasta") is not None else math.inf
    tol = max(2.0 * cfg["enchufe_s"], 2.0 * cfg["sondeo_s"], 3.0)  # resolucion de dos series muestreadas a ~1 Hz
    filas = sorted((f for f in energia if ref - MARGEN_ENERGIA_S <= f["epoch"] <= fin), key=lambda x: x["epoch"])
    if not filas:
        return {"causa": "sin_enchufe", "texto": "sin lecturas del enchufe en la ventana: no se distingue corte de energia de cuelgue"}
    medidas = [f for f in filas if f.get("ok") is True and _es_num(f.get("potencia_w"))]
    if not medidas:
        return {"causa": "enchufe_mudo", "texto": f"{len(filas)} lecturas del enchufe en la ventana y ninguna con potencia: el enchufe "
                "tambien callo (compatible con un corte de la pared o con el Wi-Fi del enchufe; no concluyente)"}
    # El voltaje solo cuenta en el instante del silencio: un bajon que la ATOM sobrevivio un minuto antes no es la causa.
    bajo_v = [f for f in medidas if _es_num(f.get("voltaje_v")) and f["voltaje_v"] < VOLTAJE_CAIDO_V and ref - tol <= f["epoch"] <= desde + tol]
    if bajo_v:
        f = bajo_v[0]
        return {"causa": "corte_energia", "origen": "pared", "epoch": f["epoch"],
                "texto": f"corte de energia de la pared: el enchufe midio {f['voltaje_v']:g} V a las {_local(f['epoch'])}"}

    def alta(f: Mapping[str, Any]) -> bool:
        return f["potencia_w"] >= CARGA_W

    def baja(f: Mapping[str, Any]) -> bool:
        return f["potencia_w"] < APAGADA_W

    # ~0 W mientras la ATOM respondia, sin consumo entre esa lectura y la respuesta (un arranque SI consume): mide otro aparato.
    for f in medidas:
        if baja(f) and f["epoch"] < ref - tol and not any(alta(g) and f["epoch"] < g["epoch"] <= ref for g in medidas):
            return {"causa": "no_concluyente", "texto": f"el enchufe marco {f['potencia_w']:g} W a las {_local(f['epoch'])} mientras "
                    "la ATOM respondia: ¿mide otro aparato?"}
    # La primera caida a ~0 W desde la ultima respuesta. En un silencio cerrado la potencia VUELVE antes que la red (el arranque
    # consume decenas de segundos antes de que sshd conteste): por eso solo cuenta lo que hay entre el silencio y esa caida.
    b = next((f for f in medidas if baja(f) and f["epoch"] >= ref - tol), None)
    if b is not None and b["epoch"] <= desde + tol:
        v = b.get("voltaje_v")
        origen = "atom_o_adaptador" if v is not None and _es_num(v) and v >= VOLTAJE_NORMAL_V else "sin_voltaje"
        detalle = (f"la pared siguio dando {v:g} V: se corto la ATOM o su adaptador" if origen == "atom_o_adaptador"
                   else "el enchufe no mide voltaje: no se distingue la pared del adaptador")
        return {"causa": "corte_energia", "origen": origen, "epoch": b["epoch"], "texto": f"corte de energia: la potencia cayo a "
                f"{b['potencia_w']:g} W a las {_local(b['epoch'])}, antes o a la vez que el silencio ({_local(desde)}); {detalle}"}
    # El enchufe vive de la misma pared: si la pared se queda sin corriente, el enchufe calla a la vez que la ATOM.
    m = next((f for f in filas if f.get("ok") is not True and f["epoch"] >= ref - tol), None)
    if m is not None and m["epoch"] <= desde + tol and not any(m["epoch"] < f["epoch"] <= desde + tol for f in medidas):
        return {"causa": "enchufe_mudo", "epoch": m["epoch"], "texto": f"el enchufe callo a la vez que la ATOM ({_local(m['epoch'])}): "
                "lo mas probable es un corte de la pared (el enchufe vive de ella), pero tambien puede ser su Wi-Fi; no concluyente"}
    tope = math.inf if b is None else b["epoch"]
    altas = [f for f in medidas if alta(f) and desde + tol < f["epoch"] < tope]
    if altas and b is not None:
        return {"causa": "apagado_tras_silencio", "epoch": b["epoch"], "texto": f"cuelgue y despues apagado o reinicio: la ATOM "
                f"dejo de responder a las {_local(desde)} consumiendo y la potencia cayo {b['epoch'] - desde:.0f} s despues"}
    if altas:
        ult = altas[-1]
        return {"causa": "cuelgue", "potencia_w": ult["potencia_w"], "texto": f"cuelgue, no corte de energia: la ATOM dejo de responder a "
                f"las {_local(desde)} y siguio consumiendo {ult['potencia_w']:g} W hasta las {_local(ult['epoch'])}"}
    return {"causa": "no_concluyente", "texto": f"{len(medidas)} lecturas con potencia en la ventana sin patron de corte ni de cuelgue"}


def _ultimo(filas: List[Dict[str, Any]], **igual: Any) -> Optional[Dict[str, Any]]:
    elegidas = [f for f in filas if all(f.get(k) == v for k, v in igual.items())]
    return max(elegidas, key=lambda x: x["epoch"]) if elegidas else None


def veredicto(ping: List[Dict[str, Any]], energia: List[Dict[str, Any]], latido: List[Dict[str, Any]],
              cfg: Mapping[str, Any], ahora: float) -> Dict[str, Any]:
    """El estado presente y el ultimo silencio. Sin latido fresco NO se concluye que la ATOM este caida."""
    lat = _ultimo(latido, evento="latido")
    edad_latido = None if lat is None else ahora - lat["epoch"]
    eps = episodios(ping)
    ep = eps[-1] if eps else None
    out: Dict[str, Any] = {"latido_edad_s": edad_latido, "ultima_respuesta_epoch": None}
    resp = [f["epoch"] for f in ping if _responde(f)]
    if resp:
        out["ultima_respuesta_epoch"] = max(resp)
    if ep is not None and ep["hasta"] is not None:
        out["episodio_anterior"] = {**ep, **causa_ventana(ep, energia, cfg)}
    fin = _ultimo(latido)
    parado = fin is not None and fin.get("evento") == "parada" and (lat is None or fin["epoch"] >= lat["epoch"])
    if edad_latido is None or edad_latido > max(3.0 * cfg["latido_s"], 30.0) or parado:
        cuando = ("nunca latio" if edad_latido is None else f"se detuvo limpiamente a las {_local(fin['epoch'])}" if parado and fin is not None
                  else f"su ultimo latido fue hace {edad_latido:.0f} s")
        return {**out, "codigo": "testigo_sin_latido", "texto": f"el testigo no esta corriendo ({cuando}): sus filas no prueban "
                "nada sobre la ATOM; arrancalo y vuelve a mirar"}
    if not ping:
        return {**out, "codigo": "sin_sondeos", "texto": "el testigo late pero no hay ningun sondeo registrado"}
    ultimo = max(ping, key=lambda x: x["epoch"])
    if ahora - ultimo["epoch"] > 3.0 * cfg["sondeo_s"] + cfg["tcp_timeout_s"] + 10.0:
        return {**out, "codigo": "sondeo_detenido", "texto": f"el ultimo sondeo fue hace {ahora - ultimo['epoch']:.0f} s: el hilo "
                "de sondeo no avanza (mira `errores` en latido.jsonl)"}
    if ultimo.get("estado") == "sin_red":
        return {**out, "codigo": "red_del_testigo", "texto": "el propio testigo no tiene red: no se concluye nada sobre la ATOM"}
    if out["ultima_respuesta_epoch"] is None:  # nunca respondio: no hay un «antes» con el que fechar un corte
        return {**out, "codigo": "sin_respuesta_registrada", "texto": "la ATOM no respondio ni una vez en lo registrado "
                "(¿esta apagada, o atom_host esta mal?)" + _resumen_energia(energia)}
    if ep is None or ep["hasta"] is not None:
        return {**out, "codigo": "atom_responde", "texto": f"la ATOM responde (ultima respuesta {_local(out['ultima_respuesta_epoch'])})"}
    causa = causa_ventana(ep, energia, cfg)
    return {**out, **causa, "codigo": "atom_callada", "desde_epoch": ep["desde"], "fallos": ep["fallos"],
            "texto": f"la ATOM dejo de responder a las {_local(ep['desde'])} ({ep['fallos']} sondeos sin respuesta; ultima respuesta "
                     f"{_local(ep['ultima_respuesta'])}). Ventana: {causa['texto']}"}


def _resumen_energia(energia: List[Dict[str, Any]]) -> str:
    f = _ultimo([x for x in energia if x.get("ok") is True and _es_num(x.get("potencia_w"))])
    if f is None:
        return ""
    if f["potencia_w"] < APAGADA_W:
        return f"; el enchufe marca {f['potencia_w']:g} W: la ATOM no consume (apagada o sin corriente)"
    return f"; el enchufe marca {f['potencia_w']:g} W: consume sin responder"


def _hace(ahora: float, t: Optional[float]) -> str:
    return "nunca" if t is None else f"hace {max(0.0, ahora - t):.0f} s ({_local(t)})"


def estado(datos: Path, ahora: Optional[float] = None) -> Dict[str, Any]:
    """Lo ultimo de cada serie mas el veredicto. Sin testigo.json usa DEFECTOS para las edades (status nunca exige config)."""
    ahora = time.time() if ahora is None else ahora
    try:
        cfg = carga_config(datos / "testigo.json")
    except ValueError:
        cfg = dict(DEFECTOS)
    series = {n: lee_filas(datos / f"{n}.jsonl") for n in ARCHIVOS}
    v = veredicto(series["ping"], series["energia"], series["latido"], cfg, ahora)
    return {"datos": str(datos), "atom_host": cfg.get("atom_host") or None, "ahora_epoch": ahora, "veredicto": v,
            "ultimo_latido": _ultimo(series["latido"]), "ultimo_tcp": _ultimo(series["ping"], fuente="tcp"),
            "ultimo_icmp": _ultimo(series["ping"], fuente="icmp"), "ultimo_enchufe": _ultimo(series["energia"]),
            "datagramas_en_cola": len(series["netconsole"]), "ultimos_datagramas": series["netconsole"][-5:]}


def texto_estado(e: Mapping[str, Any]) -> str:
    ahora, v = e["ahora_epoch"], e["veredicto"]
    lat, tcp, icmp, ench = e["ultimo_latido"], e["ultimo_tcp"], e["ultimo_icmp"], e["ultimo_enchufe"]
    lineas = [f"bb-testigo · datos en {e['datos']} · ATOM: {e['atom_host'] or '(sin configurar)'}",
              f"  Latido del testigo: {_hace(ahora, lat and lat['epoch'])}" + (f" · ultima fila: {lat.get('evento')}" if lat else "")]
    if lat and lat.get("errores"):
        lineas.append(f"  Errores de hilos: {json.dumps(lat['errores'], ensure_ascii=False)}")
    if tcp:
        lineas.append(f"  TCP {tcp.get('destino')}:{tcp.get('puerto')}: {tcp.get('estado')} {_hace(ahora, tcp['epoch'])}")
    if icmp:
        lineas.append(f"  ICMP: {icmp.get('estado')} {_hace(ahora, icmp['epoch'])}")
    lineas.append(f"  Ultima respuesta de la ATOM: {_hace(ahora, v.get('ultima_respuesta_epoch'))}")
    if ench:
        medida = f"{ench.get('potencia_w')} W, {ench.get('voltaje_v')} V" if ench.get("ok") else f"sin lectura ({ench.get('error')})"
        lineas.append(f"  Enchufe: {medida} {_hace(ahora, ench['epoch'])}")
    ult = e["ultimos_datagramas"]
    lineas.append(f"  UDP: {e['datagramas_en_cola']} datagramas en la cola; ultimo {_hace(ahora, ult[-1]['epoch'] if ult else None)}")
    for d in ult:
        lineas.append(f"    {_local(d['epoch'])} {d.get('origen')}: {(d.get('texto') or '<binario>')[:150]}")
    lineas.append(f"VEREDICTO: {v['codigo'].upper()} — {v['texto']}")
    if v.get("episodio_anterior"):
        a = v["episodio_anterior"]
        lineas.append(f"  Ultimo silencio cerrado: {_local(a['desde'])} -> {_local(a['hasta'])} ({a['hasta'] - a['desde']:.0f} s): "
                      f"{a['causa'].upper()} — {a['texto']}")
    return "\n".join(lineas)


# --- install / uninstall -------------------------------------------------------------------------------------------------

Accion = Tuple[Any, ...]  # ("escribe", ruta, bytes) | ("copia", origen, destino) | ("ejecuta", argv, tolera_fallo) | ("borra", ruta)
#                           | ("borra_dir", ruta) | ("aviso", texto)


def rutas_servicio(sistema: str, datos: Path, env: Mapping[str, str]) -> Dict[str, Path]:
    h = _home(env)
    cfg_dir = Path(env["XDG_CONFIG_HOME"]) if env.get("XDG_CONFIG_HOME") else h / ".config"
    return {"datos": datos, "config": datos / "testigo.json", "script": datos / "bb_testigo.py",
            "unidad": cfg_dir / "systemd" / "user" / UNIDAD_SYSTEMD,
            "plist": h / "Library" / "LaunchAgents" / f"{ETIQUETA_LAUNCHD}.plist", "xml": datos / "bb-testigo-tarea.xml"}


def _arg_systemd(s: str) -> str:
    # ExecStart expande %especificadores y $VARIABLES: se duplican para que una ruta rara llegue literal.
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%").replace("$", "$$") + '"'


def unidad_systemd(python: str, script: str, datos: str) -> str:
    exe = " ".join(_arg_systemd(x) for x in (python, script)) + " run --datos " + _arg_systemd(datos)
    return ("[Unit]\n"
            "Description=bb-testigo: testigo externo de la ATOM (UDP, sondeo TCP/ICMP, enchufe, latido)\n"
            "StartLimitIntervalSec=0\n\n"
            "[Service]\nType=simple\n"
            f"ExecStart={exe}\n"
            "Restart=always\nRestartSec=5\nEnvironment=PYTHONUNBUFFERED=1\nMemoryMax=256M\n\n"
            "[Install]\nWantedBy=default.target\n")


def plist_launchd(python: str, script: str, datos: str) -> bytes:
    return plistlib.dumps({"Label": ETIQUETA_LAUNCHD, "ProgramArguments": [python, script, "run", "--datos", datos],
                           "RunAtLoad": True, "KeepAlive": True, "ThrottleInterval": 10,
                           "StandardOutPath": str(Path(datos) / "launchd.log"), "StandardErrorPath": str(Path(datos) / "launchd.log")})


def tarea_windows_xml(pythonw: str, script: str, datos: str, usuario: str) -> str:
    """XML de Task Scheduler. Va por /XML y no por /SC ONLOGON porque esa via deja dos trampas: la tarea se mata a las 72 h
    (ExecutionTimeLimit) y no arranca con el portatil en bateria (DisallowStartIfOnBatteries)."""
    uid = f"<UserId>{escape(usuario)}</UserId>" if usuario else ""
    args = f'"{script}" run --datos "{datos}"'
    return ('<?xml version="1.0" encoding="UTF-16"?>\n'
            '<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
            "  <RegistrationInfo><Description>bb-testigo: testigo externo de la ATOM</Description></RegistrationInfo>\n"
            f"  <Triggers><LogonTrigger><Enabled>true</Enabled>{uid}</LogonTrigger></Triggers>\n"
            f'  <Principals><Principal id="Author">{uid}<LogonType>InteractiveToken</LogonType>'
            "<RunLevel>LeastPrivilege</RunLevel></Principal></Principals>\n"
            "  <Settings>\n"
            "    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n"
            "    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n"
            "    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>\n"
            "    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>\n"
            "    <StartWhenAvailable>true</StartWhenAvailable>\n"
            "    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>\n"
            "    <IdleSettings><StopOnIdleEnd>false</StopOnIdleEnd><RestartOnIdle>false</RestartOnIdle></IdleSettings>\n"
            "    <RestartOnFailure><Interval>PT1M</Interval><Count>999</Count></RestartOnFailure>\n"
            "    <Enabled>true</Enabled>\n"
            "  </Settings>\n"
            f'  <Actions Context="Author"><Exec><Command>{escape(pythonw)}</Command><Arguments>{escape(args)}</Arguments></Exec></Actions>\n'
            "</Task>\n")


def regla_firewall(puerto: int) -> str:
    return f"bb-testigo-udp-{puerto}"  # sin espacios: netsh no depende de como se citen los argumentos


def es_wsl(osrelease: str) -> bool:
    return "microsoft" in osrelease.lower()


def plan_install(sistema: str, cfg: Mapping[str, Any], rutas: Mapping[str, Path], python: str, script_origen: Path,
                 env: Mapping[str, str], uid: Optional[int] = None, osrelease: str = "",
                 which: Callable[[str], Optional[str]] = shutil.which) -> List[Accion]:
    """Lo que `install` hace, como datos: --dry-run lo imprime y la instalacion real lo ejecuta en orden."""
    script, datos, puerto = str(rutas["script"]), str(rutas["datos"]), cfg["udp_puerto"]
    plan: List[Accion] = []
    if sistema == "linux" and es_wsl(osrelease):
        plan.append(("aviso", "esto es WSL2: su NAT NO recibe UDP entrante de la LAN, asi que netconsole no llegaria. Instala el "
                     "testigo con el Python NATIVO de Windows (python.org), no dentro de WSL."))
    plan += [("escribe", rutas["config"], (json.dumps(dict(cfg), indent=2, ensure_ascii=False) + "\n").encode("utf-8")),
             ("copia", script_origen, rutas["script"])]
    if sistema == "linux":
        plan += [("escribe", rutas["unidad"], unidad_systemd(python, script, datos).encode("utf-8")),
                 ("ejecuta", ["systemctl", "--user", "daemon-reload"], False),
                 ("ejecuta", ["systemctl", "--user", "enable", UNIDAD_SYSTEMD], False),
                 ("ejecuta", ["systemctl", "--user", "restart", UNIDAD_SYSTEMD], False),
                 ("aviso", "para que corra aunque nadie haya iniciado sesion: loginctl enable-linger")]
        if which("ufw"):
            plan.append(("aviso", f"si ufw esta activo, abre el puerto (pide sudo): sudo ufw allow {puerto}/udp"))
        if which("firewall-cmd"):
            plan.append(("aviso", f"si firewalld esta activo (pide sudo): sudo firewall-cmd --permanent --add-port={puerto}/udp "
                         "&& sudo firewall-cmd --reload"))
    elif sistema == "darwin":
        dominio = f"gui/{os.getuid() if uid is None else uid}"
        plan += [("escribe", rutas["plist"], plist_launchd(python, script, datos)),
                 ("ejecuta", ["launchctl", "bootout", f"{dominio}/{ETIQUETA_LAUNCHD}"], True),
                 ("ejecuta", ["launchctl", "bootstrap", dominio, str(rutas["plist"])], False),
                 ("aviso", "si macOS pregunta si Python puede aceptar conexiones entrantes o usar la red local, responde Permitir")]
    elif sistema == "win32":
        usuario = "\\".join(x for x in (env.get("USERDOMAIN", ""), env.get("USERNAME", "")) if x)
        regla = regla_firewall(puerto)
        xml = tarea_windows_xml(python, script, datos, usuario).encode("utf-16")
        plan += [("aviso", "la tarea de inicio de sesion y la regla del firewall piden una terminal de ADMINISTRADOR"),
                 ("escribe", rutas["xml"], xml),
                 ("ejecuta", ["schtasks", "/Create", "/TN", TAREA_WINDOWS, "/XML", str(rutas["xml"]), "/F"], False),
                 ("ejecuta", ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={regla}"], True),
                 ("ejecuta", ["netsh", "advfirewall", "firewall", "add", "rule", f"name={regla}", "dir=in", "action=allow",
                              "protocol=UDP", f"localport={puerto}"], False),
                 ("ejecuta", ["schtasks", "/End", "/TN", TAREA_WINDOWS], True),
                 ("ejecuta", ["schtasks", "/Run", "/TN", TAREA_WINDOWS], False)]
    else:
        raise ValueError(f"sistema '{sistema}' sin instalador: corre `run` a mano")
    plan.append(("aviso", "un equipo dormido no es testigo: desactiva la suspension mientras este enchufado"))
    return plan


def plan_uninstall(sistema: str, rutas: Mapping[str, Path], puerto: int, borrar_datos: bool, uid: Optional[int] = None) -> List[Accion]:
    plan: List[Accion] = []
    if sistema == "linux":
        plan += [("ejecuta", ["systemctl", "--user", "disable", "--now", UNIDAD_SYSTEMD], True), ("borra", rutas["unidad"]),
                 ("ejecuta", ["systemctl", "--user", "daemon-reload"], True)]
    elif sistema == "darwin":
        dominio = f"gui/{os.getuid() if uid is None else uid}"
        plan += [("ejecuta", ["launchctl", "bootout", f"{dominio}/{ETIQUETA_LAUNCHD}"], True), ("borra", rutas["plist"])]
    elif sistema == "win32":
        plan += [("ejecuta", ["schtasks", "/End", "/TN", TAREA_WINDOWS], True),
                 ("ejecuta", ["schtasks", "/Delete", "/TN", TAREA_WINDOWS, "/F"], True),
                 ("ejecuta", ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={regla_firewall(puerto)}"], True),
                 ("borra", rutas["xml"])]
    else:
        raise ValueError(f"sistema '{sistema}' sin instalador")
    plan += [("borra", rutas["script"]), ("borra", rutas["config"]), ("borra", rutas["datos"] / "testigo.lock")]
    if borrar_datos:
        plan.append(("borra_dir", rutas["datos"]))
    else:
        plan.append(("aviso", f"los datos (la evidencia) se conservan en {rutas['datos']}; --borrar-datos los borra"))
    return plan


def _contenido(b: bytes) -> str:
    return b.decode("utf-16") if b[:2] in (b"\xff\xfe", b"\xfe\xff") else b.decode("utf-8", errors="replace")


def _cmd(argv: List[Any], windows: bool = False) -> str:
    """El comando como se escribiria en la terminal de ese sistema (solo para mostrarlo: se ejecuta como lista)."""
    return subprocess.list2cmdline([str(x) for x in argv]) if windows else " ".join(shlex.quote(str(x)) for x in argv)


def ejecuta_plan(plan: List[Accion], dry_run: bool, correr: Correr = subprocess.run, out: Callable[[str], None] = print,
                 windows: bool = False) -> int:
    """Ejecuta en orden; para en el primer fallo no tolerado (rc 1). En --dry-run solo imprime: no toca disco ni procesos."""
    for a in plan:
        tipo = a[0]
        if tipo == "aviso":
            out(f"AVISO: {a[1]}")
            continue
        if dry_run:
            if tipo == "escribe":
                out(f"[dry-run] escribiria {a[1]} ({len(a[2])} bytes):\n" + "\n".join(f"    {ln}" for ln in _contenido(a[2]).splitlines()))
            elif tipo == "copia":
                out(f"[dry-run] copiaria {a[1]} -> {a[2]}")
            elif tipo == "ejecuta":
                out(f"[dry-run] ejecutaria: {_cmd(a[1], windows)}" + ("  (se tolera que falle)" if a[2] else ""))
            else:
                out(f"[dry-run] borraria {a[1]}" + (" (el directorio entero)" if tipo == "borra_dir" else ""))
            continue
        try:
            if tipo == "escribe":
                a[1].parent.mkdir(parents=True, exist_ok=True)
                a[1].write_bytes(a[2])
                out(f"escrito {a[1]}")
            elif tipo == "copia":
                if not (a[2].exists() and os.path.samefile(a[1], a[2])):
                    a[2].parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(a[1], a[2])
                out(f"copiado {a[1]} -> {a[2]}")
            elif tipo == "borra":
                try:
                    a[1].unlink()
                    out(f"borrado {a[1]}")
                except FileNotFoundError:
                    pass
            elif tipo == "borra_dir":
                if a[1].name == APP and a[1].is_dir():  # nunca un directorio que no sea el del testigo
                    shutil.rmtree(a[1])
                    out(f"borrado {a[1]}")
            elif tipo == "ejecuta":
                r = correr([str(x) for x in a[1]], capture_output=True, text=True, check=False, timeout=120)
                if r.returncode != 0:
                    detalle = ((r.stderr or "") + (r.stdout or "")).strip()[:300]
                    out(f"{'aviso' if a[2] else 'ERROR'}: rc {r.returncode} de {_cmd(a[1], windows)}: {detalle}")
                    if not a[2]:
                        return 1
                else:
                    out(f"ok: {_cmd(a[1], windows)}")
        except (OSError, subprocess.SubprocessError) as e:
            out(f"{'aviso' if tipo == 'ejecuta' and a[2] else 'ERROR'}: {tipo} {a[1]}: {type(e).__name__}: {e}")
            if not (tipo == "ejecuta" and a[2]):
                return 1
    return 0


# --- linea de comandos ---------------------------------------------------------------------------------------------------


def _datos_de(a: argparse.Namespace, sistema: Optional[str] = None, env: Optional[Mapping[str, str]] = None) -> Path:
    return Path(a.datos) if a.datos else dir_datos(sistema, env)


def _cmd_run(a: argparse.Namespace) -> int:
    datos = _datos_de(a)
    try:
        cfg = carga_config(datos / "testigo.json")
    except ValueError as e:
        print(f"bb-testigo: {e}", file=sys.stderr)
        return 2
    bloqueo = toma_bloqueo(datos / "testigo.lock")
    if bloqueo is None:
        print(f"bb-testigo: ya corre otra instancia sobre {datos}", file=sys.stderr)
        return 3
    t = Testigo(cfg, datos)
    previo = None
    try:
        previo = signal.signal(signal.SIGTERM, lambda *_: t.parar.set())  # systemd y launchd paran con SIGTERM
    except (ValueError, OSError):  # fuera del hilo principal no hay senales: Ctrl+C y --duracion siguen valiendo
        pass
    try:
        t.corre(a.duracion)
    except OSError as e:
        print(f"bb-testigo: no se pudo escuchar UDP {cfg['udp_bind']}:{cfg['udp_puerto']} ({e}); ¿otro programa usa el puerto?",
              file=sys.stderr)
        return 2
    finally:
        bloqueo.close()
        if previo is not None:
            signal.signal(signal.SIGTERM, previo)
    return 0


def _cmd_status(a: argparse.Namespace) -> int:
    e = estado(_datos_de(a))
    print(json.dumps(e, ensure_ascii=False, indent=2) if a.json else texto_estado(e))
    return 0


def _osrelease() -> str:
    try:
        return Path("/proc/sys/kernel/osrelease").read_text(encoding="utf-8")
    except OSError:
        return ""


def _python_servicio(python: str, sistema: str) -> str:
    # En Windows, pythonw.exe (junto a python.exe) corre sin abrir una consola que el usuario cerraria sin querer.
    if sistema == "win32" and python.lower().endswith("python.exe"):
        w = python[: -len("python.exe")] + "pythonw.exe"
        if os.path.exists(w):
            return w
    return python


def _cmd_install(a: argparse.Namespace, env: Mapping[str, str], correr: Correr) -> int:
    nativo = sistema_actual()
    sistema = a.sistema or nativo
    if sistema != nativo and not a.dry_run:
        print(f"bb-testigo: --sistema {sistema} en un equipo {nativo} solo se acepta con --dry-run", file=sys.stderr)
        return 2
    datos = _datos_de(a, sistema, env)
    rutas = rutas_servicio(sistema, datos, env)
    try:
        previo = json.loads(rutas["config"].read_text(encoding="utf-8"))  # reinstalar conserva lo configurado
    except (OSError, ValueError):
        previo = {}
    cfg: Dict[str, Any] = {**DEFECTOS, **{k: v for k, v in (previo if isinstance(previo, dict) else {}).items() if k in DEFECTOS}}
    flags = {"atom_host": a.host, "atom_puerto": a.puerto_atom, "udp_puerto": a.udp_puerto, "enchufe_tipo": a.enchufe_tipo,
             "enchufe_url": a.enchufe_url, "sondeo_s": a.sondeo_s, "latido_s": a.latido_s}
    cfg.update({k: v for k, v in flags.items() if v is not None})
    if not cfg["atom_host"] and not a.no_preguntar and sys.stdin.isatty():
        cfg["atom_host"] = input("IP de la ATOM en la red de casa (p. ej. 192.168.x.y): ").strip()
        if not cfg["enchufe_tipo"]:
            tipo = input(f"Enchufe con medidor ({'/'.join(TIPOS_ENCHUFE)}; Enter si no hay): ").strip().lower()
            if tipo:
                cfg["enchufe_tipo"] = tipo
                cfg["enchufe_url"] = input("URL del enchufe (p. ej. http://192.168.x.z): ").strip()
    try:
        cfg = valida_config(cfg)
        plan = plan_install(sistema, cfg, rutas, _python_servicio(a.python or sys.executable, sistema),
                            Path(__file__).resolve(), env, osrelease=_osrelease() if sistema == nativo == "linux" else "")
    except ValueError as e:
        print(f"bb-testigo: {e}", file=sys.stderr)
        return 2
    rc = ejecuta_plan(plan, a.dry_run, correr, windows=sistema == "win32")
    if rc == 0 and not a.dry_run:
        print(f"Instalado. En un minuto comprueba con:\n  {_cmd([a.python or sys.executable, rutas['script'], 'status'], sistema == 'win32')}")
    return rc


def _cmd_uninstall(a: argparse.Namespace, env: Mapping[str, str], correr: Correr) -> int:
    nativo = sistema_actual()
    sistema = a.sistema or nativo
    if sistema != nativo and not a.dry_run:
        print(f"bb-testigo: --sistema {sistema} en un equipo {nativo} solo se acepta con --dry-run", file=sys.stderr)
        return 2
    datos = _datos_de(a, sistema, env)
    rutas = rutas_servicio(sistema, datos, env)
    try:
        puerto = carga_config(rutas["config"])["udp_puerto"]
    except ValueError:
        puerto = DEFECTOS["udp_puerto"]
    try:
        plan = plan_uninstall(sistema, rutas, puerto, a.borrar_datos)
    except ValueError as e:
        print(f"bb-testigo: {e}", file=sys.stderr)
        return 2
    return ejecuta_plan(plan, a.dry_run, correr, windows=sistema == "win32")


def main(argv: Optional[List[str]] = None, env: Optional[Mapping[str, str]] = None, correr: Correr = subprocess.run) -> int:
    ap = argparse.ArgumentParser(prog="bb_testigo.py", description="Testigo externo de la ATOM (ver LEEME.md).")
    sub = ap.add_subparsers(dest="orden")
    p = sub.add_parser("run", help="corre el testigo (lo arranca el servicio que deja `install`)")
    p.add_argument("--datos", help="directorio de datos (por defecto el de la plataforma)")
    p.add_argument("--duracion", type=float, help="segundos y salir (pruebas); sin esto corre hasta SIGTERM o Ctrl+C")
    p = sub.add_parser("status", help="lo ultimo recibido y sondeado, el latido y el veredicto de ventana")
    p.add_argument("--datos")
    p.add_argument("--json", action="store_true", help="salida JSON en vez de texto")
    for nombre in ("install", "uninstall"):
        p = sub.add_parser(nombre, help="instala el servicio de usuario" if nombre == "install" else "deshace `install`")
        p.add_argument("--datos")
        p.add_argument("--sistema", choices=("linux", "darwin", "win32"), help="otra plataforma (solo con --dry-run)")
        p.add_argument("--dry-run", action="store_true", help="imprime lo que haria sin escribir ni ejecutar nada")
        if nombre == "uninstall":
            p.add_argument("--borrar-datos", action="store_true", help="borra tambien la evidencia recogida")
            continue
        p.add_argument("--host", help="IP (o nombre) de la ATOM")
        p.add_argument("--puerto-atom", type=int, help="puerto TCP que se sondea (22)")
        p.add_argument("--udp-puerto", type=int, help="puerto UDP que se escucha (6666)")
        p.add_argument("--enchufe-tipo", choices=TIPOS_ENCHUFE)
        p.add_argument("--enchufe-url", help="http://<ip-del-enchufe>")
        p.add_argument("--sondeo-s", type=float)
        p.add_argument("--latido-s", type=float)
        p.add_argument("--python", help="interprete que usara el servicio (por defecto el actual)")
        p.add_argument("--no-preguntar", action="store_true", help="no hace preguntas: todo por flags")
    a = ap.parse_args(argv)
    env = os.environ if env is None else env
    if a.orden == "run":
        return _cmd_run(a)
    if a.orden == "status":
        return _cmd_status(a)
    if a.orden == "install":
        return _cmd_install(a, env, correr)
    if a.orden == "uninstall":
        return _cmd_uninstall(a, env, correr)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
