"""Que escribe y que ejecuta APT en la caja de collect_guard.py (este directorio), medido con strace (sin root).

Corre `apt-get <caja> -y remove nvidia-system-station` y `... remove tree` con el hook del repo y lista cada
escritura con exito (openat con O_WRONLY/O_RDWR/O_CREAT, rename*, unlink*, mkdir*) fuera de la caja, y cada
invocacion del dpkg real. Control negativo: el mismo filtro sobre `touch <fichero fuera>` debe contar 1.
Uso, desde la raiz del repo: python3 tasks/evidence/FEATURE-APT-CRITICAL-METAPACKAGE-GUARD/strace_caja.py
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
import collect_guard as ag  # el colector de este directorio (la caja, el stub y las constantes)

SYSCALLS = "trace=openat,rename,renameat,renameat2,unlink,unlinkat,mkdir,mkdirat,execve"
ESCRITURA = re.compile(r"openat\(.*O_(?:WRONLY|RDWR|CREAT)|rename(?:at2?)?\(|unlink(?:at)?\(|mkdir(?:at)?\(")
TMPFILE = 'openat(AT_FDCWD, "/tmp", O_RDWR|O_EXCL|O_CLOEXEC|O_TMPFILE'


def trazar(argv: list[str], traza: Path, env: dict[str, str]) -> tuple[int, list[str]]:
    r = subprocess.run(["strace", "-f", "-qq", "-o", str(traza), "-e", SYSCALLS, *argv], env=env,
                       capture_output=True, text=True)
    lineas = [x for x in traza.read_text(encoding="utf-8").splitlines() if "= -1" not in x]
    traza.unlink()
    return r.returncode, lineas


def main() -> int:
    conf = ag.CONF_REPO.read_text(encoding="utf-8").replace(ag.HOOK_INSTALADO, str(ag.HOOK_REPO))
    for accion in (["remove", ag.CRITICO], ["remove", ag.INOCUO]):
        with tempfile.TemporaryDirectory(prefix="bb-apt-guardia.") as d:
            caja = Path(d)
            opciones, env = ag._caja(caja, conf)
            rc, lineas = trazar(["apt-get", *opciones, "-y", *accion], caja.parent / f"traza-{os.getpid()}.txt",
                                os.environ | {"LC_ALL": "C"} | env)
            escrituras = [x for x in lineas if ESCRITURA.search(x)]
            fuera = [x for x in escrituras if str(caja) not in x and "/dev/" not in x]
            otras = [x for x in fuera if TMPFILE not in x]
            dpkg = sorted({re.sub(r"^\d+ ", "", x).split(", 0x")[0] for x in lineas if 'execve("/usr/bin/dpkg"' in x})
            execs = sorted({m.group(1) for x in lineas if (m := re.search(r'execve\("([^"]+)"', x))})
            print(f"== apt-get <caja> -y {' '.join(accion)}: rc={rc}")
            print(f"   escrituras con exito: {len(escrituras)}; fuera de la caja y de /dev: {len(fuera)} "
                  f"({len(fuera) - len(otras)} O_TMPFILE anonimos en /tmp, otras: {len(otras)})")
            for x in otras:
                print("   FUERA:", x[:200])
            print("   dpkg real invocado como:", dpkg)
            print("   programas ejecutados:", ", ".join(
                e.replace(str(caja), "<caja>").replace(str(ROOT), "<repo>") for e in execs))
    with tempfile.TemporaryDirectory() as d:
        _, lineas = trazar(["touch", f"{d}/fuera.txt"], Path(d) / "traza.txt", dict(os.environ))
        n = len([x for x in lineas if ESCRITURA.search(x) and "fuera.txt" in x])
        print(f"== control negativo: touch <fuera>: escrituras fuera detectadas por el mismo filtro: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
