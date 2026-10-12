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

Forense por boot (esquema `bb-reboot/1`, 2026-10-11): la medicion que hacia
`Atlas/tools/detect_atom_crash.py` vive aqui (DEBT-CONTRATO-ATLAS-INSTRUMENTOS-
EN-BLACKBOX-01, enmienda del 2026-10-11 a la SPEC). Cada fila lleva, ademas del
veredicto: la linea de journald del arranque siguiente que declara el journal
corrupto, la linea literal de panic, el `Shutting down.` de PID 1, las lineas
de kernel con los patrones del diagnostico manual del 2026-08-31, los Xid con
su pid, el vmcore de kdump que cae en el hueco del corte, la duracion del boot
y SMART/EDAC en mejor esfuerzo. Atlas lee estas filas y redacta su dictamen;
no mide. `crash_confirmado` usa el MISMO criterio que Atlas usaba (journal
corrupto o panic): el veredicto de bb y el dictamen de Atlas son dos lecturas
distintas y ninguna reemplaza a la otra.
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
ESQUEMA = "bb-reboot/1"
CRASH_DIR = Path("/var/crash")
EDAC_DIR = Path("/sys/devices/system/edac/mc")
DISPOSITIVO_NVME = "/dev/nvme0n1"  # medido con `lsblk`: SAMSUNG MZALC4T0HBL1, 3.7T
# journald lo escribe al arrancar el boot SIGUIENTE (codigo C de systemd, en ingles siempre).
PATRON_UNCLEAN = re.compile(
    r"File (\S+) corrupted or uncleanly shut down, renaming and replacing"
)
# Los patrones del diagnostico manual del 2026-08-31, tal cual los calibro Atlas: `thermal`,
# `watchdog`, `nmi` y `panic` pelados casan lineas de registro de TODO boot normal.
PATRONES_DIAGNOSTICO = re.compile(
    r"oom|killed process|kernel panic|nvrm.*xid|hung task|nmi watchdog:|"
    r"throttl|critical temp|hogged cpu|out of memory|"
    r"gpu has fallen off the bus|xid\s*(?:\([^)]*\))?\s*:?\s*\d+",
    re.IGNORECASE,
)
# `NVRM: Xid (PCI:000f:01:00): 13, ...`: el numero va DESPUES del parentesis; `Xid\s+\d+` casa
# 0 de las 145 lineas reales de la rafaga del 2026-08-30 (medido en Atlas, DGX-336).
PATRON_XID = re.compile(r"\bXid\s*(?:\([^)]*\))?\s*:?\s*(\d+)")
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


def xids_del_boot(lineas: list[str]) -> list[dict[str, Any]]:
    """Cada linea `Xid NN` con su numero y su pid cuando lo trae. Se conserva cada una: la rafaga
    del 2026-08-30 fueron 144 `Xid 13` y UN `Xid 43`, y esa asimetria es el dato."""
    encontrados = []
    for linea in lineas:
        m = PATRON_XID.search(linea)
        if not m:
            continue
        pid = re.search(r"\bpid=(\d+)", linea)
        encontrados.append(
            {
                "xid": int(m.group(1)),
                "pid": int(pid.group(1)) if pid else None,
                "linea_cruda": linea,
            }
        )
    return encontrados


def _iso(epoch: float | None) -> str:
    if not epoch:
        return ""
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def forense(ev: dict[str, Any]) -> dict[str, Any]:
    """Campos forenses de la fila, a partir de evidencia ya leida (pura, como `veredicto`).

    `crash_confirmado` es el criterio que Atlas usaba para su historial de duraciones: journal
    corrupto declarado por journald o panic literal. Un boot sin ninguna de las dos y sin
    `Shutting down.` de PID 1 NO es limpio: sale `crash_confirmado: false` y `cierre_pid1: false`,
    y quien lea la fila decide (Atlas lo rotula `sin_senal`)."""
    lineas = ev.get("lineas_diagnostico") or []
    inicio, fin = ev.get("inicio_epoch"), ev.get("fin_epoch")
    return {
        "esquema": ESQUEMA,
        "hora_inicio": _iso(inicio),
        "hora_fin_registrada": _iso(fin),
        "duracion_s": round(fin - inicio, 3) if inicio and fin else None,
        "journal_danado": ev.get("journal_danado"),
        "panic_linea": ev.get("panic_linea"),
        "cierre_pid1": ev.get("cierre_pid1"),
        "crash_confirmado": bool(ev.get("journal_danado") or ev.get("panic_linea")),
        "lineas_diagnostico": lineas,
        "xids": xids_del_boot(lineas),
        "vmcore": ev.get("vmcore"),
    }


# ---------------------------------------------------------------- colectores
def vmcore_en(desde: float, hasta: float | None) -> str | None:
    """Directorio de kdump con `dump.*` cuyo mtime cae en el hueco del corte [desde, hasta].

    kdump-tools escribe `/var/crash/<fecha>/dump.*`; `kexec_cmd`, `kdump_lock` y los `.crash` de
    apport NO son un volcado (medido en Atlas el 2026-08-31: el primer detector devolvio
    `kexec_cmd` como si lo fuera). Atlas tomaba el volcado MAS NUEVO sin mirar la hora, asi que un
    vmcore viejo se atribuia a cualquier crash posterior; aqui solo cuenta el escrito entre el
    ultimo registro del boot caido y el primero del siguiente, que es cuando corre el kernel de
    kdump."""
    if not CRASH_DIR.is_dir():
        return None
    candidatos = [
        p
        for p in CRASH_DIR.glob("*")
        if p.is_dir()
        and list(p.glob("dump.*"))
        and desde <= p.stat().st_mtime <= (hasta if hasta is not None else float("inf"))
    ]
    if not candidatos:
        return None
    return str(max(candidatos, key=lambda p: p.stat().st_mtime))


def _correr_con_codigo(*args: str) -> tuple[int, str]:
    """El codigo y stderr son el dato: sin ellos 'disco sano' y 'no pude preguntar' se confunden."""
    try:
        p = subprocess.run(
            list(args), capture_output=True, text=True, timeout=60, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return -1, str(exc)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _edac() -> dict[str, Any]:
    """Contadores EDAC. Medido el 2026-08-31: el directorio existe SIN `mc0`; omitir el campo se
    leeria como 'cero errores'."""
    if not EDAC_DIR.is_dir():
        return {"edac_no_disponible": f"{EDAC_DIR} no existe"}
    controladores = sorted(EDAC_DIR.glob("mc[0-9]*"))
    if not controladores:
        return {"edac_no_disponible": f"sin controladores registrados en {EDAC_DIR}"}
    conteos: dict[str, Any] = {}
    for mc in controladores:
        for campo in ("ce_count", "ue_count"):
            try:
                conteos[f"{mc.name}_{campo}"] = int(
                    (mc / campo).read_text(encoding="utf-8").strip()
                )
            except (OSError, ValueError) as exc:
                print(
                    f"_edac: {mc / campo} ilegible ({exc}): contador ausente, no cero",
                    file=sys.stderr,
                )
                conteos[f"{mc.name}_{campo}"] = f"ilegible: {exc}"
    return {"edac": conteos}


def salud_de_almacenamiento(dispositivo: str = DISPOSITIVO_NVME) -> dict[str, Any]:
    """SMART del NVMe y EDAC, foto al registrar (no serie: smartctl cada 5 s despertaria el disco
    17,280 veces al dia). Nunca escala privilegios: un servicio `--user` recibe `Permission denied`
    (medido el 2026-08-31) y eso se escribe como `smart_no_disponible`, no se omite. El codigo de
    smartctl es un mapa de bits que convive con una lectura buena: decide la presencia de datos."""
    codigo, salida = _correr_con_codigo("smartctl", "-H", "-A", dispositivo)
    if codigo == -1:
        r: dict[str, Any] = {"smart_no_disponible": f"smartctl no ejecutable: {salida}"}
    elif "permission denied" in salida.lower():
        r = {"smart_no_disponible": "permiso denegado, requiere root"}
    else:
        utiles = [
            ln
            for ln in salida.splitlines()
            if ln.strip() and not ln.startswith(("smartctl ", "Copyright ("))
        ]
        if any("SMART" in ln for ln in utiles):
            r = {"smart_codigo_salida": codigo, "smart": utiles}
        else:
            r = {
                "smart_no_disponible": f"salida sin datos SMART (codigo {codigo}): "
                f"{' | '.join(utiles[:2]) or 'vacia'}"
            }
    return {**r, **_edac(), "leido_en": datetime.now(timezone.utc).isoformat()}


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


def _evidencia_forense(
    b: dict[str, Any], sig: dict[str, Any] | None, no_leido: list[str]
) -> dict[str, Any]:
    """Lo que Atlas/detect_atom_crash media hasta el 2026-10-11: kernel del boot caido, PID 1, y
    la linea de journald y el vmcore que deja el arranque siguiente. Lo ilegible va a `no_leido`."""
    fin = b["last_entry"] / 1e6
    k = _journal("-b", str(b["index"]), "-k")
    if k.returncode != 0:
        no_leido.append(f"journal_kernel_boot_{b['index']}")
    kernel = k.stdout.splitlines()
    # `_PID=1` a proposito: sin el filtro, uvicorn o GNOME Shell tambien escriben "Shutting down."
    # (8 falsos positivos medidos en Atlas el 2026-09-29 sobre el panic de `07db1a8a`).
    p1 = _journal("-b", str(b["index"]), "-o", "cat", "_PID=1")
    if p1.returncode != 0:
        no_leido.append(f"journal_pid1_boot_{b['index']}")
    ev: dict[str, Any] = {
        "inicio_epoch": b["first_entry"] / 1e6,
        "lineas_diagnostico": [ln for ln in kernel if PATRONES_DIAGNOSTICO.search(ln)],
        "panic_linea": next(
            (ln for ln in kernel if "Kernel panic - not syncing" in ln), None
        ),
        "cierre_pid1": "Shutting down." in p1.stdout if p1.returncode == 0 else None,
        "journal_danado": None,
        "vmcore": None,
    }
    if sig is not None:
        jd = _journal(
            "-b", str(sig["index"]), "-o", "cat", "-u", "systemd-journald.service"
        )
        if jd.returncode != 0:
            no_leido.append(f"journal_journald_boot_{sig['index']}")
        m = PATRON_UNCLEAN.search(jd.stdout)
        ev["journal_danado"] = m.group(1) if m else None
        ev["vmcore"] = vmcore_en(fin, sig["first_entry"] / 1e6)
    return ev


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
    sig = boots[i + 1] if i + 1 < len(boots) else None
    ev.update(_evidencia_forense(b, sig, no_leido))
    if sig is not None:
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
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
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
    almacenamiento: dict[str, Any] | None = None  # una foto por corrida, no por fila
    for i in range(
        max(0, len(boots) - 1 - a.ultimos), len(boots) - 1
    ):  # el ultimo sigue vivo
        if boots[i]["boot_id"] in ya:
            continue
        ev = recoge(boots, i)
        if almacenamiento is None:
            almacenamiento = salud_de_almacenamiento()
        fila = {
            "boot_idx": boots[i]["index"],
            "boot_id": boots[i]["boot_id"],
            "boot_id_siguiente": boots[i + 1]["boot_id"],
            **veredicto(ev),
            **forense(ev),
            "almacenamiento": almacenamiento,
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
