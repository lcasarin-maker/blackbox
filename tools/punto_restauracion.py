"""Punto de restauracion: registro de la maquina SANA y jalando, al que `sudo panic` regresa (docs/PANIC.md).

Pedido de Luis (2026-11-03): "como un restore point en un videojuego: si mañana subimos el kernel a 7 de
nuevo y se cae, sudo panic me regresa". El bucle de reinicios del 2026-11-02/03 (arranques de 3 a 242 s con
7.0.0-1024-nvidia; timeout del GSP y Xid 154 a los 21-28 s) no lo corto suspender unidades: lo corto
arrancar 6.17.0-1032-nvidia. Por eso el punto guarda, ante todo, QUE kernel arranca y COMO lo elige GRUB.

    punto_restauracion.py crea          (bb-punto-restauracion.timer, cada 30 min, como root)
    punto_restauracion.py arranque-ok   (bb-arranque-ok.timer, 180 s tras arrancar, como root)

`crea` escribe /var/lib/blackbox/restore/<AAAA-MM-DDTHH-MM>/punto.json (esquema bb-restore-point/1) SOLO si
este arranque demuestra estar sano: uptime >= 6 h; en `journalctl -k -b <boot_id>` ni `rpcRecvPoll timedout`
ni `Xid ...: 154` (tools/reboot_verdict.gpu_del_boot) ni Oops/BUG/Call Trace. Un CORTE_ABRUPTO del arranque
anterior (reboots.jsonl) se registra y no niega el punto. Un punto identico al ultimo valido (mismo kernel,
misma entrada de GRUB, mismos sha256) no se repite; se conservan los 3 validos mas recientes. Al crear un punto
con un kernel que ningun otro punto vigente tiene, `apt-mark hold` de sus paquetes (que ni apt ni autoremove lo
quiten); al podar, `apt-mark unhold` de los que retuvo esta herramienta y ya ningun punto usa. Un punto cuyo
kernel, modulos, copia o entrada de GRUB ya no existen se marca `invalido` y nunca se elige. Tras cada corrida
`bb_punto_entry` del grubenv nombra la entrada del punto valido mas reciente (o se quita si no hay ninguno):
es lo que lee /etc/grub.d/09_bb_zautoarmado.

`arranque-ok` baja el contador del autoarmado (`bb_intentos=0`) cuando el arranque DEMUESTRA ser bueno: lleva
>= 180 s y su journal de kernel no tiene la firma del GSP (timeout de RPC ni Xid 154). Esa segunda condicion
va mas alla del brief a proposito: un arranque del bucle duro 242 s, asi que 180 s solos lo darian por bueno.
Registra una linea por corrida en /var/lib/blackbox/arranque-ok.jsonl y, si GRUB dejo `bb_autoarmado=1`, lo
anota y lo quita.

Root y biblioteca estandar: se instala como COPIA root-owned en /usr/local/lib/blackbox/tools/ y corre con
`python3 -I` (sin el directorio actual ni PYTHON* en sys.path); nunca se ejecuta el repo como root. Pruebas:
BB_ROJO_RAIZ=<dir> antepone una raiz falsa a toda ruta (como tools/boton_rojo.py) y cada comando de la maquina
es un shim en PATH (tests/test_punto_restauracion.py).

rc: 0 bien (con o sin punto nuevo); 1 hubo could_not_run o el arranque no es bueno (arranque-ok); 2 no pudo
empezar (no es root).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):  # `python3 -I .../tools/punto_restauracion.py`: -I no pone el directorio en sys.path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import boton_rojo as br  # noqa: E402
from tools import modulo_nvidia_registro as mnr  # noqa: E402
from tools.reboot_verdict import gpu_del_boot  # noqa: E402

ESQUEMA = "bb-restore-point/1"
ESQUEMA_OK = "bb-arranque-ok/1"
SANO_MIN_S = 6 * 3600
OK_MIN_S = 180
CONSERVA = 3
T_CMD = 30
T_JOURNAL = 120
T_APT = 120
NOMBRE_PUNTO = re.compile(r"^\d{4}-\d\d-\d\dT\d\d-\d\d$")
OOPS = re.compile(r"\bOops\b|\bBUG:|Call Trace")
PAQUETES_KERNEL = ("linux-image-{v}", "linux-modules-nvidia-580-open-{v}", "linux-modules-nvidia-fs-{v}")
PAQUETES_FIJOS = ("nvidia-driver-580-open",)
# Lo que grub-mkconfig hace con la configuracion: /etc/default/grub y DESPUES /etc/default/grub.d/*.cfg en orden
# de glob (/usr/sbin/grub-mkconfig, lineas 160-168 en GRUB 2.12-1ubuntu7.3). Lo ultimo que asigna, gana.
SIMULA_DEFAULT = (
    'r=$1; GRUB_DEFAULT=; '
    '{ [ ! -f "$r/etc/default/grub" ] || . "$r/etc/default/grub"; '
    'for x in "$r"/etc/default/grub.d/*.cfg; do [ ! -e "$x" ] || . "$x"; done; } </dev/null >/dev/null 2>&1; '
    'printf %s "$GRUB_DEFAULT"'
)
Dic = dict[str, Any]
en_raiz = br.en_raiz


def restore_dir() -> Path:
    return en_raiz("/var/lib/blackbox/restore")


def grubenv_ruta() -> Path:
    return en_raiz("/boot/grub/grubenv")


def grub_cfg_ruta() -> Path:
    return en_raiz("/boot/grub/grub.cfg")


def ahora() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def nombre_nuevo() -> str:
    """Nombre del punto: minuto local (`AAAA-MM-DDTHH-MM`), el formato del brief; ordena igual que el tiempo."""
    return dt.datetime.now().strftime("%Y-%m-%dT%H-%M")


def _lee(ruta: Path) -> str | None:
    try:
        return ruta.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _norm(boot_id: str) -> str:
    return boot_id.strip().replace("-", "").lower()


def boot_id() -> str | None:
    t = _lee(en_raiz("/proc/sys/kernel/random/boot_id"))
    return _norm(t) if t and t.strip() else None


def kernel() -> str | None:
    t = _lee(en_raiz("/proc/sys/kernel/osrelease"))
    return t.strip() if t and t.strip() else None


def uptime() -> float | None:
    t = _lee(en_raiz("/proc/uptime"))
    try:
        return float(t.split()[0]) if t else None
    except (ValueError, IndexError):
        return None


def anexa(ruta: Path, fila: Dic) -> None:
    """Solo-anexar, con fsync: la linea tiene que sobrevivir al corte que venga."""
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(fila, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


# --- grubenv y grub.cfg ----------------------------------------------------


def grubenv_lista(ej: br.Ejecutor, cnr: list[str]) -> dict[str, str] | None:
    rc, out, err = ej.corre(["grub-editenv", str(grubenv_ruta()), "list"], T_CMD)
    if rc != 0:
        cnr.append(f"grub-editenv list: {br.motivo_de(rc, err)}")
        return None
    return dict(ln.split("=", 1) for ln in out.splitlines() if "=" in ln)


def grubenv_cambia(ej: br.Ejecutor, cnr: list[str], accion: str, *args: str) -> bool:
    """`grub-editenv <grubenv> set k=v ...` o `unset k ...`. False (y could_not_run) si no se pudo."""
    rc, _, err = ej.corre(["grub-editenv", str(grubenv_ruta()), accion, *args], T_CMD)
    if rc != 0:
        cnr.append(f"grub-editenv {accion} {' '.join(args)}: {br.motivo_de(rc, err)}")
    return rc == 0


_ENTRADA = re.compile(r"""^\s*(submenu|menuentry)\s+'((?:[^']|'\\'')*)'.*\$menuentry_id_option\s+'([^']+)'""")
_VARIABLE = re.compile(r"\$\{[^}]*\}")


def entradas_grub(texto: str) -> list[Dic]:
    """Cada menuentry de grub.cfg con su id y la ruta de ids que la elige (`<submenu>><entrada>`)."""
    fuera: list[Dic] = []
    pila: list[tuple[int, str]] = []  # (profundidad de llaves al abrir, id del submenu)
    prof = 0
    for ln in texto.splitlines():
        m = _ENTRADA.match(ln)
        if m and m.group(1) == "menuentry":
            ids = [s for _, s in pila] + [m.group(3)]
            fuera.append({"titulo": m.group(2), "id": m.group(3), "ruta_id": ">".join(ids),
                          "submenu_id": pila[-1][1] if pila else None})
        limpio = _VARIABLE.sub("", ln)
        abre, cierra = limpio.count("{"), limpio.count("}")
        if m and m.group(1) == "submenu":
            pila.append((prof, m.group(3)))
        prof += abre - cierra
        while pila and prof <= pila[-1][0]:
            pila.pop()
    return fuera


def entrada_del_kernel(texto: str, version: str) -> Dic | None:
    """La entrada normal (no recovery) que arranca `version`: id `gnulinux-<version>-advanced-<uuid>`."""
    patron = re.compile(r"^gnulinux-" + re.escape(version) + r"-advanced-")
    return next((e for e in entradas_grub(texto) if patron.match(e["id"])), None)


def grub_default_efectivo() -> str | None:
    """GRUB_DEFAULT tal como lo deja grub-mkconfig tras leer default/grub y default/grub.d/*.cfg en orden."""
    raiz = os.environ.get("BB_ROJO_RAIZ") or ""
    try:
        p = subprocess.run(["/bin/sh", "-c", SIMULA_DEFAULT, "sh", raiz], capture_output=True, text=True,
                           errors="replace", timeout=10, env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"})
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout if p.returncode == 0 else None


# --- salud del arranque ----------------------------------------------------


def journal_kernel(ej: br.Ejecutor, bid: str) -> list[str] | None:
    rc, out, _ = ej.corre(["journalctl", "-k", "-b", bid, "-o", "short-monotonic", "--no-pager", "-q"], T_JOURNAL)
    return out.splitlines() if rc == 0 else None


def arranque_anterior(ctx: br.Ctx, bid: str) -> str | None:
    """Etiqueta de reboots.jsonl del arranque que termino justo antes de este (su boot_id_siguiente = este)."""
    texto = _lee(ctx.home / ".local/share/blackbox/reboots.jsonl")
    if not texto:
        return None
    filas: dict[str, Dic] = {}
    for ln in texto.splitlines():
        try:
            f = json.loads(ln)
        except ValueError:
            continue
        if not isinstance(f, dict) or "boot_id" not in f:
            continue
        if f.get("anula"):
            filas.pop(_norm(str(f["boot_id"])), None)
        else:
            filas[_norm(str(f["boot_id"]))] = f
    previas = [f for f in filas.values() if _norm(str(f.get("boot_id_siguiente") or "")) == bid]
    return str(previas[-1].get("etiqueta")) if previas else None


def salud(ctx: br.Ctx, ej: br.Ejecutor, minimo_s: float, estricto: bool) -> Dic:
    """sano=True solo con todas las pruebas leidas y pasadas: lo que no se pudo leer niega, no aprueba."""
    motivos: list[str] = []
    avisos: list[str] = []
    bid = boot_id()
    up = uptime()
    res: Dic = {"boot_id": bid, "uptime_s": up, "minimo_s": minimo_s, "gpu": None, "oops": None,
                "arranque_anterior": None}
    if bid is None:
        motivos.append("boot_id ilegible")
    if up is None:
        motivos.append("/proc/uptime ilegible")
    elif up < minimo_s:
        motivos.append(f"uptime {up:.0f} s < {minimo_s:.0f} s")
    if not motivos and bid is not None:
        lineas = journal_kernel(ej, bid)
        if lineas is None:
            motivos.append(f"journalctl -k -b {bid} no corrio: no se puede juzgar")
        elif not lineas:
            motivos.append(f"journal de kernel de {bid} vacio: no se puede juzgar")
        else:
            g = gpu_del_boot(lineas)
            res["gpu"] = g
            if g["gsp_timeout"]:
                motivos.append(f"GSP: rpcRecvPoll timedout desde el segundo {g['gsp_timeout_monotonic_s']}")
            if g["xid154"]:
                motivos.append("Xid 154 en el journal de kernel")
            if estricto:
                res["oops"] = n = sum(1 for ln in lineas if OOPS.search(ln))
                if n:
                    motivos.append(f"{n} lineas Oops/BUG/Call Trace en el journal de kernel")
    if bid is not None:
        res["arranque_anterior"] = previo = arranque_anterior(ctx, bid)
        if previo == "CORTE_ABRUPTO":
            avisos.append("el arranque anterior acabo en CORTE_ABRUPTO (reboots.jsonl): se registra, no niega")
    res.update({"sano": not motivos, "motivos": motivos, "avisos": avisos})
    return res


# --- lo que guarda un punto ------------------------------------------------


def archivos_grub() -> list[str]:
    """Rutas (logicas, sin raiz) de la configuracion de GRUB que el punto copia."""
    rutas = ["/etc/default/grub"] if en_raiz("/etc/default/grub").is_file() else []
    for d, patron in (("/etc/default/grub.d", "*"), ("/etc/grub.d", "*_bb_*")):
        try:
            rutas += [f"{d}/{f.name}" for f in sorted(en_raiz(d).glob(patron)) if f.is_file()]
        except OSError:
            pass
    return rutas


def modulo_nvidia() -> Dic:
    """El nvidia.ko de este kernel (tools/modulo_nvidia_registro), con las rutas bajo la raiz de las pruebas."""
    ruta = mnr._modinfo("-n")  # pyright: ignore[reportPrivateUsage]
    legible = not ruta.startswith("NOT_COLLECTED")
    sysm = en_raiz("/sys/module/nvidia")
    sha = br.sha256(en_raiz(ruta)) if legible else None
    return {
        "ruta": ruta,
        "sha256": sha or mnr._nc("sin ruta legible del modulo"),  # pyright: ignore[reportPrivateUsage]
        "version": mnr._lee(sysm / "version"),  # pyright: ignore[reportPrivateUsage]
        "srcversion": mnr._lee(sysm / "srcversion"),  # pyright: ignore[reportPrivateUsage]
        "srcversion_archivo": mnr._modinfo("srcversion"),  # pyright: ignore[reportPrivateUsage]
    }


def paquetes_de(version: str) -> list[str]:
    return [p.format(v=version) for p in PAQUETES_KERNEL]


def versiones(ej: br.Ejecutor, cnr: list[str], paquetes: list[str]) -> dict[str, str | None]:
    """Version instalada de cada paquete; None si no esta instalado. dpkg-query sale 1 si alguno no existe."""
    res: dict[str, str | None] = dict.fromkeys(paquetes)
    rc, out, err = ej.corre(["dpkg-query", "-W", "-f=${Package}\t${Version}\t${Status}\n", *paquetes], T_CMD)
    if rc not in (0, 1):
        cnr.append(f"dpkg-query: {br.motivo_de(rc, err)}")
        return res
    for ln in out.splitlines():
        partes = ln.split("\t")
        if len(partes) == 3 and partes[0] in res and partes[2].endswith(" installed"):
            res[partes[0]] = partes[1]
    return res


def unidades_usuario(ctx: br.Ctx, ej: br.Ejecutor, cnr: list[str]) -> list[Dic]:
    nombres = [f.name for f in br.escanea(ctx.unidades)]
    est = br.estados(ctx, ej, nombres, cnr)
    return [{"unidad": n, "enabled": est.get(n, ("desconocido",))[0],
             "active": est.get(n, ("", "desconocido"))[1]} for n in nombres]


def unidades_sistema_bb(ej: br.Ejecutor, cnr: list[str]) -> list[Dic]:
    rc, out, err = ej.corre(["systemctl", "list-unit-files", "bb-*", "--no-legend", "--plain", "--no-pager"], T_CMD)
    if rc != 0:
        cnr.append(f"systemctl list-unit-files bb-*: {br.motivo_de(rc, err)}")
        return []
    return [{"unidad": p[0], "estado": p[1]} for p in (ln.split() for ln in out.splitlines()) if len(p) >= 2]


def politicas_docker(ej: br.Ejecutor, cnr: list[str]) -> list[Dic]:
    rc, out, err = ej.corre(["docker", "ps", "-aq"], br.T_DOCKER)
    if rc != 0:
        cnr.append(f"docker ps: {br.motivo_de(rc, err)}")
        return []
    if not out.split():
        return []
    rc, out, err = ej.corre(["docker", "inspect", *out.split()], br.T_DOCKER)
    if rc != 0:
        cnr.append(f"docker inspect: {br.motivo_de(rc, err)}")
        return []
    return [{"nombre": c.get("Name", "").lstrip("/"),
             "restart_policy": ((c.get("HostConfig") or {}).get("RestartPolicy") or {}).get("Name") or "no"}
            for c in json.loads(out)]


# --- puntos: validez, eleccion, poda ---------------------------------------


def lee_punto(d: Path) -> Dic | None:
    try:
        p = json.loads((d / "punto.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return p if isinstance(p, dict) and p.get("esquema") == ESQUEMA else None


def guarda_punto(d: Path, p: Dic) -> None:
    br.escribe(d / "punto.json", json.dumps(p, ensure_ascii=False, indent=1) + "\n")


def motivo_invalido(d: Path, p: Dic, cfg: str | None) -> str | None:
    """Por que este punto ya no sirve para volver, o None si sirve. Solo lee."""
    k = p.get("kernel") or ""
    if not en_raiz(f"/boot/vmlinuz-{k}").is_file():
        return f"no existe /boot/vmlinuz-{k}"
    if not en_raiz(f"/lib/modules/{k}").is_dir():
        return f"no existe /lib/modules/{k}"
    ruta_nv = str((p.get("nvidia") or {}).get("ruta") or "")
    if ruta_nv.startswith("/") and not en_raiz(ruta_nv).is_file():
        return f"no existe el modulo nvidia del punto ({ruta_nv})"
    for a in p.get("archivos") or []:
        if br.sha256(d / a["copia"]) != a["sha256"]:
            return f"la copia de {a['ruta']} falta o no tiene el sha256 del punto"
    entrada = (p.get("grub") or {}).get("entry_id")
    if not entrada:
        return "el punto no tiene entrada de GRUB"
    if cfg is not None and entrada not in {e["id"] for e in entradas_grub(cfg)}:
        return f"la entrada {entrada} ya no esta en /boot/grub/grub.cfg"
    return None


def revisa_puntos(cnr: list[str]) -> list[tuple[Path, Dic]]:
    """Todos los puntos, del mas reciente al mas viejo; marca `invalido` (persistente) los que ya no sirven."""
    raiz = restore_dir()
    try:
        dirs = sorted((d for d in raiz.iterdir() if d.is_dir() and NOMBRE_PUNTO.match(d.name)), reverse=True)
    except OSError:
        return []
    cfg = _lee(grub_cfg_ruta())
    if cfg is None:
        cnr.append(f"{grub_cfg_ruta()} ilegible: no se comprueba que la entrada de cada punto siga en el menu")
    puntos: list[tuple[Path, Dic]] = []
    for d in dirs:
        p = lee_punto(d)
        if p is None:
            cnr.append(f"{d}/punto.json ilegible o de otro esquema: no se elige")
            continue
        if not p.get("invalido"):
            motivo = motivo_invalido(d, p, cfg)
            if motivo:
                p["invalido"] = {"motivo": motivo, "fecha": ahora()}
                try:
                    guarda_punto(d, p)
                except OSError as e:
                    cnr.append(f"no se pudo marcar invalido {d.name}: {e}")
        puntos.append((d, p))
    return puntos


def validos(puntos: list[tuple[Path, Dic]]) -> list[tuple[Path, Dic]]:
    return [(d, p) for d, p in puntos if not p.get("invalido")]


def publica_entrada(ej: br.Ejecutor, cnr: list[str], puntos: list[tuple[Path, Dic]]) -> str | None:
    """Deja `bb_punto_entry` del grubenv en la entrada del punto valido mas reciente (o la quita)."""
    if not grubenv_ruta().is_file():
        cnr.append(f"no existe {grubenv_ruta()}: bb_punto_entry sin publicar")
        return None
    env = grubenv_lista(ej, cnr)
    if env is None:
        return None
    v = validos(puntos)
    quiere = v[0][1]["grub"]["ruta_id"] if v else None
    if env.get("bb_punto_entry") != quiere:
        if quiere is None:
            grubenv_cambia(ej, cnr, "unset", "bb_punto_entry")
        else:
            grubenv_cambia(ej, cnr, "set", f"bb_punto_entry={quiere}")
    return quiere


def apt_mark(ej: br.Ejecutor, cnr: list[str], accion: str, paquetes: list[str]) -> bool:
    if not paquetes:
        return True
    rc, _, err = ej.corre(["apt-mark", accion, *paquetes], T_APT)
    if rc != 0:
        cnr.append(f"apt-mark {accion} {' '.join(paquetes)}: {br.motivo_de(rc, err)}")
    return rc == 0


def retenidos(ej: br.Ejecutor, cnr: list[str]) -> set[str] | None:
    rc, out, err = ej.corre(["apt-mark", "showhold"], T_APT)
    if rc != 0:
        cnr.append(f"apt-mark showhold: {br.motivo_de(rc, err)}")
        return None
    return set(out.split())


def poda(ej: br.Ejecutor, cnr: list[str], puntos: list[tuple[Path, Dic]]) -> list[tuple[Path, Dic]]:
    """Conserva los CONSERVA validos mas recientes (y los invalidos mas nuevos que el ultimo de ellos).

    Lo que esta herramienta retuvo con apt-mark (`hold_por_bb`) se suelta solo cuando ningun punto que queda
    usa ese kernel. Devuelve los puntos que quedan.
    """
    quedan: list[tuple[Path, Dic]] = []
    fuera: list[tuple[Path, Dic]] = []
    n = 0
    for d, p in puntos:
        if n >= CONSERVA:
            fuera.append((d, p))
            continue
        quedan.append((d, p))
        n += 0 if p.get("invalido") else 1
    vivos = {p.get("kernel") for _, p in validos(quedan)}
    soltar = sorted({pk for _, p in fuera if p.get("kernel") not in vivos for pk in p.get("hold_por_bb") or []})
    if apt_mark(ej, cnr, "unhold", soltar) and soltar:
        print(f"apt-mark unhold (ningun punto vigente usa ese kernel): {' '.join(soltar)}")
    for d, _ in fuera:
        shutil.rmtree(d)
        print(f"podado: {d.name}")
    return quedan


def firma(k: str, ruta_id: str, archivos: list[Dic], nvidia_sha: str) -> str:
    base = {"kernel": k, "entrada": ruta_id, "archivos": {a["ruta"]: a["sha256"] for a in archivos},
            "nvidia": nvidia_sha}
    return hashlib.sha256(json.dumps(base, sort_keys=True).encode()).hexdigest()


# --- crea ------------------------------------------------------------------


def crea() -> int:
    ctx, ej = br.Ctx(), br.Ejecutor()
    cnr: list[str] = []
    puntos = revisa_puntos(cnr)
    s = salud(ctx, ej, SANO_MIN_S, estricto=True)
    for a in s["avisos"]:
        print(f"AVISO: {a}")
    k = kernel()
    cfg = _lee(grub_cfg_ruta())
    entrada = entrada_del_kernel(cfg, k) if cfg is not None and k else None
    if not s["sano"]:
        print("SIN PUNTO NUEVO: este arranque no demuestra estar sano -- " + "; ".join(s["motivos"]))
    elif k is None:
        cnr.append("/proc/sys/kernel/osrelease ilegible: sin punto nuevo")
    elif entrada is None:
        cnr.append(f"sin entrada gnulinux-{k}-advanced-* en {grub_cfg_ruta()}: sin punto nuevo")
    else:
        puntos = _crea(ctx, ej, cnr, puntos, s, k, entrada, cfg or "")
    quiere = publica_entrada(ej, cnr, puntos)
    print(f"bb_punto_entry: {quiere or '(ninguno: no hay punto valido)'}")
    print(f"puntos validos: {len(validos(puntos))} de {len(puntos)}")
    print(f"COULD_NOT_RUN: {len(cnr)}")
    for c in cnr:
        print(f"  {c}")
    return 1 if cnr else 0


def _crea(ctx: br.Ctx, ej: br.Ejecutor, cnr: list[str], puntos: list[tuple[Path, Dic]], s: Dic, k: str,
          entrada: Dic, cfg: str) -> list[tuple[Path, Dic]]:
    archivos = [{"ruta": r, "sha256": br.sha256(en_raiz(r)), "modo": br.modo(en_raiz(r)),
                 "copia": "archivos" + r} for r in archivos_grub()]
    nv = modulo_nvidia()
    f = firma(k, entrada["ruta_id"], archivos, str(nv["sha256"]))
    v = validos(puntos)
    if v and v[0][1].get("firma") == f:
        print(f"SIN CAMBIOS: el punto {v[0][0].name} ya guarda este kernel, esta entrada y estos sha256")
        return puntos
    nombre = nombre_nuevo()
    dest = restore_dir() / nombre
    if dest.exists():
        print(f"AVISO: ya hay un punto {nombre}; el siguiente minuto lo intenta otra vez")
        return puntos
    env = grubenv_lista(ej, cnr) if grubenv_ruta().is_file() else None
    tmp = restore_dir() / f".{nombre}.tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    for a in archivos:
        copia = tmp / a["copia"]
        copia.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(en_raiz(a["ruta"]), copia)
    interruptores = ctx.home / ".local/share/blackbox/interruptores.json"
    copia_int = None
    if interruptores.is_file():
        shutil.copy2(interruptores, tmp / "interruptores.json")
        copia_int = {"copia": "interruptores.json", "sha256": br.sha256(tmp / "interruptores.json")}
    p: Dic = {
        "esquema": ESQUEMA, "nombre": nombre, "creado": ahora(), "firma": f, "boot_id": s["boot_id"],
        "kernel": k,
        "grub": {"entry_id": entrada["id"], "submenu_id": entrada["submenu_id"], "ruta_id": entrada["ruta_id"],
                 "titulo": entrada["titulo"], "grub_default_efectivo": grub_default_efectivo(), "grubenv": env},
        "archivos": archivos,
        "nvidia": nv,
        "paquetes": versiones(ej, cnr, [*paquetes_de(k), *PAQUETES_FIJOS]),
        "unidades_usuario": unidades_usuario(ctx, ej, cnr),
        "unidades_sistema_bb": unidades_sistema_bb(ej, cnr),
        "docker": politicas_docker(ej, cnr),
        "interruptores": copia_int,
        "salud": s,
        "hold_por_bb": [],
        "invalido": None,
    }
    motivo = motivo_invalido(tmp, p, cfg)  # el mismo criterio que lo invalidaria luego: no nace ya muerto
    if motivo:
        shutil.rmtree(tmp)
        cnr.append(f"el punto nuevo no serviria para volver ({motivo}): no se crea")
        return puntos
    otros = [q for _, q in v if q.get("kernel") == k]
    if otros:  # el kernel ya lo retiene otro punto: este hereda la responsabilidad de soltarlo
        p["hold_por_bb"] = list(otros[0].get("hold_por_bb") or [])
    else:
        instalados = [n for n in paquetes_de(k) if p["paquetes"].get(n)]
        ya = retenidos(ej, cnr)
        if ya is not None:
            nuevos = [n for n in instalados if n not in ya]
            if apt_mark(ej, cnr, "hold", nuevos):
                p["hold_por_bb"] = nuevos
                if nuevos:
                    print(f"apt-mark hold (kernel nuevo en un punto): {' '.join(nuevos)}")
    p["could_not_run"] = list(cnr)
    guarda_punto(tmp, p)
    os.rename(tmp, dest)
    br._fsync_dir(dest.parent)  # pyright: ignore[reportPrivateUsage]
    print(f"PUNTO NUEVO: {dest} kernel {k} entrada {entrada['ruta_id']}")
    return poda(ej, cnr, [(dest, p), *puntos])


# --- arranque-ok -----------------------------------------------------------


def arranque_ok() -> int:
    ctx, ej = br.Ctx(), br.Ejecutor()
    cnr: list[str] = []
    s = salud(ctx, ej, OK_MIN_S, estricto=False)
    env = grubenv_lista(ej, cnr) or {}
    fila: Dic = {
        "esquema": ESQUEMA_OK, "fecha": ahora(), "boot_id": s["boot_id"], "kernel": kernel(),
        "sano": s["sano"], "motivos": s["motivos"], "bb_intentos_antes": env.get("bb_intentos"),
        "autoarmado": env.get("bb_autoarmado") == "1", "bb_punto_entry": env.get("bb_punto_entry"),
        "bb_intentos_a_0": False,
    }
    if s["sano"]:
        fila["bb_intentos_a_0"] = grubenv_cambia(ej, cnr, "set", "bb_intentos=0")
    if fila["autoarmado"]:
        grubenv_cambia(ej, cnr, "unset", "bb_autoarmado")
    fila["could_not_run"] = cnr
    try:
        anexa(en_raiz("/var/lib/blackbox/arranque-ok.jsonl"), fila)
    except OSError as e:
        cnr.append(f"arranque-ok.jsonl: {e}")
    print(json.dumps(fila, ensure_ascii=False))
    return 0 if s["sano"] and not cnr else 1


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if os.geteuid() != 0 and not os.environ.get("BB_ROJO_RAIZ"):
        print("COULD_NOT_RUN: necesita root (lo corren bb-punto-restauracion y bb-arranque-ok como root)")
        return 2
    if args == ["crea"]:
        return crea()
    if args == ["arranque-ok"]:
        return arranque_ok()
    print("uso: punto_restauracion.py crea | arranque-ok")
    return 2


if __name__ == "__main__":
    sys.exit(main())
