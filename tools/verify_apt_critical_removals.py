"""Verify APT critical-removal classification against captured read-only evidence.

This checks the preflight instrument. A passing instrument check does not establish
that an OEM package graph is protected or that an APT guard is installed.

The installed guard is judged separately from `apt-guard-captures.json` (written by
`python3 tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD/collect_guard.py --instalado --out <dir>` after Luis runs the sealed
`apt-guardia-instalar`): `checks.installed_guard` is `verified` only when that capture
read the deployed files, their sha256 match the sealed script, and real APT aborted a
critical removal before dpkg while letting an innocuous one through. OEM coverage is
not observable from this host, so `closure` stays `open` and `--cierre` exits 2.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from tools.preflight import check_apt

ROOT = Path(__file__).resolve().parents[1]
LISTA = ROOT / "data" / "apt-paquetes-criticos.txt"
SCRIPT = ROOT / "adopted" / "root-scripts" / "apt-guardia-instalar.sh"
CONF_INSTALADO = "/etc/apt/apt.conf.d/00-bb-apt-guardia"
HOOK_INSTALADO = "/usr/local/sbin/bb-apt-guardia"
LINEA_HOOK = f'DPkg::Pre-Install-Pkgs:: "{HOOK_INSTALADO}";'
MENSAJE_BLOQUEO = "bb-apt-guardia: esta transaccion quita"
CAPTURA = "apt-guard-captures.json"
CRITICO = "nvidia-system-station"  # el metapaquete del hilo 348170
INOCUO = "tree"  # hoja sin dependientes; su remocion no toca la lista


def criticos(path: Path = LISTA) -> list[str]:
    """Los nombres de data/apt-paquetes-criticos.txt: lineas no vacias que no empiezan por '#'."""
    nombres = [x.strip() for x in path.read_text(encoding="utf-8").splitlines()]
    return [x for x in nombres if x and not x.startswith("#")]


def repo(nombre: str) -> Path:
    """Fichero desplegable: en adopted/system-config/ una vez desplegado (LEEME paso 5), si no en pendiente-de-despliegue/."""
    adoptado = ROOT / "adopted" / "system-config" / nombre
    return adoptado if adoptado.exists() else ROOT / "adopted" / "pendiente-de-despliegue" / nombre


CONF_REPO = repo("etc_apt_apt.conf.d_00-bb-apt-guardia")
HOOK_REPO = repo("usr_local_sbin_bb-apt-guardia")


def hashes_esperados(script: Path = SCRIPT) -> dict[str, str]:
    """sha256 del .conf y del hook que instala el script sellado (sus constantes sha_conf/sha_hook)."""
    texto = script.read_text(encoding="utf-8")
    return {k: m.group(1) for k in ("conf", "hook")
            if (m := re.search(rf"^sha_{k}=([0-9a-f]{{64}})$", texto, re.M))}


APT_COMMANDS = {
    "upgrade": ["apt-get", "-s", "-o", "Debug::NoLocking=1", "upgrade"],
    "remove": ["apt-get", "-s", "-o", "Debug::NoLocking=1", "remove", "nvidia-system-station"],
}
CRITICAL_PACKAGES = criticos()  # la misma lista que lleva el hook
GUARD_ROWS = ("config", "autoremove_simulado", "remove_critico", "remove_inocuo")
OEM_BLOCKER = "OEM coverage unverified: other OEM bundles' metapackage graphs are not observable from this host"
GUARD_BLOCKER = "installed APT guard unverified"


def _unknown(reason: str, could_not_run: int = 1) -> dict[str, Any]:
    return {"status": "unknown", "findings": [reason], "fail": 0,
            "could_not_run": could_not_run}


def _load(directory: Path) -> tuple[dict[str, Any], str] | str:
    try:
        path = directory / "apt-captures.json"
        raw = path.read_bytes()
        captures = json.loads(raw)
        expected_hash = (directory / "apt-captures.sha256").read_text(encoding="ascii").strip()
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return f"evidence unreadable: {exc}"
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        return "captured APT evidence hash mismatch"
    if not isinstance(captures, dict) or not isinstance(captures.get("commands"), list):
        return "captured APT commands missing or malformed"
    return captures, expected_hash


def _classify_capture(row: dict[str, Any], label: str) -> tuple[str, dict[str, Any] | str]:
    if type(row.get("exit_code")) is not int or not isinstance(row.get("stdout"), str) or not isinstance(row.get("stderr"), str):
        return "unknown", f"{label} exit/output malformed"
    if row["exit_code"] != 0:
        return "unknown", f"{label} simulation exit={row['exit_code']}"
    if row["stderr"]:
        return "unknown", f"{label} simulation wrote to stderr"
    outcome = check_apt({"plan": row["stdout"], "critical_packages": CRITICAL_PACKAGES,
                         "exit_code": row["exit_code"], "stderr": row["stderr"]})
    return outcome["status"], outcome


def _guard_reasons(cap: dict[str, Any]) -> list[str]:
    """Why a well-formed guard capture does NOT prove an installed, working guard (empty = it does)."""
    rows = {row["nombre"]: row for row in cap["commands"]}
    critico, inocuo = rows["remove_critico"], rows["remove_inocuo"]
    expected = hashes_esperados()
    checks = [
        (cap.get("instalado") is True, "capture is pre-deployment (instalado is not true)"),
        (cap.get("conf") == CONF_INSTALADO and cap.get("hook") == HOOK_INSTALADO,
         "capture did not read the installed paths"),
        (cap.get("conf_sha256") == expected.get("conf") and cap.get("hook_sha256") == expected.get("hook"),
         "installed files differ from the sealed script's sha256"),
        (rows["config"]["exit_code"] == 0 and LINEA_HOOK in rows["config"]["stdout"].splitlines(),
         "the real APT configuration does not register the hook"),
        (rows["autoremove_simulado"]["exit_code"] == 0, "apt-get -s autoremove fails with the real configuration"),
        (cap.get("critico") in CRITICAL_PACKAGES and critico["argv"][-1] == cap.get("critico"),
         "the refused transaction does not remove a listed critical package"),
        (critico["exit_code"] != 0 and MENSAJE_BLOQUEO in critico["stderr"]
         and "--remove" not in critico["dpkg_log"], "the critical removal was not aborted by the guard before dpkg"),
        (cap.get("inocuo") not in CRITICAL_PACKAGES and inocuo["argv"][-1] == cap.get("inocuo"),
         "the innocuous transaction names a critical package"),
        (inocuo["exit_code"] == 0 and f"--remove {cap.get('inocuo')}" in inocuo["dpkg_log"],
         "the innocuous removal did not reach dpkg"),
    ]
    return [reason for ok, reason in checks if not ok]


def _guard(directory: Path) -> tuple[str, list[str]] | str:
    """('verified'|'absent'|'rejected', reasons), or a string when the capture exists but cannot be read."""
    path = directory / CAPTURA
    if not path.exists():
        return "absent", [f"{CAPTURA} absent; after deployment run "
                          "python3 tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD/collect_guard.py --instalado --out <this directory>"]
    try:
        raw = path.read_bytes()
        cap = json.loads(raw)
        expected_hash = (directory / "apt-guard-captures.sha256").read_text(encoding="ascii").strip()
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return f"guard evidence unreadable: {exc}"
    if hashlib.sha256(raw).hexdigest() != expected_hash:
        return "guard evidence hash mismatch"
    rows = cap.get("commands") if isinstance(cap, dict) else None
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        return "guard evidence commands missing or malformed"
    names = [r.get("nombre") for r in rows]
    if any(names.count(n) != 1 for n in GUARD_ROWS):
        return "guard evidence must hold exactly one row per guard check"
    for row in rows:
        name = row.get("nombre")
        if name in GUARD_ROWS and not (
                type(row.get("exit_code")) is int and isinstance(row.get("argv"), list) and row["argv"]
                and all(isinstance(row.get(k), str) for k in ("stdout", "stderr"))
                and (name not in ("remove_critico", "remove_inocuo") or isinstance(row.get("dpkg_log"), str))):
            return f"guard evidence row {name} malformed"
    reasons = _guard_reasons(cap)
    if not reasons:
        return "verified", []
    return ("rejected" if cap.get("instalado") is True else "pre_deployment"), reasons


def verify(directory: Path) -> dict[str, Any]:
    """Classify captured real benign and dangerous simulations plus parser controls."""
    evidence = _load(directory)
    if isinstance(evidence, str):
        return _unknown(evidence)
    captures, digest = evidence
    if len(captures["commands"]) != len(APT_COMMANDS) or any(
            not isinstance(row, dict) for row in captures["commands"]):
        return _unknown("APT capture must contain exactly two well-formed command records")
    by_name: dict[str, list[Any]] = {name: [] for name in APT_COMMANDS}
    for row in captures["commands"]:
        if isinstance(row, dict) and isinstance(row.get("argv"), list):
            for name, argv in APT_COMMANDS.items():
                if row["argv"] == argv:
                    by_name[name].append(row)
    if any(len(rows) != 1 for rows in by_name.values()):
        return _unknown("expected exactly one raw upgrade and one raw critical remove capture")
    benign, benign_result = _classify_capture(by_name["upgrade"][0], "upgrade")
    dangerous, dangerous_result = _classify_capture(by_name["remove"][0], "remove")
    if benign == "unknown" or dangerous == "unknown":
        return _unknown(str(benign_result if benign == "unknown" else dangerous_result))
    if benign != "pass" or dangerous != "block":
        return {"status": "fail", "findings": [f"real capture classifications: upgrade={benign}, remove={dangerous}"],
                "fail": 1, "could_not_run": 0}
    return _pass(directory, digest)


def _pass(directory: Path, digest: str) -> dict[str, Any]:
    """The instrument discriminates; add the installed-guard verdict and the blockers that keep the card open."""
    guard = _guard(directory)
    if isinstance(guard, str):
        return _unknown(guard)
    guard_state, guard_reasons = guard
    blockers = [OEM_BLOCKER]
    if guard_state != "verified":
        blockers.append(f"{GUARD_BLOCKER}: " + "; ".join(guard_reasons))
    return {
        "status": "pass",
        "findings": [],
        "fail": 0,
        "could_not_run": 0,
        "evidence_sha256": digest,
        "checks": {"captured_upgrade": "pass", "captured_critical_removal": "block", "installed_guard": guard_state},
        "closure": "open",
        "open_blockers": blockers,
        "meaning": ("instrument discriminates these host simulations; installed_guard says whether a deployed "
                    "bb-apt-guardia aborted a real critical removal before dpkg; OEM coverage stays unverified"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True, help="captured evidence directory")
    parser.add_argument("--cierre", action="store_true", help="exit 0 solo si la ficha es cerrable: un pass con `closure: open` (bloqueos abiertos) sale 2")
    args = parser.parse_args(argv)
    result = verify(args.evidence)
    print(json.dumps(result, sort_keys=True))
    if args.cierre and result["status"] == "pass" and result.get("closure") == "open":
        return 2
    return 0 if result["status"] == "pass" else 1 if result["status"] == "fail" else 2


if __name__ == "__main__":
    sys.exit(main())
