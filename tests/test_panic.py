"""`sudo panic` y el punto de restauracion (tools/panic.py, tools/punto_restauracion.py) contra una ATOM falsa.

Raiz falsa (BB_ROJO_RAIZ) y PATH con SOLO shims: un comando sin shim no existe, asi que ninguna prueba puede
llegar a grub-editenv, grub-set-default, apt-mark o update-grub de verdad. Cada shim anota su argv en SHIM_LOG.
El grubenv es un modelo del de GRUB (bloque de 1024 bytes, `# GRUB Environment Block`).

Controles negativos (cada criterio tiene su caso que DEBE bloquear):
  - el punto se niega con uptime corto, con la firma del GSP, con Xid 154, con Oops/BUG/Call Trace y con el
    journal ilegible; el mismo arranque con el journal limpio SI crea punto;
  - arranque-ok no baja el contador con la firma del GSP ni antes de 180 s;
  - panic sin punto valido lo dice (COULD_NOT_RUN) y no toca el kernel; un punto invalido no se elige;
  - grub-script-check que rechaza deja grub.cfg intacto.
"""

from __future__ import annotations

import getpass
import json
import os
import pwd
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.test_boton_rojo import DOCKER, SYSTEMCTL, UNIDADES
from tools import boton_rojo as br
from tools import panic
from tools import punto_restauracion as pr

pytestmark = pytest.mark.integration

UUID = "0f0e0d0c-0b0a-4908-8706-050403020100"
BUENO = "6.17.0-1032-nvidia"
MALO = "7.0.0-1024-nvidia"
SUB = f"gnulinux-advanced-{UUID}"
RUTA_BUENO = f"{SUB}>gnulinux-{BUENO}-advanced-{UUID}"
LIMPIO = "[    0.000000] Booting Linux on physical CPU 0x0000000000 [0x410fd8c0]\n[    5.1] nvidia: loaded\n"

SHIM = r'''
import json, os, sys, time
prog = os.path.basename(sys.argv[0]); a = sys.argv[1:]
with open(os.environ["SHIM_LOG"], "a") as fh:
    fh.write(json.dumps({"argv": [prog] + a, "t": time.time()}) + "\n")
st_path = os.environ["SHIM_ATOM"]
st = json.load(open(st_path))
if prog in st.get("falla", {}):
    sys.stderr.write(prog + ": falla simulada\n"); sys.exit(st["falla"][prog])

def lee_env(f):
    d = {}
    for ln in open(f).read().splitlines():
        if not ln.startswith("#") and "=" in ln:
            k, v = ln.split("=", 1); d[k] = v
    return d

def escribe_env(f, d):
    t = "# GRUB Environment Block\n" + "".join(k + "=" + v + "\n" for k, v in d.items())
    if len(t) > 1024: sys.exit("grubenv lleno")
    open(f, "w").write(t + "#" * (1024 - len(t)))

def boot(a):
    return next(x.split("=", 1)[1] for x in a if x.startswith("--boot-directory=")) + "/grub/grubenv"

if prog == "grub-editenv":
    f, cmd, rest = a[0], a[1], a[2:]
    d = lee_env(f)
    if cmd == "list": print("\n".join(k + "=" + v for k, v in d.items()))
    elif cmd == "set": d.update(x.split("=", 1) for x in rest); escribe_env(f, d)
    elif cmd == "unset":
        for k in rest: d.pop(k, None)
        escribe_env(f, d)
elif prog == "grub-set-default":
    f = boot(a); d = lee_env(f); d.pop("next_entry", None); d.pop("prev_saved_entry", None)
    d["saved_entry"] = a[-1]; escribe_env(f, d)
elif prog == "grub-reboot":
    f = boot(a); d = lee_env(f); d["next_entry"] = a[-1]; escribe_env(f, d)
elif prog == "journalctl":
    sys.stdout.write(st["journal"])
elif prog == "dpkg-query":
    pk = st["paquetes"]; pedidos = [x for x in a if not x.startswith("-")]
    for p in pedidos:
        if p in pk: print(p + "\t" + pk[p] + "\tinstall ok installed")
    if any(p not in pk for p in pedidos): sys.exit(1)
elif prog == "apt-mark":
    h = st["holds"]
    if a[0] == "showhold": print("\n".join(sorted(h)))
    elif a[0] == "hold": st["holds"] = sorted(set(h) | set(a[1:]))
    elif a[0] == "unhold": st["holds"] = sorted(set(h) - set(a[1:]))
elif prog == "modinfo":
    k = open(os.environ["BB_ROJO_RAIZ"] + "/proc/sys/kernel/osrelease").read().strip()
    print("/lib/modules/" + k + "/updates/dkms/nvidia.ko" if a[0] == "-n" else "SRCV-" + k)
elif prog == "grub-mkconfig":
    open(a[a.index("-o") + 1], "w").write(st["grub_cfg_nuevo"])
elif prog == "grub-script-check":
    sys.exit(1 if "SINTAXIS_ROTA" in open(a[0]).read() else 0)
json.dump(st, open(st_path, "w"))
'''
SHIMS = ("grub-editenv", "grub-set-default", "grub-reboot", "journalctl", "dpkg-query", "apt-mark", "modinfo",
         "grub-mkconfig", "grub-script-check")


def grub_cfg(kernels: list[str], default: str = '${saved_entry}') -> str:
    """Como lo escribe 10_linux de Ubuntu: entrada simple (el kernel mas nuevo) y el submenu con cada kernel."""
    out = [f'set default="{default}"',
           f"menuentry 'DGX OS GNU/Linux' --class ubuntu $menuentry_id_option 'gnulinux-simple-{UUID}' {{",
           "\trecordfail", f"\tlinux\t/boot/vmlinuz-{kernels[0]} root=UUID={UUID} ro", "}",
           f"submenu 'Advanced options for DGX OS GNU/Linux' $menuentry_id_option '{SUB}' {{"]
    for k in kernels:
        for tipo, extra in (("advanced", ""), ("recovery", " (recovery mode)")):
            out += [f"\tmenuentry 'DGX OS GNU/Linux, with Linux {k}{extra}' --class ubuntu "
                    f"$menuentry_id_option 'gnulinux-{k}-{tipo}-{UUID}' {{",
                    "\t\tif [ \"${grub_platform}\" = xen ]; then insmod xzio; fi",
                    f"\t\tlinux\t/boot/vmlinuz-{k} root=UUID={UUID} ro", "\t}"]
    return "\n".join([*out, "}", ""])


def escribe(p: Path, texto: str, modo: int = 0o644) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto, encoding="utf-8")
    p.chmod(modo)
    return p


class Atom:
    def __init__(self, tmp: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.raiz = r = tmp / "raiz"
        usuario = getpass.getuser()
        pw = pwd.getpwnam(usuario)
        self.home = r / pw.pw_dir.lstrip("/")
        self.ud = self.home / ".config/systemd/user"
        for n in UNIDADES:
            escribe(self.ud / n, f"[Service]\nExecStart=/bin/true # {n}\n")
        escribe(r / f"run/user/{pw.pw_uid}/systemd/private", "")
        self.keep = escribe(tmp / "keep.txt", "bb-aviso-termico\nblackbox-*\n[suspende]\nai-nemotron*\n")
        escribe(r / "proc/uptime", "30000.00 1000.00\n")
        escribe(r / "proc/sys/kernel/random/boot_id", "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\n")
        escribe(r / "proc/sys/kernel/osrelease", BUENO + "\n")
        for k in (BUENO, MALO):
            escribe(r / f"boot/vmlinuz-{k}", f"kernel {k}\n")
            escribe(r / f"lib/modules/{k}/updates/dkms/nvidia.ko", f"ko {k}\n")
        escribe(r / "sys/module/nvidia/version", "580.95.05\n")
        escribe(r / "sys/module/nvidia/srcversion", "SRCV\n")
        self.cfg = escribe(r / "boot/grub/grub.cfg", grub_cfg([MALO, BUENO]), 0o600)
        self.env = escribe(r / "boot/grub/grubenv", "# GRUB Environment Block\n" + "#" * 999)
        escribe(r / "etc/default/grub", f'GRUB_DEFAULT="Advanced options for DGX OS GNU/Linux>DGX OS GNU/Linux, '
                                        f'with Linux {BUENO}"\nGRUB_TIMEOUT=10\nGRUB_CMDLINE_LINUX_DEFAULT="quiet"\n')
        escribe(r / "etc/default/grub.d/92-bb-panic-temprano.cfg",
                'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT panic=30"\n')
        escribe(r / "etc/default/grub.d/zzz-bb-grub-default-guardado.cfg", "GRUB_DEFAULT=saved\nGRUB_SAVEDEFAULT=false\n")
        escribe(r / "etc/grub.d/09_bb_etapa", "#!/bin/sh\necho marca\n", 0o755)
        escribe(self.home / ".local/share/blackbox/interruptores.json", '{"motor": true}\n')
        self.restore = r / "var/lib/blackbox/restore"
        shims = tmp / "shims"
        for n in SHIMS:
            escribe(shims / n, f"#!{sys.executable}\n{SHIM}", 0o755)
        for n, cuerpo in (("systemctl", SYSTEMCTL), ("docker", DOCKER)):
            escribe(shims / n, f"#!{sys.executable}\n{cuerpo}", 0o755)
        self.atom = tmp / "atom.json"
        self.docker_state = escribe(tmp / "docker.json", json.dumps({"containers": []}))
        self.state = escribe(tmp / "systemctl.json", json.dumps({"units": dict(UNIDADES), "scopes": []}))
        self.log = tmp / "log.jsonl"
        self.pon({"journal": LIMPIO, "falla": {}, "holds": [], "grub_cfg_nuevo": grub_cfg([MALO, BUENO]),
                  "paquetes": {f"linux-image-{BUENO}": "6.17.0-1032.32", f"linux-modules-nvidia-580-open-{BUENO}":
                               "6.17.0-1032.32+1", f"linux-image-{MALO}": "7.0.0-1024.24",
                               "nvidia-driver-580-open": "580.95.05-0ubuntu1"}})
        for k, v in {"BB_ROJO_RAIZ": str(r), "BB_ROJO_USUARIO": usuario, "SHIM_ATOM": str(self.atom),
                     "SHIM_LOG": str(self.log), "SHIM_STATE": str(self.state),
                     "SHIM_DOCKER_STATE": str(self.docker_state),
                     "SHIM_MANIFIESTOS": str(self.home / ".local/share/blackbox/suspensiones/*.json"),
                     "PATH": str(shims)}.items():
            monkeypatch.setenv(k, v)
        monkeypatch.delenv("BB_ROJO_COMO_ROOT", raising=False)
        monkeypatch.setattr(br, "KEEP", self.keep)
        self.minuto = 0
        monkeypatch.setattr(pr, "nombre_nuevo", self._nombre)

    def _nombre(self) -> str:
        self.minuto += 1
        return f"2026-11-03T10-{self.minuto:02d}"

    def pon(self, cambios: dict) -> None:
        st = json.loads(self.atom.read_text()) if self.atom.exists() else {}
        st.update(cambios)
        self.atom.write_text(json.dumps(st))

    def st(self) -> dict:
        return json.loads(self.atom.read_text())

    def grubenv(self) -> dict[str, str]:
        return dict(ln.split("=", 1) for ln in self.env.read_text().splitlines() if "=" in ln and ln[0] != "#")

    def llamadas(self, prog: str | None = None) -> list[list[str]]:
        if not self.log.exists():
            return []
        todas = [json.loads(ln)["argv"] for ln in self.log.read_text().splitlines()]
        return [a for a in todas if prog is None or a[0] == prog]

    def puntos(self) -> list[Path]:
        return sorted(d for d in self.restore.glob("2026-*") if d.is_dir()) if self.restore.exists() else []


@pytest.fixture
def atom(tmp_path, monkeypatch):
    return Atom(tmp_path, monkeypatch)


def crea() -> int:
    return pr.main(["crea"])


# --- el punto: que guarda ----------------------------------------------------------------------------------------


def test_crea_un_punto_completo_en_un_arranque_sano(atom, capsys):
    assert crea() == 0, capsys.readouterr().out
    (d,) = atom.puntos()
    p = json.loads((d / "punto.json").read_text())
    assert p["esquema"] == "bb-restore-point/1" and p["kernel"] == BUENO and p["invalido"] is None
    assert p["grub"]["entry_id"] == f"gnulinux-{BUENO}-advanced-{UUID}" and p["grub"]["submenu_id"] == SUB
    assert p["grub"]["ruta_id"] == RUTA_BUENO and p["grub"]["grub_default_efectivo"] == "saved"
    rutas = [a["ruta"] for a in p["archivos"]]
    assert rutas == ["/etc/default/grub", "/etc/default/grub.d/92-bb-panic-temprano.cfg",
                     "/etc/default/grub.d/zzz-bb-grub-default-guardado.cfg", "/etc/grub.d/09_bb_etapa"]
    for a in p["archivos"]:
        assert br.sha256(d / a["copia"]) == a["sha256"] == br.sha256(atom.raiz / a["ruta"].lstrip("/"))
    assert p["nvidia"]["ruta"] == f"/lib/modules/{BUENO}/updates/dkms/nvidia.ko"
    assert p["nvidia"]["sha256"] == br.sha256(atom.raiz / f"lib/modules/{BUENO}/updates/dkms/nvidia.ko")
    assert p["nvidia"]["srcversion"] == "SRCV" and p["nvidia"]["srcversion_archivo"] == f"SRCV-{BUENO}"
    assert p["paquetes"][f"linux-image-{BUENO}"] == "6.17.0-1032.32"
    assert p["paquetes"][f"linux-modules-nvidia-fs-{BUENO}"] is None  # no instalado: se dice, no se inventa
    assert {u["unidad"] for u in p["unidades_usuario"]} == set(UNIDADES)
    assert p["interruptores"]["sha256"] == br.sha256(d / "interruptores.json")
    # apt-mark hold de los paquetes INSTALADOS de este kernel, y solo de esos
    assert p["hold_por_bb"] == [f"linux-image-{BUENO}", f"linux-modules-nvidia-580-open-{BUENO}"]
    assert atom.st()["holds"] == p["hold_por_bb"]
    assert atom.grubenv()["bb_punto_entry"] == RUTA_BUENO


@pytest.mark.parametrize("cambio, motivo", [
    ({"uptime": "100.0 50.0\n"}, "uptime 100 s < 21600 s"),
    ({"journal": LIMPIO + "[   24.3] NVRM: _issueRpcAndWait: rpcRecvPoll timedout waiting for response\n"}, "GSP"),
    ({"journal": LIMPIO + "[   38.1] NVRM: Xid (PCI:000f:01:00): 154, GPU recovery action changed\n"}, "Xid 154"),
    ({"journal": LIMPIO + "[  900.2] BUG: kernel NULL pointer dereference, address: 0000000000000008\n"}, "Oops/BUG"),
    ({"journal": LIMPIO + "[  901.0] Call Trace:\n"}, "Oops/BUG/Call Trace"),
    ({"falla": {"journalctl": 1}}, "no se puede juzgar"),
    ({"journal": ""}, "vacio: no se puede juzgar"),
])
def test_un_arranque_que_no_demuestra_estar_sano_no_crea_punto(atom, capsys, cambio, motivo):
    if "uptime" in cambio:
        escribe(atom.raiz / "proc/uptime", cambio.pop("uptime"))
    atom.pon(cambio)
    assert crea() == 0
    out = capsys.readouterr().out
    assert "SIN PUNTO NUEVO" in out and motivo in out
    assert atom.puntos() == [] and atom.st()["holds"] == []


def test_control_el_mismo_arranque_con_journal_limpio_si_crea(atom):
    """Control de la prueba de arriba: lo unico que cambia es la linea mala; sin ella hay punto."""
    atom.pon({"journal": LIMPIO + "[   24.3] NVRM: algo normal\n"})
    assert crea() == 0 and len(atom.puntos()) == 1


def test_corte_abrupto_anterior_se_registra_y_no_niega(atom, capsys):
    escribe(atom.home / ".local/share/blackbox/reboots.jsonl",
            json.dumps({"boot_id": "1" * 32, "boot_id_siguiente": "aaaaaaaabbbbccccddddeeeeeeeeeeee",
                        "etiqueta": "CORTE_ABRUPTO"}) + "\n")
    assert crea() == 0
    (d,) = atom.puntos()
    assert json.loads((d / "punto.json").read_text())["salud"]["arranque_anterior"] == "CORTE_ABRUPTO"
    assert "CORTE_ABRUPTO" in capsys.readouterr().out


def test_un_punto_identico_no_se_repite_y_uno_distinto_si(atom, capsys):
    assert crea() == 0 and crea() == 0
    assert len(atom.puntos()) == 1 and "SIN CAMBIOS" in capsys.readouterr().out
    escribe(atom.raiz / "etc/default/grub.d/93-otro.cfg", "GRUB_TIMEOUT=7\n")
    assert crea() == 0 and len(atom.puntos()) == 2


def test_conserva_tres_y_suelta_el_hold_del_kernel_que_ningun_punto_usa(atom):
    escribe(atom.raiz / "proc/sys/kernel/osrelease", MALO + "\n")  # un punto con 7.0 (sano en esta ficcion)
    assert crea() == 0
    assert f"linux-image-{MALO}" in atom.st()["holds"]
    escribe(atom.raiz / "proc/sys/kernel/osrelease", BUENO + "\n")
    for i in range(3):
        escribe(atom.raiz / "etc/default/grub.d/93-otro.cfg", f"GRUB_TIMEOUT={i}\n")
        assert crea() == 0
    assert len(atom.puntos()) == 3
    assert all(json.loads((d / "punto.json").read_text())["kernel"] == BUENO for d in atom.puntos())
    assert f"linux-image-{MALO}" not in atom.st()["holds"]  # ya ningun punto lo usa
    assert f"linux-image-{BUENO}" in atom.st()["holds"]  # los vigentes si
    assert ["apt-mark", "unhold", f"linux-image-{MALO}"] in atom.llamadas("apt-mark")


def test_un_hold_que_puso_luis_no_lo_suelta_la_poda(atom):
    atom.pon({"holds": [f"linux-image-{MALO}"]})
    escribe(atom.raiz / "proc/sys/kernel/osrelease", MALO + "\n")
    assert crea() == 0
    escribe(atom.raiz / "proc/sys/kernel/osrelease", BUENO + "\n")
    for i in range(3):
        escribe(atom.raiz / "etc/default/grub.d/93-otro.cfg", f"GRUB_TIMEOUT={i}\n")
        assert crea() == 0
    assert f"linux-image-{MALO}" in atom.st()["holds"]


@pytest.mark.parametrize("rompe, motivo", [
    (lambda a: (a.raiz / f"boot/vmlinuz-{BUENO}").unlink(), f"no existe /boot/vmlinuz-{BUENO}"),
    (lambda a: (a.raiz / f"lib/modules/{BUENO}/updates/dkms/nvidia.ko").unlink(), "modulo nvidia"),
    (lambda a: (a.puntos()[0] / "archivos/etc/default/grub").write_text("x"), "copia de /etc/default/grub"),
    (lambda a: a.cfg.write_text(grub_cfg([MALO])), "ya no esta en /boot/grub/grub.cfg"),
])
def test_un_punto_que_ya_no_sirve_se_marca_invalido(atom, rompe, motivo):
    assert crea() == 0
    rompe(atom)
    crea()
    p = json.loads((atom.puntos()[0] / "punto.json").read_text())
    assert motivo in p["invalido"]["motivo"]
    publicada = atom.grubenv().get("bb_punto_entry")
    otro = [d for d in atom.puntos()[1:] if not json.loads((d / "punto.json").read_text())["invalido"]]
    assert (publicada is None) == (not otro), "bb_punto_entry nombra un punto valido o no existe"


def test_sin_kernel_en_boot_no_nace_un_punto_y_se_quita_bb_punto_entry(atom, capsys):
    assert crea() == 0
    (atom.raiz / f"boot/vmlinuz-{BUENO}").unlink()  # apt lo quito mientras corre
    assert crea() == 1
    assert "el punto nuevo no serviria para volver" in capsys.readouterr().out
    assert len(atom.puntos()) == 1 and "bb_punto_entry" not in atom.grubenv()


# --- arranque-ok: el contador del autoarmado ---------------------------------------------------------------------


def test_arranque_ok_baja_el_contador_y_anota_el_autoarmado(atom):
    escribe(atom.raiz / "proc/uptime", "181.0 10.0\n")
    atom.env.write_text("# GRUB Environment Block\nbb_intentos=2\nbb_autoarmado=1\n" + "#" * 974)
    assert pr.main(["arranque-ok"]) == 0
    env = atom.grubenv()
    assert env["bb_intentos"] == "0" and "bb_autoarmado" not in env
    (fila,) = [json.loads(ln) for ln in (atom.raiz / "var/lib/blackbox/arranque-ok.jsonl").read_text().splitlines()]
    assert fila["sano"] and fila["autoarmado"] and fila["bb_intentos_antes"] == "2" and fila["bb_intentos_a_0"]
    assert fila["kernel"] == BUENO and fila["boot_id"] == "aaaaaaaabbbbccccddddeeeeeeeeeeee"


@pytest.mark.parametrize("uptime, journal", [
    ("181.0 1.0\n", LIMPIO + "[   24.3] NVRM: _issueRpcAndWait: rpcRecvPoll timedout waiting for response\n"),
    ("181.0 1.0\n", LIMPIO + "[   38.1] NVRM: Xid (PCI:000f:01:00): 154, GPU recovery action changed\n"),
    ("120.0 1.0\n", LIMPIO),
])
def test_arranque_ok_no_baja_el_contador_de_un_arranque_malo(atom, uptime, journal):
    """El bucle del 2026-11-02 tuvo un arranque de 242 s con la firma del GSP: 180 s solos no prueban nada."""
    escribe(atom.raiz / "proc/uptime", uptime)
    atom.pon({"journal": journal})
    atom.env.write_text("# GRUB Environment Block\nbb_intentos=2\n" + "#" * 988)
    assert pr.main(["arranque-ok"]) == 1
    assert atom.grubenv()["bb_intentos"] == "2"
    fila = json.loads((atom.raiz / "var/lib/blackbox/arranque-ok.jsonl").read_text())
    assert fila["sano"] is False and fila["motivos"]


# --- sudo panic --------------------------------------------------------------------------------------------------


def _rompe_como_un_apt(atom: Atom) -> None:
    """Lo que dejaria una subida de kernel mala: otro GRUB_DEFAULT y otra linea de comandos."""
    escribe(atom.raiz / "etc/default/grub", 'GRUB_DEFAULT=0\nGRUB_TIMEOUT=0\nGRUB_CMDLINE_LINUX_DEFAULT=""\n')
    (atom.raiz / "etc/default/grub.d/92-bb-panic-temprano.cfg").unlink()


def test_panic_regresa_al_punto_en_orden_y_sin_reiniciar(atom, capsys):
    assert crea() == 0
    original = {r: (atom.raiz / r).read_bytes() for r in ("etc/default/grub", "etc/default/grub.d/92-bb-panic-temprano.cfg")}
    _rompe_como_un_apt(atom)
    atom.env.write_text("# GRUB Environment Block\nsaved_entry=0\nbb_intentos=3\n" + "#" * 974)
    atom.log.unlink()
    assert panic.main([]) == 0, capsys.readouterr().out
    out = capsys.readouterr().out
    for r, b in original.items():
        assert (atom.raiz / r).read_bytes() == b, f"{r} no volvio al punto"
    (resp,) = atom.restore.glob("panic-*")
    assert (resp / "etc/default/grub").read_text().startswith("GRUB_DEFAULT=0")  # lo de antes, respaldado
    assert (resp / "boot/grub/grub.cfg").is_file()
    env = atom.grubenv()
    assert env["saved_entry"] == RUTA_BUENO and env["bb_intentos"] == "0" and env["bb_punto_entry"] == RUTA_BUENO
    assert not (atom.ud / "ai-nemotron.service").exists()  # (d) la suspension
    orden = [" ".join(a) for a in atom.llamadas()]

    def i(pred):
        return next(n for n, c in enumerate(orden) if pred(c))

    i_kernel = i(lambda c: c.startswith("grub-set-default"))
    i_cont = i(lambda c: c.startswith("grub-editenv") and "bb_intentos=0" in c)
    i_susp = i(lambda c: c.startswith("systemctl") and " stop " in c)
    i_mk = i(lambda c: c.startswith("grub-mkconfig"))
    assert i_kernel < i_cont < i_susp < i_mk, orden
    assert f"--boot-directory={atom.raiz}/boot" in orden[i_kernel]  # nunca el /boot de verdad
    assert "COULD_NOT_RUN: 0" in out and "NO se reinicio" in out
    assert not [c for c in orden if c.split()[0] in ("reboot", "systemctl") and "reboot" in c.split()]


def test_panic_sin_cambios_en_la_configuracion_no_regenera_grub(atom):
    assert crea() == 0
    assert panic.main([]) == 0
    assert atom.llamadas("grub-mkconfig") == []
    assert atom.grubenv()["saved_entry"] == RUTA_BUENO


def test_panic_sin_punto_lo_dice_y_suspende_igual(atom, capsys):
    atom.env.write_text("# GRUB Environment Block\nbb_intentos=3\n" + "#" * 988)
    assert panic.main([]) == 1
    out = capsys.readouterr().out
    assert "COULD_NOT_RUN: sin punto de restauracion" in out
    assert atom.llamadas("grub-set-default") == [] and atom.llamadas("grub-reboot") == []
    assert atom.grubenv()["bb_intentos"] == "0"
    assert not (atom.ud / "ai-nemotron.service").exists()


def test_panic_con_grub_default_literal_usa_grub_reboot_y_lo_dice(atom, capsys):
    (atom.raiz / "etc/default/grub.d/zzz-bb-grub-default-guardado.cfg").unlink()
    assert crea() == 0
    assert panic.main([]) == 1
    out = capsys.readouterr().out
    assert "no saved" in out and "SOLO para el proximo" in out
    assert atom.grubenv()["next_entry"] == RUTA_BUENO and "saved_entry" not in atom.grubenv()


def test_panic_no_elige_un_punto_invalido(atom):
    escribe(atom.raiz / "proc/sys/kernel/osrelease", MALO + "\n")
    assert crea() == 0
    escribe(atom.raiz / "proc/sys/kernel/osrelease", BUENO + "\n")
    assert crea() == 0
    viejo, nuevo = atom.puntos()
    assert json.loads((nuevo / "punto.json").read_text())["kernel"] == BUENO
    (atom.raiz / f"boot/vmlinuz-{BUENO}").unlink()  # el punto mas nuevo deja de servir
    assert panic.main([]) == 0
    assert atom.grubenv()["saved_entry"] == f"{SUB}>gnulinux-{MALO}-advanced-{UUID}"
    assert json.loads((nuevo / "punto.json").read_text())["invalido"]


def test_panic_no_sustituye_un_grub_cfg_que_grub_script_check_rechaza(atom, capsys):
    assert crea() == 0
    _rompe_como_un_apt(atom)
    antes = atom.cfg.read_bytes()
    atom.pon({"grub_cfg_nuevo": grub_cfg([MALO, BUENO]) + "SINTAXIS_ROTA\n"})
    assert panic.main([]) == 1
    assert "grub-script-check rechaza" in capsys.readouterr().out
    assert atom.cfg.read_bytes() == antes
    assert atom.grubenv()["saved_entry"] == RUTA_BUENO  # lo rapido y persistente ya quedo hecho


def test_panic_no_toca_lo_anadido_despues_del_punto(atom, capsys):
    assert crea() == 0
    nuevo = escribe(atom.raiz / "etc/default/grub.d/95-nuevo.cfg", "GRUB_TIMEOUT=3\n")
    assert panic.main([]) == 0
    assert nuevo.read_text() == "GRUB_TIMEOUT=3\n"
    assert "95-nuevo.cfg no esta en el punto" in capsys.readouterr().out


def test_panic_sin_root_no_toca_nada(atom, monkeypatch, capsys):
    if os.geteuid() == 0:
        pytest.skip("corre como root")
    monkeypatch.delenv("BB_ROJO_RAIZ")
    assert panic.main([]) == 2 and pr.main(["crea"]) == 2
    assert "necesita root" in capsys.readouterr().out and atom.llamadas() == []


def test_panic_tarda_segundos(atom, capsys):
    assert crea() == 0
    _rompe_como_un_apt(atom)
    t0 = time.monotonic()
    assert panic.main([]) == 0
    dur = time.monotonic() - t0
    with capsys.disabled():
        print(f"\n[tiempo] sudo panic con punto, configuracion cambiada y regeneracion de grub.cfg: {dur:.2f} s")
    assert dur < 5


UNIDADES_SISTEMA = ("bb-punto-restauracion.service", "bb-punto-restauracion.timer", "bb-arranque-ok.service",
                    "bb-arranque-ok.timer")


def gemelas_distintas(raiz: Path) -> list[str]:
    """systemd/<u> y adopted/pendiente-de-despliegue/etc_systemd_system_<u> son el mismo archivo byte a byte."""
    pend = raiz / "adopted/pendiente-de-despliegue"
    return [u for u in UNIDADES_SISTEMA
            if not (pend / f"etc_systemd_system_{u}").is_file()
            or (raiz / "systemd" / u).read_bytes() != (pend / f"etc_systemd_system_{u}").read_bytes()]


def test_las_unidades_de_sistema_tienen_su_gemela_identica():
    raiz = Path(__file__).resolve().parents[1]
    assert gemelas_distintas(raiz) == []
    for u in UNIDADES_SISTEMA:
        if u.endswith(".service"):
            assert "ExecStart=/usr/bin/python3 -I /usr/local/lib/blackbox/tools/punto_restauracion.py" in \
                (raiz / "systemd" / u).read_text()


def test_control_negativo_una_gemela_que_diverge_se_detecta(tmp_path):
    for u in UNIDADES_SISTEMA:
        escribe(tmp_path / "systemd" / u, "x\n")
        escribe(tmp_path / "adopted/pendiente-de-despliegue" / f"etc_systemd_system_{u}", "x\n")
    assert gemelas_distintas(tmp_path) == []
    escribe(tmp_path / "systemd/bb-arranque-ok.timer", "y\n")
    assert gemelas_distintas(tmp_path) == ["bb-arranque-ok.timer"]


REPO = Path(__file__).resolve().parents[1]


def _instala_en(destino: Path, archivos: tuple[str, ...]) -> Path:
    tools = destino / "lib/blackbox/tools"
    tools.mkdir(parents=True)
    for a in archivos:
        (tools / Path(a).name).write_bytes((REPO / a).read_bytes())
    return tools


@pytest.mark.parametrize("script", ["panic.py", "punto_restauracion.py"])
def test_la_copia_instalada_importa_con_python_I_y_solo_con_lo_de_INSTALA(tmp_path, script):
    env = {"PATH": "/usr/bin:/bin"}
    py = "/usr/bin/python3" if Path("/usr/bin/python3").exists() else sys.executable  # el de bin/panic
    tools = _instala_en(tmp_path / "bien", panic.INSTALA)
    p = subprocess.run([py, "-I", str(tools / script)], cwd=tmp_path, env=env,
                       capture_output=True, text=True, check=False)
    if os.geteuid() != 0:
        assert (p.returncode, "necesita root" in p.stdout) == (2, True), p.stderr
    # control negativo: sin un modulo que reboot_verdict importa, la copia NO arranca
    falta = _instala_en(tmp_path / "mal", tuple(a for a in panic.INSTALA if a != "tools/interruptores.py"))
    q = subprocess.run([py, "-I", str(falta / script)], cwd=tmp_path, env=env,
                       capture_output=True, text=True, check=False)
    assert q.returncode == 1 and "ImportError: cannot import name 'interruptores'" in q.stderr, q.stderr


def test_la_doc_instala_exactamente_INSTALA():
    doc = (REPO / "docs/PANIC.md").read_text(encoding="utf-8")
    linea = "sudo install -o root -g root -m 0644 -t /usr/local/lib/blackbox/tools " + " ".join(panic.INSTALA)
    assert linea in doc


def test_bin_panic_ejecuta_la_copia_root_y_no_el_repo():
    texto = (Path(__file__).resolve().parents[1] / "bin/panic").read_text()
    assert "exec /usr/bin/python3 -I /usr/local/lib/blackbox/tools/panic.py" in texto
    assert (Path(__file__).resolve().parents[1] / "bin/panic").stat().st_mode & stat.S_IXUSR
