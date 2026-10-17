"""Read-only DRM/KMS coherence before a DGX OS OTA: gate from raw rows, its incident negatives,
and the recovery trial that closes FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT.

Twin of `tools.update_boot_coherence` (kernel gate). Nothing here changes the host: the capture
reads modprobe.d with grep, /proc/cmdline (only DRM tokens), dpkg-query, /sys/class/drm and
`ss`. The effective `nvidia_drm.modeset` is 0400 root: as a user the literal `Permission denied`
row is recorded (could_not_run); only `--root-read`, run by Luis at the console, adds the sealed
`sudo -n bb-root-run drm-modeset-leer` row, and its value counts only if its boot_id is the
capture's. Whether the target OTA requires KMS is a vendor statement, never inferred from the host:
it comes from `ota-target.json` (https source on a vendor domain); without it the observation stays
None. The `preflight.check_drm` snapshot is DERIVED from rows + statement, the incident negatives
are mutations of those rows that the gate MUST block, and a pass needs `recovery-trial.json`:
before / target-or-alternate-config / rollback, three distinct boot_ids, display connector state
and an SSH session in every phase.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from tools import preflight
from tools.capture_io import read_regular_bytes, strict_json_loads
from tools.update_boot_coherence import Correr, Row, capturar

FINDING = "FORUM-00-DGX-OTA-DRM-COMPAT-PREFLIGHT"
TRIAL_FILE = "recovery-trial.json"
DECLARATION_FILE = "ota-target.json"
TRIAL_PHASES = ("antes", "objetivo", "rollback")
VENDOR_DOMAINS = ("nvidia.com", "gigabyte.com")
BOOT_ID = ["cat", "/proc/sys/kernel/random/boot_id"]
MODESET_USER = ["cat", "/sys/module/nvidia_drm/parameters/modeset"]
MODESET_ROOT = ["sudo", "-n", "bb-root-run", "drm-modeset-leer"]
MODPROBE = ["grep", "-rHsE", r"^[[:space:]]*options[[:space:]]+nvidia[-_]drm",
            "/etc/modprobe.d", "/lib/modprobe.d", "/usr/lib/modprobe.d"]
CMDLINE = ["grep", "-oE", r"(nvidia[-_]drm\.[a-z_]+=[^ ]*|nomodeset)", "/proc/cmdline"]
PAQUETE = ["dpkg-query", "-W", "-f=${Package} ${Version} ${db:Status-Abbrev}\n", "nvidia-drm-options-modeset0"]
RELEASE = ["grep", "-E", "^DGX_SWBUILD_VERSION=", "/etc/dgx-release"]
SSH_ESCUCHA = ["ss", "-Hltn", "sport = :22"]
SSH_SESION = ["printenv", "SSH_CONNECTION"]
DRM = "/sys/class/drm"
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def comandos_conectores(drm: str = DRM) -> list[list[str]]:
    """Connector inventory: listing, per-connector status, and the driver bound to each card."""
    estados = sorted(glob.glob(f"{drm}/card*-*/status"))
    tarjetas = sorted(p for p in glob.glob(f"{drm}/card*") if re.fullmatch(r"card\d+", Path(p).name))
    filas = [["ls", drm]]
    if estados:
        filas.append(["grep", "-H", ".", *estados])
    if tarjetas:
        filas.append(["readlink", "-f", *(f"{t}/device/driver" for t in tarjetas)])
    return filas


def comandos_drm(root_read: bool = False, drm: str = DRM) -> list[list[str]]:
    """The literal read-only probes of the pre-OTA DRM gate."""
    return [BOOT_ID, ["uname", "-r"], RELEASE, PAQUETE, MODPROBE, CMDLINE,
            MODESET_ROOT if root_read else MODESET_USER, SSH_ESCUCHA, *comandos_conectores(drm)]


def _argv(row: Row) -> list[str]:
    argv = row.get("argv")
    return [str(a) for a in argv] if isinstance(argv, list) else str(argv).split()


def _fila(rows: list[Row], argv: list[str]) -> Row | None:
    return next((r for r in rows if _argv(r)[:len(argv)] == argv), None)


def _boot_id(rows: list[Row]) -> str | None:
    fila = _fila(rows, BOOT_ID)
    if fila is None or fila["rc"] != 0:
        return None
    valor = str(fila["stdout"]).strip()
    return valor if _UUID.fullmatch(valor) else None


def _modeset(rows: list[Row]) -> str | None:
    """Effective modeset: the sealed root read bound to this boot_id, or a readable user read."""
    raiz = _fila(rows, MODESET_ROOT)
    if raiz is not None:
        if raiz["rc"] != 0:
            return None
        texto = str(raiz["stdout"])
        boot = re.search(r"(?m)^== boot_id\n(\S+)$", texto)
        valor = re.search(r"(?m)^nvidia_drm\.modeset=(Y|N)$", texto)
        if boot is None or valor is None or boot.group(1) != _boot_id(rows):
            return None  # value from another boot, or unreadable: no verdict
        return valor.group(1)
    usuario = _fila(rows, MODESET_USER)
    if usuario is None or usuario["rc"] != 0:
        return None
    valor = str(usuario["stdout"]).strip()
    return valor if valor in ("Y", "N") else None


def _override(rows: list[Row]) -> bool | None:
    """modeset=0 declared in modprobe.d, or nvidia-drm.modeset=0 / nomodeset on the command line."""
    modprobe, cmdline = _fila(rows, MODPROBE), _fila(rows, CMDLINE)
    if modprobe is None or cmdline is None or modprobe["rc"] not in (0, 1) or cmdline["rc"] not in (0, 1):
        return None  # grep rc 2: unreadable configuration
    en_modprobe = re.search(r"(?m)\bmodeset=0\b", str(modprobe["stdout"])) is not None
    tokens = str(cmdline["stdout"]).split()
    return en_modprobe or "nomodeset" in tokens or any(
        re.fullmatch(r"nvidia[-_]drm\.modeset=0", t) for t in tokens)


def _ssh_escucha(rows: list[Row]) -> bool | None:
    fila = _fila(rows, SSH_ESCUCHA)
    if fila is None or fila["rc"] != 0:
        return None
    return re.search(r"(?m)^LISTEN\b", str(fila["stdout"])) is not None


def leer_declaracion(directorio: Path) -> dict[str, Any] | None:
    """The vendor statement for the target OTA, or None when absent or not attributable."""
    try:
        doc = strict_json_loads(read_regular_bytes(directorio / DECLARATION_FILE, 64 * 1024).decode("utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError):
        return None
    return doc if isinstance(doc, dict) else None


def requiere_kms(declaracion: dict[str, Any] | None) -> bool | None:
    """`requires_kms` only from a statement with target, text and an https vendor source."""
    if declaracion is None or declaracion.get("id") != FINDING:
        return None
    fuente = urlsplit(str(declaracion.get("source", "")))
    host = (fuente.hostname or "").lower()
    de_vendor = any(host == d or host.endswith("." + d) for d in VENDOR_DOMAINS) and not host.startswith("forums.")
    textos = all(isinstance(declaracion.get(k), str) and declaracion[k].strip() for k in ("target_ota", "statement"))
    valor = declaracion.get("requires_kms")
    return valor if fuente.scheme == "https" and de_vendor and textos and type(valor) is bool else None


def snapshot_drm(rows: list[Row], declaracion: dict[str, Any] | None) -> dict[str, Any]:
    """Derive the `preflight.check_drm` snapshot from literal rows; None = could not observe."""
    return {"effective_modeset": _modeset(rows), "target_requires_kms": requiere_kms(declaracion),
            "override_present": _override(rows), "recovery_accessible": _ssh_escucha(rows)}


def _cambia(rows: list[Row], argv: list[str], **cambios: Any) -> list[Row]:
    return [{**r, **cambios} if _argv(r)[:len(argv)] == argv else r for r in rows]


def _con_modeset(rows: list[Row], valor: str) -> list[Row]:
    raiz = _fila(rows, MODESET_ROOT)
    if raiz is not None:
        texto = re.sub(r"(?m)^nvidia_drm\.modeset=[YN]$", f"nvidia_drm.modeset={valor}", str(raiz["stdout"]))
        return _cambia(rows, MODESET_ROOT, stdout=texto)
    return _cambia(rows, MODESET_USER, rc=0, stdout=valor + "\n", stderr="")


def negativos_drm(rows: list[Row], declaracion: dict[str, Any] | None
                  ) -> dict[str, tuple[list[Row], dict[str, Any] | None, str]]:
    """Incident states built by mutating the real rows; each one MUST block with its label."""
    exige = {**(declaracion or {}), "requires_kms": True}
    apagado = _con_modeset(rows, "N")
    modprobe = _fila(rows, MODPROBE) or {"stdout": ""}
    con_override = str(modprobe["stdout"]) + "/etc/modprobe.d/zz-nvidia-drm-override.conf:options nvidia-drm modeset=0\n"
    return {
        "OTA exige KMS y modeset efectivo apagado (incidente 382452)": (
            apagado, exige, "OTA requires KMS but effective modeset is not enabled"),
        "override modeset=0 en modprobe.d con KMS apagado": (
            _cambia(apagado, MODPROBE, rc=0, stdout=con_override), declaracion,
            "DRM override conflicts with effective KMS state"),
        "nomodeset en la linea de arranque": (
            _cambia(apagado, CMDLINE, rc=0, stdout="nomodeset\n"), declaracion,
            "DRM override conflicts with effective KMS state"),
        "sin SSH que escuche (sin camino de recuperacion)": (
            _cambia(rows, SSH_ESCUCHA, rc=0, stdout=""), declaracion, "recovery path is unavailable"),
    }


def evaluar_negativos(rows: list[Row], declaracion: dict[str, Any] | None) -> tuple[str, str] | None:
    """None if every incident negative blocks with its own label; otherwise a `fail` verdict."""
    for nombre, (mutadas, decl, etiqueta) in negativos_drm(rows, declaracion).items():
        juicio = preflight.check_drm(snapshot_drm(mutadas, decl))
        if juicio["status"] != "block" or etiqueta not in juicio["findings"]:
            return ("fail", f"gate is blind to incident negative '{nombre}': {juicio}")
    return None


def conectores(rows: list[Row]) -> dict[str, tuple[str, str]] | None:
    """{connector: (status, driver)} from the listing, status and readlink rows; None if unreadable."""
    listado = _fila(rows, ["ls", DRM])
    if listado is None or listado["rc"] != 0:
        return None
    nombres = [n for n in str(listado["stdout"]).split() if re.fullmatch(r"card\d+-.+", n)]
    estados: dict[str, str] = {}
    fila = _fila(rows, ["grep", "-H", "."])
    for linea in str((fila or {}).get("stdout", "")).splitlines():
        m = re.fullmatch(r".*/(card\d+-[^/]+)/status:(\S+)", linea)
        if m:
            estados[m.group(1)] = m.group(2)
    drivers: dict[str, str] = {}
    enlaces = _fila(rows, ["readlink", "-f"])
    if enlaces is not None:
        rutas, salida = _argv(enlaces)[2:], str(enlaces["stdout"]).splitlines()
        if len(rutas) == len(salida):
            drivers = {Path(r).parent.parent.name: Path(s).name for r, s in zip(rutas, salida)}
    return {n: (estados.get(n, "unknown"), drivers.get(n.split("-", 1)[0], "unknown")) for n in nombres}


def _config(rows: list[Row]) -> tuple[str, ...] | None:
    """Configuration fingerprint of a phase: release, override package, modprobe options, cmdline."""
    partes = [_fila(rows, argv) for argv in (RELEASE, PAQUETE, MODPROBE, CMDLINE)]
    if any(p is None for p in partes):
        return None
    return tuple(f"{p['rc']}:{p['stdout']}" for p in partes if p is not None)


def _fase(rows: list[Row], fase: str) -> list[Row]:
    return [r for r in rows if r.get("phase") == fase]


def evaluar_recuperacion(rows: list[Row]) -> tuple[str, str]:
    """Display + SSH across before / target-or-alternate config / rollback, three real boots."""
    fases = {f: _fase(rows, f) for f in TRIAL_PHASES}
    boots = {f: _boot_id(filas) for f, filas in fases.items()}
    faltan = [f for f, b in boots.items() if b is None]
    if faltan:
        return "unknown", f"recovery trial lacks a boot_id for phases {faltan}"
    sin_ssh = [f for f, filas in fases.items()
               if (s := _fila(filas, SSH_SESION)) is None or s["rc"] != 0 or len(str(s["stdout"]).split()) != 4]
    if sin_ssh:
        return "unknown", f"recovery trial lacks an SSH session for phases {sin_ssh}: run each phase over SSH"
    if len(set(boots.values())) != 3:
        return "fail", "recovery trial phases share a boot_id: no reboot was observed"
    pantallas = {f: conectores(filas) for f, filas in fases.items()}
    if any(p is None for p in pantallas.values()):
        return "unknown", "recovery trial lacks a readable /sys/class/drm listing"
    sin_pantalla = [f for f in ("antes", "rollback") if not any(e == "connected" for e, _ in (pantallas[f] or {}).values())]
    if sin_pantalla:
        return "fail", f"no display connector is connected in phases {sin_pantalla}"
    if not any(e == "connected" and d.startswith("nvidia") for e, d in (pantallas["objetivo"] or {}).values()):
        return "fail", "target configuration registers no connected nvidia-drm connector (incident 382452 reproduced)"
    configs = {f: _config(filas) for f, filas in fases.items()}
    if any(c is None for c in configs.values()):
        return "unknown", "recovery trial lacks the configuration rows (release, package, modprobe, cmdline)"
    if configs["objetivo"] == configs["antes"]:
        return "fail", "target phase runs the same configuration as before: no OTA or alternate config was applied"
    if configs["rollback"] != configs["antes"]:
        return "fail", "rollback phase does not restore the configuration observed before"
    return "pass", ("nvidia-drm connector connected on the target configuration, display and SSH in all "
                    "three phases, rollback restores the previous configuration, three distinct boot_ids")


def _normaliza(row: dict[str, Any]) -> Row:
    return {"argv": row.get("argv", row.get("cmd")), "rc": row.get("exit_code", row.get("exit")),
            "stdout": row.get("stdout", ""), "stderr": row.get("stderr", ""), "phase": row.get("phase")}


def leer_prueba(directorio: Path) -> list[Row] | None:
    try:
        doc = strict_json_loads(read_regular_bytes(directorio / TRIAL_FILE, 4 * 1024 * 1024).decode("utf-8"))
    except (OSError, UnicodeError, ValueError, RecursionError):
        return None
    if not isinstance(doc, dict) or doc.get("id") != FINDING or not isinstance(doc.get("commands"), list):
        return None
    return [_normaliza(r) for r in doc["commands"] if isinstance(r, dict)]


def evaluar_cierre(rows: list[Row], documento: dict[str, Any], directorio: Path) -> tuple[str, str]:
    """Full close verdict for the DRM gate: raw-derived snapshot, negatives, recovery trial."""
    declaracion = leer_declaracion(directorio)
    derivado = snapshot_drm(rows, declaracion)
    if derivado != documento.get("snapshot"):
        return "fail", f"recorded snapshot differs from the one derived from raw rows and {DECLARATION_FILE}: {derivado}"
    ciego = evaluar_negativos(rows, declaracion)
    if ciego:
        return ciego
    prueba = leer_prueba(directorio)
    if prueba is None:
        return "unknown", (f"pre-OTA DRM gate and its {len(negativos_drm(rows, declaracion))} incident negatives "
                           f"pass; recovery unproven: {TRIAL_FILE} (before / target or alternate config / "
                           "rollback, each over SSH) is missing")
    return evaluar_recuperacion(prueba)


def _sin_ip(fila: dict[str, Any]) -> dict[str, Any]:
    """SSH_CONNECTION is `client_ip client_port server_ip server_port`: keep the ports, drop the IPs."""
    campos = str(fila["stdout"]).split()
    if fila["argv"] != SSH_SESION or len(campos) != 4:
        return fila
    return {**fila, "stdout": f"<ip> {campos[1]} <ip> {campos[3]}\n"}


def comandos_prueba(drm: str = DRM) -> list[list[str]]:
    return [BOOT_ID, ["uname", "-r"], RELEASE, PAQUETE, MODPROBE, CMDLINE, SSH_SESION, *comandos_conectores(drm)]


def capturar_fase(fase: str, correr: Correr = subprocess.run, drm: str = DRM) -> list[dict[str, Any]]:
    return [_sin_ip(f) for f in capturar(comandos_prueba(drm), correr, fase=fase)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="modo", required=True)
    gate = sub.add_parser("drm", help="capture the read-only pre-OTA DRM gate into DIR")
    gate.add_argument("--out", type=Path, required=True)
    gate.add_argument("--root-read", action="store_true",
                      help="add the sealed `sudo -n bb-root-run drm-modeset-leer` row (Luis, at the console)")
    trial = sub.add_parser("trial", help="append one recovery-trial phase into DIR (run it over SSH)")
    trial.add_argument("--phase", choices=TRIAL_PHASES, required=True)
    trial.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    if args.modo == "trial":
        ruta = args.out / TRIAL_FILE
        doc = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {"id": FINDING, "commands": []}
        doc["commands"] = [r for r in doc["commands"] if r.get("phase") != args.phase]
        nuevas = capturar_fase(args.phase)
        doc["commands"] += nuevas
        ruta.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(evaluar_recuperacion([_normaliza(f) for f in doc["commands"]]), ensure_ascii=False))
        return 0
    filas = capturar(comandos_drm(args.root_read))
    rows = [_normaliza(f) for f in filas]
    declaracion = leer_declaracion(args.out)
    snapshot = snapshot_drm(rows, declaracion)
    resultado = preflight.check_drm(snapshot)
    no_corrio = [" ".join(f["argv"]) for f in filas if f["exit_code"] not in (0, 1) or "Permission denied" in f["stderr"]]
    (args.out / "commands.json").write_text(json.dumps(
        {"id": FINDING, "commands": filas}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.out / "preflight.json").write_text(json.dumps(
        {"id": FINDING, "kind": "drm", "read_only": True, "declaration_file": DECLARATION_FILE,
         "snapshot": snapshot, "preflight_result": resultado, "could_not_run": no_corrio,
         "could_not_run_count": len(no_corrio)}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(resultado, sort_keys=True))
    return 0 if resultado["status"] == "pass" else 2


if __name__ == "__main__":
    sys.exit(main())
