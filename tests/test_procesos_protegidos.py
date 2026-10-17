"""Una sola lista de procesos protegidos para los cuatro vigilantes que matan (voto de Luis 2026-10-14).

Antes habia cinco listas que no coincidian: la guardia podia mandar SIGTERM a un hijo de la sesion de Claude que el
escalon protegia, y gpuoom elegia al motor vLLM. Ahora la fuente es data/procesos_protegidos.json y cada consumidor
lleva una copia de respaldo para cuando el fichero falte o este roto (un bb-usable que no arranca reinicia la maquina
por FailureAction=reboot-immediate).

Controles negativos: cada prueba de comportamiento usa nombres que el codigo VIEJO no protegia, y cada una lleva un
nombre que NO debe protegerse (python3, pytest), para que "proteger todo" no pase.
"""

from __future__ import annotations

import importlib.machinery as machinery
import importlib.util as util
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools import gpuoom_bb, vigilante_memavail

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data" / "procesos_protegidos.json"
EARLYOOM = RAIZ / "adopted" / "system-config" / "etc_default_earlyoom"
# Desplegado por Luis con `sudo -n bb-root-run earlyoom-proteger` el 2026-10-16 (DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01):
# el contenido nuevo vive ya en system-config/ y el que estuvo desplegado desde el 2026-10-14 queda como fixture, para que
# las pruebas "solo amplia" y el control negativo sigan midiendo contra el estado anterior real (sha 89fe78da...).
EARLYOOM_PENDIENTE = EARLYOOM
EARLYOOM_VIEJO = RAIZ / "tests" / "fixtures" / "etc_default_earlyoom.viejo"

# Lo votado, en comm reales de esta maquina (ps -eo comm, 2026-10-14). Independiente del fichero: si alguien borra
# un nombre del fichero Y de los respaldos, esto sigue exigiendolo.
VOTADOS = ("claude", "claude-desktop", "node", "cowork-linux-he", "electron", "chrome_crashpad", "Xorg", "Xwayland",
           "gnome-shell", "gnome-session-b", "gdm3", "gdm-x-session", "systemd", "systemd-journal", "systemd-oomd",
           "init", "sshd", "dbus", "dbus-daemon", "pipewire", "pipewire-pulse", "wireplumber", "xdg-desktop-por",
           "earlyoom", "docker", "dockerd", "docker-proxy", "containerd", "containerd-shim", "vllm", "VLLM::EngineCor",
           "bb", "bb-usable", "bb-guardia-proc", "bb-vigilante-mo", "bb-portero")
NO_PROTEGIDOS = ("python3", "pytest", "bash", "sleep")

# Medido el 2026-10-14 contra el --avoid que estuvo desplegado: nombres de la lista que earlyoom NO evitaba.
# DEBT-EARLYOOM-AVOID-NO-CUBRE-LA-LISTA-UNICA-01. Desde el despliegue del 2026-10-16 el desplegado los cubre todos.
FALTABAN_ANTES = {"claude", "node", "cowork-linux-he", "electron", "chrome_crashpad", "Xwayland", "init", "dbus",
                  "earlyoom", "bb"}
FALTAN_EN_EARLYOOM: set[str] = set()


def _cargar_bin(ruta: Path, nombre: str):
    loader = machinery.SourceFileLoader(nombre, str(ruta))
    spec = util.spec_from_loader(nombre, loader)
    assert spec is not None
    mod = util.module_from_spec(spec)
    sys.modules[nombre] = mod  # el @dataclass de la guardia se busca en sys.modules
    try:
        loader.exec_module(mod)
    finally:
        sys.modules.pop(nombre, None)
    return mod


@pytest.fixture(scope="module")
def bbu():
    return _cargar_bin(RAIZ / "bin" / "bb-usable", "bb_usable_pp")


@pytest.fixture(scope="module")
def guardia():
    return _cargar_bin(RAIZ / "bin" / "bb-guardia-proceso", "bb_guardia_pp")


def _fichero():
    d = json.loads(DATOS.read_text(encoding="utf-8"))
    pares = tuple((e["nombre"], e["prefijo"]) for e in d["comm"])
    return (frozenset(n for n, p in pares if not p), tuple(n for n, p in pares if p)), d


def _protege(exactos, prefijos, comm):
    return comm in exactos or comm.startswith(prefijos)


# ------------------------------------------------------------------ consistencia


def test_todos_los_consumidores_leen_el_fichero_y_coinciden(bbu, guardia):
    esperado, _ = _fichero()
    assert bbu.PROTEGIDOS_ERROR is None and guardia.PROTEGIDOS_ERROR is None
    assert vigilante_memavail.PROTEGIDOS.error is None
    vistos = {
        "bb-usable": (bbu.COMM_PROTEGIDOS, bbu.COMM_PROTEGIDOS_PREFIJOS),
        "bb-guardia-proceso": (guardia.COMM_PROTEGIDOS, guardia.COMM_PROTEGIDOS_PREFIJOS),
        "gpuoom": (gpuoom_bb.PROTEGIDOS.exactos, gpuoom_bb.PROTEGIDOS.prefijos),
        "memavail": (vigilante_memavail.PROTEGIDOS.exactos, vigilante_memavail.PROTEGIDOS.prefijos),
    }
    assert {k: v for k, v in vistos.items() if v != esperado} == {}
    assert vigilante_memavail.PROTEGIDAS is vigilante_memavail.PROTEGIDOS.unidades


def test_los_respaldos_son_identicos_al_fichero(bbu, guardia):
    _, d = _fichero()
    pares = tuple((e["nombre"], e["prefijo"]) for e in d["comm"])
    assert bbu.PROTEGIDOS_RESPALDO == pares
    assert guardia.PROTEGIDOS_RESPALDO == pares
    assert vigilante_memavail.RESPALDO_COMM == tuple((e["nombre"], e["prefijo"], e.get("unidad")) for e in d["comm"])
    assert vigilante_memavail.RESPALDO_UNIDADES == tuple(e["patron"] for e in d["unidades"])


def test_cada_consumidor_protege_lo_votado_y_nada_mas(bbu, guardia):
    """Contra el fichero Y contra cada respaldo: borrar un nombre de cualquiera de los dos falla aqui."""
    _, d = _fichero()
    fuentes = {
        "fichero": tuple((e["nombre"], e["prefijo"]) for e in d["comm"]),
        "respaldo bb-usable": bbu.PROTEGIDOS_RESPALDO,
        "respaldo guardia": guardia.PROTEGIDOS_RESPALDO,
        "respaldo vigilante_memavail": tuple((n, p) for n, p, _ in vigilante_memavail.RESPALDO_COMM),
    }
    nombres = set(VOTADOS)
    for pares in fuentes.values():
        nombres |= {n for n, _ in pares}
    fallos = []
    for fuente, pares in fuentes.items():
        exactos, prefijos = frozenset(n for n, p in pares if not p), tuple(n for n, p in pares if p)
        fallos += [(fuente, c) for c in sorted(nombres) if not _protege(exactos, prefijos, c)]
        fallos += [(fuente, "PROTEGE " + c) for c in NO_PROTEGIDOS if _protege(exactos, prefijos, c)]
    assert fallos == []


# ------------------------------------------------------------------ por consumidor


def test_guardia_no_toca_a_la_sesion_ni_al_motor(guardia):
    """Con un pid real del mismo usuario: el codigo viejo devolvia None (matable) para estos comm."""
    hijo = subprocess.Popen(["sleep", "30"])
    try:
        assert guardia._es_intocable(hijo.pid, "python3") is None  # control: lo no protegido sigue matable
        for comm in ("claude", "VLLM::EngineCor", "node", "gnome-shell", "Xorg", "bb-usable", "pipewire"):
            motivo = guardia._es_intocable(hijo.pid, comm)
            assert motivo is not None and "intocables" in motivo, comm
    finally:
        hijo.kill()
        hijo.wait()


def _proc(bbu, pid, comm, rss_kb):
    return bbu.Proc(pid, pid, comm, 1000, rss_kb, 1, "app-com.anthropic.Claude-1.scope", "/app.slice")


def test_escalon_protege_la_lista_unica_y_mata_lo_demas(bbu):
    """pipewire y los portales xdg- no estaban en la lista vieja del escalon."""
    for comm in ("claude", "VLLM::EngineCor", "pipewire", "xdg-desktop-por", "gdm3", "bb-portero"):
        assert bbu.protegido(_proc(bbu, 50, comm, 1), 1) is not None, comm
    assert bbu.protegido(_proc(bbu, 50, "python3", 1), 1) is None
    m = bbu.MuestraEscalon(ahora=1000.0, psi=99.0, slices=(bbu.SliceApp("/app.slice", 95, 100),),
                           candidatos=(_proc(bbu, 50, "pipewire", 9_000_000), _proc(bbu, 51, "python3", 1_000)),
                           propio_pid=1, propio_pgid=1)
    d = bbu.decidir_escalon(m, bbu.EstadoEscalon(alto_desde=0.0))
    assert d.accion == "matar" and d.objetivo is not None and d.objetivo.comm == "python3"


def test_gpuoom_no_elige_a_la_sesion_ni_al_motor():
    cs = [gpuoom_bb.Candidato(1, "VLLM::EngineCor", 2_000_000, 0, 0, 60_000_000),
          gpuoom_bb.Candidato(2, "claude", 9_000_000, 0, 0, 0),
          gpuoom_bb.Candidato(3, "python3", 1_000_000, 0, 0, 0)]
    v, _ = gpuoom_bb.elige_victima(cs, propio_pid=999)
    assert v is not None and v.pid == 3


def test_memavail_rechaza_toda_unidad_que_lleve_un_nombre_protegido():
    _, d = _fichero()
    nombres = [e["nombre"] for e in d["comm"]] + [e["patron"].replace("\\", "") for e in d["unidades"]] + list(VOTADOS)
    no_rechazadas = []
    for n in nombres:
        u = vigilante_memavail.Unidad(f"bb-lab-{n}-1.scope", "/cg/x", 1 << 30)
        if vigilante_memavail.elige_culpable([u])["veredicto"] != "REFUSED":
            no_rechazadas.append(u.nombre)
    assert no_rechazadas == []
    # control negativo: las suites elegibles siguen siendo detenibles
    for nombre in ("bb-lab-acaparador-1185676.scope", "bb-portero-suite-4242.scope"):
        u = vigilante_memavail.Unidad(nombre, "/cg/x", 1 << 30)
        assert vigilante_memavail.elige_culpable([u])["veredicto"] == "DETENER", nombre


# ------------------------------------------------------------------ respaldo: nunca lanza


ROTOS = {
    "falta": None,
    "json_roto": "{no es json",
    "lista_en_vez_de_objeto": "[]",
    "sin_comm": "{}",
    "comm_vacio": '{"comm": [], "unidades": []}',
    "prefijo_no_bool": '{"comm": [{"nombre": "claude", "prefijo": "si"}], "unidades": []}',
    "nombre_vacio": '{"comm": [{"nombre": "", "prefijo": false}], "unidades": []}',
}


@pytest.mark.parametrize("caso", sorted(ROTOS))
def test_fichero_roto_usa_el_respaldo_y_no_lanza(caso, tmp_path, bbu, guardia):
    ruta = tmp_path / "procesos_protegidos.json"
    if ROTOS[caso] is not None:
        ruta.write_text(ROTOS[caso], encoding="utf-8")
    for mod in (bbu, guardia):
        exactos, prefijos, error = mod._cargar_protegidos(ruta)
        assert error is not None
        assert (exactos, prefijos) == (frozenset(n for n, p in mod.PROTEGIDOS_RESPALDO if not p),
                                       tuple(n for n, p in mod.PROTEGIDOS_RESPALDO if p))
    p = vigilante_memavail.cargar_protegidos(ruta)
    assert p.error is not None and p.comm("claude") and p.unidades.search("bb-usable.service")


def test_regex_de_unidad_invalida_usa_el_respaldo(tmp_path):
    ruta = tmp_path / "p.json"
    ruta.write_text('{"comm": [{"nombre": "x", "prefijo": false, "unidad": "("}], "unidades": []}', encoding="utf-8")
    p = vigilante_memavail.cargar_protegidos(ruta)
    assert p.error is not None and p.comm("VLLM::EngineCor")


def test_un_fichero_valido_si_se_usa(tmp_path, bbu):
    """Control negativo de las dos de arriba: si el lector devolviera siempre el respaldo, esto falla."""
    ruta = tmp_path / "p.json"
    ruta.write_text('{"comm": [{"nombre": "solo-este", "prefijo": false}], "unidades": []}', encoding="utf-8")
    assert bbu._cargar_protegidos(ruta) == (frozenset({"solo-este"}), (), None)
    assert vigilante_memavail.cargar_protegidos(ruta).comm("solo-este") and not vigilante_memavail.cargar_protegidos(ruta).comm("claude")


def _copia_sin_datos(tmp_path: Path, script: str, contenido: str | None) -> Path:
    """El ejecutable en un arbol sin tools/ y con data/ ausente o roto, como si se hubiera desplegado mal."""
    (tmp_path / "repo" / "bin").mkdir(parents=True)
    destino = tmp_path / "repo" / "bin" / script
    shutil.copy2(RAIZ / "bin" / script, destino)
    if contenido is not None:
        (tmp_path / "repo" / "data").mkdir()
        (tmp_path / "repo" / "data" / "procesos_protegidos.json").write_text(contenido, encoding="utf-8")
    return destino


@pytest.mark.parametrize("contenido", [None, "{roto"], ids=["falta", "corrupto"])
def test_bb_usable_carga_sin_fichero_con_el_respaldo(tmp_path, contenido):
    mod = _cargar_bin(_copia_sin_datos(tmp_path, "bb-usable", contenido), "bb_usable_sin_datos")
    assert mod.PROTEGIDOS_ERROR is not None and mod.comm_protegido("claude") and not mod.comm_protegido("python3")
    assert "COPIA DE RESPALDO" in mod.protegidos_origen()


def _arranca_y_sigue_vivo(cmd: list[str], env: dict[str, str], log: Path, espera: str) -> str:
    """Vivo = `wait` agota su plazo. El primer latido de los dos demonios llega a los 15-30 s, asi que en 5 s solo
    corre el arranque (carga, sonda, anuncio de la lista): si algo de eso lanza, el proceso sale antes del plazo."""
    with open(log, "w", encoding="utf-8") as fh:
        proc = subprocess.Popen(cmd, env=env, stdout=fh, stderr=subprocess.STDOUT)
    try:
        proc.wait(timeout=5)
        vivo = False
    except subprocess.TimeoutExpired:
        vivo = True
    finally:
        proc.kill()
        proc.wait()
    salida = log.read_text(encoding="utf-8")
    assert vivo, f"el demonio murio al arrancar (rc={proc.returncode}):\n{salida}"
    assert espera in salida, salida
    return salida


@pytest.mark.parametrize("script", ["bb-usable", "bb-guardia-proceso"])
def test_el_demonio_arranca_y_sigue_vivo_con_el_fichero_roto(tmp_path, script):
    """Arranque real del ejecutable (sin NOTIFY_SOCKET, datos en tmp, guardia en DRY-RUN): no se cae y lo dice."""
    destino = _copia_sin_datos(tmp_path, script, "{roto")
    env = {k: v for k, v in os.environ.items() if k != "NOTIFY_SOCKET"}
    env.update(BLACKBOX_DATA=str(tmp_path / "datos"), BB_GUARDIA_DRY_RUN="1",
               BB_USABLE_PSI_PATH=str(tmp_path / "sin-psi"))
    (tmp_path / "datos").mkdir()
    salida = _arranca_y_sigue_vivo([sys.executable, str(destino)], env, tmp_path / "log", "procesos protegidos:")
    assert "procesos protegidos:" in salida and "COPIA DE RESPALDO" in salida and "JSONDecodeError" in salida, salida


# ------------------------------------------------------------------ earlyoom (configuracion desplegada)


def _avoid_earlyoom(ruta: Path = EARLYOOM) -> re.Pattern[str]:
    m = re.search(r'^EARLYOOM_ARGS="(.*)"$', ruta.read_text(encoding="utf-8"), re.M)
    assert m, f"sin EARLYOOM_ARGS en {ruta}"
    args = shlex.split(m.group(1))
    # earlyoom 1.7: regex POSIX extendida sin anclar contra /proc/<pid>/comm; esta es valida igual en Python
    return re.compile(args[args.index("--avoid") + 1])


def faltan_en_earlyoom(ruta: Path = EARLYOOM) -> set[str]:
    _, d = _fichero()
    avoid = _avoid_earlyoom(ruta)
    return {e["nombre"] for e in d["comm"] if not avoid.search(e["nombre"])}


def test_earlyoom_hueco_medido_es_el_declarado():
    """Si earlyoom gana o pierde cobertura, o la lista cambia, este numero cambia y hay que mirarlo."""
    assert faltan_en_earlyoom() == FALTAN_EN_EARLYOOM


def test_earlyoom_instrumento_discrimina():
    avoid = _avoid_earlyoom()
    assert avoid.search("VLLM::EngineCor") and avoid.search("bb-usable") and not avoid.search("python3")


def test_earlyoom_cubre_toda_la_lista():
    assert faltan_en_earlyoom() == set()


def test_control_negativo_el_desplegado_anterior_dejaba_diez_nombres_fuera():
    """El instrumento puede salir rojo: contra el contenido que estuvo desplegado antes faltan exactamente los diez."""
    assert faltan_en_earlyoom(EARLYOOM_VIEJO) == FALTABAN_ANTES


# ------------------------------------------------------------------ earlyoom: el contenido pendiente de despliegue


def test_earlyoom_pendiente_cubre_toda_la_lista_y_no_evita_lo_no_protegido():
    """Lo que el close_check pedira al fichero desplegado, medido ya sobre el contenido que Luis va a desplegar."""
    avoid = _avoid_earlyoom(EARLYOOM_PENDIENTE)
    assert faltan_en_earlyoom(EARLYOOM_PENDIENTE) == set()
    assert [c for c in VOTADOS if not avoid.search(c)] == []
    assert [c for c in NO_PROTEGIDOS if avoid.search(c)] == []
    # sin ancla, estos nombres cortos casarian con cualquier comm que los contenga
    assert [c for c in ("initctl", "nodejs-x", "dbbench", "xbb-x", "earlyoomx") if avoid.search(c)] == []


def test_earlyoom_pendiente_solo_amplia_lo_desplegado():
    """Todo comm que el --avoid desplegado evita lo sigue evitando el pendiente (nombres medidos en ps -eo comm)."""
    desplegado, pendiente = _avoid_earlyoom(EARLYOOM_VIEJO), _avoid_earlyoom(EARLYOOM_PENDIENTE)
    comms = ("claude-desktop", "dbus-daemon", "pipewire-pulse", "wireplumber", "gnome-shell", "gnome-session-b", "Xorg",
             "gdm3", "sshd", "systemd-journal", "journal-udp-for", "xdg-desktop-por", "antigravity", "vllm",
             "VLLM::EngineCor", "dockerd", "containerd-shim", "bb-usable")
    assert [c for c in comms if not desplegado.search(c)] == []  # control: el desplegado los evita todos
    assert [c for c in comms if not pendiente.search(c)] == []


@pytest.mark.parametrize("quitado", sorted(FALTABAN_ANTES))
def test_control_negativo_quitar_un_nombre_del_pendiente_se_ve(tmp_path, quitado):
    """El instrumento de arriba puede salir rojo: sin uno de los diez nombres, faltan_en_earlyoom lo nombra."""
    texto = EARLYOOM_PENDIENTE.read_text(encoding="utf-8")
    regex = _avoid_earlyoom(EARLYOOM_PENDIENTE).pattern
    # la alternativa exacta, vaya en medio ('|x|', '|x)') o la primera ('(x|')
    nueva = re.sub(rf"\|{re.escape(quitado)}(?=[|)])|(?<=\(){re.escape(quitado)}\|", "", regex, count=1)
    assert nueva != regex and texto.count(regex) == 1
    copia = tmp_path / "etc_default_earlyoom"
    copia.write_text(texto.replace(regex, nueva), encoding="utf-8")
    assert faltan_en_earlyoom(copia) == {quitado}
