#!/usr/bin/env python3
"""close_check reutilizable para fichas HARVEST-*.md (sugerencias de cosecha
de Atlas, ver satd_family: HARVEST_SUGGESTION).

Estas fichas no tienen un fix de código que probar -- lo único verificable
por máquina es que la DECISIÓN quedó registrada: `accepted.by/date/trigger`
llenos y `date` en ISO-8601, no el placeholder "(pendiente)" que Atlas deja
al crearlas. Sin esto, las 11 fichas originales traían `close_check: {"cmd":
"true", ...}` -- prohibido por backlog_verifier.PROHIBITED_COMMANDS como
no-op, y bloqueaba el push (medido 2026-09-09: contract_breaches=11).
"""

import re
import sys
from pathlib import Path

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLACEHOLDER = "(pendiente)"


def check(task_path: Path) -> tuple[bool, str]:
    if not task_path.is_file():
        return False, f"no existe: {task_path}"
    text = task_path.read_text(encoding="utf-8")
    m = re.search(r"^accepted:\s*(\{.*\})\s*$", text, re.MULTILINE)
    if not m:
        return False, "sin campo accepted en el frontmatter"

    import yaml
    acc = yaml.safe_load(m.group(1))
    if not isinstance(acc, dict):
        return False, "accepted no es un objeto"

    for field in ("by", "date", "trigger"):
        val = str(acc.get(field) or "").strip()
        if not val or val == PLACEHOLDER:
            return False, f"accepted.{field} sigue en placeholder o vacío: {val!r}"

    if not DATE_RE.match(acc["date"]):
        return False, f"accepted.date no es ISO-8601: {acc['date']!r}"

    return True, "accepted completo"


def main():
    if len(sys.argv) != 2:
        print("uso: check_harvest_accepted.py <ruta-a-la-ficha.md>", file=sys.stderr)
        sys.exit(2)
    ok, reason = check(Path(sys.argv[1]))
    print(reason)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":  # pragma: no cover -- entry point, ejercitado via main()
    main()
