#!/usr/bin/env python3
"""Comprueba que el gate rechaza un tool nuevo ausente del inventario funcional."""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = Path.home() / "scratch/blackbox/2026-11-21-captura-observacion"
BASE.mkdir(parents=True, exist_ok=True)

with tempfile.TemporaryDirectory(prefix="inventory-negative-", dir=BASE) as temp:
    subject = Path(temp)
    (subject / "bin").mkdir()
    (subject / "tools").mkdir()
    (subject / "adopted").mkdir()
    (subject / "bin/bb").write_text("cmd_demo() { :; }\n", encoding="utf-8")
    (subject / "tools/demo.py").write_text("pass\n", encoding="utf-8")
    (subject / "SPEC.md").write_text(
        "## Inventario de funciones\n\n| pieza | hace | prueba |\n| --- | --- | --- |\n"
        "| `bb demo` | demo | prueba |\n\n## Inventario de propiedad\n\n"
        "| destino | motivo |\n| --- | --- |\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        ["python3", "-I", str(ROOT / "tools/inventario.py"), "--root", str(subject), "--check"],
        text=True, capture_output=True, check=False,
    )
    print(result.stdout, end="")
    if result.returncode != 1 or "funcion sin inventariar en SPEC.md: tools/demo.py" not in result.stdout:
        print("[negative-control] FAIL: el gate no detectó la herramienta omitida")
        raise SystemExit(1)
    print("[negative-control] PASS: el gate bloqueó la herramienta omitida")
