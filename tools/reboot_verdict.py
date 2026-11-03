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
detector de crashes de un consumidor externo vive aqui (una ficha reubicada al
consumidor de conocimiento, enmienda del 2026-10-11 a la SPEC). Cada fila lleva,
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
  externo      `externo/ping.jsonl` y `externo/energia.jsonl` (observador_ping, NAS y
               medidor_energia en la ATOM) MAS `externo/testigo/` (las series de
               `tools/testigo/bb_testigo.py` tal cual las escribe, con sus rotaciones,
               traidas por `observador_ping --trae-testigo`): ping y energia se mezclan
               (`ok` significa lo mismo en todas); netconsole (`texto`, o `b64`) y latido
               (`evento: latido`; `parada` es el testigo detenido) solo los da el testigo.
               Un enchufe sin voltaje (`voltaje_v: null`, Shelly Gen1) se lee por potencia,
               y la causa lo declara.
  etapas       /var/lib/blackbox/arranque/etapas.jsonl (y su rotacion `.1`), tal cual la
               escribe adopted/system-units/etapa-marca.sh: `realtime` epoch en segundos
               ($EPOCHREALTIME, puede ser null) y `monotonic` segundos desde el arranque
               (/proc/uptime). La cadena y las ramas son las de `tools/etapas_arranque.py`
               (`sesion-<uid>` incluido): hasta que etapa llego cada arranque, y los
               arranques FANTASMA (con etapas o fila de arranque.jsonl pero sin boot en
               `journalctl --list-boots`), que salen como fila propia.
  aliento      el anillo de ultimo aliento (`tools/ultimo_aliento.py`, 250 ms), leido con
               su propio `leer_anillo` y filtrado por `boot`: hora de muerte y curva termica
               (`temp_c` por zona).
  bootstatus   de los arranques que ya no son el vivo se lee del journal de kernel
               (linea de sbsa_gwdt), no solo de sysfs del arranque vivo.

Compatibilidad: sigue siendo `bb-reboot/1`. Ningun campo cambia de nombre ni de
sentido; `etiqueta` conserva su dominio de valores (lo que dice el journal y el
medidor de voltaje), con una sola correccion: un boot cuyo journal no devolvio
NINGUNA linea sale INDETERMINADO y no CORTE_ABRUPTO (no hay silencio que leer donde
no hubo lectura). La causa que cruza todas las fuentes va en el campo nuevo `causa`
(PANICO_KDUMP, PANICO_PSTORE, PANICO_NETCONSOLE, CORTE_DE_ENERGIA, CUELGUE,
FALLO_DE_ARRANQUE_EN_<ETAPA> -- la ULTIMA etapa de la cadena que alcanzo, donde se quedo --,
o la etiqueta misma; INDETERMINADO sin evidencia) con
su cita en `causa_fuente`. Las filas de arranques fantasma traen `boot_idx: null` y
`arranque_fantasma: true`; un consumidor que solo espera boots del journal las
distingue por ese campo.

Orden y reloj (2026-11-02): cada boot se lee con `journalctl -b <boot_id>`, nunca con `-b <index>`. En systemd 255
el indice relativo de `-b -N` NO es el `index` de `--list-boots` cuando un boot tuvo el reloj de pared adelantado
(medido: con cd2e65ee 3.4 h por delante, `-b -1` daba 709465ff y todos los demas se corrian uno, y las filas de
`--ultimos 32` citaban el cierre del boot anterior). El arranque vivo (`/proc/sys/kernel/random/boot_id`) va al final
de la lista y nunca se juzga. Un boot cuyo `first_entry` es posterior al de su sucesor, o con duracion negativa, sale
con `reloj_desfasado: true` y `desfase_s`; `reloj_desfasado_siguiente` marca la fila cuyo `hueco_s` sale del reloj
desfasado del siguiente. `--pendientes` juzga TODO boot terminado sin fila en `reboots.jsonl` (append-only:
las filas viejas no se reescriben). Los campos `gsp_timeout`, `gsp_timeout_monotonic_s`, `xid154`,
`gpu_fullchip_reset_asserts` y `gpu_reset_required_checks` informan la rafaga del GSP de 7.0.0-1024-nvidia; no
entran en la `etiqueta`.
"""

from __future__ import annotations

import os
import argparse
import base64
import binascii
import json
from datetime import datetime, timezone
import re
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from tools import etapas_arranque, hallazgo, medidor_energia, observador_ping, ultimo_aliento

DATOS = Path(os.environ.get("BLACKBOX_DATA", Path.home() / ".local/share/blackbox"))
TELEMETRIA = DATOS / "atom_gpu_telemetry.jsonl"
# Lo escriben otros paquetes; aqui solo se leen. Las rutas de root las fija arranque-forense.sh.
PSTORE_DIR = Path("/var/lib/blackbox/pstore")  # copias de /sys/fs/pstore y BERT + arranque.jsonl
ETAPAS = etapas_arranque.ETAPAS  # {boot_id, etapa, monotonic, realtime} de etapa-marca.sh, y `.1`
ANILLO = Path(ultimo_aliento.ANILLO_RUTA)  # anillo binario de 250 ms; se lee con ultimo_aliento.leer_anillo
EXTERNO: Path | None = None  # None: `$BLACKBOX_DATA/externo` leido en cada llamada, como medidor_energia
TESTIGO = "testigo"  # subdirectorio de EXTERNO donde `observador_ping --trae-testigo` deja las series del testigo
# La cadena de etapa-marca.sh (etapas_arranque.CADENA). `sesion-usuario` depende de que alguien entre y `gpu-lista` y
# `network-online` son ramas en paralelo: un boot sin ellas no fallo al arrancar.
ETAPAS_ORDEN = etapas_arranque.CADENA
ETAPA_ARRANQUE_COMPLETO = "graphical"
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
# La rafaga del GSP medida el 2026-11-02 en los boots con 7.0.0-1024-nvidia desde el 2026-10-30 19:05 (7cd0848b:
# 3 timeouts desde el segundo 24, un Xid 154 en el 38, 7057 asserts y 244 "Reset required"). Solo se informan.
PATRON_GSP_TIMEOUT = re.compile(r"NVRM: _issueRpcAndWait: rpcRecvPoll timedout")
PATRON_FULLCHIP_ASSERT = re.compile(r"Assertion failed: \(status == NV_OK\) \|\| \(status == NV_ERR_GPU_IN_FULLCHIP_RESET\)")
PATRON_RESET_REQUIRED = re.compile(r"Check failed: Reset required \[NV_ERR_RESET_REQUIRED\]")
MONOTONIC = re.compile(r"^\[\s*(\d+\.\d+)\]")  # prefijo de `journalctl -o short-monotonic`
BOOT_ID_ACTUAL = Path("/proc/sys/kernel/random/boot_id")
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
    falla de ping que cierre la ultima respuesta (el observador vivo y cubriendo) no concluye.
    Un enchufe sin voltaje (`voltaje_v: null`) se lee por potencia, y la razon lo dice."""
    ping, enc = t.get("ping") or {}, t.get("enchufe") or {}
    u, f = ping.get("ultima_respuesta"), ping.get("primera_falla")
    if u is None or f is None or f - u > SEGUIDO_S:
        return None
    eu, ef = enc.get("ultima_ok"), enc.get("primera_falla")
    if eu is not None and ef is not None and eu >= u - SIMULTANEO_S and ef <= f + SIMULTANEO_S:
        por_potencia = enc.get("falla_por") == "potencia"
        return (
            "CORTE_DE_ENERGIA",
            f"{enc['fuente']}:{enc['linea_falla']} + {ping['fuente']} (ultima respuesta {u}, primera falla {f})",
            f"el enchufe cayo (ultima lectura {eu}, primera falla {ef}) antes o a la vez que el TCP "
            f"(ultima respuesta {u}, primera falla {f}): se fue la energia"
            + (
                f"; sin voltaje medido, la caida es de potencia (< {medidor_energia.APAGADA_W:g} W): no distingue "
                "la pared (un bajon que tumba al adaptador) de la ATOM o su adaptador"
                if por_potencia
                else ""
            ),
        )
    tras = enc.get("tras_caida_tcp") or []
    if tras and all(
        r.get("ok") is True
        and (r.get("voltaje_v") is None or _es_num(r["voltaje_v"]) and r["voltaje_v"] >= medidor_energia.VOLTAJE_NORMAL_V)
        and _es_num(r.get("potencia_w"))
        and r["potencia_w"] >= medidor_energia.CARGA_W
        for r in tras
    ):
        sin_v = sum(1 for r in tras if r.get("voltaje_v") is None)
        return (
            "CUELGUE",
            f"{ping['fuente']} (primera falla {f}) + {enc['fuente']} ({len(tras)} lecturas con consumo despues)",
            f"el TCP cayo en {f} y el enchufe siguio midiendo consumo (>= {medidor_energia.CARGA_W:g} W): "
            "la maquina quedo energizada sin responder (cuelgue, o panic que no dejo rastro)"
            + (f"; {sin_v} de {len(tras)} lecturas sin voltaje: decide la potencia" if sin_v else ""),
        )
    return None


def _causa_por_etapas(ev: dict[str, Any]) -> tuple[str, str, str] | None:
    """FALLO_DE_ARRANQUE_EN_<etapa> si murio sin completar el arranque y poco despues de su ultima etapa. La
    etapa del nombre es la ULTIMA de la cadena que alcanzo: el arranque se quedo ahi (marcas hasta `basic`
    dan FALLO_DE_ARRANQUE_EN_BASIC, y la razon nombra la que nunca llego)."""
    et = ev.get("etapas") or {}
    if not et.get("maxima") or not et.get("faltante") or et.get("ultima_epoch") is None:
        return None
    vivio = None if ev.get("fantasma") else (ev.get("fin_epoch") or 0) - et["ultima_epoch"]
    if vivio is not None and vivio > VENTANA_FALLO_ARRANQUE_S:
        return None
    falta = et["faltante"]
    return (
        f"FALLO_DE_ARRANQUE_EN_{et['maxima'].upper().replace('-', '_')}",
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
        sin_rama = [r for r, m in (et.get("ramas") or {}).items() if m is None]
        razones.append(
            f"etapas de arranque: hasta '{et['maxima']}'"
            + (f", sin '{et['faltante']}'" if et.get("faltante") else ", arranque completo")
            + (f"; ramas sin marca: {', '.join(sin_rama)}" if sin_rama else "")
        )
    if (ev.get("externo") or {}).get("decidido_por") == "potencia":
        razones.append(f"medidor externo sin voltaje, decidido por potencia: {ev['externo']['motivo']}")
    if str((ev.get("bert") or {}).get("estado", "")).startswith("no atribuido"):
        razones.append(f"BERT y bootstatus del arranque siguiente {ev['bert']['estado']}: son de ese arranque, no de este")
    latido = (ev.get("tiempos_externos") or {}).get("latido") or {}
    if latido and not latido.get("en_el_hueco"):
        razones.append(
            f"el testigo externo callo junto con la ATOM (ultimo latido {latido.get('ultimo_hasta_la_muerte')}): "
            "lo que no registro en el hueco no es prueba de nada"
        )
    if latido.get("paradas_en_el_hueco"):
        razones.append("al testigo lo detuvieron (evento parada) dentro del hueco: su silencio despues no es de la ATOM")
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


def gpu_del_boot(lineas: list[str]) -> dict[str, Any]:
    """Hechos de la rafaga del GSP en el journal de kernel de un boot (`-o short-monotonic`): timeout de RPC con su
    primer segundo monotonic, Xid 154 y cuantos asserts de reset de chip completo y "Reset required" dejo. Lineas
    vacias dan False/0: un journal ilegible se declara aparte y sale None, no cero."""
    primer = next((ln for ln in lineas if PATRON_GSP_TIMEOUT.search(ln)), None)
    m = MONOTONIC.match(primer) if primer else None
    return {
        "gsp_timeout": primer is not None,
        "gsp_timeout_monotonic_s": float(m.group(1)) if m else None,
        "xid154": any(x["xid"] == 154 for x in xids_del_boot(lineas)),
        "gpu_fullchip_reset_asserts": sum(1 for ln in lineas if PATRON_FULLCHIP_ASSERT.search(ln)),
        "gpu_reset_required_checks": sum(1 for ln in lineas if PATRON_RESET_REQUIRED.search(ln)),
    }


GPU_SIN_LEER = dict.fromkeys(
    ("gsp_timeout", "gsp_timeout_monotonic_s", "xid154", "gpu_fullchip_reset_asserts", "gpu_reset_required_checks")
)


def _boot_actual() -> str | None:
    """boot_id del arranque vivo, sin guiones; None si no se puede leer."""
    try:
        return _norm(BOOT_ID_ACTUAL.read_text(encoding="ascii").strip())
    except OSError:
        return None


def _es_vivo(boots: list[dict[str, Any]], j: int) -> bool:
    """boots[j] es el arranque vivo. Sin boot_id legible o ausente del journal, el ultimo de la lista (lo de antes)."""
    actual = _boot_actual()
    if actual is not None and any(_norm(b["boot_id"]) == actual for b in boots):
        return _norm(boots[j]["boot_id"]) == actual
    return j == len(boots) - 1


def ordena_boots(boots: list[dict[str, Any]], actual: str | None) -> list[dict[str, Any]]:
    """El orden de `--list-boots` con el arranque vivo AL FINAL: es el mas reciente por definicion. systemd 255
    ordena la lista por hora de pared; con el reloj adelantado de cd2e65ee (2026-11-02: 16:29 de pared, y arranco entre 709465ff
    de las 11:44 y fc60e471 de las 13:02) la corrida de las 13:06 puso al vivo fc60e471 ANTES que el y lo juzgo CORTE_ABRUPTO."""
    vivo = [b for b in boots if actual is not None and _norm(b["boot_id"]) == actual]
    return [b for b in boots if b not in vivo] + vivo


def desfases(boots: list[dict[str, Any]]) -> dict[str, int]:
    """boot_id -> segundos de reloj de pared adelantado, para los boots cuyo `first_entry` es POSTERIOR al de su
    sucesor en el journal o cuya `last_entry` es anterior a su `first_entry` (duracion negativa). Medido el
    2026-11-02: c092e563 con duracion -64702 s y cd2e65ee 12405 s por delante de fc60e471, que arranco despues."""
    out: dict[str, int] = {}
    for i, b in enumerate(boots):
        candidatos = [b["first_entry"] - b["last_entry"]]
        if i + 1 < len(boots):
            candidatos.append(b["first_entry"] - boots[i + 1]["first_entry"])
        d = max(candidatos) / 1e6
        if d > 0:
            out[b["boot_id"]] = round(d)
    return out


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
        **(ev.get("gpu") or GPU_SIN_LEER),
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


def _es_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


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


def etapas_de() -> dict[str, dict[str, tuple[float | None, Any, str]]] | None:
    """boot_id normalizado -> {etapa: (realtime epoch o None, monotonic tal cual, "archivo:linea")} de
    etapas.jsonl y su rotacion `.1` (la vieja primero), con la PRIMERA vez que se registro cada etapa. Una
    marca con `realtime: null` (bash sin $EPOCHREALTIME) cuenta como etapa alcanzada pero no da hora.
    Las filas que no son {boot_id, etapa, monotonic, realtime} numericos o null se descartan, como en
    `etapas_arranque.leer_marcas`. None si la generacion vigente no se pudo leer."""
    viejo = ETAPAS.with_name(ETAPAS.name + ".1")
    vigente = _jsonl(ETAPAS)
    if vigente is None:
        return None
    out: dict[str, dict[str, tuple[float | None, Any, str]]] = {}
    for ruta, filas in ((viejo, _jsonl(viejo) or []), (ETAPAS, vigente)):
        for n, f in filas:
            bid, etapa, real, mono = f.get("boot_id"), f.get("etapa"), f.get("realtime"), f.get("monotonic")
            if not (isinstance(bid, str) and isinstance(etapa, str) and (real is None or _es_num(real))
                    and (mono is None or _es_num(mono))):
                continue
            out.setdefault(_norm(bid), {}).setdefault(etapa, (_epoch(real), mono, f"{ruta}:{n}"))
    return out


def resumen_etapas(vistas: Mapping[str, tuple[float | None, Any, Any]]) -> dict[str, Any]:
    """Hasta donde llego el arranque por la cadena de etapa-marca.sh. `faltante` es la etapa de la cadena
    que sigue a la mas avanzada mientras no llego a ETAPA_ARRANQUE_COMPLETO; una intermedia ausente (gdm en
    un arranque sin pantalla) va a `saltadas` y no cuenta como fallo. Las ramas (network-online, gpu-lista)
    se informan con su monotonic o None, y nunca deciden el fallo."""
    canon: dict[str, tuple[float | None, Any, str]] = {}
    for e, v in vistas.items():
        canon.setdefault(etapas_arranque.canonica(e), v)
    alcanzadas = [e for e in ETAPAS_ORDEN if e in canon]
    maxima = alcanzadas[-1] if alcanzadas else None
    i = ETAPAS_ORDEN.index(maxima) if maxima else -1
    horas = [v[0] for v in vistas.values() if v[0] is not None]
    return {
        "alcanzadas": alcanzadas,
        "maxima": maxima,
        "faltante": ETAPAS_ORDEN[i + 1] if i < ETAPAS_ORDEN.index(ETAPA_ARRANQUE_COMPLETO) else None,
        "saltadas": [e for e in ETAPAS_ORDEN[: max(i, 0)] if e not in canon],
        "ramas": {r: canon[r][1] if r in canon else None for r in etapas_arranque.RAMAS},
        "desconocidas": sorted(e for e in vistas if etapas_arranque.canonica(e) not in
                               (*ETAPAS_ORDEN, *etapas_arranque.RAMAS, "sesion-sistema")),
        "monotonic": {e: canon[e][1] for e in alcanzadas},
        "ultima_epoch": max(horas) if horas else None,
        "fuente": canon[maxima][2] if maxima else str(ETAPAS),
    }


def arranques_fantasma(
    boots: list[dict[str, Any]], etapas: Mapping[str, Mapping[str, tuple[float | None, Any, Any]]] | None
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
        con_hora: list[tuple[float, Any, Any]] = [(v[0], v[1], v[2]) for v in vistas.values() if v[0] is not None]
        if not con_hora:
            continue  # sin ninguna hora no se puede ubicar en el tramo del journal
        primera = min(con_hora, key=lambda v: v[0])
        vistos[bid] = {
            "boot_id": bid,
            "inicio_epoch": primera[0],
            "fin_epoch": max(v[0] for v in con_hora),
            "fuente": primera[2],
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


def _serie(nombre: str, *, en_la_atom: bool) -> list[Path]:
    """Archivos de una serie externa, del mas viejo al mas nuevo: las rotaciones del testigo (`<nombre>.jsonl.N`
    ... `.1`, como las deja bb_testigo.Diario), su vigente y, si `en_la_atom`, `externo/<nombre>.jsonl` (lo
    que escriben observador_ping, su sync del NAS y medidor_energia). Solo los que existen."""
    d = _externo() / TESTIGO
    rotadas = sorted(
        (p for p in d.glob(f"{nombre}.jsonl.*") if p.name.rsplit(".", 1)[-1].isdigit()),
        key=lambda p: -int(p.name.rsplit(".", 1)[-1]),
    )
    candidatas = [*rotadas, d / f"{nombre}.jsonl"] + ([_externo() / f"{nombre}.jsonl"] if en_la_atom else [])
    return [p for p in candidatas if p.is_file()]


def _en_ventana(
    rutas: list[Path], desde: float, hasta: float, clave: str = "epoch"
) -> list[tuple[str, int, dict[str, Any], float]]:
    """(archivo, linea, fila, epoch) de las filas con hora en [desde, hasta] de todas las `rutas`, por hora."""
    out = []
    for ruta in rutas:
        for n, f in _jsonl(ruta) or []:
            e = _epoch(f.get(clave))
            if e is not None and desde <= e <= hasta:
                out.append((str(ruta), n, f, e))
    return sorted(out, key=lambda x: x[3])


def _lectura_buena(f: dict[str, Any]) -> bool:
    """El enchufe contesto y la ATOM tenia energia: voltaje medido >= VOLTAJE_CAIDO_V o, sin voltaje
    (Shelly Gen1 del testigo), potencia >= APAGADA_W. Con voltaje medido la potencia no decide: voltaje normal
    y 0 W es la ATOM apagada con pared, y eso lo concluye medidor_energia (APAGADO_INTERNO), no esta regla."""
    if f.get("ok") is not True:
        return False
    v, w = f.get("voltaje_v"), f.get("potencia_w")
    if v is None:
        return w is not None and _es_num(w) and w >= medidor_energia.APAGADA_W
    return _es_num(v) and v >= medidor_energia.VOLTAJE_CAIDO_V


def tiempos_externos(inicio: float, fin: float, siguiente_inicio: float) -> dict[str, Any]:
    """Cuando dejo de responder la ATOM por TCP y que hacia el enchufe en ese momento, de las series de
    ping y energia de la ATOM y del testigo (mismo `ok`: «la ATOM contesto»), mas el latido del testigo
    (`evento: latido`). Lee y resume; la conclusion la saca `_causa_por_tiempos`, que es pura."""
    ping, energia, latido = _serie("ping", en_la_atom=True), _serie("energia", en_la_atom=True), _serie("latido", en_la_atom=False)
    u = observador_ping.ultima_respuesta(ping, siguiente_inicio)
    if u is not None and u < inicio:
        u = None  # la ultima respuesta es de un boot anterior: este no tiene cobertura
    f = observador_ping.primera_falla(ping, u, siguiente_inicio) if u is not None else None
    filas_p = _en_ventana(ping, inicio, siguiente_inicio)
    filas_e = _en_ventana(energia, inicio, siguiente_inicio)
    enchufe: dict[str, Any] = {
        "fuente": ", ".join(map(str, energia)) or str(_externo() / "energia.jsonl"),
        "ultima_ok": None, "primera_falla": None, "linea_falla": None, "falla_por": None, "tras_caida_tcp": [],
    }
    if u is not None:
        falla = next(((a, n, r, e) for a, n, r, e in filas_e if e > u - SIMULTANEO_S and not _lectura_buena(r)), None)
        if falla:
            a, n, r, e = falla
            enchufe.update(fuente=a, primera_falla=e, linea_falla=n)
            enchufe["falla_por"] = (
                "potencia" if r.get("ok") is True and r.get("voltaje_v") is None else
                "voltaje" if r.get("ok") is True else "enchufe_mudo"
            )
            antes = [x[3] for x in filas_e if x[3] < e and _lectura_buena(x[2])]
            enchufe["ultima_ok"] = max(antes) if antes else None
    if f is not None:
        enchufe["tras_caida_tcp"] = [
            {k: r.get(k) for k in ("epoch", "ok", "voltaje_v", "potencia_w")}
            for _, _, r, e in filas_e
            if f < e <= min(f + SEGUIDO_S, siguiente_inicio)
        ]
    r: dict[str, Any] = {
        "filas": len(filas_p) + len(filas_e),
        "ping": {"fuente": ", ".join(map(str, ping)) or str(_externo() / "ping.jsonl"),
                 "ultima_respuesta": u, "primera_falla": f, "filas_en_ventana": len(filas_p)},
        "enchufe": enchufe,
        "latido": None,
    }
    if latido:
        filas_l = [(x[2], x[3]) for x in _en_ventana(latido, float("-inf"), float("inf"))]
        horas = [e for x, e in filas_l if x.get("evento") == "latido"]
        muerte = max(fin, u or fin)
        r["latido"] = {
            "fuente": ", ".join(map(str, latido)),
            "ultimo_hasta_la_muerte": max((e for e in horas if e <= muerte), default=None),
            "en_el_hueco": sum(1 for e in horas if muerte < e <= siguiente_inicio),
            # `parada`: alguien detuvo al testigo; si cae en el hueco, su silencio despues no es de la ATOM
            "paradas_en_el_hueco": sum(1 for x, e in filas_l if x.get("evento") == "parada" and muerte < e <= siguiente_inicio),
        }
    return r


def _texto_udp(f: dict[str, Any]) -> str:
    """El texto de una fila de netconsole del testigo: `texto`, o `b64` (datagrama que no era UTF-8) decodificado."""
    if isinstance(f.get("texto"), str):
        return f["texto"]
    if isinstance(f.get("b64"), str):
        try:
            return base64.b64decode(f["b64"], validate=True).decode("utf-8", errors="replace")
        except (ValueError, binascii.Error):
            return ""
    return ""


def netconsole_en(inicio: float, siguiente_inicio: float) -> dict[str, Any] | None:
    """Lineas que el testigo recibio por UDP (`externo/testigo/netconsole.jsonl`: `epoch` de recepcion y el
    texto en `texto` o `b64`) durante el boot; None si no hay ninguna."""
    filas = [x for x in _en_ventana(_serie("netconsole", en_la_atom=False), inicio, siguiente_inicio) if x[3] < siguiente_inicio]
    if not filas:
        return None
    panico = next(((a, n, _texto_udp(f)) for a, n, f, _ in filas if PANIC_TEXTO in _texto_udp(f)), None)
    return {
        "lineas_en_ventana": len(filas),
        "ultima_epoch": filas[-1][3],
        "ultima_linea": _texto_udp(filas[-1][2])[:300],
        "linea_panico": panico[2].strip()[:300] if panico else None,
        "fuente_panico": f"{panico[0]}:{panico[1]}" if panico else None,
    }


def aliento_en(boot_id: str, inicio: float, siguiente_inicio: float) -> dict[str, Any] | None:
    """Ultima `muestra` del anillo de ultimo aliento (250 ms) de ESTE boot, su periodo medido y la curva
    termica (`temp_c` por zona) de los CURVA_TERMICA_S previos, una lectura por segundo. Cada registro lleva
    `boot` (boot_id sin guiones): se filtra por el; uno con `boot: desconocido` (el demonio no pudo leer
    /proc) se atribuye por hora, si cae en [inicio, siguiente_inicio). None si el anillo no se pudo leer."""
    try:
        anillo = ultimo_aliento.leer_anillo(str(ANILLO))
    except (OSError, ValueError, KeyError):
        return None
    propio = _norm(boot_id)
    filas = [
        (r, float(r["ts"]))
        for r in anillo["registros"]
        if r.get("tipo") == "muestra" and _es_num(r.get("ts"))
        and (r.get("boot") == propio or r.get("boot") == "desconocido" and inicio <= r["ts"] < siguiente_inicio)
    ]
    filas.sort(key=lambda x: x[1])
    vacio = {"filas_en_ventana": 0, "ultima_epoch": None, "periodo_s": None, "ultima_lectura": None,
             "curva_termica": None}
    if not filas:
        return vacio
    ultima = filas[-1][1]
    pasos = [b[1] - a[1] for a, b in zip(filas[-9:], filas[-8:])]
    curva: dict[int, dict[str, Any]] = {}
    for f, e in filas:
        if e >= ultima - CURVA_TERMICA_S and isinstance(f.get("temp_c"), dict):
            curva[int(e)] = {"epoch": e, "termica": f["temp_c"]}  # la ultima de cada segundo
    return {
        **vacio,
        "filas_en_ventana": len(filas),
        "ultima_epoch": ultima,
        "periodo_s": round(statistics.median(pasos), 3) if pasos else None,
        "ultima_lectura": filas[-1][0],
        "curva_termica": list(curva.values()) or None,
    }


def bootstatus_por_journal(idx: int | str) -> tuple[int | None, str | None]:
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
    """`errors="replace"`: el journal de kernel trae bytes que no son UTF-8 (medido el 2026-11-02: tumbo un
    script con UnicodeDecodeError); un byte malo no puede costar la lectura entera del boot."""
    return subprocess.run(
        ["journalctl", "--no-pager", *args],
        capture_output=True,
        text=True,
        errors="replace",
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


def _disparador_boot(idx: int | str) -> str | None:
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


def bert_registro(idx_siguiente: int | str) -> dict[str, Any]:
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
    k = _journal("-b", b["boot_id"], "-k")
    if k.returncode != 0:
        no_leido.append(f"journal_kernel_boot_{b['index']}")
    kernel = k.stdout.splitlines()
    # `_PID=1` a proposito: sin el filtro, uvicorn o GNOME Shell tambien escriben "Shutting down."
    # (8 falsos positivos medidos por el consumidor externo el 2026-09-29 sobre el panic de `07db1a8a`).
    # aparte y con monotonic: la hora del GSP se cuenta desde el arranque, y `lineas_diagnostico` conserva su formato
    g = _journal("-b", b["boot_id"], "-k", "-o", "short-monotonic")
    if g.returncode != 0:
        no_leido.append(f"journal_kernel_gpu_boot_{b['index']}")
    p1 = _journal("-b", b["boot_id"], "-o", "cat", "_PID=1")
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
        "gpu": gpu_del_boot(g.stdout.splitlines()) if g.returncode == 0 else None,
    }
    if sig is not None:
        jd = _journal(
            "-b", sig["boot_id"], "-o", "cat", "-u", "systemd-journald.service"
        )
        if jd.returncode != 0:
            no_leido.append(f"journal_journald_boot_{sig['index']}")
        m = PATRON_UNCLEAN.search(jd.stdout)
        ev["journal_danado"] = m.group(1) if m else None
        ev["vmcore"] = vmcore_en(fin, hasta if hasta is not None else sig["first_entry"] / 1e6)
    return ev


def _evidencia_externa(
    fin: float, hueco_s: float, ruta: Path | list[Path] | None = None
) -> tuple[dict[str, Any] | None, str | None]:
    """(externo, no_concluyente): `externo` si el medidor concluye con voltaje o si, sin voltaje, decidio por
    potencia (`decidido_por`); filas sin ninguna conclusion se declaran como no leido."""
    ext = medidor_energia.ventana_de_corte(ruta if ruta is not None else _serie("energia", en_la_atom=True), fin, hueco_s)
    if ext is None:
        return None, None
    if ext["voltaje_perdido"] is None and ext.get("decidido_por") != "potencia":
        return None, f"medidor_externo ({ext['motivo']})"
    return ext, None


def _anade_evidencia_externa(ev: dict[str, Any], fin: float, ruta: Path | list[Path] | None = None) -> None:
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
    r = _journal("-b", b["boot_id"], "-o", "short-iso", "-n", "500")
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
        "-b", b["boot_id"], "-k", "--grep", "Kernel panic - not syncing", "-n", "1"
    )
    ev: dict[str, Any] = {
        "boot_id": b["boot_id"],
        "fin_epoch": fin,
        "cierre": cierre,
        "journal_parado": any(JOURNAL_PARADO.search(ln) for ln in cola),
        "disparador": _disparador_boot(b["boot_id"]) if cierre else None,
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
            _anade_arranque_siguiente(ev, sig["boot_id"], _es_vivo(boots, i + 1))
        _anade_fuera_del_journal(
            ev, b["first_entry"] / 1e6, fin, proximo["boot_id"] if proximo else sig["boot_id"], hasta
        )
    return ev


def _anade_arranque_siguiente(ev: dict[str, Any], idx: int | str, vivo: bool) -> None:
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
    ev["aliento"] = aliento_en(ev["boot_id"], inicio, siguiente_inicio)
    if ev["aliento"] is None:
        no_leido.append(f"anillo_ultimo_aliento ({ANILLO} ilegible o ausente)")


def recoge_fantasma(
    g: dict[str, Any], siguiente_id: str, siguiente_inicio: float, idx_siguiente: int | str | None, vivo: bool
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
    """boot_id con fila vigente. El ledger es solo-anexar: una fila `{"boot_id", "anula": true, "corrige_linea": N}` deja
    sin efecto la anterior de ese boot (gana la ultima), y `--pendientes` lo vuelve a juzgar."""
    if not SALIDA.exists():
        return set()
    vigentes: set[str] = set()
    for ln in SALIDA.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        f = json.loads(ln)
        (vigentes.discard if f.get("anula") else vigentes.add)(f["boot_id"])
    return vigentes


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
    ap.add_argument(
        "--pendientes", action="store_true",
        help="todo boot terminado de --list-boots sin fila en reboots.jsonl (ignora --ultimos); idempotente",
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
    ya = _ya_escritos() if a.escribe or a.pendientes else set()
    almacenamiento: dict[str, Any] | None = None  # una foto por corrida, no por fila
    actual = _boot_actual()
    if actual is None or all(_norm(b["boot_id"]) != actual for b in boots):
        print(f"# arranque vivo no localizado en --list-boots ({BOOT_ID_ACTUAL}: {actual}): se supone el ultimo",
              file=sys.stderr)
    boots = ordena_boots(boots, actual)
    desf = desfases(boots)
    fantasmas = arranques_fantasma(boots, etapas_de())
    desde = 0 if a.pendientes else max(0, len(boots) - 1 - a.ultimos)
    for i in range(desde, len(boots) - 1):  # el ultimo sigue vivo: ordena_boots pone ahi al arranque vivo
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
                    None if nxt else boots[i + 1]["boot_id"],
                    _es_vivo(boots, i + 1),
                ),
            ))
        for idx, bid, sig_id, recolecta in turno:
            if bid in ya or _norm(bid) == actual:
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
                "reloj_desfasado": bid in desf,
                "desfase_s": desf.get(bid),
                "reloj_desfasado_siguiente": sig_id in desf,
            }
            if bid in desf or sig_id in desf:
                fila["razones"].append(
                    "reloj de pared desfasado ("
                    + (f"este boot {desf[bid]} s" if bid in desf else "")
                    + (" y " if bid in desf and sig_id in desf else "")
                    + (f"el siguiente {desf[sig_id]} s" if sig_id in desf else "")
                    + "): hueco_s, duracion_s y las horas de la fila salen de ese reloj, no del tiempo real"
                )
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
