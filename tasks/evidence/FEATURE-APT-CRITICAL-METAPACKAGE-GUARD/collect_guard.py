"""Prueba bb-apt-guardia con APT real sobre una caja: estado copiado y dpkg sustituido.

`apt-get -s` no ejecuta los hooks `DPkg::Pre-Install-Pkgs`, asi que simular no prueba la
guardia. Aqui APT corre una transaccion de verdad (`-y remove`) con:
- `APT_CONFIG` apuntando a una configuracion que solo lee el fichero de la guardia (ningun
  otro hook del sistema corre), comprobado con `apt-config` antes de transaccionar;
- `Dir::State::status`, `Dir::State`, `Dir::Cache` y `Dir::Log` en la caja (copia de
  /var/lib/dpkg/status), y `Dir::Bin::dpkg` = un stub que solo anota sus argumentos.
Asi el veredicto sale de APT invocando el hook, y dpkg real nunca corre. Sin root.

`--instalado` usa /etc/apt/apt.conf.d/00-bb-apt-guardia y el hook que nombra (lo desplegado);
sin la bandera usa los ficheros de adopted/pendiente-de-despliegue/ (prueba previa al
despliegue: no es evidencia de guardia instalada). Escribe `apt-guard-captures.json` y su
`.sha256` en `--out`; los lee `tools.verify_apt_critical_removals`.
Uso, desde la raiz del repo: python3 tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD/collect_guard.py [--instalado] --out <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from tools.verify_apt_critical_removals import (CAPTURA, CONF_INSTALADO, CONF_REPO, CRITICO, HOOK_INSTALADO,
                                                HOOK_REPO, INOCUO, criticos)


STUB_DPKG = """#!/bin/sh
for a in "$@"; do
  case "$a" in --print-foreign-architectures|--print-architecture) exec /usr/bin/dpkg "$a";; esac
done
echo "$*" >> "$(dirname "$0")/dpkg.log"
exit 0
"""


def sha(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _correr(argv: list[str], env: dict[str, str] | None = None) -> dict[str, Any]:
    r = subprocess.run(argv, capture_output=True, text=True, timeout=300,
                       env=(os.environ | {"LC_ALL": "C"}) | (env or {}))
    return {"argv": argv, "exit_code": r.returncode, "stdout": r.stdout, "stderr": r.stderr}


def _caja(dir_: Path, conf_texto: str) -> tuple[list[str], dict[str, str]]:
    for sub in ("parts", "state", "cache/archives/partial", "log", "dpkg"):
        (dir_ / sub).mkdir(parents=True)
    shutil.copy("/var/lib/dpkg/status", dir_ / "dpkg" / "status")
    (dir_ / "parts" / "00-bb-apt-guardia").write_text(conf_texto, encoding="utf-8")
    stub = dir_ / "stub-dpkg"
    stub.write_text(STUB_DPKG, encoding="utf-8")
    stub.chmod(0o755)
    (dir_ / "apt.conf").write_text(f'Dir::Etc::main "/dev/null";\nDir::Etc::parts "{dir_}/parts";\n',
                                   encoding="utf-8")
    opciones = ["-o", "Debug::NoLocking=1", "-o", f"Dir::State={dir_}/state",
                "-o", "Dir::State::lists=/var/lib/apt/lists", "-o", f"Dir::State::status={dir_}/dpkg/status",
                "-o", f"Dir::Cache={dir_}/cache", "-o", f"Dir::Log={dir_}/log", "-o", f"Dir::Bin::dpkg={stub}"]
    return opciones, {"APT_CONFIG": str(dir_ / "apt.conf")}


def transaccion(conf_texto: str, accion: list[str]) -> dict[str, Any]:
    """`apt-get -y <accion>` real sobre una caja; dpkg es el stub. Incluye lo que el stub recibio."""
    with tempfile.TemporaryDirectory(prefix="bb-apt-guardia.") as d:
        caja = Path(d)
        opciones, env = _caja(caja, conf_texto)
        stub = str(caja / "stub-dpkg")
        comprobacion = _correr(["apt-config", *opciones, "shell", "P", "Dir::Etc::parts/", "B", "Dir::Bin::dpkg"], env)
        esperado = f"P='{caja}/parts/'\nB='{stub}'\n"
        if comprobacion["exit_code"] != 0 or comprobacion["stdout"] != esperado:
            return comprobacion | {"error": "la caja no aisla la configuracion; no se transacciona", "dpkg_log": ""}
        fila = _correr(["apt-get", *opciones, "-y", *accion], env)
        log = caja / "dpkg.log"
        fila["dpkg_log"] = log.read_text(encoding="utf-8") if log.exists() else ""
        fila["argv"] = ["apt-get", "<caja>", "-y", *accion]
        return fila


def capturar(instalado: bool) -> dict[str, Any]:
    if instalado:
        conf, hook = Path(CONF_INSTALADO), Path(HOOK_INSTALADO)
        conf_texto = conf.read_text(encoding="utf-8")
    else:
        conf, hook = CONF_REPO, HOOK_REPO
        conf_texto = CONF_REPO.read_text(encoding="utf-8").replace(HOOK_INSTALADO, str(HOOK_REPO))
    filas = {
        "criticos_instalados": _correr(["dpkg-query", "-W", "--showformat=${Package} ${Status}\\n", *criticos()]),
        "config": _correr(["apt-config", "dump", "DPkg::Pre-Install-Pkgs"]),
        "autoremove_simulado": _correr(["apt-get", "-s", "-o", "Debug::NoLocking=1", "autoremove"]),
        "remove_critico": transaccion(conf_texto, ["remove", CRITICO]),
        "remove_inocuo": transaccion(conf_texto, ["remove", INOCUO]),
    }
    return {"instalado": instalado, "conf": str(conf), "hook": str(hook),
            "conf_sha256": sha(conf), "hook_sha256": sha(hook), "critico": CRITICO, "inocuo": INOCUO,
            "commands": [{"nombre": k} | v for k, v in filas.items()]}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--instalado", action="store_true", help="probar lo desplegado en /etc y /usr/local/sbin")
    p.add_argument("--out", type=Path, required=True, help="directorio de evidencia")
    a = p.parse_args(argv)
    try:
        captura = capturar(a.instalado)
    except OSError as e:
        print(f"[apt-guardia] COULD_NOT_RUN: {e}", file=sys.stderr)
        return 2
    raw = (json.dumps(captura, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode()
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / CAPTURA).write_bytes(raw)
    (a.out / (CAPTURA.removesuffix(".json") + ".sha256")).write_text(hashlib.sha256(raw).hexdigest() + "\n",
                                                                     encoding="ascii")
    for fila in captura["commands"]:
        print(f"{fila['nombre']}: rc={fila['exit_code']} dpkg_remove={'--remove' in fila.get('dpkg_log', '')}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
