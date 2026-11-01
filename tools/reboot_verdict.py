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

Forense por boot (esquema `bb-reboot/1`, 2026-10-11): la medicion que hacia el
detector de crashes de un consumidor externo vive aqui (DEBT-CONTRATO-ATLAS-
INSTRUMENTOS-EN-BLACKBOX-01, enmienda del 2026-10-11 a la SPEC). Cada fila lleva,
ademas del veredicto: la linea de journald del arranque siguiente que declara el
journal corrupto, la linea literal de panic, el `Shutting down.` de PID 1, las
lineas de kernel con los patrones del diagnostico manual del 2026-08-31, los Xid
con su pid, el vmcore de kdump que cae en el hueco del corte, la duracion del boot
y SMART/EDAC en mejor esfuerzo. El consumidor externo lee estas filas y redacta su
dictamen; no mide. `crash_confirmado` usa el MISMO criterio que ese consumidor
usaba (journal corrupto o panic): el veredicto de bb y su dictamen son dos
lecturas distintas y ninguna reemplaza a la otra.

Fuentes fuera del journal (2026-11-01): seis cortes quedaron INDETERMINADOS por
cinco puntos ciegos, y cada uno tiene ahora su lector:
  kdump        con KDUMP_SKIP_VMCORE=1 kdump-tools guarda SOLO `dmesg.<ts>`; se
               busca `dmesg.*` ademas de `dump.*` y se extrae su linea de panic.
  pstore       las copias que `arranque-forense.sh` deja en /var/lib/blackbox/pstore
               y su fila de `arranque.jsonl` (la del arranque SIGUIENTE: el registro
               lo dejo el boot que murio). Una copia identica a otra anterior es un
               registro viejo que nadie borro y no se atribuye.
  externo      `externo/ping.jsonl` (via `observador_ping.ultima_respuesta`),
               `energia.jsonl`, `netconsole.jsonl` y `latido.jsonl` del testigo.
  etapas       /var/lib/blackbox/arranque/etapas.jsonl: hasta que etapa llego cada
               arranque, y los arranques FANTASMA (con etapas o fila de arranque.jsonl
               pero sin boot en `journalctl --list-boots`), que salen como fila propia.
  aliento      el anillo de ultimo aliento (250 ms): hora de muerte y curva termica.
  bootstatus   de los arranques que ya no son el vivo se lee del journal de kernel
               (linea de sbsa_gwdt), no solo de sysfs del arranque vivo.

Compatibilidad: sigue siendo `bb-reboot/1`. Ningun campo cambia de nombre ni de
sentido; `etiqueta` conserva su dominio de valores (lo que dice el journal y el
medidor de voltaje), con una sola correccion: un boot cuyo journal no devolvio
NINGUNA linea sale INDETERMINADO y no CORTE_ABRUPTO (no hay silencio que leer donde
no hubo lectura). La causa que cruza todas las fuentes va en el campo nuevo `causa`
(PANICO_KDUMP, PANICO_PSTORE, PANICO_NETCONSOLE, CORTE_DE_ENERGIA, CUELGUE,
FALLO_DE_ARRANQUE_EN_<ETAPA>, o la etiqueta misma; INDETERMINADO sin evidencia) con
su cita en `causa_fuente`. Las filas de arranques fantasma traen `boot_idx: null` y
`arranque_fantasma: true`; un consumidor que solo espera boots del journal las
distingue por ese campo.
"""

from __future__ import annotations

import os
import argparse
import json
from datetime import datetime, timezone
import re
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools import hallazgo, medidor_energia, observador_ping

DATOS = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))
TELEMETRIA = DATOS / "atom_gpu_telemetry.jsonl"
# Lo escriben otros paquetes; aqui solo se leen. Las rutas de root las fija arranque-forense.sh.
PSTORE_DIR = Path("/var/lib/blackbox/pstore")  # copias de /sys/fs/pstore y BERT + arranque.jsonl
ETAPAS = Path("/var/lib/blackbox/arranque/etapas.jsonl")  # {boot_id, etapa, monotonic, realtime}
ANILLO = DATOS / "ultimo_aliento.jsonl"  # {ts, lecturas de PSI, memoria, termica y potencia} cada 250 ms
EXTERNO: Path | None = None  # None: `$BLACKBOX_DATA/externo` leido en cada llamada, como medidor_energia
ETAPAS_ORDEN = ("local-fs", "basic", "network-online", "multi-user", "graphical", "gdm", "gpu-lista", "sesion")
# `sesion` depende de que alguien entre: un boot sin ella no fallo al arrancar.
ETAPA_ARRANQUE_COMPLETO = "gpu-lista"
# Un boot que vivio mas que esto tras su ultima etapa no murio arrancando: una etapa ausente
# ahi es un escritor que fallo, no un arranque que fallo.
VENTANA_FALLO_ARRANQUE_S = 900.0
SIMULTANEO_S = 1.0  # periodo de muestreo del ping y del enchufe: caer en la misma muestra es caer a la vez
SEGUIDO_S = 10.0  # hueco maximo entre filas para decir que el observador cubrio la caida
CURVA_TERMICA_S = 60
WDIOF_CARDRESET = 0x20  # include/uapi/linux/watchdog.h
# drivers/watchdog/sbsa_gwdt.c escribe esto al probar si WCS.WS1 esta encendido; texto del driver,
# NO visto todavia en el journal de esta maquina.
WDT_RESET = re.compile(r"System reset by WDT")
WDT_PROBE = re.compile(r"sbsa[-_]gwdt.*Initialized with")
PANIC_TEXTO = "Kernel panic - not syncing"
LEE_MAX_BYTES = 4 * 1024 * 1024
SALIDA = DATOS / "reboots.jsonl"
WATCHDOG_BOOTSTATUS = Path("/sys/class/watchdog/watchdog0/bootstatus")
VENTANA_COLAPSO_S = 900
PSI_FULL_COLAPSO = 10.0
# Clase de registro BERT que el personal de NVIDIA cita (hilo 384436), segun el catalogo de un consumidor externo
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
# Los patrones del diagnostico manual del 2026-08-31, tal cual los calibro el consumidor externo: `thermal`,
# `watchdog`, `nmi` y `panic` pelados casan lineas de registro de TODO boot normal.
PATRONES_DIAGNOSTICO = re.compile(
    r"oom|killed process|kernel panic|nvrm.*xid|hung task|nmi watchdog:|"
    r"throttl|critical temp|hogged cpu|out of memory|"
    r"gpu has fallen off the bus|xid\s*(?:\([^)]*\))?\s*:?\s*\d+",
    re.IGNORECASE,
)
# `NVRM: Xid (PCI:000f:01:00): 13, ...`: el numero va DESPUES del parentesis; `Xid\s+\d+` casa
# 0 de las 145 lineas reales de la rafaga del 2026-08-30 (medido por el consumidor externo).
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


def _sin_journal(ev: dict[str, Any]) -> bool:
    """Arranque fantasma o journal que no devolvio ni una linea: no hay silencio que leer."""
    return bool(ev.get("fantasma") or ev.get("cola_journal_vacia"))


def _causa_interna(ev: dict[str, Any]) -> tuple[str, str, str] | None:
    """(causa, fuente, razon) de un panic que el journal no guardo: kdump, pstore o netconsole."""
    k = ev.get("kdump") or {}
    if k.get("directorio"):
        if k.get("linea_panico"):
            return "PANICO_KDUMP", k["fuente_panico"], f"kdump guardo el dmesg del panic: {k['linea_panico']}"
        return (
            "PANICO_KDUMP",
            k["directorio"],
            "el kernel de kdump corrio en el hueco del corte (solo arranca tras un panic); "
            + (
                f"su rastro no se pudo leer ({'; '.join(k['ilegibles'])}): la linea de panic no consta"
                if k.get("ilegibles")
                else f"su dmesg no trae '{PANIC_TEXTO}'"
            ),
        )
    p = ev.get("pstore") or {}
    if p.get("linea_panico"):
        return "PANICO_PSTORE", p["fuente_panico"], f"pstore guardo el panic: {p['linea_panico']}"
    n = ev.get("netconsole") or {}
    if n.get("linea_panico"):
        return "PANICO_NETCONSOLE", n["fuente_panico"], f"netconsole recibio el panic fuera del host: {n['linea_panico']}"
    return None


def _causa_por_tiempos(t: dict[str, Any]) -> tuple[str, str, str] | None:
    """CORTE_DE_ENERGIA o CUELGUE comparando cuando cayo el TCP y que hizo el enchufe. Sin una
    falla de ping que cierre la ultima respuesta (el observador vivo y cubriendo) no concluye."""
    ping, enc = t.get("ping") or {}, t.get("enchufe") or {}
    u, f = ping.get("ultima_respuesta"), ping.get("primera_falla")
    if u is None or f is None or f - u > SEGUIDO_S:
        return None
    eu, ef = enc.get("ultima_ok"), enc.get("primera_falla")
    if eu is not None and ef is not None and eu >= u - SIMULTANEO_S and ef <= f + SIMULTANEO_S:
        return (
            "CORTE_DE_ENERGIA",
            f"{enc['fuente']}:{enc['linea_falla']} + {ping['fuente']} (ultima respuesta {u}, primera falla {f})",
            f"el enchufe cayo (ultima lectura {eu}, primera falla {ef}) antes o a la vez que el TCP "
            f"(ultima respuesta {u}, primera falla {f}): se fue la energia",
        )
    tras = enc.get("tras_caida_tcp") or []
    if tras and all(
        r.get("ok") is True
        and isinstance(r.get("voltaje_v"), (int, float))
        and isinstance(r.get("potencia_w"), (int, float))
        and r["voltaje_v"] >= medidor_energia.VOLTAJE_NORMAL_V
        and r["potencia_w"] >= medidor_energia.CARGA_W
        for r in tras
    ):
        return (
            "CUELGUE",
            f"{ping['fuente']} (primera falla {f}) + {enc['fuente']} ({len(tras)} lecturas con consumo despues)",
            f"el TCP cayo en {f} y el enchufe siguio midiendo consumo (>= {medidor_energia.CARGA_W:g} W): "
            "la maquina quedo energizada sin responder (cuelgue, o panic que no dejo rastro)",
        )
    return None


def _causa_por_etapas(ev: dict[str, Any]) -> tuple[str, str, str] | None:
    """FALLO_DE_ARRANQUE_EN_<etapa> si murio sin completar el arranque y poco despues de su ultima etapa."""
    et = ev.get("etapas") or {}
    if not et.get("maxima") or not et.get("faltante") or et.get("ultima_epoch") is None:
        return None
    vivio = None if ev.get("fantasma") else (ev.get("fin_epoch") or 0) - et["ultima_epoch"]
    if vivio is not None and vivio > VENTANA_FALLO_ARRANQUE_S:
        return None
    falta = et["faltante"]
    return (
        f"FALLO_DE_ARRANQUE_EN_{falta.upper().replace('-', '_')}",
        f"{et['fuente']} (ultima etapa '{et['maxima']}')",
        f"el arranque llego hasta '{et['maxima']}' y nunca a '{falta}'",
    )


def _refina(ev: dict[str, Any]) -> tuple[str, str, str] | None:
    """La causa que el journal no ve, en orden de prueba: un panic registrado fuera del journal, el
    voltaje medido, la secuencia TCP/enchufe y, solo despues, donde se quedo el arranque."""
    externo = ev.get("externo") or {}
    medidor = f"externo/energia.jsonl ({externo.get('motivo')})"
    interna = _causa_interna(ev)
    if interna:
        return interna
    if externo.get("voltaje_perdido") is True:
        return "CORTE_DE_RED", medidor, "el medidor externo registro perdida de voltaje"
    tiempos = _causa_por_tiempos(ev.get("tiempos_externos") or {})
    if tiempos:
        return tiempos
    if externo.get("voltaje_perdido") is False:
        return "APAGADO_INTERNO", medidor, "el medidor externo registro voltaje presente mientras la maquina murio"
    return _causa_por_etapas(ev)


def _corte_abrupto(
    ev: dict[str, Any], psi_full: float | None, no_corrio: list[str]
) -> tuple[str, list[str]]:
    """Journal mudo sin cierre, colapso ni panic: solo un observador externo puede decir mas."""
    if ev.get("fantasma"):
        razones = [f"arranque fantasma: no esta en `journalctl --list-boots`; lo atestigua {ev.get('fantasma_fuente')}"]
    elif ev.get("cola_journal_vacia"):
        razones = ["el journal del boot no devolvio ninguna linea: no hay silencio que leer"]
    else:
        razones = ["el journal calla sin cierre, sin colapso de memoria y sin panic"]
    base = "INDETERMINADO" if _sin_journal(ev) else "CORTE_ABRUPTO"
    if psi_full is not None:
        razones.append(
            f"PSI full avg10={psi_full} en la ultima muestra: no fue memoria"
        )
    externo = ev.get("externo")
    if externo is None:
        if not (ev.get("tiempos_externos") or {}).get("filas"):
            razones.append(
                "causa INDETERMINADA (energia vs hardware interno): falta observador externo"
            )
            no_corrio.append("observador_externo")
        return base, razones
    if externo.get("voltaje_perdido") is True:
        razones.append("el medidor externo registro perdida de voltaje")
        return "CORTE_DE_RED", razones
    if externo.get("voltaje_perdido") is False:
        razones.append(
            "el medidor externo registro voltaje presente mientras la maquina murio"
        )
        return "APAGADO_INTERNO", razones
    return base, razones


def veredicto(ev: dict[str, Any]) -> dict[str, Any]:
    """Clasifica un boot. `ev` trae solo evidencia ya leida; esta funcion no lee
    nada, para que cada rama tenga un caso que la active y otro que no."""
    razones: list[str] = []
    no_corrio: list[str] = list(ev.get("no_se_pudo_leer", []))
    tele = ev.get("telemetria") or {}
    psi_full = tele.get("psi_mem_full_avg10")

    fuente: str | None = None
    refinada: tuple[str, str, str] | None = None
    if ev.get("panic"):
        etiqueta = "PANIC_KERNEL"
        fuente = f"journal de kernel del boot: {ev.get('panic_linea') or PANIC_TEXTO}"
        razones.append("el journal del boot trae 'Kernel panic - not syncing'")
    elif ev.get("colapso_en_ventana") or (
        psi_full is not None and psi_full >= PSI_FULL_COLAPSO
    ):
        etiqueta = "COLAPSO_MEMORIA"
        fuente = (
            "journal del boot: [bb-usable] COLAPSO"
            if ev.get("colapso_en_ventana")
            else f"{TELEMETRIA.name}: psi_mem_full_avg10={psi_full}"
        )
        razones.append(
            f"bb-usable COLAPSO en los ultimos {VENTANA_COLAPSO_S}s"
            if ev.get("colapso_en_ventana")
            else f"ultima muestra con PSI full avg10={psi_full} >= {PSI_FULL_COLAPSO}"
        )
    elif ev.get("cierre"):
        etiqueta = f"CIERRE_ORDENADO_{str(ev['cierre']).upper()}"
        fuente = f"journal del boot: Reached target {ev['cierre']}.target"
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
        refinada = _refina(ev)
    else:
        etiqueta, extra = _corte_abrupto(ev, psi_full, no_corrio)
        razones.extend(extra)
        refinada = _refina(ev)
        if refinada:
            # la causa salio de otra fuente: la frase de "falta observador" ya no describe la fila
            razones = [r for r in razones if not r.startswith("causa INDETERMINADA")]

    if etiqueta.startswith(("PANIC_", "COLAPSO_", "CIERRE_ORDENADO_")):
        causa = etiqueta  # el journal (o la telemetria) ya la nombra con su fuente
    else:
        # sin cierre ni panic en el journal: la causa es la de otra fuente o no hay causa
        causa = refinada[0] if refinada else "INDETERMINADO"
        fuente = refinada[1] if refinada else None
        if refinada and refinada[0] != etiqueta:  # la del medidor ya esta en las razones
            razones.append(refinada[2])
    et = ev.get("etapas") or {}
    if et.get("maxima"):
        razones.append(
            f"etapas de arranque: hasta '{et['maxima']}'"
            + (f", sin '{et['faltante']}'" if et.get("faltante") else ", arranque completo")
        )
    if str((ev.get("bert") or {}).get("estado", "")).startswith("no atribuido"):
        razones.append(f"BERT y bootstatus del arranque siguiente {ev['bert']['estado']}: son de ese arranque, no de este")
    latido = (ev.get("tiempos_externos") or {}).get("latido") or {}
    if latido and not latido.get("en_el_hueco"):
        razones.append(
            f"el testigo externo callo junto con la ATOM (ultimo latido {latido.get('ultimo_hasta_la_muerte')}): "
            "lo que no registro en el hueco no es prueba de nada"
        )
    if ev.get("bootstatus_siguiente") not in (None, 0):
        razones.append(
            f"watchdog bootstatus={ev['bootstatus_siguiente']} en el arranque siguiente"
            + (f" ({ev['bootstatus_fuente']})" if ev.get("bootstatus_fuente") else "")
        )
    return {
        "etiqueta": etiqueta,
        "causa": causa,
        "causa_fuente": fuente,
        "watchdog_bootstatus_siguiente": ev.get("bootstatus_siguiente"),
        "watchdog_bootstatus_fuente": ev.get("bootstatus_fuente"),
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

    `crash_confirmado` es el criterio que el consumidor externo usaba para su historial de duraciones: journal
    corrupto declarado por journald o panic literal. Un boot sin ninguna de las dos y sin
    `Shutting down.` de PID 1 NO es limpio: sale `crash_confirmado: false` y `cierre_pid1: false`,
    y quien lea la fila decide (el consumidor externo lo rotula `sin_senal`)."""
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
        "arranque_fantasma": bool(ev.get("fantasma")),
        "kdump": ev.get("kdump"),
        "pstore": ev.get("pstore"),
        "etapas": ev.get("etapas"),
        "netconsole": ev.get("netconsole"),
        "tiempos_externos": ev.get("tiempos_externos"),
        "ultimo_aliento": (ev.get("aliento") or {}).get("ultima_lectura"),
        "curva_termica_previa": (ev.get("aliento") or {}).get("curva_termica"),
        "hora_muerte": hora_muerte(ev),
    }


def hora_muerte(ev: dict[str, Any]) -> dict[str, Any] | None:
    """Ultima senal de vida del boot (la mas tardia entre journal, etapas, ping, netconsole y el
    anillo de 250 ms) y la primera prueba de muerte (falla de ping o arranque siguiente). La muerte
    cae entre las dos; ninguna fuente sola la fecha, y se dice cual dio cada borde."""
    t = ev.get("tiempos_externos") or {}
    senales = {
        # `last_entry` de --list-boots es real aunque la cola no se haya podido leer; un fantasma no lo tiene
        "journal": None if ev.get("fantasma") else ev.get("fin_epoch"),
        "etapas": (ev.get("etapas") or {}).get("ultima_epoch"),
        "ping": (t.get("ping") or {}).get("ultima_respuesta"),
        "netconsole": (ev.get("netconsole") or {}).get("ultima_epoch"),
        "anillo": (ev.get("aliento") or {}).get("ultima_epoch"),
    }
    vivas = {k: v for k, v in senales.items() if isinstance(v, (int, float))}
    if not vivas:
        return None
    fuente = max(vivas, key=lambda k: vivas[k])
    ultima = vivas[fuente]
    cotas = {
        "ping": (t.get("ping") or {}).get("primera_falla"),
        "arranque_siguiente": ev.get("siguiente_inicio_epoch"),
    }
    cotas = {k: v for k, v in cotas.items() if isinstance(v, (int, float)) and v >= ultima}
    techo = min(cotas, key=lambda k: cotas[k]) if cotas else None
    return {
        "ultima_senal_epoch": ultima,
        "ultima_senal_iso": _iso(ultima),
        "fuente": fuente,
        "cota_superior_epoch": cotas[techo] if techo else None,
        "cota_superior_fuente": techo,
        "incertidumbre_s": round(cotas[techo] - ultima, 3) if techo else None,
        "periodo_anillo_s": (ev.get("aliento") or {}).get("periodo_s") if fuente == "anillo" else None,
        "senales": vivas,
    }


# ---------------------------------------------------------------- colectores
def vmcore_en(desde: float, hasta: float | None) -> str | None:
    """Directorio de kdump con `dump.*` cuyo mtime cae en el hueco del corte [desde, hasta].

    kdump-tools escribe `/var/crash/<fecha>/dump.*`; `kexec_cmd`, `kdump_lock` y los `.crash` de
    apport NO son un volcado (medido por el consumidor externo el 2026-08-31: el primer detector devolvio
    `kexec_cmd` como si lo fuera). El consumidor externo tomaba el volcado MAS NUEVO sin mirar la hora, asi que un
    vmcore viejo se atribuia a cualquier crash posterior; aqui solo cuenta el escrito entre el
    ultimo registro del boot caido y el primero del siguiente, que es cuando corre el kernel de
    kdump."""
    candidatos = [p for p in _crash_en_ventana(desde, hasta) if list(p.glob("dump.*"))]
    if not candidatos:
        return None
    return str(max(candidatos, key=lambda p: p.stat().st_mtime))


def _crash_en_ventana(desde: float, hasta: float | None) -> list[Path]:
    if not CRASH_DIR.is_dir():
        return []
    tope = hasta if hasta is not None else float("inf")
    return [p for p in CRASH_DIR.glob("*") if p.is_dir() and desde <= p.stat().st_mtime <= tope]


def _linea_panico(ruta: Path) -> tuple[int, str] | None:
    """(numero de linea, linea) del primer 'Kernel panic - not syncing' del archivo; None si no lo trae.
    Un archivo ilegible levanta OSError: "no se pudo leer" no es "no trae panic"."""
    with ruta.open("rb") as fh:
        texto = fh.read(LEE_MAX_BYTES).decode("utf-8", errors="replace")
    for n, ln in enumerate(texto.splitlines(), 1):
        if PANIC_TEXTO in ln:
            return n, ln.strip()[:300]
    return None


def kdump_en(desde: float, hasta: float | None) -> dict[str, Any] | None:
    """Rastro de kdump en el hueco del corte, haya o no vmcore. Con `KDUMP_SKIP_VMCORE=1`
    (adopted/system-config/etc_default_kdump-tools) kdump-tools guarda SOLO
    `/var/crash/<ts>/dmesg.<ts>`: buscar unicamente `dump.*` daba "ninguno" por construccion.
    La misma regla de hora que `vmcore_en`: un directorio viejo no se atribuye a un corte nuevo."""
    candidatos: list[tuple[Path, list[Path], list[str]]] = []
    for d in _crash_en_ventana(desde, hasta):
        if not os.access(d, os.R_OK | os.X_OK):
            # kdump-tools es el unico que crea directorios en /var/crash: que exista en el hueco ya es el dato
            candidatos.append((d, [], [f"{d}: sin permiso para listarlo"]))
            continue
        archivos = sorted(d.glob("dmesg.*")) + sorted(d.glob("dump.*"))
        if archivos:
            candidatos.append((d, archivos, []))
    if not candidatos:
        return None
    d, archivos, ilegibles = max(candidatos, key=lambda c: c[0].stat().st_mtime)
    r: dict[str, Any] = {
        "directorio": str(d),
        "archivos": [a.name for a in archivos],
        "vmcore": any(a.name.startswith("dump.") for a in archivos),
        "linea_panico": None,
        "fuente_panico": None,
        "ilegibles": ilegibles,
    }
    for a in (x for x in archivos if x.name.startswith("dmesg.")):
        try:
            hallado = _linea_panico(a)
        except OSError as e:
            r["ilegibles"].append(f"{a}: {e.strerror or e}")
            continue
        if hallado:
            r["linea_panico"], r["fuente_panico"] = hallado[1], f"{a}:{hallado[0]}"
            break
    return r


def _norm(boot_id: str) -> str:
    return str(boot_id).replace("-", "").lower()


def _epoch(valor: Any) -> float | None:
    """Segundos epoch de un numero (microsegundos si pasa de 1e12, como `__REALTIME_TIMESTAMP`) o
    de un ISO 8601 CON zona; None para todo lo demas (una hora sin zona no se adivina)."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor) / 1e6 if valor > 1e12 else float(valor)
    if isinstance(valor, str):
        try:
            d = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        except ValueError:
            return None
        return d.timestamp() if d.tzinfo is not None else None
    return None


def _jsonl(ruta: Path) -> list[tuple[int, dict[str, Any]]] | None:
    """(numero de linea, fila) de cada objeto JSON; None si el archivo no se pudo leer (ausente no es vacio)."""
    try:
        lineas = ruta.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    out = []
    for n, ln in enumerate(lineas, 1):
        try:
            f = json.loads(ln)
        except ValueError:
            continue
        if isinstance(f, dict):
            out.append((n, f))
    return out


def _fila_arranque(filas: list[tuple[int, dict[str, Any]]], boot_id: str | None) -> dict[str, Any] | None:
    for n, f in filas:
        if boot_id and isinstance(f.get("boot_id"), str) and _norm(f["boot_id"]) == _norm(boot_id):
            return {**f, "linea_jsonl": n}
    return None


def pstore_de(boot_id_siguiente: str, boot_id: str | None = None) -> dict[str, Any] | None:
    """Lo que `arranque-forense.sh` copio de /sys/fs/pstore al arrancar `boot_id_siguiente` (el
    registro lo dejo el boot que murio antes) y las filas de `arranque.jsonl` de los dos arranques.
    Las copias se llaman `<boot_id>-<nombre>`; una copia identica a otra MAS VIEJA del mismo nombre
    es un registro que nadie borro de pstore y no se atribuye a este corte. None sin el directorio."""
    try:
        entradas = sorted(PSTORE_DIR.iterdir())
    except OSError:
        return None
    filas = _jsonl(PSTORE_DIR / "arranque.jsonl") or []
    propios, todos = [], []
    for p in entradas:
        n = p.name
        if not p.is_file() or len(n) < 38 or n[36] != "-" or len(_norm(n[:36])) != 32:
            continue
        todos.append(p)
        if _norm(n[:36]) == _norm(boot_id_siguiente):
            propios.append(p)
    r: dict[str, Any] = {
        "fila_arranque_siguiente": _fila_arranque(filas, boot_id_siguiente),
        "fila_arranque_propia": _fila_arranque(filas, boot_id),
        "archivos": [p.name for p in propios],
        "repetidos": [],
        "linea_panico": None,
        "fuente_panico": None,
        "ilegibles": [],
    }
    for p in propios:
        if p.name.endswith("-BERT.bin"):
            continue  # tabla ACPI binaria: la decodifica bert_registro desde el journal
        try:
            dato = p.read_bytes()
            repetido = any(
                q.name[37:] == p.name[37:] and q.stat().st_mtime < p.stat().st_mtime and q.read_bytes() == dato
                for q in todos
                if q != p
            )
            hallado = None if repetido else _linea_panico(p)
        except OSError as e:
            r["ilegibles"].append(f"{p.name}: {e.strerror or e}")
            continue
        if repetido:
            r["repetidos"].append(p.name)
            continue
        if hallado and r["linea_panico"] is None:
            r["linea_panico"], r["fuente_panico"] = hallado[1], f"{p}:{hallado[0]}"
    return r


def etapas_de() -> dict[str, dict[str, tuple[float, Any, int]]] | None:
    """boot_id normalizado -> {etapa: (realtime epoch, monotonic tal cual, linea)} de etapas.jsonl,
    con la PRIMERA vez que se registro cada etapa. None si el archivo no se pudo leer."""
    filas = _jsonl(ETAPAS)
    if filas is None:
        return None
    out: dict[str, dict[str, tuple[float, Any, int]]] = {}
    for n, f in filas:
        bid, etapa, t = f.get("boot_id"), f.get("etapa"), _epoch(f.get("realtime"))
        if isinstance(bid, str) and isinstance(etapa, str) and t is not None:
            out.setdefault(_norm(bid), {}).setdefault(etapa, (t, f.get("monotonic"), n))
    return out


def resumen_etapas(vistas: dict[str, tuple[float, Any, int]]) -> dict[str, Any]:
    """Hasta donde llego el arranque. `faltante` es la etapa que sigue a la mas avanzada mientras el
    arranque no llego a ETAPA_ARRANQUE_COMPLETO; una intermedia ausente (network-online sin red) va a
    `saltadas` y no cuenta como fallo, porque el arranque siguio despues de ella."""
    alcanzadas = [e for e in ETAPAS_ORDEN if e in vistas]
    maxima = alcanzadas[-1] if alcanzadas else None
    i = ETAPAS_ORDEN.index(maxima) if maxima else -1
    return {
        "alcanzadas": alcanzadas,
        "maxima": maxima,
        "faltante": ETAPAS_ORDEN[i + 1] if i < ETAPAS_ORDEN.index(ETAPA_ARRANQUE_COMPLETO) else None,
        "saltadas": [e for e in ETAPAS_ORDEN[: max(i, 0)] if e not in vistas],
        "desconocidas": sorted(set(vistas) - set(ETAPAS_ORDEN)),
        "monotonic": {e: vistas[e][1] for e in alcanzadas},
        "ultima_epoch": max(v[0] for v in vistas.values()),
        "fuente": f"{ETAPAS}:{vistas[maxima][2]}" if maxima else str(ETAPAS),
    }


def arranques_fantasma(
    boots: list[dict[str, Any]], etapas: dict[str, dict[str, tuple[float, Any, int]]] | None
) -> list[dict[str, Any]]:
    """Arranques que dejaron etapas o fila en arranque.jsonl pero que `journalctl --list-boots` no
    tiene (murieron antes de que journald volcara a disco, o su journal no se puede leer). Solo los
    que caen dentro del tramo que el journal cubre: uno mas viejo es un journal ya rotado, no un
    fantasma. `inicio_epoch` es la PRIMERA senal registrada, no el arranque del kernel."""
    if not boots:
        return []
    en_journal = {_norm(b["boot_id"]) for b in boots}
    desde, hasta = boots[0]["first_entry"] / 1e6, boots[-1]["first_entry"] / 1e6
    vistos: dict[str, dict[str, Any]] = {}
    for bid, vistas in (etapas or {}).items():
        primera = min(vistas.values(), key=lambda v: v[0])
        vistos[bid] = {
            "boot_id": bid,
            "inicio_epoch": primera[0],
            "fin_epoch": max(v[0] for v in vistas.values()),
            "fuente": f"{ETAPAS}:{primera[2]}",
        }
    for n, f in _jsonl(PSTORE_DIR / "arranque.jsonl") or []:
        t = _epoch(f.get("ts"))
        if not isinstance(f.get("boot_id"), str) or t is None:
            continue
        g = vistos.setdefault(
            _norm(f["boot_id"]),
            {"boot_id": _norm(f["boot_id"]), "inicio_epoch": t, "fin_epoch": t,
             "fuente": f"{PSTORE_DIR / 'arranque.jsonl'}:{n}"},
        )
        g["inicio_epoch"], g["fin_epoch"] = min(g["inicio_epoch"], t), max(g["fin_epoch"], t)
    return sorted(
        (g for bid, g in vistos.items() if bid not in en_journal and desde < g["inicio_epoch"] < hasta),
        key=lambda g: g["inicio_epoch"],
    )


def _externo() -> Path:
    return EXTERNO if EXTERNO is not None else medidor_energia._datos()


def _en_ventana(ruta: Path, desde: float, hasta: float, clave: str = "epoch") -> list[tuple[int, dict[str, Any], float]]:
    """(linea, fila, epoch) de las filas con hora en [desde, hasta], ordenadas por hora."""
    out = []
    for n, f in _jsonl(ruta) or []:
        e = _epoch(f.get(clave))
        if e is not None and desde <= e <= hasta:
            out.append((n, f, e))
    return sorted(out, key=lambda x: x[2])


def _lectura_buena(f: dict[str, Any]) -> bool:
    v = f.get("voltaje_v")
    return f.get("ok") is True and isinstance(v, (int, float)) and v >= medidor_energia.VOLTAJE_CAIDO_V


def tiempos_externos(inicio: float, fin: float, siguiente_inicio: float) -> dict[str, Any]:
    """Cuando dejo de responder la ATOM por TCP y que hacia el enchufe en ese momento, de
    `externo/ping.jsonl` y `externo/energia.jsonl` (los del observador y los del testigo, mismo
    esquema), mas el latido del testigo (`externo/latido.jsonl`: filas con `epoch` o `ts`). Lee y
    resume; la conclusion la saca `_causa_por_tiempos`, que es pura."""
    d = _externo()
    ping, energia, latido = d / "ping.jsonl", d / "energia.jsonl", d / "latido.jsonl"
    u = observador_ping.ultima_respuesta(ping, siguiente_inicio)
    if u is not None and u < inicio:
        u = None  # la ultima respuesta es de un boot anterior: este no tiene cobertura
    f = observador_ping.primera_falla(ping, u, siguiente_inicio) if u is not None else None
    filas_p = _en_ventana(ping, inicio, siguiente_inicio)
    filas_e = _en_ventana(energia, inicio, siguiente_inicio)
    enchufe: dict[str, Any] = {
        "fuente": str(energia), "ultima_ok": None, "primera_falla": None, "linea_falla": None, "tras_caida_tcp": [],
    }
    if u is not None:
        falla = next(((n, e) for n, r, e in filas_e if e > u - SIMULTANEO_S and not _lectura_buena(r)), None)
        if falla:
            enchufe["primera_falla"], enchufe["linea_falla"] = falla[1], falla[0]
            antes = [e for _, r, e in filas_e if e < falla[1] and _lectura_buena(r)]
            enchufe["ultima_ok"] = max(antes) if antes else None
    if f is not None:
        enchufe["tras_caida_tcp"] = [
            {k: r.get(k) for k in ("epoch", "ok", "voltaje_v", "potencia_w")}
            for _, r, e in filas_e
            if f < e <= min(f + SEGUIDO_S, siguiente_inicio)
        ]
    r: dict[str, Any] = {
        "filas": len(filas_p) + len(filas_e),
        "ping": {"fuente": str(ping), "ultima_respuesta": u, "primera_falla": f, "filas_en_ventana": len(filas_p)},
        "enchufe": enchufe,
        "latido": None,
    }
    filas_l = _jsonl(latido)
    if filas_l is not None:
        horas = sorted(e for _, x in filas_l if (e := _epoch(x.get("epoch", x.get("ts")))) is not None)
        muerte = max(fin, u or fin)
        r["latido"] = {
            "fuente": str(latido),
            "ultimo_hasta_la_muerte": max((e for e in horas if e <= muerte), default=None),
            "en_el_hueco": sum(1 for e in horas if muerte < e <= siguiente_inicio),
        }
    return r


def netconsole_en(inicio: float, siguiente_inicio: float) -> dict[str, Any] | None:
    """Lineas de kernel que el receptor de netconsole (`externo/netconsole.jsonl`: `epoch` y el texto
    en `linea`, `mensaje` o `msg`) recibio durante el boot; None si no hay ninguna."""
    ruta = _externo() / "netconsole.jsonl"
    filas = [x for x in _en_ventana(ruta, inicio, siguiente_inicio) if x[2] < siguiente_inicio]
    if not filas:
        return None

    def texto(f: dict[str, Any]) -> str:
        return next((str(f[k]) for k in ("linea", "mensaje", "msg") if isinstance(f.get(k), str)), "")

    panico = next(((n, texto(f)) for n, f, _ in filas if PANIC_TEXTO in texto(f)), None)
    return {
        "lineas_en_ventana": len(filas),
        "ultima_epoch": filas[-1][2],
        "ultima_linea": texto(filas[-1][1])[:300],
        "linea_panico": panico[1].strip()[:300] if panico else None,
        "fuente_panico": f"{ruta}:{panico[0]}" if panico else None,
    }


def _termica(f: dict[str, Any]) -> Any:
    if "termica" in f:
        return f["termica"]
    claves = {k: v for k, v in f.items() if re.search(r"temp|termic", k, re.IGNORECASE)}
    return claves or None


def aliento_en(inicio: float, siguiente_inicio: float) -> dict[str, Any] | None:
    """Ultima fila del anillo de ultimo aliento (250 ms) dentro del boot, su periodo medido y la
    curva termica de los CURVA_TERMICA_S previos, una lectura por segundo. El anillo no lleva
    boot_id: la fila es del boot si su `ts` cae en [inicio, siguiente_inicio). None si no se pudo leer."""
    if _jsonl(ANILLO) is None:
        return None
    filas = [x for x in _en_ventana(ANILLO, inicio, siguiente_inicio, clave="ts") if x[2] < siguiente_inicio]
    if not filas:
        return {"filas_en_ventana": 0, "ultima_epoch": None, "periodo_s": None, "ultima_lectura": None, "curva_termica": None}
    ultima = filas[-1][2]
    pasos = [b[2] - a[2] for a, b in zip(filas[-9:], filas[-8:])]
    curva: dict[int, dict[str, Any]] = {}
    for _, f, e in filas:
        if e >= ultima - CURVA_TERMICA_S and _termica(f) is not None:
            curva[int(e)] = {"epoch": e, "termica": _termica(f)}  # la ultima de cada segundo
    return {
        "filas_en_ventana": len(filas),
        "ultima_epoch": ultima,
        "periodo_s": round(statistics.median(pasos), 3) if pasos else None,
        "ultima_lectura": filas[-1][1],
        "curva_termica": list(curva.values()) or None,
    }


def bootstatus_por_journal(idx: int) -> tuple[int | None, str | None]:
    """bootstatus del watchdog con que arranco el boot `idx`, leido de SU journal de kernel: sysfs
    solo sirve para el arranque vivo. (None, None) si el journal no se lee o sbsa_gwdt no aparece."""
    r = _journal("-b", str(idx), "-k", "-o", "cat")
    if r.returncode != 0:
        return None, None
    lineas = r.stdout.splitlines()
    reset = next((ln for ln in lineas if WDT_RESET.search(ln)), None)
    if reset:
        return WDIOF_CARDRESET, f"journal de kernel del boot {idx}: {reset.strip()[:200]}"
    if any(WDT_PROBE.search(ln) for ln in lineas):
        return 0, f"journal de kernel del boot {idx}: sbsa_gwdt arranco sin 'System reset by WDT'"
    return None, None


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
    b: dict[str, Any], sig: dict[str, Any] | None, no_leido: list[str], hasta: float | None = None
) -> dict[str, Any]:
    """Lo que el detector del consumidor externo media hasta el 2026-10-11: kernel del boot caido, PID 1, y
    la linea de journald y el vmcore que deja el arranque siguiente. Lo ilegible va a `no_leido`."""
    fin = b["last_entry"] / 1e6
    k = _journal("-b", str(b["index"]), "-k")
    if k.returncode != 0:
        no_leido.append(f"journal_kernel_boot_{b['index']}")
    kernel = k.stdout.splitlines()
    # `_PID=1` a proposito: sin el filtro, uvicorn o GNOME Shell tambien escriben "Shutting down."
    # (8 falsos positivos medidos por el consumidor externo el 2026-09-29 sobre el panic de `07db1a8a`).
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
        ev["vmcore"] = vmcore_en(fin, hasta if hasta is not None else sig["first_entry"] / 1e6)
    return ev


def _evidencia_externa(fin: float, hueco_s: float, ruta: Path | None = None) -> tuple[dict[str, Any] | None, str | None]:
    """(externo, no_concluyente): `externo` solo si el medidor mide el corte con voltaje; si hay filas sin conclusion se declara como no leido."""
    ext = medidor_energia.ventana_de_corte(ruta or _externo() / "energia.jsonl", fin, hueco_s)
    if ext is None:
        return None, None
    if ext["voltaje_perdido"] is None:
        return None, f"medidor_externo ({ext['motivo']})"
    return ext, None


def _anade_evidencia_externa(ev: dict[str, Any], fin: float, ruta: Path | None = None) -> None:
    """Pone `ev["externo"]` si el medidor concluye, o declara en `no_se_pudo_leer` que hubo filas sin conclusion."""
    externo, no_concluyente = _evidencia_externa(fin, ev["hueco_s"], ruta)
    if externo is not None:
        ev["externo"] = externo
    if no_concluyente is not None:
        ev["no_se_pudo_leer"].append(no_concluyente)


def recoge(
    boots: list[dict[str, Any]], i: int, fantasmas: list[dict[str, Any]] | tuple[()] = ()
) -> dict[str, Any]:
    """Evidencia del boot boots[i]; el boot siguiente (i+1) aporta BERT y hueco, salvo que
    `fantasmas` (los arranques fantasma entre i e i+1, en orden) se interpongan."""
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
    ev["cola_journal_vacia"] = not cola
    if ev["telemetria"] is None:
        ev["no_se_pudo_leer"].append("telemetria_gpu (no existe para este boot)")
    sig = boots[i + 1] if i + 1 < len(boots) else None
    # Un fantasma entre este boot y el siguiente del journal es lo que de verdad arranco despues:
    # la ventana del corte termina donde el empieza, y el BERT y el bootstatus del siguiente son suyos.
    proximo = fantasmas[0] if fantasmas else None
    hasta = proximo["inicio_epoch"] if proximo else (sig["first_entry"] / 1e6 if sig else None)
    ev.update(_evidencia_forense(b, sig, no_leido, hasta))
    if sig is not None and hasta is not None:
        ev["hueco_s"] = round(hasta - fin)
        _anade_evidencia_externa(ev, fin)
        if proximo:
            ev["bert_siguiente"] = None
            ev["bert"] = {"estado": f"no atribuido: el arranque fantasma {proximo['boot_id'][:8]} se interpone"}
        else:
            _anade_arranque_siguiente(ev, sig["index"], i + 1 == len(boots) - 1)
        _anade_fuera_del_journal(
            ev, b["first_entry"] / 1e6, fin, proximo["boot_id"] if proximo else sig["boot_id"], hasta
        )
    return ev


def _anade_arranque_siguiente(ev: dict[str, Any], idx: int, vivo: bool) -> None:
    """BERT y bootstatus del arranque `idx`, que hablan del reset que lo inicio, o sea de la muerte
    del anterior. Del arranque vivo el bootstatus sale de sysfs; de los demas, de su journal."""
    k = _journal("-b", str(idx), "-k", "--grep", "BERT: Error records from previous boot", "-n", "1")
    ev["bert_siguiente"] = k.returncode == 0 and "BERT:" in k.stdout
    ev["bert"] = bert_registro(idx)
    if vivo:
        try:
            ev["bootstatus_siguiente"] = int(WATCHDOG_BOOTSTATUS.read_text(encoding="utf-8"))
            ev["bootstatus_fuente"] = str(WATCHDOG_BOOTSTATUS)
            return
        except (OSError, ValueError):
            pass
    estado, fuente = bootstatus_por_journal(idx)
    if estado is None:
        ev["no_se_pudo_leer"].append("watchdog_bootstatus")
    else:
        ev["bootstatus_siguiente"], ev["bootstatus_fuente"] = estado, fuente


def _anade_fuera_del_journal(
    ev: dict[str, Any], inicio: float, fin: float, siguiente_id: str, siguiente_inicio: float
) -> None:
    """kdump, pstore, etapas, evidencia externa con hora y anillo de ultimo aliento del boot cuya
    ventana de muerte es [fin, siguiente_inicio]. Lo que no se pudo leer va a `no_se_pudo_leer`."""
    no_leido = ev["no_se_pudo_leer"]
    ev["siguiente_inicio_epoch"] = siguiente_inicio
    ev["kdump"] = kdump_en(fin, siguiente_inicio)
    ev["pstore"] = pstore_de(siguiente_id, ev["boot_id"])
    if ev["pstore"] is None:
        no_leido.append(f"pstore_arranque ({PSTORE_DIR} ausente o ilegible)")
    elif ev["pstore"]["ilegibles"]:
        no_leido.append(f"pstore_arranque ({len(ev['pstore']['ilegibles'])} copias ilegibles)")
    etapas = etapas_de()
    if etapas is None:
        no_leido.append(f"etapas_arranque ({ETAPAS} ilegible o ausente)")
    elif _norm(ev["boot_id"]) in etapas:
        ev["etapas"] = resumen_etapas(etapas[_norm(ev["boot_id"])])
    else:
        no_leido.append("etapas_arranque (sin filas para este boot)")
    ev["tiempos_externos"] = tiempos_externos(inicio, fin, siguiente_inicio)
    ev["netconsole"] = netconsole_en(inicio, siguiente_inicio)
    ev["aliento"] = aliento_en(inicio, siguiente_inicio)
    if ev["aliento"] is None:
        no_leido.append(f"anillo_ultimo_aliento ({ANILLO} ilegible o ausente)")


def recoge_fantasma(
    g: dict[str, Any], siguiente_id: str, siguiente_inicio: float, idx_siguiente: int | None, vivo: bool
) -> dict[str, Any]:
    """Evidencia de un arranque fantasma: sin journal propio, solo lo que vive fuera de el. Si lo que
    arranco despues es un boot del journal (`idx_siguiente`), su BERT y su bootstatus son de este."""
    ev: dict[str, Any] = {
        "boot_id": g["boot_id"],
        "fantasma": True,
        "fantasma_fuente": g["fuente"],
        "cola_journal_vacia": True,
        "inicio_epoch": g["inicio_epoch"],
        "fin_epoch": g["fin_epoch"],
        "cierre": None,
        "journal_parado": False,
        "disparador": None,
        "colapso_en_ventana": False,
        "panic": False,
        "telemetria": _ultima_telemetria(g["boot_id"]),
        "lineas_diagnostico": [],
        "panic_linea": None,
        "cierre_pid1": None,
        "journal_danado": None,
        "vmcore": vmcore_en(g["fin_epoch"], siguiente_inicio),
        "hueco_s": round(siguiente_inicio - g["fin_epoch"]),
        "no_se_pudo_leer": [f"journal_boot_{g['boot_id'][:8]} (arranque fantasma: no esta en el journal)"],
    }
    if ev["telemetria"] is None:
        ev["no_se_pudo_leer"].append("telemetria_gpu (no existe para este boot)")
    _anade_evidencia_externa(ev, g["fin_epoch"])
    if idx_siguiente is not None:
        _anade_arranque_siguiente(ev, idx_siguiente, vivo)
    _anade_fuera_del_journal(ev, g["inicio_epoch"], g["fin_epoch"], siguiente_id, siguiente_inicio)
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
    """Una nota por boot terminado en la bandeja de hallazgos; el consumidor externo la recoge con su propio flujo. Un fallo
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
    try:
        boots = json.loads(r.stdout)
    except ValueError:
        # rc 0 sin JSON: lo da journalctl en un contenedor sin journal (medido el 2026-11-01); antes era un traceback
        print(f"COULD_NOT_RUN: journalctl --list-boots no devolvio JSON: {r.stdout[:80]!r}", file=sys.stderr)
        return 2
    filas = []
    ya = _ya_escritos() if a.escribe else set()
    almacenamiento: dict[str, Any] | None = None  # una foto por corrida, no por fila
    fantasmas = arranques_fantasma(boots, etapas_de())
    for i in range(
        max(0, len(boots) - 1 - a.ultimos), len(boots) - 1
    ):  # el ultimo sigue vivo
        sig = boots[i + 1]
        entre = [
            g for g in fantasmas
            if boots[i]["first_entry"] / 1e6 <= g["inicio_epoch"] < sig["first_entry"] / 1e6
        ]
        # (boot_idx, boot_id, boot_id_siguiente, recolector): el del journal y luego sus fantasmas
        turno: list[tuple[int | None, str, str, Any]] = [
            (boots[i]["index"], boots[i]["boot_id"], entre[0]["boot_id"] if entre else sig["boot_id"],
             lambda i=i, entre=entre: recoge(boots, i, entre))
        ]
        for k, g in enumerate(entre):
            nxt = entre[k + 1] if k + 1 < len(entre) else None
            turno.append((
                None, g["boot_id"], nxt["boot_id"] if nxt else sig["boot_id"],
                lambda g=g, nxt=nxt, i=i: recoge_fantasma(
                    g,
                    nxt["boot_id"] if nxt else boots[i + 1]["boot_id"],
                    nxt["inicio_epoch"] if nxt else boots[i + 1]["first_entry"] / 1e6,
                    None if nxt else boots[i + 1]["index"],
                    i + 1 == len(boots) - 1,
                ),
            ))
        for idx, bid, sig_id, recolecta in turno:
            if bid in ya:
                continue
            ev = recolecta()
            if almacenamiento is None:
                almacenamiento = salud_de_almacenamiento()
            fila = {
                "boot_idx": idx,
                "boot_id": bid,
                "boot_id_siguiente": sig_id,
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
