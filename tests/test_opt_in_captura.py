"""tools/opt_in_captura.sh: las capas opt-in de captura de arranque, probadas contra una RAIZ FALSA.

La herramienta toca la configuracion de ARRANQUE de la ATOM (que ya dejo de encender una vez tras cambiar el
kernel), asi que lo que se prueba aqui es la disciplina, no el efecto en el kernel:
- `plan` (y cualquier invocacion ambigua) no escribe nada: el arbol de la raiz queda identico;
- `aplica` + `retrocede` deja cada fichero byte a byte como estaba (sha256, modo y destino de symlink);
- `retrocede` se niega si alguien edito un fichero (o el respaldo) entre medias, y entonces no cambia nada;
- `aplica` se niega sin grub-script-check o con una linea de comandos invalida, y deshace lo que alcanzo a escribir;
- `grub-marca` se niega con /boot en LVM, RAID o un sistema de ficheros que no sea ext4;
- control de mutacion: quitar el respaldo hace fallar la ida y vuelta.

Cada comando de la maquina es un falso de este fichero, conectado por su costura BB_OPTIN_<CMD>. Con raiz falsa
la herramienta trata un comando sin costura como ausente, asi que ninguna prueba toca la maquina real.
Las direcciones son de documentacion (RFC 5737 y RFC 7042), no de ninguna maquina.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
HERRAMIENTA = REPO / "tools" / "opt_in_captura.sh"
CONFIGFS = REPO / "adopted" / "opt-in" / "bb-netconsole-configfs.sh"
CAPAS = ["netconsole-runtime", "netconsole-arranque", "pstore-tras-panico", "grub-marca", "panic-temprano"]
CAPAS_GRUB = CAPAS[1:]
KERNEL = "6.99.0-prueba"
OTRO_KERNEL = "6.17.0-1032-nvidia"
# MAC de documentacion (RFC 7042) armada por partes: la guarda de datos privados cuenta toda MAC literal del repo.
MAC_DOC = ":".join(["00", "00", "5e", "00", "53", "01"])
TOKEN_NC = f"netconsole.netconsole=+6665@192.0.2.10/enp-prueba0,6666@192.0.2.20/{MAC_DOC}"
CONF_VALIDA = (
    "# configuracion de prueba\nDEV=enp-prueba0\nLOCAL_IP=192.0.2.10\nREMOTE_IP=192.0.2.20\n"
    f'REMOTE_MAC="{MAC_DOC.upper()}"\nDRIVER=r8127\n'
)

FALSOS = {
    "grub-mkconfig": r"""
echo "grub-mkconfig $*" >>"$FAKE_LOG"
export LC_ALL=C
out=""
while [ $# -gt 0 ]; do case "$1" in -o) out=$2; shift 2 ;; *) shift ;; esac; done
R=$FAKE_ROOT
GRUB_CMDLINE_LINUX="" GRUB_CMDLINE_LINUX_DEFAULT=""
. "$R/etc/default/grub"
if [ -z "${FAKE_IGNORA_GRUBD:-}" ]; then
    for x in "$R"/etc/default/grub.d/*.cfg; do if [ -e "$x" ]; then . "$x"; fi; done
fi
export GRUB_CMDLINE_LINUX GRUB_CMDLINE_LINUX_DEFAULT GRUB_FS=ext2
for s in "$R"/etc/grub.d/*; do if [ -x "$s" ]; then "$s"; fi; done >"$out.new"
mv "$out.new" "$out"
""",
    # Gramatica minima: llaves equilibradas, y la marca SINTAXIS_ROTA siempre se rechaza.
    "grub-script-check": r"""
echo "grub-script-check $*" >>"$FAKE_LOG"
[ -z "${FAKE_GSC_FALLA:-}" ] || exit 1
if grep -q SINTAXIS_ROTA "$1"; then exit 1; fi
awk '{ a += gsub(/\{/, "{"); c += gsub(/\}/, "}") } END { exit a != c }' "$1"
""",
    "update-initramfs": r"""
echo "update-initramfs $*" >>"$FAKE_LOG"
[ "$1" = -u ] && [ "$2" = -k ] || exit 2
K=$3 R=$FAKE_ROOT
[ -z "${FAKE_UI_FALLA:-}" ] || exit 1
{
    echo "initrd $K"
    while read -r m _; do
        case "$m" in '' | '#'*) continue ;; esac
        f=$(find "$R/lib/modules/$K" -name "$m.ko*" | head -1)
        [ -z "$f" ] || echo "usr/lib/modules/$K/${f#"$R/lib/modules/$K/"}"
    done <"$R/etc/initramfs-tools/modules"
} >"$R/boot/initrd.img-$K.new"
mv "$R/boot/initrd.img-$K.new" "$R/boot/initrd.img-$K"
sha1sum "$R/boot/initrd.img-$K" | cut -d' ' -f1 >"$R/var/lib/initramfs-tools/$K"
[ -z "${FAKE_UI_EXTRA:-}" ] || echo copia >"$R/boot/initrd.img-$K.bak"
[ -z "${FAKE_UI_TOCA_OTRO:-}" ] || echo otro >>"$R/boot/vmlinuz-$K"
""",
    "lsinitramfs": 'echo "lsinitramfs $*" >>"$FAKE_LOG"\ncat "$1"\n',
    "findmnt": 'echo "findmnt $*" >>"$FAKE_LOG"\necho "${FAKE_FINDMNT:-ext4 /dev/nvme0n1p1}"\n',
    "lsblk": 'echo "lsblk $*" >>"$FAKE_LOG"\necho "${FAKE_LSBLK:-part}"\n',
    "systemctl": 'echo "systemctl $*" >>"$FAKE_LOG"\n',
    "modprobe": r"""
echo "modprobe $*" >>"$FAKE_LOG"
if [ "$1" = -r ]; then rm -f "$FAKE_ROOT/sys/module/$2/initstate"; fi
""",
    "grub-editenv": 'echo "grub-editenv $*" >>"$FAKE_LOG"\nsed -i "/^bb_prev_/d" "$1"\n',
}
COSTURAS = {
    "GRUB_MKCONFIG": "grub-mkconfig", "GRUB_SCRIPT_CHECK": "grub-script-check", "UPDATE_INITRAMFS": "update-initramfs",
    "LSINITRAMFS": "lsinitramfs", "FINDMNT": "findmnt", "LSBLK": "lsblk", "SYSTEMCTL": "systemctl",
    "MODPROBE": "modprobe", "GRUB_EDITENV": "grub-editenv",
}

HEADER_00 = """#!/bin/sh
cat <<'EOF'
if [ -s $prefix/grubenv ]; then
  set have_grubenv=true
  load_env
fi
set default="0"
EOF
"""
LINUX_10 = """#!/bin/sh
for K in %s %s; do
  args="root=UUID=0000-prueba ro"
  [ -z "${FAKE_SIN_ROOT:-}" ] || args="ro"
  printf "menuentry 'DGX OS, con Linux %%s' {\\n\\trecordfail\\n" "$K"
  if [ -n "${FAKE_LINUX_VACIA:-}" ]; then printf "\\tlinux\\t/boot/vmlinuz-%%s\\n" "$K"
  else printf "\\tlinux\\t/boot/vmlinuz-%%s %%s %%s %%s\\n" "$K" "$args" "$GRUB_CMDLINE_LINUX" "$GRUB_CMDLINE_LINUX_DEFAULT"; fi
  printf "\\tinitrd\\t/boot/initrd.img-%%s\\n}\\n" "$K"
  printf "menuentry 'DGX OS, con Linux %%s (recovery mode)' {\\n" "$K"
  printf "\\tlinux\\t/boot/vmlinuz-%%s %%s recovery nomodeset %%s\\n}\\n" "$K" "$args" "$GRUB_CMDLINE_LINUX"
done
""" % (KERNEL, OTRO_KERNEL)


@dataclass
class Raiz:
    root: Path
    bin: Path
    log: Path

    def env(self, **extra: str) -> dict[str, str]:
        e = {"PATH": "/usr/bin:/bin", "LC_ALL": "C", "FAKE_ROOT": str(self.root), "FAKE_LOG": str(self.log)}
        e.update({f"BB_OPTIN_{k}": str(self.bin / v) for k, v in COSTURAS.items()})
        e.update(extra)
        return {k: v for k, v in e.items() if v != ""}

    def corre(self, *args: str, script: Path = HERRAMIENTA, **extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(script), "--root", str(self.root), *args],
            env=self.env(**extra), capture_output=True, text=True, timeout=120, check=False,
        )

    def llamadas(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []


def _escribe(p: Path, texto: str, modo: int = 0o644) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texto, encoding="utf-8")
    p.chmod(modo)


@pytest.fixture
def raiz(tmp_path: Path) -> Raiz:
    """Una ATOM de mentira: grub con kdump, dos kernels, initramfs-tools, configfs y la configuracion de netconsole."""
    root, binarios = tmp_path / "raiz", tmp_path / "bin"
    for nombre, cuerpo in FALSOS.items():
        _escribe(binarios / nombre, "#!/usr/bin/env bash\nset -eu\n" + cuerpo.lstrip("\n"), 0o755)
    _escribe(root / "etc/default/grub", 'GRUB_DEFAULT=0\nGRUB_TIMEOUT_STYLE=menu\nGRUB_TIMEOUT=5\n'
             'GRUB_CMDLINE_LINUX_DEFAULT="console=tty0 console=ttyS0,921600"\nGRUB_CMDLINE_LINUX=""\n')
    _escribe(root / "etc/default/grub.d/kdump-tools.cfg",
             'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT crashkernel=1G-:512M"\n')
    _escribe(root / "etc/grub.d/00_header", HEADER_00, 0o755)
    _escribe(root / "etc/grub.d/10_linux", LINUX_10, 0o755)
    _escribe(root / "boot/grub/grubenv", "# GRUB Environment Block\nrecordfail=1\n" + "#" * 990)
    for k in (KERNEL, OTRO_KERNEL):
        _escribe(root / f"boot/vmlinuz-{k}", f"kernel {k}\n")
        _escribe(root / f"boot/initrd.img-{k}", f"initrd original {k}\n")
        _escribe(root / f"var/lib/initramfs-tools/{k}", "sha1-original\n")
        _escribe(root / f"lib/modules/{k}/kernel/drivers/net/netconsole.ko.zst", "ko\n")
        _escribe(root / f"lib/modules/{k}/updates/dkms/r8127.ko.zst", "ko\n")
        _escribe(root / f"lib/modules/{k}/modules.builtin", "kernel/fs/ext4/ext4.ko\n")
    _escribe(root / "etc/initramfs-tools/modules", "# List of modules that you want to include in your initramfs.\n")
    _escribe(root / "etc/blackbox/netconsole.conf", CONF_VALIDA)
    for d in ("usr/local/sbin", "etc/systemd/system/multi-user.target.wants", "sys/kernel/config/netconsole",
              "sys/module/netconsole", "var/lib"):
        (root / d).mkdir(parents=True, exist_ok=True)
    r = Raiz(root, binarios, tmp_path / "llamadas.log")
    grub_cfg = root / "boot/grub/grub.cfg"
    grub_cfg.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(binarios / "grub-mkconfig"), "-o", str(grub_cfg)], env=r.env(), check=True)
    grub_cfg.chmod(0o444)
    r.log.unlink()
    return r


def foto(root: Path) -> dict[str, tuple]:
    """Cada entrada del arbol: tipo, modo y sha256 (fichero) o destino (symlink). Directorios incluidos."""
    out: dict[str, tuple] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for n in dirnames + filenames:
            p = Path(dirpath) / n
            st = p.lstat()
            rel = p.relative_to(root).as_posix()
            if stat.S_ISLNK(st.st_mode):
                out[rel] = ("enlace", os.readlink(p))
            elif stat.S_ISDIR(st.st_mode):
                out[rel] = ("dir", stat.S_IMODE(st.st_mode))
            else:
                out[rel] = ("fichero", stat.S_IMODE(st.st_mode), hashlib.sha256(p.read_bytes()).hexdigest())
    return out


def lineas_linux(raiz: Raiz) -> list[str]:
    cfg = (raiz.root / "boot/grub/grub.cfg").read_text(encoding="utf-8")
    return [ln for ln in cfg.splitlines() if ln.split()[:1] == ["linux"]]


def _ok(r: subprocess.CompletedProcess[str]) -> None:
    assert r.returncode == 0, f"rc={r.returncode}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"


def _negativa(r: subprocess.CompletedProcess[str], motivo: str) -> None:
    assert r.returncode == 3, f"rc={r.returncode}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    assert re.search(motivo, r.stdout + r.stderr), f"falta {motivo!r}\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"


# --- plan: el modo seco -----------------------------------------------------------------------------------------

@pytest.mark.parametrize("args, rc", [
    ((), 0), (("plan",), 0), (("estado",), 0), (("--kernel", KERNEL, "plan"), 0),
    *[(("--kernel", KERNEL, "plan", c), 0) for c in CAPAS],
    (("aplica",), 2), (("aplica", "todo"), 2), (("retrocede",), 2), (("aplica", "grub-marca", "extra"), 2),
    (("plan", "inexistente"), 2), (("activa", "grub-marca"), 2),
])
def test_plan_y_lo_ambiguo_no_escriben_nada(raiz: Raiz, args: tuple[str, ...], rc: int) -> None:
    antes = foto(raiz.root)
    r = raiz.corre(*args)
    assert r.returncode == rc, r.stdout + r.stderr
    assert foto(raiz.root) == antes
    assert not [c for c in raiz.llamadas() if c.split()[0] in ("grub-mkconfig", "update-initramfs", "systemctl")]
    if args[:1] != ("estado",):
        assert "modo seco: no se escribio nada" in r.stdout


def test_plan_describe_la_linea_de_comandos_que_quedaria(raiz: Raiz) -> None:
    r = raiz.corre("plan", "panic-temprano")
    _ok(r)
    # grub.d se lee en orden C: 92-bb-... va antes que kdump-tools.cfg, como en grub-mkconfig.
    assert "tras aplicar:                      console=tty0 console=ttyS0,921600 panic=30 crashkernel=1G-:512M" in r.stdout
    assert "se puede aplicar" in r.stdout


# --- ida y vuelta byte a byte -----------------------------------------------------------------------------------

def _ida_y_vuelta(raiz: Raiz, capa: str, script: Path = HERRAMIENTA, **extra: str) -> tuple[bool, str]:
    """True si aplica + retrocede salen 0 y el arbol queda identico. El texto explica el fallo."""
    antes = foto(raiz.root)
    a = raiz.corre("--kernel", KERNEL, "aplica", capa, script=script, **extra)
    if a.returncode != 0:
        return False, "aplica: " + a.stdout + a.stderr
    if foto(raiz.root) == antes:
        return False, "aplica no cambio nada"
    b = raiz.corre("retrocede", capa, script=script, **extra)
    if b.returncode != 0:
        return False, "retrocede: " + b.stdout + b.stderr
    despues = foto(raiz.root)
    if despues != antes:
        dif = sorted(set(antes.items()) ^ set(despues.items()))
        return False, f"el arbol cambio: {dif}"
    return True, ""


@pytest.mark.parametrize("capa", CAPAS)
def test_aplica_y_retrocede_dejan_la_raiz_byte_a_byte(raiz: Raiz, capa: str) -> None:
    ok, motivo = _ida_y_vuelta(raiz, capa)
    assert ok, motivo


def test_ida_y_vuelta_quita_tambien_lo_que_update_initramfs_creo(raiz: Raiz) -> None:
    ok, motivo = _ida_y_vuelta(raiz, "netconsole-arranque", FAKE_UI_EXTRA="1")
    assert ok, motivo


def test_aplica_deja_lo_que_cada_capa_promete(raiz: Raiz) -> None:
    _ok(raiz.corre("aplica", "panic-temprano"))
    normales = [ln for ln in lineas_linux(raiz) if " recovery " not in ln]
    rescate = [ln for ln in lineas_linux(raiz) if " recovery " in ln]
    assert normales and all(" panic=30" in ln and " root=UUID=0000-prueba" in ln for ln in normales)
    # va en _DEFAULT: las entradas de recovery quedan limpias y sirven de salida de emergencia
    assert rescate and not any("panic=30" in ln for ln in rescate)
    assert (raiz.root / "boot/grub/grub.cfg").stat().st_mode & 0o777 == 0o444
    assert (raiz.root / "var/lib/blackbox/opt-in/panic-temprano/aplicada").is_file()


def test_netconsole_arranque_mete_driver_y_modulo_en_el_initrd_y_la_linea(raiz: Raiz) -> None:
    _ok(raiz.corre("--kernel", KERNEL, "aplica", "netconsole-arranque"))
    modules = (raiz.root / "etc/initramfs-tools/modules").read_text(encoding="utf-8").splitlines()
    assert modules[-2:] == ["r8127", "netconsole"], "el driver tiene que cargarse antes que netconsole"
    initrd = (raiz.root / f"boot/initrd.img-{KERNEL}").read_text(encoding="utf-8")
    assert "r8127.ko.zst" in initrd and "netconsole.ko.zst" in initrd
    assert (raiz.root / f"boot/initrd.img-{OTRO_KERNEL}").read_text(encoding="utf-8") == f"initrd original {OTRO_KERNEL}\n"
    assert f"update-initramfs -u -k {KERNEL}" in raiz.llamadas()
    assert any(TOKEN_NC in ln for ln in lineas_linux(raiz))


def test_netconsole_runtime_instala_y_habilita_sin_arrancar(raiz: Raiz) -> None:
    _ok(raiz.corre("aplica", "netconsole-runtime"))
    enlace = raiz.root / "etc/systemd/system/multi-user.target.wants/bb-netconsole.service"
    assert os.readlink(enlace) == "/etc/systemd/system/bb-netconsole.service"
    sbin = raiz.root / "usr/local/sbin/bb-netconsole-configfs"
    assert sbin.read_bytes() == CONFIGFS.read_bytes() and sbin.stat().st_mode & 0o777 == 0o755
    assert not [c for c in raiz.llamadas() if c.startswith(("systemctl", "modprobe"))], "aplica no arranca nada"


def test_retrocede_runtime_quita_el_destino_y_descarga_el_modulo(raiz: Raiz) -> None:
    antes = foto(raiz.root)
    _ok(raiz.corre("aplica", "netconsole-runtime"))
    # Luis la arranco: hay destino en configfs (aqui vacio, como deja rmdir hacerlo en configfs) y modulo cargado.
    (raiz.root / "sys/kernel/config/netconsole/bb").mkdir()
    _escribe(raiz.root / "sys/module/netconsole/initstate", "live\n")
    _ok(raiz.corre("retrocede", "netconsole-runtime"))
    assert "systemctl stop bb-netconsole.service" in raiz.llamadas()
    assert "modprobe -r netconsole" in raiz.llamadas()
    assert foto(raiz.root) == antes


def test_las_dos_netconsole_se_excluyen(raiz: Raiz) -> None:
    _ok(raiz.corre("aplica", "netconsole-runtime"))
    antes = foto(raiz.root)
    _negativa(raiz.corre("--kernel", KERNEL, "aplica", "netconsole-arranque"), "FALTA: netconsole-runtime no esta aplicada")
    assert foto(raiz.root) == antes


# --- retrocede se niega si algo cambio fuera de la herramienta ---------------------------------------------------

@pytest.mark.parametrize("rel", [
    "etc/default/grub.d/92-bb-panic-temprano.cfg",
    "boot/grub/grub.cfg",
    "var/lib/blackbox/opt-in/panic-temprano/respaldo/boot/grub/grub.cfg",
])
def test_retrocede_se_niega_si_alguien_edito_entre_medias(raiz: Raiz, rel: str) -> None:
    _ok(raiz.corre("aplica", "panic-temprano"))
    p = raiz.root / rel
    p.chmod(0o644)
    p.write_text(p.read_text(encoding="utf-8") + "# editado a mano\n", encoding="utf-8")
    antes = foto(raiz.root)
    _negativa(raiz.corre("retrocede", "panic-temprano"), r"cambio fuera de la herramienta|respaldo de /.* no tiene")
    assert foto(raiz.root) == antes, "una negativa no cambia nada"
    assert "APLICADA" in raiz.corre("estado").stdout


def test_retrocede_se_niega_si_alguien_altero_el_initrd(raiz: Raiz) -> None:
    _ok(raiz.corre("--kernel", KERNEL, "aplica", "netconsole-arranque"))
    with (raiz.root / f"boot/initrd.img-{KERNEL}").open("a", encoding="utf-8") as f:
        f.write("regenerado por apt\n")
    antes = foto(raiz.root)
    _negativa(raiz.corre("retrocede", "netconsole-arranque"), f"/boot/initrd.img-{KERNEL} cambio fuera")
    assert foto(raiz.root) == antes


def test_capas_apiladas_se_retroceden_en_orden_inverso(raiz: Raiz) -> None:
    original = foto(raiz.root)
    _ok(raiz.corre("aplica", "pstore-tras-panico"))
    _ok(raiz.corre("aplica", "panic-temprano"))
    assert "aplicadas: pstore-tras-panico panic-temprano" in raiz.corre("estado").stdout
    apiladas = foto(raiz.root)
    # grub.cfg lo regenero panic-temprano despues: devolverlo al estado de pstore lo borraria
    _negativa(raiz.corre("retrocede", "pstore-tras-panico"), "retrocede antes panic-temprano")
    assert foto(raiz.root) == apiladas
    _ok(raiz.corre("retrocede", "panic-temprano"))
    _ok(raiz.corre("retrocede", "pstore-tras-panico"))
    assert foto(raiz.root) == original


def test_una_aplica_cortada_se_ve_y_se_retrocede(raiz: Raiz) -> None:
    original = foto(raiz.root)
    _ok(raiz.corre("aplica", "pstore-tras-panico"))
    (raiz.root / "var/lib/blackbox/opt-in/pstore-tras-panico/aplicada").unlink()  # como si la cortara un SIGKILL
    assert "pstore-tras-panico: INCOMPLETA" in raiz.corre("estado").stdout
    _ok(raiz.corre("retrocede", "pstore-tras-panico"))
    assert foto(raiz.root) == original


# --- aplica se niega antes de dejar un arranque invalido ---------------------------------------------------------

@pytest.mark.parametrize("capa", CAPAS_GRUB)
def test_aplica_se_niega_sin_grub_script_check(raiz: Raiz, capa: str) -> None:
    antes = foto(raiz.root)
    r = raiz.corre("--kernel", KERNEL, "aplica", capa, BB_OPTIN_GRUB_SCRIPT_CHECK="")
    _negativa(r, "FALTA: grub-script-check")
    assert foto(raiz.root) == antes
    assert not raiz.llamadas() or not [c for c in raiz.llamadas() if c.startswith(("grub-mkconfig", "update-initramfs"))]


@pytest.mark.parametrize("capa", CAPAS_GRUB)
@pytest.mark.parametrize("falla, motivo", [
    ({"FAKE_GSC_FALLA": "1"}, "grub-script-check lo rechaza"),
    ({"FAKE_SIN_ROOT": "1"}, "sin root="),
    ({"FAKE_LINUX_VACIA": "1"}, "sin argumentos"),
])
def test_aplica_se_niega_con_un_grub_cfg_invalido_y_deshace(raiz: Raiz, capa: str, falla: dict, motivo: str) -> None:
    antes = foto(raiz.root)
    r = raiz.corre("--kernel", KERNEL, "aplica", capa, **falla)
    _negativa(r, motivo)
    assert "grub.cfg no se toco" in r.stderr
    assert any(c.startswith("grub-mkconfig") for c in raiz.llamadas()), "la negativa tiene que venir de la validacion"
    assert foto(raiz.root) == antes, "lo que la aplica alcanzo a escribir se deshace"


@pytest.mark.parametrize("capa, palabra", [("panic-temprano", "panic=30"), ("pstore-tras-panico", "crash_kexec_post_notifiers")])
def test_aplica_se_niega_si_el_parametro_no_llega_a_las_entradas(raiz: Raiz, capa: str, palabra: str) -> None:
    antes = foto(raiz.root)
    _negativa(raiz.corre("aplica", capa, FAKE_IGNORA_GRUBD="1"), f"ninguna entrada lleva {palabra}")
    assert foto(raiz.root) == antes


def test_aplica_se_niega_si_el_parametro_ya_esta(raiz: Raiz) -> None:
    grub = raiz.root / "etc/default/grub"
    grub.write_text(grub.read_text(encoding="utf-8").replace("console=tty0", "console=tty0 panic=30"), encoding="utf-8")
    antes = foto(raiz.root)
    _negativa(raiz.corre("aplica", "panic-temprano"), "FALTA: panic=30 no esta ya en la linea de comandos")
    assert foto(raiz.root) == antes


# --- grub-marca --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("findmnt, lsblk", [
    ("ext4 /dev/mapper/vg0-boot", "lvm"),      # LVM por el nombre del dispositivo
    ("ext4 /dev/nvme0n1p2", "lvm"),            # LVM que solo delata lsblk
    ("ext4 /dev/md0", "raid1"),                # RAID por software
    ("btrfs /dev/nvme0n1p2", "part"),          # save_env no escribe en btrfs
])
def test_grub_marca_se_niega_con_boot_en_lvm_raid_u_otro_fs(raiz: Raiz, findmnt: str, lsblk: str) -> None:
    antes = foto(raiz.root)
    _negativa(raiz.corre("aplica", "grub-marca", FAKE_FINDMNT=findmnt, FAKE_LSBLK=lsblk), "FALTA: /boot en ext4 sin LVM ni RAID")
    assert foto(raiz.root) == antes
    assert not [c for c in raiz.llamadas() if c.startswith("grub-mkconfig")]


def test_grub_marca_se_niega_sin_poder_comprobar_boot(raiz: Raiz) -> None:
    antes = foto(raiz.root)
    _negativa(raiz.corre("aplica", "grub-marca", BB_OPTIN_FINDMNT=""), "sin findmnt no se puede comprobar /boot")
    assert foto(raiz.root) == antes


def test_grub_marca_guarda_despues_del_load_env_y_su_retroceso_limpia_el_grubenv(raiz: Raiz) -> None:
    antes = foto(raiz.root)
    _ok(raiz.corre("aplica", "grub-marca"))
    cfg = (raiz.root / "boot/grub/grub.cfg").read_text(encoding="utf-8")
    assert cfg.index("load_env") < cfg.index("save_env bb_prev_recordfail bb_prev_default bb_prev_boot_once")
    assert cfg.index("save_env bb_prev_recordfail") < cfg.index("recordfail\n\tlinux"), "antes de cualquier entrada"
    # GRUB arranco una vez con la marca: escribio las variables en el grubenv (eso no lo hace la herramienta)
    env = raiz.root / "boot/grub/grubenv"
    env.write_text(env.read_text(encoding="utf-8").replace("recordfail=1\n", "recordfail=1\nbb_prev_recordfail=1\n"),
                   encoding="utf-8")
    assert "grubenv: bb_prev_recordfail=1" in raiz.corre("estado").stdout
    _ok(raiz.corre("retrocede", "grub-marca"))
    assert foto(raiz.root) == antes


def test_la_plantilla_de_09_no_emite_nada_fuera_de_ext2(tmp_path: Path) -> None:
    plantilla = REPO / "adopted/opt-in/etc_grub.d_09_bb_etapa"
    con = subprocess.run(["sh", str(plantilla)], env={"PATH": "/usr/bin:/bin", "GRUB_FS": "ext2"},
                         capture_output=True, text=True, check=True).stdout
    sin = subprocess.run(["sh", str(plantilla)], env={"PATH": "/usr/bin:/bin", "GRUB_FS": "btrfs"},
                         capture_output=True, text=True, check=True).stdout
    assert "save_env bb_prev_recordfail" in con
    assert "save_env" not in sin and "btrfs" in sin


# --- netconsole-arranque: initramfs ------------------------------------------------------------------------------

def test_netconsole_arranque_se_niega_sin_kernel_o_sin_update_initramfs(raiz: Raiz) -> None:
    antes = foto(raiz.root)
    _negativa(raiz.corre("aplica", "netconsole-arranque"), r"FALTA: --kernel <falta>")
    _negativa(raiz.corre("--kernel", KERNEL, "aplica", "netconsole-arranque", BB_OPTIN_UPDATE_INITRAMFS=""),
              "FALTA: update-initramfs")
    _negativa(raiz.corre("--kernel", "6.0.0-no-instalado", "aplica", "netconsole-arranque"), "FALTA: --kernel")
    assert foto(raiz.root) == antes


def test_netconsole_arranque_se_niega_con_hooks_post_update(raiz: Raiz) -> None:
    _escribe(raiz.root / "etc/initramfs/post-update.d/zz-copia-al-esp", "#!/bin/sh\n", 0o755)
    antes = foto(raiz.root)
    _negativa(raiz.corre("--kernel", KERNEL, "aplica", "netconsole-arranque"), "FALTA: /etc/initramfs/post-update.d vacio")
    assert foto(raiz.root) == antes


def test_si_update_initramfs_falla_se_devuelve_el_initrd(raiz: Raiz) -> None:
    antes = foto(raiz.root)
    _negativa(raiz.corre("--kernel", KERNEL, "aplica", "netconsole-arranque", FAKE_UI_FALLA="1"), "update-initramfs fallo")
    assert foto(raiz.root) == antes


def test_si_update_initramfs_toca_un_fichero_sin_respaldo_lo_dice(raiz: Raiz) -> None:
    r = raiz.corre("--kernel", KERNEL, "aplica", "netconsole-arranque", FAKE_UI_TOCA_OTRO="1")
    _negativa(r, f"cambio ficheros sin respaldo: /boot/vmlinuz-{KERNEL}")
    # lo que si tenia respaldo vuelve; el fichero ajeno se nombra, no se finge devuelto
    assert (raiz.root / f"boot/initrd.img-{KERNEL}").read_text(encoding="utf-8") == f"initrd original {KERNEL}\n"
    assert not (raiz.root / "var/lib/blackbox").exists()
    assert f"NO se pudo devolver: /boot/vmlinuz-{KERNEL}" in r.stdout
    assert "la raiz quedo como estaba" not in r.stdout


# --- estado ------------------------------------------------------------------------------------------------------

def test_estado_lista_lo_aplicado_y_lo_cambiado(raiz: Raiz) -> None:
    assert "aplicadas: ninguna" in raiz.corre("estado").stdout
    _ok(raiz.corre("aplica", "panic-temprano"))
    salida = raiz.corre("estado").stdout
    assert "panic-temprano: APLICADA" in salida and "aplicadas: panic-temprano" in salida
    assert "/boot/grub/grub.cfg: intacto" in salida
    snippet = raiz.root / "etc/default/grub.d/92-bb-panic-temprano.cfg"
    snippet.write_text("# otro\n", encoding="utf-8")
    assert "92-bb-panic-temprano.cfg: CAMBIADO fuera de la herramienta" in raiz.corre("estado").stdout


# --- control de mutacion: sin respaldo, la ida y vuelta tiene que fallar -----------------------------------------

LLAMADA_RESPALDO = '[ "$antes" = - ] || respalda "$rel" "$antes"\n    anota fichero "$antes" "$despues" "$rel"'


def _mutante(tmp_path: Path, viejo: str, nuevo: str) -> Path:
    """Copia de la herramienta con un cambio; adopted/ apunta al del repo para que encuentre sus plantillas."""
    texto = HERRAMIENTA.read_text(encoding="utf-8")
    assert texto.count(viejo) == 1, "la mutacion tiene que caer en un sitio real del codigo"
    base = tmp_path / "mutante"
    _escribe(base / "tools/opt_in_captura.sh", texto.replace(viejo, nuevo), 0o755)
    (base / "adopted").symlink_to(REPO / "adopted")
    return base / "tools/opt_in_captura.sh"


@pytest.mark.parametrize("capa", ["panic-temprano", "netconsole-arranque", "grub-marca"])
def test_mutacion_quitar_el_respaldo_rompe_la_ida_y_vuelta(raiz: Raiz, tmp_path: Path, capa: str) -> None:
    mutante = _mutante(tmp_path, LLAMADA_RESPALDO, 'anota fichero "$antes" "$despues" "$rel"')
    ok, motivo = _ida_y_vuelta(raiz, capa, script=mutante)
    assert not ok, "sin respaldo la ida y vuelta no puede salir limpia: el test no protege nada"
    assert "respaldo" in motivo, motivo


def test_mutacion_control_el_original_si_pasa(raiz: Raiz, tmp_path: Path) -> None:
    copia = _mutante(tmp_path, LLAMADA_RESPALDO, LLAMADA_RESPALDO)
    ok, motivo = _ida_y_vuelta(raiz, "panic-temprano", script=copia)
    assert ok, motivo


# --- nunca reinicia ----------------------------------------------------------------------------------------------

REINICIO = re.compile(r"\b(reboot|poweroff|halt|shutdown)\b|systemctl\s+(kexec|soft-reboot)|kexec\s+-e|sysrq-trigger")


def _reinicios(texto: str) -> list[str]:
    return [ln for ln in texto.splitlines() if not ln.lstrip().startswith("#") and REINICIO.search(ln)]


def test_ningun_script_reinicia_la_maquina() -> None:
    for p in (HERRAMIENTA, CONFIGFS, REPO / "adopted/opt-in/etc_grub.d_09_bb_etapa"):
        assert _reinicios(p.read_text(encoding="utf-8")) == [], p


def test_control_negativo_el_detector_de_reinicios_los_ve() -> None:
    assert len(_reinicios("systemctl reboot\nkexec -e\necho b > /proc/sysrq-trigger\n# reboot en comentario\n")) == 3


# --- bb-netconsole-configfs --------------------------------------------------------------------------------------

def _configfs(root: Path, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
    env = {"PATH": "/usr/bin:/bin", "BB_NC_ROOT": str(root), **extra}
    return subprocess.run(["bash", str(CONFIGFS), *args], env=env, capture_output=True, text=True, timeout=60, check=False)


@pytest.mark.parametrize("cambio, motivo", [
    (("LOCAL_IP=192.0.2.10", "LOCAL_IP=192.0.2.256"), "LOCAL_IP no es una IPv4"),
    (("LOCAL_IP=192.0.2.10", "LOCAL_IP=<ip-de-la-atom>"), "LOCAL_IP no es una IPv4"),
    ((f'REMOTE_MAC="{MAC_DOC.upper()}"', "REMOTE_MAC=" + MAC_DOC[:-3]), "REMOTE_MAC no es una MAC"),
    (("DEV=enp-prueba0", "DEV=enp prueba0; reboot"), "DEV no es un nombre de interfaz"),
    (("DRIVER=r8127", "DRIVER=r8127\nDRIVER=mlx5_core"), "DRIVER repetida"),
    (("DRIVER=r8127", "PUERTO=7777"), "clave desconocida: PUERTO"),
    (("REMOTE_IP=192.0.2.20\n", ""), "falta REMOTE_IP"),
    (("REMOTE_IP=192.0.2.20", "REMOTE_IP=192.0.2.10"), "son la misma"),
    (("DRIVER=r8127", "$(touch /tmp/no)"), "no es CLAVE=valor"),
    # la MAC cero se arma aqui: un literal en el repo lo cuenta la guarda de datos privados
    ((f'REMOTE_MAC="{MAC_DOC.upper()}"', "REMOTE_MAC=" + ":".join(["00"] * 6)), "REMOTE_MAC no puede ser cero"),
])
def test_configfs_valida_rechaza_cada_valor_malo(tmp_path: Path, cambio: tuple[str, str], motivo: str) -> None:
    conf = tmp_path / "netconsole.conf"
    conf.write_text(CONF_VALIDA.replace(*cambio), encoding="utf-8")
    r = _configfs(tmp_path, "valida", str(conf))
    assert r.returncode == 3 and motivo in r.stderr, r.stdout + r.stderr


def test_configfs_valida_normaliza_y_da_el_parametro_de_arranque(tmp_path: Path) -> None:
    conf = tmp_path / "netconsole.conf"
    conf.write_text(CONF_VALIDA, encoding="utf-8")
    r = _configfs(tmp_path, "valida", str(conf))
    assert r.returncode == 0, r.stderr
    assert f"REMOTE_MAC={MAC_DOC}" in r.stdout.splitlines()
    assert _configfs(tmp_path, "cmdline", str(conf)).stdout.strip() == TOKEN_NC


def test_el_ejemplo_sin_rellenar_se_rechaza(tmp_path: Path) -> None:
    r = _configfs(tmp_path, "valida", str(REPO / "adopted/opt-in/netconsole.conf.ejemplo"))
    assert r.returncode == 3, r.stdout


def test_configfs_arranca_escribe_el_destino_en_orden_y_deja_la_marca(raiz: Raiz) -> None:
    (raiz.root / "dev").mkdir()
    (raiz.root / "dev/kmsg").write_text("", encoding="utf-8")
    r = _configfs(raiz.root, "arranca", BB_NC_MODPROBE=str(raiz.bin / "modprobe"), FAKE_LOG=str(raiz.log),
                  FAKE_ROOT=str(raiz.root))
    assert r.returncode == 0, r.stderr
    destino = raiz.root / "sys/kernel/config/netconsole/bb"
    leidos = {p.name: p.read_text(encoding="utf-8").strip() for p in destino.iterdir()}
    assert leidos == {"extended": "1", "dev_name": "enp-prueba0", "local_ip": "192.0.2.10", "remote_ip": "192.0.2.20",
                      "remote_mac": MAC_DOC, "local_port": "6665", "remote_port": "6666", "enabled": "1"}
    assert raiz.llamadas() == ["modprobe netconsole"]
    assert "bb-netconsole-marca destino=bb dev=enp-prueba0" in (raiz.root / "dev/kmsg").read_text(encoding="utf-8")


def test_configfs_arranca_se_niega_sin_configfs(raiz: Raiz) -> None:
    (raiz.root / "sys/kernel/config/netconsole").rmdir()
    r = _configfs(raiz.root, "arranca", BB_NC_MODPROBE=str(raiz.bin / "modprobe"), FAKE_LOG=str(raiz.log),
                  FAKE_ROOT=str(raiz.root))
    assert r.returncode == 3 and "CONFIG_NETCONSOLE_DYNAMIC" in r.stderr, r.stderr


def test_configfs_para_no_descarga_un_netconsole_compilado_dentro(raiz: Raiz) -> None:
    # sin initstate (compilado dentro, o no cargado) no hay modprobe -r que valga
    r = _configfs(raiz.root, "para", BB_NC_MODPROBE=str(raiz.bin / "modprobe"), FAKE_LOG=str(raiz.log),
                  FAKE_ROOT=str(raiz.root))
    assert r.returncode == 0, r.stderr
    assert raiz.llamadas() == []


def test_retrocede_quita_el_temporal_de_una_escritura_cortada(raiz: Raiz) -> None:
    original = foto(raiz.root)
    _ok(raiz.corre("aplica", "panic-temprano"))
    # una senal entre el cat y el mv dejaria esto junto a grub.cfg
    _escribe(raiz.root / "boot/grub/grub.cfg.bb-opt-in.4242", "a medias\n")
    _ok(raiz.corre("retrocede", "panic-temprano"))
    assert foto(raiz.root) == original
