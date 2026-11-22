#!/usr/bin/env python3
"""Aviso, una vez por arranque, de que el controlador NVIDIA declaro la GPU en `Reset Required`.

Lee el journal de kernel del arranque ACTUAL (solo lectura) y busca la secuencia medida el 2026-11-02 en los
arranques con 7.0.0-1024-nvidia: `NVRM: _issueRpcAndWait: rpcRecvPoll timedout` o `Xid ...: 154`. Si aparece, anota
una fila en `$BLACKBOX_DATA/aviso_gpu_reset.jsonl` (idempotente por boot_id) y avisa por el canal de
`aviso_termico` (notify-send). La fila solo se escribe cuando el aviso salio: si no habia sesion grafica, la
corrida siguiente del timer reintenta. Reusa el parser de `reboot_verdict.gpu_del_boot`; no escribe nada mas.

`--boot <id>` evalua otro arranque (control negativo/positivo) y solo imprime, sin anotar ni avisar.
DEBT-NVRM-GSP-TIMEOUT-XID154-KERNEL-7-0-SIN-ALARMA-01 punto 2.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools import aviso_termico, reboot_verdict

RUTA = reboot_verdict.DATOS / "aviso_gpu_reset.jsonl"


def corroborar_gsp(*, boot_id: str | None, evidencia_boot_id: str | None,
                   lineas: list[str] | None, intervalo_sospecha: tuple[float, float] | None,
                   ahora_monotonic: float, journal_legible: bool,
                   incertidumbre_s: float | None) -> dict[str, Any]:
    """Usa hechos y tiempo de la misma línea reconocida por el parser."""
    reloj_valido = (isinstance(ahora_monotonic, (int, float))
                    and math.isfinite(ahora_monotonic))
    incertidumbre_valida = (isinstance(incertidumbre_s, (int, float))
                            and math.isfinite(incertidumbre_s) and incertidumbre_s >= 0)
    intervalo_valido = (isinstance(intervalo_sospecha, tuple) and len(intervalo_sospecha) == 2
                        and all(isinstance(x, (int, float)) and math.isfinite(x)
                                for x in intervalo_sospecha)
                        and intervalo_sospecha[0] <= intervalo_sospecha[1])
    if (not boot_id or evidencia_boot_id != boot_id or not reloj_valido
            or not journal_legible or not intervalo_valido or not incertidumbre_valida
            or lineas is None):
        return {"estado": "desconocido", "incertidumbre_s": incertidumbre_s}
    hechos_parser = None
    tiempo = None
    for linea in lineas:
        if not isinstance(linea, str):
            continue
        # El parser canónico valida firma y monotónico en la misma línea. Parsear
        # una línea a la vez evita que un timeout antiguo oculte uno en ventana.
        candidato = reboot_verdict.gpu_del_boot([linea])
        instante = candidato["gsp_timeout_monotonic_s"]
        if (candidato["gsp_timeout"] and instante is not None
                and math.isfinite(instante)
                and intervalo_sospecha[0] <= instante <= intervalo_sospecha[1]
                and instante <= ahora_monotonic):
            hechos_parser, tiempo = candidato, instante
            break
    if hechos_parser is None:
        return {"estado": "desconocido", "incertidumbre_s": incertidumbre_s}
    return {"estado": "confirmado", "incertidumbre_s": incertidumbre_s,
            "evidencia_monotonic": tiempo, "hechos_parser": hechos_parser}


def aviso_calidad(evento: dict[str, Any], *, receptor=None, clave: str | None = None,
                  estado: set[str] | None = None) -> bool:
    """Canal de calidad solo con receptor y clave explícitos; éxito = ACK del receptor.

    `estado` deduplica en memoria dentro del llamador. Un fallo no consume la
    clave y permite reintentar; una caída del proceso pierde dedup, por lo que
    no ofrece exactamente-una-vez ni persistencia productiva.
    """
    if receptor is None or not clave or estado is None or clave in estado:
        return False
    if receptor(evento) is not True:
        return False
    estado.add(clave)
    return True


def aviso_calidad_corrobora(evento: dict[str, Any], *,
                            boot_id: str | None, evidencia_boot_id: str | None,
                            lineas: list[str] | None, intervalo_sospecha: tuple[float, float] | None,
                            observaciones_calidad: list[dict[str, Any]], ahora_monotonic: float,
                            journal_legible: bool, incertidumbre_s: float | None,
                            receptor=None, clave: str | None = None,
                            estado: set[str] | None = None) -> bool:
    """Ruta explícita de aviso sintético; main() productivo no la invoca."""
    evidencia = corroborar_gsp(
        boot_id=boot_id, evidencia_boot_id=evidencia_boot_id, lineas=lineas,
        intervalo_sospecha=intervalo_sospecha,
        ahora_monotonic=ahora_monotonic, journal_legible=journal_legible,
        incertidumbre_s=incertidumbre_s)
    if evidencia["estado"] != "confirmado":
        return False
    ultima_observacion = (observaciones_calidad[-1]
                          if isinstance(observaciones_calidad, list) and observaciones_calidad
                          and isinstance(observaciones_calidad[-1], dict) else {})
    calidad_sustenta = (isinstance(observaciones_calidad, list) and len(observaciones_calidad) >= 2
                        and isinstance(evento, dict)
                        and evento.get("tipo") == "gpu_calidad"
                        and evento.get("boot_id") == boot_id
                        and all(evento.get(k) == ultima_observacion.get(k)
                                for k in ("boot_id", "monotonic_s", "estado", "comparacion", "edad_contenido_s"))
                        and all(isinstance(o, dict) and o.get("boot_id") == boot_id
                                and o.get("estado") == "reciente"
                                and o.get("comparacion") == "igual"
                                and isinstance(o.get("monotonic_s"), (int, float))
                                and math.isfinite(o["monotonic_s"])
                                and intervalo_sospecha[0] <= o["monotonic_s"] <= intervalo_sospecha[1]
                                and o["monotonic_s"] <= ahora_monotonic
                                and isinstance(o.get("edad_contenido_s"), (int, float))
                                and math.isfinite(o["edad_contenido_s"])
                                for o in observaciones_calidad)
                        and observaciones_calidad[-1]["monotonic_s"] > observaciones_calidad[0]["monotonic_s"]
                        and observaciones_calidad[-1]["edad_contenido_s"] > observaciones_calidad[0]["edad_contenido_s"]
                        and evento.get("monotonic_s") == observaciones_calidad[-1]["monotonic_s"])
    if not calidad_sustenta:
        return False
    return aviso_calidad(evento, receptor=receptor, clave=clave, estado=estado)


def hechos(lineas: list[str]) -> dict[str, Any]:
    h = reboot_verdict.gpu_del_boot(lineas)
    return {**h, "detectado": bool(h["gsp_timeout"] or h["xid154"])}


def lee_journal(boot_id: str) -> list[str] | None:
    """Lineas de `journalctl -k -b <boot_id>`; None si journalctl falla (no se sabe, nunca 'sin secuencia')."""
    r = reboot_verdict._journal("-k", "-b", boot_id, "-o", "short-monotonic")
    return r.stdout.splitlines() if r.returncode == 0 else None


def ya_anotado(boot_id: str, ruta: Path | None = None) -> bool:
    try:
        with (ruta or RUTA).open(encoding="utf-8") as f:
            return any(
                json.loads(ln).get("boot_id") == boot_id for ln in f if ln.strip()
            )
    except (OSError, ValueError):
        return False


def aviso(h: dict[str, Any]) -> aviso_termico.Aviso:
    t = h["gsp_timeout_monotonic_s"]
    return aviso_termico.Aviso(
        "critical",
        "GPU: el controlador pide reinicio",
        f"Este arranque registro timeout del GSP (a {t} s) / Xid 154 y {h['gpu_fullchip_reset_asserts']} asserts de reset: "
        "la GPU esta en 'Reset Required' y el motor sigue sirviendo sobre ella. Guarda el trabajo y reinicia.",
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--boot", help="boot_id a evaluar (solo imprime)")
    a = ap.parse_args(argv)
    actual = reboot_verdict.BOOT_ID_ACTUAL.read_text().strip().replace("-", "")
    boot_id = a.boot or actual
    lineas = lee_journal(boot_id)
    if lineas is None:
        print("COULD_NOT_RUN: journalctl fallo", file=sys.stderr)
        return 2
    h = hechos(lineas)
    print(
        json.dumps({"boot_id": boot_id, "lineas": len(lineas), **h}, ensure_ascii=False)
    )
    if a.boot or not h["detectado"] or ya_anotado(boot_id):
        return 0
    if not aviso_termico.enviar(aviso(h)):
        return 1  # sin fila: la siguiente corrida del timer reintenta
    RUTA.parent.mkdir(parents=True, exist_ok=True)
    with RUTA.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "boot_id": boot_id,
                    "visto_en": datetime.now(timezone.utc).isoformat(),
                    **h,
                }
            )
            + "\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
