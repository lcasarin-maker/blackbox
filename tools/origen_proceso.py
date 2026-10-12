#!/usr/bin/env python3
"""ORIGEN de un proceso: QUE es y QUIEN lo lanzo, leido de /proc, solo lectura.

Atribucion: la deteccion de la fuente primaria, la regla de "el padre salio", las advertencias y los
codigos de salida estan PORTADOS a Python desde witr (https://github.com/pranshuparmar/witr, autor
pranshuparmar, commit 7e46fa6, licencia Apache-2.0). No se instala ni se ejecuta witr: se leyo su
fuente y se trajo lo que sirve aqui. Ver NOTICE en la raiz del repo. Cada pieza portada cita su
archivo:linea de origen en witr.

Por que existe
--------------
Los colapsos de memoria del 2026-10-05 y del 2026-10-11 dejaron en las muestras `pid`, `comm` y la
unidad de cgroup del proceso que crecio, y nada mas. "un python3 de 26 GB en el scope de Claude" no dice
que suite, que repo, que sesion ni que hook lo lanzo, y para cuando alguien pregunta el proceso ya
murio y su origen con el. Luis lo pidio el 2026-10-12: el origen no puede ser exclusivo de Claude; hay
que saber QUE proceso y QUIEN lo lanzo, sea un git hook, cron, systemd, docker, la shell de un usuario
u otro agente.

Que guarda, por proceso: pid, ppid, pgid, sid, estado, comm, cmdline con secretos enmascarados, cwd,
exe, starttime, uid, cgroup y unidad, tty, RSS, y la cadena de ancestros hasta PID 1. Encima:
  - `fuente`: UNA sola fuente primaria, en el orden de witr: contenedor -> ssh -> shell -> systemd ->
    supervisor -> cron -> init -> desconocido.
  - `rastros`: lo que bb necesita y witr no busca -- el git hook (repo y rama) y la sesion `claude`
    (cwd y --session-id) mas cercanos.
  - `advertencias`: RSS > 1 GiB, padre salio, sin supervisor conocido, LD_PRELOAD, zombie/detenido,
    binario borrado.

Vocabulario de lo que no se pudo leer: `NOT_COLLECTED` (proceso ya muerto, permiso denegado, plazo
agotado) y `UNSUPPORTED` (el kernel no da el dato, p.ej. cgroup v1). Nunca un cero inventado: el motivo
de cada `NOT_COLLECTED` va en `no_colectado`. Un `null` solo aparece donde el kernel SI contesto
"ninguno" (tty_nr 0 = sin terminal).

Secretos: del entorno (`/proc/<pid>/environ`) solo se guardan NOMBRES, y solo los que algo usa
(LD_PRELOAD, SNAP_NAME, FLATPAK_ID); ningun valor sale de esta funcion. En argv, todo valor cuyo nombre
contenga KEY|TOKEN|PASSWORD|PASSWD|SECRET|DATABASE_URL|CREDENTIAL|AUTH|COOKIE se reemplaza por
`<enmascarado>`; lo mismo para el argumento que sigue a una opcion con ese nombre, la contrasena de una
URL `esquema://usuario:clave@host` y los prefijos de token conocidos.

LIMITE DECLARADO: un proceso que muere antes del muestreo queda `NOT_COLLECTED`; esto no reconstruye
nada que /proc ya no tenga. Y leer `cmdline`/`environ` toma el `mmap_lock` del proceso: bajo un
estancamiento de memoria puede tardar. Quien llama desde un vigilante (`bin/bb-usable`) lo corre con
plazo.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

NOT_COLLECTED = "NOT_COLLECTED"
UNSUPPORTED = "UNSUPPORTED"
MASCARA = "<enmascarado>"
ESQUEMA = "bb-origen/1"

# Nombre que delata un secreto. Sobre-enmascarar (`--keyboard=x`) es el precio aceptado: perder un
# argumento de diagnostico cuesta menos que guardar un token en una muestra que se comparte. Dos
# exclusiones medidas el 2026-10-12 sobre el vLLM de esta maquina: `--max-num-batched-tokens 8192`
# perdia su valor por TOKEN, y `--author` caeria por AUTH; ninguno de los dos es un secreto.
NOMBRE_SECRETO = re.compile(
    r"(KEY|TOKEN(?!S)|PASSWORD|PASSWD|SECRET|DATABASE_URL|CREDENTIAL|AUTH(?!ORS?\b)|COOKIE)", re.IGNORECASE)
_PALABRAS = NOMBRE_SECRETO.pattern[1:-1]
# Argumento entero `NOMBRE=valor`, `--nombre=valor`, `Nombre: valor` con nombre secreto.
PAR_SECRETO = re.compile(r"^(-{0,2}[^\s=:]*?(?:" + _PALABRAS + r")[^\s=:]*)\s*([=:])", re.IGNORECASE)
# El mismo par DENTRO de un texto libre: el `bash -c "... --api-key=x ..."` de un padre lleva el
# comando del hijo entero en UN argumento. Medido el 2026-10-12 por test_real_cadena_cmdline_y_ningun_
# secreto: sin esto el secreto del hijo salia por la cmdline del bash que lo lanzo.
PAR_EN_TEXTO = re.compile(r"([\w.-]*(?:" + _PALABRAS + r")[\w.-]*)(=|:\s*|\s+)([^\s'\";&|]+)", re.IGNORECASE)
CREDENCIAL_HTTP = re.compile(r"\b(Bearer|Basic|Token)\s+[^\s'\";&|]+", re.IGNORECASE)
URL_CON_CLAVE = re.compile(r"(\w+://[^/\s:@]+:)[^@\s/]+@")
PREFIJO_TOKEN = re.compile(r"\b(ghp_|gho_|ghs_|github_pat_|sk-ant-|sk-|xox[abp]-|AKIA)[A-Za-z0-9_\-]{8,}")

# Variables de entorno cuyo NOMBRE (nunca su valor) se registra: witr detect.go:38-51 (LD_PRELOAD) y
# container.go:56-73 (SNAP_NAME, FLATPAK_ID). DYLD_* se descarta: es macOS.
ENV_NOMBRES = frozenset({"LD_PRELOAD", "SNAP_NAME", "FLATPAK_ID"})

GIT_HOOKS = frozenset({
    "pre-commit", "pre-push", "commit-msg", "pre-merge-commit", "prepare-commit-msg",
    "post-commit", "post-checkout", "post-merge", "pre-rebase", "post-rewrite",
})
PROFUNDIDAD_MAX = 64
RSS_ALTO_KB = 1024 * 1024  # witr process_linux.go:218, memMB > 1024
SYSTEMD_CORRIENDO = Path("/run/systemd/system")  # witr systemd_linux.go:24-27, sd_booted()

# witr shell.go:18-25 (sin los de Windows) y shell.go:27-56 (herramientas de usuario).
SHELLS = frozenset({"bash", "zsh", "sh", "fish", "csh", "tcsh", "ksh", "dash", "ash"})
HERRAMIENTAS_USUARIO = frozenset({
    "python", "python3", "node", "ruby", "perl", "php", "go", "java", "cargo", "npm", "yarn", "make",
    "code", "cursor", "vim", "nvim", "emacs", "nano",
    "gnome-terminal-", "kitty", "alacritty", "wezterm", "konsole",
})
# witr supervisor.go:10-39, sin launchd/smf/nssm (no son Linux).
SUPERVISORES = {
    "pm2": "pm2", "supervisord": "supervisord", "supervisor": "supervisord", "gunicorn": "gunicorn",
    "uwsgi": "uwsgi", "s6-supervise": "s6", "s6": "s6", "s6-svscan": "s6", "runsv": "runit",
    "runit": "runit", "runit-init": "runit", "openrc": "openrc", "openrc-init": "openrc",
    "monit": "monit", "circusd": "circus", "circus": "circus", "systemd": "systemd service",
    "systemctl": "systemd service", "daemontools": "daemontools", "initctl": "upstart",
    "tini": "tini", "docker-init": "docker-init", "podman-init": "podman-init", "god": "god",
    "forever": "forever",
}
ID_CONTENEDOR = re.compile(r"[0-9a-f]{64}")


def _datos() -> Path:
    return Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))


# ------------------------------------------------------------------ enmascarado (puro)


def enmascarar_argv(argv: list[str]) -> list[str]:
    """argv sin valores secretos. Conserva el NOMBRE de cada secreto, nunca su valor."""
    out: list[str] = []
    ocultar_siguiente = False
    for arg in argv:
        if ocultar_siguiente:
            out.append(MASCARA)
            ocultar_siguiente = False
            continue
        m = PAR_SECRETO.match(arg)
        if m:
            out.append(f"{m.group(1)}{m.group(2)}{MASCARA}")
            continue
        if arg.startswith("-") and NOMBRE_SECRETO.search(arg):
            ocultar_siguiente = True
        arg = CREDENCIAL_HTTP.sub(lambda c: f"{c.group(1)} {MASCARA}", arg)
        arg = URL_CON_CLAVE.sub(lambda u: u.group(1) + MASCARA + "@", arg)
        arg = PAR_EN_TEXTO.sub(lambda p: p.group(1) + p.group(2) + MASCARA, arg)
        out.append(PREFIJO_TOKEN.sub(MASCARA, arg))
    return out


# ------------------------------------------------------------------ lectura de /proc


class _Lector:
    """Lee campos de UN pid y anota por que falta cada uno que no pudo leer."""

    def __init__(self, proc: Path, pid: int):
        self.base = proc / str(pid)
        self.no_colectado: dict[str, str] = {}

    def _fallo(self, campo: str, exc: OSError) -> str:
        if isinstance(exc, PermissionError):
            motivo = "permiso denegado"
        elif isinstance(exc, (FileNotFoundError, ProcessLookupError)):
            motivo = "proceso terminado"
        else:
            motivo = f"{type(exc).__name__}: {exc.strerror or exc}"
        self.no_colectado[campo] = motivo
        return NOT_COLLECTED

    def texto(self, campo: str, nombre: str) -> str:
        try:
            return (self.base / nombre).read_bytes().decode("utf-8", errors="replace")
        except OSError as exc:
            return self._fallo(campo, exc)

    def enlace(self, campo: str, nombre: str) -> str:
        try:
            return os.readlink(self.base / nombre)
        except OSError as exc:
            return self._fallo(campo, exc)


def _tty(tty_nr: int) -> str | None:
    if tty_nr == 0:
        return None
    mayor, menor = (tty_nr >> 8) & 0xFFF, (tty_nr & 0xFF) | ((tty_nr >> 12) & 0xFFF00)
    if 136 <= mayor <= 143:
        return f"pts/{(mayor - 136) * 256 + menor}"
    return f"dev {mayor}:{menor}"


CLAVES_STAT = ("estado", "ppid", "pgid", "sid", "comm", "starttime_ticks", "tty", "rss_kb")


def _campos_stat(lector: _Lector) -> dict[str, Any]:
    stat = lector.texto("stat", "stat")
    if stat == NOT_COLLECTED:
        motivo = lector.no_colectado.pop("stat")
        for c in CLAVES_STAT:
            lector.no_colectado[c] = motivo
        return dict.fromkeys(CLAVES_STAT, NOT_COLLECTED)
    resto = stat[stat.rfind(")") + 2:].split()
    return {
        "estado": resto[0], "ppid": int(resto[1]), "pgid": int(resto[2]), "sid": int(resto[3]),
        "comm": stat[stat.find("(") + 1:stat.rfind(")")],
        "starttime_ticks": int(resto[19]), "tty": _tty(int(resto[4])),
        "rss_kb": int(resto[21]) * (os.sysconf("SC_PAGE_SIZE") // 1024),
    }


def _uid(lector: _Lector) -> int | str:
    status = lector.texto("uid", "status")
    for linea in status.splitlines():
        if linea.startswith("Uid:"):
            return int(linea.split()[1])
    return status if status == NOT_COLLECTED else UNSUPPORTED


def _cgroup(lector: _Lector) -> tuple[str, str]:
    texto = lector.texto("cgroup", "cgroup")
    if texto == NOT_COLLECTED:
        lector.no_colectado["unit"] = lector.no_colectado["cgroup"]
        return NOT_COLLECTED, NOT_COLLECTED
    for linea in texto.splitlines():
        if linea.startswith("0::"):
            ruta = linea[3:]
            return ruta, ruta.rsplit("/", 1)[-1] or "/"
    return UNSUPPORTED, UNSUPPORTED  # sin la linea unificada: cgroup v1


def _env_nombres(lector: _Lector) -> list[str] | str:
    """NOMBRES de ENV_NOMBRES con valor no vacio (witr detect.go:202-205 salta los vacios). El valor
    se descarta aqui mismo y nunca sale de la funcion."""
    crudo = lector.texto("env_nombres", "environ")
    if crudo == NOT_COLLECTED:
        return crudo
    nombres = set()
    for entrada in crudo.split("\0"):
        nombre, sep, valor = entrada.partition("=")
        if sep and valor and nombre in ENV_NOMBRES:
            nombres.add(nombre)
    return sorted(nombres)


def leer_proceso(pid: int, proc: Path = Path("/proc"), entorno: bool = False) -> dict[str, Any]:
    """Todo lo que /proc dice de un pid. Cada campo es su valor, NOT_COLLECTED o UNSUPPORTED."""
    lector = _Lector(proc, pid)
    datos: dict[str, Any] = {"pid": pid, **_campos_stat(lector)}
    datos["uid"] = _uid(lector)
    crudo = lector.texto("cmdline", "cmdline")
    datos["cmdline"] = crudo if crudo == NOT_COLLECTED else enmascarar_argv(
        [a for a in crudo.split("\0") if a])
    datos["cwd"] = lector.enlace("cwd", "cwd")
    datos["exe"] = lector.enlace("exe", "exe")
    datos["cgroup"], datos["unit"] = _cgroup(lector)
    if entorno:
        datos["env_nombres"] = _env_nombres(lector)
    datos["no_colectado"] = lector.no_colectado
    return datos


def _padre_salio_por_inicio(padre: dict[str, Any], hijo: dict[str, Any]) -> bool:
    """witr ancestry.go:52-55 y 86-88: un padre no puede haber nacido despues que su hijo; si el pid
    del padre lo ocupa alguien mas nuevo, el padre real salio y su pid se recicio."""
    a, b = padre.get("starttime_ticks"), hijo.get("starttime_ticks")
    return isinstance(a, int) and isinstance(b, int) and a > b


def _adoptado(hijo: dict[str, Any], padre: dict[str, Any]) -> bool:
    """witr ancestry.go:90-98: un hijo hereda la sesion de su padre; un padre de OTRA sesion lo
    adopto, salvo que el hijo abriera su propia sesion (lider de sesion: servicio o demonio)."""
    hs, ps = hijo.get("sid"), padre.get("sid")
    return (isinstance(hs, int) and isinstance(ps, int) and hs > 0 and ps > 0
            and hs != hijo.get("pid") and ps != hs)


def ancestros(datos: dict[str, Any], proc: Path = Path("/proc")) -> list[dict[str, Any]]:
    """Cadena de padres hasta PID 1, del mas cercano al mas lejano (witr ancestry.go:17-67).

    Marca `padre_salio` en el eslabon (el objetivo o un ancestro) cuyo padre ya no es quien lo
    inicio: el padre no existe, nacio despues que el, o es de otra sesion (fue adoptado)."""
    cadena: list[dict[str, Any]] = []
    hijo = datos
    vistos = {datos.get("pid")}
    while isinstance(hijo.get("ppid"), int) and hijo["ppid"] > 0 and len(cadena) < PROFUNDIDAD_MAX:
        ppid = hijo["ppid"]
        if ppid in vistos:
            break
        vistos.add(ppid)
        padre = leer_proceso(ppid, proc)
        if padre["comm"] == NOT_COLLECTED:
            # ancestry.go:35-41: solo un padre que YA NO EXISTE dice que quien lo inicio salio.
            if padre["no_colectado"].get("comm") == "proceso terminado":
                hijo["padre_salio"] = True
            break
        if _padre_salio_por_inicio(padre, hijo):
            hijo["padre_salio"] = True
            break
        if _adoptado(hijo, padre):
            hijo["padre_salio"] = True
        cadena.append({k: padre[k] for k in ("pid", "ppid", "sid", "comm", "starttime_ticks", "cmdline",
                                              "cwd", "cgroup", "unit", "tty", "no_colectado")})
        hijo = cadena[-1]
        if ppid == 1:
            break
    return cadena


# ------------------------------------------------------------------ fuente primaria (witr detect.go)


def _base(p: dict[str, Any]) -> str:
    argv = p.get("cmdline")
    argv0 = argv[0] if isinstance(argv, list) and argv else ""
    return p["comm"] if p.get("comm") not in (None, NOT_COLLECTED) else Path(argv0).name


def _nombres(p: dict[str, Any]) -> set[str]:
    argv = p.get("cmdline")
    argv0 = argv[0] if isinstance(argv, list) and argv else ""
    return {str(p.get("comm")), Path(argv0).name}


def _contenedor(cadena: list[dict[str, Any]], objetivo_env: list[str] | str) -> dict[str, Any] | None:
    """witr container.go:12-96. Solo un cgroup con ID de 64 hex es un contenedor: el servicio del
    runtime (docker.service) nombra al runtime pero aloja sus demonios, no contenedores."""
    for p in cadena:
        cg = str(p.get("cgroup", ""))
        es_id = ID_CONTENEDOR.search(cg) and "-conmon-" not in cg
        for marcas, nombre in ((("docker",), "docker"), (("podman", "libpod"), "podman"),
                               (("containerd",), "containerd")):
            if es_id and any(m in cg for m in marcas):
                return {"tipo": "contenedor", "nombre": nombre}
        for marca, nombre in (("kubepods", "kubernetes"), ("colima", "colima"), ("lxc.payload", "lxc")):
            if marca in cg:
                return {"tipo": "contenedor", "nombre": nombre}
    if isinstance(objetivo_env, list):
        for var, nombre in (("SNAP_NAME", "snap"), ("FLATPAK_ID", "flatpak")):
            if var in objetivo_env:
                return {"tipo": "contenedor", "nombre": nombre}
    return None


def _ssh(cadena: list[dict[str, Any]]) -> dict[str, Any] | None:
    """witr ssh.go:11-41. La IP remota de SSH_CLIENT NO se porta: es un valor del entorno."""
    for p in cadena[1:]:
        if {n.rstrip(":").lower() for n in _nombres(p)} & {"sshd", "sshd-session"}:
            return {"tipo": "ssh", "nombre": "sshd", "pid": p["pid"]}
    return None


def _multiplexor(base: str) -> str | None:
    """witr shell.go:120-130. El nombre de sesion de tmux NO se porta: witr ejecuta `tmux`."""
    if base == "tmux" or base.startswith("tmux:"):
        return "tmux"
    if base == "screen" or base.startswith("SCREEN"):
        return "screen"
    return None


def _shell(cadena: list[dict[str, Any]]) -> dict[str, Any] | None:
    """witr shell.go:58-118: el ancestro MAS CERCANO que es shell, multiplexor o herramienta de usuario."""
    for p in cadena[1:]:
        base = _base(p)
        nombre = (base if base.lower() in SHELLS or base in HERRAMIENTAS_USUARIO
                  or base.startswith(("python", "node")) else _multiplexor(base))
        if nombre:
            return {"tipo": "shell", "nombre": nombre, "pid": p["pid"]}
    return None


def unidad_systemd(cgroup: str) -> str:
    """witr systemd_linux.go:264-292: el ultimo componente .service o .scope de la ruta."""
    for parte in reversed(str(cgroup).split("/")):
        if parte.endswith((".service", ".scope")):
            return parte
    return ""


def _systemd(cadena: list[dict[str, Any]]) -> dict[str, Any] | None:
    """witr systemd_linux.go:29-59, sin el enriquecimiento por D-Bus (NRestarts, timer, descripcion)."""
    if not SYSTEMD_CORRIENDO.exists() or not any(p.get("pid") == 1 for p in cadena):
        return None
    return {"tipo": "systemd", "nombre": unidad_systemd(cadena[0].get("cgroup", ""))}


def _supervisor(cadena: list[dict[str, Any]]) -> dict[str, Any] | None:
    """witr supervisor.go:41-99."""
    hay_shell = any(_base(p).lower() in SHELLS for p in cadena)
    for p in cadena:
        base = _base(p)
        if base == "init" and not hay_shell:
            return {"tipo": "supervisor", "nombre": "init"}
        cmdline = p.get("cmdline")
        tokens = [base.lower()] + [Path(t).name for t in (cmdline if isinstance(cmdline, list) else [])
                                   if not t.startswith("-") and "=" not in t]
        for t in tokens:
            if t.lower() in SUPERVISORES:
                return {"tipo": "supervisor", "nombre": SUPERVISORES[t.lower()]}
    return None


def _cron(cadena: list[dict[str, Any]]) -> dict[str, Any] | None:
    """witr cron.go:9-20."""
    for p in cadena:
        if _base(p) in ("cron", "crond"):
            return {"tipo": "cron", "nombre": "cron", "pid": p["pid"]}
    return None


def _init(cadena: list[dict[str, Any]]) -> dict[str, Any] | None:
    """witr init.go:15-60: hijo directo de la cadena de PID 1 sin shell de por medio."""
    if not cadena or cadena[-1].get("pid") != 1:
        return None
    if any(_base(p).lower() in SHELLS for p in cadena[1:-1]):
        return None
    return {"tipo": "init", "nombre": _base(cadena[-1]) or "init"}


def _detectar(cadena: list[dict[str, Any]], objetivo_env: list[str] | str) -> dict[str, Any]:
    """witr detect.go:149-186: UNA fuente, la primera que aparece en este orden."""
    for detector in (lambda c: _contenedor(c, objetivo_env), _ssh, _shell, _systemd, _supervisor,
                     _cron, _init):
        fuente = detector(cadena)
        if fuente:
            return fuente
    return {"tipo": "desconocido"}


def _explica_huerfano(fuente: dict[str, Any], debajo: list[dict[str, Any]]) -> bool:
    """witr detect.go:116-147. Lo leido del propio proceso (contenedor, unidad systemd, scope de app o
    sesion) sigue valiendo; lo hallado en ancestros solo vale si se halla DEBAJO del corte."""
    tipo, nombre = fuente["tipo"], fuente.get("nombre", "")
    if tipo == "contenedor":
        return True
    if tipo == "systemd":
        return bool(nombre) and nombre != "init.scope" and not nombre.startswith("user@")
    redetector = {"shell": _shell, "ssh": _ssh, "supervisor": _supervisor, "cron": _cron}.get(tipo)
    return bool(redetector and redetector(debajo))


def corte_padre_salio(cadena: list[dict[str, Any]]) -> int:
    """Indice (0 = objetivo) del eslabon MAS CERCANO al objetivo cuyo padre salio, o -1.
    witr detect.go:97-106 recorre desde el objetivo hacia la raiz; aqui la cadena ya va en ese orden."""
    return next((i for i, p in enumerate(cadena) if p.get("padre_salio")), -1)


def fuente_primaria(cadena: list[dict[str, Any]], objetivo_env: list[str] | str) -> dict[str, Any]:
    """witr detect.go:62-82: detectar y luego no acreditar a quien solo lo adopto."""
    fuente = _detectar(cadena, objetivo_env)
    corte = corte_padre_salio(cadena)
    if corte < 0:
        return fuente
    if fuente["tipo"] == "init":
        return {**fuente, "descripcion": "adoptado por init tras salir quien lo inicio"}
    if not _explica_huerfano(fuente, cadena[:corte + 1]):
        return {"tipo": "desconocido", "padre_salio": True,
                "descripcion": "quien lo inicio ya salio; lo de arriba solo lo adopto"}
    return fuente


# ------------------------------------------------------------------ rastros propios de bb


def _rama(cwd: str) -> str:
    """Rama de git del repo que contiene cwd, leyendo .git/HEAD sin ejecutar git."""
    if cwd in (NOT_COLLECTED, UNSUPPORTED):
        return NOT_COLLECTED
    d = Path(cwd)
    for carpeta in (d, *d.parents):
        git = carpeta / ".git"
        try:
            if git.is_file():
                git = carpeta / git.read_text(encoding="utf-8").split("gitdir:", 1)[1].strip()
            if (git / "HEAD").is_file():
                head = (git / "HEAD").read_text(encoding="utf-8").strip()
                return head.removeprefix("ref: refs/heads/") if head.startswith("ref:") else head[:12]
        except (OSError, IndexError):
            return NOT_COLLECTED
    return NOT_COLLECTED


def _sesion_claude(argv: list[str] | str) -> str:
    if not isinstance(argv, list):
        return NOT_COLLECTED
    for i, a in enumerate(argv):
        for opcion in ("--session-id", "--resume", "-r"):
            if a == opcion and i + 1 < len(argv):
                return argv[i + 1]
            if a.startswith(opcion + "="):
                return a.split("=", 1)[1]
    return NOT_COLLECTED


def rastros(debajo: list[dict[str, Any]]) -> dict[str, Any]:
    """El git hook y la sesion `claude` MAS CERCANOS, buscados solo debajo del corte de padre-salio:
    por encima, un ancestro solo adopto al proceso y no puede reclamarlo."""
    out: dict[str, Any] = {}
    for e in debajo[1:]:
        hook = next((n for n in _nombres(e) if n in GIT_HOOKS), None)
        argv = e["cmdline"] if isinstance(e["cmdline"], list) else []
        if (hook or (argv and "/hooks/" in argv[0])) and "git_hook" not in out:
            out["git_hook"] = {"hook": hook or "hook", "pid": e["pid"], "repo": e["cwd"],
                               "rama": _rama(e["cwd"])}
        if e["comm"] == "claude" and "claude" not in out:
            out["claude"] = {"pid": e["pid"], "cwd": e["cwd"], "session_id": _sesion_claude(e["cmdline"]),
                             "args": argv[1:] if argv else e["cmdline"]}
    return out


# ------------------------------------------------------------------ advertencias (witr detect.go:243)


def advertencias(datos: dict[str, Any], fuente: dict[str, Any], hubo_corte: bool) -> list[str]:
    """Lo util de witr detect.go:243-354 para este repo. Descartado: reinicios (D-Bus), sockets
    publicos, capacidades, antiguedad > 90 dias, healthcheck, nombre de servicio vs proceso."""
    w = []
    if datos.get("estado") == "Z":
        w.append("proceso zombi (defunct)")
    elif datos.get("estado") == "T":
        w.append("proceso detenido (estado T)")
    if isinstance(datos.get("rss_kb"), int) and datos["rss_kb"] > RSS_ALTO_KB:
        w.append(f"RSS alto: {datos['rss_kb'] / 1048576:.1f} GiB > 1 GiB")
    if fuente["tipo"] == "desconocido":
        w.append("el padre original salio: no se puede saber quien lo inicio" if hubo_corte
                 else "ningun supervisor ni gestor de servicios conocido")
    if str(datos.get("exe", "")).endswith(" (deleted)"):
        w.append("corre desde un binario borrado")
    if isinstance(datos.get("env_nombres"), list) and "LD_PRELOAD" in datos["env_nombres"]:
        w.append("el proceso define LD_PRELOAD (posible inyeccion de biblioteca; valor no guardado)")
    return w


def origen(pid: int, proc: Path = Path("/proc")) -> dict[str, Any]:
    datos = leer_proceso(pid, proc, entorno=True)
    cadena_padres = ancestros(datos, proc)
    cadena = [datos, *cadena_padres]
    corte = corte_padre_salio(cadena)
    fuente = fuente_primaria(cadena, datos.get("env_nombres", NOT_COLLECTED))
    datos["ancestros"] = cadena_padres
    datos["fuente"] = fuente
    datos["rastros"] = rastros(cadena if corte < 0 else cadena[:corte + 1])
    datos["advertencias"] = advertencias(datos, fuente, corte >= 0)
    return datos


# ------------------------------------------------------------------ captura


def mayores_por_rss(n: int, proc: Path = Path("/proc")) -> tuple[list[int], int, int]:
    """Los n pids de mayor RSS de TODO el sistema. Devuelve (pids, vistos, ilegibles)."""
    filas, ilegibles = [], []
    for entrada in proc.iterdir():
        if not entrada.name.isdigit():
            continue
        try:
            stat = (entrada / "stat").read_text(encoding="ascii", errors="replace")
            filas.append((int(stat[stat.rfind(")") + 2:].split()[21]), int(entrada.name)))
        except (OSError, ValueError, IndexError):
            ilegibles.append(entrada.name)  # se cuenta y sale en el registro, no se pierde
    filas.sort(reverse=True)
    return [pid for _rss, pid in filas[:n]], len(filas), len(ilegibles)


def capturar(motivo: str, top: int, pids: list[int] | None = None,
             proc: Path = Path("/proc")) -> dict[str, Any]:
    elegidos, vistos, ilegibles = mayores_por_rss(top, proc) if top > 0 else ([], NOT_COLLECTED, NOT_COLLECTED)
    for pid in pids or []:
        if pid not in elegidos:
            elegidos.append(pid)
    return {
        "esquema": ESQUEMA, "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "motivo": motivo,
        "top_n": top, "procesos_vistos": vistos, "procesos_ilegibles": ilegibles,
        "procesos": [origen(pid, proc) for pid in elegidos],
    }


def anexar_jsonl(ruta: Path, obj: dict[str, Any]) -> None:
    """Una linea, un solo write(2) con O_APPEND: dos escritores (bb sample y bb-usable) no se mezclan.
    `bin/bb-usable` corre como root y escribe con su propio `_anexar`, que ademas cede la propiedad
    al dueno de $BLACKBOX_DATA; esta version es la del usuario."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(ruta, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
    finally:
        os.close(fd)


def ruta_del_dia(datos: Path | None = None) -> Path:
    return (datos or _datos()) / "origen" / f"{time.strftime('%Y-%m-%d')}.jsonl"


# ------------------------------------------------------------------ lector `bb origen`

# witr internal/app/app.go:99-125: codigos y su severidad. Con varios registros gana el mas severo;
# "origen desconocido" es un hallazgo, asi que pesa menos que cualquier fallo pese a su numero.
SALIDA_OK, SALIDA_ADVERTENCIAS, SALIDA_NO_ENCONTRADO = 0, 1, 2
SALIDA_PERMISO, SALIDA_ENTRADA_INVALIDA, SALIDA_ERROR_INTERNO, SALIDA_ORIGEN_DESCONOCIDO = 3, 4, 5, 6
SEVERIDAD = {0: 0, 1: 1, 6: 2, 2: 3, 3: 4, 4: 5, 5: 6}
FECHA_VALIDA = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}(:\d{2}(:\d{2})?)?)?$")


def _en_ventana(ts: str, desde: str | None, hasta: str | None) -> bool:
    # Todos los registros llevan la misma zona: se compara el prefijo de fecha-hora.
    return (desde is None or ts[:len(desde)] >= desde) and (hasta is None or ts[:len(hasta)] <= hasta)


def clave_lanzador(p: dict[str, Any]) -> str:
    """Texto con el que `leer` agrupa. El rastro mas especifico manda; si no hay, la fuente."""
    r, f = p.get("rastros", {}), p.get("fuente", {})
    if "git_hook" in r:
        g = r["git_hook"]
        return f"git_hook {g['hook']} repo={g['repo']} rama={g['rama']}"
    if "claude" in r:
        return f"claude cwd={r['claude']['cwd']} session={r['claude']['session_id']}"
    return f"{f.get('tipo', 'desconocido')} {f.get('nombre', '')} unit={p.get('unit')}".rstrip()


def agrupar(registros: list[dict[str, Any]]) -> dict[str, list[tuple[dict[str, Any], dict[str, Any]]]]:
    grupos: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for reg in registros:
        for p in reg.get("procesos", []):
            grupos[clave_lanzador(p)].append((reg, p))
    return grupos


def leer(datos: Path, desde: str | None, hasta: str | None) -> tuple[list[dict[str, Any]], int]:
    """Registros de la ventana y cuantas lineas NO se pudieron leer: una linea corrupta (un escritor
    que murio a media linea) se cuenta y se dice, no se salta en silencio."""
    out, ilegibles = [], 0
    for f in sorted((datos / "origen").glob("*.jsonl")):
        for linea in f.read_text(encoding="utf-8").splitlines():
            try:
                reg = json.loads(linea)
            except ValueError:
                ilegibles += 1
                continue
            if _en_ventana(str(reg.get("ts", "")), desde, hasta):
                out.append(reg)
    return out, ilegibles


def codigo_de(registros: list[dict[str, Any]]) -> int:
    procesos = [p for r in registros for p in r.get("procesos", [])]
    if not procesos:
        return SALIDA_NO_ENCONTRADO
    codigos = [SALIDA_ORIGEN_DESCONOCIDO if p.get("fuente", {}).get("tipo") == "desconocido"
               else SALIDA_ADVERTENCIAS if p.get("advertencias") else SALIDA_OK for p in procesos]
    return max(codigos, key=SEVERIDAD.__getitem__)


def imprimir(grupos: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]]) -> None:
    if not grupos:
        print("sin registros de origen en la ventana")
        return
    for clave, filas in sorted(grupos.items(), key=lambda kv: -len(kv[1])):
        print(f"== {clave}  ({len(filas)} procesos)")
        for reg, p in filas:
            rss = p["rss_kb"] if isinstance(p["rss_kb"], str) else f"{p['rss_kb'] / 1048576:.1f} GiB"
            cmd = " ".join(p["cmdline"]) if isinstance(p["cmdline"], list) else p["cmdline"]
            print(f"   {reg['ts']}  {reg['motivo']:<22} pid={p['pid']} {p['comm']} rss={rss}  {cmd[:120]}")
            for w in p.get("advertencias", []):
                print(f"       ! {w}")


def _leer_cli(a: argparse.Namespace) -> int:
    for valor in (a.desde, a.hasta):
        if valor is not None and not FECHA_VALIDA.match(valor):
            print(f"fecha invalida: {valor!r} (AAAA-MM-DD[THH[:MM[:SS]]])", file=sys.stderr)
            return SALIDA_ENTRADA_INVALIDA
    try:
        registros, ilegibles = leer(_datos(), a.desde, a.hasta)
    except PermissionError as exc:
        print(f"permiso denegado: {exc}", file=sys.stderr)
        return SALIDA_PERMISO
    codigo = codigo_de(registros)
    if ilegibles:
        print(f"lineas ilegibles en los registros: {ilegibles}", file=sys.stderr)
        codigo = max(codigo, SALIDA_ADVERTENCIAS, key=SEVERIDAD.__getitem__)
    grupos = agrupar(registros)
    if a.json:
        print(json.dumps({"esquema": "bb-origen-lectura/1", "codigo": codigo, "lineas_ilegibles": ilegibles,
                          "grupos": [
            {"lanzador": k, "procesos": [{"ts": r["ts"], "motivo": r["motivo"], **p} for r, p in v]}
            for k, v in grupos.items()]}, ensure_ascii=False))
    else:
        imprimir(grupos)
    return codigo


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="origen de procesos: captura y lectura")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capturar")
    c.add_argument("--motivo", required=True)
    c.add_argument("--top", type=int, default=10)
    c.add_argument("--pid", type=int, action="append", default=[])
    c.add_argument("--sin-guardar", action="store_true")
    r = sub.add_parser("leer")
    r.add_argument("--desde")
    r.add_argument("--hasta")
    r.add_argument("--json", action="store_true")
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return SALIDA_ENTRADA_INVALIDA if exc.code else SALIDA_OK
    try:
        if a.cmd == "leer":
            return _leer_cli(a)
        reg = capturar(a.motivo, a.top, a.pid)
        if not a.sin_guardar:
            anexar_jsonl(ruta_del_dia(), reg)
        print(json.dumps(reg, ensure_ascii=False))
        return SALIDA_OK
    except Exception:  # witr app.go:106-108: un fallo propio no se confunde con "advertencias"
        logging.getLogger("bb.origen").exception("error interno")
        return SALIDA_ERROR_INTERNO


if __name__ == "__main__":
    sys.exit(main())
