#!/usr/bin/env python3
"""Manejador de las solicitudes al motor de inferencia local (contrato `bb-motor-solicitud/1`).

blackbox es el UNICO actor que arranca, reinicia y para la unidad del motor (voto de Luis,
2026-11-01). El consumidor no la toca: deja una solicitud por archivo y espera la respuesta.
Lo corre `bin/bb-vigilante-motor` al principio de cada vuelta (cada 2 min), asi que el
proceso que reinicia por cuelgue es el mismo que atiende las solicitudes, en serie y bajo un
flock: no hay dos actores sobre la unidad.

Directorio `$BLACKBOX_DATA/motor/`:
- `solicitudes/<id>.json`  las escribe el consumidor (tmp + rename). Al tomarla, bb la
  renombra a `<id>.tomada`: si el consumidor se rinde y la borra antes, bb nunca actua.
- `respuestas/<id>.json`   `aceptada`, `rechazada` (con motivo), `hecha` o `fallida` (con rc).
- `manejador.json`         latido `bb-motor-manejador/1`: `actualizado`, `latido_s` y la
  ventana vigente. Sin latido fresco el consumidor no pide: falla cerrado.
- `ventana.json`           la ventana vigente, si la hay.

Acciones: `arrancar`, `reiniciar`, `parar` y `ventana`. La `ventana` lleva `{duracion_s,
motivo, compensacion}`: mientras dura, el vigilante NO reinicia por su cuenta (las
solicitudes del consumidor si se atienden: son su experimento). Al cerrarla
(`duracion_s: 0`) o al vencer se aplica la compensacion: `arrancar`, o `restaurar` la
config del motor desde una copia que el consumidor deja en su mismo directorio.

Cada accion queda en la salida (el vigilante la anexa a `vigilante_motor.log`) con la
solicitud y su id. Esas lineas no llevan la palabra que `tools/motor_caidas.py` cuenta
como cuelgue: un reinicio pedido no es un cuelgue.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ESQUEMA = "bb-motor-solicitud/1"
ESQUEMA_RESPUESTA = "bb-motor-respuesta/1"
ESQUEMA_MANEJADOR = "bb-motor-manejador/1"
ACCIONES = {"arrancar": "start", "reiniciar": "restart", "parar": "stop", "ventana": None}
# El vigilante corre cada 2 min y una vuelta dura hasta ~4 (sonda de chat de 120 s mas un
# reinicio): 600 s cubre una vuelta perdida sin dar por vivo a un manejador muerto.
LATIDO_S = 600
TOPE_VENTANA_S = 4 * 3600      # una ventana mas larga que la cola del consumidor es un olvido
TOPE_PLAZO_S = 3600
SYSTEMCTL_TIMEOUT_S = 300      # el ExecStop de la unidad es `docker stop -t 30`
RESPUESTAS_DIAS = 7
ID_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


def directorio() -> Path:
    base = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))
    return base / "motor"


def config_motor() -> Path:
    """La config del motor, la misma variable y el mismo default que `bb status`."""
    return Path(os.environ.get("BLACKBOX_MOTOR_CONFIG", "/srv/ai/gateway/active_engine.json"))


def iso(t: datetime) -> str:
    return t.astimezone(timezone.utc).isoformat(timespec="seconds")


def escribe(ruta: Path, texto: str) -> None:
    """Escritura atomica y durable: temporal oculto junto al destino, fsync, rename, fsync del dir."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.parent / f".{ruta.name}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(texto)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, ruta)
    fd = os.open(ruta.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _json(dato: dict) -> str:
    return json.dumps(dato, ensure_ascii=False) + "\n"


def systemctl(verbo: str, unidad: str) -> int:
    try:
        return subprocess.run(["systemctl", "--user", verbo, unidad], capture_output=True,
                              text=True, timeout=SYSTEMCTL_TIMEOUT_S, check=False).returncode
    except subprocess.TimeoutExpired:
        return 124
    except OSError:
        return 127


def _resultado(unidad: str) -> str:
    try:
        return subprocess.run(["systemctl", "--user", "show", "-p", "Result", "--value", unidad],
                              capture_output=True, text=True, timeout=30, check=False).stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        return ""


def ejecuta(accion: str, unidad: str) -> int:
    """El UNICO sitio de bb que actua sobre la unidad por una solicitud. Si systemd aplica
    su limite de arranques, se limpia antes: un arranque pedido no debe chocar contra el."""
    if accion in ("arrancar", "reiniciar") and _resultado(unidad) == "start-limit-hit":
        systemctl("reset-failed", unidad)
    return systemctl(ACCIONES[accion], unidad)


def _lee_iso(texto: object) -> datetime | None:
    if not isinstance(texto, str):
        return None
    try:
        t = datetime.fromisoformat(texto)
    except ValueError:
        return None
    return t if t.tzinfo else None


def _entero(v: object, minimo: int, maximo: int) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) and minimo <= v <= maximo else None


def _motivo_compensacion(c: object) -> str:
    if not isinstance(c, dict) or c.get("accion") not in ("arrancar", "restaurar"):
        return "compensacion debe ser {'accion': 'arrancar'} o {'accion': 'restaurar', 'copia': ...}"
    if c["accion"] == "arrancar":
        return ""
    cfg = config_motor()
    copia = Path(str(c.get("copia", "")))
    if not copia.is_absolute() or copia.resolve().parent != cfg.resolve().parent:
        return f"la copia a restaurar debe vivir junto a {cfg}"
    if copia.resolve() == cfg.resolve() or not copia.is_file():
        return f"la copia {copia} no existe o es la config misma"
    return ""


def valida(sol: object, nombre: str, ahora: datetime) -> str:
    """Motivo de rechazo, o "" si la solicitud se puede atender."""
    if not isinstance(sol, dict) or sol.get("esquema") != ESQUEMA:
        return f"no es {ESQUEMA}"
    if sol.get("id") != nombre or not ID_VALIDO.match(nombre):
        return "id invalido o distinto del nombre del archivo"
    if sol.get("accion") not in ACCIONES:
        return f"accion desconocida {sol.get('accion')!r}"
    if not isinstance(sol.get("origen"), str) or not sol["origen"].strip():
        return "sin origen"
    creada, plazo = _lee_iso(sol.get("creada")), _entero(sol.get("plazo_s"), 1, TOPE_PLAZO_S)
    if creada is None or plazo is None:
        return "creada (ISO con zona) o plazo_s (1..3600) ilegibles"
    if ahora > creada + timedelta(seconds=plazo):
        return f"caducada: el solicitante dejo de esperar a los {plazo} s"
    if sol["accion"] != "ventana":
        return ""
    v = sol.get("ventana")
    if not isinstance(v, dict) or _entero(v.get("duracion_s"), 0, TOPE_VENTANA_S) is None:
        return f"ventana sin duracion_s entera de 0 a {TOPE_VENTANA_S}"
    if not isinstance(v.get("motivo"), str) or not v["motivo"].strip():
        return "ventana sin motivo"
    return _motivo_compensacion(v.get("compensacion")) if v["duracion_s"] else ""


def ventana_vigente(d: Path, ahora: datetime) -> dict | None:
    """La ventana que sigue abierta, o None. Ilegible cuenta como ninguna: un archivo roto
    no puede dejar al motor sin vigilante indefinidamente (lo registra `atender`)."""
    try:
        v = json.loads((d / "ventana.json").read_text(encoding="utf-8"))
        hasta = _lee_iso(v["hasta"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return v if hasta and hasta > ahora else None


def latido(d: Path, unidad: str, ahora: datetime) -> None:
    v = ventana_vigente(d, ahora)
    vista = {k: v[k] for k in ("id", "origen", "motivo", "hasta")} if v else None
    escribe(d / "manejador.json", _json({"esquema": ESQUEMA_MANEJADOR, "actualizado": iso(ahora),
                                         "latido_s": LATIDO_S, "unidad": unidad, "ventana": vista}))


def responde(d: Path, sol_id: str, accion: object, estado: str, **campos: object) -> None:
    escribe(d / "respuestas" / f"{sol_id}.json",
            _json({"esquema": ESQUEMA_RESPUESTA, "id": sol_id, "accion": accion, "estado": estado,
                   **campos, "actualizado": iso(datetime.now(timezone.utc))}))


def compensa(v: dict, unidad: str) -> tuple[int, str]:
    """La compensacion de una ventana que cierra o vence. `restaurar` solo reinicia si la
    config difiere de la copia; si ya es igual (el consumidor la devolvio), basta arrancar,
    que sobre una unidad activa no hace nada: cerrar no cuesta un reinicio doble."""
    c = v.get("compensacion") or {"accion": "arrancar"}
    if c.get("accion") == "restaurar":
        motivo = _motivo_compensacion(c)
        if motivo:
            rc = ejecuta("arrancar", unidad)
            return rc or 1, f"no se pudo restaurar ({motivo}); arrancar rc={rc}"
        cfg, copia = config_motor(), Path(c["copia"])
        texto = copia.read_text(encoding="utf-8")
        if not cfg.is_file() or cfg.read_text(encoding="utf-8") != texto:
            escribe(cfg, texto)
            rc = ejecuta("reiniciar", unidad)
            return rc, f"config restaurada desde {copia}; reiniciar rc={rc}"
        rc = ejecuta("arrancar", unidad)
        return rc, f"config ya igual a {copia}; arrancar rc={rc}"
    rc = ejecuta("arrancar", unidad)
    return rc, f"arrancar rc={rc}"


def cierra(d: Path, unidad: str, porque: str) -> tuple[int, str]:
    """Cierra la ventana (vigente, vencida o ilegible): compensa, la borra y lo anota en la
    respuesta de la solicitud que la abrio."""
    try:
        v = json.loads((d / "ventana.json").read_text(encoding="utf-8"))
        v = v if isinstance(v, dict) else {}
    except (OSError, ValueError):
        v = {}
    rc, det = compensa(v, unidad)
    (d / "ventana.json").unlink(missing_ok=True)
    if isinstance(v.get("id"), str) and ID_VALIDO.match(v["id"]):
        responde(d, v["id"], "ventana", "hecha" if rc == 0 else "fallida", rc=rc,
                 detalle=f"{porque}; compensacion: {det}")
    return rc, f"VENTANA {v.get('id', '(ilegible)')} {porque}; compensacion: {det}"


def _ventana(d: Path, sol: dict, unidad: str, ahora: datetime) -> tuple[str, dict]:
    v = sol["ventana"]
    if v["duracion_s"] == 0:
        if not (d / "ventana.json").exists():
            return "hecha", {"rc": 0, "detalle": "no habia ventana que cerrar"}
        rc, det = cierra(d, unidad, f"cerrada por {sol['id']}")
        return ("hecha" if rc == 0 else "fallida"), {"rc": rc, "detalle": det}
    vigente = ventana_vigente(d, ahora)
    if vigente:
        return "rechazada", {"motivo": f"ya hay una ventana vigente ({vigente['id']}, hasta {vigente['hasta']})"}
    hasta = iso(ahora + timedelta(seconds=v["duracion_s"]))
    escribe(d / "ventana.json", _json({"id": sol["id"], "origen": sol["origen"], "motivo": v["motivo"],
                                       "desde": iso(ahora), "hasta": hasta, "compensacion": v["compensacion"]}))
    return "hecha", {"rc": 0, "detalle": f"ventana abierta hasta {hasta}"}


def _pendientes(d: Path) -> list[Path]:
    """En orden de `creada` (y de nombre en un empate); una ilegible va al final y se rechaza."""
    filas = []
    for p in (d / "solicitudes").glob("*.json"):
        if p.name.startswith("."):
            continue                              # el temporal de una escritura a medias
        try:
            creada = _lee_iso(json.loads(p.read_text(encoding="utf-8")).get("creada"))
        except (OSError, ValueError, AttributeError):
            creada = None
        filas.append((creada or datetime.max.replace(tzinfo=timezone.utc), p.name, p))
    return [p for _c, _n, p in sorted(filas, key=lambda f: (f[0], f[1]))]


def _atiende(d: Path, ruta: Path, unidad: str, ahora: datetime, previa: tuple[str, str] | None):
    """Una solicitud. Devuelve (linea de registro, la accion hecha en esta vuelta)."""
    nombre, tomada = ruta.stem, ruta.with_suffix(".tomada")
    try:
        os.rename(ruta, tomada)
    except FileNotFoundError:
        return f"solicitud {nombre} retirada por su autor antes de tomarla", previa
    try:
        sol = json.loads(tomada.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        sol = None
    accion = sol.get("accion") if isinstance(sol, dict) else None
    motivo = valida(sol, nombre, ahora)
    if motivo:
        responde(d, nombre, accion, "rechazada", motivo=motivo)
        tomada.unlink()
        return f"SOLICITUD {nombre} {accion}: rechazada ({motivo})", previa
    assert isinstance(sol, dict)
    accion = str(accion)  # valida() ya garantizo que es una de ACCIONES
    responde(d, nombre, accion, "aceptada")
    if accion == "ventana":
        estado, campos = _ventana(d, sol, unidad, ahora)
        previa = None
    elif previa and previa[0] == accion:
        # Dos solicitudes de la misma accion en una vuelta: la primera ya la cumplio despues
        # de que las dos se escribieran. Repetirla seria el reinicio doble.
        estado, campos = "hecha", {"rc": 0, "detalle": f"atendida por la de {previa[1]}, en esta misma vuelta"}
    else:
        rc = ejecuta(accion, unidad)
        estado, campos = ("hecha" if rc == 0 else "fallida"), {"rc": rc}
        previa = (accion, nombre) if rc == 0 else None
    responde(d, nombre, accion, estado, **campos)
    tomada.unlink()
    return f"SOLICITUD {nombre} {accion} de {sol['origen']}: {estado} {json.dumps(campos, ensure_ascii=False)}", previa


def atender(d: Path, unidad: str, reloj=lambda: datetime.now(timezone.utc)) -> list[str]:
    """Una vuelta del manejador: latido, ventana vencida, solicitudes en orden, latido."""
    (d / "solicitudes").mkdir(parents=True, exist_ok=True)
    with open(d / "manejador.lock", "w", encoding="utf-8") as cerrojo:
        try:
            fcntl.flock(cerrojo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return ["otro manejador atiende las solicitudes: esta vuelta no"]
        lineas: list[str] = []
        latido(d, unidad, reloj())
        for huerfana in sorted((d / "solicitudes").glob("*.tomada")):
            responde(d, huerfana.stem, None, "fallida", motivo="el manejador murio a media accion")
            huerfana.unlink()
            lineas.append(f"SOLICITUD {huerfana.stem}: fallida (el manejador murio a media accion)")
        if (d / "ventana.json").exists() and ventana_vigente(d, reloj()) is None:
            lineas.append(cierra(d, unidad, "vencida o ilegible")[1])
        previa = None
        for ruta in _pendientes(d):
            linea, previa = _atiende(d, ruta, unidad, reloj(), previa)
            lineas.append(linea)
        limite = time.time() - RESPUESTAS_DIAS * 86400
        for vieja in (d / "respuestas").glob("*.json"):
            if vieja.stat().st_mtime < limite:
                vieja.unlink()
        latido(d, unidad, reloj())
    return lineas


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="motor_solicitudes", description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--dir", type=Path, default=None, help="default: $BLACKBOX_DATA/motor")
    ap.add_argument("--unidad", default=os.environ.get("VIGILANTE_UNIDAD", "ai-nemotron.service"))
    ap.add_argument("orden", choices=("atender", "ventana"),
                    help="atender: una vuelta del manejador; ventana: sale 0 e imprime la vigente, 1 si no hay")
    a = ap.parse_args(argv)
    d = a.dir or directorio()
    if a.orden == "ventana":
        v = ventana_vigente(d, datetime.now(timezone.utc))
        if v is None:
            return 1
        print(f"{v['id']} de {v['origen']} hasta {v['hasta']}: {v['motivo']}")
        return 0
    for linea in atender(d, a.unidad):
        print(linea)
    return 0


if __name__ == "__main__":
    sys.exit(main())
