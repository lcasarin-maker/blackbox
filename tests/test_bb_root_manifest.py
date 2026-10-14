"""`tools/bb_root_manifest.py`, el sudoers y los cuatro scripts root, con sus controles negativos.

Lo que exige root de verdad (install -o root, visudo sobre /etc/sudoers.d, la regex de
sudo casando argv) se simula: el comando de instalacion se ejecuta con las rutas
reescritas a tmp_path y sin `-o root -g root`; la regex de sudo se emula con
`re.fullmatch` sobre los argumentos unidos por espacio, que es como sudo >= 1.9.10 la
aplica. Ninguna de las dos simulaciones prueba el comportamiento del sudo instalado.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from tools import bb_root_manifest as bm
from tools import bb_root_run as rr

ROOT = Path(__file__).resolve().parents[1]
UID = os.getuid()
SCRIPTS = sorted(bm.SRC_DIR.glob("*.sh"))


@pytest.fixture
def src(tmp_path: Path) -> Path:
    d = tmp_path / "root-scripts"
    shutil.copytree(bm.SRC_DIR, d)
    return d


# --- la propuesta ------------------------------------------------------------------

def test_la_propuesta_commiteada_es_la_de_los_scripts_actuales():
    assert bm.PROPUESTA.read_bytes() == bm.serializar(bm.proponer(bm.SRC_DIR)), (
        "adopted/pendiente-de-despliegue/bb-root-run.manifest.json esta vieja: "
        "python3 -m tools.bb_root_manifest --propose")


def test_control_negativo_editar_un_script_cambia_la_propuesta(src: Path):
    (src / "dmidecode-sistema.sh").write_text("#!/bin/bash\necho otro\n", encoding="utf-8")
    assert bm.serializar(bm.proponer(src)) != bm.PROPUESTA.read_bytes()


def test_la_propuesta_cubre_los_cinco_scripts_y_nada_mas():
    m = bm.proponer(bm.SRC_DIR)
    assert sorted(m) == ["arranque-forense", "audit-rules-leer", "crontabs-leer", "dmidecode-sistema", "pstore-preparar"]
    assert sorted(str(e["file"]) for e in m.values()) == [p.name for p in SCRIPTS]
    for e in m.values():
        assert e["sha256"] == hashlib.sha256((bm.SRC_DIR / str(e["file"])).read_bytes()).hexdigest()


def _src_con(src: Path, name: str, **entrada: object) -> None:
    datos = json.loads((src / "manifest.src.json").read_text(encoding="utf-8"))
    datos[name] = {"file": "dmidecode-sistema.sh", "descripcion": "x", **entrada}
    (src / "manifest.src.json").write_text(json.dumps(datos), encoding="utf-8")


@pytest.mark.parametrize("name,entrada,motivo", [
    ("Mal_Nombre", {}, "nombre invalido"),
    ("bien", {"file": "../dmidecode-sistema.sh"}, "nombre de fichero simple"),
    ("bien", {"timeout": "10"}, "timeout"),
    ("bien", {"file": "no-existe.sh"}, "no se puede abrir"),
])
def test_proponer_aplica_las_guardas_del_runner(src: Path, name: str, entrada: dict[str, object], motivo: str):
    _src_con(src, name, **entrada)
    with pytest.raises(ValueError, match=motivo):
        bm.proponer(src)


def test_proponer_rechaza_shebang_fuera_de_lista_y_symlink(src: Path):
    (src / "py.sh").write_text("#!/usr/bin/python3\nprint(1)\n", encoding="utf-8")
    _src_con(src, "py", file="py.sh")
    with pytest.raises(ValueError, match="shebang"):
        bm.proponer(src)
    (src / "py.sh").unlink()
    (src / "py.sh").symlink_to(src / "dmidecode-sistema.sh")
    with pytest.raises(ValueError, match="symlink"):
        bm.proponer(src)


def test_main_propose_escribe_la_propuesta_e_imprime_scripts_y_comando(
        tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    out = tmp_path / "prop.json"
    assert bm.main(["--propose", "--out", str(out)]) == 0
    texto = capsys.readouterr().out
    assert out.read_bytes() == bm.PROPUESTA.read_bytes()
    for p in SCRIPTS:
        assert p.read_text(encoding="utf-8") in texto, f"falta el texto completo de {p.name}"
    assert hashlib.sha256(out.read_bytes()).hexdigest() in texto
    assert texto.rstrip().splitlines()[-1].startswith("sudo sh -c ")


def test_main_propose_con_un_script_malo_sale_3(src: Path, tmp_path: Path):
    _src_con(src, "Malo")
    out = tmp_path / "prop.json"
    assert bm.main(["--propose", "--src-dir", str(src), "--out", str(out)]) == 3
    assert not out.exists()


# --- el comando de instalacion, simulado sin root ------------------------------------

def _simular(tmp_path: Path) -> tuple[Path, Path, Path, str, Path]:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    prop, runner, sudoers = pkg / "m.json", pkg / "runner.py", pkg / "sudoers"
    shutil.copy(bm.PROPUESTA, prop)
    shutil.copy(bm.RUNNER, runner)
    shutil.copy(bm.SUDOERS, sudoers)
    raiz = tmp_path / "raiz"
    for d in ("sbin", "sudoers.d"):
        (raiz / d).mkdir(parents=True)
    cmd = bm.comando_instalacion(prop, runner, sudoers)
    sudo, sh, c, interior = shlex.split(cmd)
    assert (sudo, sh, c) == ("sudo", "sh", "-c")
    for viejo, nuevo in (("/etc/bb-root-run", f"{raiz}/etc/bb-root-run"),
                         ("/usr/local/sbin", f"{raiz}/sbin"),
                         ("/etc/sudoers.d", f"{raiz}/sudoers.d"),
                         (" -o root -g root", "")):
        assert viejo in interior
        interior = interior.replace(viejo, nuevo)
    return prop, runner, sudoers, interior, raiz


def test_el_comando_de_instalacion_instala_los_tres_con_sus_modos(tmp_path: Path):
    prop, runner, sudoers, interior, raiz = _simular(tmp_path)
    r = subprocess.run(["sh", "-c", interior], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for origen, destino, modo in ((runner, raiz / "sbin/bb-root-run", 0o755),
                                  (prop, raiz / "etc/bb-root-run/manifest.json", 0o644),
                                  (sudoers, raiz / "sudoers.d/bb-root-run", 0o440)):
        assert destino.read_bytes() == origen.read_bytes()
        assert stat.S_IMODE(destino.stat().st_mode) == modo
    assert not list(raiz.rglob("*.nuevo"))


def test_control_negativo_un_fichero_cambiado_tras_la_revision_no_se_instala(tmp_path: Path):
    _, runner, _, interior, raiz = _simular(tmp_path)
    runner.write_text(runner.read_text(encoding="utf-8") + "\n# cambiazo\n", encoding="utf-8")
    r = subprocess.run(["sh", "-c", interior], capture_output=True, text=True)
    assert r.returncode != 0
    assert not (raiz / "sbin/bb-root-run").exists()
    assert not (raiz / "sudoers.d/bb-root-run").exists(), "sudoers activo con un runner no revisado"


# --- sudoers ---------------------------------------------------------------------

LINEA_SUDOERS = r"lcasarin ALL=(root) NOPASSWD: /usr/local/sbin/bb-root-run ^[a-z0-9][a-z0-9-]*$"


def test_sudoers_tiene_una_sola_regla_y_es_la_regex_de_un_argumento():
    reglas = [x for x in bm.SUDOERS.read_text(encoding="utf-8").splitlines()
              if x.strip() and not x.startswith("#")]
    assert reglas == [LINEA_SUDOERS]


def test_sudoers_pasa_visudo_y_el_control_negativo_falla(tmp_path: Path):
    assert subprocess.run(["visudo", "-c", "-f", str(bm.SUDOERS)], capture_output=True).returncode == 0
    roto = tmp_path / "roto"
    roto.write_text(LINEA_SUDOERS.replace("NOPASSWD:", "NOPASSWD") + ",\n", encoding="utf-8")
    assert subprocess.run(["visudo", "-c", "-f", str(roto)], capture_output=True).returncode != 0


@pytest.mark.parametrize("argv,pasa", [
    (["audit-rules-leer"], True), (["a"], True),
    (["../x"], False), (["a/b"], False), (["a", "b"], False), (["a b"], False),
    ([], False), (["-x"], False), (["A"], False),
])
def test_emulacion_de_la_regex_de_sudo_sobre_argv(argv: list[str], pasa: bool):
    regex = LINEA_SUDOERS.rsplit(" ", 1)[1]
    assert (re.fullmatch(regex[1:-1], " ".join(argv)) is not None) is pasa


def test_control_negativo_el_glob_de_sudoers_dejaria_pasar_espacios_y_rutas():
    # El '*' de sudoers casa espacios y '/', como fnmatch: por eso no se usa.
    from fnmatch import fnmatchcase
    assert fnmatchcase(" ".join(["a", "../../x", "b"]), "[a-z0-9]*")


# --- --check -----------------------------------------------------------------------

def _instalado(tmp_path: Path, src: Path) -> tuple[Path, Path]:
    inst = tmp_path / "manifest.json"
    inst.write_bytes(bm.serializar(bm.proponer(src)))
    runner = tmp_path / "bb-root-run"
    shutil.copy(bm.RUNNER, runner)
    return inst, runner


def _check(inst: Path, src: Path, runner: Path) -> int:
    return bm.main(["--check", "--installed", str(inst), "--src-dir", str(src),
                    "--installed-runner", str(runner)])


def test_check_limpio_sale_0_e_imprime_los_ceros(tmp_path: Path, src: Path, capsys: pytest.CaptureFixture[str]):
    inst, runner = _instalado(tmp_path, src)
    assert _check(inst, src, runner) == 0
    assert "aprobados iguales: 5, cambios: 0, could_not_run: 0" in capsys.readouterr().out


def test_check_control_negativo_un_script_editado_se_reporta(
        tmp_path: Path, src: Path, capsys: pytest.CaptureFixture[str]):
    inst, runner = _instalado(tmp_path, src)
    with (src / "crontabs-leer.sh").open("a", encoding="utf-8") as f:
        f.write("echo extra\n")
    assert _check(inst, src, runner) == 1
    out = capsys.readouterr().out
    assert "cambiado desde la aprobacion: crontabs-leer" in out and "aprobados iguales: 4" in out


def test_check_reporta_ausente_sin_aprobar_y_runner_cambiado(
        tmp_path: Path, src: Path, capsys: pytest.CaptureFixture[str]):
    inst, runner = _instalado(tmp_path, src)
    (src / "dmidecode-sistema.sh").unlink()
    _src_con(src, "nuevo-script", file="audit-rules-leer.sh")
    runner.write_text("otro runner\n", encoding="utf-8")
    assert _check(inst, src, runner) == 1
    out = capsys.readouterr().out
    assert "ilegible o ausente en el repo: dmidecode-sistema" in out
    assert "sin aprobar (en manifest.src.json, no instalado): nuevo-script" in out
    assert "runner cambiado" in out


@pytest.mark.parametrize("contenido", [None, "no json", "[1]"])
def test_check_sin_manifiesto_legible_es_could_not_run_no_limpio(
        tmp_path: Path, src: Path, capsys: pytest.CaptureFixture[str], contenido: str | None):
    inst, runner = _instalado(tmp_path, src)
    if contenido is None:
        inst.unlink()
    else:
        inst.write_text(contenido, encoding="utf-8")
    assert _check(inst, src, runner) == 2
    assert "COULD_NOT_RUN" in capsys.readouterr().out


def test_check_runner_instalado_ilegible_es_could_not_run(
        tmp_path: Path, src: Path, capsys: pytest.CaptureFixture[str]):
    inst, runner = _instalado(tmp_path, src)
    runner.unlink()
    assert _check(inst, src, runner) == 2
    assert "could_not_run: 1" in capsys.readouterr().out


# --- los scripts root: forma estatica -----------------------------------------------

PROHIBIDO = re.compile(
    r"\b(curl|wget|nc|ncat|socat|ssh|scp|rsync|eval|source|exec|apt|apt-get|systemctl|docker)\b"
    r"|/dev/(tcp|udp)/|\$[1-9@*#]|\$\{(?:[1-9]|[@*#])[}:-]")
ESCRIBE = re.compile(r"\b(mkdir|chown|chmod|touch|cp|mv|rm|tee|install|ln|dd|truncate|sed\s+-i)\b")
REDIR = re.compile(r">>?\s*(&\d|[^\s;|&)]+)")
# Escrituras declaradas, por script: solo a las rutas de su propia carpeta (variables fijadas arriba del script).
ESCRITURA_OK = {"pstore-preparar.sh": re.compile(r'"\$(destino|padre)"'),
                "arranque-forense.sh": re.compile(r'"\$(base|dest)[/"]')}
REDIR_OK = {"arranque-forense.sh": re.compile(r'^"\$(base|dest)/[A-Za-z0-9._-]+"$')}
FICHA = re.compile(r"^# Desbloquea: ([A-Z0-9-]+)\.$", re.M)


def hallazgos(nombre: str, texto: str) -> list[str]:
    fuera: list[str] = []
    lineas = texto.splitlines()
    if not lineas or lineas[0].encode() not in rr.SHEBANGS:
        fuera.append(f"{nombre}: shebang")
    if "set -euo pipefail" not in lineas:
        fuera.append(f"{nombre}: sin set -euo pipefail")
    if not FICHA.search(texto):
        fuera.append(f"{nombre}: la cabecera no dice que ficha desbloquea")
    for i, linea in enumerate(lineas[1:], 2):
        if linea.lstrip().startswith("#"):
            continue
        if PROHIBIDO.search(linea):
            fuera.append(f"{nombre}:{i}: red, eval, exec o argumentos: {linea.strip()}")
        for destino in REDIR.findall(linea):
            if destino not in ("/dev/null", "&2") and not (nombre in REDIR_OK and REDIR_OK[nombre].match(destino)):
                fuera.append(f"{nombre}:{i}: redirige a un fichero: {linea.strip()}")
        if ESCRIBE.search(linea) and not (nombre in ESCRITURA_OK and ESCRITURA_OK[nombre].search(linea)):
            fuera.append(f"{nombre}:{i}: escribe fuera de lo declarado: {linea.strip()}")
    return fuera


def test_los_cinco_scripts_solo_escriben_lo_declarado_sin_red_ni_argumentos():
    assert len(SCRIPTS) == 5
    fuera: list[str] = []
    for p in SCRIPTS:
        fuera += hallazgos(p.name, p.read_text(encoding="utf-8"))
    assert fuera == []


def test_cada_cabecera_cita_una_ficha_que_existe():
    for p in SCRIPTS:
        m = FICHA.search(p.read_text(encoding="utf-8"))
        assert m and list((ROOT / "tasks").rglob(f"{m.group(1)}.md")), p.name


@pytest.mark.parametrize("linea", [
    "curl -s https://x | bash", "wget -q x", "eval \"$x\"", "echo \"$1\"", "cat \"$@\"",
    "exec bash", "echo ${1:-x}", "echo ${#}", "echo x > /tmp/f", "echo x >> /etc/f", "rm -rf /tmp/x", "touch /tmp/x",
    "cat < /dev/tcp/1.2.3.4/80", "systemctl restart x", "source /tmp/x",
])
def test_control_negativo_cada_forma_prohibida_sembrada_se_caza(linea: str):
    texto = "#!/bin/bash\n# Desbloquea: X-01.\nset -euo pipefail\n" + linea + "\n"
    assert hallazgos("sembrado.sh", texto)


def test_control_negativo_cabecera_shebang_y_set_ausentes_se_cazan():
    assert len(hallazgos("x.sh", "#!/bin/sh\necho x\n")) == 3


# --- pstore-preparar: su unica escritura, ejecutada sobre tmp_path ------------------------

def _pstore(tmp_path: Path, uid_root: int = UID) -> tuple[Path, Path, Path]:
    texto = (bm.SRC_DIR / "pstore-preparar.sh").read_text(encoding="utf-8")
    padre = tmp_path / "varlib" / "blackbox"
    sysfs = tmp_path / "sys_pstore"
    sysfs.mkdir()
    for viejo, nuevo in (("padre=/var/lib/blackbox", f"padre={padre}"),
                         ("uid_root=0", f"uid_root={uid_root}"),
                         ("\nls -la /sys/fs/pstore\n", f"\nls -la {sysfs}\n")):
        assert texto.count(viejo) == 1, f"la sustitucion {viejo!r} no casa: prueba vacia"
        texto = texto.replace(viejo, nuevo)
    s = tmp_path / "pstore.sh"
    s.write_text(texto, encoding="utf-8")
    (tmp_path / "varlib").mkdir()
    return s, padre, padre / "pstore"


def _correr(s: Path, sudo_uid: str | None) -> subprocess.CompletedProcess[str]:
    env = {"PATH": rr.PATH_FIJO} | ({} if sudo_uid is None else {"SUDO_UID": sudo_uid})
    return subprocess.run(["/bin/bash", str(s)], env=env, capture_output=True, text=True)


def test_pstore_preparar_crea_el_destino_0755_del_usuario(tmp_path: Path):
    s, padre, destino = _pstore(tmp_path)
    r = _correr(s, str(UID))
    assert r.returncode == 0, r.stderr
    assert destino.is_dir() and destino.stat().st_uid == UID
    assert stat.S_IMODE(destino.stat().st_mode) == 0o755
    assert stat.S_IMODE(padre.stat().st_mode) == 0o755
    assert _correr(s, str(UID)).returncode == 0  # idempotente


@pytest.mark.parametrize("uid", [None, "0", "abc", "1000;id"])
def test_pstore_preparar_sin_sudo_uid_valido_no_crea_nada(tmp_path: Path, uid: str | None):
    s, padre, _ = _pstore(tmp_path)
    assert _correr(s, uid).returncode == 3
    assert not padre.exists()


def test_pstore_preparar_no_sigue_un_destino_symlink(tmp_path: Path):
    s, padre, destino = _pstore(tmp_path)
    padre.mkdir(mode=0o755)
    victima = tmp_path / "victima"
    victima.mkdir(mode=0o700)
    destino.symlink_to(victima)
    assert _correr(s, str(UID)).returncode == 3
    assert stat.S_IMODE(victima.stat().st_mode) == 0o700, "el chmod siguio el symlink"


def test_pstore_preparar_no_sigue_un_padre_symlink(tmp_path: Path):
    s, padre, _ = _pstore(tmp_path)
    otro = tmp_path / "otro"
    otro.mkdir()
    padre.symlink_to(otro)
    assert _correr(s, str(UID)).returncode == 3
    assert not (otro / "pstore").exists()


def test_pstore_preparar_rechaza_padre_escribible_por_grupo(tmp_path: Path):
    s, padre, destino = _pstore(tmp_path)
    padre.mkdir()
    padre.chmod(0o775)
    assert _correr(s, str(UID)).returncode == 3
    assert not destino.exists()


def test_pstore_preparar_rechaza_padre_que_no_es_de_root(tmp_path: Path):
    # Sin root el padre siempre es del usuario; se le dice al script que "root" es otro uid.
    s, _, destino = _pstore(tmp_path, uid_root=UID + 1)
    assert _correr(s, str(UID)).returncode == 3
    assert not destino.exists()


@pytest.mark.parametrize("linea", [
    'echo x > /etc/passwd', 'echo x >> "$base/../../etc/f"', 'install -m 0644 /etc/shadow /tmp/x', 'rm -f -- /etc/hosts',
    'cp /sys/fs/pstore/x /tmp/x', 'echo x > "$otra/f"',
])
def test_control_negativo_arranque_forense_no_escribe_fuera_de_su_carpeta(linea: str):
    texto = "#!/bin/bash\n# Desbloquea: X-01.\nset -euo pipefail\n" + linea + "\n"
    assert hallazgos("arranque-forense.sh", texto), linea


def test_arranque_forense_si_puede_escribir_en_su_carpeta():
    texto = "#!/bin/bash\n# Desbloquea: X-01.\nset -euo pipefail\nprintf x >> \"$dest/arranque.jsonl\"\nrm -f -- \"$base/a.nuevo\"\n"
    assert hallazgos("arranque-forense.sh", texto) == []


# --- arranque-forense: ejecutado sobre tmp_path (rutas y dueno de root sustituidos) -------

def _forense(tmp_path: Path, uid_root: int = UID) -> tuple[Path, Path, Path]:
    texto = (bm.SRC_DIR / "arranque-forense.sh").read_text(encoding="utf-8")
    base = tmp_path / "varlib" / "blackbox"
    pst = tmp_path / "sys_pstore"
    pst.mkdir()
    (tmp_path / "varlib").mkdir()
    for viejo, nuevo in (("base=/var/lib/blackbox", f"base={base}"), ("/sys/fs/pstore/*", f"{pst}/*"),
                         ('!= "0" ]]', f'!= "{uid_root}" ]]'), ("-o root -g root", f"-o {uid_root}"), ("root:root", f"{uid_root}:{os.getgid()}"),
                         ("/sys/firmware/acpi/tables/BERT", str(tmp_path / "BERT"))):
        assert viejo in texto, f"la sustitucion {viejo!r} no casa: prueba vacia"
        texto = texto.replace(viejo, nuevo)
    s = tmp_path / "forense.sh"
    s.write_text(texto, encoding="utf-8")
    return s, base, pst


def test_arranque_forense_copia_pstore_y_escribe_una_fila_por_ejecucion(tmp_path: Path):
    s, base, pst = _forense(tmp_path)
    (pst / "dmesg-efi-1").write_text("panic", encoding="utf-8")
    (tmp_path / "BERT").write_bytes(b"BERT")
    for _ in range(2):
        r = _correr(s, str(UID))
        assert r.returncode == 0, r.stderr
    filas = [json.loads(x) for x in (base / "pstore" / "arranque.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(filas) == 2 and all(f["pstore_archivos"] == 1 and f["bert"] == "copiada" for f in filas)
    boot = filas[0]["boot_id"]
    assert (base / "pstore" / f"{boot}-dmesg-efi-1").read_text(encoding="utf-8") == "panic"
    assert (base / "pstore" / f"{boot}-BERT.bin").read_bytes() == b"BERT"


def test_arranque_forense_declara_la_ausencia_con_cero_archivos(tmp_path: Path):
    s, base, _ = _forense(tmp_path)
    assert _correr(s, str(UID)).returncode == 0
    fila = json.loads((base / "pstore" / "arranque.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert fila["pstore_archivos"] == 0 and fila["bert"] == "ausente"


def test_arranque_forense_control_negativo_symlink_o_dueno_ajeno_aborta_sin_escribir(tmp_path: Path):
    s, base, _ = _forense(tmp_path)
    blanco = tmp_path / "blanco"
    blanco.mkdir()
    base.symlink_to(blanco)
    r = _correr(s, str(UID))
    assert r.returncode == 3 and "symlink" in r.stderr and not list(blanco.iterdir())
    base.unlink()
    base.mkdir(mode=0o777)
    base.chmod(0o777)
    r = _correr(s, str(UID))
    assert r.returncode == 3 and "escribible" in r.stderr and not (base / "pstore" / "arranque.jsonl").exists()


def test_arranque_forense_control_negativo_symlink_dentro_del_destino_no_se_sigue(tmp_path: Path):
    s, base, _ = _forense(tmp_path)
    assert _correr(s, str(UID)).returncode == 0  # control: crea el destino y escribe
    blanco = tmp_path / "blanco.txt"
    blanco.write_text("intacto", encoding="utf-8")
    (base / "pstore" / "arranque.jsonl").unlink()
    (base / "pstore" / "arranque.jsonl").symlink_to(blanco)
    r = _correr(s, str(UID))
    assert r.returncode == 3 and "symlink" in r.stderr and blanco.read_text(encoding="utf-8") == "intacto"


def test_arranque_forense_control_negativo_base_de_otro_dueno_aborta(tmp_path: Path):
    s, base, _ = _forense(tmp_path, uid_root=UID + 1)
    base.mkdir()
    r = _correr(s, str(UID))
    assert r.returncode == 3 and "no es de root" in r.stderr and not (base / "pstore").exists()
