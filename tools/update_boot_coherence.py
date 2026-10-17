"""Read-only update/boot coherence: pre-reboot kernel gate from raw rows, its incident negatives,
and the reboot-recovery trial that closes FORUM-00-KERNEL-INITRD-UPDATE-GATE.

Nothing here changes the host: the capture runs `dpkg --audit`, `apt-get -s check` (simulation, no
lock), `stat`, `mokutil --sb-state` and `modinfo`. The snapshot that `tools.preflight.check_kernel`
judges is DERIVED from the literal rows, so a recorded snapshot cannot assert what the rows lack.
The incident negatives are mutations of the real rows (initrd empty, dpkg half-configured, unsigned
module under Secure Boot...): if the gate does not block one of them, the instrument is blind and
the verdict is `fail`, never `pass`. A bootable recovery is only proven by `recovery-trial.json`,
captured across real reboots; without it the verdict stays `unknown` (could_not_run).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from tools import preflight
from tools.capture_io import read_regular_bytes, strict_json_loads

FINDING = "FORUM-00-KERNEL-INITRD-UPDATE-GATE"
TRIAL_FILE = "recovery-trial.json"
TRIAL_PHASES = ("antes", "recuperacion", "restaurado")
Row = dict[str, Any]
Correr = Callable[..., Any]


def comandos_kernel(objetivo: str, actual: str) -> list[list[str]]:
    """The literal read-only probes of the pre-reboot gate for `objetivo` (previous = `actual`)."""
    return [
        ["uname", "-r"],
        ["dpkg", "--audit"],
        ["apt-get", "-s", "check"],
        ["stat", "-c", "%n %s", f"/boot/vmlinuz-{objetivo}", f"/boot/initrd.img-{objetivo}",
         f"/boot/vmlinuz-{actual}", f"/boot/initrd.img-{actual}"],
        ["mokutil", "--sb-state"],
        ["modinfo", "-k", objetivo, "-F", "signer", "nvidia"],
        ["modinfo", "-k", objetivo, "-F", "vermagic", "nvidia"],
    ]


def _argv(row: Row) -> list[str]:
    argv = row.get("argv")
    return argv if isinstance(argv, list) else str(argv).split()


def _fila(rows: list[Row], *prefijo: str) -> Row | None:
    return next((r for r in rows if _argv(r)[:len(prefijo)] == list(prefijo)), None)


def _tamanos(rows: list[Row]) -> dict[str, int]:
    fila = _fila(rows, "stat")
    tamanos: dict[str, int] = {}
    for linea in (fila or {}).get("stdout", "").splitlines():
        partes = linea.rsplit(" ", 1)
        if len(partes) == 2 and partes[1].isdigit():
            tamanos[partes[0]] = int(partes[1])
    return tamanos


def _modulo_listo(rows: list[Row], objetivo: str) -> bool | None:
    firma = _fila(rows, "modinfo", "-k", objetivo, "-F", "signer")
    magia = _fila(rows, "modinfo", "-k", objetivo, "-F", "vermagic")
    sb = _fila(rows, "mokutil", "--sb-state")
    if firma is None or magia is None:
        return None
    if magia["rc"] != 0 or not magia["stdout"].startswith(objetivo + " "):
        return False  # module absent for the target kernel, or built for another one
    if firma["rc"] == 0 and firma["stdout"].strip():
        return True
    if sb is None or sb["rc"] != 0:
        return None  # unsigned module and Secure Boot state unreadable: cannot judge
    return "SecureBoot disabled" in sb["stdout"]


def snapshot_kernel(rows: list[Row], objetivo: str) -> dict[str, bool | None]:
    """Derive the `preflight.check_kernel` snapshot from literal rows; None = could not observe."""
    uname, audit, apt = _fila(rows, "uname", "-r"), _fila(rows, "dpkg", "--audit"), _fila(rows, "apt-get")
    actual = uname["stdout"].strip() if uname and uname["rc"] == 0 else ""
    tam = _tamanos(rows) if _fila(rows, "stat") else None

    def presente(ruta: str) -> bool | None:
        return None if tam is None else tam.get(ruta, 0) > 0

    apt_roto = apt is not None and re.search(r"(?m)^E:", apt["stdout"] + apt["stderr"]) is not None
    return {
        "dpkg_clean": None if audit is None or audit["rc"] != 0 else not audit["stdout"].strip(),
        "apt_check": None if apt is None else apt["rc"] == 0 and not apt_roto,
        "vmlinuz_present": presente(f"/boot/vmlinuz-{objetivo}"),
        "initrd_present": presente(f"/boot/initrd.img-{objetivo}"),
        "module_ready": _modulo_listo(rows, objetivo),
        "previous_kernel_bootable": None if not actual or tam is None else (
            actual != objetivo and bool(presente(f"/boot/vmlinuz-{actual}"))
            and bool(presente(f"/boot/initrd.img-{actual}"))),
    }


def _cambia(rows: list[Row], prefijo: tuple[str, ...], **cambios: Any) -> list[Row]:
    return [{**r, **cambios} if _argv(r)[:len(prefijo)] == list(prefijo) else r for r in rows]


def negativos_kernel(rows: list[Row], objetivo: str) -> dict[str, tuple[list[Row], str]]:
    """Incident states built by mutating the real rows; each one MUST block with its label."""
    stat = _fila(rows, "stat") or {"stdout": ""}
    vmlinuz, initrd = f"/boot/vmlinuz-{objetivo}", f"/boot/initrd.img-{objetivo}"
    sin_vmlinuz = "".join(l + "\n" for l in stat["stdout"].splitlines() if not l.startswith(vmlinuz + " "))
    initrd_vacio = re.sub(rf"(?m)^{re.escape(initrd)} \d+$", f"{initrd} 0", stat["stdout"])
    return {
        "dpkg a medio configurar": (_cambia(rows, ("dpkg", "--audit"), stdout=(
            "The following packages have been unpacked but not yet configured:\n nvidia-dkms-580-open\n")),
            "dpkg audit reports incomplete packages"),
        "dependencias rotas": (_cambia(rows, ("apt-get",), rc=100, stderr="E: Unmet dependencies.\n"),
                               "APT dependency check failed"),
        "vmlinuz ausente": (_cambia(rows, ("stat",), rc=1, stdout=sin_vmlinuz), "target vmlinuz missing"),
        "initrd vacio": (_cambia(rows, ("stat",), stdout=initrd_vacio), "target initrd missing or empty"),
        "modulo sin firmar con Secure Boot": (
            _cambia(_cambia(rows, ("modinfo", "-k", objetivo, "-F", "signer"), stdout=""),
                    ("mokutil",), rc=0, stdout="SecureBoot enabled\n"),
            "target GPU module is unavailable or unsigned"),
        "modulo de otro kernel": (_cambia(rows, ("modinfo", "-k", objetivo, "-F", "vermagic"),
                                          stdout="0.0.0-otro SMP mod_unload aarch64\n"),
                                  "target GPU module is unavailable or unsigned"),
        "sin kernel previo": (_cambia(rows, ("uname", "-r"), stdout=objetivo + "\n"),
                              "previous kernel recovery is unverified"),
    }


def evaluar_negativos(rows: list[Row], objetivo: str) -> tuple[str, str] | None:
    """None if every incident negative blocks with its own label; otherwise a `fail` verdict."""
    for nombre, (mutadas, etiqueta) in negativos_kernel(rows, objetivo).items():
        juicio = preflight.check_kernel(snapshot_kernel(mutadas, objetivo))
        if juicio["status"] != "block" or etiqueta not in juicio["findings"]:
            return ("fail", f"gate is blind to incident negative '{nombre}': {juicio}")
    return None


def _boot_kernel(rows: list[Row], fase: str) -> tuple[str, str] | None:
    boot = next((r for r in rows if r.get("phase") == fase and _argv(r)[-1:] == ["/proc/sys/kernel/random/boot_id"]), None)
    uname = next((r for r in rows if r.get("phase") == fase and _argv(r)[:2] == ["uname", "-r"]), None)
    if boot is None or uname is None or boot["rc"] != 0 or uname["rc"] != 0:
        return None
    ident, kernel = boot["stdout"].strip(), uname["stdout"].strip()
    return (ident, kernel) if re.fullmatch(r"[0-9a-f-]{36}", ident) and kernel else None


def evaluar_recuperacion(rows: list[Row], previo: str) -> tuple[str, str]:
    """Bootable recovery: a manual boot into another kernel, then rollback to `previo`, 3 real boots."""
    fases = {fase: _boot_kernel(rows, fase) for fase in TRIAL_PHASES}
    faltan = [fase for fase, valor in fases.items() if valor is None]
    if faltan:
        return "unknown", f"recovery trial lacks boot_id/uname for phases {faltan}"
    antes, recuperacion, restaurado = (fases[f] for f in TRIAL_PHASES)
    assert antes is not None and recuperacion is not None and restaurado is not None
    if len({antes[0], recuperacion[0], restaurado[0]}) != 3:
        return "fail", "recovery trial phases share a boot_id: no reboot was observed"
    if antes[1] != previo or restaurado[1] != previo:
        return "fail", f"trial does not start and roll back on the gate's previous kernel {previo}"
    if recuperacion[1] == previo:
        return "fail", "recovery boot ran the default kernel: no alternate kernel was selected"
    return "pass", (f"recovery boot into {recuperacion[1]} and rollback to {previo} observed across "
                    "three distinct boot_ids")


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
    """Full close verdict for the kernel gate: raw-derived snapshot, negatives, recovery trial."""
    objetivo = documento.get("target_kernel")
    if not isinstance(objetivo, str) or not objetivo:
        return "unknown", "preflight lacks target_kernel: snapshot cannot be re-derived from raw rows"
    derivado = snapshot_kernel(rows, objetivo)
    if derivado != documento.get("snapshot"):
        return "fail", f"recorded snapshot differs from the one derived from raw rows: {derivado}"
    ciego = evaluar_negativos(rows, objetivo)
    if ciego:
        return ciego
    uname = _fila(rows, "uname", "-r")
    previo = uname["stdout"].strip() if uname else ""
    prueba = leer_prueba(directorio)
    if prueba is None:
        return "unknown", (f"pre-reboot gate and its {len(negativos_kernel(rows, objetivo))} incident negatives "
                           f"pass; bootable recovery unproven: {TRIAL_FILE} (boot into another kernel and "
                           f"roll back to {previo}) is missing")
    return evaluar_recuperacion(prueba, previo)


def _sin_host(texto: str) -> str:
    host = socket.gethostname()
    return texto.replace(host, "<host>") if host else texto


def capturar(comandos: list[list[str]], correr: Correr = subprocess.run, fase: str | None = None) -> list[dict[str, Any]]:
    filas = []
    env = {**os.environ, "LC_ALL": "C"}
    for argv in comandos:
        try:
            r = correr(argv, capture_output=True, text=True, timeout=60, env=env)
            fila: dict[str, Any] = {"argv": argv, "exit_code": r.returncode,
                                    "stdout": _sin_host(r.stdout), "stderr": _sin_host(r.stderr)}
        except (OSError, subprocess.TimeoutExpired) as exc:
            fila = {"argv": argv, "exit_code": 127, "stdout": "", "stderr": f"could_not_run: {exc}"}
        if fase:
            fila["phase"] = fase
        filas.append(fila)
    return filas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="modo", required=True)
    gate = sub.add_parser("kernel", help="capture the read-only pre-reboot gate into DIR")
    gate.add_argument("--target", required=True)
    gate.add_argument("--out", type=Path, required=True)
    trial = sub.add_parser("trial", help="append one recovery-trial phase (boot_id + uname) into DIR")
    trial.add_argument("--phase", choices=TRIAL_PHASES, required=True)
    trial.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    if args.modo == "trial":
        ruta = args.out / TRIAL_FILE
        doc = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {"id": FINDING, "commands": []}
        doc["commands"] = [r for r in doc["commands"] if r.get("phase") != args.phase]
        doc["commands"] += capturar([["cat", "/proc/sys/kernel/random/boot_id"], ["uname", "-r"]], fase=args.phase)
        ruta.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(doc["commands"][-2:], ensure_ascii=False))
        return 0
    actual = subprocess.run(["uname", "-r"], capture_output=True, text=True, check=False).stdout.strip()
    filas = capturar(comandos_kernel(args.target, actual))
    rows = [_normaliza(f) for f in filas]
    snapshot = snapshot_kernel(rows, args.target)
    resultado = preflight.check_kernel(snapshot)
    (args.out / "commands.json").write_text(json.dumps(
        {"id": FINDING, "commands": filas}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.out / "preflight.json").write_text(json.dumps(
        {"id": FINDING, "kind": "kernel", "target_kernel": args.target, "read_only": True,
         "snapshot": snapshot, "preflight_result": resultado}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(resultado, sort_keys=True))
    return 0 if resultado["status"] == "pass" else 2


if __name__ == "__main__":
    sys.exit(main())
