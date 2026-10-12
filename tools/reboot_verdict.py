#!/usr/bin/env python3
"""Veredicto por reinicio de la ATOM: UNA fila por boot terminado, con la causa
y la evidencia que la sostiene.

Por que existe (2026-10-11): de los ultimos 10 reinicios, 4 fueron cortes
abruptos bajo carga sin ninguna causa interna, y nadie podia decir si fue
energia o hardware. Cada boot se clasifica con reglas que miran SU evidencia:

  CIERRE_ORDENADO    reboot.target / poweroff.target y "Journal stopped".
  COLAPSO_MEMORIA    `bb-usable` registro COLAPSO en los ultimos 15 min del boot,
                     o la ultima muestra de telemetria llevaba PSI full >= 10.
  PANIC_KERNEL       el journal del boot trae "Kernel panic".
  CORTE_ABRUPTO      el journal calla sin cierre, sin colapso y sin panic. La
                     causa queda INDETERMINADA (energia vs hardware interno)
                     hasta que un observador EXTERNO (enchufe medidor, ping de
                     otro equipo) aporte evidencia; sin ella el veredicto lo
                     dice, no lo adivina.

Estado por defecto: INDETERMINADO. Un boot sin evidencia suficiente jamas se
rotula "limpio". Toda fuente que no se pudo leer sale en `could_not_run`, y un
reporte con `could_not_run` no vacio no es un reporte limpio.

Lo que esta herramienta NO ve: la perdida de alimentacion. Un corte de energia
mata este mismo proceso, asi que la prueba tiene que venir de afuera
(`--externo`). Ver DEBT-CORTES-BAJO-CARGA-SIN-RASTRO-01.
"""

from __future__ import annotations

import os
import argparse
import json
from datetime import datetime, timezone
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools import hallazgo

DATOS = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))
TELEMETRIA = DATOS / "atom_gpu_telemetry.jsonl"
SALIDA = DATOS / "reboots.jsonl"
WATCHDOG_BOOTSTATUS = Path("/sys/class/watchdog/watchdog0/bootstatus")
VENTANA_COLAPSO_S = 900
PSI_FULL_COLAPSO = 10.0
# Clase de registro BERT que el personal de NVIDIA cita (hilo 384436): Atlas, catalogo_destilado.md#forum:G6
GUID_MTKID = "3c1e3f4b-1e1a-43df-af28-59820e958e3c"

CIERRE = re.compile(r"Reached target (reboot|poweroff|halt|kexec)\.target")
JOURNAL_PARADO = re.compile(r"systemd-journald\[\d+\]: Journal stopped")
COLAPSO = re.compile(r"\[bb-usable\] COLAPSO")
PANIC = re.compile(r"Kernel panic - not syncing")
DISPARADOR = re.compile(
    r"sudo\b.*COMMAND=\S*(?:reboot|poweroff|shutdown|halt)"
    r"|systemd-logind\[\d+\]: (?:Power key pressed|The system will (?:reboot|power off|halt) now!"
    r"|System is (?:rebooting|powering down|halting))"
    r"|audit.*EXECVE.*(?:reboot|poweroff|shutdown)"
)


def disparador(lineas: list[str]) -> str | None:
    """Ultima linea del journal que nombra quien/que ordeno el cierre, o None."""
    for linea in reversed(lineas):
        if DISPARADOR.search(linea):
            return linea.strip()[:200]
    return None


def _corte_abrupto(
    ev: dict[str, Any], psi_full: float | None, no_corrio: list[str]
) -> tuple[str, list[str]]:
    """Journal mudo sin cierre, colapso ni panic: solo un observador externo puede decir mas."""
    razones = ["el journal calla sin cierre, sin colapso de memoria y sin panic"]
    if psi_full is not None:
        razones.append(
            f"PSI full avg10={psi_full} en la ultima muestra: no fue memoria"
        )
    externo = ev.get("externo")
    if externo is None:
        razones.append(
            "causa INDETERMINADA (energia vs hardware interno): falta observador externo"
        )
        no_corrio.append("observador_externo")
        return "CORTE_ABRUPTO", razones
    if externo.get("voltaje_perdido") is True:
        razones.append("el medidor externo registro perdida de voltaje")
        return "CORTE_DE_RED", razones
    if externo.get("voltaje_perdido") is False:
        razones.append(
            "el medidor externo registro voltaje presente mientras la maquina murio"
        )
        return "APAGADO_INTERNO", razones
    return "CORTE_ABRUPTO", razones


def veredicto(ev: dict[str, Any]) -> dict[str, Any]:
    """Clasifica un boot. `ev` trae solo evidencia ya leida; esta funcion no lee
    nada, para que cada rama tenga un caso que la active y otro que no."""
    razones: list[str] = []
    no_corrio: list[str] = list(ev.get("no_se_pudo_leer", []))
    tele = ev.get("telemetria") or {}
    psi_full = tele.get("psi_mem_full_avg10")

    if ev.get("panic"):
        etiqueta = "PANIC_KERNEL"
        razones.append("el journal del boot trae 'Kernel panic - not syncing'")
    elif ev.get("colapso_en_ventana") or (
        psi_full is not None and psi_full >= PSI_FULL_COLAPSO
    ):
        etiqueta = "COLAPSO_MEMORIA"
        razones.append(
            f"bb-usable COLAPSO en los ultimos {VENTANA_COLAPSO_S}s"
            if ev.get("colapso_en_ventana")
            else f"ultima muestra con PSI full avg10={psi_full} >= {PSI_FULL_COLAPSO}"
        )
    elif ev.get("cierre"):
        etiqueta = f"CIERRE_ORDENADO_{str(ev['cierre']).upper()}"
        if ev.get("disparador") and "COMMAND=" in ev["disparador"]:
            razones.append(f"pedido por sudo: {ev['disparador']}")
        elif ev.get("disparador"):
            razones.append(
                f"orden ejecutada por logind ({ev['disparador']}); QUIEN la pidio no consta "
                "(D-Bus/escritorio no deja execve en auditoria)"
            )
        else:
            razones.append(
                "disparador NO_REGISTRADO: ninguna linea de sudo/logind/audit lo nombra"
            )
    elif ev.get("journal_parado"):
        etiqueta = "INDETERMINADO"
        razones.append("Journal stopped sin target de cierre: apagado a medias")
    else:
        etiqueta, extra = _corte_abrupto(ev, psi_full, no_corrio)
        razones.extend(extra)

    if ev.get("bootstatus_siguiente") not in (None, 0):
        razones.append(
            f"watchdog bootstatus={ev['bootstatus_siguiente']} en el arranque siguiente"
        )
    return {
        "etiqueta": etiqueta,
        "razones": razones,
        "bert_siguiente": ev.get("bert_siguiente"),
        "bert_palabra_0x14": (ev.get("bert") or {}).get("palabra_en_0x14"),
        "bert_guid": (ev.get("bert") or {}).get("section_guid"),
        "hueco_s": ev.get("hueco_s"),
        "could_not_run": no_corrio,
    }


# ---------------------------------------------------------------- colectores
def _journal(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["journalctl", "--no-pager", *args],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _ultima_telemetria(boot_id: str) -> dict[str, Any] | None:
    if not TELEMETRIA.exists():
        return None
    ultima = None
    marca = (
        boot_id
        if "-" in boot_id
        else f"{boot_id[:8]}-{boot_id[8:12]}-{boot_id[12:16]}-{boot_id[16:20]}-{boot_id[20:]}"
    )
    with TELEMETRIA.open(encoding="utf-8") as fh:
        for linea in fh:
            if marca in linea and '"evento": "muestra"' in linea:
                ultima = linea
    return json.loads(ultima) if ultima else None


def _disparador_boot(idx: int) -> str | None:
    """logind y sudo por identificador: el cierre escribe cientos de lineas y `-n 500` las pierde."""
    lineas: list[str] = []
    for ident in ("systemd-logind", "sudo"):
        lineas += _journal(
            "-b", str(idx), "-t", ident, "-n", "40", "-o", "short-iso"
        ).stdout.splitlines()
    return disparador(lineas)


BERT_GUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
BERT_VOLCADO = re.compile(
    r"\[Hardware Error\]:\s+([0-9a-f]{8}): ((?:[0-9a-f]{8} ?){1,4})"
)


def bert_registro(idx_siguiente: int) -> dict[str, Any]:
    """Registro BERT que el firmware deja para el arranque SIGUIENTE al corte. El payload es del
    fabricante (creador MTKID) y Linux no lo decodifica (NVIDIA staff, hilo 384436): se informa
    cada campo tal cual, mas la palabra en 0x14, que es la que cambia entre cortes."""
    r = _journal("-b", str(idx_siguiente), "-k", "-o", "cat")
    if r.returncode != 0:
        return {"estado": "COLLECTION_FAILED"}
    lineas = r.stdout.splitlines()
    ini = next(
        (
            i
            for i, x in enumerate(lineas)
            if "BERT: Error records from previous boot" in x
        ),
        None,
    )
    if ini is None:
        return {
            "estado": f"0 registros BERT en el journal del kernel del boot {idx_siguiente} (ausente: el firmware no registro un error)"
        }
    fin = next(
        (
            i
            for i, x in enumerate(lineas[ini:], ini)
            if "BERT: Total records found" in x
        ),
        len(lineas),
    )
    bloque = lineas[ini:fin]
    guid = next(
        (
            m.group(0)
            for x in bloque
            if "section type" in x
            for m in [BERT_GUID.search(x)]
            if m
        ),
        "NOT_COLLECTED",
    )
    sev = next(
        (x.split(":")[-1].strip() for x in bloque if "event severity" in x),
        "NOT_COLLECTED",
    )
    longitud = next(
        (x.split(":")[-1].strip() for x in bloque if "section length" in x),
        "NOT_COLLECTED",
    )
    volcado = {
        m.group(1): m.group(2).split()
        for x in bloque
        for m in [BERT_VOLCADO.search(x)]
        if m
    }
    palabras = volcado.get("00000010", [])
    return {
        "severidad": sev,
        "section_guid": guid,
        "section_length": longitud,
        "creador_tabla_acpi": "MTKID"
        if any("MTKID" in x for x in lineas[:60])
        else "NOT_COLLECTED",
        "palabra_en_0x14": palabras[1] if len(palabras) > 1 else "NOT_COLLECTED",
        "volcado_hex": {k: " ".join(v) for k, v in list(volcado.items())[:4]},
        "misma_clase_que_cita_el_personal_de_nvidia": guid == GUID_MTKID,
    }


def recoge(boots: list[dict[str, Any]], i: int) -> dict[str, Any]:
    """Evidencia del boot boots[i]; el boot siguiente (i+1) aporta BERT y hueco."""
    b = boots[i]
    no_leido: list[str] = []
    r = _journal("-b", str(b["index"]), "-o", "short-iso", "-n", "500")
    if r.returncode != 0:
        no_leido.append(f"journal_boot_{b['index']}")
    cola = r.stdout.splitlines()
    cierre = None
    for linea in cola:
        m = CIERRE.search(linea)
        if m:
            cierre = m.group(1)
    fin = b["last_entry"] / 1e6
    ventana = [ln for ln in cola if COLAPSO.search(ln)]
    # la linea mas reciente con COLAPSO debe caer dentro de la ventana final
    colapso = False
    if ventana:
        m = re.match(r"(\d{4}-\d\d-\d\dT[\d:]+[-+]\d\d:\d\d)", ventana[-1])
        if m:
            colapso = (
                fin - datetime.fromisoformat(m.group(1)).timestamp()
                <= VENTANA_COLAPSO_S
            )
    p = _journal(
        "-b", str(b["index"]), "-k", "--grep", "Kernel panic - not syncing", "-n", "1"
    )
    ev: dict[str, Any] = {
        "boot_id": b["boot_id"],
        "fin_epoch": fin,
        "cierre": cierre,
        "journal_parado": any(JOURNAL_PARADO.search(ln) for ln in cola),
        "disparador": _disparador_boot(b["index"]) if cierre else None,
        "colapso_en_ventana": colapso,
        "panic": p.returncode == 0 and "Kernel panic" in p.stdout,
        "telemetria": _ultima_telemetria(b["boot_id"]),
        "no_se_pudo_leer": no_leido,
    }
    if ev["telemetria"] is None:
        ev["no_se_pudo_leer"].append("telemetria_gpu (no existe para este boot)")
    if i + 1 < len(boots):
        sig = boots[i + 1]
        ev["hueco_s"] = round(sig["first_entry"] / 1e6 - fin)
        k = _journal(
            "-b",
            str(sig["index"]),
            "-k",
            "--grep",
            "BERT: Error records from previous boot",
            "-n",
            "1",
        )
        ev["bert_siguiente"] = k.returncode == 0 and "BERT:" in k.stdout
        ev["bert"] = bert_registro(sig["index"])
        if (
            i + 1 == len(boots) - 1
        ):  # el boot siguiente es el vivo: su bootstatus es el del reset que lo inicio
            try:
                ev["bootstatus_siguiente"] = int(WATCHDOG_BOOTSTATUS.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                ev["no_se_pudo_leer"].append("watchdog_bootstatus")
    return ev


def _ya_escritos() -> set[str]:
    if not SALIDA.exists():
        return set()
    return {
        json.loads(ln)["boot_id"]
        for ln in SALIDA.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    }


def _publica_hallazgos(filas: list[dict[str, Any]]) -> None:
    """Una nota por boot terminado en la bandeja de hallazgos; Atlas la recoge con su propio flujo. Un fallo
    al publicar se dice en stderr y NO tumba el registro del veredicto, que ya quedo escrito."""
    nodo = hallazgo.nodo_anonimo()
    for f in filas:
        try:
            texto = hallazgo.desde_veredicto(
                f,
                nodo=nodo,
                generado=f["_generado"],
                datos=f"reboots.jsonl#{f['boot_id']}",
            )
            ruta, estado = hallazgo.publica(texto)
            print(f"# hallazgo {estado}: {ruta.name}", file=sys.stderr)
        except (ValueError, FileExistsError, OSError) as e:
            print(f"COULD_NOT_PUBLISH {f['boot_id'][:8]}: {e}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--ultimos", type=int, default=10, help="cuantos boots terminados revisar"
    )
    ap.add_argument(
        "--escribe", action="store_true", help="agrega las filas a reboots.jsonl"
    )
    a = ap.parse_args(argv)
    r = _journal("--list-boots", "-o", "json")
    if r.returncode != 0:
        print(
            f"COULD_NOT_RUN: journalctl --list-boots fallo: {r.stderr.strip()}",
            file=sys.stderr,
        )
        return 2
    boots = json.loads(r.stdout)
    filas = []
    ya = _ya_escritos() if a.escribe else set()
    for i in range(
        max(0, len(boots) - 1 - a.ultimos), len(boots) - 1
    ):  # el ultimo sigue vivo
        if boots[i]["boot_id"] in ya:
            continue
        ev = recoge(boots, i)
        fila = {
            "boot_idx": boots[i]["index"],
            "boot_id": boots[i]["boot_id"],
            **veredicto(ev),
        }
        fila["_generado"] = (
            datetime.fromtimestamp(ev["fin_epoch"], tz=timezone.utc)
            .astimezone()
            .isoformat(timespec="seconds")
        )
        filas.append(fila)
        print(
            json.dumps(
                {k: v for k, v in fila.items() if k != "_generado"}, ensure_ascii=False
            )
        )
    if a.escribe:
        SALIDA.parent.mkdir(parents=True, exist_ok=True)
        with SALIDA.open("a", encoding="utf-8") as fh:
            fh.writelines(
                json.dumps(
                    {k: v for k, v in f.items() if k != "_generado"}, ensure_ascii=False
                )
                + "\n"
                for f in filas
            )
        _publica_hallazgos(filas)
    sin_leer = sum(1 for f in filas if f["could_not_run"])
    print(f"# {len(filas)} boots; con could_not_run: {sin_leer}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
