"""Boton rojo: `sudo rojo` suspende todo y deja la maquina en su estado base.

Pedido de Luis (2026-11-02): "si vuelve a pasar un megacrash, UN solo comando
que suspenda todo y deje la maquina en estado funcional base", y despues: "un
comando que se corra en la terminal en segundos, que se escriba facil y rapido
sin caracteres especiales, por si tenemos un ciclo de reboot de segundos". Es
lo que se hizo a mano el 2026-10-30 (`2026-10-30-crashloop.json`, 22
unidades), en un comando, sin red, sin sesion grafica y con el home medio roto.

    sudo rojo               suspende
    sudo rojo seco          imprime el plan y no toca nada
    sudo rojo estado        que esta suspendido, desde cuando, cuando vence
    sudo rojo restaura      deshace desde el manifiesto (motor: restaura todo si)

Corre como root y actua sobre el usuario `lcasarin` (BB_ROJO_USUARIO). El
`sudo rojo` instalado es `/usr/local/sbin/rojo` (bin/rojo) y ejecuta una COPIA
root-owned de este archivo en /usr/local/lib/blackbox/, nunca el repo: un root
no ejecuta codigo de un directorio que un usuario escribe (mismo principio que
tools/ultimo_aliento.py). Solo biblioteca estandar: corre con `python3 -I`.
Instalacion: docs/BOTON-ROJO.md.

Orden, por el ciclo de reboot de segundos: primero lo que PERSISTE y despues lo
vivo. (1) manifiesto con fsync; (2) marca /var/lib/blackbox/rojo.activo;
(3) renombres `<unidad>.suspendido-<fecha>` (rename conserva dueno y modo);
(4) `docker update --restart=no` a los contenedores con GPU; (5) solo entonces
`systemctl --user stop` (via `--machine=<usuario>@.host` siendo root) y
`docker stop -t 5` en paralelo. Si el manager de usuario no esta arriba (aun no
hay sesion), el stop se omite sin fallar: los renombres bastan, porque en el
siguiente arranque no hay nada que arrancar.

Contrato de suspension (CLAUDE.md, "Suspension contract"): suspender =
RENOMBRAR, nunca borrar; restaura solo lo que verifica por sha256, modo y
destino del enlace contra el manifiesto, y lo que no cuadra lo reporta y NO lo
toca; el manifiesto lleva vencimiento (hoy + 7 dias) y quien lo vigila. Si el
manifiesto no se puede escribir en ~/.local/share/blackbox/suspensiones, cae a
/var/lib/blackbox/rojo/ y lo dice.

Lo que NO hace, a proposito: matar procesos sueltos ni scopes transitorios de
otras sesiones (los lista); parar contenedores sin GPU (bases de datos
incluidas); tocar unidades de sistema o de paquetes.

Pruebas: BB_ROJO_RAIZ=<dir> antepone una raiz falsa a toda ruta absoluta
(home, /run/user, /var/lib); BB_ROJO_COMO_ROOT=1 construye los comandos como
root sin serlo.

Salida: 0 todo hecho; 1 hubo could_not_run (la lista va impresa); 2 no pudo ni
empezar (falta la lista KEEP, no hay manifiesto que restaurar).
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import pwd
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ESQUEMA = "bb-suspension/1"
AQUI = Path(__file__).resolve().parent
# Instalado: la lista vive junto a la copia root (/usr/local/lib/blackbox/). En el repo: adopted/.
KEEP = (AQUI / "boton-rojo-keep.txt") if (AQUI / "boton-rojo-keep.txt").is_file() \
    else AQUI.parent / "adopted" / "boton-rojo-keep.txt"
SUFIJOS = (".service", ".timer")
# Arrancar esto otra vez vuelve a cargar la GPU: restaura no lo hace sin `todo si`.
MOTOR = ("ai-nemotron*", "ai-ollama*")
VIGENCIA_DIAS = 7
T_SYSTEMCTL = 3
T_RELOAD = 10
T_DOCKER = 5
DOCKER_STOP_T = 5
T_DOCKER_STOP = 15
Dic = dict[str, Any]


def en_raiz(ruta: str) -> Path:
    return Path(os.environ.get("BB_ROJO_RAIZ") or "/") / ruta.lstrip("/")


class Ctx:
    """Rutas y modo de ejecucion, resueltos una vez."""

    def __init__(self) -> None:
        self.usuario = os.environ.get("BB_ROJO_USUARIO") or "lcasarin"
        try:
            pw = pwd.getpwnam(self.usuario)
            self.uid, self.gid, home = pw.pw_uid, pw.pw_gid, pw.pw_dir
        except KeyError:
            self.uid, self.gid, home = 1000, 1000, f"/home/{self.usuario}"
        self.home = en_raiz(home)
        self.unidades = self.home / ".config" / "systemd" / "user"
        self.susp = [self.home / ".local/share/blackbox/suspensiones", en_raiz("/var/lib/blackbox/rojo")]
        self.marca = en_raiz("/var/lib/blackbox/rojo.activo")
        self.es_root = os.geteuid() == 0
        como_root = self.es_root or os.environ.get("BB_ROJO_COMO_ROOT") == "1"
        self.systemctl = (["systemctl", f"--machine={self.usuario}@.host", "--user"]
                          if como_root else ["systemctl", "--user"])
        self.manager = en_raiz(f"/run/user/{self.uid}/systemd/private").exists()


class Ejecutor:
    """Comandos con techo de tiempo; tras un systemctl colgado no se le insiste.

    Con la maquina medio rota, un `systemctl` colgado una vez se cuelga las
    demas: tras el primer timeout no se le vuelve a llamar y cada paso que lo
    necesitaba queda en could_not_run; los renombres (solo disco) no dependen
    de el y ya ocurrieron antes.
    """

    def __init__(self) -> None:
        self.systemd_mudo = False

    def corre(self, cmd: list[str], timeout: int) -> tuple[int | None, str, str]:
        if cmd[0] == "systemctl" and self.systemd_mudo:
            return None, "", "systemd no respondio antes; no se reintenta"
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except FileNotFoundError:
            return None, "", f"no existe {cmd[0]} en PATH"
        except subprocess.TimeoutExpired:
            if cmd[0] == "systemctl":
                self.systemd_mudo = True
            return None, "", f"timeout de {timeout}s"
        return p.returncode, p.stdout, p.stderr

    @staticmethod
    def lanza(cmd: list[str]) -> subprocess.Popen[str] | str:
        try:
            return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        except FileNotFoundError:
            return f"no existe {cmd[0]} en PATH"

    @staticmethod
    def espera(p: subprocess.Popen[str] | str, timeout: int) -> tuple[int | None, str, str]:
        if isinstance(p, str):
            return None, "", p
        try:
            out, err = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            p.communicate()
            return None, "", f"timeout de {timeout}s"
        return p.returncode, out, err


def motivo_de(rc: int | None, err: str) -> str:
    return err.strip() or f"rc={rc}"


# --- clasificacion ---------------------------------------------------------


def lee_listas(ruta: Path) -> tuple[list[str], list[str]]:
    """(keep, suspende) del archivo KEEP; las lineas antes de `[suspende]` son KEEP."""
    keep: list[str] = []
    suspende: list[str] = []
    destino = keep
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.split("#", 1)[0].strip()
        if linea == "[suspende]":
            destino = suspende
        elif linea:
            destino.append(linea)
    return keep, suspende


def casa(unidad: str, patrones: list[str] | tuple[str, ...]) -> bool:
    return any(
        fnmatch.fnmatchcase(unidad, p) or fnmatch.fnmatchcase(unidad, p + ".service")
        or fnmatch.fnmatchcase(unidad, p + ".timer")
        for p in patrones
    )


def sha256(ruta: Path) -> str | None:
    try:
        return hashlib.sha256(ruta.read_bytes()).hexdigest()
    except OSError:
        return None  # symlink colgante o ilegible


def modo(ruta: Path) -> str | None:
    try:
        return oct(ruta.stat().st_mode & 0o7777)
    except OSError:
        return None


def escanea(d: Path) -> list[Path]:
    """Archivos de unidad de usuario (.service/.timer), symlinks incluidos; ni dirs ni .bak."""
    try:
        return [f for f in sorted(d.iterdir())
                if f.name.endswith(SUFIJOS) and (f.is_symlink() or f.is_file())]
    except OSError:
        return []


def estados(ctx: Ctx, ej: Ejecutor, unidades: list[str], cnr: list[str]) -> dict[str, tuple[str, str]]:
    """{unidad: (UnitFileState, ActiveState)} en UNA llamada a systemctl show."""
    if not unidades or not ctx.manager:
        return {}
    rc, out, err = ej.corre([*ctx.systemctl, "show", "-p", "Id", "-p", "UnitFileState",
                             "-p", "ActiveState", "--", *unidades], T_SYSTEMCTL)
    if rc != 0:
        cnr.append(f"estado previo de las unidades: {motivo_de(rc, err)}")
        return {}
    res: dict[str, tuple[str, str]] = {}
    for bloque, u in zip(out.strip().split("\n\n"), unidades):
        kv = dict(ln.split("=", 1) for ln in bloque.splitlines() if "=" in ln)
        u = kv["Id"] if kv.get("Id") in unidades else u
        res[u] = (kv.get("UnitFileState", "desconocido"), kv.get("ActiveState", "desconocido"))
    return res


def contenedores_gpu(ej: Ejecutor, cnr: list[str]) -> list[Dic]:
    """Contenedores con GPU (runtime nvidia o DeviceRequests de GPU), corriendo o no.

    Los parados tambien cuentan: con `restart=always` o `unless-stopped`
    docker los levanta en el siguiente arranque, que es justo el ciclo que el
    boton corta.
    """
    rc, out, err = ej.corre(["docker", "ps", "-aq"], T_DOCKER)
    if rc != 0:
        cnr.append(f"docker ps: {motivo_de(rc, err)}")
        return []
    ids = out.split()
    if not ids:
        return []
    rc, out, err = ej.corre(["docker", "inspect", *ids], T_DOCKER)
    if rc != 0:
        cnr.append(f"docker inspect: {motivo_de(rc, err)}")
        return []
    fuera = []
    for c in json.loads(out):
        hc = c.get("HostConfig") or {}
        pide_gpu = any(
            r.get("Driver") == "nvidia" or any("gpu" in caps for caps in (r.get("Capabilities") or []))
            for r in (hc.get("DeviceRequests") or [])
        )
        if hc.get("Runtime") == "nvidia" or pide_gpu:
            fuera.append({
                "nombre": c.get("Name", "").lstrip("/"),
                "restart_policy": (hc.get("RestartPolicy") or {}).get("Name", "") or "no",
                "corriendo": bool((c.get("State") or {}).get("Running")),
                "restart_cambiado": False, "parado": False, "restaurado": False,
            })
    return fuera


def scopes_vivos(ctx: Ctx, ej: Ejecutor, cnr: list[str]) -> list[str]:
    """Scopes transitorios vivos (`run-*` y los con nombre propio, p. ej. `liberation_job_*`).

    Fuera de la lista: el escritorio (`app-*`, `snap.*`) e `init.scope`. Se
    listan para que se vean; el boton no los mata.
    """
    if not ctx.manager:
        return []
    rc, out, err = ej.corre([*ctx.systemctl, "list-units", "--type=scope", "--state=running",
                             "--no-legend", "--plain"], T_SYSTEMCTL)
    if rc != 0:
        cnr.append(f"listar scopes transitorios: {motivo_de(rc, err)}")
        return []
    fuera = []
    for ln in out.splitlines():
        partes = ln.split(None, 4)
        if partes and partes[0] != "init.scope" and not partes[0].startswith(("app-", "snap.")):
            fuera.append(f"{partes[0]}: {partes[4] if len(partes) > 4 else '?'}")
    return fuera


# --- manifiesto ------------------------------------------------------------


def _fsync_dir(d: Path) -> None:
    fd = os.open(d, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def escribe(ruta: Path, texto: str, dueno: tuple[int, int] | None = None) -> None:
    """Escritura atomica con fsync del archivo y del directorio."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(ruta.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(texto)
        fh.flush()
        os.fsync(fh.fileno())
    if dueno is not None:
        os.chown(tmp, *dueno)
    os.replace(tmp, ruta)
    _fsync_dir(ruta.parent)


class Registro:
    """El manifiesto y donde vive; cae a /var/lib/blackbox/rojo si el home no deja escribir."""

    def __init__(self, ctx: Ctx, ruta: Path, m: Dic) -> None:
        self.ctx, self.ruta, self.m = ctx, ruta, m

    def guarda(self) -> None:
        texto = json.dumps(self.m, ensure_ascii=False, indent=1) + "\n"
        dueno = (self.ctx.uid, self.ctx.gid) if self.ctx.es_root and self.ruta.parent == self.ctx.susp[0] else None
        try:
            escribe(self.ruta, texto, dueno)
        except OSError as e:
            if self.ruta.parent == self.ctx.susp[-1]:
                raise
            nueva = self.ctx.susp[-1] / self.ruta.name
            print(f"AVISO: no se pudo escribir {self.ruta} ({e}); el manifiesto va a {nueva}")
            self.ruta = nueva
            escribe(self.ruta, texto)


def _orden(p: Path) -> tuple[str, int]:
    """`2026-11-02-boton-rojo-2.json` va DESPUES de `2026-11-02-boton-rojo.json`."""
    fecha, _, cola = p.stem.partition("-boton-rojo")
    n = cola.lstrip("-")
    return fecha, int(n) if n.isdigit() else 1


def manifiestos(ctx: Ctx) -> list[Path]:
    rutas: list[Path] = []
    for d in ctx.susp:
        try:
            rutas.extend(d.glob("*-boton-rojo*.json"))
        except OSError:
            pass
    return sorted(rutas, key=_orden)


def lee(ruta: Path) -> Dic:
    return json.loads(ruta.read_text(encoding="utf-8"))


def manifiesto_del_dia(ctx: Ctx, fecha: str) -> tuple[Path, Dic | None]:
    """El manifiesto vivo de hoy (en cualquiera de los dos sitios), o la ruta para uno nuevo.

    Uno restaurado no se reabre: la siguiente pulsacion del mismo dia abre
    `<fecha>-boton-rojo-2.json`, para no mezclar dos suspensiones.
    """
    n = 1
    while True:
        nombre = f"{fecha}-boton-rojo.json" if n == 1 else f"{fecha}-boton-rojo-{n}.json"
        existentes = [d / nombre for d in ctx.susp if (d / nombre).is_file()]
        if not existentes:
            return ctx.susp[0] / nombre, None
        m = lee(existentes[0])
        if m.get("estado") != "restaurado":
            return existentes[0], m
        n += 1


def ahora() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


# --- suspende --------------------------------------------------------------


def suspende(seco: bool, keep_ruta: Path, motivo: str) -> int:
    t0 = time.monotonic()
    ctx, ej = Ctx(), Ejecutor()
    cnr: list[str] = []
    if not keep_ruta.is_file():
        print(f"COULD_NOT_RUN: no existe la lista KEEP {keep_ruta}; no se toca nada")
        return 2
    keep, suspende_l = lee_listas(keep_ruta)
    archivos = escanea(ctx.unidades)
    a_suspender = [f for f in archivos if not casa(f.name, keep)]
    quedan = [f.name for f in archivos if casa(f.name, keep)]
    est = estados(ctx, ej, [f.name for f in a_suspender], cnr)
    plan_u: list[Dic] = []
    for f in a_suspender:
        en, ac = est.get(f.name, ("desconocido", "desconocido"))
        u: Dic = {"unidad": f.name, "enabled": en, "active": ac, "sha256": sha256(f),
                  "modo": modo(f), "sin_clasificar": not casa(f.name, suspende_l),
                  "hecho": False, "detenida": False, "restaurado": False}
        if f.is_symlink():
            u["enlace"] = os.readlink(f)
        plan_u.append(u)
    plan_c = contenedores_gpu(ej, cnr)
    avisos = [] if ctx.manager else [
        f"manager de usuario de {ctx.usuario} abajo: estado previo y stop OMITIDOS (los renombres bastan)"]

    if seco:
        imprime(plan_u, plan_c, quedan, scopes_vivos(ctx, ej, cnr), avisos, cnr,
                titulo="PLAN (seco: no se toca nada)", hechas=False)
        return 1 if cnr else 0

    hoy = dt.date.today()
    ruta, m = manifiesto_del_dia(ctx, hoy.isoformat())
    if m is None:
        m = {
            "esquema": ESQUEMA, "fecha": hoy.isoformat(), "motivo": motivo,
            "vence": (hoy + dt.timedelta(days=VIGENCIA_DIAS)).isoformat(),
            "vigila": "Luis / sudo rojo estado",
            "restaurar": "sudo rojo restaura   (motor: sudo rojo restaura todo si)",
            "usuario": ctx.usuario, "estado": "en_curso", "creado": ahora(),
            "unidades": plan_u, "contenedores": plan_c,
            "corridas": [{"tipo": "primera corrida", "inicio": ahora(), "nuevas": []}],
        }
    else:
        tipo = "continuacion" if m.get("estado") == "en_curso" else "segunda corrida"
        conocidas = {u["unidad"] for u in m["unidades"]}
        nuevas = [u for u in plan_u if u["unidad"] not in conocidas]
        cono_c = {c["nombre"] for c in m["contenedores"]}
        nuevos_c = [c for c in plan_c if c["nombre"] not in cono_c]
        m["unidades"].extend(nuevas)
        m["contenedores"].extend(nuevos_c)
        m["estado"] = "en_curso"
        m["corridas"].append({"tipo": tipo, "inicio": ahora(),
                              "nuevas": [u["unidad"] for u in nuevas] + [c["nombre"] for c in nuevos_c]})
    reg = Registro(ctx, ruta, m)
    reg.guarda()  # (1) PRIMERO el manifiesto, con fsync; despues las acciones.

    try:  # (2) marca de boton pulsado
        escribe(ctx.marca, f"{ahora()} pulsado; manifiesto {reg.ruta}\n")
    except OSError as e:
        cnr.append(f"marca {ctx.marca}: {e}")

    for u in m["unidades"]:  # (3) renombres: lo que persiste al siguiente arranque
        if u["hecho"]:
            continue
        orig = ctx.unidades / u["unidad"]
        dest = ctx.unidades / f"{u['unidad']}.suspendido-{m['fecha']}"
        if not os.path.lexists(orig):
            if os.path.lexists(dest):
                u["hecho"], u["suspendido_como"] = True, dest.name
            else:
                cnr.append(f"{u['unidad']}: no esta ni en su nombre ni suspendida")
            continue
        if os.path.lexists(dest):
            cnr.append(f"{u['unidad']}: ya existe {dest.name}; no se pisa")
            continue
        os.rename(orig, dest)  # suspender = RENOMBRAR, nunca borrar; conserva dueno y modo
        u["hecho"], u["suspendido_como"] = True, dest.name
    reg.guarda()

    por_politica = [c for c in m["contenedores"] if not c["restart_cambiado"] and c["restart_policy"] != "no"]
    if por_politica:  # (4) que docker no los levante en el siguiente arranque
        rc, out, err = ej.corre(["docker", "update", "--restart=no", *[c["nombre"] for c in por_politica]],
                                T_DOCKER)
        hechos = set(out.split())
        for c in por_politica:
            if c["nombre"] in hechos:
                c["restart_cambiado"] = True
            else:
                cnr.append(f"docker update --restart=no {c['nombre']}: {motivo_de(rc, err)}")
        reg.guarda()

    # (5) lo vivo: docker stop en paralelo con systemctl
    a_parar = [c for c in m["contenedores"] if c["corriendo"] and not c["parado"]]
    docker_p = ej.lanza(["docker", "stop", "-t", str(DOCKER_STOP_T), *[c["nombre"] for c in a_parar]]) \
        if a_parar else None
    por_detener = [u["unidad"] for u in m["unidades"] if u["hecho"] and not u["detenida"]]
    if ctx.manager and por_detener:
        rc, _, err = ej.corre([*ctx.systemctl, "stop", "--no-block", "--", *por_detener], T_SYSTEMCTL)
        if rc == 0:
            for u in m["unidades"]:
                if u["unidad"] in por_detener:
                    u["detenida"] = True
        else:
            cnr.append(f"systemctl stop ({len(por_detener)} unidades): {motivo_de(rc, err)}"
                       " -- los archivos ya estan renombrados")
        rc, _, err = ej.corre([*ctx.systemctl, "daemon-reload"], T_RELOAD)
        if rc != 0:
            cnr.append(f"daemon-reload: {motivo_de(rc, err)}")
    scopes = scopes_vivos(ctx, ej, cnr)
    if docker_p is not None:
        rc, out, err = ej.espera(docker_p, T_DOCKER_STOP)
        parados = set(out.split())
        for c in a_parar:
            if c["nombre"] in parados:
                c["parado"] = True
            else:
                cnr.append(f"docker stop {c['nombre']}: {motivo_de(rc, err)}")

    completo = all(u["hecho"] for u in m["unidades"]) and all(
        c["parado"] or not c["corriendo"] for c in m["contenedores"]) and all(
        c["restart_cambiado"] or c["restart_policy"] == "no" for c in m["contenedores"])
    m["estado"] = "completo" if completo else "en_curso"
    m["corridas"][-1].update({"fin": ahora(), "could_not_run": cnr, "avisos": avisos})
    reg.guarda()

    corrida = m["corridas"][-1]
    if corrida["tipo"] == "primera corrida":
        unidades, conts = m["unidades"], m["contenedores"]
    else:
        nuevas_n = set(corrida["nuevas"])
        unidades = [u for u in m["unidades"] if u["unidad"] in nuevas_n]
        conts = [c for c in m["contenedores"] if c["nombre"] in nuevas_n]
        print(f"[{corrida['tipo']}] manifiesto existente {reg.ruta}; solo lo nuevo:")
    imprime(unidades, conts, quedan, scopes, avisos, cnr,
            titulo=f"SUSPENDIDO -- manifiesto {reg.ruta}", hechas=True)
    print(f"duracion: {time.monotonic() - t0:.2f} s")
    return 1 if cnr else 0


def imprime(unidades: list[Dic], conts: list[Dic], keep: list[str], scopes: list[str],
            avisos: list[str], cnr: list[str], titulo: str, hechas: bool) -> None:
    print(f"== {titulo}")
    for a in avisos:
        print(f"AVISO: {a}")
    print(f"\nUNIDADES {'suspendidas' if hechas else 'se suspenderian'}: {len(unidades)}")
    for u in unidades:
        marca = "  SIN CLASIFICAR" if u.get("sin_clasificar") else ""
        print(f"  {u['unidad']:<42} [{u['enabled']}/{u['active']}]{marca}")
    sin = [u["unidad"] for u in unidades if u.get("sin_clasificar")]
    print(f"  sin clasificar (ni KEEP ni [suspende]; decidir en {KEEP.name}): {len(sin)}")
    print(f"\nCONTENEDORES con GPU {'tratados' if hechas else 'a tratar'}: {len(conts)}")
    for c in conts:
        vivo = "corriendo -> docker stop" if c["corriendo"] else "parado"
        pol = "restart ya era no" if c["restart_policy"] == "no" else f"restart {c['restart_policy']} -> no"
        print(f"  {c['nombre']:<42} {vivo}; {pol}")
    print("  (contenedores sin GPU, bases de datos incluidas: no se tocan)")
    print(f"\nSE QUEDAN (KEEP): {len(keep)}")
    for k in keep:
        print(f"  {k}")
    print(f"\nSIGUEN CORRIENDO (scopes transitorios; no se matan): {len(scopes)}")
    for s in scopes:
        print(f"  {s}")
    print(f"\nCOULD_NOT_RUN: {len(cnr)}")
    for c in cnr:
        print(f"  {c}")
    print("\nRESTAURAR: sudo rojo restaura        (motor y contenedores GPU: sudo rojo restaura todo si)")


# --- restaura --------------------------------------------------------------


def verifica(u: Dic, dest: Path, orig: Path) -> str | None:
    """Motivo para NO tocar, o None si el archivo es el que se suspendio."""
    if not os.path.lexists(dest):
        return f"no existe {dest.name}"
    if os.path.lexists(orig):
        return f"ya existe {orig.name}; no se pisa"
    if u.get("enlace") is not None and (not dest.is_symlink() or os.readlink(dest) != u["enlace"]):
        return "el enlace no apunta a donde apuntaba"
    if sha256(dest) != u.get("sha256"):
        return f"sha256 distinto del manifiesto ({sha256(dest)} != {u.get('sha256')})"
    if modo(dest) != u.get("modo"):
        return f"modo distinto del manifiesto ({modo(dest)} != {u.get('modo')})"
    return None


def restaura(todo: bool, si: bool) -> int:
    ctx, ej = Ctx(), Ejecutor()
    vivos = [r for r in manifiestos(ctx) if lee(r).get("estado") != "restaurado"]
    if not vivos:
        print("COULD_NOT_RUN: no hay manifiesto del boton rojo pendiente de restaurar")
        return 2
    reg = Registro(ctx, vivos[-1], lee(vivos[-1]))
    m = reg.m
    cnr: list[str] = []
    motor_ok = todo and si
    print(f"== RESTAURA desde {reg.ruta}")

    for u in m["unidades"]:
        if not u["hecho"] or u["restaurado"]:
            continue
        orig = ctx.unidades / u["unidad"]
        dest = ctx.unidades / u.get("suspendido_como", "")
        motivo = verifica(u, dest, orig)
        if motivo:
            cnr.append(f"{u['unidad']}: NO se toca -- {motivo}")
            continue
        os.rename(dest, orig)
        u["restaurado"], u["pendiente_arranque"] = True, True
        print(f"  renombrada  {dest.name} -> {orig.name}")
    reg.guarda()

    motor_pendiente: list[str] = []
    if not ctx.manager:
        cnr.append(f"manager de usuario de {ctx.usuario} abajo: archivos restaurados, "
                   "enable/start pendientes (repetir `sudo rojo restaura` con la sesion arriba)")
    else:
        rc, _, err = ej.corre([*ctx.systemctl, "daemon-reload"], T_RELOAD)
        if rc != 0:
            cnr.append(f"daemon-reload: {motivo_de(rc, err)}")
        for u in m["unidades"]:
            if not u.get("pendiente_arranque"):
                continue
            nombre = u["unidad"]
            if casa(nombre, MOTOR) and not motor_ok:
                motor_pendiente.append(nombre)
                continue
            actual = estados(ctx, ej, [nombre], cnr).get(nombre, ("desconocido", "desconocido"))
            if u["enabled"] == "enabled" and actual[0] != "enabled":
                rc, _, err = ej.corre([*ctx.systemctl, "enable", "--", nombre], T_SYSTEMCTL)
                print(f"  enable      {nombre}: rc={rc}")
                if rc != 0:
                    cnr.append(f"{nombre}: enable -> {motivo_de(rc, err)}")
            if u["active"] in ("active", "activating", "reloading") and actual[1] not in ("active", "activating"):
                rc, _, err = ej.corre([*ctx.systemctl, "start", "--no-block", "--", nombre], T_SYSTEMCTL)
                print(f"  start       {nombre}: rc={rc}")
                if rc != 0:
                    cnr.append(f"{nombre}: start -> {motivo_de(rc, err)}")
                    continue
            else:
                print(f"  sin arranque {nombre}: antes {u['enabled']}/{u['active']}, ahora {actual[0]}/{actual[1]}")
            u["pendiente_arranque"] = False
            reg.guarda()

    for c in m["contenedores"]:
        if c["restaurado"]:
            continue
        if not (c["restart_cambiado"] or c["parado"]):
            c["restaurado"] = True
            continue
        if not motor_ok:
            motor_pendiente.append(f"contenedor {c['nombre']}")
            continue
        ok = True
        if c["restart_cambiado"]:
            rc, _, err = ej.corre(["docker", "update", f"--restart={c['restart_policy']}", c["nombre"]], T_DOCKER)
            print(f"  docker update --restart={c['restart_policy']} {c['nombre']}: rc={rc}")
            if rc != 0:
                ok = False
                cnr.append(f"docker update {c['nombre']}: {motivo_de(rc, err)}")
        if ok and c["parado"]:
            rc, _, err = ej.corre(["docker", "start", c["nombre"]], T_DOCKER_STOP)
            print(f"  docker start {c['nombre']}: rc={rc}")
            if rc != 0:
                ok = False
                cnr.append(f"docker start {c['nombre']}: {motivo_de(rc, err)}")
        c["restaurado"] = ok
        reg.guarda()

    hecho = all(u["restaurado"] or not u["hecho"] for u in m["unidades"])
    hecho = hecho and not any(u.get("pendiente_arranque") for u in m["unidades"])
    hecho = hecho and all(c["restaurado"] for c in m["contenedores"])
    m["estado"] = "restaurado" if hecho else "restaurado_parcial"
    m.setdefault("restauraciones", []).append({"fecha": ahora(), "could_not_run": cnr})
    reg.guarda()
    if hecho:
        try:
            ctx.marca.unlink(missing_ok=True)
        except OSError as e:
            cnr.append(f"no se pudo quitar la marca {ctx.marca}: {e}")

    print(f"\nMOTOR sin arrancar (falta `todo si`): {len(motor_pendiente)}")
    for x in motor_pendiente:
        print(f"  {x}")
    if motor_pendiente:
        print("  para arrancarlo: sudo rojo restaura todo si")
    print(f"\nCOULD_NOT_RUN: {len(cnr)}")
    for x in cnr:
        print(f"  {x}")
    print(f"\nmanifiesto: {reg.ruta}  estado={m['estado']}")
    return 1 if cnr else 0


# --- estado ----------------------------------------------------------------


def estado() -> int:
    ctx = Ctx()
    try:
        print(f"marca {ctx.marca}: PULSADO -- {ctx.marca.read_text(encoding='utf-8').strip()}")
    except FileNotFoundError:
        print(f"marca {ctx.marca}: no existe (boton sin pulsar)")
    except OSError as e:
        print(f"marca {ctx.marca}: ilegible ({e})")
    rutas = manifiestos(ctx)
    print(f"manifiestos del boton rojo: {len(rutas)}")
    hoy = dt.date.today().isoformat()
    for r in rutas:
        m = lee(r)
        vencida = "  VENCIDA" if m.get("vence", "9999") < hoy and m.get("estado") != "restaurado" else ""
        susp = [u["unidad"] for u in m["unidades"] if u["hecho"] and not u["restaurado"]]
        conts = [c["nombre"] for c in m["contenedores"]
                 if (c["parado"] or c["restart_cambiado"]) and not c["restaurado"]]
        print(f"\n{r}: estado={m.get('estado')} desde={m.get('creado')} vence={m.get('vence')}{vencida}")
        print(f"  unidades suspendidas: {len(susp)}")
        for s in susp:
            print(f"    {s}")
        print(f"  contenedores tocados por el boton: {len(conts)}")
        for c in conts:
            print(f"    {c}")
    return 0


PALABRAS = {"seco": "--seco", "todo": "--todo", "si": "--si"}


def main(argv: list[str] | None = None) -> int:
    argv = [PALABRAS.get(a, a) for a in (sys.argv[1:] if argv is None else argv)]
    ap = argparse.ArgumentParser(prog="rojo", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("accion", nargs="?", choices=["restaura", "estado"])
    ap.add_argument("--seco", action="store_true", help="imprime el plan, no toca nada")
    ap.add_argument("--todo", action="store_true", help="restaura tambien el motor (pide --si)")
    ap.add_argument("--si", action="store_true", help="confirma arrancar el motor")
    ap.add_argument("--keep", type=Path, default=KEEP, help="lista KEEP")
    ap.add_argument("--motivo", default="boton rojo: megacrash")
    a = ap.parse_args(argv)
    if a.accion == "restaura":
        return restaura(a.todo, a.si)
    if a.accion == "estado":
        return estado()
    return suspende(a.seco, a.keep, a.motivo)


if __name__ == "__main__":
    sys.exit(main())
