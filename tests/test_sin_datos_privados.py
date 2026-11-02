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

Encogida el 2026-11-01 (boleta #35 A de Luis, antes de reescribir el historial): el usuario, el hostname y la IP de la
LAN salen de la evidencia, las fichas y los documentos, y los nombres ajenos de los comentarios adoptados y del codigo
de la entrega; la linea base pasa de 494 archivos (4361 datos) a 38 (80). Quedan los nombres de compatibilidad que la
maquina usa hoy, las MAC e IP sinteticas de fixtures, la direccion de diseno del laboratorio y lo que la boleta #32 A
deja sin tocar. Los tokens del patron ya no van literales en este archivo (ver TOKENS).
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
BASE = Path(__file__).parent / "fixtures" / "datos_privados_baseline.json"
IP_RFC1918 = (
    r"(?<![\d.])(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})(?!\.?\d)"
)
# Los tokens que busca la guarda (el usuario y el hostname de la maquina, los nombres de proyectos ajenos y las rutas
# privadas de la base de conocimiento) NO van literales en este archivo (boleta #35 A, 2026-11-01): la reescritura del
# historial (boleta #36 B) sustituye esos mismos tokens en cada blob y, si estuvieran aqui, dejaria a la guarda buscando
# su propio marcador. Van en base64; `test_el_patron_construido_es_el_firmado` fija el sha256 del patron resultante, que
# es identico al de la regex literal anterior.
TOKENS: dict[str, Any] = json.loads(base64.b64decode(
    "eyJ1c3VhcmlvIjoibGNhc2FyaW4iLCJob3N0IjoiYWl0b3BhdG9tIiwicHJveWVjdG9zIjpbImF0bGFzIiwidHdpbmVyIiwiYWVxdWl0YXMiLCJj"
    "dWVuemEiLCJvd25fY2hhdHMiLCJvd24tY2hhdHMiLCJvZmZpY2Uyb2ZmaWNlIiwiZGVjbHV0dGVyIiwibzJvIl0sImtiIjoia25vd2xlZGdlLyg/"
    "OnJlZmVyZW5jZXN8aW52ZXN0aWdhdGlvbnN8aWRlbnRpdHkpLyJ9"
).decode("utf-8"))
USUARIO: str = TOKENS["usuario"]
HOST: str = TOKENS["host"]
PROYECTOS: list[str] = TOKENS["proyectos"]
SHA256_PATRON = "b7947268c3a41419dbf9843da69f5c04bc6b976ad58a0ceb341ce5e59c830e7e"


def construye_patron(usuario: str, host: str, proyectos: list[str], kb: str) -> re.Pattern[str]:
    return re.compile(
        r"(?:[0-9a-f]{2}:){5}[0-9a-f]{2}"
        # `<usuario>-maker` es la cuenta PUBLICA de GitHub que aloja el repo (LICENSE, URL de clonado, la
        # dependencia simplecode de los hooks): no es dato de la maquina. El usuario de la maquina si.
        + "|" + usuario + r"(?!-maker)|" + host
        + r"|" + IP_RFC1918
        + r"|(?<![a-z0-9])(?:" + "|".join(proyectos) + r")(?![a-z0-9])"
        + r"|" + kb,
        re.I,
    )


PATRON = construye_patron(USUARIO, HOST, PROYECTOS, TOKENS["kb"])

# Lo que queda en la linea base FUERA de `tasks/` y `docs/`, con su motivo (2026-11-01). Un archivo de codigo,
# unidad o test no entra en la linea base sin una razon escrita aqui; uno que se limpia sale de las dos.
_ADOPTADA = ("copia adoptada: `bb drift` la compara byte a byte con el instalado; el comentario cita el nombre REAL de la "
             "unidad del consumidor que corre bajo app.slice (compatibilidad, boleta #35 A)")
_MAC = "MAC sintetica de fixture (aa:bb:..., 00:11:...), en la linea base desde el 2026-10-11"
_REF = "ruta de procedencia en la KB del consumidor (`ref_raiz` de rules/firmas_gb10.json, una sola fuente)"
_LEGADO = "clave de legado del contrato neutro (boleta #18 A): se lee por compatibilidad hasta que el productor migre"
_LAB = "la /24 RFC 1918 es la direccion de DISENO del puente propio del laboratorio (bblab0), no un dato de la maquina"
MOTIVOS: dict[str, str] = {
    "SPEC.md": _LAB,
    "adopted/system-config/home_@BB_USUARIO@_.config_systemd_user_app.slice.d_99-blackbox.conf": _ADOPTADA,
    "data/cargas_externas.json": "nombre real del contenedor que la medicion excluye (`contenedores_excluidos`)",
    "rules/firmas_gb10.json": _REF,
    "tests/test_closure_kernel.py": _MAC,
    "tests/test_closure_netconsole_edges.py": _MAC,
    "tests/test_cobertura_grupo4_residuos.py": _REF,
    "tests/test_hallazgo.py": _REF,
    "tests/test_hardware_missing_selectors.py": _MAC,
    "tests/test_hardware_reader_command_ownership.py": _MAC,
    "tests/test_hardware_reader_safety.py": _MAC,
    "tests/test_kernel_capture.py": _MAC,
    "tests/test_lab_no_toca_docker0.py": _LAB,
    "tests/test_wifi_trial_invariants.py": _MAC,
    "tools/accion_termica.py": _LEGADO,
    "tools/hallazgo.py": _REF,
    "tools/incident_report.py": _LEGADO,
    "tools/portero_docker_lab.sh": _LAB,
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


def _kb() -> tuple[str, list[str]]:
    """La raiz y los directorios de la ruta privada, sacados del mismo token que usa el patron."""
    m = re.fullmatch(r"([a-z]+)/\(\?:([a-z|]+)\)/", TOKENS["kb"])
    assert m, TOKENS["kb"]
    return m.group(1), m.group(2).split("|")


def test_el_patron_construido_es_el_firmado():
    assert hashlib.sha256(PATRON.pattern.encode("utf-8")).hexdigest() == SHA256_PATRON
    assert PATRON.flags & re.I
    # control: el mismo constructor con un solo token distinto da otro patron, y ese token deja de cazarse
    sin_ultimo = construye_patron(USUARIO, HOST, PROYECTOS[:-1], TOKENS["kb"])
    assert hashlib.sha256(sin_ultimo.pattern.encode("utf-8")).hexdigest() != SHA256_PATRON
    assert len(PATRON.findall(PROYECTOS[-1])) == 1 and sin_ultimo.findall(PROYECTOS[-1]) == []
    otro_usuario = construye_patron(USUARIO[:-1], HOST, PROYECTOS, TOKENS["kb"])
    assert hashlib.sha256(otro_usuario.pattern.encode("utf-8")).hexdigest() != SHA256_PATRON


def test_el_patron_caza_lo_de_la_boleta_23_y_respeta_lo_publico():
    kb, dirs = _kb()
    proyecto = dict(zip(("a", "t", "aq", "c", "oc_", "oc", "oo", "d", "o"), PROYECTOS, strict=True))
    sembrados = ["/home/" + USUARIO + "/x", HOST + "-41f1", "10." + "194." + "62.85", "192.168." + "100.25",
                 "172.16." + "0.1", "172.31." + "255.254", "10.0." + "0.0/24", proyecto["a"].capitalize(), proyecto["t"],
                 proyecto["oc"], proyecto["oc_"], proyecto["o"], f"{kb}/{dirs[2]}/x.md", f"{kb}/{dirs[0]}/",
                 proyecto["oo"].title()]
    for s in sembrados:
        assert cuenta(s) == 1, s
    limpios = ["192.0.2.7", "198.51.100.0/24", "203.0.113.9", "172.15.0.1", "172.32.0.1", "simplecode",
               f"github.com/{USUARIO}-maker/simplecode", proyecto["a"] + "sian", proyecto["a"] + "2", f"{kb}/hardware/x.md",
               "version 110." + "0.0.1", "10.1." + "2.3.4", "foo" + proyecto["o"], "127.0.0.1"]
    for s in limpios:
        assert cuenta(s) == 0, s


def test_la_guarda_detecta_un_archivo_nuevo_y_una_subida():
    assert compara({"nuevo.md": 1}, {}) == ["nuevo.md: archivo nuevo con 1 dato(s) privado(s)"]
    assert compara({"a.md": 3}, {"a.md": 2}) == ["a.md: sube de 2 a 3"]
    assert compara({"a.md": 2}, {"a.md": 2}) == []
    assert cuenta("host " + HOST + "-41f1 y aa:bb:cc:dd:ee:ff") == 2
    assert cuenta("texto limpio") == 0
