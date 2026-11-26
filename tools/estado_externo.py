#!/usr/bin/env python3
"""Canal único de estado externo `bb-estado-externo/1` (FEATURE-ESTADO-EXTERNO-UN-SOLO-CANAL-01).

Construye y publica de forma atómica (`os.replace`) el estado del equipo testigo y del
enchufe medidor (procesos, caminos de alarma, netconsole, sondeos 5m, enchufe/Wh, disco
externo, enlaces y deriva SHA-256 contra el repo), y lo trae a `/run/bb-estado-externo/estado_externo.json`.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Callable, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import energia_acumulada

ESQUEMA = "bb-estado-externo/1"
INTERVALO_S_DEFECTO = 30.0
RUN_ESTADO_DEFECTO = Path("/run/bb-estado-externo/estado_externo.json")
ORIGEN_TESTIGO_RE = re.compile(r"[A-Za-z0-9._-]+@(?:[A-Za-z0-9._-]+|\[[0-9A-Fa-f:]+\])")
Correr = Callable[..., Any]


def _escribir_atomico(destino: Path, payload: dict[str, Any]) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(dir=destino.parent, prefix=f".tmp-{destino.name}-")
    try:
        os.chmod(tmp_name, 0o644)
        with os.fdopen(fd, "wb") as fh:
            fh.write(datos)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, destino)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def _sha256(ruta: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with ruta.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def medir_deriva_despliegue(
    repo_hashes: dict[str, str],
    desplegado_hashes: dict[str, str | None],
    edad_lectura_s: float | None = None,
) -> dict[str, Any]:
    archivos: dict[str, dict[str, Any]] = {}
    divergente = False
    for nombre, esperado in sorted(repo_hashes.items()):
        actual = desplegado_hashes.get(nombre)
        if actual is None:
            estado = "NOT_COLLECTED"
            divergente = True
        elif actual == esperado:
            estado = "igual"
        else:
            estado = "divergente"
            divergente = True
        archivos[nombre] = {
            "repo_sha256": esperado,
            "desplegado_sha256": actual,
            "estado": estado,
        }
    return {
        "divergente": divergente,
        "edad_s": edad_lectura_s,
        "archivos": archivos,
    }


def _percentil(valores: list[float], p: float) -> float | None:
    if not valores:
        return None
    s = sorted(valores)
    idx = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return round(s[idx], 2)


def _resumen_sondeos(filas_ping: Sequence[dict[str, Any]], desde: float, hasta: float) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for fuente in ("tcp", "icmp"):
        sub = [
            f for f in filas_ping
            if f.get("fuente") == fuente
            and isinstance(f.get("epoch"), (int, float))
            and desde <= float(f["epoch"]) <= hasta
            and f.get("estado") != "sin_red"
        ]
        if not sub:
            out[fuente] = {"ok_pct": "NOT_COLLECTED", "rtt_p50_ms": "NOT_COLLECTED", "rtt_p95_ms": "NOT_COLLECTED", "muestras": 0}
            continue
        oks = sum(1 for f in sub if f.get("ok") is True)
        rtts = [float(f["rtt_ms"]) for f in sub if isinstance(f.get("rtt_ms"), (int, float)) and not isinstance(f.get("rtt_ms"), bool)]
        out[fuente] = {
            "ok_pct": round((oks / len(sub)) * 100.0, 2),
            "rtt_p50_ms": _percentil(rtts, 50.0) if rtts else "NOT_COLLECTED",
            "rtt_p95_ms": _percentil(rtts, 95.0) if rtts else "NOT_COLLECTED",
            "muestras": len(sub),
        }
    return out


def construir_estado_externo(
    *,
    ts: float,
    ahora: float,
    intervalo_s: float = INTERVALO_S_DEFECTO,
    procesos: dict[str, Any] | None = None,
    alarma_caminos: dict[str, Any] | None = None,
    netconsole: dict[str, Any] | None = None,
    filas_ping: Sequence[dict[str, Any]] = (),
    filas_energia: Sequence[dict[str, Any]] = (),
    disco_externo: dict[str, Any] | None = None,
    enlaces: dict[str, Any] | None = None,
    deriva: dict[str, Any] | None = None,
) -> dict[str, Any]:
    edad_s = ahora - ts
    vigente = 0.0 <= edad_s <= 3.0 * intervalo_s
    if edad_s < 0.0:
        motivo_vigencia = "ts en el futuro"
        vigente = False
    elif edad_s > 3.0 * intervalo_s:
        motivo_vigencia = f"archivo vencido ({edad_s:.1f}s > {3.0 * intervalo_s:.1f}s)"
    else:
        motivo_vigencia = "vigente"

    caminos = alarma_caminos or {}
    caminos_bool = {
        "ssh_casa": caminos.get("ssh_casa", "NOT_COLLECTED"),
        "ssh_tailscale": caminos.get("ssh_tailscale", "NOT_COLLECTED"),
        "rustdesk": caminos.get("rustdesk", "NOT_COLLECTED"),
    }
    completa = all(v is True for v in caminos_bool.values())

    res_energia = energia_acumulada.resumen_energia(filas_energia, ahora=ahora) if filas_energia else None
    ultima_en = next(
        (f for f in reversed(list(filas_energia)) if f.get("ok") is True),
        None,
    )
    enchufe = {
        "ok": bool(ultima_en) if filas_energia else "NOT_COLLECTED",
        "potencia_w": ultima_en.get("potencia_w", "NOT_COLLECTED") if ultima_en else "NOT_COLLECTED",
        "voltaje_v": ultima_en.get("voltaje_v", "NOT_COLLECTED") if ultima_en else "NOT_COLLECTED",
        "corriente_a": ultima_en.get("corriente_a", "NOT_COLLECTED") if ultima_en else "NOT_COLLECTED",
        "energia_dia_wh": res_energia["wh_hoy"] if res_energia and res_energia["wh_hoy"] is not None else "NOT_COLLECTED",
        "energia_fuente": res_energia["energia_fuente"] if res_energia else "NOT_COLLECTED",
    }

    return {
        "esquema": ESQUEMA,
        "ts": datetime.fromtimestamp(ts, timezone.utc).isoformat(),
        "epoch": ts,
        "intervalo_s": intervalo_s,
        "vigente": vigente,
        "motivo_vigencia": motivo_vigencia,
        "procesos": procesos or {
            "testigo": "NOT_COLLECTED",
            "alarma": "NOT_COLLECTED",
            "receptor_netconsole": "NOT_COLLECTED",
        },
        "alarma_caminos": {**caminos_bool, "completa": completa},
        "netconsole": netconsole or {"edad_s": "NOT_COLLECTED", "tamano_bytes": "NOT_COLLECTED"},
        "sondeos_5m": _resumen_sondeos(filas_ping, ahora - 300.0, ahora),
        "enchufe": enchufe,
        "disco": disco_externo or {"ok": False, "volumenes": []},
        "enlaces": enlaces or {"estado": "NOT_COLLECTED"},
        "deriva_despliegue": deriva or {"divergente": False, "archivos": {}},
    }


def evaluar_vigencia(doc: dict[str, Any], *, ahora: float) -> dict[str, Any]:
    out = dict(doc)
    intervalo = float(out.get("intervalo_s") or INTERVALO_S_DEFECTO)
    epoch = out.get("epoch")
    if not isinstance(epoch, (int, float)) or isinstance(epoch, bool):
        out["vigente"] = False
        out["motivo_vigencia"] = "epoch ausente o invalido"
        return out
    edad = ahora - float(epoch)
    if edad > 3.0 * intervalo:
        out["vigente"] = False
        out["motivo_vigencia"] = f"archivo vencido ({edad:.1f}s > {3.0 * intervalo:.1f}s)"
    elif edad < -intervalo:
        out["vigente"] = False
        out["motivo_vigencia"] = "epoch en el futuro"
    return out


def trae_estado_externo(
    cfg_ruta: Path,
    destino: Path = RUN_ESTADO_DEFECTO,
    *,
    correr: Correr = subprocess.run,
    ahora: float | None = None,
) -> dict[str, Any]:
    t = datetime.now(timezone.utc).timestamp() if ahora is None else ahora
    try:
        cfg = json.loads(cfg_ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"estado": "COULD_NOT_RUN", "motivo": f"{cfg_ruta.name} ilegible: {exc}"}
    origen = cfg.get("origen")
    ruta_remota = cfg.get("ruta_estado") or cfg.get("ruta")
    if not isinstance(origen, str) or not ORIGEN_TESTIGO_RE.fullmatch(origen):
        return {"estado": "COULD_NOT_RUN", "motivo": "origen invalido en configuracion"}
    if not isinstance(ruta_remota, str) or not ruta_remota.strip() or any(c in ruta_remota for c in "\n\r\"*?["):
        return {"estado": "COULD_NOT_RUN", "motivo": "ruta remota invalida"}

    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destino.parent, prefix=".trae-estado-") as d:
        tmp_dl = Path(d) / "estado_externo.json"
        cmd = ["scp", "-s", "-q", "-B", "-p", "-o", "ConnectTimeout=10", f"{origen}:{ruta_remota}", str(tmp_dl)]
        try:
            r = correr(cmd, capture_output=True, text=True, check=False, timeout=20)
        except (OSError, subprocess.SubprocessError) as exc:
            return {"estado": "COULD_NOT_RUN", "motivo": f"scp: {type(exc).__name__}"}
        if r.returncode != 0 or not tmp_dl.is_file():
            return {"estado": "COULD_NOT_RUN", "motivo": f"scp rc={r.returncode}"}
        try:
            doc = json.loads(tmp_dl.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return {"estado": "COULD_NOT_RUN", "motivo": f"json externo ilegible: {exc}"}
        if not isinstance(doc, dict) or doc.get("esquema") != ESQUEMA:
            return {"estado": "COULD_NOT_RUN", "motivo": "esquema externo invalido"}
        doc = evaluar_vigencia(doc, ahora=t)
        _escribir_atomico(destino, doc)
        return {"estado": "OK", "vigente": doc["vigente"], "destino": str(destino)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="estado_externo")
    ap.add_argument("--traer", type=Path, help="Ruta a testigo.json para traer estado_externo.json")
    ap.add_argument("--destino", type=Path, default=RUN_ESTADO_DEFECTO)
    args = ap.parse_args(argv)
    if args.traer:
        res = trae_estado_externo(args.traer, args.destino)
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res.get("estado") == "OK" else 2
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
