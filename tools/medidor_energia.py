#!/usr/bin/env python3
"""Medidor de energia externo (interruptor `medidor_energia`): FEATURE-MEDIDOR-DE-ENERGIA-EXTERNO-01.

Un corte de energia mata al propio instrumento, asi que la unica prueba de si la pared dejo de dar corriente o la ATOM se
apago sola viene de un enchufe con medidor entre la pared y el adaptador. Este modulo lee ese enchufe por su API local, una
lectura por ejecucion (la repeticion de 1 s es de `systemd/bb-medidor-energia.timer`, sin bucles ni `sleep` aqui), y anade
una fila a `$BLACKBOX_DATA/externo/energia.jsonl`. DEBE correr en OTRO equipo (o en un archivo que ese equipo sincronice):
si corre en la ATOM muere con ella y no prueba nada.

Configuracion: `$BLACKBOX_DATA/externo/medidor.json` = {"tipo": "shelly"|"tasmota", "url": "http://<ip-del-enchufe>"}.
Los campos que se leen son los de la documentacion de cada fabricante (Shelly Gen2/3 `Switch.GetStatus`: apower, voltage,
current; Tasmota `Status 8`: ENERGY.Power, Voltage, Current); NO se verificaron contra un dispositivo, y por eso un campo ausente sale
`NOT_COLLECTED`, nunca un cero. Un enchufe que no responde se registra como `ok: false`: eso NO es voltaje perdido (puede ser el
Wi-Fi del enchufe).

`ventana_de_corte` clasifica un corte con tres estados y solo concluye con voltaje MEDIDO:
  voltaje_perdido True   una fila de la ventana mide menos de VOLTAJE_CAIDO_V.
  voltaje_perdido False  antes del corte la ATOM consumia (>= CARGA_W) y despues el enchufe sigue midiendo voltaje normal con
                         consumo ~0 (< APAGADA_W): la pared dio corriente y la maquina se apago.
  None                   cualquier otra cosa (sin filas, enchufe mudo, datos parciales): no concluyente.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tools import interruptores

NOMBRE = "medidor_energia"
VOLTAJE_CAIDO_V = 90.0  # red de 120 V: por debajo de esto el adaptador de 240 W ya no entrega
VOLTAJE_NORMAL_V = 100.0
CARGA_W = 20.0  # la ATOM encendida y sin carga consume 22-45 W (medicion de Tom's Hardware, no de esta unidad)
APAGADA_W = 5.0
MARGEN_ANTES_S = 30.0
Abre = Callable[[str], bytes]


def _datos() -> Path:
    return Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox")) / "externo"


def _abre(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=2) as r:
        return bytes(r.read())


def _num(d: Any, *claves: str) -> float | None:
    for c in claves:
        d = d.get(c) if isinstance(d, dict) else None
    return float(d) if isinstance(d, (int, float)) and not isinstance(d, bool) else None


def lee(cfg: dict[str, Any], abre: Abre = _abre) -> dict[str, Any]:
    """Una lectura: `ok`, voltaje_v, potencia_w, corriente_a. Una respuesta ilegible o con campos ausentes no inventa cifras."""
    tipo, url = cfg.get("tipo"), str(cfg.get("url", "")).rstrip("/")
    if tipo == "shelly":
        ruta, campos = "/rpc/Switch.GetStatus?id=0", (("voltage",), ("apower",), ("current",))
    elif tipo == "tasmota":
        ruta, campos = "/cm?cmnd=Status%208", (("StatusSNS", "ENERGY", "Voltage"), ("StatusSNS", "ENERGY", "Power"), ("StatusSNS", "ENERGY", "Current"))
    else:
        return {"ok": False, "error": f"NOT_COLLECTED: tipo '{tipo}' sin lector"}
    try:
        j = json.loads(abre(url + ruta))
    except (OSError, ValueError) as e:
        return {"ok": False, "error": f"{type(e).__name__}"}
    v, w, a = (_num(j, *c) for c in campos)
    if v is None or w is None:
        return {"ok": False, "error": "NOT_COLLECTED: respuesta sin voltaje o potencia"}
    return {"ok": True, "voltaje_v": v, "potencia_w": w, "corriente_a": a}


def paso(modo_actual: str, cfg: dict[str, Any], ruta: Path, abre: Abre = _abre, ahora: float | None = None) -> dict[str, Any] | None:
    """Una fila en `energia.jsonl`. `off` no lee."""
    if modo_actual == "off":
        return None
    t = datetime.now(timezone.utc).timestamp() if ahora is None else ahora
    fila = {"ts": datetime.fromtimestamp(t, timezone.utc).isoformat(), "epoch": t, **lee(cfg, abre)}
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(fila) + "\n")
    return fila


def _filas(ruta: Path) -> list[dict[str, Any]]:
    try:
        lineas = ruta.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for ln in lineas:
        try:
            f = json.loads(ln)
        except ValueError:
            continue
        if isinstance(f, dict) and isinstance(f.get("epoch"), (int, float)):
            out.append(f)
    return out


def ventana_de_corte(ruta: Path, fin_epoch: float, hueco_s: float) -> dict[str, Any] | None:
    """Evidencia externa de un corte que ocurrio en `fin_epoch` y duro `hueco_s`. None si no hay filas que cubran la ventana."""
    filas = [f for f in _filas(ruta) if fin_epoch - MARGEN_ANTES_S <= f["epoch"] <= fin_epoch + max(hueco_s, 0.0)]
    if not filas:
        return None
    medidas = [f for f in filas if f.get("ok") is True]
    if any(f["voltaje_v"] < VOLTAJE_CAIDO_V for f in medidas):
        return {"voltaje_perdido": True, "motivo": f"una fila de la ventana mide menos de {VOLTAJE_CAIDO_V:g} V"}
    antes = [f for f in medidas if f["epoch"] <= fin_epoch]
    despues = [f for f in medidas if f["epoch"] > fin_epoch]
    if antes and despues and antes[-1]["potencia_w"] >= CARGA_W and all(f["voltaje_v"] >= VOLTAJE_NORMAL_V and f["potencia_w"] < APAGADA_W for f in despues[:3]):
        return {"voltaje_perdido": False, "motivo": "el enchufe siguio midiendo voltaje normal con la ATOM sin consumo despues del corte"}
    return {"voltaje_perdido": None, "motivo": f"{len(filas)} filas en la ventana, {len(medidas)} con medicion: no concluyente"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="medidor_energia")
    ap.add_argument("--paso", action="store_true", help="una lectura segun el interruptor medidor_energia (la repite bb-medidor-energia.timer)")
    a = ap.parse_args(argv)
    if not a.paso:
        ap.print_help()
        return 2
    try:
        cfg = json.loads((_datos() / "medidor.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("NOT_COLLECTED: falta $BLACKBOX_DATA/externo/medidor.json con {tipo, url}", file=sys.stderr)
        return 1
    print(json.dumps(paso(interruptores.modo(NOMBRE), cfg, _datos() / "energia.jsonl"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
