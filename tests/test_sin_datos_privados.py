"""Guarda del repo publico: ningun archivo versionado gana datos de la maquina ni de proyectos privados.

Medido el 2026-10-11 (analisis de la frontera entre bb y su consumidor): el arbol ya publicaba MACs, IPs de LAN, el hostname y nombres de
proyectos privados dentro de evidencias historicas. Esas evidencias llevan hashes de procedencia y NO se
reescriben; quedan en `datos_privados_baseline.json` con su cuenta. La guarda falla si un archivo nuevo
contiene estos datos o si uno de la lista sube su cuenta. La lista solo puede encogerse.

Ampliada el 2026-11-01 (boleta #23 A de Luis: el repo publico no lleva datos personales de la maquina): el
usuario, cualquier IP RFC 1918 (las de documentacion, 192.0.2.x, 198.51.100.x y 203.0.113.x, no lo son), los
nombres de proyectos ajenos y las rutas privadas de la base de conocimiento. La linea base se recalculo ese
dia; lo que queda fuera de `tasks/` y `docs/` lleva su motivo en `MOTIVOS`. `simplecode` NO entra en el patron:
es el nombre real de una dependencia de los hooks. Al cerrar la boleta ese mismo dia salieron de la linea base
`DECISIONS.md` (el usuario del sudoers), el usuario de las rutas de `SPEC.md`, la IP de `tests/test_observador_ping.py`
y el id de ficha ajeno de `tools/reboot_verdict.py` y su test: ninguno tenia motivo, solo esperaba su turno.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BASE = Path(__file__).parent / "fixtures" / "datos_privados_baseline.json"
IP_RFC1918 = (
    r"(?<![\d.])(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})(?!\.?\d)"
)
PATRON = re.compile(
    r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}"
    # `lcasarin-maker` es la cuenta PUBLICA de GitHub que aloja el repo (LICENSE, URL de clonado, la
    # dependencia simplecode de los hooks): no es dato de la maquina. El usuario de la maquina si.
    r"|lcasarin(?!-maker)|aitopatom"
    r"|" + IP_RFC1918
    + r"|(?<![a-z0-9])(?:atlas|twiner|aequitas|cuenza|own_chats|own-chats|office2office|declutter|o2o)(?![a-z0-9])"
    r"|knowledge/(?:references|investigations|identity)/",
    re.I,
)

# Lo que queda en la linea base FUERA de `tasks/` y `docs/`, con su motivo (2026-11-01). Un archivo de codigo,
# unidad o test no entra en la linea base sin una razon escrita aqui; uno que se limpia sale de las dos.
_ADOPTADA = "copia adoptada: `bb drift` la compara byte a byte con el instalado, que lleva el nombre en un comentario"
_MAC = "MAC sintetica de fixture (aa:bb:..., 00:11:...), en la linea base desde el 2026-10-11"
_REF = "ruta de procedencia en la KB del consumidor (`ref_raiz` de rules/firmas_gb10.json, una sola fuente)"
_ENTREGA = "la entrega al consumidor de conocimiento: su carpeta y el manifiesto que citan las evidencias"
_LEGADO = "clave de legado del contrato neutro (boleta #18 A): se lee por compatibilidad hasta que el productor migre"
_LAB = "la /24 RFC 1918 es la direccion de DISENO del puente propio del laboratorio (bblab0), no un dato de la maquina"
MOTIVOS: dict[str, str] = {
    "SPEC.md": _LAB,
    "adopted/root-scripts/earlyoom-proteger.sh": "script sellado por sha256 en el manifiesto de bb-root-run",
    "adopted/system-config/etc_default_earlyoom": _ADOPTADA,
    "adopted/system-config/etc_sysctl.d_99-blackbox-panic.conf": _ADOPTADA,
    "adopted/system-config/home_@BB_USUARIO@_.config_systemd_user_app.slice.d_99-blackbox.conf": _ADOPTADA,
    "adopted/systemd-user/atom-gpu-telemetry.service": _ADOPTADA,
    "data/cargas_externas.json": "nombre real del contenedor que la medicion excluye (`contenedores_excluidos`)",
    "rules/firmas_gb10.json": _REF,
    "suspended/MANIFIESTO.md": "nombre real de una unit suspendida: `bb drift` lee su `Ruta original`",
    "tests/fixtures/etc_default_earlyoom.viejo": "fixture fijado por sha256: el /etc/default/earlyoom desplegado",
    "tests/test_closure_kernel.py": _MAC,
    "tests/test_closure_netconsole_edges.py": _MAC,
    "tests/test_cobertura_grupo4_residuos.py": _REF,
    "tests/test_entrega_cosecha_foro.py": _ENTREGA,
    "tests/test_hallazgo.py": _REF,
    "tests/test_hardware_missing_selectors.py": _MAC,
    "tests/test_hardware_reader_command_ownership.py": _MAC,
    "tests/test_hardware_reader_safety.py": _MAC,
    "tests/test_kernel_capture.py": _MAC,
    "tests/test_lab_no_toca_docker0.py": _LAB,
    "tests/test_wifi_trial_invariants.py": _MAC,
    "tools/accion_termica.py": _LEGADO,
    "tools/entrega_cosecha_foro.py": _ENTREGA,
    "tools/hallazgo.py": _REF,
    "tools/incident_report.py": _LEGADO,
    "tools/portero_docker_lab.sh": _LAB,
    "tools/verifica_cosecha_foro.py": "atribucion del origen del patron cosechado (lente de cosecha)",
}


def cuenta(texto: str) -> int:
    return len(PATRON.findall(texto))


def archivos_versionados() -> list[str]:
    r = subprocess.run(
        ["git", "ls-files", "-z"], cwd=RAIZ, capture_output=True, check=True
    )
    return [p for p in r.stdout.decode().split("\0") if p]


def medir() -> dict[str, int]:
    out: dict[str, int] = {}
    ilegibles: list[str] = []
    for rel in archivos_versionados():
        if rel == "tests/fixtures/datos_privados_baseline.json" or rel == Path(__file__).relative_to(RAIZ).as_posix():
            continue
        p = RAIZ / rel
        try:
            if not p.is_file():
                continue
            n = cuenta(p.read_bytes().decode("utf-8", errors="ignore"))
        except OSError:
            ilegibles.append(rel)
            continue
        if n:
            out[rel] = n
    assert ilegibles == [], f"archivos versionados que no se pudieron leer: {ilegibles}"
    return out


def compara(actual: dict[str, int], base: dict[str, int]) -> list[str]:
    faltas = [f"{r}: archivo nuevo con {n} dato(s) privado(s)" for r, n in actual.items() if r not in base]
    faltas += [f"{r}: sube de {base[r]} a {n}" for r, n in actual.items() if r in base and n > base[r]]
    return faltas


def test_el_repo_no_gana_datos_privados():
    base = json.loads(BASE.read_text(encoding="utf-8"))
    assert compara(medir(), base) == []


def test_lo_que_queda_fuera_de_tasks_y_docs_lleva_su_motivo():
    base = json.loads(BASE.read_text(encoding="utf-8"))
    fuera = {r for r in base if not r.startswith(("tasks/", "docs/"))}
    assert sorted(fuera - MOTIVOS.keys()) == [], "en la linea base sin motivo en MOTIVOS"
    assert sorted(MOTIVOS.keys() - fuera) == [], "motivo de algo que ya no esta en la linea base: quitarlo"


def test_el_patron_caza_lo_de_la_boleta_23_y_respeta_lo_publico():
    sembrados = ["/home/" + "lcasarin/x", "aitopatom" + "-41f1", "10.194." + "62.85", "192.168." + "100.25",
                 "172.16." + "0.1", "172.31." + "255.254", "10.0." + "0.0/24", "Atlas", "twiner", "own-chats",
                 "own_chats", "o2o", "knowledge/" + "identity/x.md", "knowledge/" + "references/", "Office2Office"]
    for s in sembrados:
        assert cuenta(s) == 1, s
    limpios = ["192.0.2.7", "198.51.100.0/24", "203.0.113.9", "172.15.0.1", "172.32.0.1", "simplecode",
               "github.com/lcasarin-maker/simplecode", "atlassian", "atlas2", "knowledge/hardware/x.md",
               "version 110." + "0.0.1", "10.1." + "2.3.4", "fooo2o", "127.0.0.1"]
    for s in limpios:
        assert cuenta(s) == 0, s


def test_la_guarda_detecta_un_archivo_nuevo_y_una_subida():
    assert compara({"nuevo.md": 1}, {}) == ["nuevo.md: archivo nuevo con 1 dato(s) privado(s)"]
    assert compara({"a.md": 3}, {"a.md": 2}) == ["a.md: sube de 2 a 3"]
    assert compara({"a.md": 2}, {"a.md": 2}) == []
    assert cuenta("host " + "aitopatom" + "-41f1 y aa:bb:cc:dd:ee:ff") == 2
    assert cuenta("texto limpio") == 0
