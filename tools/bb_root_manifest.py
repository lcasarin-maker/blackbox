"""Propone y vigila el manifiesto de `bb-root-run` (scripts sellados por hash).

`--propose`: lee `adopted/root-scripts/manifest.src.json` (nombre -> file, descripcion,
timeout) y los scripts, valida cada uno con las MISMAS guardas del runner, escribe la
propuesta en `--out` e imprime: el JSON exacto, el texto completo de cada script con su
sha256, y UN comando `sudo sh -c '...'` que instala runner, manifiesto y sudoers. El
comando compara el sha256 de cada copia YA root-owned con el impreso antes de moverla a
su sitio, asi que cambiar el fichero del repo entre la revision de Luis y la instalacion
hace fallar la instalacion en vez de instalar otra cosa.

`--check`: compara el manifiesto instalado (si se puede leer) con los scripts del repo y
lista los que cambiaron desde la aprobacion. rc 0 = todo igual, 1 = hay cambios,
2 = COULD_NOT_RUN (manifiesto instalado ilegible: no es un veredicto de limpio).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import sys
from pathlib import Path

from tools import bb_root_run as rr

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "adopted" / "root-scripts"
PENDIENTE = ROOT / "adopted" / "pendiente-de-despliegue"
PROPUESTA = PENDIENTE / "bb-root-run.manifest.json"
SUDOERS = PENDIENTE / "etc_sudoers.d_bb-root-run"
RUNNER = ROOT / "tools" / "bb_root_run.py"
RUNNER_INSTALADO = "/usr/local/sbin/bb-root-run"
SUDOERS_INSTALADO = "/etc/sudoers.d/bb-root-run"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def proponer(src_dir: Path) -> dict[str, dict[str, object]]:
    """El manifiesto que aprobaria los scripts tal como estan. ValueError si alguno no pasa."""
    src = json.loads((src_dir / "manifest.src.json").read_text(encoding="utf-8"))
    manifest: dict[str, dict[str, object]] = {}
    for name in sorted(src):
        e = src[name]
        try:
            if not rr.nombre_valido(name):
                raise rr.Rechazo(f"nombre invalido {name!r}")
            fila: dict[str, object] = {"file": e["file"], "sha256": "0" * 64,
                                       "descripcion": e["descripcion"],
                                       "timeout": e.get("timeout", rr.TIMEOUT_DEFECTO)}
            rr.entrada({name: fila}, name)  # file simple y timeout entero ANTES de leer nada
            data = rr.leer_una_vez(str(src_dir / e["file"]), "script")
            rr.comprobar_shebang(data)
            manifest[name] = fila | {"sha256": sha(data)}
        except rr.Rechazo as err:
            raise ValueError(f"{name}: {err}") from err
    return manifest


def serializar(manifest: dict[str, dict[str, object]]) -> bytes:
    return (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _paso(origen: Path, destino: str, modo: str, digest: str) -> str:
    nuevo = destino + ".nuevo"  # constante sin espacios; sudoers.d ignora nombres con '.'
    return (f"install -m {modo} -o root -g root {shlex.quote(str(origen))} {nuevo}; "
            f'echo "{digest}  {nuevo}" | sha256sum -c -; ')


def comando_instalacion(propuesta: Path, runner: Path, sudoers: Path) -> str:
    m = rr.MANIFEST
    interior = (
        "set -e; install -d -m 0755 -o root -g root /etc/bb-root-run; "
        + _paso(runner, RUNNER_INSTALADO, "0755", sha(runner.read_bytes()))
        + _paso(propuesta, m, "0644", sha(propuesta.read_bytes()))
        + _paso(sudoers, SUDOERS_INSTALADO, "0440", sha(sudoers.read_bytes()))
        + f"visudo -c -f {SUDOERS_INSTALADO}.nuevo; "
        + f"mv -f {RUNNER_INSTALADO}.nuevo {RUNNER_INSTALADO}; "
        + f"mv -f {m}.nuevo {m}; "
        + f"mv -f {SUDOERS_INSTALADO}.nuevo {SUDOERS_INSTALADO}"
    )
    return "sudo sh -c " + shlex.quote(interior)


def texto_propuesta(manifest: dict[str, dict[str, object]], src_dir: Path,
                    propuesta: Path, runner: Path) -> str:
    partes = ["===== manifiesto propuesto (" + str(propuesta) + ", sha256 "
              + sha(propuesta.read_bytes()) + ") =====", serializar(manifest).decode()]
    for name, e in manifest.items():
        partes.append(f"===== {name}: {e['file']} sha256 {e['sha256']} =====")
        partes.append((src_dir / str(e["file"])).read_text(encoding="utf-8"))
    partes.append(f"===== runner {runner} sha256 {sha(runner.read_bytes())} =====")
    partes.append("Revisa los scripts de arriba; para instalar runner + manifiesto + sudoers:")
    partes.append(comando_instalacion(propuesta, runner, SUDOERS))
    return "\n".join(partes) + "\n"


def revisar(instalado: Path, src_dir: Path, runner: Path, runner_instalado: Path) -> tuple[int, list[str]]:
    """(rc, lineas): 0 todo igual, 1 algo cambio, 2 algo no se pudo leer (COULD_NOT_RUN)."""
    try:
        aprobado = json.loads(instalado.read_bytes())
    except (OSError, ValueError) as e:
        aprobado = e
    if not isinstance(aprobado, dict):
        return 2, [f"COULD_NOT_RUN: el manifiesto instalado {instalado} no se puede leer "
                   f"como objeto JSON ({aprobado})"]
    src = json.loads((src_dir / "manifest.src.json").read_text(encoding="utf-8"))
    cambios: list[str] = []
    no_corrio: list[str] = []
    iguales = 0
    for name, e in sorted(aprobado.items()):
        try:
            actual = sha(rr.leer_una_vez(str(src_dir / e["file"]), "script"))
        except rr.Rechazo as err:
            cambios.append(f"ilegible o ausente en el repo: {name} ({err})")
            continue
        if actual == e["sha256"]:
            iguales += 1
        else:
            cambios.append(f"cambiado desde la aprobacion: {name} ({e['file']}: "
                           f"aprobado {e['sha256'][:12]}, repo {actual[:12]})")
    cambios += [f"sin aprobar (en manifest.src.json, no instalado): {n}"
                for n in sorted(set(src) - set(aprobado))]
    try:
        if runner_instalado.read_bytes() != runner.read_bytes():
            cambios.append(f"runner cambiado: {runner} difiere de {runner_instalado}")
    except OSError as e:
        no_corrio.append(f"COULD_NOT_RUN: runner instalado {runner_instalado} ilegible ({e.strerror})")
    resumen = (f"[bb-root-manifest] aprobados iguales: {iguales}, cambios: {len(cambios)}, "
               f"could_not_run: {len(no_corrio)}")
    rc = 2 if no_corrio else (1 if cambios else 0)
    return rc, cambios + no_corrio + [resumen]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    modo = p.add_mutually_exclusive_group(required=True)
    modo.add_argument("--propose", action="store_true")
    modo.add_argument("--check", action="store_true")
    p.add_argument("--src-dir", type=Path, default=SRC_DIR)
    p.add_argument("--out", type=Path, default=PROPUESTA, help="donde escribir la propuesta")
    p.add_argument("--installed", type=Path, default=Path(rr.MANIFEST))
    p.add_argument("--runner", type=Path, default=RUNNER)
    p.add_argument("--installed-runner", type=Path, default=Path(RUNNER_INSTALADO))
    a = p.parse_args(argv)
    if a.check:
        rc, lineas = revisar(a.installed, a.src_dir, a.runner, a.installed_runner)
        print("\n".join(lineas))
        return rc
    try:
        manifest = proponer(a.src_dir)
    except ValueError as e:
        print(f"[bb-root-manifest] PROPUESTA RECHAZADA: {e}", file=sys.stderr)
        return 3
    a.out.write_bytes(serializar(manifest))
    sys.stdout.write(texto_propuesta(manifest, a.src_dir, a.out.resolve(), a.runner.resolve()))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
