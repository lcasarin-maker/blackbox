"""Cada guarda de `bb-root-run` con su control negativo.

Corre sin root: el uid de confianza, el padre del directorio temporal, el entorno y el
destino del eco se inyectan con `Opciones`. Lo que solo pasa con root de verdad (sudo
delante, ficheros root:root) queda simulado con el uid propio; ver la docstring del
modulo y el LEEME de despliegue.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import subprocess
import time
from pathlib import Path

import pytest

from tools import bb_root_run as rr

UID = os.getuid()
OK = "#!/usr/bin/env bash\nset -euo pipefail\necho hola-desde-root\n"


class Banco:
    """Un manifiesto, un directorio de scripts, uno de salida y un padre temporal, en tmp_path."""

    def __init__(self, base: Path) -> None:
        self.etc = base / "etc"
        self.scripts = base / "scripts"
        self.out = base / "out"
        self.tmp = base / "tmp"
        for d in (self.etc, self.scripts, self.tmp):
            d.mkdir(mode=0o755)
        self.manifest = self.etc / "manifest.json"
        self.entradas: dict[str, dict[str, object]] = {}
        self.salida = io.BytesIO()
        self.environ: dict[str, str] = {"SUDO_UID": str(UID)}
        self.trusted_uid = UID
        self.marca = base / "marca"

    def aprobar(self, name: str, body: str, file: str | None = None, **extra: object) -> Path:
        file = file or f"{name}.sh"
        p = self.scripts / file
        p.write_text(body, encoding="utf-8")
        self.entradas[name] = {"file": file, "sha256": hashlib.sha256(body.encode()).hexdigest(),
                               "descripcion": "prueba", **extra}
        self.escribir_manifiesto(self.entradas)
        return p

    def escribir_manifiesto(self, datos: object) -> None:
        self.manifest.write_text(json.dumps(datos), encoding="utf-8")
        self.manifest.chmod(0o644)

    def run(self, name: str | None) -> int:
        opts = rr.Opciones(trusted_uid=self.trusted_uid, tmp_parent=str(self.tmp),
                           environ=self.environ, salida=self.salida)
        return rr.run(name, str(self.manifest), str(self.scripts), str(self.out), opts)

    def auditoria(self) -> list[dict[str, object]]:
        f = self.out / "auditoria.jsonl"
        return [json.loads(x) for x in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []

    def salidas(self) -> list[Path]:
        return sorted(p for p in self.out.glob("*.txt"))


@pytest.fixture
def b(tmp_path: Path) -> Banco:
    return Banco(tmp_path)


# --- camino feliz: es el positivo contra el que se leen todos los rechazos -------------

def test_script_aprobado_corre_deja_salida_0644_y_auditoria(b: Banco):
    b.aprobar("saluda", OK)
    assert b.run("saluda") == 0
    assert b.salida.getvalue() == b"hola-desde-root\n"
    [f] = b.salidas()
    assert f.name.startswith("saluda-") and f.read_bytes() == b"hola-desde-root\n"
    assert stat.S_IMODE(f.stat().st_mode) == 0o644
    assert stat.S_IMODE((b.out / "auditoria.jsonl").stat().st_mode) == 0o644
    inicio, fin = b.auditoria()
    assert inicio["evento"] == "inicio" and fin["evento"] == "fin"
    assert fin["rc"] == 0 and fin["name"] == "saluda" and fin["caller_uid"] == str(UID)
    assert fin["sha256"] == b.entradas["saluda"]["sha256"] and fin["salida"] == str(f)


def test_rc_del_script_se_propaga_y_la_senal_sale_como_128_mas_n(b: Banco):
    b.aprobar("siete", "#!/bin/bash\necho x\nexit 7\n")
    assert b.run("siete") == 7
    b.aprobar("senal", "#!/bin/bash\nkill -TERM $$\n")
    assert b.run("senal") == 128 + 15
    assert [r["rc"] for r in b.auditoria() if r["evento"] == "fin"] == [7, 143]


def test_out_dir_se_crea_0755_aunque_la_umask_sea_077(b: Banco):
    b.aprobar("saluda", OK)
    vieja = os.umask(0o077)
    try:
        assert b.run("saluda") == 0
    finally:
        os.umask(vieja)
    assert stat.S_IMODE(b.out.stat().st_mode) == 0o755
    assert stat.S_IMODE(b.salidas()[0].stat().st_mode) == 0o644


# --- nombre ------------------------------------------------------------------------

def test_nombre_desconocido_se_rechaza_con_rc_3_y_queda_auditado(b: Banco):
    b.aprobar("saluda", OK)
    assert b.run("otro") == rr.RECHAZO
    [r] = b.auditoria()
    assert r["evento"] == "rechazo" and r["rc"] == 3 and "desconocido" in str(r["motivo"])
    assert b.salidas() == [] and b.salida.getvalue() == b""


@pytest.mark.parametrize("malo", ["../x", "a/b", "/etc/passwd", "A", "-x", "x_y", "a b",
                                  "saluda\n", "", "a" * 42, "ñ", None])
def test_nombre_malformado_se_rechaza(b: Banco, malo: str | None):
    # `saluda\n` casaria con `re.match(...$)`; con fullmatch no. "../x" casaria si el
    # nombre se usara como ruta. Para los dos hay un script aprobado al que apuntar.
    b.aprobar("saluda", OK)
    b.entradas["../x"] = b.entradas["saluda\n"] = b.entradas["saluda"]
    b.escribir_manifiesto(b.entradas)
    assert b.run(malo) == rr.RECHAZO
    assert "exactamente un argumento" in str(b.auditoria()[0]["motivo"])
    assert b.salida.getvalue() == b""


def test_control_negativo_el_nombre_limite_de_41_caracteres_si_pasa(b: Banco):
    nombre = "a" * 41
    b.aprobar(nombre, OK, file="largo.sh")
    assert b.run(nombre) == 0


def _kw(b: Banco) -> dict[str, object]:
    return {"manifest_path": str(b.manifest), "scripts_dir": str(b.scripts), "out_dir": str(b.out),
            "opts": rr.Opciones(trusted_uid=b.trusted_uid, tmp_parent=str(b.tmp), environ=b.environ, salida=b.salida)}


def test_main_exige_exactamente_un_argumento(b: Banco):
    b.aprobar("saluda", OK)
    assert rr.main([], **_kw(b)) == 3
    assert rr.main(["saluda", "otro"], **_kw(b)) == 3
    assert [r["name"] for r in b.auditoria() if r.get("rc") == 3] == [None, None]
    assert not b.salidas()  # nada se ejecuto con 0 o 2 argumentos
    assert rr.main(["saluda"], **_kw(b)) == 0  # control: con exactamente uno si corre
    assert len(b.salidas()) == 1


def test_main_sin_argv_lee_sys_argv(b: Banco, monkeypatch: pytest.MonkeyPatch):
    b.aprobar("saluda", OK)
    monkeypatch.setattr(rr.sys, "argv", ["bb-root-run", "saluda"])
    assert rr.main(**_kw(b)) == 0 and len(b.salidas()) == 1
    monkeypatch.setattr(rr.sys, "argv", ["bb-root-run"])
    assert rr.main(**_kw(b)) == 3


# --- el script: symlink, no regular, tamano, hash ------------------------------------

def test_script_symlink_se_rechaza_aunque_su_hash_coincida(b: Banco):
    real = b.aprobar("saluda", OK, file="real.sh")
    (b.scripts / "enlace.sh").symlink_to(real)
    b.entradas["saluda"]["file"] = "enlace.sh"
    b.escribir_manifiesto(b.entradas)
    assert b.run("saluda") == rr.RECHAZO
    assert "symlink" in str(b.auditoria()[0]["motivo"])
    # control negativo: el mismo hash por el fichero real si corre
    b.entradas["saluda"]["file"] = "real.sh"
    b.escribir_manifiesto(b.entradas)
    assert b.run("saluda") == 0


def test_script_fifo_se_rechaza_sin_colgarse(b: Banco):
    b.aprobar("saluda", OK)
    (b.scripts / "saluda.sh").unlink()
    os.mkfifo(b.scripts / "saluda.sh")
    assert b.run("saluda") == rr.RECHAZO
    assert "no es un fichero regular" in str(b.auditoria()[0]["motivo"])


def test_script_ausente_y_script_gigante_se_rechazan(b: Banco):
    b.aprobar("saluda", OK)
    b.aprobar("gigante", "#!/bin/bash\n" + "#" * rr.MAX_BYTES)
    (b.scripts / "saluda.sh").unlink()
    assert b.run("saluda") == rr.RECHAZO
    assert b.run("gigante") == rr.RECHAZO
    motivos = [str(r["motivo"]) for r in b.auditoria()]
    assert "no se puede abrir" in motivos[0] and "mas de" in motivos[1]


def test_script_editado_despues_de_aprobar_NO_corre(b: Banco):
    p = b.aprobar("saluda", OK)
    p.write_text(OK + f"touch {b.marca}\n", encoding="utf-8")
    assert b.run("saluda") == rr.RECHAZO
    assert not b.marca.exists(), "un script modificado llego a ejecutarse"
    r = b.auditoria()[0]
    assert "no es el aprobado" in str(r["motivo"])
    assert r["sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()
    # control negativo: aprobado con ese mismo contenido, la marca si aparece
    b.aprobar("saluda", p.read_text(encoding="utf-8"))
    assert b.run("saluda") == 0 and b.marca.exists()


# --- manifiesto -----------------------------------------------------------------

@pytest.mark.parametrize("modo", [0o664, 0o646, 0o666])
def test_manifiesto_escribible_por_grupo_u_otros_se_rechaza(b: Banco, modo: int):
    b.aprobar("saluda", OK)
    b.manifest.chmod(modo)
    assert b.run("saluda") == rr.RECHAZO
    assert "escribible por grupo u otros" in str(b.auditoria()[0]["motivo"])
    b.manifest.chmod(0o644)  # control negativo: el mismo manifiesto en 0644 pasa
    assert b.run("saluda") == 0


def test_directorio_del_manifiesto_escribible_por_grupo_se_rechaza(b: Banco):
    b.aprobar("saluda", OK)
    b.etc.chmod(0o775)
    assert b.run("saluda") == rr.RECHAZO
    assert "directorio del manifiesto" in str(b.auditoria()[0]["motivo"])


def test_la_guarda_de_dueno_mira_el_fichero_no_solo_su_directorio(b: Banco):
    # Sin root no hay un directorio de root con un fichero propio dentro; se prueba la
    # funcion sobre el stat del manifiesto: otro uid -> Rechazo; el propio -> pasa.
    b.aprobar("saluda", OK)
    st = os.stat(b.manifest)
    with pytest.raises(rr.Rechazo, match="dueno es uid"):
        rr.confiable(st, UID + 1, "manifiesto")
    rr.confiable(st, UID, "manifiesto")
    with pytest.raises(rr.Rechazo, match="dueno es uid"):
        rr.leer_una_vez(str(b.manifest), "manifiesto", UID + 1)
    with pytest.raises(rr.Rechazo, match=f"directorio del manifiesto .*se exige uid {UID + 1}"):
        rr.leer_manifiesto(str(b.manifest), UID + 1)
    assert rr.leer_manifiesto(str(b.manifest), UID) == b.entradas


def test_manifiesto_symlink_ausente_o_sin_directorio_se_rechaza(b: Banco):
    b.aprobar("saluda", OK)
    real = b.etc / "real.json"
    b.manifest.rename(real)
    b.manifest.symlink_to(real)
    assert b.run("saluda") == rr.RECHAZO
    b.manifest.unlink()
    assert b.run("saluda") == rr.RECHAZO
    b.manifest = b.etc / "no" / "manifest.json"
    assert b.run("saluda") == rr.RECHAZO
    motivos = [str(r["motivo"]) for r in b.auditoria()]
    assert "symlink" in motivos[0] and "no se puede abrir" in motivos[1]
    assert "no se puede leer" in motivos[2]


@pytest.mark.parametrize("datos", [
    "no es json", [1, 2], {"saluda": "texto"},
    {"saluda": {"file": "../saluda.sh", "sha256": "0" * 64}},
    {"saluda": {"file": "sub/saluda.sh", "sha256": "0" * 64}},
    {"saluda": {"file": "saluda.sh", "sha256": "A" * 64}},
    {"saluda": {"file": "saluda.sh", "sha256": "0" * 63}},
    {"saluda": {"file": "saluda.sh", "sha256": "0" * 64, "timeout": "60"}},
    {"saluda": {"file": "saluda.sh", "sha256": "0" * 64, "timeout": True}},
    {"saluda": {"file": "saluda.sh", "sha256": "0" * 64, "timeout": 0}},
])
def test_manifiesto_malformado_se_rechaza(b: Banco, datos: object):
    b.aprobar("saluda", OK)
    if isinstance(datos, str):
        b.manifest.write_text(datos, encoding="utf-8")
    else:
        b.escribir_manifiesto(datos)
    assert b.run("saluda") == rr.RECHAZO
    assert b.salida.getvalue() == b""


def test_timeout_por_defecto_y_techo_de_600():
    sha = "0" * 64
    assert rr.entrada({"x": {"file": "x.sh", "sha256": sha}}, "x").timeout == 120
    assert rr.entrada({"x": {"file": "x.sh", "sha256": sha, "timeout": 30}}, "x").timeout == 30
    assert rr.entrada({"x": {"file": "x.sh", "sha256": sha, "timeout": 10**6}}, "x").timeout == 600


# --- shebang ----------------------------------------------------------------------

@pytest.mark.parametrize("shebang", ["#!/bin/sh", "#!/usr/bin/python3", "#!/usr/bin/env python3",
                                     "#!/usr/bin/env bash -x", "#! /bin/bash", "#!/bin/bash\r",
                                     "echo sin shebang"])
def test_shebang_fuera_de_la_lista_blanca_se_rechaza(b: Banco, shebang: str):
    b.aprobar("raro", f"{shebang}\ntouch {b.marca}\n")  # hash correcto: solo frena el shebang
    assert b.run("raro") == rr.RECHAZO
    assert "shebang" in str(b.auditoria()[0]["motivo"])
    assert not b.marca.exists()


@pytest.mark.parametrize("shebang", ["#!/usr/bin/env bash", "#!/bin/bash"])
def test_control_negativo_los_dos_shebangs_permitidos_corren(b: Banco, shebang: str):
    b.aprobar("bien", f"{shebang}\ntouch {b.marca}\n")
    assert b.run("bien") == 0 and b.marca.exists()


# --- timeout ----------------------------------------------------------------------

def _vivo(pid: int) -> bool:
    """Vivo = existe y no es zombi (un zombi ya murio; solo espera que init lo recoja)."""
    try:
        estado = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()[0]
    except FileNotFoundError:
        return False
    return estado != "Z"


def test_timeout_mata_el_grupo_entero_y_sale_124(b: Banco):
    # El nieto deja su pid y retiene el pipe de salida: si el runner solo matara al hijo,
    # el nieto seguiria vivo al volver run().
    b.aprobar("lento", f"#!/bin/bash\n(echo $BASHPID > {b.marca}; exec sleep 30) &\nsleep 30\n",
              timeout=1)
    t0 = time.monotonic()
    assert b.run("lento") == rr.RC_TIMEOUT
    assert time.monotonic() - t0 < 10
    assert b"TIMEOUT" in b.salida.getvalue()
    assert not _vivo(int(b.marca.read_text(encoding="utf-8"))), "un nieto sobrevivio al timeout"


def test_control_negativo_el_detector_de_vivos_ve_un_proceso_vivo():
    p = subprocess.Popen(["sleep", "30"])
    try:
        assert _vivo(p.pid)
    finally:
        p.kill()
        p.wait()
    assert not _vivo(p.pid)


class _ProcTerco:
    """Un Popen falso que nunca termina de entregar el pipe (nieto fuera del grupo)."""

    pid = 2**22 + 12345  # no existe: killpg da ProcessLookupError y se ignora
    returncode = None

    def __init__(self, *a: object, **k: object) -> None:
        self.esperado = False

    def communicate(self, timeout: float | None = None) -> tuple[bytes, None]:
        raise subprocess.TimeoutExpired("bash", timeout or 0)

    def poll(self) -> int | None:
        return None

    def wait(self) -> int:
        self.esperado = True
        return -9


def test_timeout_con_pipe_retenido_no_cuelga_y_reapea(monkeypatch: pytest.MonkeyPatch):
    procs: list[_ProcTerco] = []
    monkeypatch.setattr(rr.subprocess, "Popen", lambda *a, **k: procs.append(_ProcTerco()) or procs[-1])
    rc, out = rr._correr(["/bin/bash", "-c", "true"], 1, {})
    assert rc == rr.RC_TIMEOUT and b"TIMEOUT" in out and procs[0].esperado


# --- entorno -----------------------------------------------------------------------

def test_entorno_se_construye_desde_cero_sin_ld_python_ni_bash_env(b: Banco, tmp_path: Path):
    veneno = tmp_path / "bash_env.sh"
    veneno.write_text(f"touch {b.marca}\n", encoding="utf-8")
    b.environ = {"LD_PRELOAD": "/x/evil.so", "LD_LIBRARY_PATH": "/x", "PYTHONPATH": "/x",
                 "PYTHONSTARTUP": "/x", "BASH_ENV": str(veneno), "PATH": "/x/bin",
                 "BASH_FUNC_echo%%": "() { :; }", "SUDO_UID": str(UID), "HOME": "/x"}
    b.aprobar("env", "#!/bin/bash\nenv\n")
    assert b.run("env") == 0
    vars_ = dict(x.split("=", 1) for x in b.salida.getvalue().decode().splitlines() if "=" in x)
    assert not [k for k in vars_ if k.startswith(("LD_", "PYTHON", "BASH_ENV", "BASH_FUNC"))]
    assert vars_["PATH"] == rr.PATH_FIJO and vars_["HOME"] == "/root"
    assert vars_["SUDO_UID"] == str(UID)
    assert not b.marca.exists(), "BASH_ENV del llamante llego a bash"
    # control negativo: el mismo BASH_ENV pasado a bash a pelo si ejecuta el veneno
    subprocess.run(["/bin/bash", "-c", "true"], env={"BASH_ENV": str(veneno)}, check=True)
    assert b.marca.exists()


@pytest.mark.parametrize("uid", ["1000; rm -rf /", "-1", "", "١٢"])
def test_sudo_uid_no_numerico_no_pasa_ni_se_audita(b: Banco, uid: str):
    b.environ = {"SUDO_UID": uid}
    b.aprobar("env", "#!/bin/bash\nenv\n")
    assert b.run("env") == 0
    assert b"SUDO_UID" not in b.salida.getvalue()
    assert b.auditoria()[-1]["caller_uid"] is None


def test_scripts_dir_por_defecto_es_el_home_del_llamante(b: Banco):
    import pwd
    home = pwd.getpwuid(UID).pw_dir
    assert rr.scripts_dir_por_defecto({"SUDO_UID": str(UID)}) == f"{home}/{rr.SCRIPTS_REL}"
    assert rr.scripts_dir_por_defecto({}) == f"{home}/{rr.SCRIPTS_REL}"
    b.aprobar("saluda", OK)
    b.environ = {"SUDO_UID": "2147483000"}  # sin entrada en passwd
    opts = rr.Opciones(trusted_uid=UID, tmp_parent=str(b.tmp), environ=b.environ, salida=b.salida)
    assert rr.run("saluda", str(b.manifest), None, str(b.out), opts) == rr.RECHAZO
    assert "sin entrada en passwd" in str(b.auditoria()[-1]["motivo"])


def test_sin_environ_inyectado_usa_os_environ(b: Banco, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SUDO_UID", "4242")
    b.aprobar("saluda", OK)
    opts = rr.Opciones(trusted_uid=UID, tmp_parent=str(b.tmp), salida=b.salida)
    assert rr.run("saluda", str(b.manifest), str(b.scripts), str(b.out), opts) == 0
    assert b.auditoria()[-1]["caller_uid"] == "4242"


# --- TOCTOU: lo que corre son los bytes hasheados -----------------------------------

def test_cambiar_el_script_entre_hash_y_ejecucion_no_cambia_lo_que_corre(
        b: Banco, monkeypatch: pytest.MonkeyPatch):
    p = b.aprobar("saluda", OK)
    malo = f"#!/usr/bin/env bash\ntouch {b.marca}\necho MALO\n"
    original = rr.ejecutar

    def cambiazo(data: bytes, file: str, timeout: int, env: dict[str, str],
                 opts: rr.Opciones) -> tuple[int, bytes]:
        p.write_text(malo, encoding="utf-8")  # el usuario reescribe el repo tras el hash
        return original(data, file, timeout, env, opts)

    monkeypatch.setattr(rr, "ejecutar", cambiazo)
    assert b.run("saluda") == 0
    assert b.salida.getvalue() == b"hola-desde-root\n"
    assert not b.marca.exists() and p.read_text(encoding="utf-8") == malo
    # control negativo: un runner que ejecutara la ruta del repo correria el cambiazo
    r = subprocess.run(["/bin/bash", str(p)], capture_output=True, check=True)
    assert r.stdout == b"MALO\n" and b.marca.exists()


def test_se_ejecuta_desde_un_directorio_0700_propio_que_luego_se_borra(b: Banco):
    b.aprobar("donde", '#!/bin/bash\nstat -c %a "$(dirname "$0")"\npwd\n')
    assert b.run("donde") == 0
    assert b.salida.getvalue() == b"700\n/\n"
    assert list(b.tmp.iterdir()) == []


@pytest.mark.parametrize("modo", [0o775, 0o757])
def test_padre_temporal_escribible_por_otros_se_rechaza(b: Banco, modo: int):
    b.aprobar("saluda", OK)
    b.tmp.chmod(modo)
    assert b.run("saluda") == rr.RECHAZO
    assert "padre del directorio temporal" in str(b.auditoria()[-1]["motivo"])


# --- directorio de salida -------------------------------------------------------------

def test_out_dir_no_confiable_se_rechaza_sin_escribir_nada(b: Banco, capsys: pytest.CaptureFixture[str]):
    b.aprobar("saluda", OK)
    b.out.mkdir(mode=0o777)
    b.out.chmod(0o777)
    assert b.run("saluda") == rr.RECHAZO
    assert list(b.out.iterdir()) == []
    assert "sin auditoria posible" in capsys.readouterr().err


def test_out_dir_que_no_se_puede_crear_o_es_fichero_se_rechaza(b: Banco):
    b.aprobar("saluda", OK)
    b.out = b.etc / "no" / "existe"
    assert b.run("saluda") == rr.RECHAZO
    b.out = b.manifest
    assert b.run("saluda") == rr.RECHAZO


def test_el_nombre_basura_queda_escapado_en_la_auditoria(b: Banco):
    b.aprobar("saluda", OK)
    assert b.run("\x1b[2J\nfalso") == rr.RECHAZO
    linea = (b.out / "auditoria.jsonl").read_text(encoding="utf-8")
    assert linea.count("\n") == 1 and "\x1b" not in linea
