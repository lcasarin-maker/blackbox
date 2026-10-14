"""bb-apt-guardia: la lista, el hook, el script sellado que lo instala y la evidencia que lee el verificador.

El script root se ejecuta sobre tmp_path: rutas de /etc/apt/apt.conf.d, /usr/local/sbin y /run reescritas, dueno
root sustituido por el uid del test, y la "configuracion real" de APT apuntada (por APT_CONFIG en un envoltorio de
apt-get/apt-config) al directorio falso donde el script instala. APT es el de verdad, sobre la copia de
/var/lib/dpkg/status que el script hace en su caja; dpkg es el stub del script. Lo que no se prueba aqui: que
root, el /etc/apt real y el sudo instalado se comporten igual; eso lo mide
`tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD/collect_guard.py --instalado`.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tools import bb_root_run as rr
from tools import verify_apt_critical_removals as ag  # lista, rutas y constantes de la guardia; el verificador

ROOT = Path(__file__).resolve().parents[1]
UID = os.getuid()
SCRIPT = ag.SCRIPT
HOOK = ag.HOOK_REPO
CONF = ag.CONF_REPO
COLECTOR = ROOT / "tasks" / "evidence" / "FEATURE-APT-CRITICAL-METAPACKAGE-GUARD" / "collect_guard.py"


def _heredoc(texto: str, delim: str) -> str:
    return texto.split(f"<<'{delim}'\n", 1)[1].split(f"\n{delim}\n", 1)[0] + "\n"


def _instalado(paquete: str) -> bool:
    if shutil.which("dpkg-query") is None:
        return False
    r = subprocess.run(["dpkg-query", "-W", "--showformat=${Status}", paquete], capture_output=True, text=True)
    return r.stdout.endswith("ok installed")


APT_REAL = pytest.mark.skipif(
    shutil.which("apt-get") is None or not (_instalado(ag.CRITICO) and _instalado(ag.INOCUO)),
    reason="sin apt-get, o sin nvidia-system-station/tree instalados: la validacion no puede discriminar")


# --- la lista y su sitio ------------------------------------------------------------------

def test_la_lista_es_unica_sin_vacios_y_la_usa_el_verificador():
    nombres = ag.criticos()
    assert len(nombres) == len(set(nombres)) >= 20
    assert all(re.fullmatch(r"[a-z0-9][a-z0-9.+-]+", n) for n in nombres)
    assert ag.CRITICAL_PACKAGES == nombres
    assert ag.CRITICO in nombres and ag.INOCUO not in nombres


def test_el_kernel_fijado_en_grub_esta_en_la_lista():
    grub = (ROOT / "adopted" / "system-config" / "etc_default_grub").read_text(encoding="utf-8")
    m = re.search(r'^GRUB_DEFAULT=".*with Linux (\S+)"$', grub, re.M)
    assert m, "GRUB_DEFAULT ya no fija un kernel: revisar la lista"
    k = m.group(1)
    nombres = set(ag.criticos())
    assert {f"linux-image-{k}", f"linux-modules-{k}", f"linux-modules-nvidia-580-open-{k}"} <= nombres
    # Control negativo: otro kernel no esta (el test no es una tautologia sobre cualquier cadena).
    assert "linux-image-6.17.0-1031-nvidia" not in nombres


def test_el_hook_lleva_la_lista_del_repo_byte_a_byte():
    assert _heredoc(HOOK.read_text(encoding="utf-8"), "LISTA") == ag.LISTA.read_text(encoding="utf-8")


def test_el_script_sellado_embebe_hook_conf_y_stub_con_sus_sha256():
    texto = SCRIPT.read_text(encoding="utf-8")
    assert _heredoc(texto, "HOOK") == HOOK.read_text(encoding="utf-8")
    assert _heredoc(texto, "CONF") == CONF.read_text(encoding="utf-8")
    assert f'STUB_DPKG = """{_heredoc(texto, "STUB")}"""' in COLECTOR.read_text(encoding="utf-8")
    assert ag.hashes_esperados() == {"conf": hashlib.sha256(CONF.read_bytes()).hexdigest(),
                                     "hook": hashlib.sha256(HOOK.read_bytes()).hexdigest()}
    assert f"critico={ag.CRITICO}\n" in texto and f"inocuo={ag.INOCUO}\n" in texto


def test_el_conf_registra_el_hook_con_protocolo_3():
    conf = CONF.read_text(encoding="utf-8")
    assert f'DPkg::Pre-Install-Pkgs {{ "{ag.HOOK_INSTALADO}"; }};' in conf
    assert f'DPkg::Tools::Options::{ag.HOOK_INSTALADO}::Version "3";' in conf


@pytest.mark.skipif(shutil.which("apt-config") is None, reason="sin apt-config")
def test_apt_lee_el_conf_y_registra_el_hook(tmp_path: Path):
    (tmp_path / "parts").mkdir()
    shutil.copy(CONF, tmp_path / "parts" / "00-bb-apt-guardia")
    (tmp_path / "apt.conf").write_text(f'Dir::Etc::parts "{tmp_path}/parts";\n', encoding="utf-8")
    r = subprocess.run(["apt-config", "dump", "DPkg"], capture_output=True, text=True,
                       env={"PATH": rr.PATH_FIJO, "APT_CONFIG": str(tmp_path / "apt.conf")})
    assert r.returncode == 0 and r.stderr == ""
    assert ag.LINEA_HOOK in r.stdout.splitlines()
    assert f'DPkg::Tools::Options::{ag.HOOK_INSTALADO}::Version "3";' in r.stdout.splitlines()


# --- el hook, alimentado con el protocolo version 3 ------------------------------------------

CABECERA = "VERSION 3\nAPT::Architecture=arm64\nDPkg::Pre-Install-Pkgs::=x\n"


def _rm(nombre: str) -> str:
    return f"{nombre} 1.0 arm64 same > - - none **REMOVE**\n"


def _hook(entrada: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["/bin/bash", str(HOOK)], input=entrada, capture_output=True, text=True,
                          env={"PATH": rr.PATH_FIJO}, timeout=10)


@pytest.mark.parametrize("entrada,rc,en_stderr", [
    (CABECERA + "\n" + _rm("nvidia-system-station"), 1, "nvidia-system-station"),
    (CABECERA + "\n" + _rm("tree") + _rm("gdm3") + _rm("jq"), 1, "criticos de la plataforma: gdm3\n"),
    (CABECERA + "\n" + _rm("tree"), 0, ""),
    (CABECERA + "\n" + _rm("nvidia-system-station-games") + _rm("gdm3x") + _rm("xgdm3"), 0, ""),
    (CABECERA + "\nnvidia-system-station 1 all none < 2 all none /var/cache/apt/archives/x.deb\n", 0, ""),
    (CABECERA + "\nnvidia-system-station 1 all none = 1 all none **CONFIGURE**\n", 0, ""),
    (CABECERA + "BB::Apt-Guardia::Permitir=1\n\n" + _rm("gdm3"), 0, "permitida por"),
    (CABECERA + "BB::Apt-Guardia::Permitir=0\n\n" + _rm("gdm3"), 1, "no se aplica nada"),
    (CABECERA + "\nBB::Apt-Guardia::Permitir=1\n" + _rm("gdm3"), 1, "gdm3"),
    ("VERSION 2\n\ngdm3 1.0 > - **REMOVE**\n", 1, "VERSION 3"),
    ("", 1, "VERSION 3"),
    (CABECERA + "\n", 0, ""),
])
def test_hook_bloquea_solo_remociones_de_la_lista(entrada: str, rc: int, en_stderr: str):
    r = _hook(entrada)
    assert r.returncode == rc, r.stderr
    assert (en_stderr in r.stderr) if en_stderr else r.stderr == ""
    assert r.stdout == ""


# --- el script sellado, ejecutado sobre tmp_path ---------------------------------------------

def _bloque(texto: str, delim: str, cuerpo: str) -> str:
    viejo = _heredoc(texto, delim)
    assert texto.count(f"<<'{delim}'\n{viejo}{delim}\n") == 1
    return texto.replace(f"<<'{delim}'\n{viejo}{delim}\n", f"<<'{delim}'\n{cuerpo}{delim}\n")


def _guardia(tmp_path: Path, *, hook: str | None = None, inocuo: str | None = None,
             rompe_aislamiento: bool = False) -> dict[str, Path]:
    d = {k: tmp_path / k for k in ("etc", "sbin", "run", "stub", "vacio")}
    for p in d.values():
        p.mkdir()
        p.chmod(0o755)
    texto = SCRIPT.read_text(encoding="utf-8")
    for viejo, nuevo in (("/etc/apt/apt.conf.d", str(d["etc"])), ("/usr/local/sbin", str(d["sbin"])),
                         ("/run/bb-apt-guardia.", f"{d['run']}/bb-apt-guardia."), ('!= "0" ]]', f'!= "{UID}" ]]'),
                         ('== "0 755"', f'== "{UID} 755"'), ("chown root:root", f"chown {UID}:{os.getgid()}")):
        assert viejo in texto, f"la sustitucion {viejo!r} no casa: prueba vacia"
        texto = texto.replace(viejo, nuevo)
    if hook is not None:
        texto = _bloque(texto, "HOOK", hook)
    if inocuo is not None:
        texto = texto.replace(f"\ninocuo={ag.INOCUO}\n", f"\ninocuo={inocuo}\n")
    for k, delim in (("conf", "CONF"), ("hook", "HOOK")):
        nuevo = hashlib.sha256(_heredoc(texto, delim).encode()).hexdigest()
        texto, n = re.subn(rf"^sha_{k}=[0-9a-f]{{64}}$", f"sha_{k}={nuevo}", texto, flags=re.M)
        assert n == 1
    s = tmp_path / "apt-guardia-instalar.sh"
    s.write_text(texto, encoding="utf-8")
    sistema = tmp_path / "sistema.conf"
    sistema.write_text(f'Dir::Etc::main "/dev/null";\nDir::Etc::parts "{d["etc"]}";\n', encoding="utf-8")
    for nombre in ("apt-get", "apt-config"):
        romper = 'case "$*" in *"shell P"*) unset APT_CONFIG; exec /usr/bin/apt-config "$@";; esac\n' if (
            rompe_aislamiento and nombre == "apt-config") else ""
        (d["stub"] / nombre).write_text(
            f'#!/bin/sh\n{romper}if [ -z "${{APT_CONFIG:-}}" ]; then APT_CONFIG={sistema}; export APT_CONFIG; fi\n'
            f'exec /usr/bin/{nombre} "$@"\n', encoding="utf-8")
        (d["stub"] / nombre).chmod(0o755)
    d["script"], d["sistema"] = s, sistema
    d["conf"], d["hook"] = d["etc"] / "00-bb-apt-guardia", d["sbin"] / "bb-apt-guardia"
    return d


def _correr(d: dict[str, Path]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["/bin/bash", str(d["script"])], env={"PATH": f"{d['stub']}:{rr.PATH_FIJO}", "LC_ALL": "C"},
                          capture_output=True, text=True, timeout=300)


def _restos(d: dict[str, Path]) -> list[Path]:
    return sorted([*d["etc"].glob(".bb-apt-guardia.*"), *d["sbin"].glob(".bb-apt-guardia.*"), *d["run"].iterdir()])


def _nada_creado(d: dict[str, Path]) -> bool:
    return not d["conf"].exists() and not d["hook"].exists() and _restos(d) == []


@APT_REAL
def test_instala_valida_con_apt_real_y_es_idempotente(tmp_path: Path):
    d = _guardia(tmp_path)
    r = _correr(d)
    assert r.returncode == 0, r.stdout + r.stderr
    assert stat.S_IMODE(d["conf"].stat().st_mode) == 0o644 and stat.S_IMODE(d["hook"].stat().st_mode) == 0o755
    texto = d["script"].read_text(encoding="utf-8")
    assert d["conf"].read_text(encoding="utf-8") == _heredoc(texto, "CONF")
    assert d["hook"].read_text(encoding="utf-8") == _heredoc(texto, "HOOK")
    assert f"remove {ag.CRITICO}, rc 100" in r.stdout and f"remove {ag.INOCUO}, rc 0" in r.stdout
    assert f"--remove {ag.INOCUO}:" in r.stdout, "el stub de dpkg no recibio la remocion inocua"
    assert "guardia activa y validada" in r.stdout and _restos(d) == []
    antes = {p: p.stat().st_mtime_ns for p in (d["conf"], d["hook"])}
    r2 = _correr(d)
    assert r2.returncode == 0 and "estado:" in r2.stdout and "nuevo" in r2.stdout, r2.stdout + r2.stderr
    assert "creado" not in r2.stdout and {p: p.stat().st_mtime_ns for p in antes} == antes and _restos(d) == []


@APT_REAL
@pytest.mark.parametrize("hook,motivo", [
    ("#!/bin/bash\ncat > /dev/null\nexit 0\n", "no fue abortada"),
    ("#!/bin/bash\ncat > /dev/null\necho 'bb-apt-guardia: esta transaccion quita todo' >&2\nexit 1\n", "remocion inocua"),
])
def test_control_negativo_un_hook_que_no_discrimina_se_desinstala(tmp_path: Path, hook: str, motivo: str):
    d = _guardia(tmp_path, hook=hook)
    r = _correr(d)
    assert r.returncode == 5 and "VALIDACION FALLIDA" in r.stderr and motivo in r.stderr, r.stdout + r.stderr
    assert "borrado" in r.stderr and _nada_creado(d)


@APT_REAL
def test_control_negativo_una_caja_que_no_aisla_no_transacciona_y_desinstala(tmp_path: Path):
    d = _guardia(tmp_path, rompe_aislamiento=True)
    r = _correr(d)
    assert r.returncode == 5 and "no aisla" in r.stderr, r.stdout + r.stderr
    assert "caja: remove" not in r.stdout and _nada_creado(d)


@APT_REAL
def test_control_negativo_ya_instalada_y_validacion_fallida_no_borra_lo_previo(tmp_path: Path):
    d = _guardia(tmp_path)
    assert _correr(d).returncode == 0
    d["sistema"].write_text(f'Dir::Etc::main "/dev/null";\nDir::Etc::parts "{tmp_path / "vacio"}";\n',
                            encoding="utf-8")
    r = _correr(d)
    assert r.returncode == 5 and "no registra el hook" in r.stderr, r.stdout + r.stderr
    assert "borrado" not in r.stderr and d["conf"].exists() and d["hook"].exists()


@pytest.mark.parametrize("caso", ["conf_ajeno", "hook_ajeno", "hook_modo", "suspendida", "conf_symlink",
                                  "conf_symlink_al_contenido_nuevo", "hook_symlink_al_contenido_nuevo", "dir_escribible"])
def test_control_negativo_estado_desconocido_no_escribe_nada(tmp_path: Path, caso: str):
    d = _guardia(tmp_path)
    blanco = tmp_path / "blanco"
    blanco.write_text("intacto\n", encoding="utf-8")
    if caso == "conf_ajeno":
        d["conf"].write_text("// otro\n", encoding="utf-8")
    elif caso == "hook_ajeno":
        d["hook"].write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        d["hook"].chmod(0o755)
    elif caso == "hook_modo":
        d["hook"].write_text(_heredoc(d["script"].read_text(encoding="utf-8"), "HOOK"), encoding="utf-8")
        d["hook"].chmod(0o775)
    elif caso == "suspendida":
        (d["etc"] / "00-bb-apt-guardia.disabled").write_text("x\n", encoding="utf-8")
    elif caso == "conf_symlink":
        d["conf"].symlink_to(blanco)
    elif caso.endswith("_symlink_al_contenido_nuevo"):
        # El symlink apunta a un fichero con el contenido correcto: solo la guarda de symlink lo rechaza.
        k = caso.split("_", 1)[0]
        blanco.write_text(_heredoc(d["script"].read_text(encoding="utf-8"), k.upper()), encoding="utf-8")
        blanco.chmod(0o755)
        d[k].symlink_to(blanco)
    else:
        d["etc"].chmod(0o775)
    previos = {p: p.read_bytes() for p in (*d["etc"].iterdir(), *d["sbin"].iterdir()) if not p.is_symlink()}
    blanco_antes = blanco.read_bytes()
    r = _correr(d)
    assert r.returncode == 3, r.stdout + r.stderr
    assert {p: p.read_bytes() for p in (*d["etc"].iterdir(), *d["sbin"].iterdir()) if not p.is_symlink()} == previos
    assert blanco.read_bytes() == blanco_antes and _restos(d) == []
    assert caso != "hook_ajeno" or not d["conf"].exists()
    assert caso != "conf_ajeno" or not d["hook"].exists()


@pytest.mark.skipif(shutil.which("apt-get") is None, reason="sin apt-get")
def test_control_negativo_sin_paquete_inocuo_instalado_no_escribe_nada(tmp_path: Path):
    d = _guardia(tmp_path, inocuo="bb-paquete-que-no-existe")
    r = _correr(d)
    assert r.returncode == 4 and "no esta instalado" in r.stderr, r.stdout + r.stderr
    assert _nada_creado(d)


# --- la evidencia y el verificador -----------------------------------------------------------

def _captura_instalada() -> dict[str, Any]:
    """Una captura con la forma de `--instalado` cuyos resultados son los que la guardia debe producir."""
    esperado = ag.hashes_esperados()

    def fila(nombre: str, rc: int, stdout: str = "", stderr: str = "", **extra: Any) -> dict[str, Any]:
        return {"nombre": nombre, "argv": extra.pop("argv", ["x"]), "exit_code": rc, "stdout": stdout,
                "stderr": stderr} | ({"dpkg_log": extra["log"]} if "log" in extra else {})
    return {"instalado": True, "conf": ag.CONF_INSTALADO, "hook": ag.HOOK_INSTALADO, "critico": ag.CRITICO,
            "inocuo": ag.INOCUO, "conf_sha256": esperado["conf"], "hook_sha256": esperado["hook"], "commands": [
                fila("config", 0, ag.LINEA_HOOK + "\n"), fila("autoremove_simulado", 0),
                fila("remove_critico", 100, stderr=ag.MENSAJE_BLOQUEO + " ...\n", log="",
                     argv=["apt-get", "<caja>", "-y", "remove", ag.CRITICO]),
                fila("remove_inocuo", 0, log=f"--status-fd 72 --remove {ag.INOCUO}:arm64\n",
                     argv=["apt-get", "<caja>", "-y", "remove", ag.INOCUO])]}


def _evidencia(tmp_path: Path, captura: dict[str, Any] | None) -> Path:
    ev = tmp_path / "ev"
    shutil.copytree(ROOT / "tasks" / "evidence" / "FEATURE-APT-CRITICAL-METAPACKAGE-GUARD", ev)
    (ev / ag.CAPTURA).unlink()
    if captura is not None:
        raw = json.dumps(captura).encode()
        (ev / ag.CAPTURA).write_bytes(raw)
        (ev / "apt-guard-captures.sha256").write_text(hashlib.sha256(raw).hexdigest(), encoding="ascii")
    return ev


def test_verificador_guardia_instalada_quita_su_bloqueo_y_deja_el_de_oem(tmp_path: Path):
    r = ag.verify(_evidencia(tmp_path, _captura_instalada()))
    assert r["status"] == "pass" and r["checks"]["installed_guard"] == "verified", r
    assert r["open_blockers"] == [ag.OEM_BLOCKER] and r["closure"] == "open"
    assert ag.main(["--evidence", str(tmp_path / "ev"), "--cierre"]) == 2


def _mutar(campo: str, valor: Any, fila: str | None = None):
    def f(c: dict[str, Any]) -> None:
        destino = next(x for x in c["commands"] if x["nombre"] == fila) if fila else c
        destino[campo] = valor
    return f


@pytest.mark.parametrize("mutacion,motivo", [
    (_mutar("instalado", False), "pre-deployment"),
    (_mutar("conf", str(ag.CONF_REPO)), "installed paths"),
    (_mutar("hook_sha256", "0" * 64), "sha256"),
    (_mutar("stdout", "", "config"), "does not register"),
    (_mutar("exit_code", 100, "autoremove_simulado"), "autoremove fails"),
    (_mutar("exit_code", 0, "remove_critico"), "not aborted"),
    (_mutar("dpkg_log", f"--remove {ag.CRITICO}:all\n", "remove_critico"), "not aborted"),
    (_mutar("stderr", "E: otra cosa\n", "remove_critico"), "not aborted"),
    (_mutar("critico", ag.INOCUO), "does not remove a listed critical"),
    (_mutar("inocuo", "gdm3"), "names a critical"),
    (_mutar("dpkg_log", "", "remove_inocuo"), "did not reach dpkg"),
    (_mutar("exit_code", 100, "remove_inocuo"), "did not reach dpkg"),
])
def test_control_negativo_verificador_cada_prueba_faltante_mantiene_el_bloqueo(tmp_path: Path, mutacion, motivo: str):
    captura = _captura_instalada()
    mutacion(captura)
    r = ag.verify(_evidencia(tmp_path, captura))
    assert r["status"] == "pass" and r["checks"]["installed_guard"] in ("rejected", "pre_deployment"), r
    assert len(r["open_blockers"]) == 2 and motivo in r["open_blockers"][1], r["open_blockers"]


@pytest.mark.parametrize("dano", ["hash", "sin_fila", "fila_doble", "exit_texto", "sin_dpkg_log", "json"])
def test_control_negativo_evidencia_de_guardia_ilegible_es_could_not_run(tmp_path: Path, dano: str):
    captura = _captura_instalada()
    if dano == "sin_fila":
        captura["commands"].pop()
    elif dano == "fila_doble":
        captura["commands"].append(captura["commands"][0])
    elif dano == "exit_texto":
        captura["commands"][0]["exit_code"] = "0"
    elif dano == "sin_dpkg_log":
        del captura["commands"][2]["dpkg_log"]
    ev = _evidencia(tmp_path, captura)
    if dano == "hash":
        (ev / "apt-guard-captures.sha256").write_text("0" * 64, encoding="ascii")
    elif dano == "json":
        (ev / ag.CAPTURA).write_bytes(b"{")
        (ev / "apt-guard-captures.sha256").write_text(hashlib.sha256(b"{").hexdigest(), encoding="ascii")
    r = ag.verify(ev)
    assert r["status"] == "unknown" and r["could_not_run"] == 1, r


def test_sin_captura_de_guardia_el_bloqueo_dice_que_correr(tmp_path: Path):
    r = ag.verify(_evidencia(tmp_path, None))
    assert r["checks"]["installed_guard"] == "absent" and "--instalado" in r["open_blockers"][1]


def test_la_evidencia_commiteada_es_previa_al_despliegue_y_discrimina():
    ev = ROOT / "tasks" / "evidence" / "FEATURE-APT-CRITICAL-METAPACKAGE-GUARD"
    r = ag.verify(ev)
    assert r["status"] == "pass" and r["checks"]["installed_guard"] == "pre_deployment", r
    cap = json.loads((ev / ag.CAPTURA).read_text(encoding="utf-8"))
    filas = {x["nombre"]: x for x in cap["commands"]}
    # Lo que SI prueba la captura previa: APT real con el hook del repo aborta la critica y deja pasar la inocua.
    assert filas["remove_critico"]["exit_code"] != 0 and ag.MENSAJE_BLOQUEO in filas["remove_critico"]["stderr"]
    assert "--remove" not in filas["remove_critico"]["dpkg_log"]
    assert filas["remove_inocuo"]["exit_code"] == 0 and f"--remove {ag.INOCUO}" in filas["remove_inocuo"]["dpkg_log"]
