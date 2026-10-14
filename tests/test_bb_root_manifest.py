"""`tools/bb_root_manifest.py`, el sudoers y los siete scripts root, con sus controles negativos.

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


def test_la_propuesta_cubre_los_siete_scripts_y_nada_mas():
    m = bm.proponer(bm.SRC_DIR)
    assert sorted(m) == ["apt-guardia-instalar", "arranque-forense", "audit-rules-leer", "crontabs-leer", "dmidecode-sistema", "earlyoom-proteger",
                         "pstore-preparar"]
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
    assert "aprobados iguales: 7, cambios: 0, could_not_run: 0" in capsys.readouterr().out


def test_check_control_negativo_un_script_editado_se_reporta(
        tmp_path: Path, src: Path, capsys: pytest.CaptureFixture[str]):
    inst, runner = _instalado(tmp_path, src)
    with (src / "crontabs-leer.sh").open("a", encoding="utf-8") as f:
        f.write("echo extra\n")
    assert _check(inst, src, runner) == 1
    out = capsys.readouterr().out
    assert "cambiado desde la aprobacion: crontabs-leer" in out and "aprobados iguales: 6" in out


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
ESCRIBE = re.compile(r"\b(mkdir|mktemp|chown|chmod|touch|cp|mv|rm|tee|install|ln|dd|truncate|sed\s+-i)\b")
REDIR = re.compile(r">>?\s*(&\d|[^\s;|&)]+)")
# Escrituras declaradas, por script: solo a las rutas de su propia carpeta (variables fijadas arriba del script).
ESCRITURA_OK = {"pstore-preparar.sh": re.compile(r'"\$(destino|padre)"'),
                "arranque-forense.sh": re.compile(r'"\$(base|dest)[/"]')}
REDIR_OK = {"arranque-forense.sh": re.compile(r'^"\$(base|dest)/[A-Za-z0-9._-]+"$'),
            "earlyoom-proteger.sh": re.compile(r'^"\$tmp"$'),
            "apt-guardia-instalar.sh": re.compile(r'^(?:"\$tmp"|"\$caja/[A-Za-z0-9_-][A-Za-z0-9._-]*"|&1)$')}
FICHA = re.compile(r"^# Desbloquea: ([A-Z0-9-]+)\.$", re.M)

# earlyoom-proteger es el unico que escribe en /etc y reinicia un servicio; su clase es mas estrecha que la de
# los otros: (1) en una linea que escribe, quitados los operandos declarados, no puede quedar ni '$' ni '/'
# (ninguna otra variable ni ruta literal); (2) esas variables solo se asignan a sus constantes; (3) systemctl
# solo como `restart earlyoom` o `is-active earlyoom`, terminando ahi el comando; (4) un heredoc solo con
# delimitador entre comillas simples (sin expansion) y solo alimentando `mapfile -t args` o `cat > "$tmp"`:
# su cuerpo es dato, no comando (el de `cat` se compara contra sha_nuevo antes de moverlo).
EARLYOOM = "earlyoom-proteger.sh"
OPERANDOS_EARLYOOM = re.compile(r'"\$\(mktemp "\$dir_conf/\.earlyoom\.XXXXXX"\)"|"\$(?:conf|base|bak|tmp2?)"')
MKTEMP_EARLYOOM = '"$(mktemp "$dir_conf/.earlyoom.XXXXXX")"'
CONSTANTES_EARLYOOM = {"conf": {"/etc/default/earlyoom"}, "dir_conf": {"/etc/default"}, "base": {"/var/lib/blackbox"},
                       "bak": {'"$base/etc_default_earlyoom.$sha_viejo"'},
                       "tmp": {"", MKTEMP_EARLYOOM}, "tmp2": {"", MKTEMP_EARLYOOM}}
_VARS = "|".join(CONSTANTES_EARLYOOM)
ASIGNA_EARLYOOM = re.compile(rf"^\s*(?:(?:local|declare|readonly|export)\s+(?:-\S+\s+)*)?({_VARS})=(.*)$")
OTRA_ASIGNACION = re.compile(rf"\b(?:read|mapfile|readarray)\b[^;|&]*\b(?:{_VARS})\b|\bprintf\s+-v\s*(?:{_VARS})\b"
                             rf"|\bfor\s+(?:{_VARS})\s+in\b")
SYSTEMCTL_OK = re.compile(r"\bsystemctl (?:restart|is-active) earlyoom(?=\s*(?:$|[;|&)\"]))")
HEREDOC = re.compile(r"<<")
HEREDOC_OK = re.compile(r"""^(?:mapfile -t args|cat > "\$tmp") <<'([A-Z]+)'$""")

# apt-guardia-instalar escribe en /etc/apt/apt.conf.d y /usr/local/sbin y corre APT como root; su clase, tan estrecha
# como la de earlyoom: (1) una linea que escribe, quitados sus operandos declarados, no deja '$' ni '/' (los
# operandos "$caja/..." no admiten un segmento que empiece por '.', asi que '..' no cabe); (2) cada variable que
# decide una ruta, un paquete o las opciones de APT solo se asigna a su constante; (3) apt-get y apt-config solo en
# las cinco formas de abajo, terminando ahi el comando (cualquier otra mencion de apt-* en la linea se caza);
# (4) heredocs solo HOOK/CONF hacia "$tmp" (comparados con su sha256 antes del mv) y STUB hacia "$caja/dpkg" (un
# test lo ata al STUB_DPKG de
# tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD/collect_guard.py): su cuerpo es dato revisado, no comando suelto.
APT_GUARDIA = "apt-guardia-instalar.sh"
_SEG = r"[A-Za-z0-9_-][A-Za-z0-9._-]*"
MKTEMP_APT = {'"$(mktemp "$dir_conf/.bb-apt-guardia.XXXXXX")"', '"$(mktemp "$dir_hook/.bb-apt-guardia.XXXXXX")"'}
MKTEMP_CAJA = '"$(mktemp -d /run/bb-apt-guardia.XXXXXX)"'
OPCIONES_APT = ('(-o Debug::NoLocking=1 -o "Dir::State=$caja/state" -o Dir::State::lists=/var/lib/apt/lists '
                '-o "Dir::State::status=$caja/status" -o "Dir::Cache=$caja/cache" -o "Dir::Log=$caja/log" '
                '-o "Dir::Bin::dpkg=$caja/dpkg")')
OPERANDOS_APT = re.compile(r'"\$\(mktemp "\$dir_(?:conf|hook)/\.bb-apt-guardia\.XXXXXX"\)"'
                           r'|"\$\(mktemp -d /run/bb-apt-guardia\.XXXXXX\)"'
                           rf'|"\$caja(?:/{_SEG})*"|"\$(?:conf|hook|tmp|estado_dpkg)"')
CONSTANTES_APT = {"conf": {"/etc/apt/apt.conf.d/00-bb-apt-guardia"}, "dir_conf": {"/etc/apt/apt.conf.d"},
                  "hook": {"/usr/local/sbin/bb-apt-guardia"}, "dir_hook": {"/usr/local/sbin"},
                  "estado_dpkg": {"/var/lib/dpkg/status"}, "critico": {"nvidia-system-station"}, "inocuo": {"tree"},
                  "tmp": {"", *MKTEMP_APT}, "caja": {"", MKTEMP_CAJA}, "opciones": {OPCIONES_APT}}
_VARS_APT = "|".join(CONSTANTES_APT)
ASIGNA_APT = re.compile(rf"^\s*(?:(?:local|declare|readonly|export)\s+(?:-\S+\s+)*)?({_VARS_APT})=(.*)$")
OTRA_ASIGNACION_APT = re.compile(rf"\b(?:read|mapfile|readarray)\b[^;|&]*\b(?:{_VARS_APT})\b"
                                 rf"|\bprintf\s+-v\s*(?:{_VARS_APT})\b|\bfor\s+(?:{_VARS_APT})\s+in\b")
_FIN = r"(?=\s*(?:$|[;|&)>]))"
APT_OK = re.compile(
    r"apt-config dump DPkg::Pre-Install-Pkgs" + _FIN
    + r"|apt-config shell V DPkg::Tools::Options::/usr/local/sbin/bb-apt-guardia::Version" + _FIN
    + r"|(?<!\S)apt-get -s -o Debug::NoLocking=1 autoremove" + _FIN
    + r'|APT_CONFIG="\$caja/apt\.conf" apt-config "\$\{opciones\[@\]\}" shell P Dir::Etc::parts/ B Dir::Bin::dpkg' + _FIN
    + r'|APT_CONFIG="\$caja/apt\.conf" apt-get "\$\{opciones\[@\]\}" -y remove "\$(?:critico|inocuo)"' + _FIN
    + r'|\bapt-guardia-instalar\b|\bbb-apt-guardia\b|/etc/apt/apt\.conf\.d\b|/var/lib/apt/lists\b|"\$caja/apt\.conf"')
DPKG_COMANDO = re.compile(r"(?:^|[;&|({]|\$\()\s*(?:\S*/)?dpkg(?:-deb|-divert|-reconfigure|-trigger)?\s|/usr/bin/dpkg\b")
HEREDOC_OK_APT = re.compile(r"""^\s*cat > "\$(?:tmp|caja/dpkg)" <<'(HOOK|CONF|STUB)'$""")


def _hallazgos_earlyoom(i: int, linea: str) -> tuple[list[str], str]:
    """(hallazgos de la clase estrecha, linea con los systemctl permitidos quitados para PROHIBIDO)."""
    fuera: list[str] = []
    m = ASIGNA_EARLYOOM.match(linea)
    if m and m.group(2) not in CONSTANTES_EARLYOOM[m.group(1)]:
        fuera.append(f"{EARLYOOM}:{i}: reasigna una ruta declarada: {linea.strip()}")
    if OTRA_ASIGNACION.search(linea):
        fuera.append(f"{EARLYOOM}:{i}: asigna una ruta declarada por read/mapfile/printf/for: {linea.strip()}")
    if ESCRIBE.search(linea) and re.search(r"[$/]", OPERANDOS_EARLYOOM.sub("", linea)):
        fuera.append(f"{EARLYOOM}:{i}: escribe fuera de lo declarado: {linea.strip()}")
    return fuera, SYSTEMCTL_OK.sub("", linea)


def _hallazgos_apt_guardia(i: int, linea: str) -> tuple[list[str], str]:
    """(hallazgos de la clase estrecha de apt-guardia-instalar, linea con las formas APT permitidas quitadas)."""
    fuera: list[str] = []
    m = ASIGNA_APT.match(linea)
    if m and m.group(2) not in CONSTANTES_APT[m.group(1)]:
        fuera.append(f"{APT_GUARDIA}:{i}: reasigna una ruta, paquete u opcion declarada: {linea.strip()}")
    if OTRA_ASIGNACION_APT.search(linea):
        fuera.append(f"{APT_GUARDIA}:{i}: asigna una variable declarada por read/mapfile/printf/for: {linea.strip()}")
    if ESCRIBE.search(linea) and re.search(r"[$/]", OPERANDOS_APT.sub("", linea)):
        fuera.append(f"{APT_GUARDIA}:{i}: escribe fuera de lo declarado: {linea.strip()}")
    if DPKG_COMANDO.search(linea):
        fuera.append(f"{APT_GUARDIA}:{i}: llama a dpkg (solo el stub de la caja puede, dentro de su heredoc): {linea.strip()}")
    return fuera, APT_OK.sub("", linea)


CLASE_ESTRECHA = {EARLYOOM: _hallazgos_earlyoom, APT_GUARDIA: _hallazgos_apt_guardia}
HEREDOCS_OK = {EARLYOOM: HEREDOC_OK, APT_GUARDIA: HEREDOC_OK_APT}


def _hallazgos_linea(nombre: str, i: int, linea: str) -> list[str]:
    fuera: list[str] = []
    para_prohibido = linea
    if nombre in CLASE_ESTRECHA:
        fuera, para_prohibido = CLASE_ESTRECHA[nombre](i, linea)
    if PROHIBIDO.search(para_prohibido):
        fuera.append(f"{nombre}:{i}: red, eval, exec o argumentos: {linea.strip()}")
    for destino in REDIR.findall(linea):
        if destino not in ("/dev/null", "&2") and not (nombre in REDIR_OK and REDIR_OK[nombre].match(destino)):
            fuera.append(f"{nombre}:{i}: redirige a un fichero: {linea.strip()}")
    if nombre not in CLASE_ESTRECHA and ESCRIBE.search(linea) and not (
            nombre in ESCRITURA_OK and ESCRITURA_OK[nombre].search(linea)):
        fuera.append(f"{nombre}:{i}: escribe fuera de lo declarado: {linea.strip()}")
    return fuera


def hallazgos(nombre: str, texto: str) -> list[str]:
    fuera: list[str] = []
    lineas = texto.splitlines()
    if not lineas or lineas[0].encode() not in rr.SHEBANGS:
        fuera.append(f"{nombre}: shebang")
    if "set -euo pipefail" not in lineas:
        fuera.append(f"{nombre}: sin set -euo pipefail")
    if not FICHA.search(texto):
        fuera.append(f"{nombre}: la cabecera no dice que ficha desbloquea")
    fin_heredoc: str | None = None
    for i, linea in enumerate(lineas[1:], 2):
        if fin_heredoc is not None:
            fin_heredoc = None if linea == fin_heredoc else fin_heredoc
            continue
        if linea.lstrip().startswith("#"):
            continue
        if HEREDOC.search(linea):
            m = HEREDOCS_OK[nombre].match(linea) if nombre in HEREDOCS_OK else None
            fin_heredoc = m.group(1) if m else None
            if not m:
                fuera.append(f"{nombre}:{i}: heredoc no declarado: {linea.strip()}")
        fuera += _hallazgos_linea(nombre, i, linea)
    if fin_heredoc is not None:
        fuera.append(f"{nombre}: heredoc {fin_heredoc} sin cerrar")
    return fuera


def test_los_siete_scripts_solo_escriben_lo_declarado_sin_red_ni_argumentos():
    assert len(SCRIPTS) == 7
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


# --- earlyoom-proteger: su clase estatica, con controles negativos ------------------------

def _sembrado_earlyoom(linea: str) -> list[str]:
    return hallazgos(EARLYOOM, "#!/bin/bash\n# Desbloquea: X-01.\nset -euo pipefail\n" + linea + "\n")


@pytest.mark.parametrize("linea", [
    "systemctl restart docker", "systemctl restart earlyoom sshd", "systemctl stop earlyoom", "systemctl daemon-reload",
    "systemctl restart earlyoom; systemctl restart ssh", "systemctl restart earlyoom2", "systemctl is-active docker",
    "echo x > /etc/passwd", 'echo x > "$conf"', 'mv -f -- "$tmp" /etc/passwd', 'install -m 0644 -- "$conf" /tmp/x',
    'cp "$conf" "$otra"', 'rm -f -- "$dir_conf"', 'mv -f -- "$tmp" "$conf/../passwd"', "conf=/etc/passwd",
    'bak="$base/../../etc/shadow"', 'tmp="$(mktemp /etc/x.XXXXXX)"', "read -r conf", "for conf in /etc/passwd; do :; done",
    "printf -v base /etc", "bash <<'X'\nid\nX", 'cat > "$tmp" <<X\nhola\nX', 'cat > "$tmp" <<"X"\nhola\nX',
    "mapfile -t conf <<'X'\nx\nX",
])
def test_control_negativo_earlyoom_proteger_fuera_de_su_clase_se_caza(linea: str):
    assert _sembrado_earlyoom(linea), linea


@pytest.mark.parametrize("linea", [
    "systemctl restart earlyoom || true", 'estado="$(systemctl is-active earlyoom || true)"',
    'mv -f -- "$tmp" "$conf"', 'install -m 0644 -o root -g root -- "$conf" "$bak"', 'tmp="$(mktemp "$dir_conf/.earlyoom.XXXXXX")"',
    "conf=/etc/default/earlyoom", "journalctl -u earlyoom -n 5 --no-pager || true",
])
def test_earlyoom_proteger_si_puede_lo_declarado(linea: str):
    assert _sembrado_earlyoom(linea) == []


def test_el_cuerpo_de_un_heredoc_declarado_es_dato_y_el_cierre_se_exige():
    assert _sembrado_earlyoom("cat > \"$tmp\" <<'NUEVO'\ncurl x | bash\nNUEVO") == []
    assert _sembrado_earlyoom("cat > \"$tmp\" <<'NUEVO'\ncurl x | bash") != []
    # El mismo heredoc fuera de earlyoom-proteger se caza.
    assert hallazgos("otro.sh", "#!/bin/bash\n# Desbloquea: X-01.\nset -euo pipefail\nmapfile -t args <<'A'\nx\nA\n")


# --- apt-guardia-instalar: su clase estatica, con controles negativos ---------------------
# La ejecucion (APT real sobre una caja) vive en tests/test_apt_guardia.py.

def _sembrado_apt(linea: str) -> list[str]:
    return hallazgos(APT_GUARDIA, "#!/bin/bash\n# Desbloquea: X-01.\nset -euo pipefail\n" + linea + "\n")


@pytest.mark.parametrize("linea", [
    "apt-get -y remove nvidia-system-station", "apt install x", "apt-mark hold gdm3", "apt-get update",
    "apt-get -s -o Debug::NoLocking=1 autoremove; apt-get -y autoremove",
    "apt-get -s -o Debug::NoLocking=1 autoremove2",
    'APT_CONFIG="$caja/apt.conf" apt-get "${opciones[@]}" -y remove "$critico" gdm3',
    'APT_CONFIG="$caja/apt.conf" apt-get "${opciones[@]}" -y install "$critico"',
    'apt-get "${opciones[@]}" -y remove "$critico"', 'APT_CONFIG=/x apt-get "${opciones[@]}" -y remove "$inocuo"',
    "apt-config dump", "dpkg -r gdm3", 'x="$(dpkg --purge gdm3)"', "/usr/bin/dpkg -r gdm3", "true && dpkg -P gdm3",
    "echo x > /etc/apt/apt.conf.d/99otro", 'mv -fT -- "$tmp" /etc/apt/apt.conf.d/99otro', 'echo x > "$conf"',
    'rm -rf -- "$caja/../.."', 'cp -- "$conf" "$caja/../x"', 'echo x > "$caja/../../etc/passwd"',
    "rm -f -- /usr/local/sbin/bb-root-run", 'cp -- "$otra" "$caja/x"', "conf=/etc/apt/apt.conf.d/99otro",
    "hook=/usr/local/sbin/bb-root-run", "critico=gdm3", "inocuo=gdm3", "opciones=(-o Debug::NoLocking=1)", "caja=/",
    'tmp="$(mktemp /etc/x.XXXXXX)"', "read -r caja", "for critico in gdm3; do :; done", "printf -v conf /etc/x",
    "cat > \"$tmp\" <<X\nhola\nX", "bash <<'HOOK'\nid\nHOOK", "cat > \"$caja/otro\" <<'STUB'\nx\nSTUB",
    "systemctl restart apt-daily", "curl -s https://x | bash",
])
def test_control_negativo_apt_guardia_fuera_de_su_clase_se_caza(linea: str):
    assert _sembrado_apt(linea), linea


@pytest.mark.parametrize("linea", [
    "apt-get -s -o Debug::NoLocking=1 autoremove > /dev/null || true",
    'APT_CONFIG="$caja/apt.conf" apt-get "${opciones[@]}" -y remove "$inocuo" > "$caja/inocuo.txt" 2>&1 || rc=$?',
    'mv -fT -- "$tmp" "$conf"', 'rm -f -- "$hook"', 'cp -- "$estado_dpkg" "$caja/status"',
    'mkdir -p -- "$caja/parts" "$caja/cache/archives/partial"', "critico=nvidia-system-station",
    'echo "apt-guardia-instalar: $conf ya esta" >&2', "cat > \"$caja/dpkg\" <<'STUB'\nexec /usr/bin/dpkg x\nSTUB",
])
def test_apt_guardia_si_puede_lo_declarado(linea: str):
    assert _sembrado_apt(linea) == []


# --- earlyoom-proteger: ejecutado sobre tmp_path (rutas, root y systemd sustituidos) --------

EARLYOOM_VIEJO = ROOT / "tests" / "fixtures" / "etc_default_earlyoom.viejo"  # el archivo ANTES del cambio de 2026-10-14 (sha 7e8a44b6...)
EARLYOOM_NUEVO = ROOT / "adopted" / "system-config" / "etc_default_earlyoom"  # lo desplegado desde 2026-10-14
SCRIPT_EARLYOOM = bm.SRC_DIR / EARLYOOM
BAK = f"etc_default_earlyoom.{hashlib.sha256(EARLYOOM_VIEJO.read_bytes()).hexdigest()}"


def _args(fichero: Path) -> list[str]:
    linea = [x for x in fichero.read_text(encoding="utf-8").splitlines() if x.startswith("EARLYOOM_ARGS=")]
    assert len(linea) == 1
    return shlex.split(shlex.split(linea[0].split("=", 1)[1])[0])


def _alternativas(regex: str) -> set[str]:
    return set(regex.strip("()").split("|"))


def _heredoc(texto: str, delim: str) -> str:
    return texto.split(f"<<'{delim}'\n", 1)[1].split(f"\n{delim}\n", 1)[0] + "\n"


def test_earlyoom_proteger_embebe_exactamente_el_fichero_nuevo_y_los_sha256():
    texto = SCRIPT_EARLYOOM.read_text(encoding="utf-8")
    assert _heredoc(texto, "NUEVO") == EARLYOOM_NUEVO.read_text(encoding="utf-8")
    assert f"sha_viejo={hashlib.sha256(EARLYOOM_VIEJO.read_bytes()).hexdigest()}\n" in texto
    assert f"sha_nuevo={hashlib.sha256(EARLYOOM_NUEVO.read_bytes()).hexdigest()}\n" in texto
    # Lo que se valida con earlyoom --dryrun es lo que systemd le pasara (systemd quita las comillas simples).
    assert _heredoc(texto, "ARGS").splitlines() == _args(EARLYOOM_NUEVO)


def test_earlyoom_nuevo_conserva_umbrales_y_amplia_avoid_y_prefer():
    viejo, nuevo = _args(EARLYOOM_VIEJO), _args(EARLYOOM_NUEVO)
    assert viejo[:6] == nuevo[:6] == ["-r", "60", "-m", "10", "-s", "100,100"]
    assert [viejo[6], viejo[8]] == [nuevo[6], nuevo[8]] == ["--avoid", "--prefer"] and len(nuevo) == len(viejo) == 10
    assert _alternativas(nuevo[7]) - _alternativas(viejo[7]) == {"vllm", "VLLM", "docker", "containerd", "^bb-"}
    assert _alternativas(nuevo[9]) - _alternativas(viejo[9]) == {"xdist", "bb-portero"}
    assert _alternativas(viejo[7]) < _alternativas(nuevo[7]) and _alternativas(viejo[9]) < _alternativas(nuevo[9])


@pytest.mark.parametrize("comm,avoid,prefer", [
    ("VLLM::EngineCor", True, False), ("vllm", True, False), ("dockerd", True, False), ("containerd-shim", True, False),
    ("bb-root-run", True, False), ("[pytest-xdist r", False, True), ("pytest", False, True),
    ("python3", False, False), ("xbb-x", False, False),
])
def test_las_regex_nuevas_sobre_los_comm_reales(comm: str, avoid: bool, prefer: bool):
    # re.search emula regexec sin anclar; estas regex no usan nada que difiera entre POSIX ERE y re.
    nuevo = _args(EARLYOOM_NUEVO)
    assert (re.search(nuevo[7], comm) is not None, re.search(nuevo[9], comm) is not None) == (avoid, prefer)


@pytest.mark.skipif(shutil.which("earlyoom") is None, reason="earlyoom no instalado")
def test_earlyoom_real_compila_las_regex_nuevas_y_el_control_negativo_no():
    args = _args(EARLYOOM_NUEVO)
    ok = subprocess.run(["timeout", "1", "earlyoom", "--dryrun", *args], capture_output=True, text=True)
    assert ok.returncode == 124, ok.stdout + ok.stderr
    malo = subprocess.run(["timeout", "1", "earlyoom", "--dryrun", *args[:7], args[7][:-1]],
                          capture_output=True, text=True)
    assert malo.returncode == 6 and "could not compile regexp" in malo.stdout + malo.stderr


def _earlyoom(tmp_path: Path, uid_root: int = UID) -> tuple[Path, Path, Path, Path]:
    texto = SCRIPT_EARLYOOM.read_text(encoding="utf-8")
    etc = tmp_path / "etc_default"
    etc.mkdir()
    conf = etc / "earlyoom"
    base = tmp_path / "varlib" / "blackbox"
    (tmp_path / "varlib").mkdir()
    for viejo, nuevo in (("conf=/etc/default/earlyoom", f"conf={conf}"), ("dir_conf=/etc/default", f"dir_conf={etc}"),
                         ("base=/var/lib/blackbox", f"base={base}"), ("espera=3", "espera=0.4"),
                         ('!= "0" ]]', f'!= "{uid_root}" ]]'), ("-o root -g root", f"-o {UID}"),
                         ("chown root:root", f"chown {UID}:{os.getgid()}")):
        assert viejo in texto, f"la sustitucion {viejo!r} no casa: prueba vacia"
        texto = texto.replace(viejo, nuevo)
    s = tmp_path / "earlyoom-proteger.sh"
    s.write_text(texto, encoding="utf-8")
    stub = tmp_path / "stub"
    stub.mkdir()
    log = tmp_path / "systemctl.log"
    for nombre, cuerpo in (
            ("systemctl", f'echo "$*" >> {log}\nif [ "$1" = is-active ]; then e=$(cat {stub}/estado); echo "$e"; '
                          f'[ "$e" = active ]; fi\n'),
            ("journalctl", 'echo "journal stub $*"\n'),
            ("earlyoom", f'rc=$(cat {stub}/earlyoom_rc)\n[ "$rc" = vive ] && exec sleep 30\nexit "$rc"\n')):
        (stub / nombre).write_text("#!/bin/sh\n" + cuerpo, encoding="utf-8")
        (stub / nombre).chmod(0o755)
    (stub / "estado").write_text("active\n", encoding="utf-8")
    (stub / "earlyoom_rc").write_text("vive\n", encoding="utf-8")
    shutil.copy(EARLYOOM_VIEJO, conf)
    return s, conf, base, stub


def _correr_earlyoom(s: Path, stub: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["/bin/bash", str(s)], env={"PATH": f"{stub}:{rr.PATH_FIJO}", "LC_ALL": "C"},
                          capture_output=True, text=True, timeout=60)


def _llamadas(tmp_path: Path) -> list[str]:
    log = tmp_path / "systemctl.log"
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def _restos(conf: Path) -> list[Path]:
    return sorted(conf.parent.glob(".earlyoom.*"))


def test_earlyoom_proteger_escribe_lo_nuevo_guarda_lo_viejo_y_es_idempotente(tmp_path: Path):
    s, conf, base, stub = _earlyoom(tmp_path)
    r = _correr_earlyoom(s, stub)
    assert r.returncode == 0, r.stdout + r.stderr
    assert conf.read_bytes() == EARLYOOM_NUEVO.read_bytes() and stat.S_IMODE(conf.stat().st_mode) == 0o644
    assert (base / BAK).read_bytes() == EARLYOOM_VIEJO.read_bytes()
    assert _restos(conf) == [] and _llamadas(tmp_path) == ["restart earlyoom", "is-active earlyoom"]
    assert "tras el reinicio (is-active): active" in r.stdout and "journal stub -u earlyoom -n 5" in r.stdout
    r2 = _correr_earlyoom(s, stub)
    assert r2.returncode == 0 and "ya tiene el contenido nuevo" in r2.stdout, r2.stdout + r2.stderr
    assert conf.read_bytes() == EARLYOOM_NUEVO.read_bytes()
    assert _llamadas(tmp_path) == ["restart earlyoom", "is-active earlyoom", "is-active earlyoom"], "reinicio de mas"


def test_earlyoom_proteger_control_negativo_contenido_desconocido_no_escribe_nada(tmp_path: Path):
    s, conf, base, stub = _earlyoom(tmp_path)
    conf.write_text(EARLYOOM_VIEJO.read_text(encoding="utf-8") + "# editado a mano\n", encoding="utf-8")
    antes = conf.read_bytes()
    r = _correr_earlyoom(s, stub)
    assert r.returncode == 3 and "ni el conocido" in r.stderr
    assert conf.read_bytes() == antes and not base.exists() and _restos(conf) == [] and _llamadas(tmp_path) == []


def test_earlyoom_proteger_control_negativo_si_no_queda_activo_restaura_el_viejo(tmp_path: Path):
    s, conf, base, stub = _earlyoom(tmp_path)
    (stub / "estado").write_text("failed\n", encoding="utf-8")
    r = _correr_earlyoom(s, stub)
    assert r.returncode == 5 and "se restaura" in r.stderr, r.stdout + r.stderr
    assert conf.read_bytes() == EARLYOOM_VIEJO.read_bytes() and stat.S_IMODE(conf.stat().st_mode) == 0o644
    assert (base / BAK).exists() and _restos(conf) == []
    assert _llamadas(tmp_path) == ["restart earlyoom", "is-active earlyoom", "restart earlyoom", "is-active earlyoom"]


def test_earlyoom_proteger_control_negativo_regex_que_earlyoom_rechaza_no_escribe(tmp_path: Path):
    s, conf, base, stub = _earlyoom(tmp_path)
    (stub / "earlyoom_rc").write_text("6\n", encoding="utf-8")
    r = _correr_earlyoom(s, stub)
    assert r.returncode == 4 and "salio 6" in r.stderr
    assert conf.read_bytes() == EARLYOOM_VIEJO.read_bytes() and not base.exists() and _restos(conf) == []
    assert _llamadas(tmp_path) == []


def test_earlyoom_proteger_control_negativo_conf_symlink_no_se_sigue(tmp_path: Path):
    s, conf, _, stub = _earlyoom(tmp_path)
    blanco = tmp_path / "blanco"
    shutil.copy(EARLYOOM_VIEJO, blanco)
    conf.unlink()
    conf.symlink_to(blanco)
    r = _correr_earlyoom(s, stub)
    assert r.returncode == 3 and "symlink" in r.stderr
    assert blanco.read_bytes() == EARLYOOM_VIEJO.read_bytes() and conf.is_symlink() and _llamadas(tmp_path) == []


def test_earlyoom_proteger_con_base_ya_existente_y_segura_si_escribe(tmp_path: Path):
    # Control del control: las guardas de base de abajo no rechazan TODO directorio existente.
    s, conf, base, stub = _earlyoom(tmp_path)
    base.mkdir()
    base.chmod(0o755)
    r = _correr_earlyoom(s, stub)
    assert r.returncode == 0, r.stdout + r.stderr
    assert conf.read_bytes() == EARLYOOM_NUEVO.read_bytes() and (base / BAK).read_bytes() == EARLYOOM_VIEJO.read_bytes()


@pytest.mark.parametrize("caso", ["escribible", "otro_dueno", "bak_symlink"])
def test_earlyoom_proteger_control_negativo_base_insegura_aborta_sin_tocar_conf(tmp_path: Path, caso: str):
    s, conf, base, stub = _earlyoom(tmp_path, uid_root=UID + 1 if caso == "otro_dueno" else UID)
    base.mkdir()
    base.chmod(0o777 if caso == "escribible" else 0o755)  # chmod explicito: mkdir hereda el umask (002 aqui)
    blanco = tmp_path / "blanco"
    blanco.write_text("intacto", encoding="utf-8")
    if caso == "bak_symlink":
        (base / BAK).symlink_to(blanco)
    r = _correr_earlyoom(s, stub)
    motivo = "symlink" if caso == "bak_symlink" else "no es de root o es escribible por grupo/otros"
    assert r.returncode == 3 and motivo in r.stderr, r.stdout + r.stderr
    assert conf.read_bytes() == EARLYOOM_VIEJO.read_bytes() and _restos(conf) == [] and _llamadas(tmp_path) == []
    assert blanco.read_text(encoding="utf-8") == "intacto"
