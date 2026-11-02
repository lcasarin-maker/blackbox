#!/usr/bin/env python3
"""Observador externo de ping (interruptor `observador_ping`): FEATURE-OBSERVADOR-EXTERNO-DE-REINICIOS-01, parte construible aqui.

Una lectura por ejecucion (la repeticion de 1 s es de `systemd/bb-observador-ping.timer`, sin bucles ni `sleep`): un ping a la ATOM
desde OTRO equipo, con una fila en `$BLACKBOX_DATA/externo/ping.jsonl`. Un ping que corre en la ATOM muere con ella y no prueba nada.
Aporta la hora de la ULTIMA respuesta de la maquina con precision de ~1 s, independiente del journal (que se corta sin cierre), y separa
"la maquina murio" de "el journal calla pero la red responde". `ultima_respuesta` y `primera_falla` las lee `reboot_verdict`
al cruzar el hueco de un corte: entre las dos queda acotada la hora en que la ATOM dejo de responder.
Configuracion: `$BLACKBOX_DATA/externo/observador.json` = {"destino": "<ip o nombre de la ATOM>"}.

Variante NAS (`--sync`): el observador es `adopted/nas/bb-ping-atom.sh` en el QNAP (una linea `<epoch> ok|fail` por segundo). `sync` TRAE ese
log con `smbclient` y lo mezcla en `ping.jsonl` (fuente "nas", clave epoch: repetir el sync no duplica). Configuracion:
`$BLACKBOX_DATA/externo/nas.json` = {"host", "share", "ruta", "credenciales": "<archivo con usuario y clave, modo 600>"}; la clave nunca se lee
aqui (la lee smbclient con `-A`) ni se imprime. Tres estados: OK, OBSOLETO (el log del NAS no avanza) y NOT_COLLECTED (nada se pudo traer:
`ping.jsonl` queda intacto); un log ausente nunca se lee como "sin huecos". Estado de la ultima corrida en `externo/sync.json`.

Testigo (`--trae-testigo`, 2026-11-01): `tools/testigo/bb_testigo.py` escribe en el directorio de datos de OTRO equipo, y lo que
vio solo sirve si llega a la ATOM despues del corte. La ATOM lo TRAE por `scp` (OpenSSH: `sshd` del equipo testigo, que existe en
Linux, en macOS como «Sesion remota» y en Windows como «Servidor OpenSSH»); en la ATOM no se abre nada, solo sale una conexion.
Configuracion: `$BLACKBOX_DATA/externo/testigo.json` = {"origen": "<usuario>@<ip-del-testigo>", "ruta": "<directorio de datos
del testigo>"} con la llave de `ssh` del usuario ya aceptada en el testigo (`BatchMode`: nunca pide clave). Copia `*.jsonl*`
(las cuatro series y sus rotaciones, tal cual) a `externo/testigo/`: los nombres y campos son los del testigo y nadie los
traduce. Lo corre `bb-reboot-verdict.service` como `ExecStartPre`, una vez por arranque y justo antes del veredicto, que es el
unico que lo lee. Costo declarado: copia completa cada vez (a lo sumo `rota_copias + 1` archivos de `rota_mb` por serie).
Estado de la ultima corrida en `externo/testigo/trae.json`; sin `testigo.json` es NOT_COLLECTED y no toca nada.

`ok` significa lo mismo en las tres fuentes de `ping.jsonl` (observador, NAS y testigo): «la ATOM contesto»; en el testigo un
RST (`estado: rechazado`) tambien es `ok`. Una fila `estado: sin_red` es la red del propio testigo caida: no es respuesta ni
falla de la ATOM, y `ultima_respuesta`/`primera_falla` la saltan como lo hace `bb_testigo.episodios`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

from tools import interruptores

NOMBRE = "observador_ping"
Correr = Callable[..., Any]


def _datos() -> Path:
    return Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox")) / "externo"


def sondea(destino: str, correr: Correr = subprocess.run) -> dict[str, Any]:
    """Un ping de 1 intento y 1 s de espera. `ok` es rc 0; no se interpreta nada mas (un fallo puede ser la red del observador)."""
    try:
        r = correr(["ping", "-c", "1", "-W", "1", destino], capture_output=True, text=True, check=False, timeout=5)
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "error": type(e).__name__}
    return {"ok": r.returncode == 0}


def paso(modo_actual: str, destino: str, ruta: Path, correr: Correr = subprocess.run, ahora: float | None = None) -> dict[str, Any] | None:
    """Una fila en `ping.jsonl`. `off` no sondea."""
    if modo_actual == "off":
        return None
    t = datetime.now(timezone.utc).timestamp() if ahora is None else ahora
    fila = {"ts": datetime.fromtimestamp(t, timezone.utc).isoformat(), "epoch": t, **sondea(destino, correr)}
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(fila) + "\n")
    return fila


def _filas_ping(rutas: Path | Sequence[Path]) -> list[dict[str, Any]]:
    """Filas con `ok` booleano y `epoch` numerico de una o varias series; un archivo ilegible no aporta filas (sin cobertura).
    `sin_red` (la red del testigo) se descarta aqui: no dice nada de la ATOM."""
    filas: list[dict[str, Any]] = []
    for ruta in [rutas] if isinstance(rutas, Path) else rutas:
        try:
            lineas = ruta.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for ln in lineas:
            try:
                f = json.loads(ln)
            except ValueError:
                continue
            if (isinstance(f, dict) and isinstance(f.get("ok"), bool) and isinstance(f.get("epoch"), (int, float))
                    and f.get("estado") != "sin_red"):
                filas.append(f)
    return filas


def ultima_respuesta(rutas: Path | Sequence[Path], hasta: float) -> float | None:
    """Epoch de la ultima fila `ok` anterior o igual a `hasta` entre todas las series; None si no hay ninguna (sin cobertura)."""
    oks = [float(f["epoch"]) for f in _filas_ping(rutas) if f["ok"] is True and f["epoch"] <= hasta]
    return max(oks) if oks else None


def primera_falla(rutas: Path | Sequence[Path], desde: float, hasta: float) -> float | None:
    """Epoch de la primera fila con `ok` false en (desde, hasta]; None si no hay ninguna. Es la prueba de que el observador
    seguia vivo despues de `desde`: sin ella, la ausencia de respuestas es ausencia de filas, no un corte medido."""
    fallas = [float(f["epoch"]) for f in _filas_ping(rutas) if f["ok"] is False and desde < f["epoch"] <= hasta]
    return min(fallas) if fallas else None


LINEA_NAS = re.compile(r"(\d{10}) (ok|fail)")
OBSOLETO_S = 900.0
CLAVES_NAS = ("host", "share", "ruta", "credenciales")


def _trae(cfg: dict[str, Any], destino: Path, correr: Correr) -> str | None:
    """Baja el log del NAS a `destino` con smbclient; None si lo logro, o el motivo (sin credenciales ni salida de smbclient)."""
    for k in CLAVES_NAS:
        if not isinstance(cfg.get(k), str) or not cfg[k] or '"' in cfg[k] or "\n" in cfg[k]:
            return f"nas.json: falta o es invalido '{k}'"
    cred = Path(cfg["credenciales"])
    try:
        modo = stat.S_IMODE(cred.stat().st_mode)
    except OSError:
        return "archivo de credenciales ilegible"
    if modo & 0o077:
        return f"credenciales con modo {modo:o}: exige 600"
    cmd = ["smbclient", f"//{cfg['host']}/{cfg['share']}", "-A", str(cred), "-c", f'get "{cfg["ruta"]}" "{destino}"']
    try:
        r = correr(cmd, capture_output=True, text=True, check=False, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return f"smbclient: {type(e).__name__}"
    if r.returncode != 0:
        return f"smbclient rc {r.returncode}"
    if not destino.exists():
        return "smbclient rc 0 sin archivo"
    return None


def _epochs_nas(ruta: Path) -> set[int]:
    vistos: set[int] = set()
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()
    except OSError:
        return vistos
    for ln in lineas:
        try:
            f = json.loads(ln)
        except ValueError:
            continue
        if isinstance(f, dict) and f.get("fuente") == "nas" and isinstance(f.get("epoch"), (int, float)):
            vistos.add(int(f["epoch"]))
    return vistos


def sync(cfg_ruta: Path, ruta: Path, correr: Correr = subprocess.run, ahora: float | None = None) -> dict[str, Any]:
    """Trae el log del NAS y anade a `ruta` solo las filas cuyo epoch no esta; devuelve {estado, nuevas, descartadas, ...} y lo guarda en sync.json."""
    t = datetime.now(timezone.utc).timestamp() if ahora is None else ahora
    res: dict[str, Any] = {"estado": "NOT_COLLECTED", "nuevas": 0, "descartadas": 0, "epoch": t}
    try:
        cfg = json.loads(cfg_ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = None
    lineas: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        bajado = Path(d) / "nas.log"
        motivo = _trae(cfg, bajado, correr) if isinstance(cfg, dict) else "falta o es ilegible nas.json"
        if motivo is None:
            try:
                lineas = bajado.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                motivo = "log bajado ilegible"
    if motivo is None:
        buenas = {int(m.group(1)): m.group(2) == "ok" for ln in lineas if (m := LINEA_NAS.fullmatch(ln.strip()))}
        res["descartadas"] = sum(1 for ln in lineas if ln.strip() and not LINEA_NAS.fullmatch(ln.strip()))
        if not buenas:
            motivo = "log del NAS sin una sola linea valida"
        else:
            vistos = _epochs_nas(ruta)
            nuevas = sorted(e for e in buenas if e not in vistos)
            if nuevas:
                ruta.parent.mkdir(parents=True, exist_ok=True)
                with ruta.open("a", encoding="utf-8") as fh:
                    for e in nuevas:
                        iso = datetime.fromtimestamp(e, timezone.utc).isoformat()
                        fh.write(json.dumps({"ts": iso, "epoch": e, "ok": buenas[e], "fuente": "nas"}) + "\n")
            res["nuevas"] = len(nuevas)
            res["ultima_epoch_nas"] = max(buenas)
            res["estado"] = "OBSOLETO" if t - max(buenas) > OBSOLETO_S else "OK"
    if motivo is not None:
        res["motivo"] = motivo
    ruta.parent.mkdir(parents=True, exist_ok=True)
    (ruta.parent / "sync.json").write_text(json.dumps(res) + "\n", encoding="utf-8")
    return res


ORIGEN_TESTIGO = re.compile(r"[A-Za-z0-9._-]+@(?:[A-Za-z0-9._-]+|\[[0-9A-Fa-f:]+\])")
PATRON_TESTIGO = "*.jsonl*"  # netconsole, ping, energia y latido con sus rotaciones .1 ... .N (bb_testigo.Diario)


def trae_testigo(cfg_ruta: Path, destino: Path, correr: Correr = subprocess.run, ahora: float | None = None) -> dict[str, Any]:
    """Copia las series del testigo a `destino` con `scp -s` (SFTP: la ruta remota no pasa por un shell, y una ruta con espacios
    como la de macOS llega intacta). Primero a un temporal hermano y luego `os.replace` archivo por archivo: un scp cortado a
    medias no deja una serie truncada en lugar de la buena. Al terminar, `destino` refleja al testigo: lo que el ya roto y
    borro se borra aqui tambien, para no leer dos veces la misma fila. Devuelve {estado, archivos, ...} y lo guarda en trae.json."""
    t = datetime.now(timezone.utc).timestamp() if ahora is None else ahora
    res: dict[str, Any] = {"estado": "NOT_COLLECTED", "archivos": [], "epoch": t}
    try:
        cfg = json.loads(cfg_ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = None
    motivo: str | None = None
    if not isinstance(cfg, dict):
        motivo = f"falta o es ilegible {cfg_ruta.name}"
    elif not isinstance(cfg.get("origen"), str) or not ORIGEN_TESTIGO.fullmatch(cfg["origen"]):
        motivo = f"{cfg_ruta.name}: 'origen' debe ser <usuario>@<host>"
    elif not isinstance(cfg.get("ruta"), str) or not cfg["ruta"].strip() or any(c in cfg["ruta"] for c in "\n\r\"*?["):
        motivo = f"{cfg_ruta.name}: 'ruta' debe ser el directorio de datos del testigo, sin comodines ni comillas"
    if motivo is None and isinstance(cfg, dict):  # motivo None implica cfg dict
        destino.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=destino.parent, prefix=".trae-testigo-") as d:
            fuente = f"{cfg['origen']}:{cfg['ruta'].rstrip('/')}/{PATRON_TESTIGO}"
            cmd = ["scp", "-s", "-q", "-B", "-p", "-o", "ConnectTimeout=10", fuente, d]
            try:
                r = correr(cmd, capture_output=True, text=True, check=False, timeout=120)
                motivo = None if r.returncode == 0 else f"scp rc {r.returncode}"
            except (OSError, subprocess.SubprocessError) as e:
                motivo = f"scp: {type(e).__name__}"
            nuevos = sorted(x.name for x in Path(d).iterdir() if x.is_file()) if motivo is None else []
            if motivo is None and not nuevos:
                motivo = f"scp rc 0 sin archivos {PATRON_TESTIGO}"
            for n in nuevos:
                os.replace(Path(d) / n, destino / n)
        if motivo is None:
            for viejo in destino.glob(PATRON_TESTIGO):
                if viejo.name not in nuevos:
                    viejo.unlink()
            res["archivos"], res["estado"] = nuevos, "OK"
    if motivo is not None:
        res["motivo"] = motivo
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "trae.json").write_text(json.dumps(res, ensure_ascii=False) + "\n", encoding="utf-8")
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="observador_ping")
    ap.add_argument("--paso", action="store_true", help="un ping segun el interruptor observador_ping (lo repite bb-observador-ping.timer)")
    ap.add_argument("--sync", action="store_true", help="trae el log del NAS (nas.json) y lo mezcla en ping.jsonl; lo repite bb-observador-ping-sync.timer")
    ap.add_argument("--trae-testigo", action="store_true", help="copia las series del testigo (testigo.json) a externo/testigo/; lo corre bb-reboot-verdict")
    a = ap.parse_args(argv)
    if a.trae_testigo:
        r = trae_testigo(_datos() / "testigo.json", _datos() / "testigo")
        print(json.dumps(r, ensure_ascii=False))
        return 0 if r["estado"] == "OK" else 1
    if a.sync:
        if interruptores.modo(NOMBRE) == "off":
            print(json.dumps({"estado": "off"}))
            return 0
        r = sync(_datos() / "nas.json", _datos() / "ping.jsonl")
        print(json.dumps(r, ensure_ascii=False))
        return 0 if r["estado"] == "OK" else 1
    if not a.paso:
        ap.print_help()
        return 2
    try:
        destino = str(json.loads((_datos() / "observador.json").read_text(encoding="utf-8"))["destino"])
    except (OSError, ValueError, KeyError):
        print("NOT_COLLECTED: falta $BLACKBOX_DATA/externo/observador.json con {destino}", file=sys.stderr)
        return 1
    print(json.dumps(paso(interruptores.modo(NOMBRE), destino, _datos() / "ping.jsonl"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
