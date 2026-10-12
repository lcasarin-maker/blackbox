#!/usr/bin/env bash
# Aplica la propuesta de vLLM (ver propuesta.txt). Hace respaldo con fecha, valida el JSON y NO reinicia nada.
set -euo pipefail
AQUI=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
GW=/srv/ai/gateway
FECHA=pre-reinicio-$(date +%Y%m%d-%H%M%S)
python3 -m json.tool "$AQUI/propuesta-active_engine.json" >/dev/null || { echo "propuesta invalida" >&2; exit 1; }
python3 -m py_compile "$AQUI/propuesta-main.py.txt" 2>/dev/null || cp "$AQUI/propuesta-main.py.txt" /tmp/pm.py && python3 -m py_compile /tmp/pm.py || { echo "main.py propuesto no compila" >&2; exit 1; }
cp -p "$GW/active_engine.json" "$GW/active_engine.json.bak-$FECHA"
cp -p "$GW/main.py" "$GW/main.py.bak-$FECHA"
cp "$AQUI/propuesta-active_engine.json" "$GW/active_engine.json.nuevo" && mv "$GW/active_engine.json.nuevo" "$GW/active_engine.json"
cp "$AQUI/propuesta-main.py.txt" "$GW/main.py.nuevo" && mv "$GW/main.py.nuevo" "$GW/main.py"
echo "aplicado. Respaldos: $GW/active_engine.json.bak-$FECHA y $GW/main.py.bak-$FECHA"
echo "Retroceso: cp -p $GW/active_engine.json.bak-$FECHA $GW/active_engine.json && cp -p $GW/main.py.bak-$FECHA $GW/main.py"
echo "Surte efecto en el proximo arranque de vLLM (no se reinicio nada)."
