# Evidencia de cierre

Base `c3e3e23b`, 2026-11-21. Alcance de ejecución: `IDEA-TABULAR-BLOQUEADORES-Y-BOLETA-DE-DESBLOQUEO`. La clasificación se hizo mediante lectura individual de las 85 fichas iniciales, incluidas la de este lote y las 84 que siguen abiertas. Las referencias de estado de la máquina se leyeron del repositorio.

## Close check

Comando de la ficha, antes y después de escribir el documento y mover la ficha.

```sh
test -s docs/BLOQUEADORES-DEL-BACKLOG.md
rc=$?
printf 'exit=%s\n' "$rc"
exit "$rc"
```

Antes, stdout y stderr vacíos, salvo el código impreso por el envoltorio.

```text
exit=1
```

Después, stdout y stderr vacíos, salvo el código impreso por el envoltorio.

```text
exit=0
```

## Cobertura por ID

Se compara el ID y estado del frontmatter de cada ficha en `tasks/backlog` con la fila y su enlace en el documento. Desde la raíz del repo, con `run_dir` apuntando a un directorio temporal propio bajo `~/scratch/blackbox/`:

```sh
cat > "$run_dir/cobertura.py" <<'PY'
from collections import Counter
from pathlib import Path
import re
import sys

document = Path(sys.argv[1])
backlog = Path("tasks/backlog")
files = sorted(backlog.glob("*.md"))
if len(sys.argv) == 3:
    files.remove(backlog / (sys.argv[2] + ".md"))
expected = set()
invalid_fiches = []
for file in files:
    frontmatter = file.read_text(encoding="utf-8").split("\n---\n", 1)[0]
    fields = dict(re.findall(r"^(id|status): (.+)$", frontmatter, re.M))
    if fields != {"id": file.stem, "status": "open"}:
        invalid_fiches.append(file.name)
    expected.add(file.stem)

rows = {}
duplicates = set()
invalid_rows = []
for line in document.read_text(encoding="utf-8").splitlines():
    if not line.startswith("| ["):
        continue
    columns = [cell.strip() for cell in line.strip("|").split("|")]
    link = re.fullmatch(r"\[([A-Z0-9-]+)\]\(\.\./tasks/backlog/\1\.md\)", columns[0])
    if len(columns) != 5 or not link or not all(columns):
        invalid_rows.append(line)
        continue
    item = link[1]
    if item in rows:
        duplicates.add(item)
    kind = columns[3].split()[0].rstrip(".,:")
    if kind not in {"No", "Observado", "Condicional", "Sí", "Apagado"}:
        invalid_rows.append(line)
    rows[item] = kind

missing = sorted(expected - rows.keys())
extra = sorted(rows.keys() - expected)
restart = Counter(rows.values())
print(f"backlog={len(files)} filas={len(rows)} faltantes={len(missing)} sobrantes={len(extra)} "
      f"duplicados={len(duplicates)} fichas_invalidas={len(invalid_fiches)} filas_invalidas={len(invalid_rows)}")
print("reinicio:", ", ".join(f"{kind}={restart[kind]}" for kind in ("No", "Observado", "Condicional", "Sí", "Apagado")))
for label, errors in (("falta", missing), ("sobra", extra), ("duplicado", sorted(duplicates)),
                      ("ficha inválida", invalid_fiches), ("fila inválida", invalid_rows)):
    for error in errors:
        print(f"{label}: {error}")
sys.exit(int(bool(missing or extra or duplicates or invalid_fiches or invalid_rows)))
PY

doc=docs/BLOQUEADORES-DEL-BACKLOG.md
python3 "$run_dir/cobertura.py" "$doc"
printf 'exit=%s\n' "$?"

cp "$doc" "$run_dir/sin-una-fila.md"
sed -i '/^| \[DEBT-NETCONSOLE-ARRANQUE-SIN-PRUEBA-DE-ARRANQUE-01\]/d' "$run_dir/sin-una-fila.md"
python3 "$run_dir/cobertura.py" "$run_dir/sin-una-fila.md"
printf 'exit=%s\n' "$?"
```

Árbol tras mover la ficha.

```text
backlog=84 filas=84 faltantes=0 sobrantes=0 duplicados=0 fichas_invalidas=0 filas_invalidas=0
reinicio: No=50, Observado=15, Condicional=7, Sí=11, Apagado=1
exit=0
```

Copia temporal con una fila eliminada.

```text
backlog=84 filas=83 faltantes=1 sobrantes=0 duplicados=0 fichas_invalidas=0 filas_invalidas=0
reinicio: No=50, Observado=14, Condicional=7, Sí=11, Apagado=1
falta: DEBT-NETCONSOLE-ARRANQUE-SIN-PRUEBA-DE-ARRANQUE-01
exit=1
```

## Inventario de documentación

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider --basetemp "$run_dir/pytest-docs-final" tests/test_inventario.py
python3 -m tools.inventario --check
printf 'exit=%s\n' "$?"
```

```text
.......................                                                  [100%]
23 passed in 0.08s
[inventario] HALLAZGOS: 0
[inventario] OK: los dos inventarios describen el repo y la maquina.
exit=0
```

La suite incluye `test_main_sale_1_con_sujeto_mutado`, que añade un comando ausente del inventario y exige salida 1 y hallazgo por nombre.

## Escáner de deuda

```sh
env -u DEBT_NO_DYNAMIC python3 "$HOME/.codex/skills/debt/scan.py"
printf 'exit=%s\n' "$?"
```

Antes, líneas del escáner y código de salida.

```text
  tasks/backlog/                   85 abiertas
  COULD_NOT_RUN                    0   (fuentes o archivos sin medir)
  TOTAL PENDIENTE (sin duplicar)   85
exit=1
```

Después, líneas del escáner y código de salida.

```text
  tasks/backlog/                   84 abiertas
  COULD_NOT_RUN                    0   (fuentes o archivos sin medir)
  TOTAL PENDIENTE (sin duplicar)   84
exit=1
```

El escáner devuelve 1 mientras quedan fichas abiertas. El cierre del lote descansa en el `close_check` y en la comparación de cobertura con su control negativo.
