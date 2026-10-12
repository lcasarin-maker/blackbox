#!/usr/bin/env bash
# Aplica la propuesta de vLLM (ver propuesta.txt). Hace respaldo con fecha, valida el JSON y NO reinicia nada.
set -euo pipefail
AQUI=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
GW=/srv/ai/gateway
FECHA=pre-reinicio-$(date +%Y%m%d-%H%M%S)
python3 -m json.tool "$AQUI/propuesta-active_engine.json" >/dev/null || { echo "propuesta invalida" >&2; exit 1; }
# main.py: se aplica el DIFF (no se copia un archivo entero de produccion); primero en seco
patch -d / -p1 --dry-run -s < "$AQUI/propuesta-main.py.diff" || { echo "el diff de main.py no aplica a $GW/main.py (¿cambio desde la propuesta?)" >&2; exit 1; }
cp -p "$GW/active_engine.json" "$GW/active_engine.json.bak-$FECHA"
cp -p "$GW/main.py" "$GW/main.py.bak-$FECHA"
cp "$AQUI/propuesta-active_engine.json" "$GW/active_engine.json.nuevo" && mv "$GW/active_engine.json.nuevo" "$GW/active_engine.json"
patch -d / -p1 -s < "$AQUI/propuesta-main.py.diff"
python3 -m py_compile "$GW/main.py" || { echo "main.py no compila tras el parche: restaurando"; cp -p "$GW/main.py.bak-$FECHA" "$GW/main.py"; exit 1; }
echo "aplicado. Respaldos: $GW/active_engine.json.bak-$FECHA y $GW/main.py.bak-$FECHA"
echo "Retroceso: cp -p $GW/active_engine.json.bak-$FECHA $GW/active_engine.json && cp -p $GW/main.py.bak-$FECHA $GW/main.py"
echo "Surte efecto en el proximo arranque de vLLM (no se reinicio nada)."
